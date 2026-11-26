"""Tests for create_once.py, against the fake Jira. No network. Every name, site and title here is made up."""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import create_once as co   # noqa: E402
import fake_jira           # noqa: E402

HOST = "fixture-site.example.invalid"
TITLE = "Archive the October export files"
PERSON = "A made-up person"


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-once-test-")
        self.state = os.path.join(self.folder, "state")
        self.fake = fake_jira.FakeJira()
        self.draft = self.write_draft("export-archive", "SAND", TITLE)
        self.allowlist = os.path.join(self.folder, "allowlist.json")
        self.write_allowlist([("20001", HOST)])
        self.clock = datetime.datetime(2026, 11, 26, 9, 0, 0)
        self.real_now, co.now_utc = co.now_utc, lambda: self.clock
        self.conns = []

    def tearDown(self):
        co.now_utc = self.real_now
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def write_draft(self, name, project, summary):
        path = os.path.join(self.folder, name + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"project": project, "summary": summary}, f)
        return path

    def write_allowlist(self, entries):
        with open(self.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": [{"site_fingerprint": co.site_fingerprint(host), "project_id": project} for project, host in entries]}, f)

    def later(self, seconds):
        self.clock += datetime.timedelta(seconds=seconds)

    def run_command(self, command, host=HOST, draft=None, **options):
        del co.LINES[:]
        co.PENDING.clear()
        conn = co.Connection(self.fake.get, self.fake.post if command == "confirm" else None, host)
        self.conns.append(conn)
        args = argparse.Namespace(command=command, source="fake", draft=draft or self.draft, state=self.state, allowlist=self.allowlist, fingerprint=None,
                                  confirmed_by=None, pretend_minutes_later=0, pretend_seconds_later=0, interrupt_at=None, result=None, log=None)
        for name, value in options.items():
            setattr(args, name, value)
        code = co.run(args, conn)
        co.write_pending()
        text = "\n".join(shown for shown, _ in co.LINES)
        self.saved = "\n".join(saved for _, saved in co.LINES)
        self.assertNotIn(fake_jira.HOSTILE_SUMMARY, text)      # other people's titles are never shown
        return code, text

    def preview(self, **options):
        code, text = self.run_command("preview", **options)
        found = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text)
        return code, text, found.group(1) if found else None

    def confirm(self, fingerprint, **options):
        options.setdefault("confirmed_by", PERSON)
        return self.run_command("confirm", fingerprint=fingerprint, **options)

    def resolve(self, **options):
        return self.run_command("resolve", **options)

    def release(self):
        """Two empty searches that count: each 60 seconds or more after the request ended, and 30 or more apart."""
        self.later(91)
        first = self.resolve()
        self.later(31)
        return first, self.resolve()

    def record(self, name="export-archive"):
        with open(os.path.join(self.state, "intents", name + ".json"), encoding="utf-8") as f:
            return json.load(f)

    def record_bytes(self):
        with open(os.path.join(self.state, "intents", "export-archive.json"), "rb") as f:
            return f.read()

    def keyed(self):
        key = self.record()["key"]
        return [issue for issue in self.fake.state["issues"].values() if key in issue["labels"]]

    def posts(self):
        return sum(1 for method, _ in self.fake.requests if method == "POST")

    def interrupted(self, point):
        """A preview, then a confirmed run that ends at `point`."""
        _, _, code = self.preview()
        result = self.confirm(code, interrupt_at=point)
        self.assertEqual(result[0], 3)
        return result[1]

    def unknown(self, fail_post):
        _, _, code = self.preview()
        self.fake.fail_post = fail_post
        return self.confirm(code)


class TheKey(Case):
    """Criterion 1: each creation carries a stable key stored on the Jira item."""

    def test_the_key_is_saved_before_anything_is_asked_of_jira(self):
        seen = []
        real_get = self.fake.get
        self.fake.get = lambda path, params=None: (seen.append(os.path.exists(os.path.join(self.state, "intents", "export-archive.json"))), real_get(path, params))[1]
        self.preview()
        self.assertTrue(seen and all(seen))

    def test_the_key_is_the_same_at_every_preview_and_survives_an_edit_of_the_title(self):
        self.preview()
        first = self.record()["key"]
        self.assertRegex(first, r"^gtq-key-[0-9a-f]{16}$")
        self.write_draft("export-archive", "SAND", TITLE + ", corrected")
        self.later(5)
        self.preview()
        self.assertEqual(self.record()["key"], first)

    def test_two_drafts_with_the_same_words_get_different_keys(self):
        other = self.write_draft("second-draft", "SAND", TITLE)
        self.preview()
        self.preview(draft=other)
        self.assertNotEqual(self.record()["key"], self.record("second-draft")["key"])

    def test_the_key_goes_to_jira_inside_the_request_that_creates_the_task(self):
        bodies = []
        real_post = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (bodies.append(body), real_post(path, params, body))[1]
        _, _, code = self.preview()
        self.assertEqual(self.confirm(code)[0], 0)
        key = self.record()["key"]
        self.assertEqual(bodies, [{"fields": {"project": {"id": "20001"}, "issuetype": {"id": "10002"}, "summary": TITLE, "labels": [key]}}])
        self.assertEqual([issue["labels"] for issue in self.keyed()], [[key]])

    def test_the_record_says_sending_at_the_moment_the_request_goes(self):
        seen = []
        real_post = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (seen.append(self.record()["status"]), real_post(path, params, body))[1]
        _, _, code = self.preview()
        self.confirm(code)
        self.assertEqual(seen, ["sending"])


class AnOrdinaryRun(Case):
    """Criteria 4, 5, 8 and 9."""

    def test_the_preview_shows_site_project_changes_and_both_checks_and_writes_nothing(self):
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 0)
        for wanted in ("PREVIEW. Nothing has been written.", "https://" + HOST, "SAND (project id 20001)", "| " + TITLE, "labels      one label, the key: " + self.record()["key"],
                       "(CREATE_ISSUES):   yes", "Duplicate check 1, by the key", "Found: 0.", "Duplicate check 2, by the title", "Where Jira cannot check",
                       "Every one was a GET", "The two are the same"):
            self.assertIn(wanted, text)
        self.assertTrue(fingerprint)
        self.assertEqual(self.posts(), 0)
        self.assertEqual(len(self.fake.state["issues"]), 3)

    def test_a_confirmed_run_creates_one_task_and_records_it(self):
        _, _, fingerprint = self.preview()
        result = os.path.join(self.folder, "out", "result.md")
        code, text = self.confirm(fingerprint, result=result)
        self.assertEqual(code, 0, text)
        record = self.record()
        self.assertEqual(record["status"], "linked")
        self.assertEqual((record["issue"]["id"], record["issue"]["key"]), ("30004", "SAND-3"))
        self.assertEqual(len(self.keyed()), 1)
        for wanted in ("CONFIRMATION for preview %s, given by: %s" % (fingerprint, PERSON), "WRITTEN to Jira: one task, SAND-3 (issue id 30004)",
                       "The confirmation and the write happened in this one run", "Issue key: SAND-3", "Jira issue id 30004, carrying the label " + record["key"],
                       "Target project: SAND (project id 20001)", "Confirmed by: " + PERSON, "this one, and no other"):
            self.assertIn(wanted, text)
        with open(result, encoding="utf-8") as f:
            saved = f.read()
        self.assertIn("Issue key: SAND-3", saved)
        self.assertNotIn(HOST, saved)

    def test_running_it_all_again_creates_nothing(self):
        _, _, fingerprint = self.preview()
        self.confirm(fingerprint)
        self.later(30)
        code, text, again = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("NOTHING TO CREATE", text)
        self.assertIn("SAND-3 (issue id 30004)", text)
        self.assertIsNone(again)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("already exists: SAND-3", text)
        code, text = self.resolve()
        self.assertEqual(code, 0)
        self.assertIn("ALREADY RECORDED", text)
        self.assertEqual((self.posts(), len(self.keyed()), len(self.fake.state["issues"])), (1, 1, 4))

    def test_no_temporary_file_is_left_behind(self):
        _, _, fingerprint = self.preview()
        self.confirm(fingerprint)
        left = [name for _, _, names in os.walk(self.state) for name in names if name.endswith(".tmp")]
        self.assertEqual(left, [])


class Interruptions(Case):
    """Criteria 2 and 3, and the first stretch goal: three points."""

    def test_after_jira_accepted_and_before_anything_was_recorded(self):
        text = self.interrupted("after-send")
        self.assertIn("STOPPED ON PURPOSE", text)
        self.assertEqual(self.record()["status"], "sending")
        self.assertIsNone(self.record()["issue"])
        self.assertEqual(len(self.keyed()), 1)
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 1)
        self.assertIn("ITS OUTCOME IS NOT KNOWN", text)
        self.assertIsNone(fingerprint)
        code, text = self.resolve()
        self.assertEqual(code, 0, text)
        self.assertIn("FOUND BY ITS KEY: SAND-3 (issue id 30004)", text)
        self.assertIn("NOTHING WAS CREATED by this run", text)
        self.assertIn("Every one was a GET", text)
        record = self.record()
        self.assertEqual((record["status"], record["issue"]["id"]), ("linked", "30004"))
        self.assertIn("found by its key", record["issue"]["how"])
        self.assertIn("Confirmed by: " + PERSON, text)
        self.assertEqual((self.posts(), len(self.keyed())), (1, 1))

    def test_before_the_request_went(self):
        self.interrupted("before-send")
        self.assertEqual((self.record()["status"], self.posts(), len(self.keyed())), ("sending", 0, 0))
        _, _, fingerprint = self.preview()
        self.assertIsNone(fingerprint)
        code, text = self.resolve()
        self.assertEqual(code, 1)
        self.assertIn("NOT FOUND YET", text)
        self.assertIn("Empty searches that count so far: 0", text)
        self.assertEqual(self.record()["status"], "sending")
        (code, text), second = self.release()
        self.assertEqual(code, 1)
        self.assertIn("Empty searches that count so far: 1", text)
        code, text = second
        self.assertEqual(code, 0)
        self.assertIn("NOT FOUND, at ", text)
        self.assertIn("It will carry the same key", text)
        self.assertIn("THAT IS NOT PROOF", text)
        self.assertIn("make a new preview", text)
        self.assertEqual((self.record()["status"], self.posts()), ("released", 0))
        code, text, fingerprint = self.preview()
        self.assertIn("this is attempt 2", text)
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertEqual((self.posts(), len(self.keyed()), self.record()["status"]), (1, 1, "linked"))

    def test_the_interrupted_run_says_what_jira_answered(self):
        self.assertIn("The request was sent, and Jira answered 201.", self.interrupted("after-send"))
        self.tearDown()
        self.setUp()
        _, _, fingerprint = self.preview()
        self.fake.fail_post = 400
        code, text = self.confirm(fingerprint, interrupt_at="after-send")
        self.assertIn("The request was sent, and Jira answered 400.", text)

    def test_an_issue_with_the_key_that_is_not_a_task_is_not_recorded(self):
        self.interrupted("before-send")
        made = self.fake.other_issue("SAND", "labelled by hand", [self.record()["key"]])
        self.fake.state["issues"][made]["type_id"] = fake_jira.STORY
        code, text = self.resolve()
        self.assertEqual(code, 2)
        self.assertEqual(self.record()["status"], "sending")

    def test_after_the_task_was_recorded_and_before_it_was_read_back(self):
        self.interrupted("after-record")
        self.assertEqual(self.record()["status"], "linked")
        code, text = self.resolve()
        self.assertEqual(code, 0)
        self.assertIn("ALREADY RECORDED: SAND-3", text)
        code, text, fingerprint = self.preview()
        self.assertIn("NOTHING TO CREATE", text)
        self.assertEqual((self.posts(), len(self.keyed())), (1, 1))

    def test_a_confirmation_while_the_outcome_is_unknown_is_refused(self):
        self.interrupted("after-send")
        with open(os.path.join(self.state, "previews", os.listdir(os.path.join(self.state, "previews"))[0]), encoding="utf-8") as f:
            fingerprint = json.load(f)["fingerprint"][:12]
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("ITS OUTCOME IS NOT KNOWN", text)
        self.assertEqual(self.posts(), 1)


class WhenNoAnswerComes(Case):
    """A timeout is an unknown outcome, not a failure."""

    def test_no_answer_and_nothing_created_is_not_known_and_is_not_sent_again(self):
        code, text = self.unknown("timeout")
        self.assertEqual(code, 2)
        self.assertIn("IT IS NOT KNOWN whether Jira created the task", text)
        self.assertIn("DO NOT CONFIRM AGAIN", text)
        self.assertEqual((self.record()["status"], self.posts(), len(self.keyed())), ("uncertain", 1, 0))

    def test_no_answer_and_the_task_was_created(self):
        code, _ = self.unknown("applied-timeout")
        self.assertEqual((code, self.record()["status"], len(self.keyed())), (2, "uncertain", 1))
        code, text = self.resolve()
        self.assertEqual(code, 0)
        self.assertIn("FOUND BY ITS KEY", text)
        self.assertEqual((self.record()["status"], self.posts(), len(self.keyed())), ("linked", 1, 1))

    def test_a_server_error_is_not_taken_to_mean_nothing_was_written(self):
        for status in (500, 502, 503, 429):
            self.tearDown()
            self.setUp()
            code, text = self.unknown(status)
            self.assertEqual((code, self.record()["status"]), (2, "uncertain"), status)
            self.assertIn("IT IS NOT KNOWN", text)

    def test_a_refusal_by_jira_with_nothing_found_means_nothing_was_written(self):
        for status in co.REFUSALS:
            self.tearDown()
            self.setUp()
            code, text = self.unknown(status)
            self.assertEqual((code, self.record()["status"], self.posts()), (1, "new", 1), status)
            self.assertIn("Jira answered %d to the write" % status, text)
            self.later(5)
            _, text, fingerprint = self.preview()
            self.assertTrue(fingerprint)
            self.assertIn("this is attempt 2", text)

    def test_a_refusal_is_not_believed_when_the_search_after_it_fails(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_post = 403
        self.fake.before_post = lambda fake: setattr(fake, "fail_search", 500)
        code, text = self.confirm(fingerprint)
        self.assertEqual((code, self.record()["status"]), (2, "uncertain"))

    def test_a_refusal_is_not_believed_when_an_issue_carries_the_key_after_it(self):
        _, _, fingerprint = self.preview()
        key = self.record()["key"]
        self.fake.fail_post = 400
        self.fake.before_post = lambda fake: fake.other_issue("SAND", TITLE, [key])
        code, text = self.confirm(fingerprint)
        self.assertEqual((code, self.record()["status"]), (2, "uncertain"))
        self.assertIn("finds 1 issue", text)

    def test_a_read_that_fails_after_the_write_does_not_lose_the_new_issue(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_get_after_post = "broken"
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertEqual((self.record()["status"], self.record()["issue"]["id"]), ("linked", "30004"))


class WhenTheSearchIsBehind(Case):
    def test_one_empty_search_does_not_release_the_record(self):
        self.interrupted("after-send")
        self.fake.search_lag = 1
        self.later(120)
        code, text = self.resolve()
        self.assertEqual(code, 1)
        self.assertIn("NOT FOUND YET", text)
        self.assertEqual((self.record()["status"], self.posts()), ("sending", 1))
        code, text = self.resolve()
        self.assertEqual(code, 0)
        self.assertIn("FOUND BY ITS KEY", text)
        self.assertEqual(len(self.keyed()), 1)

    def test_empty_searches_soon_after_sending_or_close_together_do_not_release_it(self):
        self.interrupted("after-send")
        self.fake.search_lag = 9
        for _ in range(3):                      # at 10, 20 and 30 seconds: too soon to count
            self.later(10)
            self.assertEqual(self.resolve()[0], 1)
        self.assertEqual(self.record()["status"], "sending")
        self.later(65)                          # at 95 seconds: the first that counts
        self.assertEqual(self.resolve()[0], 1)
        self.later(5)                           # at 100: counts, and is too close to the first
        self.assertEqual(self.resolve()[0], 1)
        self.assertEqual(self.record()["status"], "sending")
        self.later(26)                          # at 126: 31 seconds after the first that counted
        self.assertEqual(self.resolve()[0], 0)
        self.assertEqual(self.record()["status"], "released")

    def test_a_killed_runs_request_is_taken_to_have_lasted_as_long_as_a_request_may(self):
        self.interrupted("before-send")          # no time of ending was recorded
        self.later(65)                           # 60 seconds after sending, and not 60 after the latest it could have ended
        self.resolve()
        self.later(31)
        self.assertEqual(self.resolve()[0], 1)
        self.assertEqual(self.record()["status"], "sending")
        self.later(31)
        self.assertEqual(self.resolve()[0], 0)

    def test_the_wait_is_counted_from_when_the_request_ended_if_that_is_known(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_post = "timeout"
        self.fake.before_post = lambda fake: self.later(25)       # the request hung for 25 seconds before it failed
        self.confirm(fingerprint)
        sent, ended = co.parse(self.record()["attempts"][-1]["sent_at"]), co.parse(self.record()["attempts"][-1]["ended_at"])
        self.assertEqual((ended - sent).total_seconds(), 25)
        self.later(59)
        self.resolve()
        self.later(31)
        self.assertEqual(self.resolve()[0], 1)                     # the first was 59 seconds after it ended: it did not count
        self.later(31)
        self.assertEqual(self.resolve()[0], 0)

    def test_the_test_clock_switch_moves_now_forward_and_is_refused_against_a_real_jira(self):
        self.interrupted("before-send")
        self.assertEqual(self.resolve(pretend_seconds_later=91)[0], 1)
        code, text = self.resolve(pretend_seconds_later=122)
        self.assertEqual(code, 0)
        self.assertIn("TEST CLOCK", text)
        self.assertEqual(self.record()["status"], "released")
        self.tearDown()
        self.setUp()
        self.interrupted("before-send")
        before = self.record_bytes()
        code, text = self.resolve(pretend_seconds_later=500, source="live")
        self.assertEqual(code, 1)
        self.assertIn("for the fake Jira only", text)
        self.assertEqual(self.record_bytes(), before)

    def test_a_clock_that_has_gone_backwards_is_refused(self):
        self.interrupted("before-send")
        self.later(100)
        self.resolve()
        self.later(-50)
        code, text = self.resolve()
        self.assertEqual(code, 1)
        self.assertIn("clock is earlier than a time in the draft's record", text)

    def test_an_empty_answer_from_an_identity_that_can_no_longer_see_the_project_is_not_counted(self):
        self.interrupted("after-send")
        self.fake.state["hidden"] = ["20001"]
        before = self.record_bytes()
        for _ in range(3):
            self.later(100)
            code, text = self.resolve()
            self.assertEqual(code, 2)
            self.assertIn("an empty answer cannot be believed", text)
        self.assertEqual(self.record_bytes(), before)
        self.fake.state["hidden"] = []
        self.assertIn("FOUND BY ITS KEY", self.resolve()[1])

    def test_a_task_that_shows_up_after_the_record_was_released_is_still_not_created_twice(self):
        self.interrupted("after-send")
        self.fake.search_lag = 2
        self.assertEqual(self.release()[1][0], 0)
        self.assertEqual(self.record()["status"], "released")
        code, text, fingerprint = self.preview()            # the search has caught up by now
        self.assertIsNone(fingerprint)
        self.assertIn("An issue already carries this draft's key: SAND-3", text)
        self.assertIn("Run `resolve`", text)
        code, text = self.resolve()
        self.assertIn("FOUND BY ITS KEY", text)
        self.assertEqual((self.record()["status"], self.posts(), len(self.keyed())), ("linked", 1, 1))

    def test_a_task_that_shows_up_between_the_preview_and_the_confirmation_stops_the_write(self):
        self.interrupted("after-send")
        self.fake.search_lag = 4                             # two for resolve, two for the preview
        self.release()
        _, _, fingerprint = self.preview()
        self.assertTrue(fingerprint)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("an issue now carries this draft's key", text)
        self.assertEqual((self.posts(), len(self.keyed())), (1, 1))


class WhenTheSearchItselfFails(Case):
    """The hint: searching can fail too. When it cannot tell, it stops and asks."""

    def test_resolve_stops_creates_nothing_and_leaves_the_record_as_it_was(self):
        for failure in (500, 401, "timeout", "garbled", "partial"):
            self.tearDown()
            self.setUp()
            self.interrupted("after-send")
            before = self.record_bytes()
            self.fake.fail_search = failure
            code, text = self.resolve()
            self.assertEqual(code, 2, failure)
            self.assertIn("THE SEARCH FOR THE KEY FAILED", text)
            self.assertIn("NOT KNOWN", text)
            self.assertIn('labels = "%s"' % self.record()["key"], text)
            self.assertEqual(self.record_bytes(), before)
            self.assertEqual(self.posts(), 1)

    def test_a_failed_search_does_not_count_as_an_empty_one(self):
        self.interrupted("before-send")
        self.fake.fail_search = 500
        self.resolve()
        self.later(61)
        self.fake.fail_search = "timeout"
        self.resolve()
        self.assertEqual((self.record()["status"], self.record()["not_found"]), ("sending", []))

    def test_a_preview_is_not_issued_when_the_search_fails(self):
        for failure in (500, "timeout", "garbled", "partial"):
            self.tearDown()
            self.setUp()
            self.fake.fail_search = failure
            code, text, fingerprint = self.preview()
            self.assertEqual(code, 1)
            self.assertIn("THE SEARCH FOR THE KEY FAILED", text)
            self.assertIsNone(fingerprint)

    def test_nothing_is_sent_when_the_search_just_before_the_write_fails(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_search = "timeout"
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("THE SEARCH FOR THE KEY FAILED just before the write", text)
        self.assertEqual((self.posts(), self.record()["status"], self.record()["attempts"]), (0, "new", []))

    def test_an_empty_answer_needs_both_the_permission_and_something_found_in_the_project(self):
        def stub(may_see, issues):
            def get(path, params=None):
                if path == "/rest/api/3/mypermissions":
                    return 200, {}, {"permissions": {"BROWSE_PROJECTS": {"havePermission": may_see}}}
                return 200, {}, {"issues": issues}
            return co.Connection(get, None, HOST)

        co.can_be_seen(stub(True, [{"id": "1"}]), "20001")
        for may_see, issues in ((False, [{"id": "1"}]), (True, []), (None, [{"id": "1"}])):
            with self.assertRaises(co.SearchFailed):
                co.can_be_seen(stub(may_see, issues), "20001")

    def test_a_search_answer_with_as_many_results_as_were_asked_for_is_not_trusted(self):
        conn = co.Connection(lambda path, params=None: (200, {}, {"issues": [{"id": str(n), "fields": {}} for n in range(1, 51)]}), None, HOST)
        with self.assertRaises(co.SearchFailed):
            co.search(conn, 'labels = "x"', "labels")

    def test_a_search_answer_holding_an_issue_without_the_key_is_not_trusted(self):
        answer = {"issues": [{"id": "5", "key": "SAND-5", "fields": {"labels": ["something-else"], "project": {"id": "20001"}}}]}
        conn = co.Connection(lambda path, params=None: (200, {}, answer), None, HOST)
        with self.assertRaises(co.SearchFailed):
            co.find_by_key(conn, "gtq-key-" + "a" * 16)


class WhenMoreThanOneIsFound(Case):
    def test_two_issues_with_the_key_are_reported_and_neither_is_recorded(self):
        self.interrupted("after-send")
        self.fake.other_issue("SAND", "a copy made some other way", [self.record()["key"]])
        before = self.record_bytes()
        code, text = self.resolve()
        self.assertEqual(code, 2)
        self.assertIn("MORE THAN ONE ISSUE CARRIES THE KEY: SAND-3 (issue id 30004), SAND-4 (issue id 30005)", text)
        self.assertEqual(self.record_bytes(), before)

    def test_an_issue_with_the_key_in_another_project_is_not_recorded(self):
        self.interrupted("before-send")
        self.fake.other_issue("PROD", "moved or copied", [self.record()["key"]])
        code, text = self.resolve()
        self.assertEqual(code, 2)
        self.assertIn("not project id 20001 where the request was sent", text)
        self.assertEqual(self.record()["status"], "sending")

    def test_an_issue_with_the_key_when_nothing_was_ever_sent_is_not_recorded(self):
        self.preview()
        self.fake.other_issue("SAND", "label added by hand", [self.record()["key"]])
        code, text = self.resolve()
        self.assertEqual(code, 2)
        self.assertIn("nothing was ever sent", text)
        self.assertEqual(self.record()["status"], "new")


class OneRunAtATime(Case):
    """Two confirmations at the same moment must not both send."""

    def claim(self):
        return os.path.join(self.state, "claims", "export-archive")

    def test_while_one_run_is_confirming_another_is_refused_and_the_claim_is_given_up_afterwards(self):
        _, _, fingerprint = self.preview()
        seen = []
        real_get = self.fake.get

        def get(path, params=None):
            try:
                co.claim_draft(self.state, "export-archive")
                seen.append("a second run got in")
            except co.Refused as refusal:
                seen.append(str(refusal))
            return real_get(path, params)

        self.fake.get = get
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertTrue(seen and all("another run is confirming this draft" in said for said in seen), seen[:1])
        self.assertFalse(os.path.exists(self.claim()))
        self.assertEqual(self.posts(), 1)

    def test_a_claim_held_by_another_run_stops_the_confirmation_before_anything_is_asked_of_jira(self):
        _, _, fingerprint = self.preview()
        co.claim_draft(self.state, "export-archive")
        asked = len(self.fake.requests)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("another run is confirming this draft", text)
        self.assertEqual((len(self.fake.requests), self.posts()), (asked, 0))
        self.assertTrue(os.path.exists(self.claim()))            # the other run's claim is not taken away

    def test_a_claim_left_by_a_killed_run_can_be_taken_over_after_ten_minutes_and_not_before(self):
        _, _, fingerprint = self.preview()
        co.claim_draft(self.state, "export-archive")
        self.later(10 * 60)
        self.assertEqual(self.confirm(fingerprint)[0], 1)
        self.later(1)
        _, _, fingerprint = self.preview()
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertEqual(self.posts(), 1)

    def test_a_refused_confirmation_gives_up_its_claim(self):
        self.preview()
        self.confirm("0123456789ab")
        self.assertFalse(os.path.exists(self.claim()))

    def test_the_record_is_read_after_the_claim_is_taken(self):
        """A run that waited for an abandoned claim must see what the run before it did."""
        _, _, fingerprint = self.preview()
        real_claim = co.claim_draft

        def claim_then_another_run_finishes(state, name):
            path = real_claim(state, name)
            record = self.record()
            record["status"] = "sending"
            record["attempts"].append({"sent_at": co.stamp(self.clock), "outcome": "sent by another run"})
            co.save_json(os.path.join(self.state, "intents", "export-archive.json"), record)
            return path

        co.claim_draft = claim_then_another_run_finishes
        try:
            code, text = self.confirm(fingerprint)
        finally:
            co.claim_draft = real_claim
        self.assertEqual(code, 1)
        self.assertIn("ITS OUTCOME IS NOT KNOWN", text)
        self.assertEqual(self.posts(), 0)


class Refusals(Case):
    """Criteria 6 and 7. Each ends with nothing written."""

    def refused(self, result, words):
        code, text = result
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED", text)
        self.assertIn(words, text)
        self.assertIn("Nothing has been written.", text)
        self.assertEqual((self.posts(), len(self.fake.state["issues"])), (0, 3))

    def test_a_missing_confirmation(self):
        self.preview()
        self.refused(self.confirm(None), "no confirmation was given")
        self.refused(self.confirm(""), "no confirmation was given")
        _, _, fingerprint = self.preview(draft=self.write_draft("other", "SAND", "Another made-up task"))
        self.refused(self.confirm(fingerprint, confirmed_by=" ", draft=os.path.join(self.folder, "other.json")), "gives the name of the person confirming")

    def test_a_change_that_differs_from_the_preview(self):
        _, _, fingerprint = self.preview()
        self.write_draft("export-archive", "SAND", TITLE + " and delete the originals")
        self.refused(self.confirm(fingerprint), "the title is not the title the preview showed")

    def test_a_draft_rewritten_with_the_same_words_is_still_not_the_file_previewed(self):
        _, _, fingerprint = self.preview()
        with open(self.draft, "a", encoding="utf-8") as f:
            f.write("\n")
        self.refused(self.confirm(fingerprint), "the draft is not the file the preview showed")

    def test_a_preview_older_than_the_limit(self):
        _, _, fingerprint = self.preview()
        self.later(15 * 60 + 1)
        self.refused(self.confirm(fingerprint), "this preview is too old")

    def test_a_preview_exactly_at_the_limit_is_accepted_and_the_test_clock_switch_works(self):
        _, _, fingerprint = self.preview()
        self.refused(self.confirm(fingerprint, pretend_minutes_later=16), "this preview is too old")
        self.later(15 * 60)
        self.assertEqual(self.confirm(fingerprint)[0], 0)

    def test_a_project_that_is_not_on_the_allowlist(self):
        draft = self.write_draft("to-production", "PROD", "A made-up task for production")
        code, text, fingerprint = self.preview(draft=draft)
        self.assertIsNone(fingerprint)
        self.refused((code, text), "PROD (project id 20002) on the Jira site with fingerprint %s is not on the sandbox allowlist" % co.site_fingerprint(HOST))

    def test_the_same_project_id_on_another_site_is_not_on_the_allowlist(self):
        self.write_allowlist([("20001", "another-site.example.invalid")])
        self.refused(self.preview()[:2], "is not on the sandbox allowlist")

    def test_an_allowlist_changed_after_the_preview(self):
        _, _, fingerprint = self.preview()
        self.write_allowlist([("20001", HOST), ("20002", HOST)])
        self.refused(self.confirm(fingerprint), "the allowlist file is not the one the preview used")
        self.write_allowlist([])
        self.refused(self.confirm(fingerprint), "is not on the sandbox allowlist")

    def test_a_project_where_jira_says_this_identity_may_not_create(self):
        self.write_allowlist([("20003", HOST)])
        self.refused(self.preview(draft=self.write_draft("read-only", "RO", "A made-up task"))[:2], "may not create issues in this project")

    def test_permission_withdrawn_after_the_preview(self):
        _, _, fingerprint = self.preview()
        self.fake.state["may_create"]["20001"] = False
        self.refused(self.confirm(fingerprint), "may not create issues in this project")

    def test_a_saved_preview_that_was_altered(self):
        _, _, fingerprint = self.preview()
        path = os.path.join(self.state, "previews", fingerprint + ".json")
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        saved["proposal"]["summary"] = "something else"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(saved, f)
        self.refused(self.confirm(fingerprint), "has been altered since it was made")

    def test_a_fingerprint_that_names_no_preview_or_is_not_a_fingerprint(self):
        self.preview()
        self.refused(self.confirm("0123456789ab"), "there is no preview with the fingerprint")
        self.refused(self.confirm("../../x"), "a fingerprint is 12 characters")

    def test_a_preview_made_against_another_site(self):
        _, _, fingerprint = self.preview()
        self.write_allowlist([("20001", HOST), ("20001", "another-site.example.invalid")])
        self.refused(self.confirm(fingerprint, host="another-site.example.invalid"), "not the Jira site the preview was made against")

    def test_a_title_that_looks_like_it_holds_a_secret(self):
        draft = self.write_draft("leaky", "SAND", "Rotate it: pass" + "word=" + "example-not-real-1")
        self.refused(self.preview(draft=draft)[:2], "looks as if it holds")

    def test_another_draft_with_the_same_file_name_in_another_folder_does_not_share_the_record(self):
        self.preview()
        os.makedirs(os.path.join(self.folder, "elsewhere"))
        other = os.path.join(self.folder, "elsewhere", "export-archive.json")
        with open(other, "w", encoding="utf-8") as f:
            json.dump({"project": "SAND", "summary": "Quite another task"}, f)
        self.refused(self.preview(draft=other)[:2], "belongs to a draft file in another folder")

    def test_jiras_own_words_about_a_refusal_are_shown_and_not_saved(self):
        _, _, fingerprint = self.preview()
        self.fake.before_post = lambda fake: fake.state["may_create"].__setitem__("20001", False)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("no permission to create issues in this project", text)
        self.assertNotIn("no permission to create issues in this project", self.saved)
        self.assertIn("were shown on screen and are not saved", self.saved)
        self.assertEqual(self.record()["status"], "new")

    def test_a_draft_that_was_never_previewed_cannot_be_confirmed_or_resolved(self):
        self.refused(self.confirm("0123456789ab"), "it has never been previewed")
        self.refused(self.resolve(), "it has never been previewed")

    def test_a_record_that_cannot_be_read_stops_everything(self):
        self.preview()
        with open(os.path.join(self.state, "intents", "export-archive.json"), "w", encoding="utf-8") as f:
            f.write("{")
        self.refused(self.preview()[:2], "cannot be read")
        self.refused(self.resolve(), "cannot be read")


class PreviewsAreUsedOnce(Case):
    def test_a_preview_from_before_an_interrupted_attempt_cannot_be_confirmed_after_it(self):
        _, _, first = self.preview()
        self.later(2)
        _, _, second = self.preview()
        self.assertNotEqual(first, second)
        self.assertEqual(self.confirm(first, interrupt_at="before-send")[0], 3)
        self.release()
        self.assertEqual(self.record()["status"], "released")
        code, text = self.confirm(second)
        self.assertEqual(code, 1)
        self.assertIn("is not for this draft as its record now stands", text)
        self.assertEqual(self.posts(), 0)


class TheTitleCheck(Case):
    """The backstop for a lost record: it points, and does not refuse."""

    def test_an_issue_with_the_same_title_and_no_key_is_pointed_out(self):
        self.fake.other_issue("SAND", "  archive THE october export   files ")
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 0)
        self.assertTrue(fingerprint)
        self.assertIn("with this title, capitals and spacing aside: 1 (SAND-3 (issue id 30004))", text)
        self.assertIn("LOOK AT IT BEFORE CONFIRMING", text)

    def test_one_that_appears_after_the_preview_stops_the_confirmation(self):
        _, _, fingerprint = self.preview()
        self.fake.other_issue("SAND", TITLE)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("the issues in the project with this title are not the ones the preview showed", text)
        self.assertEqual(self.posts(), 0)

    def test_a_title_with_the_same_words_in_a_longer_title_is_not_the_same_title(self):
        self.fake.other_issue("SAND", TITLE + " and the September ones")
        _, text, _ = self.preview()
        self.assertIn("with this title, capitals and spacing aside: 0.", text)


class AfterAManualEdit(Case):
    """The second stretch goal."""

    def created(self):
        _, _, fingerprint = self.preview()
        self.confirm(fingerprint)

    def test_the_key_survives_an_edit_of_the_title(self):
        self.created()
        self.fake.edit("SAND-3", summary="Archive the export files (retitled by hand)", add_label="team-label")
        code, text = self.run_command("check")
        self.assertEqual(code, 0, text)
        self.assertIn("it carries the label %s: yes" % self.record()["key"], text)
        self.assertIn("It has been changed in Jira since", text)
        self.assertIn("this one, and no other", text)
        self.assertIn("AS RECORDED", text)
        _, text, fingerprint = self.preview()
        self.assertIn("NOTHING TO CREATE", text)
        self.assertIsNone(fingerprint)
        self.assertEqual(self.posts(), 1)

    def test_an_interrupted_creation_is_still_found_after_its_title_was_edited(self):
        self.interrupted("after-send")
        self.fake.edit("SAND-3", summary="Retitled by hand before anyone resolved it")
        code, text = self.resolve()
        self.assertIn("FOUND BY ITS KEY: SAND-3", text)
        self.assertEqual(self.record()["status"], "linked")

    def test_a_label_removed_by_hand_is_said_plainly_and_nothing_is_created(self):
        self.created()
        self.fake.edit("SAND-3", remove_label=self.record()["key"])
        code, text = self.run_command("check")
        self.assertEqual(code, 1)
        self.assertIn("NO. The label has been removed", text)
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 1)                             # nothing to create, and not as recorded
        self.assertIsNone(fingerprint)
        self.assertEqual(self.posts(), 1)

    def test_a_label_removed_before_anyone_resolved_means_not_found_and_that_is_the_stated_limit(self):
        self.interrupted("after-send")
        self.fake.edit("SAND-3", remove_label=self.record()["key"])
        _, (code, text) = self.release()
        self.assertEqual(self.record()["status"], "released")
        self.assertIn("THAT IS NOT PROOF", text)
        _, text, fingerprint = self.preview()                # the title check is what points the earlier one out
        self.assertIn("LOOK AT IT BEFORE CONFIRMING", text)

    def test_a_recorded_task_that_jira_no_longer_returns_is_not_created_again(self):
        self.created()
        self.fake.state["issues"].pop("30004")
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 1)
        self.assertIn("NOTHING IS CREATED IN ITS PLACE", text)
        self.assertIsNone(fingerprint)
        self.assertEqual(self.posts(), 1)

    def test_check_does_not_say_found_by_its_key_when_the_search_did_not_find_it(self):
        self.created()
        for knob, value in (("search_lag", 1), ("fail_search", 500)):
            setattr(self.fake, knob, value)
            code, text = self.run_command("check")
            self.assertEqual(code, 1, knob)
            self.assertNotIn("AS RECORDED", text)
            self.assertIn("IT WAS NOT FOUND BY ITS KEY in this run", text)
        self.assertEqual(self.run_command("check")[0], 0)

    def test_a_search_that_is_behind_just_after_the_write_does_not_fail_the_write(self):
        _, _, fingerprint = self.preview()
        self.fake.before_post = lambda fake: setattr(fake, "search_lag", 1)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("returns 0 issues", text)
        self.assertIn("Run `check` later", text)
        self.assertEqual(self.record()["status"], "linked")

    def test_two_issues_with_the_key_after_the_write_need_a_person(self):
        _, _, fingerprint = self.preview()
        key = self.record()["key"]
        self.fake.before_post = lambda fake: fake.other_issue("SAND", "made by another run at the same moment", [key])
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("NOT THIS ONE ALONE", text)

    def test_check_needs_a_recorded_task(self):
        self.preview()
        code, text = self.run_command("check")
        self.assertEqual(code, 1)
        self.assertIn("no recorded task to check", text)


class TheCommandLine(Case):
    """main(): the fake kept in the state folder, the saved log, and the live connection's guard."""

    def main(self, *args):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = co.main(list(args))
        return code, out.getvalue()

    def test_a_whole_run_through_main_with_a_saved_log(self):
        common = ["--source", "fake", "--draft", self.draft, "--state", self.state]
        log = os.path.join(self.folder, "logs", "preview.txt")
        code, text = self.main("preview", *common, "--allowlist", self.allowlist, "--log", log)
        fingerprint = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text).group(1)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertIn(HOST, text)
        self.assertNotIn(HOST, saved)
        self.assertIn(co.SITE_MARK, saved)
        code, text = self.main("confirm", *common, "--allowlist", self.allowlist, "--fingerprint", fingerprint, "--confirmed-by", PERSON, "--interrupt-at", "after-send")
        self.assertEqual(code, 3)
        code, text = self.main("resolve", *common)
        self.assertEqual(code, 0)
        self.assertIn("FOUND BY ITS KEY", text)
        code, text = self.main("check", *common)
        self.assertEqual(code, 0)

    def test_only_confirm_is_given_a_way_to_write(self):
        made = []
        real = co.Connection

        class Watched(real):
            def __init__(self, get, post, host):
                made.append(post is not None)
                real.__init__(self, get, post, host)

        co.Connection = Watched
        try:
            common = ["--source", "fake", "--draft", self.draft, "--state", self.state]
            self.main("preview", *common, "--allowlist", self.allowlist)
            self.main("resolve", *common)
            self.main("check", *common)
            self.main("confirm", *common, "--allowlist", self.allowlist, "--fingerprint", "0123456789ab", "--confirmed-by", PERSON)
        finally:
            co.Connection = real
        self.assertEqual(made, [False, False, False, True])

    def test_the_live_connection_sends_no_write_but_one_new_task_with_the_key(self):
        """A stand-in for the network is given, so that nothing is sent anywhere, and so that what WOULD be sent is seen."""
        sent = []

        class Opener:
            def open(self, request, timeout=None):
                sent.append((request.get_method(), request.full_url))
                raise OSError("the stand-in sends nothing")

        names = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        before = {name: os.environ.get(name) for name in names}
        os.environ.update(dict(zip(names, ("https://" + HOST, "tester@example.invalid", "made-up-value"))))
        try:
            conn, hidden = co.make_live(True, Opener())
            key = "gtq-key-" + "a" * 16
            good = {"project": {"id": "1"}, "issuetype": {"id": "2"}, "summary": "x", "labels": [key]}
            for path, body in (("/rest/api/3/issue/30001", {"fields": good}), (co.WRITE_PATH, {"fields": dict(good, description="x")}),
                               (co.WRITE_PATH, {"fields": dict(good, labels=[key, "other"])}), (co.WRITE_PATH, {"fields": dict(good, labels=["other"])}),
                               (co.WRITE_PATH, {"fields": good, "update": {}}), (co.WRITE_PATH, {"fields": {k: v for k, v in good.items() if k != "labels"}})):
                with self.assertRaises(co.Refused):
                    conn._post(path, None, body)
            self.assertEqual(sent, [])
            with self.assertRaises(OSError):
                conn._post(co.WRITE_PATH, None, {"fields": good})
            self.assertEqual(sent, [("POST", "https://%s%s" % (HOST, co.WRITE_PATH))])
            self.assertIsNone(co.make_live(False, Opener())[0]._post)
            self.assertEqual(len(hidden), 3)
        finally:
            for name, value in before.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ.update({name: value})

    def test_against_a_real_jira_too_only_confirm_is_given_a_way_to_write(self):
        asked = []
        real = co.make_live

        def watched(may_write, opener=None):
            asked.append(may_write)
            return co.Connection(self.fake.get, self.fake.post if may_write else None, HOST), []

        co.make_live = watched
        try:
            common = ["--source", "live", "--draft", self.draft, "--state", self.state]
            self.main("preview", *common, "--allowlist", self.allowlist)
            self.main("resolve", *common)
            self.main("check", *common)
        finally:
            co.make_live = real
        self.assertEqual(asked, [False, False, False])

    def test_a_real_write_needs_a_terminal(self):
        class Stream:
            def __init__(self, answer):
                self.answer = answer

            def isatty(self):
                return self.answer

        self.assertTrue(co.person_present(Stream(True)))
        self.assertFalse(co.person_present(Stream(False)))
        self.assertFalse(co.person_present(None))
        names = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        before = {name: os.environ.get(name) for name in names}
        os.environ.update(dict(zip(names, ("https://" + HOST, "tester@example.invalid", "made-up-value"))))
        real_stdin, sys.stdin = sys.stdin, Stream(False)
        try:
            code, text = self.main("confirm", "--source", "live", "--draft", self.draft, "--state", self.state, "--allowlist", self.allowlist,
                                   "--fingerprint", "0123456789ab", "--confirmed-by", PERSON)
        finally:
            sys.stdin = real_stdin
            for name, value in before.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ.update({name: value})
        self.assertEqual(code, 1)
        self.assertIn("confirmed by a person at a terminal", text)

    def test_a_site_address_that_is_not_plain_https_is_refused(self):
        names = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        before = {name: os.environ.get(name) for name in names}
        try:
            for base in ("http://" + HOST, "https://%s:8443" % HOST, "https://%s/path" % HOST, "https://user@" + HOST):
                os.environ.update(dict(zip(names, (base, "tester@example.invalid", "made-up-value"))))
                with self.assertRaises(co.Refused):
                    co.make_live(False)
        finally:
            for name, value in before.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ.update({name: value})


if __name__ == "__main__":
    unittest.main()

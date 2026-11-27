"""Tests for sync.py and rank.py, against the fake Jira. No network. Every item, site and person here is made up."""
import argparse
import contextlib
import datetime
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import fake_jira   # noqa: E402
import rank        # noqa: E402
import sync        # noqa: E402

HOST = "fixture-site.example.invalid"
T0 = "2026-11-20T09:00:00Z"
FIELDS = ("priority", "duedate", "issuelinks", "created", "key", "status", "assignee", "issuetype", "copied_at")


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-next-test-")
        self.records = os.path.join(self.folder, "records.json")
        self.fake = fake_jira.FakeJira()
        self.params = []
        real_get = self.fake.get
        self.fake.get = lambda path, params=None: (self.params.append((path, dict(params or {}))), real_get(path, params))[1]

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def copy(self, at=T0, refresh=None, project="DEMO", out=None):
        del sync.LINES[:]
        conn = sync.Connection(self.fake.get, HOST)
        args = argparse.Namespace(project=project, out=out or self.records, refresh=refresh, pretend_now=at)
        fixed = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ")
        try:
            code = sync.cmd_copy(args, conn, lambda: fixed)
        except sync.Refused as refusal:
            return 1, "REFUSED: %s" % refusal
        return code, "\n".join(sync.LINES)

    def data(self):
        with open(self.records, encoding="utf-8") as f:
            return json.load(f)

    def item(self, key):
        return [i for i in self.data()["items"] if i["key"] == key][0]

    def edit(self, change):
        """Change the records file by hand, as a test of the ranking alone."""
        data = self.data()
        change(data, {i["key"]: i for i in data["items"]})
        with open(self.records, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def ranking(self, now="2026-11-20T10:00:00Z", rule="priority-first"):
        return rank.Ranking(rank.load(self.records), rank.parse_now(now), rule)

    def text(self, now="2026-11-20T10:00:00Z", rule="priority-first", also=None):
        return rank.write_recommendation(self.ranking(now, rule), also)

    def main(self, module, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(list(args))
        return code, out.getvalue()


class TheCopyOnlyReads(Case):
    """Criterion 7: the recommendation changes nothing in Jira."""

    def test_every_request_is_a_get_and_the_connection_has_no_way_to_send_anything_else(self):
        before = json.dumps(self.fake.state, sort_keys=True)
        code, text = self.copy()
        self.assertEqual(code, 0, text)
        self.assertEqual(json.dumps(self.fake.state, sort_keys=True), before)
        self.assertIn("Every one was a GET with no body", text)
        self.assertFalse([name for name in dir(sync.Connection) if name.startswith(("post", "put", "delete", "patch", "send"))])
        self.assertFalse(hasattr(self.fake, "post"))
        with open(os.path.join(SKILL, "sync.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(re.findall(r'method="([A-Z]+)"', source), ["GET"])
        self.assertNotIn("data=", source)

    def test_the_live_connection_sends_get_with_no_body(self):
        sent = []

        class Opener:
            def open(self, request, timeout=None):
                sent.append((request.get_method(), request.full_url, request.data))
                raise OSError("the stand-in sends nothing")

        names = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        before = {name: os.environ.get(name) for name in names}
        os.environ.update(dict(zip(names, ("https://" + HOST, "tester@example.invalid", "made-up-value"))))
        try:
            conn, hidden = sync.make_live(Opener())
            with self.assertRaises(sync.Refused):
                conn.get("/rest/api/3/myself", {"a": "b"})
            self.assertEqual(sent, [("GET", "https://%s/rest/api/3/myself?a=b" % HOST, None)])
            self.assertEqual(len(hidden), 3)

            class Answer:
                status, headers = 200, {}

                def read(self):
                    return b'{"accountId": "x"}'

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            class Answering:
                def open(self, request, timeout=None):
                    sent.append((request.get_method(), request.full_url, request.data))
                    return Answer()

            conn, _ = sync.make_live(Answering())
            self.assertEqual(conn.get("/rest/api/3/myself")[:1], (200,))
            self.assertEqual(conn.sent, [("GET", "/rest/api/3/myself", False)])       # read back from the request as it was built
            self.assertTrue(conn.only_read())
            conn.sent.append(("GET", "/x", True))                  # a GET that carried a body is not a plain read
            self.assertFalse(conn.only_read())
            conn.sent[-1] = ("POST", "/x", False)
            self.assertFalse(conn.only_read())

            real_request = sync.urllib.request.Request

            class Altered(real_request):                             # stands for a request that was not built as a GET
                def get_method(self):
                    return "PATCH"

            sync.urllib.request.Request = Altered
            try:
                conn, _ = sync.make_live(Answering())
                conn.get("/rest/api/3/myself")
            finally:
                sync.urllib.request.Request = real_request
            self.assertEqual(conn.sent, [("PATCH", "/rest/api/3/myself", False)])      # what is reported is what the request was
            self.assertFalse(conn.only_read())
            for base in ("http://" + HOST, "https://%s:8443" % HOST, "https://%s/path" % HOST):
                os.environ.update({"JIRA_BASE_URL": base})
                with self.assertRaises(sync.Refused):
                    sync.make_live(Opener())
        finally:
            for name, value in before.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ.update({name: value})

    def test_the_snapshots_before_and_after_are_the_same_when_nobody_changed_anything(self):
        _, text = self.copy()
        codes = re.findall(r"Snapshot of Jira (?:before|after) the copy:\s+([0-9a-f]{16}) \(13 items\)", text)
        self.assertEqual(len(codes), 2)
        self.assertEqual(codes[0], codes[1])
        self.assertIn("The two are the same", text)

    def test_a_change_by_someone_else_during_the_copy_is_noticed(self):
        real_get, calls = self.fake.get, [0]

        def get(path, params=None):
            if path == sync.SEARCH_PATH:
                calls[0] += 1
                if calls[0] == 3:                    # between the copy and the second snapshot
                    self.fake.resolve("DEMO-3")
            return real_get(path, params)

        self.fake.get = get
        code, text = self.copy()
        self.assertEqual(code, 0)
        self.assertIn("THE TWO DIFFER", text)

    def test_ranking_leaves_the_records_file_as_it_was_and_refuses_to_write_over_it(self):
        self.copy()
        before = rank.file_sha(self.records)
        out = os.path.join(self.folder, "recommendation.md")
        code, _ = self.main(rank, "rank", "--records", self.records, "--now", "2026-11-20T10:00:00Z", "--out", out)
        self.assertEqual((code, rank.file_sha(self.records)), (0, before))
        code, text = self.main(rank, "rank", "--records", self.records, "--now", "2026-11-20T10:00:00Z", "--out", self.records)
        self.assertEqual(code, 2)
        self.assertIn("never written over", text)
        self.assertEqual(rank.file_sha(self.records), before)

    def test_the_ranking_file_has_no_network_code_and_never_reads_a_clock(self):
        with open(os.path.join(SKILL, "rank.py"), encoding="utf-8") as f:
            source = f.read()
        for word in ("urllib", "http.client", "socket", "requests", "subprocess", "datetime.now", ".now()", "utcnow", "time.time(", "import time", "today()", "os.environ"):
            self.assertNotIn(word, source, word)


class WhatIsCopied(Case):
    def test_no_title_no_person_and_no_account_id_reaches_the_records_or_the_output(self):
        code, text = self.copy()
        with open(self.records, encoding="utf-8") as f:
            saved = f.read()
        for secret in (fake_jira.HOSTILE_SUMMARY, "A made-up task", fake_jira.ME, fake_jira.OTHER, "A made-up person", "tester@example.invalid", "displayName", "summary"):
            self.assertNotIn(secret, saved)
            self.assertNotIn(secret, text)
        asked = [params["fields"] for path, params in self.params if path == sync.SEARCH_PATH]
        self.assertTrue(asked and all("summary" not in fields and "description" not in fields and "comment" not in fields for fields in asked))

    def test_who_has_an_item_is_kept_as_one_of_three_words(self):
        self.copy()
        self.assertEqual([self.item(k)["assignee"] for k in ("DEMO-3", "DEMO-9", "DEMO-1")], ["someone else", "me", "nobody"])

    def test_a_link_is_kept_with_its_phrase_and_which_end_this_item_is(self):
        self.copy()
        blocked, blocker = self.item("DEMO-5")["links"][0], self.item("DEMO-3")["links"][0]
        self.assertEqual((blocked["type"], blocked["says"], blocked["this_item_is"], blocked["other"], blocked["other_status"]["category"]),
                         ("Blocks", "is blocked by", "target", "DEMO-3", "indeterminate"))
        self.assertEqual((blocker["says"], blocker["this_item_is"], blocker["other"]), ("blocks", "source", "DEMO-5"))
        self.assertEqual(self.item("DEMO-2")["links"][0]["says"], "relates to")

    def test_the_sites_priorities_are_kept_in_jiras_order(self):
        self.copy()
        self.assertEqual(self.data()["priorities"], ["Highest", "High", "Medium", "Low", "Lowest"])

    def test_every_page_of_a_long_answer_is_read(self):
        self.fake.page_size = 5
        code, text = self.copy()
        self.assertEqual((code, len(self.data()["items"])), (0, 13))

    def test_a_copy_that_would_not_be_whole_is_refused(self):
        real_get = self.fake.get

        def short(path, params=None):
            status, headers, body = real_get(path, params)
            if path == sync.SEARCH_PATH and "status" in (params or {}).get("fields", ""):
                body["issues"] = body["issues"][:-1]
            return status, headers, body

        self.fake.get = short
        code, text = self.copy()
        self.assertEqual(code, 1)
        self.assertIn("the copy is not whole", text)
        self.assertFalse(os.path.exists(self.records))

    def test_an_answer_that_says_there_is_more_and_gives_no_way_to_ask_is_refused(self):
        real_get = self.fake.get

        def cut(path, params=None):
            status, headers, body = real_get(path, params)
            if path == sync.SEARCH_PATH:
                body.pop("nextPageToken", None)
                body["isLast"] = False
            return status, headers, body

        self.fake.get = cut
        self.assertEqual(self.copy()[0], 1)

    def test_answers_that_cannot_be_used_are_refused_and_nothing_is_written(self):
        for path, words in (("/rest/api/3/myself", "which account"), ("/rest/api/3/priority", "did not list its priorities"),
                            ("/rest/api/3/project/DEMO", "the project could not be used"), (sync.SEARCH_PATH, "answer to a search could not be used")):
            self.fake.fail = {path: 500}
            code, text = self.copy()
            self.assertEqual(code, 1, path)
            self.assertIn(words, text)
            self.assertFalse(os.path.exists(self.records))
        self.fake.fail = {"/rest/api/3/myself": 401}
        self.assertIn("rejected the credentials", self.copy()[1])

    def test_an_item_whose_status_or_links_cannot_be_read_stops_the_copy(self):
        for field, words in (("status", "usable status"), ("issuelinks", "did not list the links")):
            real_get = self.fake.get

            def broken(path, params=None, field=field, real_get=real_get):
                status, headers, body = real_get(path, params)
                if path == sync.SEARCH_PATH and body.get("issues") and field in body["issues"][0]["fields"]:
                    body["issues"][0]["fields"][field] = None
                return status, headers, body

            self.fake.get = broken
            code, text = self.copy()
            self.assertEqual(code, 1)
            self.assertIn(words, text)
            self.fake.get = real_get


class Refreshing(Case):
    def test_refresh_copies_the_named_items_again_and_keeps_the_rest_with_their_older_time(self):
        self.copy(T0)
        self.fake.resolve("DEMO-3")
        code, text = self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-3", "DEMO-5"])
        self.assertEqual(code, 0, text)
        self.assertEqual((self.item("DEMO-3")["copied_at"], self.item("DEMO-3")["status"]["category"]), ("2026-12-01T08:00:00Z", "done"))
        self.assertEqual(self.item("DEMO-5")["links"][0]["other_status"]["category"], "done")
        self.assertEqual(self.item("DEMO-1")["copied_at"], T0)
        self.assertEqual(len(self.data()["items"]), 13)
        self.assertIn("The other 11 items keep the copy they had, taken at: " + T0, text)

    def test_an_item_jira_no_longer_returns_is_taken_out_and_said(self):
        self.copy(T0)
        self.fake.state["issues"].pop("30012")
        code, text = self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-12"])
        self.assertIn("NO LONGER RETURNED BY JIRA, and taken out of the records: DEMO-12", text)
        self.assertEqual(len(self.data()["items"]), 12)

    def test_an_item_jira_now_returns_under_another_key_is_taken_out_and_said(self):
        self.copy(T0)
        self.fake.moved = {"DEMO-12": "DEMO-13"}              # a request for the old key is answered with another item
        code, text = self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-12"])
        self.assertEqual(code, 0, text)
        self.assertIn("MOVED: Jira now returns DEMO-12 as DEMO-13. It is taken out of the records.", text)
        self.assertEqual([i["key"] for i in self.data()["items"]].count("DEMO-13"), 1)
        self.assertNotIn("DEMO-12", [i["key"] for i in self.data()["items"]])

    def test_a_refresh_says_which_other_items_have_changed_in_jira_since_their_copy(self):
        self.copy(T0)
        self.fake.resolve("DEMO-3")
        self.fake.state["issues"]["30099"] = dict(self.fake.state["issues"]["30001"], id="30099", key="DEMO-99")
        code, text = self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-5"])
        self.assertIn("CHANGED IN JIRA SINCE THEIR COPY, and not copied again: DEMO-3", text)
        self.assertIn("IN JIRA WITH NO RECORD HERE: DEMO-99.", text)

    def test_times_are_kept_in_utc_and_names_the_site_chose_are_made_safe_for_a_markdown_file(self):
        self.fake.state["issues"]["30001"]["created"] = "2026-11-02T10:00:00.000+0300"
        self.copy()
        self.assertEqual(self.item("DEMO-1")["created"], "2026-11-02T07:00:00Z")
        self.assertEqual(sync.word("Done` | **x** <b>"), "Done? ? ??x?? ?b?")
        self.assertEqual(sync.word("In Progress (dev/test)"), "In Progress (dev/test)")
        self.assertIsNone(sync.word("   "))
        self.assertEqual(len(sync.word("x" * 100)), 40)

    def test_a_status_with_no_category_is_copied_as_open(self):
        fake_jira.STATUSES["todo"]["statusCategory"]["key"] = "undefined"
        try:
            self.assertEqual(self.copy()[0], 0)
            self.assertEqual(self.item("DEMO-1")["status"]["category"], "undefined")
            self.assertIn("DEMO-1", self.ranking().ranked)
        finally:
            fake_jira.STATUSES["todo"]["statusCategory"]["key"] = "new"

    def test_an_empty_page_that_says_there_is_more_is_refused_and_does_not_loop(self):
        real_get = self.fake.get
        self.fake.get = lambda path, params=None: (200, {}, {"issues": [], "nextPageToken": "5"}) if path == sync.SEARCH_PATH else real_get(path, params)
        code, text = self.copy()
        self.assertEqual(code, 1)
        self.assertIn("an empty page and said there was more", text)

    def test_refresh_is_refused_without_records_or_for_another_project_or_a_bad_key(self):
        self.assertIn("needs a records file", self.copy(refresh=["DEMO-1"])[1])
        self.copy(T0)
        before = rank.file_sha(self.records)
        for keys, words in ((["OTHER-1"], "is not in project DEMO"), (["DEMO-1", "DEMO-1"], "each once"), (["DEMO-1); DROP"], "each once")):
            code, text = self.copy(refresh=keys)
            self.assertEqual(code, 1)
            self.assertIn(words, text)
        self.assertEqual(rank.file_sha(self.records), before)

    def test_the_test_clock_is_refused_against_a_real_jira(self):
        code, text = self.main(sync, "copy", "--source", "live", "--project", "DEMO", "--out", self.records, "--pretend-now", T0)
        self.assertEqual(code, 1)
        self.assertIn("for the fake Jira only", text)

    def test_a_whole_run_through_main_with_a_saved_log(self):
        state, log = os.path.join(self.folder, "state"), os.path.join(self.folder, "logs", "copy.txt")
        code, text = self.main(sync, "copy", "--source", "fake", "--state", state, "--project", "DEMO", "--out", self.records, "--pretend-now", T0, "--log", log)
        self.assertEqual(code, 0, text)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertIn(HOST, text)
        self.assertNotIn(HOST, saved)
        self.assertIn(sync.SITE_MARK, saved)


class TheThreeLists(Case):
    """Criterion 2, and who is not offered."""

    def setUp(self):
        Case.setUp(self)
        self.copy()

    def test_every_item_is_in_exactly_one_list(self):
        r = self.ranking()
        self.assertEqual(r.ranked, ["DEMO-7", "DEMO-1", "DEMO-2", "DEMO-9", "DEMO-12", "DEMO-11", "DEMO-13", "DEMO-8"])
        self.assertEqual(sorted(r.blocked), ["DEMO-10", "DEMO-4", "DEMO-5"])
        self.assertEqual([key for key, _ in r.not_offered], ["DEMO-3", "DEMO-6"])
        self.assertEqual(len(r.ranked) + len(r.blocked) + len(r.not_offered), 13)

    def test_a_blocked_item_is_not_ranked_and_its_blocker_is_named_with_its_status(self):
        text = self.text()
        self.assertNotIn("DEMO-5", [line.split("`")[1] for line in text.split("\n") if line.startswith("| ") and "`" in line])
        self.assertIn("- BLOCKED BY `DEMO-3`: `issuelinks` says `DEMO-5` is blocked by it, in both records. Its `status` is `In Progress`, read from `DEMO-3`'s own record, "
                      "copied at `%s` and from what Jira showed of it inside `DEMO-5`'s record, copied at `%s`." % (T0, T0), text)

    def test_the_highest_priority_item_is_not_recommended_when_it_is_blocked(self):
        r = self.ranking()
        self.assertEqual(r.items["DEMO-5"]["priority"], "Highest")
        self.assertIn("DEMO-5", r.blocked)
        self.assertNotEqual(r.start_here(), "DEMO-5")

    def test_a_done_item_and_someone_elses_item_are_not_offered_and_the_field_is_named(self):
        text = self.text()
        self.assertIn("- `DEMO-6`: `status` is `Done`, which Jira puts in its \"done\" category.", text)
        self.assertIn("- `DEMO-3`: `assignee` is someone else.", text)

    def test_an_item_assigned_to_me_is_ranked(self):
        self.assertIn("DEMO-9", self.ranking().ranked)

    def done(self, status):
        status.update({"name": "Done", "category": "done"})

    def test_a_blocker_that_is_done_in_every_copy_no_longer_blocks_and_the_reason_says_so(self):
        def both(data, items):
            self.done(items["DEMO-3"]["status"])
            self.done(items["DEMO-5"]["links"][0]["other_status"])
        self.edit(both)
        r = self.ranking()
        self.assertIn("DEMO-5", r.ranked)
        self.assertEqual(r.confidence("DEMO-5"), "high")
        self.assertIn("- No longer blocked by `DEMO-3`: `issuelinks` says `DEMO-5` is blocked by it, in both records. Its `status` is `Done`", self.text())

    def test_when_the_two_copies_of_a_blockers_status_disagree_the_item_stays_blocked_whichever_says_done(self):
        for change in (lambda data, items: self.done(items["DEMO-3"]["status"]), lambda data, items: self.done(items["DEMO-5"]["links"][0]["other_status"])):
            self.copy()
            self.edit(change)
            r = self.ranking()
            self.assertIn("DEMO-5", r.blocked)
            self.assertEqual(r.confidence("DEMO-5"), "medium")
            text = self.text()
            self.assertIn("THE COPIES OF ITS STATUS DISAGREE", text)
            self.assertIn("It is treated as still blocking. Copy both items again", text)
            self.assertIn("- Confidence in the data: medium, because what is recorded about a blocker is in doubt.", text)

    def test_an_item_is_blocked_when_only_the_blockers_record_shows_the_link(self):
        """Found by a reader: the item's own copy was older than the link. Its blocker's fresher record showed it."""
        self.fake.block("DEMO-7", "DEMO-9")
        self.copy("2026-11-20T09:30:00Z", refresh=["DEMO-9"])           # DEMO-7 is not copied again
        r = self.ranking()
        self.assertIn("DEMO-7", r.blocked)
        self.assertNotIn("DEMO-7", r.ranked)
        self.assertEqual(r.waiters("DEMO-9"), ["DEMO-7", "DEMO-10"])
        self.assertIn("- BLOCKED BY `DEMO-9`: `issuelinks` in `DEMO-9`'s record says it blocks `DEMO-7`. `DEMO-7`'s own record, copied earlier, does not show the link.", self.text())
        self.assertEqual(r.confidence("DEMO-7"), "high")                # the newer record is the one that shows the link

    def test_a_link_that_only_the_older_record_shows_still_blocks_and_is_in_doubt(self):
        self.copy("2026-11-20T09:30:00Z", refresh=["DEMO-5"])
        self.edit(lambda data, items: items["DEMO-5"].update({"links": []}))       # DEMO-5's newer copy no longer shows the link
        r = self.ranking()
        self.assertIn("DEMO-5", r.blocked)
        self.assertEqual(r.confidence("DEMO-5"), "medium")
        self.assertIn("`DEMO-5`'s own record, copied LATER, does not show the link, so it may have been removed", self.text())

    def test_a_link_the_blockers_newer_record_no_longer_shows_still_blocks_and_is_in_doubt(self):
        self.copy("2026-11-20T09:30:00Z", refresh=["DEMO-3"])
        self.edit(lambda data, items: items["DEMO-3"].update({"links": []}))       # DEMO-3's newer copy no longer shows the link
        r = self.ranking()
        self.assertIn("DEMO-5", r.blocked)
        self.assertEqual(r.confidence("DEMO-5"), "medium")
        self.assertIn("`issuelinks` in `DEMO-5`'s own record says it is blocked by it. `DEMO-3`'s own record, copied LATER, does not show the link, so it may have been removed", self.text())

    def test_a_blocker_with_no_record_of_its_own_is_read_from_the_blocked_items_record(self):
        def change(data, items):
            data["items"] = [i for i in data["items"] if i["key"] != "DEMO-3"]
        self.edit(change)
        self.assertIn("DEMO-5", self.ranking().blocked)
        self.assertIn("Its `status` is `In Progress`, read from what Jira showed of it inside `DEMO-5`'s record, copied at `%s`." % T0, self.text())
        self.edit(lambda data, items: self.done(items["DEMO-5"]["links"][0]["other_status"]))
        self.assertIn("DEMO-5", self.ranking().ranked)

    def test_a_blocker_whose_status_is_recorded_nowhere_still_blocks_and_lowers_confidence(self):
        def change(data, items):
            data["items"] = [i for i in data["items"] if i["key"] != "DEMO-3"]
            [i for i in data["items"] if i["key"] == "DEMO-5"][0]["links"][0]["other_status"] = None
        self.edit(change)
        r = self.ranking()
        self.assertIn("DEMO-5", r.blocked)
        self.assertEqual(r.confidence("DEMO-5"), "medium")
        self.assertIn("Its status is recorded nowhere, so it is treated as still blocking", self.text())

    def test_a_site_with_no_link_type_named_blocks_gets_a_warning_and_not_an_empty_blocked_list_in_silence(self):
        self.fake.link_types = [dict(fake_jira.BLOCKS, name="Dependency"), fake_jira.RELATES]
        self.copy()
        r = self.ranking()
        self.assertEqual((r.blocks, r.blocked), (None, []))
        text = self.text()
        self.assertIn("**WARNING: NOTHING CAN BE SHOWN AS BLOCKED.** This site has no link type named `Blocks`. Its link types are: `Dependency`, `Relates`.", text)
        code, said = self.main(rank, "rank", "--records", self.records, "--now", "2026-11-20T10:00:00Z")
        self.assertIn("WARNING: the site has no link type named Blocks", said)

    def test_an_item_blocked_by_itself_or_two_that_block_each_other_do_not_loop(self):
        def knot(data, items):
            link = lambda end, other: {"type": "Blocks", "says": "x", "this_item_is": end, "other": other, "other_status": None}   # noqa: E731
            items["DEMO-1"]["links"] = [link("target", "DEMO-1"), link("target", "DEMO-2"), link("source", "DEMO-2")]
            items["DEMO-2"]["links"] = [link("target", "DEMO-1"), link("source", "DEMO-1")]
        self.edit(knot)
        r = self.ranking()
        self.assertTrue({"DEMO-1", "DEMO-2"} <= set(r.blocked))
        self.assertTrue(self.text())

    def test_started_work_is_listed_at_the_top_and_keeps_its_place(self):
        text = self.text()
        section = text.split("## Already started by you")[1].split("## Ranked")[0]
        self.assertIn("- `DEMO-9`, place 4: `status` is `In Progress`; `issuelinks` shows 1 open item waiting on it: `DEMO-10`.", section)
        self.assertIn("`status` is not a ranking criterion", section)
        self.assertEqual(self.ranking().ranked.index("DEMO-9"), 3)

    def test_a_blocked_item_that_would_outrank_the_start_is_pointed_out_with_its_blocker(self):
        start = self.text().split("## Start here")[1].split("## Already started")[0]
        self.assertIn("Blocked items that would rank above it if they were not blocked.", start)
        self.assertIn("- `DEMO-5`: `priority` is `Highest`, number 1 of the site's 5; `duedate` is `2026-12-02`", start)
        self.assertIn("blocked by `DEMO-3`.", start)
        self.assertNotIn("`DEMO-10`:", start)

    def test_only_a_blocks_link_in_which_the_item_is_the_target_blocks_it(self):
        r = self.ranking()
        self.assertEqual(r.open_blockers("DEMO-3"), [])                  # it blocks DEMO-5; it is not blocked by it
        self.assertEqual(r.open_blockers("DEMO-2"), [])                  # a "relates to" link
        self.assertIn("DEMO-1", r.ranked)                                # DEMO-1 blocks DEMO-4


class TheOrder(Case):
    """Criteria 4 and 6."""

    def setUp(self):
        Case.setUp(self)
        self.copy()

    def test_the_same_input_gives_the_same_recommendation_byte_for_byte(self):
        self.assertEqual(self.text(), self.text())

    def test_the_order_of_the_items_in_the_file_does_not_matter(self):
        first = self.text()
        for seed in range(5):
            def shuffle(data, items, seed=seed):
                random.Random(seed).shuffle(data["items"])
                for item in data["items"]:
                    random.Random(seed).shuffle(item["links"])
            self.edit(shuffle)
            self.assertEqual(self.text(), first)

    def test_a_tie_on_priority_and_due_is_broken_by_waiters_and_the_reason_says_tie_break(self):
        r = self.ranking()
        self.assertEqual(r.decided("DEMO-1", "DEMO-2")[0], "waiters")
        self.assertIn("It is below `DEMO-1` on **waiters**", self.text())
        self.assertIn("Every earlier criterion was equal, so this is the tie-break.", self.text())

    def test_items_equal_on_everything_are_ordered_by_key_by_number_not_by_text(self):
        def same(data, items):
            for key in ("DEMO-2", "DEMO-12"):
                items[key].update({"priority": "Low", "duedate": None, "created": "2026-11-01T09:00:00.000+0000", "links": []})
        self.edit(same)
        r = self.ranking()
        self.assertLess(r.ranked.index("DEMO-2"), r.ranked.index("DEMO-12"))
        self.assertEqual(r.decided("DEMO-2", "DEMO-12")[0], "key")

    def test_created_is_compared_as_a_moment_whatever_offset_jira_wrote_it_with(self):
        def offsets(data, items):
            for key, created in (("DEMO-2", "2026-11-01T08:30:00.000+0000"), ("DEMO-12", "2026-11-01T10:00:00.000+0300")):
                items[key].update({"priority": "Low", "duedate": None, "created": created, "links": []})
        self.edit(offsets)
        r = self.ranking()
        # DEMO-12 was created at 07:00 UTC, before DEMO-2 at 08:30 UTC, though as text "T10:00" comes after "T08:30"
        self.assertLess(r.ranked.index("DEMO-12"), r.ranked.index("DEMO-2"))
        self.assertEqual(r.decided("DEMO-12", "DEMO-2")[0], "created")

    def test_priority_follows_the_sites_own_order_not_the_alphabet(self):
        def reorder(data, items):
            data["priorities"] = ["Blocker", "Major", "Minor"]
            for key, priority in (("DEMO-1", "Minor"), ("DEMO-2", "Major"), ("DEMO-7", "Blocker")):
                items[key]["priority"] = priority
        self.edit(reorder)
        ranked = self.ranking().ranked
        self.assertEqual([k for k in ranked if k in ("DEMO-1", "DEMO-2", "DEMO-7")], ["DEMO-7", "DEMO-2", "DEMO-1"])

    def test_the_other_rule_puts_due_before_priority(self):
        self.edit(lambda data, items: items["DEMO-12"].update({"duedate": "2026-11-25"}))
        self.assertEqual(self.ranking(rule="due-first").ranked[0], "DEMO-12")
        self.assertIn("Why `DEMO-12` is first under `due-first` and not under `priority-first`: `duedate` is `2026-11-25`", self.text(also="due-first"))
        self.assertEqual(self.ranking().ranked[0], "DEMO-7")
        text = self.text(also="due-first")
        self.assertIn("## The same records under the rule `due-first`", text)
        self.assertIn("| `DEMO-12` | 4 | 1 | moved up |", text)

    def test_waiters_counts_open_items_from_either_record(self):
        r = self.ranking()
        self.assertEqual(r.waiters("DEMO-9"), ["DEMO-10"])
        self.edit(lambda data, items: items["DEMO-9"].update({"links": []}))      # only DEMO-10's own record says so now
        self.assertEqual(self.ranking().waiters("DEMO-9"), ["DEMO-10"])
        self.edit(lambda data, items: items["DEMO-10"]["status"].update({"name": "Done", "category": "done"}))
        self.assertEqual(self.ranking().waiters("DEMO-9"), [])


class ReasonsAndMissingFields(Case):
    """Criteria 1 and 5."""

    def setUp(self):
        Case.setUp(self)
        self.copy()

    def test_every_reason_names_a_recorded_field(self):
        self.copy("2026-11-20T09:30:00Z", refresh=["DEMO-1"])
        text = self.text(now="2026-11-21T09:10:00Z", also="due-first")           # some copies stale, so every kind of line is there
        reasons = [line for line in text.split("\n") if line.startswith(("- Reason", "- BLOCKED BY", "- No longer blocked", "- It is below", "- It is first because", "- WARNING",
                                                                          "- If it were not blocked", "- Facts not used", "- `DEMO-", "Why this one", "Why it beat", "Why `DEMO-"))]
        self.assertGreater(len(reasons), 70)
        for line in reasons:
            self.assertTrue(any("`%s`" % field in line for field in FIELDS), line)
        kinds = set(line.split(":")[0].split(",")[0].split(" `")[0] for line in reasons)
        for wanted in ("- Reason", "- BLOCKED BY", "- It is below", "- It is first because no other ranked item comes before it on", "- WARNING", "- If it were not blocked", "- Facts not used to rank", "Why this one"):
            self.assertIn(wanted, kinds)

    def test_a_missing_field_puts_the_item_last_on_that_criterion_and_lowers_confidence_a_step_each(self):
        r = self.ranking()
        self.assertEqual(r.ranked[-1], "DEMO-8")                              # no priority: after every item that has one, DEMO-13 with its low priority included
        self.assertEqual((r.missing("DEMO-8"), r.confidence("DEMO-8")), (["priority", "duedate"], "low"))
        self.assertEqual((r.missing("DEMO-12"), r.confidence("DEMO-12")), (["duedate"], "medium"))
        self.assertEqual((r.missing("DEMO-1"), r.confidence("DEMO-1")), ([], "high"))
        self.assertEqual((r.missing("DEMO-11"), r.confidence("DEMO-11")), (["duedate", "created"], "low"))
        self.assertLess(r.ranked.index("DEMO-12"), r.ranked.index("DEMO-11"))  # same priority, neither has a due date: the one with no created date is after

    def test_missing_fields_are_reported_in_the_item_and_in_their_own_section(self):
        text = self.text()
        self.assertIn("- Reason, priority: `priority` is not recorded.", text)
        self.assertIn("- Confidence in the data: low, because `priority` is not recorded; `duedate` is not recorded.", text)
        section = text.split("## Missing fields")[1].split("##")[0]
        self.assertIn("On the criterion that uses it, the item goes after every item that has a value.", section)
        for line in ("- `DEMO-8`: `priority`, `duedate`.", "- `DEMO-9`: `duedate`.", "- `DEMO-11`: `duedate`, `created`.", "- `DEMO-12`: `duedate`."):
            self.assertIn(line, section)
        self.assertNotIn("`DEMO-1`:", section)
        self.assertIn("**Confidence is about the data, not the advice.**", text)

    def test_a_priority_name_the_site_does_not_list_is_treated_as_missing_and_said(self):
        self.edit(lambda data, items: items["DEMO-7"].update({"priority": "Urgent"}))
        r = self.ranking()
        self.assertGreater(r.ranked.index("DEMO-7"), r.ranked.index("DEMO-12"))
        self.assertIn("`priority` is `Urgent`, which is not among the site's priorities as copied", self.text())
        self.assertEqual(r.confidence("DEMO-7"), "medium")

    def test_a_due_date_already_past_says_before(self):
        self.assertNotIn("OVERDUE", self.text(now="2026-11-30T23:59:59Z"))        # DEMO-13 is due that day
        self.assertIn("`duedate` is `2026-11-30`, the UTC date of the clock value", self.text(now="2026-11-30T23:59:59Z"))
        self.assertIn("`duedate` is `2026-11-30`, OVERDUE: 1 day BEFORE the UTC date of the clock value", self.text(now="2026-12-01T00:00:00Z"))


class StaleCopies(Case):
    """Criterion 3."""

    def setUp(self):
        Case.setUp(self)
        self.copy(T0)

    def test_a_copy_older_than_the_limit_carries_a_warning_and_one_just_inside_it_does_not(self):
        self.assertNotIn("STALE", self.text(now="2026-11-21T09:00:00Z"))            # exactly 24 hours
        text = self.text(now="2026-11-21T09:00:01Z")
        self.assertIn("WARNING: STALE COPY: `copied_at` is `%s`, 24 hours before the clock value. The limit is 24 hours." % T0, text)
        self.assertIn("`copied_at` is a field of the local record, not of Jira", text)

    def test_a_stale_item_keeps_its_place_and_is_never_start_here(self):
        self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-1", "DEMO-2"])
        r = self.ranking(now="2026-12-01T09:00:00Z")
        self.assertEqual(r.ranked[0], "DEMO-7")
        self.assertTrue(r.stale("DEMO-7"))
        self.assertEqual(r.start_here(), "DEMO-1")
        text = self.text(now="2026-12-01T09:00:00Z")
        self.assertIn("**`DEMO-1`**, place 2. Confidence in the data: high.", text)
        self.assertIn("It is not first on the recorded fields. Ranked above it, on copies too old to act on. **Copy these again first: they may be the better choice.**", text)
        self.assertIn("- `DEMO-7`, place 1. STALE COPY: `copied_at` is `%s`, 11 days before the clock value." % T0, text)
        self.assertIn("| 1 | `DEMO-7` | medium | STALE |", text)
        own = text.split("### 1. `DEMO-7`")[1].split("###")[0]                 # the warning is in the item's own reasons
        self.assertIn("- WARNING: STALE COPY: `copied_at` is `%s`" % T0, own)
        self.assertIn("- Confidence in the data: medium, because the copy is stale.", own)
        self.assertNotIn("WARNING", text.split("### 2. `DEMO-1`")[1].split("###")[0])

    def test_the_item_the_scenario_describes_is_not_recommended(self):
        """Highest priority; since the copy, someone took it and it became blocked; the copy is eleven days old."""
        self.fake.assign("DEMO-7", "other")
        self.fake.block("DEMO-7", "DEMO-9")
        self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-1", "DEMO-2"])            # DEMO-7 is NOT copied again
        r = self.ranking(now="2026-12-01T09:00:00Z")
        self.assertEqual((r.ranked[0], r.start_here()), ("DEMO-7", "DEMO-1"))       # still first on its old fields, and not offered as the start
        self.copy("2026-12-01T08:30:00Z", refresh=["DEMO-7"])                       # copied again: the truth
        r = self.ranking(now="2026-12-01T09:00:00Z")
        self.assertIn("DEMO-7", [key for key, _ in r.not_offered])

    def test_when_every_ranked_copy_is_stale_nothing_is_recommended(self):
        text = self.text(now="2026-12-01T09:00:00Z")
        self.assertIn("**Nothing.** Every ranked item's copy is stale. Copy the project again before starting anything.", text)

    def test_a_stale_blocker_is_said_to_be_stale(self):
        self.copy("2026-12-01T08:00:00Z", refresh=["DEMO-5"])
        text = self.text(now="2026-12-01T09:00:00Z")
        self.assertIn("`DEMO-3`'s own record IS STALE.", text)
        self.assertEqual(self.ranking(now="2026-12-01T09:00:00Z").confidence("DEMO-5"), "medium")

    def test_a_clock_value_is_required_and_cannot_be_earlier_than_a_copy(self):
        code, text = self.main(rank, "rank", "--records", self.records)
        self.assertEqual(code, 2)
        self.assertIn("It is required: the computer's clock is never read", text)
        code, text = self.main(rank, "rank", "--records", self.records, "--now", "2026-11-19T09:00:00Z")
        self.assertEqual(code, 2)
        self.assertIn("the clock value is earlier than the copy", text)

    def test_records_with_a_value_of_the_wrong_shape_stop_the_ranking_cleanly(self):
        for change in (lambda data, items: items["DEMO-1"].update({"duedate": "2026-13-40"}), lambda data, items: items["DEMO-1"].update({"duedate": 5}),
                       lambda data, items: items["DEMO-1"].update({"priority": "High` | x"}), lambda data, items: items["DEMO-1"]["status"].update({"name": "<b>Done</b>"}),
                       lambda data, items: items["DEMO-1"].update({"created": "yesterday"}), lambda data, items: items["DEMO-5"]["links"][0].update({"this_item_is": "middle"}),
                       lambda data, items: data.pop("link_types"), lambda data, items: data.update({"priorities": ["High", "High"]})):
            self.copy(T0)
            self.edit(change)
            code, text = self.main(rank, "rank", "--records", self.records, "--now", "2026-11-20T10:00:00Z")
            self.assertEqual(code, 2)
            self.assertIn("STOPPED: the records file cannot be read", text)

    def test_two_keys_that_differ_only_by_a_leading_zero_are_still_ordered_by_a_rule(self):
        def twin(data, items):
            data["items"].append(dict(items["DEMO-1"], key="DEMO-01", id="39999"))
        self.edit(twin)
        first = self.text()
        self.assertLess(self.ranking().ranked.index("DEMO-01"), self.ranking().ranked.index("DEMO-1"))
        self.edit(lambda data, items: data["items"].reverse())
        self.assertEqual(self.text(), first)

    def test_the_recommendation_is_the_same_in_another_process_with_another_hash_seed(self):
        out = os.path.join(self.folder, "r.md")
        shas = []
        for seed in ("1", "2", "77"):
            done = subprocess.run([sys.executable, os.path.join(SKILL, "rank.py"), "rank", "--records", self.records, "--now", "2026-11-21T10:00:00Z", "--also-rule", "due-first", "--out", out],
                                  capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed), cwd=self.folder)
            self.assertEqual(done.returncode, 0, done.stderr)
            shas.append((rank.file_sha(out), done.stdout))
        self.assertEqual(len(set(shas)), 1)

    def test_records_that_cannot_be_read_or_hold_a_key_twice_stop_the_ranking(self):
        def twice(data, items):
            data["items"].append(dict(data["items"][0]))
        self.edit(twice)
        self.assertEqual(self.main(rank, "rank", "--records", self.records, "--now", "2026-11-20T10:00:00Z")[0], 2)
        with open(self.records, "w", encoding="utf-8") as f:
            f.write("{")
        self.assertEqual(self.main(rank, "rank", "--records", self.records, "--now", "2026-11-20T10:00:00Z")[0], 2)


class WhatChanged(Case):
    def test_diff_says_which_items_moved_and_names_the_field_that_changed(self):
        self.copy(T0)
        before = os.path.join(self.folder, "before.json")
        shutil.copy(self.records, before)
        self.fake.resolve("DEMO-3")
        self.copy("2026-11-20T09:30:00Z", refresh=["DEMO-3", "DEMO-5"])
        code, text = self.main(rank, "diff", "--before", before, "--now-before", "2026-11-20T10:00:00Z", "--after", self.records, "--now-after", "2026-11-20T10:00:00Z")
        self.assertEqual(code, 0)
        self.assertIn("Start here, before: DEMO-7. After: DEMO-5.", text)
        self.assertIn("DEMO-5: was blocked by DEMO-3. Now ranked, place 1.", text)
        self.assertIn('why: in the record of DEMO-3, `status` was "In Progress" and is now "Done".', text)
        self.assertIn("DEMO-3: was assignee is someone else. Now status is Done", text)
        self.assertIn("DEMO-7: was ranked, place 1. Now ranked, place 2.", text)
        self.assertIn("why: none of its own fields changed.", text)

    def test_the_rules_are_written_from_the_same_file_and_name_the_criteria_ties_and_missing_fields(self):
        out = os.path.join(self.folder, "rules.md")
        self.assertEqual(self.main(rank, "rules", "--out", out)[0], 0)
        with open(out, encoding="utf-8") as f:
            text = f.read()
        for wanted in ("| 1 | priority | `priority` |", "| 5 | key | `key` |", "## Ties", "## Missing fields", "## Stale copies", "24 hours", "its blocker named"):
            self.assertIn(wanted, text)
        self.assertEqual(rank.RULES["priority-first"], ("priority", "due", "waiters", "created", "key"))


if __name__ == "__main__":
    unittest.main()

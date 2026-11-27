"""Tests for link_work.py, against the fake Jira. No network. Every name, site and title here is made up."""
import argparse
import contextlib
import datetime
import io
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
import fake_jira           # noqa: E402
import link_work as lw     # noqa: E402

HOST = "fixture-site.example.invalid"
PERSON = "A made-up person"
BLOCKS, RELATES = "10000", "10003"


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-link-test-")
        self.state = os.path.join(self.folder, "state")
        self.fake = fake_jira.FakeJira()
        self.request = os.path.join(self.folder, "links.json")
        self.ask(("SAND-1", "blocks", "SAND-2"))
        self.allowlist = os.path.join(self.folder, "allowlist.json")
        self.write_allowlist([("20001", HOST)])
        self.clock = datetime.datetime(2026, 11, 27, 9, 0, 0)
        self.real_now, lw.now_utc = lw.now_utc, lambda: self.clock
        self.pauses = 0
        self.real_pause, lw.pause = lw.pause, lambda: setattr(self, "pauses", self.pauses + 1)
        self.bodies = []
        real_post = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (self.bodies.append(body), real_post(path, params, body))[1]

    def tearDown(self):
        lw.now_utc, lw.pause = self.real_now, self.real_pause
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def ask(self, *links, path=None):
        with open(path or self.request, "w", encoding="utf-8") as f:
            json.dump({"links": [{"from": a, "phrase": phrase, "to": b} for a, phrase, b in links]}, f)

    def write_allowlist(self, entries):
        with open(self.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": [{"site_fingerprint": lw.site_fingerprint(host), "project_id": project} for project, host in entries]}, f)

    def later(self, seconds):
        self.clock += datetime.timedelta(seconds=seconds)

    def run_command(self, command, host=HOST, **options):
        del lw.LINES[:]
        lw.PENDING.clear()
        conn = lw.Connection(self.fake.get, self.fake.post if command == "confirm" else None, host)
        args = argparse.Namespace(command=command, source="fake", request=self.request, state=self.state, allowlist=self.allowlist, fingerprint=None,
                                  confirmed_by=None, pretend_minutes_later=0, result=None, log=None)
        for name, value in options.items():
            setattr(args, name, value)
        code = lw.run(args, conn)
        lw.write_pending()
        self.saved = "\n".join(saved for _, saved in lw.LINES)
        self.assertNotIn(fake_jira.HOSTILE_SUMMARY, self.saved)      # other people's titles are never saved
        return code, "\n".join(shown for shown, _ in lw.LINES)

    def preview(self, **options):
        code, text = self.run_command("preview", **options)
        found = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text)
        return code, text, found.group(1) if found else None

    def confirm(self, fingerprint, **options):
        options.setdefault("confirmed_by", PERSON)
        return self.run_command("confirm", fingerprint=fingerprint, **options)

    def go(self, *links):
        """Ask for these links, preview and confirm. Returns the confirmation's (code, text)."""
        if links:
            self.ask(*links)
        self.later(2)
        _, text, fingerprint = self.preview()
        self.assertTrue(fingerprint, text)
        self.fingerprint = fingerprint
        return self.confirm(fingerprint)

    def links(self):
        """The fake's links as sentences, in order: ["SAND-3 blocks SAND-4", ...]."""
        issues = self.fake.state["issues"]
        return ["%s %s %s" % (issues[l["source"]]["key"], fake_jira.TYPES[l["type_id"]][2], issues[l["target"]]["key"])
                for l in sorted(self.fake.state["links"].values(), key=lambda item: int(item["id"]))]

    def posts(self):
        return sum(1 for method, _ in self.fake.requests if method == "POST")

    def refused(self, result, words, posts=0):
        code, text = result[0], result[1]
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED", text)
        self.assertIn(words, text)
        self.assertEqual(self.posts(), posts)
        self.assertNotRegex(text, r"Fingerprint of this preview")


class Direction(Case):
    """Criteria 1 and 3: the relationship in words, and the right type and direction on both items."""

    def test_the_preview_says_the_link_in_words_from_both_items(self):
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 0)
        for wanted in ("IN WORDS:                        SAND-1 blocks SAND-2.", "The same link, from the other item: SAND-2 is blocked by SAND-1.",
                       'Link type:  "Blocks" (link type id 10000)', 'inwardIssue   issue id 30001 (SAND-1), the item that "blocks"',
                       'outwardIssue  issue id 30002 (SAND-2), the item that "is blocked by"', "READ IT ALOUD", "That is: SAND-1 comes first, and SAND-2 waits for it.",
                       "DO NOT JUDGE THE LINK BY THESE TWO SLOT NAMES"):
            self.assertIn(wanted, text)
        self.assertEqual(self.posts(), 0)

    def test_a_blocks_b_is_sent_with_the_blocker_as_the_source(self):
        code, text = self.go()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.bodies, [{"type": {"id": BLOCKS}, "inwardIssue": {"id": "30001"}, "outwardIssue": {"id": "30002"}}])
        self.assertEqual(self.links()[-1], "SAND-1 blocks SAND-2")

    def test_b_is_blocked_by_a_is_the_same_link_and_is_sent_the_same_way(self):
        self.ask(("SAND-2", "is blocked by", "SAND-1"))
        text = self.preview()[1]
        self.assertIn("IN WORDS:                        SAND-2 is blocked by SAND-1.", text)
        self.assertIn("The same link, from the other item: SAND-1 blocks SAND-2.", text)
        code, text = self.go()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.bodies, [{"type": {"id": BLOCKS}, "inwardIssue": {"id": "30001"}, "outwardIssue": {"id": "30002"}}])
        self.assertEqual(self.links()[-1], "SAND-1 blocks SAND-2")
        self.assertIn("read from SAND-2: it lists link id 40002 as: SAND-2 is blocked by SAND-1", text)

    def test_the_link_is_read_back_from_both_items_in_words(self):
        code, text = self.go()
        for wanted in ("read from SAND-1: it lists link id 40002 as: SAND-1 blocks SAND-2. Wanted: SAND-1 blocks SAND-2. Type \"Blocks\": yes",
                       "read from SAND-2: it lists link id 40002 as: SAND-2 is blocked by SAND-1. Wanted: SAND-2 is blocked by SAND-1. Type \"Blocks\": yes",
                       "`inwardIssue` is issue id 30001 and `outwardIssue` is issue id 30002, as sent: yes", "counted on each: 1 and 1. One is wanted: yes"):
            self.assertIn(wanted, text)

    def test_a_link_that_jira_stores_the_other_way_round_is_noticed_and_named(self):
        """The one thing the fake cannot prove is which of Jira's two slots is which. If the workflow has it wrong, it must say so."""
        self.later(2)
        _, _, fingerprint = self.preview()
        self.fake.reverse_next = True
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("THE LINK READS BACKWARDS, AND IT IS IN JIRA NOW. Asked for: SAND-1 blocks SAND-2. What Jira now holds is link id 40002: SAND-2 blocks SAND-1", text)
        self.assertIn("1. Remove link id 40002 by hand in Jira", text)
        self.assertIn("2. Do not run this workflow again", text)
        self.assertNotIn("Preview again", text)                   # not the advice for this case
        self.assertNotIn("WRITTEN to Jira", text)
        with open(os.path.join(self.state, "written", fingerprint + ".json"), encoding="utf-8") as f:
            entry = json.load(f)["links"][0]
        self.assertEqual(entry["link_id"], "40002")
        self.assertIn("THE WRONG WAY ROUND IS IN JIRA", entry["status"])
        self.assertEqual(self.links()[-1], "SAND-2 blocks SAND-1")

    def test_an_opposite_link_that_appears_while_jira_refuses_the_write_is_not_called_this_workflows_mistake(self):
        self.later(2)
        _, _, fingerprint = self.preview()
        self.fake.fail_post = 400
        self.fake.before_post = lambda fake: fake.other_link("SAND-2", "Blocks", "SAND-1")
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertNotIn("READS BACKWARDS", text)
        self.assertIn("A new link the OPPOSITE way round is there (link id 40002). Jira refused this write, so it is someone else's", text)
        self.tearDown()
        self.setUp()
        self.later(2)
        _, _, fingerprint = self.preview()
        self.fake.fail_post = 500
        self.fake.before_post = lambda fake: fake.other_link("SAND-2", "Blocks", "SAND-1")
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertNotIn("READS BACKWARDS", text)
        self.assertIn("a new link the OPPOSITE way round (link id 40002), which may be someone else's", text)

    def test_reading_an_item_takes_outward_issue_to_mean_this_item_is_the_source(self):
        reader = lw.Reader(lw.Connection(self.fake.get, None, HOST))
        blocker, blocked = reader.read("SAND-3", "x"), reader.read("SAND-4", "x")
        self.assertEqual([(l["source"], l["target"]) for l in blocker["links"]], [("30003", "30004")])
        self.assertEqual([(l["source"], l["target"]) for l in blocked["links"]], [("30003", "30004")])
        kind = {"outward": "blocks", "inward": "is blocked by"}
        keys = {"30003": "SAND-3", "30004": "SAND-4"}
        self.assertEqual(lw.in_words(blocker, blocker["links"][0], kind, keys), "SAND-3 blocks SAND-4")
        self.assertEqual(lw.in_words(blocked, blocked["links"][0], kind, keys), "SAND-4 is blocked by SAND-3")

    def test_the_same_link_and_the_opposite_link_are_told_apart(self):
        want = {"type": {"id": BLOCKS}, "symmetric": False, "source": {"id": "1"}, "target": {"id": "2"}}
        same, other_way, other_type = ({"type_id": BLOCKS, "source": "1", "target": "2"}, {"type_id": BLOCKS, "source": "2", "target": "1"},
                                       {"type_id": RELATES, "source": "1", "target": "2"})
        self.assertEqual([lw.same_link(l, want) for l in (same, other_way, other_type)], [True, False, False])
        self.assertEqual([lw.opposite_link(l, want) for l in (same, other_way, other_type)], [False, True, False])
        either = dict(want, symmetric=True)
        self.assertEqual([lw.same_link(l, either) for l in (same, other_way, other_type)], [True, True, False])
        self.assertEqual([lw.opposite_link(l, either) for l in (same, other_way)], [False, False])

    def test_a_link_type_with_one_phrase_has_no_direction(self):
        code, text = self.go(("SAND-1", "relates to", "SAND-2"))
        self.assertEqual(code, 0, text)
        self.assertIn("read from SAND-2: it lists link id 40002 as: SAND-2 relates to SAND-1", text)
        self.later(5)
        self.ask(("SAND-2", "relates to", "SAND-1"))
        code, text, fingerprint = self.preview()
        self.assertIn("ALREADY THERE", text)
        self.assertIn("it has no direction", text)
        self.assertIsNone(fingerprint)
        self.assertEqual(self.posts(), 1)

    def test_a_link_of_the_wrong_type_between_the_same_items_is_not_taken_for_the_link(self):
        self.fake.other_link("SAND-1", "Relates", "SAND-2")
        code, text = self.go()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.links()[-2:], ["SAND-1 relates to SAND-2", "SAND-1 blocks SAND-2"])


class ExistingLinks(Case):
    """Criteria 2 and 9."""

    def test_an_identical_link_is_detected_and_not_created_again(self):
        self.ask(("SAND-3", "blocks", "SAND-4"))
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 0)
        for wanted in ("NOTHING TO CREATE", "ALREADY THERE. It is not created again", "the same type and the same way round: 1 (link id 40001)", "No fingerprint is issued"):
            self.assertIn(wanted, text)
        self.assertIsNone(fingerprint)
        self.assertEqual((self.posts(), len(self.links())), (0, 1))

    def test_it_is_detected_when_asked_for_from_the_other_item(self):
        self.ask(("SAND-4", "is blocked by", "SAND-3"))
        code, text, fingerprint = self.preview()
        self.assertIn("ALREADY THERE", text)
        self.assertIsNone(fingerprint)

    def test_the_opposite_link_is_a_conflict_and_nothing_is_created(self):
        self.ask(("SAND-4", "blocks", "SAND-3"))
        self.refused(self.preview(), "THE OPPOSITE LINK ALREADY EXISTS (link id 40001): SAND-3 blocks SAND-4. The request says: SAND-4 blocks SAND-3")
        self.ask(("SAND-3", "is blocked by", "SAND-4"))
        self.refused(self.preview(), "THE OPPOSITE LINK ALREADY EXISTS")

    def test_running_the_approved_workflow_again_creates_nothing(self):
        self.assertEqual(self.go()[0], 0)
        before = self.links()
        self.later(30)
        code, text, fingerprint = self.preview()
        self.assertIn("NOTHING TO CREATE", text)
        self.assertIsNone(fingerprint)
        code, text = self.confirm(self.fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("has been used", text)
        self.assertEqual((self.links(), self.posts()), (before, 1))

    def test_a_link_made_by_someone_else_after_the_preview_stops_the_confirmation(self):
        _, _, fingerprint = self.preview()
        self.fake.other_link("SAND-1", "Blocks", "SAND-2")
        self.refused(self.confirm(fingerprint), "it was to be created when previewed, and is already there now (link id 40002)")

    def test_the_opposite_link_made_after_the_preview_stops_the_confirmation(self):
        _, _, fingerprint = self.preview()
        self.fake.other_link("SAND-2", "Blocks", "SAND-1")
        self.refused(self.confirm(fingerprint), "THE OPPOSITE LINK ALREADY EXISTS")

    def test_a_link_made_in_the_last_moment_before_the_write_is_reported_as_a_double(self):
        """Jira has no 'only if absent'. The count after the write is what reports this."""
        _, _, fingerprint = self.preview()
        self.fake.before_post = lambda fake: fake.other_link("SAND-1", "Blocks", "SAND-2")
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("show 2 and 2 new links of this kind where one on each was wanted", text)

    def test_items_that_do_not_agree_about_their_links_stop_the_preview(self):
        real_get = self.fake.get

        def get(path, params=None):
            status, headers, body = real_get(path, params)
            if path.endswith("/SAND-4"):
                body["fields"]["issuelinks"] = []
            return status, headers, body

        self.fake.get = get
        self.ask(("SAND-3", "blocks", "SAND-4"))
        self.refused(self.preview(), "do not list the same links between them")


class WhichLinks(Case):
    """Only Blocks and Relates."""

    def test_a_phrase_of_a_type_this_workflow_does_not_create_is_refused(self):
        for phrase, name in (("duplicates", "Duplicate"), ("is duplicated by", "Duplicate"), ("clones", "Cloners"), ("is cloned by", "Cloners")):
            self.ask(("SAND-1", phrase, "SAND-2"))
            self.refused(self.preview(), 'is a phrase of the link type "%s", which this workflow does not create' % name)

    def test_a_phrase_the_site_does_not_use_is_refused_and_the_sites_phrases_are_listed(self):
        self.ask(("SAND-1", "depends on", "SAND-2"))
        self.refused(self.preview(), '"depends on" is not a phrase this Jira site uses')
        self.assertIn('"blocks", "is blocked by", "relates to"', self.preview()[1])

    def test_a_phrase_is_matched_exactly(self):
        for phrase in ("Blocks", "blocks ", "block", "is blocked", "blocks; relates to"):
            self.ask(("SAND-1", phrase, "SAND-2"))
            code, text, fingerprint = self.preview()
            self.assertEqual((code, fingerprint), (1, None), phrase)

    def test_a_phrase_that_two_link_types_share_is_refused(self):
        real = dict(fake_jira.TYPES)
        fake_jira.TYPES["10009"] = ("Gates", "is gated by", "blocks")
        self.fake.state["types"].append("10009")
        try:
            self.refused(self.preview(), 'the phrase "blocks" belongs to 2 link types')
        finally:
            fake_jira.TYPES.clear()
            fake_jira.TYPES.update(real)

    def test_a_site_type_named_blocks_with_its_phrases_the_other_way_round_is_followed_as_the_site_has_it(self):
        """The direction comes from the site's own phrases, not from the type's name."""
        real = dict(fake_jira.TYPES)
        fake_jira.TYPES[BLOCKS] = ("Blocks", "blocks", "is blocked by")       # inward and outward exchanged
        try:
            code, text = self.go(("SAND-1", "blocks", "SAND-2"))
            self.assertEqual(code, 0, text)
            self.assertEqual(self.bodies[-1], {"type": {"id": BLOCKS}, "inwardIssue": {"id": "30002"}, "outwardIssue": {"id": "30001"}})
            self.assertIn("read from SAND-1: it lists link id 40002 as: SAND-1 blocks SAND-2", text)
        finally:
            fake_jira.TYPES.clear()
            fake_jira.TYPES.update(real)

    def test_a_site_with_no_link_types_is_refused(self):
        self.fake.state["types"] = []
        self.refused(self.preview(), "Jira did not list its link types")


class WhichItems(Case):
    """Criterion 6, and the items themselves."""

    def test_an_item_linked_to_itself_is_refused_however_it_is_named(self):
        for a, b in (("SAND-1", "SAND-1"), ("SAND-1", "30001")):
            self.ask((a, "blocks", b))
            self.refused(self.preview(), "names one item twice")

    def test_an_item_jira_does_not_return_is_refused(self):
        self.ask(("SAND-1", "blocks", "SAND-99"))
        self.refused(self.preview(), 'Jira answered 404 for the item "SAND-99"')

    def test_either_item_in_a_project_off_the_allowlist_is_refused(self):
        for a, b in (("SAND-1", "PROD-9"), ("PROD-9", "SAND-1")):
            self.ask((a, "blocks", b))
            self.refused(self.preview(), "PROD-9 is in project PROD (project id 20002), which on the Jira site with fingerprint %s is not on the sandbox allowlist" % lw.site_fingerprint(HOST))

    def test_the_same_project_id_on_another_site_is_not_on_the_allowlist(self):
        self.write_allowlist([("20001", "another-site.example.invalid")])
        self.refused(self.preview(), "is not on the sandbox allowlist")

    def test_an_item_this_identity_may_not_link_is_refused(self):
        self.write_allowlist([("20001", HOST), ("20003", HOST)])
        self.ask(("SAND-1", "blocks", "RO-1"))
        self.refused(self.preview(), "may not link issues for RO-1")

    def test_a_title_is_not_accepted_as_a_reference(self):
        self.ask(("Collect the export requirements", "blocks", "SAND-2"))
        self.refused(self.preview(), "A title is not accepted")

    def test_titles_are_shown_on_screen_and_not_saved(self):
        self.ask(("SAND-5", "blocks", "SAND-6"))
        code, text, _ = self.preview()
        self.assertIn(fake_jira.HOSTILE_SUMMARY, text)
        self.assertNotIn(fake_jira.HOSTILE_SUMMARY, self.saved)
        self.assertIn("the title was shown on screen and is not saved", self.saved)
        self.assertEqual(self.posts(), 0)


class Circles(Case):
    """The first stretch goal."""

    def test_a_link_that_would_close_a_circle_is_refused(self):
        self.fake.other_link("SAND-4", "Blocks", "SAND-5")           # SAND-3 blocks SAND-4 blocks SAND-5
        self.ask(("SAND-5", "blocks", "SAND-3"))
        self.refused(self.preview(), 'THIS LINK WOULD CLOSE A CIRCLE. Followed from SAND-3, existing "blocks" links lead back to SAND-5')
        self.ask(("SAND-3", "is blocked by", "SAND-5"))
        self.refused(self.preview(), "THIS LINK WOULD CLOSE A CIRCLE")

    def test_a_circle_made_by_the_links_of_one_request_is_refused(self):
        self.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "blocks", "SAND-6"), ("SAND-6", "blocks", "SAND-1"))
        self.refused(self.preview(), "link 3: THIS LINK WOULD CLOSE A CIRCLE")

    def test_a_chain_that_does_not_come_back_is_allowed(self):
        self.fake.other_link("SAND-4", "Blocks", "SAND-5")
        code, text = self.go(("SAND-5", "blocks", "SAND-6"))
        self.assertEqual(code, 0, text)

    def test_links_of_another_type_do_not_make_a_circle(self):
        self.fake.other_link("SAND-2", "Relates", "SAND-1")
        self.assertEqual(self.go(("SAND-1", "blocks", "SAND-2"))[0], 0)

    def test_a_chain_too_long_to_follow_is_refused_and_not_assumed_clear(self):
        issues = self.fake.state["issues"]
        previous = "30002"
        for n in range(60):
            issue_id = str(31000 + n)
            issues[issue_id] = {"id": issue_id, "key": "SAND-%d" % (100 + n), "project_id": "20001", "summary": "one of a long chain", "updated": "x"}
            self.fake.add_link(BLOCKS, previous, issue_id)
            previous = issue_id
        self.refused(self.preview(), "reaches more than 50 items, so the check for a circle could not be finished")

    def test_a_chain_through_an_item_that_cannot_be_read_is_refused(self):
        self.fake.other_link("SAND-2", "Blocks", "SAND-6")
        real_get = self.fake.get
        self.fake.get = lambda path, params=None: (404, {}, {}) if path.endswith("/30006") else real_get(path, params)
        self.refused(self.preview(), "an item further along the chain from SAND-2")


class Batches(Case):
    """The second stretch goal: several links, one preview, one confirmation."""

    def three(self):
        self.ask(("SAND-3", "blocks", "SAND-4"), ("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))

    def test_several_links_under_one_fingerprint_and_one_already_there(self):
        self.three()
        _, text, fingerprint = self.preview()
        self.assertIn("It asks for 3 links. To create: 2. Already there: 1.", text)
        self.assertEqual(len(re.findall(r"Fingerprint of this preview", text)), 1)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("LINK 1 of 3: SAND-3 blocks SAND-4. ALREADY THERE (link id 40001). Not sent.", text)
        self.assertIn("ALL DONE: 2 links written, 1 already there.", text)
        self.assertEqual((self.posts(), self.links()), (2, ["SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2", "SAND-2 relates to SAND-6"]))
        self.assertEqual(self.run_command("check", fingerprint=fingerprint)[0], 0)

    def test_each_link_is_read_back_before_the_next_is_sent(self):
        self.three()
        _, _, fingerprint = self.preview()
        self.confirm(fingerprint)
        sent = [method + " " + path for method, path in self.fake.requests]
        first, second = [n for n, line in enumerate(sent) if line.startswith("POST")]
        self.assertIn("GET /rest/api/3/issueLink/40002", sent[first:second])

    def test_when_jira_refuses_one_the_run_stops_and_says_which_were_written(self):
        self.three()
        _, _, fingerprint = self.preview()
        self.fake.before_post = lambda fake: setattr(fake, "before_post", lambda again: setattr(again, "fail_post", 400))
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("link 3 (SAND-2 relates to SAND-6): Jira answered 400 to the write", text)
        self.assertIn("Written in this run before it stopped: link 2 (link id 40002). Not sent: none", text)
        self.assertNotIn("Nothing has been written.", text)
        self.assertEqual(self.links(), ["SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2"])
        self.later(5)
        _, text, fingerprint = self.preview()                # the rerun finds what was made, and offers only the rest
        self.assertIn("To create: 1. Already there: 2.", text)
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertEqual(len(self.links()), 3)

    def test_a_link_made_by_someone_else_while_the_batch_is_running_is_not_sent(self):
        self.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))
        _, _, fingerprint = self.preview()
        self.fake.before_post = lambda fake: fake.other_link("SAND-6", "Relates", "SAND-2")      # during the first write
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("link 2 (SAND-2 relates to SAND-6): just before its write, the link or its opposite was found there (link id 40002)", text)
        self.assertIn("Written in this run before it stopped: link 1 (link id 40003)", text)
        self.assertEqual(self.posts(), 1)

    def test_the_record_says_sending_at_the_moment_each_request_goes(self):
        self.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))
        _, _, fingerprint = self.preview()
        seen = []
        wrapped = self.fake.post

        def post(path, params=None, body=None):
            with open(os.path.join(self.state, "written", fingerprint + ".json"), encoding="utf-8") as f:
                seen.append([entry["status"] for entry in json.load(f)["links"]])
            return wrapped(path, params, body)

        self.fake.post = post
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertEqual(seen, [["sending", "not sent"], ["written", "sending"]])

    def test_more_than_five_links_or_the_same_link_twice_is_refused(self):
        self.ask(*[("SAND-1", "relates to", "SAND-%d" % n) for n in (2, 3, 4, 5, 6)] + [("SAND-2", "relates to", "SAND-3")])
        self.refused(self.preview(), "a list of 1 to 5 links")
        self.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "is blocked by", "SAND-1"))
        self.refused(self.preview(), "link 2 is link 1 again, or its opposite")
        self.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "blocks", "SAND-1"))
        self.refused(self.preview(), "link 2 is link 1 again, or its opposite")


class WhenNoAnswerComes(Case):
    def test_no_answer_and_the_link_was_made_is_found_by_reading_both_items(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_post = "applied-timeout"
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("NO ANSWER came back", text)
        self.assertIn("No answer came to the write; the link was found by reading both items", text)
        self.assertEqual(self.posts(), 1)

    def test_no_answer_and_no_link_is_not_known_and_is_not_sent_again(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_post = "timeout"
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("show 0 and 0 new links", text)
        self.assertIn("Do not confirm again with this fingerprint", text)
        self.assertEqual((self.posts(), len(self.links())), (1, 1))
        self.assertEqual(self.confirm(fingerprint)[0], 1)
        self.assertEqual(self.posts(), 1)

    def test_a_server_error_is_not_taken_to_mean_nothing_was_written(self):
        for status in (500, 503, 429):
            self.tearDown()
            self.setUp()
            _, _, fingerprint = self.preview()
            self.fake.fail_post = status
            code, text = self.confirm(fingerprint)
            self.assertEqual(code, 2, status)
            self.assertIn("IT IS NOT KNOWN whether it was written", text)

    def test_a_refusal_by_jira_with_nothing_read_back_means_nothing_was_written(self):
        for status in lw.REFUSALS:
            self.tearDown()
            self.setUp()
            _, _, fingerprint = self.preview()
            self.fake.fail_post = status
            code, text = self.confirm(fingerprint)
            self.assertEqual(code, 1, status)
            self.assertIn("so it was not written", text)
            self.assertIn("the fake was told to refuse", text)
            self.assertNotIn("the fake was told to refuse", self.saved)

    def test_a_refusal_is_not_believed_when_the_link_is_there_afterwards(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_post = 400
        self.fake.before_post = lambda fake: fake.other_link("SAND-1", "Blocks", "SAND-2")
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("IT IS NOT KNOWN whether it was written", text)

    def hide_new_link(self, times):
        """After the write, the first `times` reads of an item do not list the new link, as if Jira were slow to show it."""
        real_get, left = self.fake.get, [times]

        def get(path, params=None):
            status, headers, body = real_get(path, params)
            if self.posts() and re.fullmatch(r"/rest/api/3/issue/\d+", path) and left[0] > 0:
                left[0] -= 1
                body["fields"]["issuelinks"] = [l for l in body["fields"]["issuelinks"] if l["id"] != "40002"]
            return status, headers, body

        self.fake.get = get

    def test_a_link_jira_is_slow_to_show_is_read_again_and_the_write_is_not_sent_again(self):
        _, _, fingerprint = self.preview()
        self.hide_new_link(2)                    # one look at both items
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("Reading them again in 2 seconds. The write is not sent again.", text)
        self.assertEqual((self.pauses, self.posts(), len(self.links())), (1, 1, 2))

    def test_a_link_that_never_shows_needs_a_person_after_three_more_reads(self):
        _, _, fingerprint = self.preview()
        self.hide_new_link(100)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("show 0 and 0 new links", text)
        self.assertEqual((self.pauses, self.posts()), (3, 1))

    def test_reads_are_not_repeated_when_jira_gave_no_answer_or_refused(self):
        for failure in ("timeout", 400, 500):
            self.tearDown()
            self.setUp()
            _, _, fingerprint = self.preview()
            self.fake.fail_post = failure
            self.confirm(fingerprint)
            self.assertEqual(self.pauses, 0, failure)

    def test_a_read_that_fails_after_the_write_needs_a_person(self):
        _, _, fingerprint = self.preview()
        self.fake.fail_get_after_post = "broken"
        self.assertEqual(self.confirm(fingerprint)[0], 2)


class Refusals(Case):
    """Criterion 7."""

    def test_a_missing_confirmation(self):
        self.preview()
        self.refused(self.confirm(None), "no confirmation was given")
        self.later(2)
        _, _, fingerprint = self.preview()
        self.refused(self.confirm(fingerprint, confirmed_by="  "), "gives the name of the person confirming")

    def test_a_change_that_differs_from_the_preview(self):
        _, _, fingerprint = self.preview()
        self.ask(("SAND-2", "blocks", "SAND-1"))
        self.refused(self.confirm(fingerprint), "the request is not the file the preview showed")

    def test_a_reference_that_now_leads_to_another_item(self):
        _, _, fingerprint = self.preview()
        issues = self.fake.state["issues"]
        issues["30002"]["key"], issues["30006"]["key"] = "SAND-6", "SAND-2"      # the keys are exchanged, as after a move
        self.refused(self.confirm(fingerprint), "link 1 is no longer the same link")

    def test_a_preview_older_than_the_limit(self):
        _, _, fingerprint = self.preview()
        self.refused(self.confirm(fingerprint, pretend_minutes_later=16), "this preview is too old")
        self.later(15 * 60 + 1)
        self.refused(self.confirm(fingerprint), "this preview is too old")

    def test_a_preview_exactly_at_the_limit_is_accepted(self):
        _, _, fingerprint = self.preview()
        self.later(15 * 60)
        self.assertEqual(self.confirm(fingerprint)[0], 0)

    def test_an_allowlist_changed_after_the_preview(self):
        _, _, fingerprint = self.preview()
        self.write_allowlist([("20001", HOST), ("20002", HOST)])
        self.refused(self.confirm(fingerprint), "the allowlist file is not the one the preview used")
        self.write_allowlist([])
        self.refused(self.confirm(fingerprint), "is not on the sandbox allowlist")

    def test_permission_withdrawn_after_the_preview(self):
        _, _, fingerprint = self.preview()
        self.fake.state["may_link"]["20001"] = False
        self.refused(self.confirm(fingerprint), "may not link issues")

    def test_a_saved_preview_that_was_altered(self):
        _, _, fingerprint = self.preview()
        path = os.path.join(self.state, "previews", fingerprint + ".json")
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        saved["proposal"]["links"][0]["target"]["id"] = "30006"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(saved, f)
        self.refused(self.confirm(fingerprint), "has been altered since it was made")

    def test_a_fingerprint_that_names_no_preview_or_is_not_one(self):
        self.refused(self.confirm("0123456789ab"), "there is no preview with the fingerprint")
        self.refused(self.confirm("../../x"), "a fingerprint is 12 characters")

    def test_a_preview_made_against_another_site_or_for_another_request_file(self):
        _, _, fingerprint = self.preview()
        self.write_allowlist([("20001", HOST), ("20001", "another-site.example.invalid")])
        self.refused(self.confirm(fingerprint, host="another-site.example.invalid"), "not the Jira site the preview was made against")
        other = os.path.join(self.folder, "other.json")
        shutil.copy(self.request, other)
        self.refused(self.confirm(fingerprint, request=other), "was made for another request file")

    def test_a_site_whose_words_for_the_type_changed_after_the_preview(self):
        _, _, fingerprint = self.preview()
        real = dict(fake_jira.TYPES)
        try:
            fake_jira.TYPES["10003"] = ("Relates", "relates to", "is related to")
            before = self.posts()
            self.later(1)
            fake_jira.TYPES[BLOCKS] = ("Blocks", "is waiting on", "blocks")      # the other phrase of the link's own type
            self.refused(self.confirm(fingerprint), "link 1: the site's words for this link type have changed since the preview")
            fake_jira.TYPES[BLOCKS] = real[BLOCKS]
            self.assertEqual(self.confirm(fingerprint)[0], 0)        # another type's words changing does not matter
            self.assertEqual(self.posts(), before + 1)
        finally:
            fake_jira.TYPES.clear()
            fake_jira.TYPES.update(real)

    def test_an_item_that_moved_to_another_project_just_before_the_write(self):
        _, _, fingerprint = self.preview()
        real_get = self.fake.get

        def get(path, params=None):
            status, headers, body = real_get(path, params)
            if path.endswith("/30002"):                       # the last read before the write is by issue id
                body["fields"]["project"] = {"id": "20002", "key": "PROD"}
            return status, headers, body

        self.fake.get = get
        self.refused(self.confirm(fingerprint), "an item was found to have moved to another project")

    def test_a_saved_preview_marked_unused_by_hand_is_stopped_by_what_jira_holds(self):
        """The 'used' mark is not covered by the fingerprint. What stops a second write is the read of both items."""
        self.assertEqual(self.go()[0], 0)
        path = os.path.join(self.state, "previews", self.fingerprint + ".json")
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        saved["state"] = "open"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(saved, f)
        code, text = self.confirm(self.fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("is already there now", text)
        self.assertEqual(self.posts(), 1)


class OneRunAtATime(Case):
    def test_while_one_run_is_confirming_another_is_refused(self):
        _, _, fingerprint = self.preview()
        seen = []
        real_get = self.fake.get

        def get(path, params=None):
            try:
                lw.claim_request(self.state, "links")
                seen.append("a second run got in")
            except lw.Refused as refusal:
                seen.append(str(refusal))
            return real_get(path, params)

        self.fake.get = get
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertTrue(seen and all("another run is confirming this request" in said for said in seen), seen[:1])
        self.assertFalse(os.path.exists(os.path.join(self.state, "claims", "links")))

    def test_a_held_claim_stops_a_confirmation_and_an_old_one_can_be_taken_over(self):
        _, _, fingerprint = self.preview()
        lw.claim_request(self.state, "links")
        asked = len(self.fake.requests)
        self.refused(self.confirm(fingerprint), "another run is confirming this request")
        self.assertEqual(len(self.fake.requests), asked)
        self.later(10 * 60 + 1)
        self.assertEqual(self.confirm(fingerprint)[0], 0)

    def test_a_run_whose_claim_was_taken_sends_nothing_and_does_not_remove_the_other_runs_claim(self):
        _, _, fingerprint = self.preview()
        claim = os.path.join(self.state, "claims", "links")
        real_get = self.fake.get

        def get(path, params=None):
            if path == "/rest/api/3/mypermissions":          # partway through: another run takes the claim over
                with open(claim, "w", encoding="ascii") as f:
                    f.write("%s|%s" % (lw.stamp(self.clock), "another-runs-mark"))
            return real_get(path, params)

        self.fake.get = get
        self.refused(self.confirm(fingerprint), "this run's claim on the request has been taken by another run")
        with open(claim, encoding="ascii") as f:
            self.assertIn("another-runs-mark", f.read())

    def test_the_claim_is_renewed_before_each_write(self):
        self.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))
        _, _, fingerprint = self.preview()
        claim = os.path.join(self.state, "claims", "links")
        times = []
        wrapped = self.fake.post

        def post(path, params=None, body=None):
            with open(claim, encoding="ascii") as f:
                times.append(f.read().split("|")[0])
            self.later(120)
            return wrapped(path, params, body)

        self.fake.post = post
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertEqual(times, ["2026-11-27 09:00:00 UTC", "2026-11-27 09:02:00 UTC"])

    def test_the_saved_preview_is_read_after_the_claim_is_taken(self):
        _, _, fingerprint = self.preview()
        real_claim = lw.claim_request

        def claim_then_another_run_writes(state, name):
            path = real_claim(state, name)
            file = os.path.join(self.state, "previews", fingerprint + ".json")
            with open(file, encoding="utf-8") as f:
                saved = json.load(f)
            saved["state"] = "writing"
            lw.save_json(file, saved)
            return path

        lw.claim_request = claim_then_another_run_writes
        try:
            self.refused(self.confirm(fingerprint), "has been used")
        finally:
            lw.claim_request = real_claim


class TheCheck(Case):
    def test_check_reads_each_link_back_from_both_items(self):
        self.go()
        code, text = self.run_command("check", fingerprint=self.fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("read from SAND-2: it lists link id 40002 as: SAND-2 is blocked by SAND-1", text)
        self.assertIn("FOUND: every link is there", text)
        self.assertIn("Every one was a GET", text)

    def test_check_says_so_when_the_link_has_been_removed_or_doubled_or_opposed(self):
        self.go()
        self.fake.other_link("SAND-1", "Blocks", "SAND-2")
        code, text = self.run_command("check", fingerprint=self.fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("counted on each: 2 and 2. One is wanted: NO", text)
        self.fake.remove_link("40003")
        self.fake.other_link("SAND-2", "Blocks", "SAND-1")
        code, text = self.run_command("check", fingerprint=self.fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("A LINK THE OPPOSITE WAY ROUND is also there: link id 40004", text)
        self.fake.remove_link("40004")
        self.fake.remove_link("40002")
        code, text = self.run_command("check", fingerprint=self.fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("NOT LISTED", text)

    def test_check_says_so_when_the_link_with_that_id_now_runs_the_other_way(self):
        self.go()
        held = self.fake.state["links"]["40002"]
        held["source"], held["target"] = held["target"], held["source"]
        code, text = self.run_command("check", fingerprint=self.fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("read from SAND-1: it lists link id 40002 as: SAND-1 is blocked by SAND-2. Wanted: SAND-1 blocks SAND-2. Type \"Blocks\": NO", text)

    def test_the_link_read_by_its_own_id_must_agree_with_what_was_sent(self):
        self.later(2)
        _, _, fingerprint = self.preview()
        real_get = self.fake.get

        def get(path, params=None):
            status, headers, body = real_get(path, params)
            if path.startswith("/rest/api/3/issueLink/"):
                body["inwardIssue"], body["outwardIssue"] = body["outwardIssue"], body["inwardIssue"]
            return status, headers, body

        self.fake.get = get
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2)
        self.assertIn("`inwardIssue` is issue id 30002 and `outwardIssue` is issue id 30001, as sent: NO", text)

    def test_the_result_record_names_the_link_its_id_the_project_the_time_and_the_confirmer(self):
        self.later(2)
        _, _, fingerprint = self.preview()
        result = os.path.join(self.folder, "out", "result.md")
        code, text = self.confirm(fingerprint, result=result)
        with open(result, encoding="utf-8") as f:
            saved = f.read()
        for wanted in ("Link 1. Issue keys: SAND-1 and SAND-2", "Identifier of what was created: Jira issue link id 40002. Status: written",
                       "In words: SAND-1 blocks SAND-2. From the other item: SAND-2 is blocked by SAND-1", "Target project: SAND (project id 20001)",
                       "Written at: 2026-11-27 09:00:02 UTC", "Confirmed by: " + PERSON, "as asked: the right type and the right way round on each"):
            self.assertIn(wanted, saved)
        self.assertNotIn(HOST, saved)


class TheCommandLine(Case):
    def main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = lw.main(list(args))
        return code, out.getvalue()

    def test_a_whole_run_through_main_with_a_saved_log(self):
        self.ask(("SAND-5", "blocks", "SAND-6"))
        common = ["--source", "fake", "--state", self.state]
        files = ["--request", self.request, "--allowlist", self.allowlist]
        log = os.path.join(self.folder, "logs", "preview.txt")
        code, text = self.main("preview", *common, *files, "--log", log)
        fingerprint = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text).group(1)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertIn(HOST, text)
        self.assertNotIn(HOST, saved)
        self.assertIn(fake_jira.HOSTILE_SUMMARY, text)
        self.assertNotIn(fake_jira.HOSTILE_SUMMARY, saved)
        self.assertEqual(self.main("confirm", *common, *files, "--fingerprint", fingerprint, "--confirmed-by", PERSON)[0], 0)
        self.assertEqual(self.main("check", *common, "--fingerprint", fingerprint)[0], 0)
        self.assertIn("NOTHING TO CREATE", self.main("preview", *common, *files)[1])

    def test_a_result_record_that_cannot_be_saved_does_not_change_what_happened(self):
        files = ["--source", "fake", "--state", self.state, "--request", self.request, "--allowlist", self.allowlist]
        _, text = self.main("preview", *files)
        fingerprint = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text).group(1)
        code, text = self.main("confirm", *files, "--fingerprint", fingerprint, "--confirmed-by", PERSON, "--result", os.path.join(self.request, "under-a-file", "result.md"))
        self.assertEqual(code, 0)
        self.assertIn("THE RESULT RECORD COULD NOT BE SAVED", text)
        self.assertIn("ALL DONE: 1 link written", text)

    def test_only_confirm_is_given_a_way_to_write_whatever_the_source(self):
        made, asked = [], []
        real, real_live = lw.Connection, lw.make_live

        class Watched(real):
            def __init__(self, get, post, host):
                made.append(post is not None)
                real.__init__(self, get, post, host)

        def live(may_write, opener=None):
            asked.append(may_write)
            return real(self.fake.get, self.fake.post if may_write else None, HOST), []

        lw.Connection, lw.make_live = Watched, live
        try:
            for source in ("fake", "live"):
                common = ["--source", source, "--state", self.state]
                self.main("preview", *common, "--request", self.request, "--allowlist", self.allowlist)
                self.main("check", *common, "--fingerprint", "0123456789ab")
            self.main("confirm", "--source", "fake", "--state", self.state, "--request", self.request, "--allowlist", self.allowlist, "--fingerprint", "0123456789ab", "--confirmed-by", PERSON)
        finally:
            lw.Connection, lw.make_live = real, real_live
        self.assertEqual((made, asked), ([False, False, True], [False, False]))      # the fake's three, then the two asked of the live one

    def test_the_live_connection_sends_no_write_but_one_new_link(self):
        sent = []

        class Opener:
            def open(self, request, timeout=None):
                sent.append((request.get_method(), request.full_url))
                raise OSError("the stand-in sends nothing")

        names = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        before = {name: os.environ.get(name) for name in names}
        os.environ.update(dict(zip(names, ("https://" + HOST, "tester@example.invalid", "made-up-value"))))
        try:
            conn, hidden = lw.make_live(True, Opener())
            good = {"type": {"id": "1"}, "inwardIssue": {"id": "2"}, "outwardIssue": {"id": "3"}}
            for path, body in (("/rest/api/3/issue", good), ("/rest/api/3/issueLink/40001", good), (lw.WRITE_PATH, dict(good, comment={"body": "x"})),
                               (lw.WRITE_PATH, dict(good, type={"name": "Duplicate"})), (lw.WRITE_PATH, dict(good, inwardIssue={"key": "SAND-1"})),
                               (lw.WRITE_PATH, {k: v for k, v in good.items() if k != "type"})):
                with self.assertRaises(lw.Refused):
                    conn._post(path, None, body)
            self.assertEqual(sent, [])
            with self.assertRaises(OSError):
                conn._post(lw.WRITE_PATH, None, good)
            self.assertEqual(sent, [("POST", "https://%s%s" % (HOST, lw.WRITE_PATH))])
            self.assertIsNone(lw.make_live(False, Opener())[0]._post)
            self.assertEqual(len(hidden), 3)
            for base in ("http://" + HOST, "https://%s:8443" % HOST, "https://%s/path" % HOST):
                os.environ.update({"JIRA_BASE_URL": base})
                with self.assertRaises(lw.Refused):
                    lw.make_live(False)
        finally:
            for name, value in before.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ.update({name: value})

    def test_a_real_write_needs_a_terminal(self):
        class Stream:
            def isatty(self):
                return False

        names = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        before = {name: os.environ.get(name) for name in names}
        os.environ.update(dict(zip(names, ("https://" + HOST, "tester@example.invalid", "made-up-value"))))
        real_stdin, sys.stdin = sys.stdin, Stream()
        try:
            code, text = self.main("confirm", "--source", "live", "--state", self.state, "--request", self.request, "--allowlist", self.allowlist,
                                   "--fingerprint", "0123456789ab", "--confirmed-by", PERSON)
        finally:
            sys.stdin = real_stdin
            for name, value in before.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ.update({name: value})
        self.assertEqual(code, 1)
        self.assertIn("confirmed by a person at a terminal", text)
        self.assertFalse(lw.person_present(None))


if __name__ == "__main__":
    unittest.main()

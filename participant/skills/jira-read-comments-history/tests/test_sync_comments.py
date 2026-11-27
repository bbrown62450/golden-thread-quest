"""Tests for sync_comments.py, against the made-up Jira. No network. Every comment, change and person here is made up."""
import argparse
import builtins
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import fake_jira        # noqa: E402
import sync_comments    # noqa: E402

RULES_FILE = os.path.abspath(os.path.join(SKILL, "..", "..", "context", "jira", "history-rules.md"))
T1, T2, T3, T4 = "2026-11-07T09:00:00Z", "2026-11-07T10:00:00Z", "2026-11-08T12:00:00Z", "2026-11-09T12:00:00Z"
MADE_UP = "-".join(["made", "up", "value", "used", "only", "in", "tests"])      # stands where an API token would be
NOTES = "# My notes\n\nThese are mine. A sync must leave them alone.\n"


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-comments-test-")
        self.out = os.path.join(self.folder, "out")
        os.makedirs(self.out)
        self.state = os.path.join(self.folder, "jira")
        os.makedirs(self.state)
        self.fake_path = os.path.join(self.state, "fake-jira.json")
        fake_jira.FakeJira(fake_jira.fresh()).save(self.fake_path)
        self.notes = os.path.join(self.out, "sample.notes.md")
        with open(self.notes, "w", encoding="utf-8") as f:
            f.write(NOTES)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def main(self, *argv):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                code = sync_comments.main(list(argv))
            except SystemExit as stop:
                code = stop.code
        return code, printed.getvalue()

    def sync(self, now=T1, extra=(), name="sample"):
        return self.main("sync", "--source", "fake", "--issue", "DEMO-7", "--out-dir", self.out, "--name", name, "--state", self.state, "--pretend-now", now, *extra)

    @contextlib.contextmanager
    def jira(self):
        """The made-up Jira, opened to be changed the way people change a story, and saved again."""
        fake = fake_jira.FakeJira.open(self.fake_path)
        yield fake
        fake.save(self.fake_path)

    def copy(self, name="sample"):
        with open(os.path.join(self.out, name + ".json"), encoding="utf-8") as f:
            return json.load(f)

    def page(self, name="sample"):
        with open(os.path.join(self.out, name + ".md"), encoding="utf-8") as f:
            return f.read()

    def comment(self, ident):
        found = [c for c in self.copy()["comments"] if c["id"] == ident]
        self.assertEqual(len(found), 1, "comment %s is in the copy %d times" % (ident, len(found)))
        return found[0]

    def files(self):
        """Every file in the out folder with its bytes and the time it was last written."""
        state = {}
        for name in sorted(os.listdir(self.out)):
            path = os.path.join(self.out, name)
            with open(path, "rb") as f:
                state[name] = (f.read(), os.stat(path).st_mtime_ns, os.stat(path).st_ino)
        return state

    def headings(self):
        return [line for line in self.page().split("\n") if line.startswith("### Comment ")]


class KeyedByJirasIdentifier(Case):
    def test_each_comment_is_under_its_identifier_once_in_the_copy_and_on_the_page(self):
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertEqual([c["id"] for c in self.copy()["comments"]], ["31001", "31002", "31003", "31004", "31005"])
        self.assertEqual(self.headings(), ["### Comment %d" % n for n in range(31001, 31006)])

    def test_two_comments_with_the_same_words_are_two_comments(self):
        self.sync()
        with self.jira() as jira:
            same = jira.data["comments"][0]["text"]
            new = jira.add(same, "2026-11-08T09:00:00.000+0000")
        code, text = self.sync(T3)
        self.assertEqual(code, 0)
        self.assertIn("added:                          1  [%s]" % new, text)
        self.assertEqual(len(self.copy()["comments"]), 6)
        self.assertEqual(self.comment(new)["text"], self.comment("31001")["text"])

    def test_the_same_identifier_with_other_words_is_the_same_comment(self):
        self.sync()
        with self.jira() as jira:
            jira.edit("31001", "Made-up comment: entirely different words.", "2026-11-08T08:00:00.000+0000")
        self.sync(T3)
        self.assertEqual(len(self.copy()["comments"]), 5)
        self.assertEqual(len(self.headings()), 5)

    def test_comments_come_in_pages_and_every_page_is_read(self):
        with mock.patch.object(sync_comments, "PAGE", 2):
            code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertEqual(len(self.copy()["comments"]), 5)
        self.assertEqual(len(self.copy()["history"]), 7)
        self.assertIn("/rest/api/3/issue/{key}/comment  x3", text)
        self.assertIn("/rest/api/3/issue/{key}/changelog  x5", text)


class ASecondSyncAddsNothing(Case):
    def test_the_files_are_byte_for_byte_the_same_and_are_not_even_written(self):
        self.sync(T1)
        before = self.files()
        code, text = self.sync(T2)
        self.assertEqual(code, 0)
        self.assertEqual(self.files(), before)
        self.assertIn("RESULT: NOTHING TO DO", text)
        self.assertIn("added:                          0", text)
        self.assertEqual(text.count("not written: byte for byte the same"), 2)

    def test_ten_more_syncs_add_nothing(self):
        self.sync(T1)
        before = self.files()
        for hour in range(10):
            self.sync("2026-11-08T%02d:00:00Z" % hour)
        self.assertEqual(self.files(), before)
        self.assertEqual(len(self.headings()), 5)
        self.assertEqual(len(self.copy()["history"]), 7)

    def test_after_a_change_is_taken_in_the_next_sync_adds_nothing_again(self):
        self.sync(T1)
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, corrected.", "2026-11-08T08:00:00.000+0000")
            jira.add("Made-up new comment.", "2026-11-08T09:00:00.000+0000")
            jira.delete("31004")
            jira.change("status", "In Progress", "In Review", "2026-11-08T10:00:00.000+0000")
        self.sync(T3)
        before = self.files()
        code, text = self.sync(T4)
        self.assertEqual(self.files(), before)
        self.assertIn("RESULT: NOTHING TO DO", text)
        self.assertIn("marked by an earlier sync, still kept: 1  [31004]", text)


class AnEditedComment(Case):
    def edit(self, by="other"):
        self.sync(T1)
        self.old = self.comment("31002")["text"]
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, corrected: two days, not one.", "2026-11-08T08:00:00.000+0000", by)
        return self.sync(T3)

    def test_the_text_is_replaced_in_place_and_the_old_text_is_gone(self):
        code, text = self.edit()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.comment("31002")["text"], "Made-up comment, corrected: two days, not one.")
        self.assertEqual(len(self.copy()["comments"]), 5)
        self.assertEqual(self.headings().count("### Comment 31002"), 1)
        self.assertNotIn(self.old, self.page())
        self.assertNotIn(self.old, json.dumps(self.copy()))
        self.assertIn("corrected: two days, not one.", self.page())
        self.assertEqual([c["id"] for c in self.copy()["comments"]], ["31001", "31002", "31003", "31004", "31005"], "the comment kept its place")

    def test_the_change_is_noted_with_when_how_long_and_a_checksum_of_what_was_replaced(self):
        _, text = self.edit()
        edits = self.comment("31002")["edits"]
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0], {"noticed": T3, "jira_says_edited": "2026-11-08T08:00:00Z", "by": "someone else",
                                    "replaced_text_checksum": sync_comments.checksum(self.old), "seconds_until_noticed": 4 * 3600})
        self.assertIn("edited in Jira, updated in place: 1  [31002]", text)
        self.assertIn("**Edited in Jira** at 2026-11-08T08:00:00Z, by someone else. Noticed by the sync of %s, 4 hours later." % T3, self.page())
        self.assertIn(sync_comments.checksum(self.old), self.page())

    def test_an_edit_by_the_author_is_said_to_be_that(self):
        self.edit(by="author")
        self.assertEqual(self.comment("31002")["edits"][0]["by"], "its author")

    def test_a_second_edit_is_a_second_note_under_the_same_comment(self):
        self.edit()
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, corrected again.", "2026-11-09T08:00:00.000+0000", "author")
        self.sync(T4)
        self.assertEqual([e["by"] for e in self.comment("31002")["edits"]], ["someone else", "its author"])
        self.assertEqual(self.headings().count("### Comment 31002"), 1)

    def test_two_edits_between_two_syncs_are_seen_as_one(self):
        """A stated limit: only the latest text is seen."""
        self.sync(T1)
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, first correction.", "2026-11-08T07:00:00.000+0000")
            jira.edit("31002", "Made-up comment, second correction.", "2026-11-08T08:00:00.000+0000")
        self.sync(T3)
        self.assertEqual(len(self.comment("31002")["edits"]), 1)
        self.assertNotIn("first correction", self.page())

    def test_a_comment_already_edited_when_first_copied_says_so(self):
        with self.jira() as jira:
            jira.edit("31003", "Made-up comment, edited before any sync.", "2026-11-06T08:00:00.000+0000", "other")
        self.sync(T1)
        self.assertEqual(self.comment("31003")["edited_before_first_sync"], {"by": "someone else", "jira_says_edited": "2026-11-06T08:00:00Z"})
        self.assertEqual(self.comment("31003")["edits"], [])
        self.assertIn("Already edited in Jira when first copied, by someone else. Jira's edit time then: 2026-11-06T08:00:00Z.", self.page())
        with self.jira() as jira:           # a later edit must not rewrite what that line says (a reader's find)
            jira.edit("31003", "Made-up comment, edited again.", "2026-11-08T08:00:00.000+0000", "author")
        self.sync(T3)
        self.assertIn("Already edited in Jira when first copied, by someone else. Jira's edit time then: 2026-11-06T08:00:00Z.", self.page())
        self.assertIsNone(self.comment("31001")["edited_before_first_sync"])

    def test_a_new_edit_time_with_the_same_body_is_not_called_an_edit(self):
        self.sync(T1)
        with self.jira() as jira:
            jira.data["comments"][0]["updated"] = "2026-11-08T08:00:00.000+0000"
        code, text = self.sync(T3)
        self.assertIn("same words, changed in Jira in some other way: 1  [31001]", text)
        self.assertIn("edited in Jira, updated in place: 0", text)
        self.assertEqual(self.comment("31001")["edits"], [])
        self.assertEqual(self.comment("31001")["other_changes"], [{"noticed": T3, "jira_says_edited": "2026-11-08T08:00:00Z"}])
        self.assertIn("Changed in Jira at 2026-11-08T08:00:00Z with the same words", self.page())


class ANewComment(Case):
    def test_it_is_added_once(self):
        self.sync(T1)
        with self.jira() as jira:
            new = jira.add("Made-up new comment.", "2026-11-08T09:00:00.000+0000")
        code, text = self.sync(T3)
        self.assertIn("added:                          1  [%s]" % new, text)
        self.sync(T4)
        self.sync(T4)
        self.assertEqual(self.headings().count("### Comment %s" % new), 1)
        self.assertEqual(len(self.copy()["comments"]), 6)
        self.assertEqual(self.comment(new)["first_synced"], T3)


class ADeletedComment(Case):
    def delete(self):
        self.sync(T1)
        self.text_before = self.comment("31004")["text"]
        with self.jira() as jira:
            jira.delete("31004")
        return self.sync(T3)

    def test_it_is_marked_and_kept_with_its_last_text(self):
        code, text = self.delete()
        self.assertEqual(code, 0, text)
        comment = self.comment("31004")
        self.assertEqual((comment["in_jira"], comment["not_returned_since"], comment["text"]), (False, T3, self.text_before))
        self.assertIn("NOT RETURNED BY JIRA ANY MORE, marked now and kept: 1  [31004]", text)
        self.assertIn("this tool cannot tell which", text)
        page = self.page()
        at = page.index("### Comment 31004")
        section = page[at:page.index("### Comment 31005")]
        self.assertIn("**NOT RETURNED BY JIRA ANY MORE. First found missing by the sync of %s.**" % T3, section)
        self.assertIn(self.text_before, section)
        self.assertEqual(len(self.copy()["comments"]), 5)

    def test_later_syncs_do_not_take_it_out_or_mark_it_again(self):
        self.delete()
        before = self.files()
        for now in (T4, "2026-11-10T12:00:00Z", "2026-11-11T12:00:00Z"):
            code, text = self.sync(now)
            self.assertIn("marked now and kept: 0", text)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.comment("31004")["not_returned_since"], T3)

    def test_the_other_comments_are_not_marked(self):
        self.delete()
        self.assertEqual([c["id"] for c in self.copy()["comments"] if not c["in_jira"]], ["31004"])
        self.assertEqual(self.page().count("NOT RETURNED BY JIRA ANY MORE"), 1)

    def test_every_comment_gone_at_once_marks_every_one_and_keeps_every_text(self):
        """All comments hidden from the account looks like this too. The words say so, and nothing is thrown away."""
        self.sync(T1)
        texts = [c["text"] for c in self.copy()["comments"]]
        with self.jira() as jira:
            jira.data["comments"] = []
        code, text = self.sync(T3)
        self.assertEqual(code, 0)
        self.assertIn("marked now and kept: 5", text)
        self.assertEqual([c["text"] for c in self.copy()["comments"]], texts)
        self.assertIn("hidden from the account", text)

    def test_a_marked_comment_that_jira_returns_again_is_unmarked_and_says_so(self):
        self.sync(T1)
        with self.jira() as jira:
            gone = [c for c in jira.data["comments"] if c["id"] == "31004"][0]
            jira.delete("31004")
        self.sync(T3)
        with self.jira() as jira:
            jira.data["comments"].insert(3, gone)
        code, text = self.sync(T4)
        self.assertIn("marked earlier and returned by Jira again: 1  [31004]", text)
        self.assertTrue(self.comment("31004")["in_jira"])
        self.assertIn("Returned by Jira again as of the sync of %s" % T4, self.page())
        self.assertEqual(len(self.copy()["comments"]), 5)


class NothingChangesUnlessEverythingWasRead(Case):
    """A page that fails must not look like deleted comments."""

    def refused_and_untouched(self, faults, page=2):
        self.sync(T1)
        before = self.files()
        with self.jira() as jira:
            jira.data["faults"] = faults
            jira.data["asked"] = {"comments": 0, "history": 0}
            jira.add("Made-up new comment that must not be taken in by a failed sync.", "2026-11-08T09:00:00.000+0000")
        with mock.patch.object(sync_comments, "PAGE", page):
            code, text = self.sync(T3)
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED", text)
        self.assertNotIn("RESULT:", text)
        self.assertEqual(self.files(), before)
        self.assertTrue(all(c["in_jira"] for c in self.copy()["comments"]))
        return text

    def test_a_page_of_comments_that_fails(self):
        for n in (1, 2, 3):
            with self.subTest(n):
                self.refused_and_untouched({"fail_comments_page": n})
                self.tearDown()
                self.setUp()

    def test_a_page_of_history_that_fails(self):
        for n in (1, 3, 5):
            with self.subTest(n):
                self.refused_and_untouched({"fail_history_page": n})
                self.tearDown()
                self.setUp()

    def test_fewer_comments_arriving_than_jira_says_there_are(self):
        text = self.refused_and_untouched({"short_total": 1})
        self.assertIn("Jira said the story has 7 comments and 6 arrived", text)

    def test_a_comment_that_comes_twice(self):
        text = self.refused_and_untouched({"repeat_comment": True})
        self.assertIn("twice", text)

    def test_jira_that_cannot_be_reached(self):
        self.sync(T1)
        before = self.files()
        with mock.patch.object(fake_jira.FakeJira, "get", side_effect=OSError("made up")):
            code, text = self.sync(T3)
        self.assertEqual(code, 1)
        self.assertIn("could not be reached", text)
        self.assertEqual(self.files(), before)

    def test_answers_that_are_not_what_was_asked_for(self):
        self.sync(T1)
        before = self.files()
        real = fake_jira.FakeJira.get
        cases = {
            "a comment with a time that cannot be read": lambda body: body["comments"][0].update(created="last week"),
            "a comment with an identifier that is not digits": lambda body: body["comments"][0].update(id="abc"),
            "a total that is not a number": lambda body: body.update(total="5"),
            "a total of true": lambda body: body.update(total=True),
            "comments that is not a list": lambda body: body.update(comments={}),
        }
        for what, spoil in cases.items():
            with self.subTest(what):
                def get(fake, path, params=None, spoil=spoil):
                    status, headers, body = real(fake, path, params)
                    if path.endswith("/comment"):
                        spoil(body)
                    return status, headers, body
                with mock.patch.object(fake_jira.FakeJira, "get", get):
                    code, text = self.sync(T3)
                self.assertEqual(code, 1, text)
                self.assertEqual(self.files(), before)

    def test_a_total_of_true_is_not_one_even_when_one_comment_arrives(self):
        with self.jira() as jira:
            jira.data["comments"] = jira.data["comments"][:1]
        real = fake_jira.FakeJira.get

        def get(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            if path.endswith("/comment"):
                body["total"] = True
            return status, headers, body
        with mock.patch.object(fake_jira.FakeJira, "get", get):
            code, text = self.sync(T1)
        self.assertEqual(code, 1, text)
        self.assertEqual(os.listdir(self.out), ["sample.notes.md"])

    def test_a_status_that_is_not_200_is_not_a_list_whatever_its_body(self):
        self.sync(T1)
        before = self.files()
        real = fake_jira.FakeJira.get
        with mock.patch.object(fake_jira.FakeJira, "get", lambda fake, path, params=None: ((503,) + real(fake, path, params)[1:]) if path.endswith("/comment") else real(fake, path, params)):
            code, text = self.sync(T3)
        self.assertEqual(code, 1)
        self.assertEqual(self.files(), before)

    def test_a_story_that_is_not_there_or_has_moved(self):
        code, text = self.main("sync", "--source", "fake", "--issue", "DEMO-8", "--out-dir", self.out, "--name", "sample", "--state", self.state)
        self.assertEqual(code, 1)
        self.assertIn("404", text)
        real = fake_jira.FakeJira.get

        def moved(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            if "key" in body:
                body["key"] = "OTHER-3"
            return status, headers, body
        with mock.patch.object(fake_jira.FakeJira, "get", moved):
            code, text = self.sync()
        self.assertEqual(code, 1)
        self.assertIn("moved or renamed", text)
        self.assertEqual(sorted(os.listdir(self.out)), ["sample.notes.md"])


class TheHistory(Case):
    def test_only_the_kinds_listed_as_material_are_kept(self):
        code, text = self.sync()
        history = self.copy()["history"]
        self.assertEqual([(h["id"], h["kind"]) for h in history], [("41001:0", "status"), ("41003:0", "assignee"), ("41004:0", "priority"), ("41006:0", "duedate"),
                                                                 ("41007:0", "summary"), ("41008:0", "link"), ("41010:1", "description")])
        self.assertTrue(set(h["kind"] for h in history) <= set(sync_comments.MATERIAL_NAMES))
        kept = json.dumps(self.copy()) + self.page()
        for noise in ("Ranked higher", "Ranked lower", "quarter-end", "Made-up Sprint", "made-up.png", "3600", "Story Points"):
            self.assertNotIn(noise, kept, "%s is noise or unlisted and was kept" % noise)

    def test_what_is_kept_of_each_kind(self):
        self.sync()
        by_kind = {h["kind"]: (h["from"], h["to"]) for h in self.copy()["history"]}
        self.assertEqual(by_kind, {"status": ("To Do", "In Progress"), "assignee": ("", "reassigned"), "priority": ("Medium", "High"),
                                   "duedate": ("2026-11-18", "2026-11-25"), "summary": ("", "changed"), "link": ("", "link added: DEMO-9"), "description": ("", "changed")})

    def test_no_person_title_or_description_is_kept(self):
        self.sync()
        kept = json.dumps(self.copy()) + self.page()
        for private in ("Ana Example", "Ben Example", "Made-up Person", "acct-", "Made-up old title", "Made-up new title", "Made-up old description", "Made-up new description"):
            self.assertNotIn(private, kept)

    def test_noise_is_counted_and_a_field_on_neither_list_is_named_as_unlisted(self):
        _, text = self.sync()
        self.assertIn("noise, left out:                6 (attachment x1, labels x1, rank x2, sprint x1, timespent x1)", text)
        self.assertIn("UNLISTED, on neither list, not kept: 1 (Story Points x1)", text)
        self.assertIn("HISTORY. Jira lists 14 changes", text)

    def test_a_material_change_is_added_once_and_a_noise_change_writes_nothing(self):
        self.sync(T1)
        with self.jira() as jira:
            new = jira.change("status", "In Progress", "In Review", "2026-11-08T10:00:00.000+0000")
        _, text = self.sync(T3)
        self.assertIn("of which new to the copy: 1  [%s:0]" % new, text)
        self.assertIn("status: In Progress -> In Review. Noticed 2 hours later.", text)
        before = self.files()
        with self.jira() as jira:
            jira.change("Rank", "", "Ranked higher", "2026-11-09T10:00:00.000+0000", "customfield_10019")
            jira.change("labels", "quarter-end", "quarter-end urgent", "2026-11-09T10:01:00.000+0000")
            jira.change("Team", "", "Made-up Team", "2026-11-09T10:02:00.000+0000", "customfield_10001")
        code, text = self.sync(T4)
        self.assertEqual(self.files(), before)
        self.assertIn("RESULT: NOTHING TO DO", text)
        self.assertIn("Team x1", text)
        self.assertEqual(sum(1 for h in self.copy()["history"] if h["id"] == new + ":0"), 1)

    def test_assigned_and_unassigned_and_a_link_removed(self):
        self.sync(T1)
        with self.jira() as jira:
            jira.change("assignee", "Ben Example", "", "2026-11-08T10:00:00.000+0000")
            jira.change("assignee", "", "Cho Example", "2026-11-08T10:01:00.000+0000")
            jira.change("Link", "This issue blocks DEMO-9", "", "2026-11-08T10:02:00.000+0000", "issuelinks")
            jira.change("duedate", "2026-11-25", "", "2026-11-08T10:03:00.000+0000")
        self.sync(T3)
        self.assertEqual([h["to"] for h in self.copy()["history"][-4:]], ["unassigned", "assigned", "link removed: DEMO-9", "no date"])
        self.assertNotIn("Cho Example", json.dumps(self.copy()) + self.page())

    def test_the_time_until_a_change_was_noticed(self):
        self.sync(T1)
        first = self.copy()["history"][0]
        self.assertEqual((first["at"], first["noticed"], first["seconds_until_noticed"]), ("2026-11-01T10:00:00Z", T1, 5 * 86400 + 23 * 3600))
        self.assertIn("| 5 days 23 hours |", self.page())
        self.assertEqual([sync_comments.span(s) for s in (0, 59, 60, 3600, 3660, 86400, 90000, -5)],
                         ["under a minute", "under a minute", "1 minute", "1 hour", "1 hour 1 minute", "1 day", "1 day 1 hour", "dated after this sync's clock"])

    def test_a_status_name_with_markup_in_it_is_cleaned(self):
        self.sync(T1)
        with self.jira() as jira:
            jira.change("status", "In Progress", "Done | <b>x</b>‮", "2026-11-08T10:00:00.000+0000")
        self.sync(T3)
        self.assertEqual(self.copy()["history"][-1]["to"], "Done ? ?b?x?/b??")


class TheRules(Case):
    def test_the_rules_document_is_what_the_tool_writes_from_its_lists(self):
        with open(RULES_FILE, encoding="utf-8") as f:
            self.assertEqual(f.read(), sync_comments.rules_text())

    def test_every_kind_on_either_list_is_in_the_document_and_no_kind_is_on_both(self):
        text = sync_comments.rules_text()
        for name in sync_comments.MATERIAL_NAMES + sync_comments.NOISE_NAMES:
            self.assertIn("| `%s` |" % name, text)
        self.assertEqual(set(sync_comments.MATERIAL_NAMES) & set(sync_comments.NOISE_NAMES), set())
        self.assertEqual(len(set(sync_comments.MATERIAL_NAMES + sync_comments.NOISE_NAMES)), len(sync_comments.MATERIAL) + len(sync_comments.NOISE))

    def test_rank_is_noise_and_status_is_material(self):
        self.assertIn("rank", sync_comments.NOISE_NAMES)
        self.assertIn("status", sync_comments.MATERIAL_NAMES)

    def test_the_rules_can_be_written_to_a_file(self):
        target = os.path.join(self.folder, "rules.md")
        code, _ = self.main("rules", "--write", target)
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as f:
            self.assertEqual(f.read(), sync_comments.rules_text())


class TheNotesFile(Case):
    def test_it_is_unchanged_in_bytes_time_and_place_through_every_kind_of_sync(self):
        before = self.files()["sample.notes.md"]
        self.sync(T1)
        self.sync(T2)
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, corrected.", "2026-11-08T08:00:00.000+0000")
            jira.add("Made-up new comment.", "2026-11-08T09:00:00.000+0000")
            jira.delete("31004")
        code, text = self.sync(T3)
        self.assertEqual(self.files()["sample.notes.md"], before)
        self.assertIn("UNCHANGED. This tool never writes it", text)

    def test_it_is_never_opened_for_writing(self):
        opened = []
        real_open = builtins.open

        def watching(path, mode="r", *args, **kwargs):
            if str(path).endswith(".notes.md"):
                opened.append(mode)
            return real_open(path, mode, *args, **kwargs)
        with mock.patch.object(builtins, "open", watching), mock.patch.object(sync_comments.os, "replace", side_effect=lambda a, b: self.assertFalse(b.endswith(".notes.md")) or os.rename(a, b)):
            self.sync(T1)
        self.assertEqual(set(opened), {"rb"})

    def test_when_there_is_no_notes_file_none_is_made(self):
        os.unlink(self.notes)
        code, text = self.sync(T1)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(self.out)), ["sample.json", "sample.md"])
        self.assertIn("before not there   after not there", text)

    def test_the_sync_prints_its_checksum_before_and_after(self):
        import hashlib
        _, text = self.sync(T1)
        digest = hashlib.sha256(NOTES.encode("utf-8")).hexdigest()
        self.assertIn("before %s   after %s" % (digest, digest), text)

    def test_a_notes_file_changed_by_something_else_during_the_sync_is_reported(self):
        real = sync_comments.read_story

        def meddle(conn, key):
            with open(self.notes, "a", encoding="utf-8") as f:
                f.write("someone else wrote this\n")
            return real(conn, key)
        with mock.patch.object(sync_comments, "read_story", meddle):
            code, text = self.sync(T1)
        self.assertEqual(code, 1)
        self.assertIn("IT CHANGED DURING THE SYNC", text)

    def test_a_copy_or_page_that_is_a_link_to_the_notes_is_refused(self):
        for name in ("sample.json", "sample.md"):
            with self.subTest(name):
                os.symlink(self.notes, os.path.join(self.out, name))
                code, text = self.sync(T1)
                self.assertEqual(code, 1, text)
                with open(self.notes, encoding="utf-8") as f:
                    self.assertEqual(f.read(), NOTES)
                os.unlink(os.path.join(self.out, name))
        os.link(self.notes, os.path.join(self.out, "sample.md"))
        code, text = self.sync(T1)
        self.assertEqual(code, 1, text)
        with open(self.notes, encoding="utf-8") as f:
            self.assertEqual(f.read(), NOTES)

    def test_the_log_may_not_be_the_notes_or_one_of_the_two_files(self):
        for name in ("sample.notes.md", "sample.json", "sample.md"):
            code, text = self.sync(T1, extra=["--log", os.path.join(self.out, name)])
            self.assertEqual(code, 1, text)
        with open(self.notes, encoding="utf-8") as f:
            self.assertEqual(f.read(), NOTES)
        self.assertEqual(os.listdir(self.out), ["sample.notes.md"])


class OtherPeoplesText(Case):
    def test_a_comment_cannot_close_its_fence_or_forge_a_heading(self):
        nasty = "~~~\n### Comment 99999\n\n**NOT RETURNED BY JIRA ANY MORE.**\n~~~~~~\n## Material changes"
        with self.jira() as jira:
            new = jira.add(nasty, "2026-11-06T12:00:00.000+0000")
        self.sync(T1)
        page = self.page()
        fences = [line for line in page.split("\n") if line.startswith("~~~~~~~")]
        self.assertEqual(len(fences), 2, "the comment is inside one fence longer than any run of ~ in it")
        self.assertEqual(self.copy()["comments"][-1]["id"], new)
        self.assertEqual(self.comment(new)["text"], nasty)
        # everything after the opening long fence up to the closing one is the comment, whatever it says
        start = page.index(fences[0])
        end = page.index("\n" + fences[1].split("text")[0] + "\n", start + 1)
        self.assertIn("### Comment 99999", page[start:end])
        self.assertNotIn("### Comment 99999", page[:start] + page[end:])

    def test_unseen_characters_in_a_comment_are_replaced(self):
        with self.jira() as jira:
            new = jira.add("Made-up comment with a hidden‮ mark and a zero​width one.", "2026-11-06T12:00:00.000+0000")
        self.sync(T1)
        self.assertEqual(self.comment(new)["text"], "Made-up comment with a hidden? mark and a zero?width one.")

    def test_a_mention_is_kept_as_a_person_and_other_pieces_by_their_kind(self):
        document = {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Thanks "}, {"type": "mention", "attrs": {"id": "acct-ana", "text": "@Ana Example"}}, {"type": "text", "text": ", see below."}]},
            {"type": "bulletList", "content": [{"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "one"}]}]}]},
            {"type": "mediaSingle", "attrs": {}}, {"type": "paragraph", "content": [{"type": "text", "text": "a"}, {"type": "hardBreak"}, {"type": "text", "text": "b"}]}]}
        text = sync_comments.text_of(document)
        self.assertIn("Thanks [a person], see below.", text)
        self.assertNotIn("Ana", text)
        self.assertIn("one", text)
        self.assertIn("[mediaSingle]", text)
        self.assertIn("a\nb", text)

    def test_a_very_long_comment_is_cut_and_says_so(self):
        with self.jira() as jira:
            new = jira.add("Made-up " + "x" * 9000, "2026-11-06T12:00:00.000+0000")
        self.sync(T1)
        self.assertEqual(len(self.comment(new)["text"]), sync_comments.TEXT_LIMIT)
        self.assertTrue(self.comment(new)["text_cut"])
        self.assertIn("was cut", self.page())

    def test_the_output_never_prints_a_comments_text(self):
        _, first = self.sync(T1)
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, corrected.", "2026-11-08T08:00:00.000+0000")
            jira.delete("31004")
        _, second = self.sync(T3)
        self.assertNotIn("Made-up comment", first + second)
        self.assertNotIn("archived", first + second)


class TheCopyOnDisk(Case):
    def test_a_copy_changed_by_hand_into_something_else_is_left_alone(self):
        self.sync(T1)
        path = os.path.join(self.out, "sample.json")
        twice = self.copy()
        twice["comments"].append(twice["comments"][0])
        for what, text in (("not JSON", "{"), ("another format", json.dumps({"format": "x"})), ("a comment twice", json.dumps(twice)), ("an empty file", "")):
            with self.subTest(what):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                code, out = self.sync(T3)
                self.assertEqual(code, 1, out)
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), text)

    def test_a_copy_of_another_story_or_another_jira_is_not_mixed_in(self):
        self.sync(T1)
        path = os.path.join(self.out, "sample.json")
        for field, value in (("story", {"key": "DEMO-7", "id": "99999"}), ("source", "live"), ("site_fingerprint", "0123456789abcdef")):
            with self.subTest(field):
                copy = self.copy()
                copy[field] = value
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(copy, f)
                before = self.files()
                code, text = self.sync(T3)
                self.assertEqual(code, 1, text)
                self.assertIn("another story, or was made from another Jira", text)
                self.assertEqual(self.files(), before)
                os.unlink(path)
                self.sync(T1)

    def test_the_page_is_put_right_from_the_copy_if_it_was_changed_or_lost(self):
        self.sync(T1)
        good = self.page()
        with open(os.path.join(self.out, "sample.md"), "w", encoding="utf-8") as f:
            f.write("scribbled over")
        code, text = self.sync(T2)
        self.assertEqual(self.page(), good)
        os.unlink(os.path.join(self.out, "sample.md"))
        self.sync(T2)
        self.assertEqual(self.page(), good)

    def test_a_write_that_fails_says_which_file_is_behind_and_the_next_sync_mends_it(self):
        calls = []
        real = sync_comments.write_file

        def failing(path, text):
            calls.append(path)
            if path.endswith(".md"):
                raise OSError("made up")
            return real(path, text)
        with mock.patch.object(sync_comments, "write_file", failing):
            code, text = self.sync(T1)
        self.assertEqual(code, 1)
        self.assertIn("NOT FINISHED", text)
        self.assertIn("The copy was written and the page was not", text)
        self.assertNotIn("RESULT:", text)
        code, text = self.sync(T1)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.headings()), 5)

    def test_no_temporary_file_is_left(self):
        self.sync(T1)
        with mock.patch.object(sync_comments.os, "replace", side_effect=OSError("made up")):
            code, _ = self.sync(T3, name="other")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(os.listdir(self.out)), ["sample.json", "sample.md", "sample.notes.md"])

    def test_names_and_folders_that_are_not_allowed(self):
        for name in ("Sample", "../x", "a b", "", "x.json"):
            with self.subTest(name):
                code, text = self.sync(T1, name=name)
                self.assertEqual(code, 1, text)
        code, text = self.main("sync", "--source", "fake", "--issue", "DEMO-7", "--out-dir", os.path.join(self.folder, "missing"), "--name", "sample", "--state", self.state)
        self.assertEqual(code, 1)
        code, text = self.main("sync", "--source", "fake", "--issue", "DEMO-7/comment", "--out-dir", self.out, "--name", "sample", "--state", self.state)
        self.assertEqual(code, 1)
        self.assertEqual(os.listdir(self.out), ["sample.notes.md"])

    def test_something_unforeseen_is_a_refusal_and_not_a_crash(self):
        with mock.patch.object(sync_comments, "read_history", side_effect=RuntimeError("unforeseen")):
            code, text = self.sync(T1)
        self.assertEqual(code, 1)
        self.assertIn("did not foresee (RuntimeError)", text)
        self.assertEqual(os.listdir(self.out), ["sample.notes.md"])


class Response:
    def __init__(self, body):
        self.status, self.headers, self._body = 200, {}, json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Opener:
    """Stands where the network would be for a live connection. It answers from the made-up Jira and keeps each request."""

    def __init__(self, fake, fail=None):
        self.fake, self.requests, self.fail = fake, [], fail

    def open(self, request, timeout=None):
        import urllib.error
        self.requests.append(request)
        if self.fail and len(self.requests) == self.fail[0]:
            raise urllib.error.HTTPError(request.full_url, self.fail[1], "made up", {}, io.BytesIO(b"{}"))
        url = urllib.parse.urlparse(request.full_url)
        _, _, body = self.fake.get(url.path, dict(urllib.parse.parse_qsl(url.query)))
        return Response(body)


class ALiveSync(Case):
    ENV = {"JIRA_BASE_URL": "https://real.example.invalid", "JIRA_EMAIL": "someone@example.invalid", "JIRA_API_TOKEN": MADE_UP}

    def setUp(self):
        Case.setUp(self)
        self.private = os.path.join(self.folder, "local-data", "jira")
        os.makedirs(self.private)

    def live(self, out_dir=None, fail=None, now=T1):
        del sync_comments.LINES[:]
        opener = Opener(fake_jira.FakeJira.open(self.fake_path), fail)
        with mock.patch.dict(os.environ, self.ENV):
            conn, secrets = sync_comments.make_live(opener)
        args = argparse.Namespace(issue="DEMO-7", out_dir=out_dir or self.private, name="real", log=None)
        try:
            code = sync_comments.cmd_sync(args, conn, True, now)
        except sync_comments.Refused as refusal:
            return 1, "REFUSED: %s" % refusal, opener, conn, secrets
        return code, "\n".join(sync_comments.LINES), opener, conn, secrets

    def test_every_request_is_a_get_with_no_body_to_one_of_three_places(self):
        code, text, opener, conn, secrets = self.live()
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(set((r.get_method(), r.data, urllib.parse.urlparse(r.full_url).path) for r in opener.requests)),
                         [("GET", None, "/rest/api/3/issue/DEMO-7"), ("GET", None, "/rest/api/3/issue/DEMO-7/changelog"), ("GET", None, "/rest/api/3/issue/DEMO-7/comment")])
        self.assertIn("Every one was a GET with no body", text)
        self.assertTrue(conn.only_gets())
        for request in opener.requests:
            self.assertTrue(request.get_header("Authorization").startswith("Basic "))
            self.assertTrue(request.full_url.startswith("https://real.example.invalid/"))

    def test_the_connection_builds_nothing_else(self):
        with mock.patch.dict(os.environ, self.ENV):
            conn, _ = sync_comments.make_live(Opener(None))
        for path in ("/rest/api/3/issue/DEMO-7/comment/31001/properties", "/rest/api/3/issue/DEMO-7/comment/abc", "/rest/api/3/myself", "/rest/api/3/issue/DEMO-7/../../x", "/rest/api/3/issue"):
            with self.assertRaises(sync_comments.Refused):
                conn._get(path, {})
        self.assertFalse(hasattr(conn, "post") or hasattr(conn, "put") or hasattr(conn, "delete"))

    def test_a_request_that_was_not_a_plain_get_is_not_called_one(self):
        conn = sync_comments.Connection(None, "x")
        for sent in ([("POST", "/x")], [("GET WITH A BODY", "/x")], [("?", "/x")], [("DELETE", "/x")]):
            conn.sent = sent
            self.assertFalse(conn.only_gets(), sent)
        conn.sent = [("GET", "/x")]
        self.assertTrue(conn.only_gets())

    def test_a_live_sync_writes_only_inside_a_folder_named_local_data(self):
        code, text, opener, _, _ = self.live(out_dir=self.out)
        self.assertEqual(code, 1)
        self.assertIn("local-data", text)
        self.assertEqual(opener.requests, [], "Jira was asked before the place was refused")
        self.assertEqual(os.listdir(self.out), ["sample.notes.md"])
        code, text, _, _, _ = self.live()
        self.assertEqual(sorted(os.listdir(self.private)), ["real.json", "real.md"])

    def test_no_credential_site_address_or_comment_text_is_in_the_output(self):
        code, text, _, _, secrets = self.live()
        self.assertEqual(len(secrets), 3)
        for secret in secrets + ["real.example.invalid", "Made-up comment", "Made-up Person", "acct-"]:
            self.assertNotIn(secret, text)
        self.assertIn(sync_comments.site_fingerprint("real.example.invalid"), text)

    def test_a_real_servers_refusals_leave_the_copy_as_it_was(self):
        self.live()
        with open(os.path.join(self.private, "real.json"), "rb") as f:
            before = f.read()
        with open(self.fake_path, encoding="utf-8") as f:
            data = json.load(f)
        data["comments"] = data["comments"][:2]
        with open(self.fake_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        for status in (401, 403, 404, 429, 500, 302):
            for on in (1, 2, 3):
                with self.subTest(status=status, on=on):
                    code, text, _, _, _ = self.live(fail=(on, status), now=T3)
                    self.assertEqual(code, 1, text)
                    with open(os.path.join(self.private, "real.json"), "rb") as f:
                        self.assertEqual(f.read(), before)

    def test_a_real_servers_refusal_is_read_for_what_it_says(self):
        code, text, _, _, _ = self.live(fail=(1, 401))
        self.assertIn("rejected the credentials (401)", text)
        code, text, _, _, _ = self.live(fail=(1, 404))
        self.assertIn("404", text)
        code, text, _, _, _ = self.live(fail=(2, 500))
        self.assertIn("did not list the story's comments (status 500)", text)

    def test_the_made_up_jiras_switches_are_refused_for_a_real_one(self):
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(sync_comments, "make_live", side_effect=AssertionError("a connection was made")):
            for extra in (["--state", self.state], ["--pretend-now", T1]):
                code, text = self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real", *extra)
                self.assertEqual(code, 1)
                self.assertIn("for the made-up Jira only", text)

    def test_without_the_environment_variables_nothing_is_asked(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code, text = self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real")
        self.assertEqual(code, 1)
        self.assertIn("JIRA_BASE_URL is not set", text)

    def test_a_credential_in_the_output_stops_the_output(self):
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(sync_comments, "make_live", return_value=(sync_comments.Connection(None, "x"), [MADE_UP])), \
                mock.patch.object(sync_comments, "cmd_sync", side_effect=lambda *a, **k: sync_comments.say("leaked " + MADE_UP) or 0):
            code, text = self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real")
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertIn("STOPPED", text)

    def test_the_saved_output_has_the_sites_address_taken_out(self):
        log = os.path.join(self.folder, "log.txt")
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(sync_comments, "make_live", return_value=(sync_comments.Connection(None, "real.example.invalid"), [])), \
                mock.patch.object(sync_comments, "cmd_sync", side_effect=lambda *a, **k: sync_comments.say("see https://real.example.invalid/browse and real.example.invalid") or 0):
            self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real", "--log", log)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn("real.example.invalid", saved)
        self.assertEqual(saved.count(sync_comments.SITE_MARK), 2)


class TheMadeUpJiraItself(Case):
    def test_the_sync_tool_cannot_change_it(self):
        """The sync asks through `get`. After a sync, the made-up Jira's comments and history are what they were."""
        with open(self.fake_path, encoding="utf-8") as f:
            before = json.load(f)
        self.sync(T1)
        with open(self.fake_path, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual((before["comments"], before["history"]), (after["comments"], after["history"]))

    def test_its_own_commands_change_it(self):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            fake_jira.main(["edit", "--state", self.state, "--id", "31002", "--text", "Made-up edit.", "--by", "other", "--at", "2026-11-08T08:00:00.000+0000"])
            fake_jira.main(["add", "--state", self.state, "--text", "Made-up addition.", "--at", "2026-11-08T09:00:00.000+0000"])
            fake_jira.main(["delete", "--state", self.state, "--id", "31004"])
            fake_jira.main(["change", "--state", self.state, "--field", "status", "--from", "In Progress", "--to", "Done", "--at", "2026-11-08T10:00:00.000+0000"])
        code, text = self.sync(T3)
        self.assertIn("RESULT: UP TO DATE. 5 added, 0 edited in place, 0 marked as not returned, 8 material changes added.", text)
        self.assertEqual([c["id"] for c in self.copy()["comments"]], ["31001", "31002", "31003", "31005", "31006"])
        self.assertEqual(self.comment("31002")["edited_before_first_sync"]["by"], "someone else")


class WhatTheReadersFound(Case):
    """Each of these is something an independent reader found in the first version, or showed the tests would miss."""

    def notes_now(self):
        with open(self.notes, encoding="utf-8") as f:
            return f.read()

    # ------------------------------------------------ the notes file could be written over

    def test_the_log_cannot_be_the_notes_under_another_spelling_or_another_name(self):
        other_name = os.path.join(self.folder, "innocent.txt")
        os.link(self.notes, other_name)
        link = os.path.join(self.folder, "link.txt")
        os.symlink(self.notes, link)
        for what, log in (("capitals", os.path.join(self.out, "SAMPLE.NOTES.MD")), ("a second name for the same file", other_name), ("a link", link),
                          ("a notes file of another name", os.path.join(self.out, "other.notes.md")), ("a path with a dot in it", os.path.join(self.out, ".", "sample.notes.md"))):
            with self.subTest(what):
                code, text = self.sync(T1, extra=["--log", log])
                self.assertEqual(code, 1, text)
                self.assertIn("REFUSED: --log:", text)
                self.assertEqual(self.notes_now(), NOTES)
        os.unlink(other_name)
        self.assertEqual(sorted(os.listdir(self.out)), ["sample.notes.md"])

    def test_the_log_cannot_be_the_copy_or_the_page_under_another_spelling(self):
        self.sync(T1)
        before = self.files()
        for name in ("SAMPLE.JSON", "Sample.md"):
            code, text = self.sync(T3, extra=["--log", os.path.join(self.out, name)])
            self.assertEqual(code, 1, text)
        self.assertEqual(self.files(), before)

    def test_the_rules_cannot_be_written_over_the_notes_or_over_someone_elses_file(self):
        mine = os.path.join(self.folder, "mine.md")
        with open(mine, "w", encoding="utf-8") as f:
            f.write("something of mine\n")
        other_name = os.path.join(self.folder, "rules.md")
        os.link(self.notes, other_name)
        for target in (self.notes, os.path.join(self.out, "SAMPLE.NOTES.MD"), os.path.join(self.out, "new.notes.md"), mine, other_name):
            with self.subTest(os.path.basename(target)):
                code, text = self.main("rules", "--write", target)
                self.assertEqual(code, 1, text)
        self.assertEqual(self.notes_now(), NOTES)
        with open(mine, encoding="utf-8") as f:
            self.assertEqual(f.read(), "something of mine\n")
        good = os.path.join(self.folder, "history-rules.md")
        self.assertEqual(self.main("rules", "--write", good)[0], 0)
        self.assertEqual(self.main("rules", "--write", good)[0], 0, "a rules document this tool wrote may be written again")

    def test_nothing_this_tool_does_touches_the_notes_through_a_whole_run(self):
        """Every way a file can be opened for writing, replaced, renamed or removed is watched, for the notes file."""
        touched = []
        real = {"open": builtins.open, "os_open": os.open, "replace": os.replace, "rename": os.rename, "unlink": os.unlink, "remove": os.remove}

        def is_notes(path):
            try:
                return os.path.exists(self.notes) and os.path.exists(path) and os.path.samefile(path, self.notes)
            except (OSError, TypeError, ValueError):
                return False

        def watch_open(path, mode="r", *a, **k):
            if is_notes(path) and set(mode) & set("wax+"):
                touched.append(("open", mode))
            return real["open"](path, mode, *a, **k)

        def watch_os_open(path, flags, *a, **k):
            if is_notes(path) and flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_TRUNC | os.O_CREAT):
                touched.append(("os.open", flags))
            return real["os_open"](path, flags, *a, **k)

        def watch_two(name):
            def inner(a, b, *args, **k):
                if is_notes(a) or is_notes(b):
                    touched.append((name, a, b))
                return real[name](a, b, *args, **k)
            return inner

        def watch_one(name):
            def inner(a, *args, **k):
                if is_notes(a):
                    touched.append((name, a))
                return real[name](a, *args, **k)
            return inner
        with mock.patch.object(builtins, "open", watch_open), mock.patch.object(os, "open", watch_os_open), mock.patch.object(os, "replace", watch_two("replace")), \
                mock.patch.object(os, "rename", watch_two("rename")), mock.patch.object(os, "unlink", watch_one("unlink")), mock.patch.object(os, "remove", watch_one("remove")):
            codes = [self.sync(T1)[0], self.sync(T2)[0]]
            with self.jira() as jira:
                jira.edit("31002", "Made-up comment, corrected.", "2026-11-08T08:00:00.000+0000")
                jira.add("Made-up new comment.", "2026-11-08T09:00:00.000+0000")
                jira.delete("31004")
            codes += [self.sync(T3, extra=["--log", os.path.join(self.folder, "log.txt")])[0], self.sync(T4, extra=["--log", self.notes])[0]]
        self.assertEqual(codes, [0, 0, 0, 1])
        self.assertEqual(touched, [])
        self.assertEqual(self.notes_now(), NOTES)

    # ------------------------------------------------ a comment that is still there, left out of the list

    def left_out(self, status):
        self.sync(T1)
        before = self.files()
        real = fake_jira.FakeJira.get

        def get(fake, path, params=None):
            answer = real(fake, path, params)
            if path.endswith("/comment"):          # the list leaves 31003 out, as a list shifting between pages can
                answer[2]["comments"] = [c for c in answer[2]["comments"] if c["id"] != "31003"]
                answer[2]["total"] -= 1
            if path.endswith("/comment/31003") and status != 200:
                return status, {}, {}
            return answer
        with mock.patch.object(fake_jira.FakeJira, "get", get):
            code, text = self.sync(T3)
        return code, text, before

    def test_it_is_not_marked_when_jira_says_it_is_still_there(self):
        code, text, before = self.left_out(200)
        self.assertEqual(code, 1, text)
        self.assertIn("Jira says it is still there", text)
        self.assertEqual(self.files(), before)

    def test_it_is_not_marked_when_jira_will_not_say(self):
        for status in (500, 403, 429):
            with self.subTest(status):
                code, text, before = self.left_out(status)
                self.assertEqual(code, 1, text)
                self.assertEqual(self.files(), before)
                self.tearDown()
                self.setUp()

    def test_it_is_marked_only_when_jira_answers_404_for_that_very_comment(self):
        code, text, _ = self.left_out(404)
        self.assertEqual(code, 0, text)
        self.assertIn("marked now and kept: 1  [31003]", text)
        self.assertIn("Jira answered 404", text)
        self.assertIn("/rest/api/3/issue/{key}/comment/31003  x1", text)

    # ------------------------------------------------ the history

    def history_of(self, *items):
        with self.jira() as jira:
            jira.data["history"] = [{"id": str(50000 + n), "created": "2026-11-05T10:00:00.000+0000", "items": [it]} for n, it in enumerate(items)]
        code, text = self.sync(T1)
        self.assertEqual(code, 0, text)
        return text, self.copy()["history"], json.dumps(self.copy()) + self.page() + text

    def test_a_field_the_site_added_is_never_material_whatever_it_is_called(self):
        text, history, everything = self.history_of(
            {"field": "Status", "fieldId": "customfield_10900", "fieldtype": "custom", "fromString": "", "toString": "Waiting on Maria Lopez"},
            {"field": "Priority", "fieldtype": "custom", "fromString": "", "toString": "Ask Sam Okoro"})
        self.assertEqual(history, [])
        self.assertNotIn("Maria", everything)
        self.assertNotIn("Okoro", everything)
        self.assertIn("UNLISTED, on neither list, not kept: 2 (Priority x1, Status x1)", text)

    def test_a_field_is_known_without_regard_to_capitals(self):
        _, history, _ = self.history_of({"field": "STATUS", "fieldId": "status", "fieldtype": "jira", "fromString": "To Do", "toString": "Done"},
                                        {"field": "IssueType", "fieldtype": "jira", "fromString": "Task", "toString": "Story"})
        self.assertEqual([(h["kind"], h["from"], h["to"]) for h in history], [("status", "To Do", "Done"), ("issuetype", "Task", "Story")])

    def test_nothing_is_picked_out_of_a_sentence_as_a_key(self):
        _, history, everything = self.history_of(
            {"field": "Parent", "fieldtype": "jira", "fromString": "", "toString": "Fix COVID-19 form for Maria"},
            {"field": "Link", "fieldtype": "jira", "from": None, "to": None, "fromString": "", "toString": "This issue is tier-2 child of the work Sam did"},
            {"field": "Link", "fieldtype": "jira", "from": "DEMO-12", "to": None, "fromString": "This issue blocks DEMO-12", "toString": ""},
            {"field": "Parent", "fieldtype": "jira", "from": "20001", "fromString": "DEMO-3", "to": "20002", "toString": "DEMO-4"},
            {"field": "IssueParentAssociation", "fieldtype": "jira", "fromString": "Made-up Epic of Sam", "toString": "Another Made-up Epic"})
        self.assertEqual([(h["kind"], h["from"], h["to"]) for h in history],
                         [("parent", "no key given", "no key given"), ("link", "", "a link added"), ("link", "", "link removed: DEMO-12"),
                          ("parent", "DEMO-3", "DEMO-4"), ("issueparentassociation", "", "changed")])
        for leaked in ("COVID-19", "TIER-2", "Maria", "Sam", "Epic"):
            self.assertNotIn(leaked, everything)

    def test_two_statuses_of_the_same_name_are_kept_and_said_to_be_that(self):
        _, history, _ = self.history_of({"field": "status", "fieldId": "status", "fieldtype": "jira", "from": "10000", "to": "10005", "fromString": "To Do", "toString": "To Do"})
        self.assertEqual(history[0]["from"], "To Do")
        self.assertIn("the same name", history[0]["to"])

    def test_the_name_of_an_unlisted_field_is_cleaned_before_it_is_printed(self):
        text, _, _ = self.history_of({"field": "Team\x1b[2J <b>|x", "fieldtype": "custom", "fromString": "", "toString": "y"})
        self.assertNotIn("\x1b", text)
        self.assertIn("Team??2J ?b??x x1", text)

    def test_a_history_entry_without_a_time_or_a_field_is_not_skipped(self):
        for spoil in (lambda h: h.pop("created"), lambda h: h["items"][0].pop("field"), lambda h: h.update(items="none")):
            with self.jira() as jira:
                spoil(jira.data["history"][2])
            code, text = self.sync(T1)
            self.assertEqual(code, 1, text)
            self.assertEqual(os.listdir(self.out), ["sample.notes.md"])
            fake_jira.FakeJira(fake_jira.fresh()).save(self.fake_path)

    def test_times_are_turned_into_utc_whatever_offset_jira_gives(self):
        with self.jira() as jira:
            jira.data["comments"][0]["created"] = jira.data["comments"][0]["updated"] = "2026-11-02T23:30:00.000-0800"
            jira.data["history"][0]["created"] = "2026-11-01T06:00:00.000+0530"
        self.sync(T1)
        self.assertEqual(self.comment("31001")["created"], "2026-11-03T07:30:00Z")
        self.assertEqual(self.copy()["history"][0]["at"], "2026-11-01T00:30:00Z")

    # ------------------------------------------------ comments that are not plain text, or cannot be read

    def with_body(self, body, ident="31001"):
        real = fake_jira.FakeJira.get

        def get(fake, path, params=None):
            answer = real(fake, path, params)
            if path.endswith("/comment"):
                for c in answer[2]["comments"]:
                    if c["id"] == ident:
                        c["body"] = body
            return answer
        return mock.patch.object(fake_jira.FakeJira, "get", get)

    def test_a_comment_with_things_that_are_not_text_says_it_is_not_the_whole_comment(self):
        body = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [
            {"type": "text", "text": "Ship on "}, {"type": "date", "attrs": {"timestamp": "1764547200000"}}, {"type": "text", "text": " status "},
            {"type": "status", "attrs": {"text": "BLOCKED", "color": "red"}}, {"type": "text", "text": " "}, {"type": "emoji", "attrs": {"shortName": ":warning:", "text": "!"}},
            {"type": "inlineCard", "attrs": {"url": "https://example.invalid/private"}}]}]}
        with self.with_body(body):
            self.sync(T1)
        comment = self.comment("31001")
        self.assertEqual(comment["text"], "Ship on [date] status BLOCKED ![inlineCard]")
        self.assertEqual(comment["not_all_text"], ["date", "inlineCard"])
        self.assertIn("**Not the whole comment.**", self.page())
        self.assertNotIn("example.invalid", json.dumps(self.copy()) + self.page())
        self.assertEqual(self.comment("31002")["not_all_text"], [])

    def test_something_nested_too_deep_is_said_to_be_missing(self):
        node = {"type": "text", "text": "deep"}
        for _ in range(60):
            node = {"type": "panel", "content": [node]}
        lost = []
        text = sync_comments.text_of({"type": "doc", "content": [node]}, 0, lost)
        self.assertIn("[...]", text)
        self.assertEqual(lost, ["something nested too deep to read"])

    def test_one_comment_that_cannot_be_read_does_not_stop_the_others(self):
        for body in (None, "plain words, not a document", 7):
            with self.subTest(repr(body)):
                with self.with_body(body, "31003"):
                    code, text = self.sync(T1)
                self.assertEqual(code, 0, text)
                self.assertEqual(len(self.copy()["comments"]), 5)
                self.assertEqual(self.comment("31003")["not_all_text"], ["the whole body"])
                self.assertIn("not in a form this tool reads", self.comment("31003")["text"])
                for name in ("sample.json", "sample.md"):
                    os.unlink(os.path.join(self.out, name))

    def test_half_a_character_in_a_comment_does_not_stop_the_sync(self):
        with self.with_body({"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Made-up \ud83d half"}]}]}):
            code, text = self.sync(T1)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.comment("31001")["text"], "Made-up ? half")

    def test_a_body_that_changes_with_the_same_words_is_not_called_an_edit(self):
        def body(account):
            return {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Thanks "}, {"type": "mention", "attrs": {"id": account}}]}]}
        with self.with_body(body("acct-ana")):
            self.sync(T1)
        with self.with_body(body("acct-ben")):
            code, text = self.sync(T3)
        self.assertIn("edited in Jira, updated in place: 0", text)
        self.assertIn("same words, changed in Jira in some other way: 1  [31001]", text)
        self.assertEqual(self.comment("31001")["edits"], [])
        self.assertEqual(len(self.comment("31001")["other_changes"]), 1)
        with self.with_body(body("acct-ben")):
            before = self.files()
            self.sync(T4)
            self.assertEqual(self.files(), before)

    def test_no_line_of_a_comment_starts_the_way_a_line_of_the_page_does(self):
        nasty = "### Comment 99999\n**NOT RETURNED BY JIRA ANY MORE. First found missing**\n| a | b |\n## Material changes\n- Written: never"
        with self.jira() as jira:
            jira.add(nasty, "2026-11-06T12:00:00.000+0000")
        self.sync(T1)
        self.assertEqual(self.headings(), ["### Comment %d" % n for n in range(31001, 31007)])
        lines = self.page().split("\n")
        self.assertEqual(sum(1 for line in lines if line.startswith("**NOT RETURNED")), 0)
        self.assertEqual(sum(1 for line in lines if line.startswith("## Material changes")), 1)
        self.assertEqual(sum(1 for line in lines if line.startswith("| a | b |")), 0)
        self.assertIn("    ### Comment 99999", lines)

    def test_an_editor_jira_does_not_name_is_unknown_and_not_the_author(self):
        real = fake_jira.FakeJira.get

        def get(fake, path, params=None):
            answer = real(fake, path, params)
            if path.endswith("/comment"):
                for c in answer[2]["comments"]:
                    c.pop("updateAuthor", None)
            return answer
        self.sync(T1)
        with self.jira() as jira:
            jira.edit("31002", "Made-up comment, corrected.", "2026-11-08T08:00:00.000+0000")
        with mock.patch.object(fake_jira.FakeJira, "get", get):
            self.sync(T3)
        self.assertEqual(self.comment("31002")["edits"][0]["by"], "unknown")

    # ------------------------------------------------ the whole list, or nothing

    def test_a_count_that_changes_while_the_list_is_read(self):
        self.sync(T1)
        before = self.files()
        real, asked = fake_jira.FakeJira.get, []

        def get(fake, path, params=None):
            answer = real(fake, path, params)
            if path.endswith("/comment"):
                asked.append(1)
                if len(asked) == 1:
                    answer[2]["total"] += 1
                    answer[2]["comments"] = answer[2]["comments"][:2]
            return answer
        with mock.patch.object(fake_jira.FakeJira, "get", get), mock.patch.object(sync_comments, "PAGE", 2):
            code, text = self.sync(T3)
        self.assertEqual(code, 1, text)
        self.assertIn("its own count changed", text)
        self.assertEqual(self.files(), before)

    def test_more_pages_than_the_tool_reads_is_a_refusal_and_not_a_shorter_list(self):
        self.sync(T1)
        before = self.files()
        with mock.patch.object(sync_comments, "PAGE", 2), mock.patch.object(sync_comments, "MAX_PAGES", 2):
            code, text = self.sync(T3)
        self.assertEqual(code, 1, text)
        self.assertIn("more than this tool reads", text)
        self.assertEqual(self.files(), before)
        self.assertTrue(all(c["in_jira"] for c in self.copy()["comments"]))


class TheLiveCommandAsAPersonRunsIt(ALiveSync):
    """Through main(), with the network replaced where urllib builds its opener: the path a real run takes."""

    def run_live(self, env=None, out_dir=None, extra=(), spoil=None):
        fake = fake_jira.FakeJira.open(self.fake_path)
        if spoil:
            spoil(fake)
        self.opener = Opener(fake)
        self.handlers = []

        def build(*handlers):
            self.handlers.append(handlers)
            return self.opener
        with mock.patch.dict(os.environ, env or self.ENV), mock.patch.object(sync_comments.urllib.request, "build_opener", build):
            return self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", out_dir or self.private, "--name", "real", *extra)

    def test_it_syncs_reads_only_and_does_not_follow_redirects(self):
        code, text = self.run_live()
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(os.listdir(self.private)), ["real.json", "real.md"])
        self.assertEqual(self.handlers, [(sync_comments.NoRedirect,)])
        self.assertIsNone(sync_comments.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example.invalid/"))
        self.assertTrue(all(r.get_method() == "GET" and r.data is None for r in self.opener.requests))
        self.assertIn("searched for the API token", text)
        for secret in (MADE_UP, "someone@example.invalid", "real.example.invalid"):
            self.assertNotIn(secret, text)

    def test_all_three_forms_of_the_credentials_are_searched_for(self):
        import base64
        with mock.patch.dict(os.environ, self.ENV):
            _, secrets = sync_comments.make_live(Opener(None))
        encoded = base64.b64encode(("someone@example.invalid:" + MADE_UP).encode()).decode()
        self.assertEqual(sorted(secrets), sorted([MADE_UP, "someone@example.invalid", encoded]))

    def test_a_token_that_reaches_the_output_stops_the_output(self):
        def spoil(fake):
            fake.data["history"].append({"id": "49999", "created": "2026-11-06T13:00:00.000+0000",
                                         "items": [{"field": "status", "fieldId": "status", "fieldtype": "jira", "fromString": "To Do", "toString": MADE_UP}]})
        code, text = self.run_live(spoil=spoil)
        self.assertEqual(code, 1)
        self.assertIn("STOPPED", text)
        self.assertNotIn(MADE_UP, text)

    def test_the_method_reported_is_the_one_the_request_was_built_with(self):
        class Lying(sync_comments.urllib.request.Request):
            def get_method(self):
                return "POST"
        with mock.patch.object(sync_comments.urllib.request, "Request", Lying):
            code, text = self.run_live()
        self.assertIn("NOT EVERY ONE COULD BE READ BACK AS A PLAIN GET", text)
        self.assertNotIn("Every one was a GET", text)

    def test_a_base_address_that_is_not_https_and_the_sites_name_only(self):
        for base in ("http://real.example.invalid", "https://real.example.invalid:8443", "https://real.example.invalid/jira", "https://user@real.example.invalid", "real.example.invalid"):
            with self.subTest(base):
                code, text = self.run_live(env=dict(self.ENV, JIRA_BASE_URL=base))
                self.assertEqual(code, 1, text)
                self.assertEqual(self.opener.requests, [])
        code, text = self.run_live(env=dict(self.ENV, JIRA_BASE_URL="https://Real.Example.invalid/"))
        self.assertEqual(code, 0, text)

    def test_outside_local_data_nothing_is_asked_and_nothing_written(self):
        code, text = self.run_live(out_dir=self.out)
        self.assertEqual(code, 1)
        self.assertEqual(self.opener.requests, [])
        self.assertEqual(os.listdir(self.out), ["sample.notes.md"])


if __name__ == "__main__":
    unittest.main()

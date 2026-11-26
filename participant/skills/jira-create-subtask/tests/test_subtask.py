"""Tests for subtask.py, against the fake Jira. No network. Each test gets its own fake and its own folder."""
import argparse
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import subtask as st      # noqa: E402
import fake_jira as fj    # noqa: E402

HOST = "fixture-site.example.invalid"
SITE = "738169e667642f09"
TITLE = "Add a column for the export date"


def made_up_settings(base):
    """The three settings a live run reads, with invented values. Nothing here is a real address or credential."""
    return dict(zip(("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"), (base, "made-up@example.invalid", "made-up-value")))


class Case(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-subtask-test-")
        self.state = os.path.join(self.root, "state")
        self.fake = fj.FakeJira()
        self.write_change({"parent": "SAND-1", "summary": TITLE})
        self.allowlist = os.path.join(self.root, "allowlist.json")
        self.write_allowlist([(SITE, "20001"), (SITE, "20003")])

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_change(self, change, name="change.json"):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            json.dump(change, f) if not isinstance(change, str) else f.write(change)

    def write_allowlist(self, pairs, path=None):
        with open(path or self.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": [{"site_fingerprint": s, "project_id": p} for s, p in pairs]}, f)

    def go(self, command, may_write=None, host=HOST, **more):
        args = argparse.Namespace(command=command, change=os.path.join(self.root, more.pop("change", "change.json")), allowlist=self.allowlist,
                                  state=self.state, fingerprint=None, confirmed_by=None, result=None, pretend_minutes_later=0, log=None)
        for key, value in more.items():
            setattr(args, key, value)
        post = self.fake.post if (command == "confirm" if may_write is None else may_write) else None
        conn = st.Connection(self.fake.get, post, host)
        del st.LINES[:]
        code = st.run(args, conn)
        self.saved = "\n".join(saved for _, saved in st.LINES)
        return code, "\n".join(shown for shown, _ in st.LINES), conn

    def preview(self, **more):
        return self.go("preview", **more)

    def fingerprint(self, **more):
        code, out, _ = self.preview(**more)
        self.assertEqual(code, 0, out)
        return re.search(r"^Fingerprint of this preview: ([0-9a-f]{12})$", out, re.M).group(1)

    def confirm(self, fp, by="the participant", **more):
        return self.go("confirm", fingerprint=fp, confirmed_by=by, **more)

    def children(self, parent="30001"):
        return [i for i in self.fake.state["issues"].values() if i["parent_id"] == parent]

    def count(self):
        return len(self.fake.state["issues"])

    def posts(self):
        return [r for r in self.fake.requests if r[0] == "POST"]

    def refused(self, result, *parts):
        code, out, _ = result
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED:", out)
        self.assertIn("Nothing has been written.", out)
        self.assertNotIn("Fingerprint of this preview", out)
        for part in parts:
            self.assertIn(part, out)
        self.assertEqual(self.posts(), [])
        return out

    def written(self):
        fp = self.fingerprint()
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 0, out)
        return fp, out


class TheParent(Case):
    """Criteria 1 and 2."""

    def test_the_parent_is_read_by_the_reference_given_and_shown_with_its_key_and_its_id(self):
        code, out, conn = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn("Parent:     SAND-1 (issue id 30001).", out)
        self.assertEqual(conn.sent[0], ("GET", "/rest/api/3/issue/SAND-1"))

    def test_two_stories_with_one_title_are_told_apart_by_the_reference(self):
        self.write_change({"parent": "SAND-2", "summary": TITLE})
        fp = self.fingerprint()
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.children("30002")), 1)
        self.assertEqual(len(self.children("30001")), 1)   # SAND-1 still has only the one it began with

    def test_a_parent_can_be_named_by_its_issue_id(self):
        self.write_change({"parent": "30001", "summary": TITLE})
        code, out, _ = self.confirm(self.fingerprint())
        self.assertEqual(code, 0, out)
        self.assertEqual(self.children()[-1]["summary"], TITLE)

    def test_a_title_in_place_of_a_reference_is_refused_before_jira_is_asked(self):
        self.write_change({"parent": fj.TWIN_TITLE, "summary": TITLE})
        _, _, conn = result = self.preview()
        self.refused(result, "A title is not accepted")
        self.assertEqual(conn.sent, [])

    def test_no_request_searches_for_anything(self):
        self.confirm(self.fingerprint())
        for _, path in self.fake.requests:
            self.assertNotIn("search", path)
            self.assertNotIn("jql", path.lower())

    def test_a_parent_that_does_not_exist_is_refused_before_the_preview(self):
        self.write_change({"parent": "SAND-999", "summary": TITLE})
        out = self.refused(self.preview(), "Jira answered 404 for the parent", "does not exist")
        self.assertNotIn("PREVIEW", out)
        self.assertFalse(os.path.exists(os.path.join(self.state, "previews")))

    def test_a_parent_that_is_a_subtask_is_refused_before_the_preview(self):
        self.write_change({"parent": "SAND-4", "summary": TITLE})
        out = self.refused(self.preview(), "SAND-4 (issue id 30004), is itself a subtask")
        self.assertNotIn("PREVIEW", out)
        self.assertFalse(os.path.exists(os.path.join(self.state, "previews")))

    def test_a_closed_parent_is_refused_before_the_preview(self):
        self.write_change({"parent": "SAND-3", "summary": TITLE})
        out = self.refused(self.preview(), "SAND-3 (issue id 30003), is closed", "reopen the story in Jira first")
        self.assertNotIn("PREVIEW", out)

    def test_a_parent_in_progress_is_not_refused(self):
        self.write_change({"parent": "SAND-5", "summary": TITLE})
        code, out, _ = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn('in Jira\'s category "indeterminate"', out)

    def test_a_parent_whose_status_category_jira_does_not_give_is_refused(self):
        real = self.fake.shown
        self.fake.shown = lambda issue: (lambda out: (out["fields"]["status"].pop("statusCategory"), out)[1])(real(issue))
        self.refused(self.preview(), "it is not known whether the parent is closed")

    def test_the_parents_title_is_shown_on_screen_and_left_out_of_what_is_saved(self):
        _, out, _ = self.preview()
        self.assertIn("    | " + fj.TWIN_TITLE, out)
        self.assertNotIn(fj.TWIN_TITLE, self.saved)
        self.assertIn("is not saved: %d characters" % len(fj.TWIN_TITLE), self.saved)

    def test_a_title_worded_as_an_instruction_is_shown_and_changes_nothing(self):
        self.write_change({"parent": "SAND-5", "summary": TITLE})
        code, out, _ = self.confirm(self.fingerprint())
        self.assertEqual(code, 0, out)
        self.assertEqual([c["summary"] for c in self.children("30005")], [TITLE])
        self.assertEqual(self.count(), 8)

    def test_unseen_characters_in_the_parents_title_are_replaced(self):
        self.fake.state["issues"]["30001"]["summary"] = "Export" + chr(0x202e) + "report" + chr(7)
        _, out, _ = self.preview()
        self.assertIn("    | Export?report?", out)


class ThePreview(Case):
    """Criteria 4 and 5."""

    def test_it_shows_the_site_the_project_and_the_exact_change(self):
        code, out, _ = self.preview()
        self.assertEqual(code, 0, out)
        for part in ("PREVIEW. Nothing has been written.", "Jira site:  https://" + HOST, "site fingerprint " + SITE, "Project:    SAND (project id 20001)",
                     "project     project id 20001 (SAND)", "parent      issue id 30001 (SAND-1)", 'issue type  "Subtask" (issue type id 10003)',
                     "    | " + TITLE, "%d characters" % len(TITLE)):
            self.assertIn(part, out)

    def test_it_writes_nothing_and_sends_only_reads(self):
        before = json.dumps(self.fake.state, sort_keys=True)
        _, out, conn = self.preview()
        self.assertEqual(json.dumps(self.fake.state, sort_keys=True), before)
        self.assertEqual({method for method, _ in conn.sent}, {"GET"})
        self.assertIn("Every one was a GET", out)

    def test_a_preview_has_no_way_to_write(self):
        conn = st.Connection(self.fake.get, None, HOST)
        with self.assertRaises(st.Refused):
            conn.post_subtask("20001", "30001", "10003", TITLE)
        self.assertEqual(self.posts(), [])

    def test_the_two_snapshots_are_the_same_and_shown(self):
        _, out, _ = self.preview()
        codes = re.findall(r"(?:before|after) the preview:\s+([0-9a-f]{16})", out)
        self.assertEqual(len(codes), 2)
        self.assertEqual(codes[0], codes[1])

    def test_a_change_in_jira_during_the_preview_is_refused(self):
        real, seen = self.fake.get, []

        def get(path, params=None):
            seen.append(path)
            if len(seen) == 4:
                self.fake.other_subtask("SAND-1", "Something else")
            return real(path, params)
        self.fake.get = get
        self.refused(self.preview(), "changed in Jira while the preview was being made")

    def test_the_snapshot_moves_when_a_subtask_is_added(self):
        first = st.snapshot(self.fake.get("/rest/api/3/issue/30001")[2])
        self.fake.other_subtask("SAND-1", "Something else")
        self.assertNotEqual(st.snapshot(self.fake.get("/rest/api/3/issue/30001")[2]), first)

    def test_the_snapshot_moves_when_only_the_title_of_a_subtask_changes(self):
        first = st.snapshot(self.fake.get("/rest/api/3/issue/30001")[2])
        self.fake.state["issues"]["30004"]["summary"] = "Write another query"     # the parent's own updated time does not move
        self.assertNotEqual(st.snapshot(self.fake.get("/rest/api/3/issue/30001")[2]), first)

    def test_the_permission_check_is_shown(self):
        _, out, _ = self.preview()
        self.assertRegex(out, r"\(BROWSE_PROJECTS\): yes")
        self.assertRegex(out, r"\(CREATE_ISSUES\):\s+yes")

    def test_no_permission_to_create_is_refused(self):
        self.write_change({"parent": "RO-1", "summary": TITLE})
        self.refused(self.preview(), "may not create issues in this project (CREATE_ISSUES: no)")

    def test_a_permission_check_jira_does_not_answer_is_not_taken_as_yes(self):
        real = self.fake.get
        self.fake.get = lambda path, params=None: (500, {}, {}) if path.endswith("mypermissions") else real(path, params)
        self.refused(self.preview(), "did not answer the permission check")

    def test_the_duplicate_check_is_shown_with_what_jira_cannot_check(self):
        _, out, _ = self.preview()
        self.assertIn("the parent has 1 subtask that this identity can see", out)
        self.assertIn("With the same title, under this parent: 0.", out)
        self.assertIn("Where Jira cannot check", out)

    def test_a_subtask_with_this_title_already_there_means_no_fingerprint(self):
        self.fake.other_subtask("SAND-1", TITLE)
        code, out, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("NOTHING TO ADD", out)
        self.assertIn("SAND-6 (issue id 30008)", out)
        self.assertNotIn("Fingerprint of this preview", out)

    def test_capitals_and_spacing_do_not_make_a_title_new(self):
        self.fake.other_subtask("SAND-1", "  add a COLUMN for   the export date ")
        _, out, _ = self.preview()
        self.assertIn("NOTHING TO ADD", out)

    def test_the_same_letters_encoded_another_way_do_not_make_a_title_new(self):
        self.write_change({"parent": "SAND-1", "summary": "Caf" + chr(0xe9) + " export"})
        self.fake.other_subtask("SAND-1", "Cafe" + chr(0x301) + " export")
        _, out, _ = self.preview()
        self.assertIn("NOTHING TO ADD", out)

    def test_the_same_title_under_another_story_is_not_a_duplicate(self):
        self.fake.other_subtask("SAND-2", TITLE)
        _, out, _ = self.preview()
        self.assertIn("Fingerprint of this preview", out)

    def test_a_project_with_no_subtask_type_is_refused(self):
        self.fake.state["subtask_types"]["20001"] = []
        self.refused(self.preview(), "has no subtask issue type")

    def test_a_project_with_two_subtask_types_is_refused(self):
        self.fake.state["subtask_types"]["20001"] = ["10003", "10099"]
        self.refused(self.preview(), "has 2 subtask issue types", "does not choose between them")

    def test_a_list_of_subtasks_jira_does_not_give_is_refused(self):
        real = self.fake.shown
        self.fake.shown = lambda issue: (lambda out: (out["fields"].pop("subtasks"), out)[1])(real(issue))
        self.refused(self.preview(), "the duplicate check cannot be made")

    def test_the_preview_is_saved_with_its_expiry(self):
        fp = self.fingerprint()
        with open(os.path.join(self.state, "previews", fp + ".json")) as f:
            record = json.load(f)
        self.assertEqual(record["state"], "open")
        self.assertEqual(record["proposal"]["parent_id"], "30001")
        self.assertIn("UTC", record["expires_at"])

    def test_the_fingerprint_depends_on_the_parent_and_on_the_title(self):
        proposal = {"parent_id": "30001", "summary": TITLE}
        base = st.fingerprint_of(proposal, "t")
        self.assertNotEqual(st.fingerprint_of(dict(proposal, parent_id="30002"), "t"), base)
        self.assertNotEqual(st.fingerprint_of(dict(proposal, summary=TITLE + "."), "t"), base)
        self.assertNotEqual(st.fingerprint_of(proposal, "u"), base)


class TheTitle(Case):
    def bad(self, summary, *parts):
        self.write_change({"parent": "SAND-1", "summary": summary})
        _, _, conn = result = self.preview()
        self.refused(result, *parts)
        self.assertEqual(conn.sent, [])

    def test_empty(self):
        self.bad("", "is empty")

    def test_not_text(self):
        self.bad(["a"], "is empty")

    def test_two_lines(self):
        self.bad("one\ntwo", "must be one line")

    def test_too_long(self):
        self.bad("x" * 201, "201 characters long and the limit is 200")

    def test_the_longest_allowed_is_accepted(self):
        self.write_change({"parent": "SAND-1", "summary": "x" * 200})
        self.assertEqual(self.preview()[0], 0)

    def test_space_at_an_end(self):
        self.bad("A title ", "begins or ends with a space")

    def test_a_tab(self):
        self.bad("A\ttitle", "cannot be seen")

    def test_a_character_that_cannot_be_seen(self):
        self.bad("A" + chr(0x200b) + "title", "cannot be seen")

    def test_a_title_that_looks_like_a_key_is_refused_and_not_shown(self):
        key = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.write_change({"parent": "SAND-1", "summary": "Rotate " + key})
        out = self.refused(self.preview(), "an AWS access key", "not shown here")
        self.assertNotIn(key, out)

    def test_a_password_written_out_is_refused(self):
        self.bad("Set the " + "pass" + "word: " + "hunter22x", "a password, key or token written out")

    def test_private_looking_things_are_pointed_out_and_not_refused(self):
        self.write_change({"parent": "SAND-1", "summary": "Ask ada@example.invalid about the confidential export"})
        code, out, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("LOOK AT THESE BEFORE CONFIRMING", out)
        self.assertIn("an email address", out)
        self.assertIn("a word that marks something as private", out)
        self.assertIn("Fingerprint of this preview", out)

    def test_a_plain_title_has_nothing_pointed_out(self):
        _, out, _ = self.preview()
        self.assertNotIn("LOOK AT THESE", out)
        self.assertIn("Looked for in the title and not found: email addresses", out)


class TheChangeFile(Case):
    def test_no_file(self):
        self.refused(self.preview(change="nothing.json"), "there is no change file")

    def test_not_json(self):
        self.write_change("{not json")
        self.refused(self.preview(), "is not JSON")

    def test_a_name_given_twice(self):
        self.write_change('{"parent": "SAND-1", "parent": "PROD-9", "summary": "A title"}')
        self.refused(self.preview(), "twice")

    def test_an_extra_field_is_refused(self):
        self.write_change({"parent": "SAND-1", "summary": TITLE, "assignee": "someone"})
        self.refused(self.preview(), "exactly 'parent' and 'summary'")

    def test_a_path_in_place_of_a_reference(self):
        self.write_change({"parent": "SAND-1/../../PROD-9", "summary": TITLE})
        self.refused(self.preview(), "letters, digits and dashes only")


class TheAllowlist(Case):
    """Criterion 6."""

    def test_a_project_not_on_the_allowlist_is_refused_at_the_preview(self):
        self.write_change({"parent": "PROD-9", "summary": TITLE})
        _, _, conn = result = self.preview()
        self.refused(result, "project PROD (project id 20002)", "is not on the sandbox allowlist")
        self.assertEqual(len(conn.sent), 1)

    def test_the_same_project_id_on_another_site_is_refused(self):
        self.refused(self.preview(host="another-site.example.invalid"), "is not on the sandbox allowlist")

    def test_it_is_refused_again_at_confirmation_if_the_allowlist_loses_the_project(self):
        fp = self.fingerprint()
        self.write_allowlist([(SITE, "20003")])
        self.refused(self.confirm(fp), "is not on the sandbox allowlist")
        self.assertEqual(self.count(), 7)

    def test_another_allowlist_file_at_confirmation_is_refused(self):
        fp = self.fingerprint()
        other = os.path.join(self.root, "other.json")
        self.write_allowlist([(SITE, "20001")], other)
        self.refused(self.confirm(fp, allowlist=other), "the allowlist file is not the one the preview used")

    def test_no_allowlist_file(self):
        os.remove(self.allowlist)
        self.refused(self.preview(), "there is no sandbox allowlist")

    def test_a_malformed_allowlist(self):
        with open(self.allowlist, "w") as f:
            json.dump({"sandbox_projects": [{"site_fingerprint": "x", "project_id": "SAND"}]}, f)
        self.refused(self.preview(), "is not a site fingerprint and a project id")

    def test_the_allowlist_is_checked_before_what_kind_of_issue_the_parent_is(self):
        self.fake.state["issues"]["30006"]["status"] = "done"
        self.write_change({"parent": "PROD-9", "summary": TITLE})
        out = self.refused(self.preview(), "is not on the sandbox allowlist")
        self.assertNotIn("is closed", out)


class TheConfirmation(Case):
    """Criteria 3, 4, 7 and 8."""

    def test_a_confirmed_preview_creates_one_subtask_under_the_parent(self):
        fp, out = self.written()
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.count(), 8)
        child = self.fake.state["issues"]["30008"]
        self.assertEqual((child["parent_id"], child["summary"], child["type_id"], child["project_id"]), ("30001", TITLE, "10003", "20001"))
        self.assertIn("WRITTEN to Jira: one subtask, SAND-6 (issue id 30008), under parent SAND-1.", out)
        self.assertIn("CONFIRMATION for preview %s, given by: the participant" % fp, out)

    def test_what_is_sent_is_the_four_fields_and_nothing_else(self):
        sent = []
        real = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (sent.append((path, params, body)), real(path, params, body))[1]
        self.written()
        self.assertEqual(sent, [("/rest/api/3/issue", None, {"fields": {"project": {"id": "20001"}, "parent": {"id": "30001"},
                                                                         "issuetype": {"id": "10003"}, "summary": TITLE}})])

    def test_the_parent_link_is_read_back_and_matches(self):
        _, out = self.written()
        self.assertIn("its parent, read back, is issue id 30001. The parent intended is issue id 30001 (SAND-1). They are the same: yes", out)
        self.assertIn("holds issue id 30008: yes", out)
        self.assertIn("counted after the write: 1", out)
        self.assertIn(("GET", "/rest/api/3/issue/30008"), self.fake.requests)

    def test_a_subtask_stored_under_another_parent_needs_a_person(self):
        self.fake.alter = lambda child: child.update(parent_id="30002")
        code, out, _ = self.confirm(self.fingerprint())
        self.assertEqual(code, 2, out)
        self.assertIn("its parent, read back, is issue id 30002. The parent intended is issue id 30001 (SAND-1). They are the same: NO", out)
        self.assertIn("A PERSON NEEDS TO LOOK", out)
        self.assertIn("NOT THE SAME", out)

    def test_a_title_stored_differently_needs_a_person(self):
        self.fake.alter = lambda child: child.update(summary=TITLE + " (edited)")
        code, out, _ = self.confirm(self.fingerprint())
        self.assertEqual(code, 2, out)
        self.assertIn("character for character", out)
        self.assertRegex(out, r"its title, read back, .*: NO")

    def test_a_subtask_stored_as_another_type_needs_a_person(self):
        self.fake.alter = lambda child: child.update(type_id="10004")
        code, out, _ = self.confirm(self.fingerprint())
        self.assertEqual(code, 2, out)
        self.assertRegex(out, r"is a subtask type .*: NO")

    def test_the_result_record_holds_what_criterion_8_asks(self):
        fp, out = self.written()
        for part in ("RESULT RECORD", "Issue key: SAND-6", "Identifier of what was created: Jira issue id 30008", "Parent intended: SAND-1, issue id 30001",
                     "Parent read back from the subtask after the write: issue id 30001, the same", "Target project: SAND (project id 20001)",
                     "Confirmed by: the participant, at ", "Preview: fingerprint " + fp):
            self.assertIn(part, out)
        self.assertRegex(out, r"Written at: \d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC")

    def test_the_result_record_is_saved_as_markdown_without_the_site(self):
        path = os.path.join(self.root, "out", "result.md")
        self.confirm(self.fingerprint(), result=path)
        with open(path) as f:
            text = f.read()
        self.assertTrue(text.startswith("# Result record"))
        self.assertIn("- Issue key: SAND-6", text)
        self.assertNotIn(HOST, text)

    def test_no_fingerprint_is_refused(self):
        self.fingerprint()
        self.refused(self.confirm(None), "no confirmation was given")
        self.refused(self.confirm(""), "no confirmation was given")

    def test_no_name_is_refused(self):
        self.refused(self.confirm(self.fingerprint(), by=" "), "the name of the person confirming")

    def test_an_email_address_as_the_name_is_refused(self):
        self.refused(self.confirm(self.fingerprint(), by="made-up@example.invalid"), "not an email address")

    def test_an_unknown_fingerprint_is_refused(self):
        self.fingerprint()
        self.refused(self.confirm("0123456789ab"), "there is no preview with the fingerprint")

    def test_a_malformed_fingerprint_is_refused(self):
        self.refused(self.confirm("../../x"), "a fingerprint is 12 characters")

    def test_a_different_title_is_refused(self):
        fp = self.fingerprint()
        self.write_change({"parent": "SAND-1", "summary": TITLE + " and the time"})
        self.refused(self.confirm(fp), "the title is not the title the preview showed")
        self.assertEqual(self.count(), 7)

    def test_a_different_parent_is_refused(self):
        fp = self.fingerprint()
        self.write_change({"parent": "SAND-2", "summary": TITLE})
        self.refused(self.confirm(fp), "it names a different parent")

    def test_another_change_file_with_the_same_content_is_refused(self):
        fp = self.fingerprint()
        self.write_change({"parent": "SAND-1", "summary": TITLE}, "copy.json")
        self.refused(self.confirm(fp, change="copy.json"), "the change file is not the file the preview showed")

    def test_a_key_that_now_leads_to_another_issue_is_refused(self):
        fp = self.fingerprint()
        issues = self.fake.state["issues"]
        issues["30001"]["key"], issues["30002"]["key"] = "OLD-1", "SAND-1"     # the key the change file names now belongs to the twin
        self.refused(self.confirm(fp), 'the reference "SAND-1" now leads to a different issue', "issue id 30001")
        self.assertEqual(self.count(), 7)

    def test_a_preview_older_than_the_limit_is_refused(self):
        fp = self.fingerprint()
        out = self.refused(self.confirm(fp, pretend_minutes_later=16), "this preview is too old", "the limit is 15")
        self.assertIn("TEST CLOCK", out)

    def test_a_preview_just_inside_the_limit_is_accepted(self):
        code, out, _ = self.confirm(self.fingerprint(), pretend_minutes_later=14)
        self.assertEqual(code, 0, out)

    def test_a_preview_dated_in_the_future_is_refused(self):
        fp = self.fingerprint()
        path = os.path.join(self.state, "previews", fp + ".json")
        with open(path) as f:
            record = json.load(f)
        record["made_at"] = "2099-01-01 00:00:00 UTC"
        record["fingerprint"] = st.fingerprint_of(record["proposal"], record["made_at"])
        os.rename(path, os.path.join(self.state, "previews", record["fingerprint"][:12] + ".json"))
        with open(os.path.join(self.state, "previews", record["fingerprint"][:12] + ".json"), "w") as f:
            json.dump(record, f)
        self.refused(self.confirm(record["fingerprint"][:12]), "dated later than the clock")

    def test_an_altered_preview_is_refused(self):
        fp = self.fingerprint()
        path = os.path.join(self.state, "previews", fp + ".json")
        with open(path) as f:
            record = json.load(f)
        record["proposal"]["parent_id"] = "30002"
        with open(path, "w") as f:
            json.dump(record, f)
        self.refused(self.confirm(fp), "has been altered since it was made")

    def test_a_fingerprint_is_used_once(self):
        fp, _ = self.written()
        self.fake.requests.clear()
        self.refused(self.confirm(fp), "already been confirmed and written", "used once")
        self.assertEqual(self.count(), 8)

    def test_two_runs_cannot_confirm_one_preview_at_once(self):
        fp = self.fingerprint()
        os.makedirs(os.path.join(self.state, "sending"))
        open(os.path.join(self.state, "sending", fp), "w").close()
        self.refused(self.confirm(fp), "another run is confirming the preview")

    def test_a_parent_closed_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.fake.state["issues"]["30001"]["status"] = "done"
        self.refused(self.confirm(fp), "is closed")

    def test_a_parent_turned_into_a_subtask_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.fake.state["issues"]["30001"].update(type_id="10003", parent_id="30002")
        self.refused(self.confirm(fp), "is itself a subtask")

    def test_permission_lost_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.fake.state["may_create"]["20001"] = False
        self.refused(self.confirm(fp), "may not create issues")

    def test_the_same_subtask_added_by_someone_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.fake.other_subtask("SAND-1", TITLE)
        self.refused(self.confirm(fp), "has been given a subtask with this title since the preview")
        self.assertEqual(len(self.children()), 2)

    def test_a_confirmation_against_another_site_is_refused(self):
        fp = self.fingerprint()
        self.refused(self.confirm(fp, host="another-site.example.invalid"), "not the Jira site the preview was made against")

    def test_a_confirm_command_given_no_way_to_write_writes_nothing(self):
        fp = self.fingerprint()
        self.refused(self.confirm(fp, may_write=False), "this command has no way to write")
        self.assertEqual(self.count(), 7)

    def test_the_last_read_before_the_write_is_of_the_parent_by_its_id(self):
        self.written()
        index = self.fake.requests.index(("POST", "/rest/api/3/issue"))
        self.assertEqual(self.fake.requests[index - 1], ("GET", "/rest/api/3/issue/30001"))


class WhenTheWriteGoesWrong(Case):
    def test_a_refusal_by_jira_with_nothing_created_is_reported_as_not_written(self):
        fp = self.fingerprint()
        self.fake.fail_post = 400
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 1, out)
        self.assertIn("Jira answered 400 to the write", out)
        self.assertIn("so nothing was written", out)
        self.assertEqual(self.count(), 7)
        self.fake.fail_post = None
        self.fake.requests.clear()
        self.refused(self.confirm(fp), "It cannot be used again")

    def test_a_server_error_with_nothing_created_yet_is_not_reported_as_not_written(self):
        fp = self.fingerprint()
        for status in (500, 502, 504, 429, 302):
            self.setUp()
            fp = self.fingerprint()
            self.fake.fail_post = status
            code, out, _ = self.confirm(fp)
            self.assertEqual(code, 2, out)
            self.assertNotIn("Nothing has been written", out)
            self.assertIn("Jira may still be creating it", out)

    def test_each_plain_refusal_by_jira_is_reported_as_not_written(self):
        for status in (400, 401, 403, 404):
            self.setUp()
            fp = self.fingerprint()
            self.fake.fail_post = status
            code, out, _ = self.confirm(fp)
            self.assertEqual(code, 1, (status, out))

    def test_a_refusal_by_jira_with_the_subtask_created_all_the_same_needs_a_person(self):
        fp = self.fingerprint()
        real = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (real(path, params, body), (400, {}, {}))[1]
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertNotIn("Nothing has been written", out)

    def test_jiras_own_words_are_shown_quoted(self):
        fp = self.fingerprint()
        self.fake.state["may_create"]["20001"] = False
        real = self.fake.get
        self.fake.get = lambda path, params=None: (200, {}, {"permissions": {n: {"havePermission": True} for n in ("BROWSE_PROJECTS", "CREATE_ISSUES")}}) if path.endswith("mypermissions") else real(path, params)
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 1, out)
        self.assertIn("Jira's own words, which are not this workflow's: \"no permission to create issues in this project\"", out)

    def test_no_answer_to_the_write_needs_a_person_and_is_not_sent_again(self):
        fp = self.fingerprint()
        self.fake.fail_post = "timeout"
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("It is NOT KNOWN whether Jira created the subtask. It was not sent again", out)
        self.assertEqual(len(self.posts()), 1)

    def test_a_write_applied_with_the_answer_lost_needs_a_person(self):
        fp = self.fingerprint()
        self.fake.fail_post = "applied-timeout"
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertEqual(self.count(), 8)
        self.assertNotIn("Nothing has been written", out)
        self.fake.fail_post = None
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 1)
        self.assertIn("a write was sent", out)

    def test_a_server_error_with_the_subtask_created_needs_a_person(self):
        fp = self.fingerprint()
        real = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (real(path, params, body), (500, {}, {}))[1]
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("2 subtasks where it had 1, and 1 with this title (SAND-6, issue id 30008)", out)

    def test_a_read_that_fails_after_the_write_needs_a_person(self):
        fp = self.fingerprint()
        self.fake.fail_get_after_post = 500
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("WRITTEN to Jira: one subtask, SAND-6", out)
        self.assertNotIn("Nothing has been written", out)
        with open(os.path.join(self.state, "written", fp + ".json")) as f:
            self.assertEqual(json.load(f)["subtask_id"], "30008")

    def test_jira_out_of_reach_after_the_write_needs_a_person(self):
        fp = self.fingerprint()
        real = self.fake.get

        def get(path, params=None):
            if self.posts():
                raise TimeoutError()
            return real(path, params)
        self.fake.get = get
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("after the write was sent, a read failed", out)
        self.assertNotIn("Nothing has been written", out)

    def test_a_program_failure_after_the_write_needs_a_person(self):
        fp = self.fingerprint()
        self.fake.fail_get_after_post = "broken"
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("the program then failed", out)

    def test_the_same_subtask_created_by_someone_at_the_last_moment_is_reported(self):
        fp = self.fingerprint()
        self.fake.before_post = lambda fake: fake.other_subtask("SAND-1", TITLE)
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("MORE THAN ONE: issue ids 30008, 30009", out)

    def test_an_answer_with_no_usable_id_needs_a_person(self):
        fp = self.fingerprint()
        real = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (201, {}, dict(real(path, params, body)[2], id="abc"))
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("gave no usable issue id", out)


class TheRerun(Case):
    """Criterion 9."""

    def test_a_second_preview_after_the_write_finds_nothing_to_add(self):
        self.written()
        code, out, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("NOTHING TO ADD", out)
        self.assertIn("The parent already has a subtask with this title: SAND-6 (issue id 30008).", out)
        self.assertNotIn("Fingerprint of this preview", out)
        self.assertEqual(self.count(), 8)

    def test_the_whole_workflow_run_twice_creates_one_subtask(self):
        fp, _ = self.written()
        self.preview()
        self.confirm(fp)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len([c for c in self.children() if c["summary"] == TITLE]), 1)


class TheCheck(Case):
    """Criterion 3."""

    def check(self, fp, **more):
        return self.go("check", fingerprint=fp, **more)

    def test_it_reads_the_subtask_back_and_compares_the_parent(self):
        fp, _ = self.written()
        code, out, conn = self.check(fp)
        self.assertEqual(code, 0, out)
        for part in ("PARENT CHECK", "Subtask:    SAND-6 (issue id 30008)", "Parent intended, as the preview showed it: SAND-1 (issue id 30001).",
                     "Parent read back from the subtask just now: issue id 30001.", "They are the same: yes", "FOUND: the subtask is under the parent intended."):
            self.assertIn(part, out)
        self.assertEqual({method for method, _ in conn.sent}, {"GET"})

    def test_a_subtask_since_moved_to_another_parent_is_reported(self):
        fp, _ = self.written()
        self.fake.state["issues"]["30008"]["parent_id"] = "30002"
        code, out, _ = self.check(fp)
        self.assertEqual(code, 1, out)
        self.assertIn("Parent read back from the subtask just now: issue id 30002.", out)
        self.assertIn("They are the same: NO", out)
        self.assertIn("NOT AS PREVIEWED", out)

    def test_a_subtask_since_deleted_is_reported(self):
        fp, _ = self.written()
        del self.fake.state["issues"]["30008"]
        code, out, _ = self.check(fp)
        self.assertEqual(code, 1, out)
        self.assertIn("NOT AS PREVIEWED", out)

    def test_a_second_subtask_with_the_title_is_reported(self):
        fp, _ = self.written()
        self.fake.other_subtask("SAND-1", TITLE)
        code, out, _ = self.check(fp)
        self.assertEqual(code, 1, out)
        self.assertIn("NOT ONE: issue ids 30008, 30009", out)

    def test_a_write_record_that_names_another_parent_than_the_preview_is_reported(self):
        fp, _ = self.written()
        path = os.path.join(self.state, "written", fp + ".json")
        with open(path) as f:
            record = json.load(f)
        record["parent_id"] = "30002"
        with open(path, "w") as f:
            json.dump(record, f)
        code, out, _ = self.check(fp)
        self.assertEqual(code, 1, out)
        self.assertIn("the parent the write recorded is the parent the preview showed (issue id 30001): NO", out)

    def test_no_record_of_a_write(self):
        self.refused(self.check(self.fingerprint()), "there is no record of a write")

    def test_another_site(self):
        fp, _ = self.written()
        self.fake.requests.clear()
        self.refused(self.check(fp, host="another-site.example.invalid"), "not the Jira site the subtask was written to")

    def test_a_check_has_no_way_to_write(self):
        fp, _ = self.written()
        before = self.count()
        _, _, conn = self.check(fp)
        self.assertIsNone(conn._post)
        self.assertEqual(self.count(), before)


class TheFirstRead(Case):
    def test_rejected_credentials(self):
        self.fake.get = lambda path, params=None: (401, {}, {})
        self.refused(self.preview(), "Jira rejected the credentials (401)")

    def test_jira_cannot_be_reached(self):
        def get(path, params=None):
            raise TimeoutError()
        self.fake.get = get
        self.refused(self.preview(), "could not reach Jira (TimeoutError)")

    def test_an_answer_with_no_usable_ids(self):
        real = self.fake.shown
        self.fake.shown = lambda issue: dict(real(issue), id="abc")
        self.refused(self.preview(), "could not be used")

    def test_an_issue_type_that_does_not_say_whether_it_is_a_subtask(self):
        real = self.fake.shown
        self.fake.shown = lambda issue: (lambda out: (out["fields"]["issuetype"].pop("subtask"), out)[1])(real(issue))
        self.refused(self.preview(), "could not be used")

    def test_a_program_failure_before_anything_is_sent_is_a_refusal(self):
        self.fake.get = lambda path, params=None: None      # not an answer at all
        self.refused(self.preview(), "the program failed before anything was sent")


class TheLiveConnection(unittest.TestCase):
    def live(self, base, may_write=False):
        with mock.patch.dict(os.environ, made_up_settings(base), clear=False):
            return st.make_live(may_write)

    def test_each_setting_is_needed(self):
        for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
            settings = made_up_settings("https://made-up.example.invalid")
            settings[name] = ""
            with mock.patch.dict(os.environ, settings, clear=False):
                with self.assertRaisesRegex(st.Refused, name):
                    st.make_live(False)

    def test_the_address_must_be_https_and_the_sites_name(self):
        for base in ("http://made-up.example.invalid", "https://made-up.example.invalid:8443", "https://made-up.example.invalid/jira", "https://someone@made-up.example.invalid"):
            with self.assertRaises(st.Refused, msg=base):
                self.live(base)

    def test_a_preview_is_given_no_way_to_write(self):
        conn, _ = self.live("https://made-up.example.invalid")
        self.assertIsNone(conn._post)

    def test_the_only_write_a_live_connection_sends_is_one_subtask(self):
        conn, _ = self.live("https://made-up.example.invalid", True)
        good = {"fields": {"project": {"id": "1"}, "parent": {"id": "2"}, "issuetype": {"id": "3"}, "summary": "A title"}}
        for path, params, body in (("/rest/api/3/issue/30001", None, good), ("/rest/api/3/issue/30001/comment", None, good), ("/rest/api/3/issue", {"updateHistory": "true"}, good),
                                   ("/rest/api/3/issue", None, {"fields": dict(good["fields"], assignee={"id": "x"})}), ("/rest/api/3/issue", None, dict(good, update={})),
                                   ("/rest/api/3/issue", None, {"fields": {"project": {"id": "1"}, "issuetype": {"id": "3"}, "summary": "A title"}})):
            with self.assertRaises(st.Refused, msg=path):
                conn._post(path, params, body)

    def test_the_secrets_to_search_for_are_the_token_the_email_and_their_encoded_form(self):
        _, secrets = self.live("https://made-up.example.invalid")
        self.assertEqual(len(secrets), 3)
        self.assertIn("made-up-value", secrets)


class TheProgram(Case):
    def main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = st.main(list(argv))
        return code, out.getvalue()

    def common(self):
        return ["--source", "fake", "--state", self.state]

    def both(self):
        return self.common() + ["--change", os.path.join(self.root, "change.json"), "--allowlist", self.allowlist]

    def test_the_three_commands_from_the_command_line(self):
        log = os.path.join(self.root, "logs", "preview.txt")
        code, out = self.main("preview", *self.both(), "--log", log)
        self.assertEqual(code, 0, out)
        fp = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", out).group(1)
        with open(log) as f:
            saved = f.read()
        self.assertNotIn(HOST, saved)
        self.assertIn(st.SITE_MARK, saved)
        self.assertNotIn(fj.TWIN_TITLE, saved)
        self.assertIn(fj.TWIN_TITLE, out)
        code, out = self.main("confirm", *self.both(), "--fingerprint", fp, "--confirmed-by", "the participant")
        self.assertEqual(code, 0, out)
        code, out = self.main("check", *self.common(), "--fingerprint", fp)
        self.assertEqual(code, 0, out)
        self.assertIn("FOUND", out)
        code, out = self.main("preview", *self.both())
        self.assertIn("NOTHING TO ADD", out)

    def test_only_confirm_is_given_a_way_to_write(self):
        made = []
        real = st.Connection

        def spy(get, post, host):
            made.append(post)
            return real(get, post, host)
        with mock.patch.object(st, "Connection", spy):
            _, out = self.main("preview", *self.both())
            fp = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", out).group(1)
            self.main("check", *self.common(), "--fingerprint", fp)
            self.main("confirm", *self.both(), "--fingerprint", fp, "--confirmed-by", "x")
        self.assertEqual([post is None for post in made], [True, True, False])

    def test_a_live_run_with_no_settings_is_refused(self):
        with mock.patch.dict(os.environ, made_up_settings(""), clear=False):
            code, out = self.main("preview", "--source", "live", "--state", self.state, "--change", os.path.join(self.root, "change.json"), "--allowlist", self.allowlist)
        self.assertEqual(code, 1)
        self.assertIn("JIRA_BASE_URL is not set", out)

    def test_output_holding_a_credential_is_not_shown_or_saved(self):
        log = os.path.join(self.root, "log.txt")
        conn = st.Connection(self.fake.get, None, HOST)
        with mock.patch.object(st, "make_live", lambda may_write: (conn, [HOST])):
            code, out = self.main("preview", "--source", "live", "--state", self.state, "--change", os.path.join(self.root, "change.json"), "--allowlist", self.allowlist, "--log", log)
        self.assertEqual(code, 1)
        self.assertIn("STOPPED: a credential was found in the output", out)
        self.assertNotIn("PREVIEW", out)
        self.assertFalse(os.path.exists(log))

    def test_a_log_that_cannot_be_saved_does_not_change_the_exit_code(self):
        blocker = os.path.join(self.root, "a-file")
        open(blocker, "w").close()
        code, out = self.main("preview", *self.both(), "--log", os.path.join(blocker, "log.txt"))
        self.assertEqual(code, 0, out)
        self.assertIn("COULD NOT BE SAVED", out)

    def test_a_credential_found_after_a_write_says_that_a_write_was_sent(self):
        _, out = self.main("preview", *self.both())
        fp = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", out).group(1)
        conn = st.Connection(self.fake.get, self.fake.post, HOST)
        with mock.patch.object(st, "make_live", lambda may_write: (conn, ["RESULT RECORD"])):
            code, out = self.main("confirm", "--source", "live", "--state", self.state, "--change", os.path.join(self.root, "change.json"), "--allowlist", self.allowlist,
                                  "--fingerprint", fp, "--confirmed-by", "x")
        self.assertEqual(code, 2)
        self.assertIn("A WRITE WAS SENT TO JIRA", out)

    def test_minutes_must_be_a_whole_number(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            st.main(["confirm", *self.both(), "--pretend-minutes-later", "-5"])


class TheFake(unittest.TestCase):
    def test_two_stories_share_a_title(self):
        fake = fj.FakeJira()
        self.assertEqual(fake.find("SAND-1")["summary"], fake.find("SAND-2")["summary"])

    def test_it_refuses_a_subtask_under_a_subtask(self):
        fake = fj.FakeJira()
        status, _, _ = fake.post("/rest/api/3/issue", None, {"fields": {"project": {"id": "20001"}, "parent": {"id": "30004"}, "issuetype": {"id": "10003"}, "summary": "x"}})
        self.assertEqual(status, 400)

    def test_its_state_survives_a_file(self):
        root = tempfile.mkdtemp(prefix="gtq-subtask-test-")
        try:
            fake = fj.FakeJira()
            fake.other_subtask("SAND-2", "A title")
            fake.save(os.path.join(root, "f.json"))
            again = fj.FakeJira.open(os.path.join(root, "f.json"))
            self.assertEqual(again.state, fake.state)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

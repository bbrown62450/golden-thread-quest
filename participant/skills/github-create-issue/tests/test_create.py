"""Tests for the github-create-issue skill. Every test runs against fake_github.py. None contacts GitHub."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
sys.path.insert(0, SKILL)
import create  # noqa: E402
import fake_github  # noqa: E402
from fake_github import OTHER, REPO, FakeGitHub  # noqa: E402

pv = create.pv
PRETEND = "-".join(("made", "up", "value", "for", "the", "tests", "only"))
NEW_ISSUE = os.path.join(ROOT, "participant", "context", "github", "new-issue")
NAME = "the participant"


def duplicates_fixture(folder):
    spec = importlib.util.spec_from_file_location("fixture_maker_for_the_create_tests", os.path.join(SKILL, "..", "github-duplicate-search", "make_fixture.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write_all(folder)
    return os.path.join(folder, "fixture.md")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._shared = tempfile.TemporaryDirectory()
        cls.index = duplicates_fixture(os.path.join(cls._shared.name, "duplicates"))

    @classmethod
    def tearDownClass(cls):
        cls._shared.cleanup()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = os.path.join(self._tmp.name, "new-issue")
        os.makedirs(os.path.join(self.dir, "sources"))
        for name in ("draft.md", "sandbox-allowlist.json", os.path.join("sources", "notes.md")):
            shutil.copy(os.path.join(NEW_ISSUE, name), os.path.join(self.dir, name))
        self.draft, self.allow = os.path.join(self.dir, "draft.md"), os.path.join(self.dir, "sandbox-allowlist.json")
        self.link, self.state, self.results = os.path.join(self.dir, "linked.md"), os.path.join(self.dir, "state"), os.path.join(self.dir, "results")
        self.fake = FakeGitHub()

    def go(self, command, **more):
        args = argparse.Namespace(command=command, source="fake", draft=self.draft, allowlist=self.allow, index=self.index, state=self.state, link=None,
                                  results=self.results, fingerprint=None, confirmed_by=None, despite_duplicate=None, payload_out=None, number=None,
                                  fake_store=None, fake=self.fake)
        for key, value in more.items():
            setattr(args, key, value)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = create.run(args)
        return code, printed.getvalue()

    def preview(self):
        code, printed = self.go("preview")
        self.assertEqual(code, 0, printed)
        return re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", printed).group(1)

    def confirm(self, mark, name=NAME, **more):
        return self.go("confirm", fingerprint=mark, confirmed_by=name, **more)

    def created(self):
        return self.fake.created()

    def link_now(self):
        return create.read_link(self.link)

    def record(self, mark):
        with open(os.path.join(self.state, mark + ".json"), encoding="utf-8") as f:
            return json.load(f)

    def result(self):
        with open(os.path.join(self.results, "create-issue.md"), encoding="utf-8") as f:
            return f.read()

    def edit_draft(self, old, new):
        with open(self.draft, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(old, text)
        with open(self.draft, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))


class SameAsThePreview(Base):
    """Criterion 1: the issue created matches the previewed payload field for field."""

    def test_the_issue_created_holds_exactly_the_previewed_fields(self):
        mark = self.preview()
        payload = self.record(mark)["record"]["payload"]
        code, printed = self.confirm(mark)
        self.assertEqual(code, 0, printed)
        (issue,) = self.created().values()
        self.assertEqual((issue["title"], issue["body"], issue["labels"], issue["assignees"], issue["milestone"]["number"]),
                         (payload["title"], payload["body"], payload["labels"], payload["assignees"], payload["milestone"]))
        self.assertIn("RESULT: DONE. Issue 108 was created, recorded, read back, and is the same as the preview field for field", printed)

    def test_the_bytes_github_received_are_the_bytes_the_preview_showed(self):
        code, shown = self.go("preview")
        mark = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", shown).group(1)
        lines = shown.splitlines()
        bytes_line = lines[next(number for number, line in enumerate(lines) if "the exact bytes" in line) + 1].split("github-preview:      ", 1)[1]
        self.confirm(mark)
        self.assertEqual(self.fake.store["received"], [bytes_line])
        self.assertEqual(hashlib.sha256(bytes_line.encode("utf-8")).hexdigest(), self.record(mark)["record"]["payload_sha256"])

    def test_the_write_builds_no_payload_of_its_own(self):
        with open(os.path.join(SKILL, "create.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn("build_payload", code)
        self.assertEqual(code.count("pv.payload_bytes("), 1)
        self.assertEqual(code.count("conn.create("), 1)
        self.assertNotIn("json.dumps(payload", code.split("def cmd_confirm")[1].split("def linked_or_stop")[0])

    def test_every_field_is_read_back_and_compared(self):
        _, printed = self.confirm(self.preview())
        for line in ('title      the same: previewed "Export writes dates in two different formats in one file"', "body       the same, character for character: previewed 516 characters, read back 516 characters",
                     'labels     the same: previewed ["bug", "export"], read back ["bug", "export"]', 'assignees  the same: previewed ["robin-fixture"], read back ["robin-fixture"]',
                     "milestone  the same: previewed 3, read back 3"):
            self.assertIn("     " + line, printed)

    def test_an_issue_github_made_differently_needs_looking_and_is_not_fixed(self):
        mark = self.preview()
        self.fake.store["mode"] = "drop-labels"
        code, printed = self.confirm(mark)
        self.assertEqual(code, 3)
        self.assertIn("RESULT: NEEDS LOOKING. Issue 108 exists and is recorded, and it is NOT what the preview showed: labels, assignees, milestone. Nothing was changed to fix it", printed)
        self.assertIn('labels     DIFFERENT: previewed ["bug", "export"], read back []', printed)
        self.assertEqual(len(self.fake.writes()), 1)
        self.assertEqual((self.link_now()["status"], self.link_now()["compared"]), ("linked", "different"))
        self.assertIn("- outcome: CREATED, and NOT the same as the preview", self.result())
        self.assertIn("| `labels` | [\"bug\", \"export\"] | [] | **NO** |", self.result())

    def test_the_comparison_is_exact(self):
        payload = {"title": "T", "body": "a\nb", "labels": ["b", "a"], "assignees": ["x"], "milestone": 3}
        issue = {"title": "T", "body": "a\nb", "labels": [{"name": "a"}, {"name": "b"}], "assignees": [{"login": "x"}], "milestone": {"number": 3}}
        self.assertTrue(all(row[3] for row in create.compare(payload, issue)))
        for change, field in (({"title": "T "}, "title"), ({"body": "a\nb\n"}, "body"), ({"body": None}, "body"), ({"labels": [{"name": "a"}]}, "labels"),
                              ({"assignees": []}, "assignees"), ({"milestone": None}, "milestone"), ({"milestone": {"number": 4}}, "milestone")):
            rows = create.compare(payload, dict(issue, **change))
            self.assertEqual([row[0] for row in rows if not row[3]], [field], change)
        bare = {"title": "T", "body": "x"}
        self.assertTrue(all(row[3] for row in create.compare(bare, {"title": "T", "body": "x", "labels": [], "assignees": [], "milestone": None})))


class Recorded(Base):
    """Criterion 2: the returned number and identifier are written to the local file."""

    def test_the_local_link_holds_what_github_returned(self):
        self.confirm(self.preview())
        link = self.link_now()
        (issue,) = self.created().values()
        self.assertEqual((link["status"], link["repository"], link["number"], link["node_id"], link["id"], link["created_at"]),
                         ("linked", REPO, 108, issue["node_id"], issue["id"], "2026-11-24T09:00:00Z"))
        with open(self.link, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("- node ID, the identifier this file is matched by: `I_kwFX4010108`", text)
        self.assertIn("- issue number: 108", text)

    def test_the_number_is_on_disk_before_the_issue_is_read_back(self):
        seen = []

        def at_read_back(method, path):
            if path.endswith("/issues/108"):
                seen.append(self.link_now()["number"])
        self.fake.before = at_read_back
        self.confirm(self.preview())
        self.assertEqual(seen, [108])

    def test_the_intent_is_on_disk_and_the_preview_is_spent_before_the_create_is_sent(self):
        mark = self.preview()
        seen = []

        def at_send(method, path):
            if method == "POST":
                seen.append((self.link_now()["status"], self.link_now()["fingerprint"], self.record(mark)["status"]))
        self.fake.before = at_send
        self.confirm(mark)
        self.assertEqual(seen, [("creating", mark, "used")])

    def test_the_link_holds_the_read_back_comparison_and_the_payload(self):
        mark = self.preview()
        self.confirm(mark)
        with open(self.link, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Result: **every field is the same**.", text)
        self.assertIn('| `labels` | ["bug", "export"] | ["bug", "export"] | yes |', text)
        self.assertEqual(self.link_now()["payload"], self.record(mark)["record"]["payload"])

    def test_if_the_number_cannot_be_recorded_it_is_shouted_and_nothing_is_created_again(self):
        mark = self.preview()
        real, calls = create.write_link, []

        def failing(path, link, rows=None):
            calls.append(link["status"])
            if link["status"] == "linked":
                raise OSError("made-up: the disk is full")
            return real(path, link, rows)
        create.write_link = failing
        self.addCleanup(setattr, create, "write_link", real)
        code, printed = self.confirm(mark)
        create.write_link = real
        self.assertEqual(code, 3)
        self.assertIn("THE ISSUE EXISTS AND COULD NOT BE RECORDED (OSError). WRITE THIS DOWN: issue number 108, node ID I_kwFX4010108", printed)
        self.assertEqual(self.link_now()["status"], "creating")
        code, printed = self.confirm(self.record(mark)["record"]["fingerprint"])
        self.assertIn("OUTCOME IS NOT KNOWN", printed)
        self.assertEqual(len(self.fake.writes()), 1)
        self.fake.advance(2)
        self.assertEqual(self.go("reconcile")[0], 0)
        self.assertEqual((self.link_now()["status"], self.link_now()["number"]), ("linked", 108))


class MatchedByIdentifier(Base):
    """Criterion 3: the local file is matched to the GitHub issue by identifier afterwards."""

    def test_verify_matches_by_node_id_and_compares(self):
        self.confirm(self.preview())
        code, printed = self.go("verify")
        self.assertEqual(code, 0, printed)
        self.assertIn("2. MATCHED BY IDENTIFIER. GitHub's issue number 108 has the same node ID as the local link", printed)
        self.assertIn("RESULT: THE SAME. The issue on GitHub is the previewed payload, field for field", printed)

    def test_the_same_number_with_another_identifier_is_not_the_same_issue(self):
        self.confirm(self.preview())
        self.created()["108"]["node_id"] = "I_kwFXanother"
        code, printed = self.go("verify")
        self.assertEqual(code, 3)
        self.assertIn("MATCHED BY IDENTIFIER? NO.", printed)
        self.assertIn("RESULT: NOT THE SAME ISSUE", printed)

    def test_a_change_made_on_github_afterwards_is_found(self):
        self.confirm(self.preview())
        self.created()["108"]["title"] = "Edited on GitHub"
        self.created()["108"]["labels"] = ["bug"]
        code, printed = self.go("verify")
        self.assertEqual(code, 3)
        self.assertIn("RESULT: DIFFERENT in title, labels.", printed)

    def test_verify_only_reads_and_changes_nothing_locally(self):
        self.confirm(self.preview())
        with open(self.link, "rb") as f:
            before = f.read()
        writes, calls = len(self.fake.writes()), len(self.fake.calls)
        self.go("verify")
        with open(self.link, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(len(self.fake.writes()), writes)
        self.assertEqual(self.fake.calls[calls:], [["GET", "/repos/acme-fixture/tracker/issues/108"]])

    def test_verify_needs_a_linked_draft(self):
        self.assertIn("there is no local link file", self.go("verify")[1])
        mark = self.preview()
        self.fake.store["mode"] = "lost-answer"
        self.confirm(mark)
        self.assertIn('the local link\'s status is "unknown", not linked', self.go("verify")[1])

    def test_a_link_file_that_cannot_be_trusted_stops_everything(self):
        with open(self.link, "w") as f:
            f.write("# my own notes\n")
        for command in ("preview", "verify", "reconcile"):
            code, printed = self.go(command)
            self.assertEqual(code, 1)
            self.assertIn("is not one this workflow wrote, so it is not known whether this draft was already created", printed)
        self.assertEqual(self.fake.calls, [])


class PreviewFirst(Base):
    """Criteria 4 and 5: a preview shows the repository and the exact changes, and nothing is written before the human confirms."""

    def test_the_preview_is_the_preview_skill_s_and_writes_nothing(self):
        before = self.fake.snapshot()
        code, printed = self.go("preview")
        self.assertEqual(code, 0)
        for words in ("github-preview: 1. WHERE. Repository \"acme-fixture/tracker\", id 401", "5. DUPLICATE CHECK.", "6. PERMISSION CHECK.", "7. THE EXACT PAYLOAD",
                      "8. NOTHING WAS WRITTEN.", "RESULT: READY. Nothing has been written"):
            self.assertIn(words, printed)
        self.assertEqual({method for method, _ in self.fake.calls}, {"GET"})
        self.assertEqual(self.fake.snapshot(), before)
        self.assertEqual(self.created(), {})
        self.assertFalse(os.path.exists(self.link))

    def test_only_the_confirm_command_gets_a_connection_that_can_create(self):
        args = argparse.Namespace(source="fake", fake=self.fake, fake_store=None)
        self.assertFalse(hasattr(create.connection(args), "create"))
        self.assertTrue(hasattr(create.connection(args, writer=True), "create"))
        with open(os.path.join(SKILL, "create.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertEqual(code.count("writer=True)"), 1)
        self.assertIn("conn = connection(args, writer=True)", code.split("def cmd_confirm")[1].split("def linked_or_stop")[0])

    def test_a_writer_sends_one_create_and_only_where_it_was_allowed(self):
        conn = create.Writer(self.fake.send)
        with self.assertRaises(create.Refused):
            conn.create(b"{}")
        conn.allow(REPO)
        with self.assertRaises(create.Refused):
            conn.create({"title": "not bytes"})
        self.assertEqual(self.fake.calls, [])
        conn.create(b'{"title":"One"}')
        with self.assertRaises(create.Refused):
            conn.create(b'{"title":"Two"}')
        self.assertEqual(len(self.fake.writes()), 1)

    def test_the_live_sender_refuses_every_write_but_a_post_of_bytes_to_a_repository_s_issues(self):
        for method, path, body in (("PUT", "/repos/a/b/issues", b"{}"), ("PATCH", "/repos/a/b/issues/1", b"{}"), ("DELETE", "/repos/a/b/issues/1", None),
                                   ("POST", "/repos/a/b/issues/1/comments", b"{}"), ("POST", "/repos/a/b/labels", b"{}"), ("POST", "/repos/a/b", b"{}"),
                                   ("POST", "/repos/a/b/issues", {"title": "not bytes"}), ("POST", "/user/repos", b"{}")):
            with self.assertRaises(RuntimeError):
                create.live_create(method, path, None, body)
        with self.assertRaises(RuntimeError):
            create.live_create("POST", "/repos/a/b/issues", {"x": 1}, b"{}")

    def test_a_refused_preview_cannot_be_confirmed(self):
        self.edit_draft('labels: ["bug", "export"]', 'labels: ["bug", "export", "nope"]')
        code, printed = self.go("preview")
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(self.state))
        self.assertIn("there is no preview with the fingerprint", self.confirm("0" * 32)[1])
        self.assertEqual(self.created(), {})


class Allowlist(Base):
    """Criterion 6: the workflow writes only to a repository on an explicit sandbox allowlist."""

    def test_a_repository_off_the_allowlist_is_refused_before_any_request(self):
        mark = self.preview()
        calls = len(self.fake.calls)
        self.edit_draft('repository: "acme-fixture/tracker"', 'repository: "acme-fixture/production"')
        for command in ("preview", "confirm"):
            code, printed = self.go(command, fingerprint=mark, confirmed_by=NAME)
            self.assertEqual(code, 1)
            self.assertIn('the repository "acme-fixture/production" is NOT ON THE SANDBOX ALLOWLIST', printed)
        self.assertEqual(len(self.fake.calls), calls)
        self.assertEqual(self.fake.created(OTHER), {})

    def test_a_repository_taken_off_the_allowlist_after_the_preview_is_refused(self):
        mark = self.preview()
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": []}, f)
        code, printed = self.confirm(mark)
        self.assertEqual(code, 1)
        self.assertIn("NOT ON THE SANDBOX ALLOWLIST", printed)
        self.assertEqual(self.created(), {})

    def test_a_preview_for_one_repository_cannot_be_confirmed_for_another(self):
        mark = self.preview()
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": [REPO, OTHER]}, f)
        self.edit_draft('repository: "acme-fixture/tracker"', 'repository: "acme-fixture/production"')
        code, printed = self.confirm(mark)
        self.assertEqual(code, 1)
        self.assertIn("THE CHANGE DIFFERS FROM THE PREVIEW: the preview with this fingerprint is for another repository", printed)
        self.assertEqual(self.fake.created(OTHER), {})

    def test_verify_and_reconcile_check_the_allowlist_too(self):
        self.confirm(self.preview())
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": []}, f)
        calls = len(self.fake.calls)
        self.assertIn("NOT ON THE SANDBOX ALLOWLIST", self.go("verify")[1])
        self.assertEqual(len(self.fake.calls), calls)


class Confirmation(Base):
    """Criterion 7: tied to a fingerprint of the exact preview, refused when missing or when the change differs, and it expires."""

    def refused(self, words, **more):
        calls = len(self.fake.writes())
        code, printed = self.go("confirm", **more)
        self.assertEqual(code, 1, printed)
        self.assertIn(words, printed)
        self.assertEqual(len(self.fake.writes()), calls)
        self.assertEqual(self.created(), {})
        self.assertFalse(os.path.exists(os.path.join(self.results, "create-issue.md")))
        return printed

    def test_a_missing_confirmation_is_refused_before_any_request(self):
        mark = self.preview()
        calls = len(self.fake.calls)
        for more in ({}, {"fingerprint": mark}, {"confirmed_by": NAME}, {"fingerprint": mark, "confirmed_by": ""}):
            self.refused("NO CONFIRMATION was given", **more)
        self.assertEqual(len(self.fake.calls), calls)
        self.assertFalse(os.path.exists(self.link))

    def test_the_confirmer_must_be_a_plain_name(self):
        mark = self.preview()
        for name in ("   ", "x" * 61, "a\nb", "@".join(("someone", "example.invalid"))):
            self.refused("must be a short plain name", fingerprint=mark, confirmed_by=name)

    def test_a_draft_changed_after_the_preview_is_refused(self):
        mark = self.preview()
        self.edit_draft("Every date in the file written the same way", "Every date in the file written the same way, please")
        printed = self.refused("THE CHANGE DIFFERS FROM THE PREVIEW: the draft was changed after the preview was made", fingerprint=mark, confirmed_by=NAME)
        self.assertIn("A confirmation covers exactly what its preview showed", printed)
        self.assertFalse(os.path.exists(self.link))

    def test_a_change_to_any_field_of_the_draft_is_refused(self):
        for old, new in (('title: "Export writes', 'title: "The export writes'), ('labels: ["bug", "export"]', 'labels: ["bug"]'), ('milestone: "Sprint 13"', 'milestone: "Sprint 14"')):
            self.setUp()
            mark = self.preview()
            self.edit_draft(old, new)
            self.refused("THE CHANGE DIFFERS FROM THE PREVIEW", fingerprint=mark, confirmed_by=NAME)

    def test_a_fingerprint_no_preview_has_or_of_the_wrong_shape_is_refused(self):
        self.preview()
        self.refused("there is no preview with the fingerprint", fingerprint="0" * 32, confirmed_by=NAME)
        for mark in ("../sandbox-allowlist", "a" * 31, "A" * 32):
            self.refused("not the shape of a preview fingerprint", fingerprint=mark, confirmed_by=NAME)

    def test_a_saved_preview_whose_payload_was_altered_is_refused(self):
        mark = self.preview()
        saved = self.record(mark)
        saved["record"]["payload"]["title"] = "Something nobody previewed"
        with open(os.path.join(self.state, mark + ".json"), "w") as f:
            json.dump(saved, f)
        self.refused("It was altered after it was made", fingerprint=mark, confirmed_by=NAME)

    def test_a_payload_altered_under_a_fingerprint_worked_out_again_is_still_refused(self):
        mark = self.preview()
        saved = self.record(mark)
        record = dict(saved["record"], payload=dict(saved["record"]["payload"], title="Something nobody previewed"))
        del record["fingerprint"]
        forged = hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()[:32]
        with open(os.path.join(self.state, forged + ".json"), "w") as f:
            json.dump({"record": dict(record, fingerprint=forged), "status": "ready"}, f)
        self.refused("the saved payload does not give the bytes the preview showed", fingerprint=forged, confirmed_by=NAME)

    def test_a_preview_older_than_the_limit_is_refused_and_one_at_the_limit_is_good(self):
        mark = self.preview()
        self.fake.advance(16)
        printed = self.refused("THE PREVIEW HAS EXPIRED", fingerprint=mark, confirmed_by=NAME)
        self.assertIn("16 minutes, and the limit is 15", printed)
        self.assertFalse(os.path.exists(self.link))
        self.fake.advance(-1)
        code, printed = self.confirm(mark)
        self.assertEqual(code, 0, printed)
        self.assertIn("15 minutes. The limit is 15", printed)

    def test_a_preview_can_be_confirmed_once(self):
        mark = self.preview()
        self.fake.store["mode"] = "refused"
        self.assertEqual(self.confirm(mark)[0], 1)
        self.fake.store["mode"] = "ok"
        printed = self.refused("this preview was ALREADY USED, at 2026-11-24T09:00:00Z by GitHub's clock, confirmed by \"the participant\"", fingerprint=mark, confirmed_by=NAME)
        self.assertIn("A preview can be confirmed once", printed)

    def test_another_account_or_a_repository_that_changed_is_refused(self):
        mark = self.preview()
        self.fake.store["me"]["login"] = "kit-fixture"
        self.refused("is not the one of the preview", fingerprint=mark, confirmed_by=NAME)
        self.fake.store["me"]["login"] = "robin-fixture"
        self.fake.repo()["labels"] = [row for row in self.fake.repo()["labels"] if row["name"] != "export"]
        self.refused('the repository changed after the preview: the label "export" is gone', fingerprint=mark, confirmed_by=NAME)
        self.assertEqual(len(self.fake.repo()["labels"]), 5)

    def test_a_milestone_closed_after_the_preview_is_refused(self):
        mark = self.preview()
        self.fake.repo()["milestones"][1]["state"] = "closed"
        self.refused("the milestone is gone or closed", fingerprint=mark, confirmed_by=NAME)

    def test_the_same_title_filed_by_someone_else_after_the_preview_is_refused(self):
        mark = self.preview()
        self.fake.advance(1)
        self.fake.someone_else("Export writes dates in two different formats in one file")
        code, printed = self.confirm(mark)
        self.assertEqual(code, 1)
        self.assertIn("an issue with exactly this title was created in the repository AFTER the preview: number 108", printed)
        self.assertEqual(sorted(self.created()), ["108"])

    def test_the_approved_run_says_who_confirmed_for_which_fingerprint(self):
        mark = self.preview()
        _, printed = self.confirm(mark)
        self.assertIn('1. CONFIRMATION. Given by "the participant", for the preview with fingerprint %s, in this same command' % mark, printed)
        self.assertIn("This workflow cannot check who typed it", printed)


class ResultRecord(Base):
    """Criterion 8: a result record holds the repository, the number, the identifier, the timestamp and the confirmer."""

    def test_the_record_holds_everything_the_criterion_names(self):
        mark = self.preview()
        self.fake.advance(3)
        self.confirm(mark)
        text = self.result()
        for line in ("## Issue 108 of acme-fixture/tracker", "- outcome: CREATED, and the same as the preview", '- repository: "acme-fixture/tracker", id 401', "- issue number: 108",
                     "- identifier of what was created: node ID `I_kwFX4010108`, GitHub's id 5000108", "- created at: 2026-11-24T09:03:00Z, by GitHub's clock",
                     '- confirmed by: "the participant", as typed with the fingerprint in the command that wrote.', "- preview fingerprint: %s" % mark,
                     "- how it was recorded: created by this workflow, and recorded from GitHub's answer", '| `milestone` | 3 | 3 | yes |'):
            self.assertIn(line, text)

    def test_a_refusal_writes_no_record_and_a_second_issue_adds_a_section(self):
        self.go("confirm", fingerprint="0" * 32, confirmed_by=NAME)
        self.assertFalse(os.path.exists(os.path.join(self.results, "create-issue.md")))
        self.confirm(self.preview())
        shutil.copy(self.draft, os.path.join(self.dir, "draft-two.md"))
        self.draft, self.link = os.path.join(self.dir, "draft-two.md"), os.path.join(self.dir, "linked-two.md")
        self.edit_draft('title: "Export writes dates in two different formats in one file"', 'title: "A second made-up issue"')
        self.edit_draft('- title: sources/notes.md line 7: "The export writes dates in two different formats in the same file."', '- title: sources/notes.md line 2: ""')
        self.edit_draft('- title: sources/notes.md line 2: ""', '- title: sources/notes.md line 3: "Made-up notes."')
        code, printed = self.go("preview", link=self.link)
        self.assertEqual(code, 0, printed)
        mark = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", printed).group(1)
        self.assertEqual(self.confirm(mark, link=self.link)[0], 0)
        self.assertEqual(re.findall(r"^## Issue (\d+) of", self.result(), re.M), ["108", "109"])


class Rerun(Base):
    """Criterion 9: running the approved workflow again creates no duplicate."""

    def test_the_same_confirmation_again_is_refused_and_no_second_issue_is_made(self):
        mark = self.preview()
        self.confirm(mark)
        code, printed = self.confirm(mark)
        self.assertEqual(code, 1)
        self.assertIn("this draft is ALREADY the GitHub issue number 108 of acme-fixture/tracker (node ID I_kwFX4010108)", printed)
        self.assertEqual((len(self.fake.writes()), sorted(self.created())), (1, ["108"]))
        self.assertEqual(self.result().count("## Issue "), 1)

    def test_the_whole_workflow_again_stops_at_the_preview(self):
        self.confirm(self.preview())
        calls = len(self.fake.calls)
        code, printed = self.go("preview")
        self.assertEqual(code, 1)
        self.assertIn("It is not created again", printed)
        self.assertEqual(len(self.fake.calls), calls)
        self.assertEqual(len(os.listdir(self.state)), 1)

    def lost(self, mode="lost-answer"):
        mark = self.preview()
        self.fake.store["mode"] = mode
        code, printed = self.confirm(mark)
        self.fake.store["mode"] = "ok"
        return mark, code, printed

    def test_a_lost_answer_is_an_unknown_outcome_and_is_never_sent_again(self):
        mark, code, printed = self.lost()
        self.assertEqual(code, 3)
        self.assertIn("NO ANSWER CAME BACK (TimeoutError). The request was sent and may have arrived", printed)
        self.assertIn("RESULT: OUTCOME UNKNOWN. The issue MAY exist on GitHub. It was NOT sent again", printed)
        self.assertEqual(self.link_now()["status"], "unknown")
        self.assertEqual(sorted(self.created()), ["108"])
        for command in ("confirm", "preview"):
            code, printed = self.go(command, fingerprint=mark, confirmed_by=NAME)
            self.assertEqual(code, 1)
            self.assertIn("its OUTCOME IS NOT KNOWN. The issue may exist on GitHub. Nothing more is sent until `reconcile` has settled it", printed)
        self.assertEqual(len(self.fake.writes()), 1)

    def test_reconcile_finds_the_issue_that_was_created_and_links_it(self):
        self.lost()
        self.fake.advance(2)
        code, printed = self.go("reconcile")
        self.assertEqual(code, 0, printed)
        self.assertIn("Found: 1 (numbers 108)", printed)
        self.assertIn("RESULT: DONE. Issue 108 was created, recorded, read back, and is the same as the preview field for field", printed)
        link = self.link_now()
        self.assertEqual((link["status"], link["number"], link["node_id"], link["compared"]), ("linked", 108, "I_kwFX4010108", "same"))
        self.assertIn("- how it was recorded: found on GitHub by `reconcile`, by its title, body, author and time, after the create's answer was lost", self.result())
        self.assertEqual(len(self.fake.writes()), 1)

    def test_reconcile_only_reads(self):
        self.lost()
        self.fake.advance(2)
        calls = len(self.fake.calls)
        self.go("reconcile")
        self.assertEqual({method for method, _ in self.fake.calls[calls:]}, {"GET"})

    def test_a_request_that_never_arrived_is_settled_as_not_created_but_not_too_soon(self):
        mark, code, printed = self.lost("never-arrived")
        self.assertEqual((code, self.link_now()["status"], self.created()), (3, "unknown", {}))
        code, printed = self.go("reconcile")
        self.assertEqual(code, 3)
        self.assertIn("RESULT: NOT SETTLED YET. No such issue is listed, and the create was sent only 0 seconds ago", printed)
        self.assertEqual(self.link_now()["status"], "unknown")
        self.fake.advance(2)
        code, printed = self.go("reconcile")
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NOT CREATED. GitHub lists no such issue, 120 seconds after the create was sent", printed)
        self.assertEqual(self.link_now()["status"], "not-created")
        self.assertEqual(self.confirm(self.preview())[0], 0)
        self.assertEqual(sorted(self.created()), ["108"])

    def test_reconcile_does_not_take_another_issue_for_this_one(self):
        self.lost("never-arrived")
        self.fake.advance(2)
        payload = self.link_now()["payload"]
        self.fake.someone_else(payload["title"])
        self.fake._create(REPO, {"title": payload["title"], "body": payload["body"] + " edited"}, "robin-fixture")
        self.fake._create(REPO, {"title": "Another title", "body": payload["body"]}, "robin-fixture")
        code, printed = self.go("reconcile")
        self.assertEqual(code, 0)
        self.assertIn("Found: 0", printed)
        self.assertEqual(self.link_now()["status"], "not-created")

    def test_two_matching_issues_are_left_for_a_person_who_then_names_one(self):
        self.lost()
        self.fake._create(REPO, dict(self.link_now()["payload"]), "robin-fixture")
        self.fake.advance(2)
        code, printed = self.go("reconcile")
        self.assertEqual(code, 3)
        self.assertIn("RESULT: MORE THAN ONE. 2 issues match", printed)
        self.assertEqual(self.link_now()["status"], "unknown")
        self.assertIn("issue 7 is not one of the issues that match this create", self.go("reconcile", number=7)[1])
        self.assertEqual(self.go("reconcile", number=109)[0], 0)
        self.assertEqual(self.link_now()["number"], 109)

    def test_a_refusal_by_github_creates_nothing_and_says_so(self):
        mark = self.preview()
        self.fake.store["mode"] = "refused"
        code, printed = self.confirm(mark)
        self.assertEqual(code, 1)
        self.assertIn("-> status 403. GITHUB REFUSED THE CREATE. A refusal of this kind means no issue was made", printed)
        self.assertIn("RESULT: NOT DONE. No issue was created", printed)
        self.assertEqual((self.created(), self.link_now()["status"]), ({}, "not-created"))
        self.fake.store["mode"] = "ok"
        self.assertEqual(self.confirm(self.preview())[0], 0)

    def test_there_is_nothing_to_reconcile_when_the_outcome_is_known(self):
        self.confirm(self.preview())
        self.assertIn('there is nothing to reconcile: the local link\'s status is "linked"', self.go("reconcile")[1])

    def test_the_workflow_never_retries_a_create(self):
        with open(os.path.join(SKILL, "create.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertEqual(code.count("self._send("), 1)
        self.assertNotIn("retry", code.replace("never retries", "").lower().replace("retry-after", ""))
        self.lost()
        self.assertEqual(len(self.fake.writes()), 1)


class CommandLine(Base):
    def main(self, *argv, env=None):
        printed, old = io.StringIO(), dict(os.environ)
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.update(env or {})
        try:
            with contextlib.redirect_stdout(printed):
                code = create.main(list(argv))
        finally:
            os.environ.clear()
            os.environ.update(old)
        return code, printed.getvalue()

    def test_preview_confirm_and_verify_as_separate_commands(self):
        store = os.path.join(self._tmp.name, "github.json")
        with contextlib.redirect_stdout(io.StringIO()):
            fake_github.main([store, "new"])
        common = ["--source", "fake", "--fake-store", store, "--draft", self.draft, "--allowlist", self.allow, "--state", self.state, "--results", self.results]
        code, printed = self.main("preview", *common, "--index", self.index)
        self.assertEqual(code, 0, printed)
        mark = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", printed).group(1)
        self.assertEqual(fake_github.load(store).writes(), [])
        code, printed = self.main("confirm", *common, "--fingerprint", mark, "--confirmed-by", NAME)
        self.assertEqual(code, 0, printed)
        self.assertEqual(sorted(fake_github.load(store).created()), ["108"])
        self.assertEqual(self.main("verify", *common)[0], 0)
        code, printed = self.main("confirm", *common, "--fingerprint", mark, "--confirmed-by", NAME)
        self.assertEqual(code, 1)
        self.assertEqual(len(fake_github.load(store).writes()), 1)

    def test_what_each_command_needs(self):
        base = ["--source", "fake", "--draft", self.draft, "--allowlist", self.allow]
        self.assertIn("preview needs --state", self.main("preview", *base)[1])
        self.assertIn("preview needs --index", self.main("preview", *base, "--state", self.state)[1])
        self.assertIn("--source fake needs --fake-store", self.main("preview", *base, "--state", self.state, "--index", self.index)[1])

    def test_a_live_run_keeps_its_files_outside_the_repository_and_needs_the_token(self):
        live = ["--source", "live", "--allowlist", self.allow]
        env = dict([("GITHUB_TOKEN", PRETEND)])
        code, printed = self.main("verify", *live, "--draft", os.path.join(SKILL, "draft.md"), env=env)
        self.assertEqual(code, 1)
        shutil.copy(self.draft, os.path.join(self.dir, "x.md"))
        self.assertIn("a live confirm needs --results", self.main("confirm", *live, "--draft", self.draft, "--state", self.state, env=env)[1])
        code, printed = self.main("preview", *live, "--draft", self.draft, "--index", self.index, "--state", os.path.join(SKILL, "state"), env=env)
        self.assertIn("outside this repository, because they name a real account. Give --state", printed)
        code, printed = self.main("preview", *live, "--draft", self.draft, "--index", self.index, "--state", self.state)
        self.assertEqual(code, 1)
        self.assertIn("GITHUB_TOKEN is not set", printed)
        self.assertNotIn(PRETEND, printed)


if __name__ == "__main__":
    unittest.main()

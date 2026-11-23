"""Tests for the github-create-issue-preview skill. Every test runs against fake_github.py. None contacts GitHub."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
import fake_github  # noqa: E402
import preview  # noqa: E402
from fake_github import OTHER, REPO, FakeGitHub  # noqa: E402

PRETEND = "-".join(("made", "up", "value", "for", "the", "tests", "only"))
NOTES = "\n".join([
    "# Made-up notes", "",
    "The export writes dates in two different formats in the same file.",
    "In the March file the column order_date is 2026-03-04 in some rows and 04/03/2026 in others.",
    "They expected every date to be written the same way.",
    "It is a bug in the export. Assign it to robin-fixture.",
    "It should go in Sprint 13.",
    "Saving the March orders ran out of memory. They ran `export.py` on `orders-march.csv` with `v2.3.1`.",
    "It stopped with MemoryError: cannot allocate 2147483648 bytes. The whole orders file is loaded into memory before anything is written.", ""])
SECTIONS = [("What happened", "The export writes dates in two different formats in the same file."),
            ("Steps to reproduce", "1. Run the export.\n2. Open the file."),
            ("What you expected", "Every date written the same way."),
            ("Environment (optional)", "The March file.")]
SOURCES = ['- title: notes.md line 3: "The export writes dates in two different formats"',
           '- body: notes.md lines 4-5: "2026-03-04 in some rows and 04/03/2026 in others. They expected every date"',
           '- labels: notes.md line 6: "It is a bug in the export."',
           '- assignees: notes.md line 6: "Assign it to robin-fixture."',
           '- milestone: notes.md line 7: "It should go in Sprint 13."']
MEMORY = [("What happened", "Saving the March orders ran out of memory.\n\n```\nMemoryError: cannot allocate 2147483648 bytes\n```\n\n"
                            "The whole orders file is loaded into memory before anything is written."),
          ("Steps to reproduce", "1. Run `export.py` on `orders-march.csv` with `v2.3.1`."), ("What you expected", "The export to finish.")]
MEMORY_SOURCES = ['- title: notes.md line 8: "Saving the March orders ran out of memory."', '- body: notes.md line 9: "MemoryError: cannot allocate 2147483648 bytes"',
                  '- labels: notes.md line 9: "whole orders file is loaded into memory"']


def duplicates_fixture(folder):
    spec = importlib.util.spec_from_file_location("fixture_maker_for_the_preview_tests", os.path.join(SKILL, "..", "github-duplicate-search", "make_fixture.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write_all(folder)
    return os.path.join(folder, "fixture.md")


def draft_text(title="Export writes dates in two formats", labels=("bug", "export"), assignees=("robin-fixture",), milestone="Sprint 13",
               sections=SECTIONS, sources=SOURCES, repo=REPO, template="bug_report.md", before=""):
    lines = ["---", 'format: "github-issue-draft/1"', "repository: " + json.dumps(repo), "template: " + json.dumps(template), "title: " + json.dumps(title),
             "labels: " + json.dumps(list(labels)), "assignees: " + json.dumps(list(assignees)), "milestone: " + json.dumps(milestone), "---", "", "## Body", ""]
    lines += [before] if before else []
    for name, text in sections:
        lines += ["### " + name, "", text, ""]
    return "\n".join(lines + ["## Sources", ""] + list(sources) + [""])


class Base(unittest.TestCase):
    index = None

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
        self.dir = self._tmp.name
        self.allow = os.path.join(self.dir, "allow.json")
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": [REPO]}, f)
        with open(os.path.join(self.dir, "notes.md"), "w", encoding="utf-8") as f:
            f.write(NOTES)
        self.state, self.payload_file = os.path.join(self.dir, "state"), os.path.join(self.dir, "payload.md")
        self.fake = FakeGitHub()

    def go(self, text=None, despite=(), **more):
        """Write a draft and preview it. Returns (exit code, what was printed)."""
        path = os.path.join(self.dir, "draft.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(draft_text(**more) if text is None else text)
        args = argparse.Namespace(source="fake", draft=path, index=self.index, allowlist=self.allow, despite_duplicate=list(despite),
                                  payload_out=self.payload_file, state=self.state, fake_store=None)
        self.conn = preview.Connection(self.fake.send, sleep=lambda seconds: None, clock=lambda: 0)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = preview.run(args, self.conn)
        return code, printed.getvalue()

    def ready(self, **more):
        code, printed = self.go(**more)
        self.assertEqual(code, 0, printed)
        self.assertIn("RESULT: READY. Nothing has been written", printed)
        return printed

    def refused(self, words, **more):
        before = self.fake.snapshot()
        code, printed = self.go(**more)
        self.assertEqual(code, 1, printed)
        self.assertIn(words, printed)
        self.assertNotIn("FINGERPRINT", printed)
        self.assertFalse(os.path.exists(self.payload_file))
        self.assertFalse(os.path.exists(self.state))
        self.assertEqual(self.fake.not_gets(), [])
        self.assertEqual(self.fake.snapshot(), before)
        return printed

    def record(self):
        (name,) = os.listdir(self.state)
        with open(os.path.join(self.state, name), encoding="utf-8") as f:
            return json.load(f)["record"]


class Template(Base):
    """Criterion 1: the draft follows the repository's issue template."""

    def test_the_template_is_read_from_the_repository(self):
        printed = self.ready()
        self.assertIn(["GET", "/repos/acme-fixture/tracker/contents/.github/ISSUE_TEMPLATE/bug_report.md"], self.fake.calls)
        self.assertIn('2. TEMPLATE. The repository\'s own template "bug_report.md" was read from the repository. It has 4 sections.', printed)

    def test_each_section_is_shown_with_whether_it_is_required_and_filled(self):
        printed = self.ready()
        for line in ('section "What happened" (required): filled in, 1 line', 'section "Steps to reproduce" (required): filled in, 2 lines',
                     'section "What you expected" (required): filled in, 1 line', 'section "Environment (optional)" (optional): filled in, 1 line'):
            self.assertIn("     " + line, printed)

    def test_an_optional_section_may_be_left_out_or_left_empty(self):
        self.ready(sections=SECTIONS[:3])
        self.ready(sections=SECTIONS[:3] + [("Environment (optional)", "<!-- Version, file names, anything else that helps. -->")])

    def test_sections_in_another_order_are_refused(self):
        self.refused("the draft's sections are not in the template's order", sections=[SECTIONS[1], SECTIONS[0], SECTIONS[2]])

    def test_a_section_the_template_does_not_have_is_refused(self):
        self.refused('the draft has a section "Workaround" that the template does not have', sections=SECTIONS + [("Workaround", "None.")])

    def test_the_same_section_twice_and_text_before_the_first_section_are_refused(self):
        self.refused("the draft has the same section twice", sections=SECTIONS[:3] + [SECTIONS[0]])
        self.refused("text before its first section", before="Hello maintainers,\n")

    def test_a_heading_inside_a_code_block_is_not_a_section(self):
        sections = [("What happened", "It printed:\n\n```\n### Steps to reproduce\n### Not a section\n```")] + SECTIONS[1:]
        self.ready(sections=sections)
        self.assertIn("### Not a section", self.record()["payload"]["body"])

    def test_a_template_the_repository_does_not_have_is_refused_and_the_ones_it_has_are_named(self):
        code, printed = self.go(template="feature_request.md")
        self.assertEqual(code, 1)
        self.assertIn('the repository has no issue template named "feature_request.md". It has: "bug_report.md"', printed)

    def test_a_repository_with_no_templates_and_a_template_with_no_sections_stop_the_preview(self):
        self.fake.repo()["templates"] = {}
        self.assertIn("It has no .github/ISSUE_TEMPLATE folder that this connection can read", self.go()[1])
        self.fake.repo()["templates"] = {"bug_report.md": "## Only level two\n\ntext\n"}
        self.assertIn("the template has no level-3 headings", self.go()[1])

    def test_a_template_file_that_cannot_be_read_stops_the_preview(self):
        self.fake.fail("/repos/acme-fixture/tracker/contents/", 403)
        code, printed = self.go()
        self.assertEqual(code, 1)
        self.assertIn("Reading it needs permission to read the repository's files", printed)

    def test_the_template_s_labels_are_read_in_the_ways_they_are_written(self):
        for line, want in (("labels: bug, export", ["bug", "export"]), ("labels: 'bug'", ["bug"]), ('labels: ["bug", "export"]', ["bug", "export"]),
                           ("labels:\n  - bug\n  - export", ["bug", "export"]), ("labels: ''", [])):
            self.fake.repo()["templates"]["bug_report.md"] = fake_github.BUG_TEMPLATE.replace("labels: bug", line)
            conn = preview.Connection(self.fake.send)
            self.assertEqual(preview.read_template(conn, REPO, "bug_report.md")["labels"], want, line)


class OnlyWhatExists(Base):
    """Criterion 2: labels, assignee and milestone are chosen from those that exist."""

    def test_each_one_is_looked_up_and_shown(self):
        printed = self.ready()
        for line in ('label "bug": exists, id 7001', 'label "export": exists, id 7011', 'assignee "robin-fixture": can be assigned in this repository',
                     'milestone "Sprint 13": exists, is open, number 3', "the repository has 6 labels and 3 milestones to choose from"):
            self.assertIn("     " + line, printed)

    def test_an_assignee_who_cannot_be_assigned_is_refused(self):
        printed = self.refused('GitHub says "stranger-fixture" cannot be assigned to issues in this repository', assignees=["stranger-fixture"])
        self.assertIn('assignee "stranger-fixture": CANNOT BE ASSIGNED', printed)

    def test_a_milestone_that_is_missing_closed_or_not_unique_is_refused(self):
        self.refused('the repository has no milestone with exactly the title "Sprint 99"', milestone="Sprint 99")
        self.refused('the milestone "Sprint 12" is closed', milestone="Sprint 12")
        self.fake.repo()["milestones"].append({"number": 9, "title": "Sprint 13", "state": "open"})
        self.refused("more than one milestone with exactly the title", milestone="Sprint 13")

    def test_the_label_the_template_gives_must_be_in_the_draft(self):
        self.refused('the template gives issues of this kind the label "bug", and the draft does not have it', labels=["export"],
                     sources=[line for line in SOURCES])

    def test_a_label_is_written_as_the_repository_writes_it(self):
        self.ready(labels=["BUG", "Export"])
        self.assertEqual(self.record()["payload"]["labels"], ["bug", "export"])

    def test_the_same_label_or_assignee_twice_is_refused(self):
        self.refused('the label "Bug" is in the draft twice', labels=["bug", "Bug", "export"])
        self.refused("is in the draft twice", assignees=["robin-fixture", "Robin-Fixture"])

    def test_a_draft_with_no_assignee_and_no_milestone_is_fine(self):
        printed = self.ready(assignees=[], milestone=None, sources=SOURCES[:3])
        self.assertIn("milestone: none asked for", printed)
        self.assertEqual(sorted(self.record()["payload"]), ["body", "labels", "title"])


class Refusals(Base):
    """Criterion 3: a missing template section or unknown label stops the preview with a reason."""

    def test_an_unknown_label_stops_the_preview_and_is_not_created(self):
        printed = self.refused('the label "data-quality" does not exist in the repository. The preview does not invent labels', labels=["bug", "export", "data-quality"])
        self.assertIn('label "data-quality": DOES NOT EXIST in the repository', printed)
        self.assertEqual(len(self.fake.repo()["labels"]), 6)

    def test_a_required_section_that_is_missing_stops_the_preview(self):
        printed = self.refused('the required template section "What you expected" is missing from the draft', sections=SECTIONS[:2])
        self.assertIn('section "What you expected" (required): MISSING from the draft', printed)

    def test_a_required_section_holding_only_the_template_s_placeholder_is_empty(self):
        for text in ("1.", "", "   \n\n", "<!-- nothing yet -->", "1.\n\n<!-- to do -->"):
            printed = self.refused('the required template section "Steps to reproduce" is empty', sections=[SECTIONS[0], ("Steps to reproduce", text)] + SECTIONS[2:])
            self.assertIn('section "Steps to reproduce" (required): EMPTY', printed)
        self.refused('the required template section "What happened" is empty',
                     sections=[("What happened", "<!-- Say what you saw. Quote any error text exactly. -->")] + SECTIONS[1:])

    def test_a_refused_preview_shows_no_payload_and_says_why_nothing_can_be_sent(self):
        printed = self.refused("7. THE EXACT PAYLOAD. Not shown: the draft cannot be sent as it is", labels=["bug", "nope"])
        self.assertIn("RESULT: NOT READY. 1 reason:", printed)
        self.assertIn("No fingerprint is given and no payload was saved, so there is nothing a write could send", printed)

    def test_every_reason_is_listed_not_only_the_first(self):
        printed = self.refused("RESULT: NOT READY. 3 reasons:", labels=["bug", "nope"], milestone="Sprint 99", sections=SECTIONS[:2])
        for words in ("is missing from the draft", 'the label "nope" does not exist', 'no milestone with exactly the title "Sprint 99"'):
            self.assertIn(words, printed)

    def test_a_draft_that_is_not_a_draft_stops_at_once(self):
        for text in ("no front matter", draft_text().replace("github-issue-draft/1", "other/1"), draft_text().replace("## Sources", "## Notes"),
                     draft_text(title=""), draft_text().replace('title: "Export', "title: Export"), draft_text(repo="nameonly"), draft_text(template="../x.md")):
            code, printed = self.go(text=text)
            self.assertEqual(code, 1)
            self.assertIn("STOPPED", printed)
            self.assertEqual(self.fake.calls, [])


class DuplicateAndPermission(Base):
    """Criterion 4: the duplicate result and the permission check appear in the preview."""

    def test_a_weaker_candidate_is_shown_and_does_not_stop_the_preview(self):
        printed = self.ready(sections=[("What happened", "The export of `orders-march.csv` with `export.py` in `v2.3.1` writes two date formats.")] + SECTIONS[1:])
        self.assertIn("5. DUPLICATE CHECK.", printed)
        self.assertRegex(printed, r'candidate acme-fixture/tracker#102 "Export is slow on large files", open: low confidence, \d of 14 points')
        self.assertIn("to LINK: the new issue should point to", printed)
        self.assertIn("duplicate result: link", printed)
        self.assertEqual(self.record()["duplicate"]["result"], "link")

    def test_no_duplicate_says_so(self):
        printed = self.ready(labels=["bug"], sources=SOURCES)
        self.assertIn("duplicate result: proceed. No likely duplicate was found", printed)
        self.assertIn("searched the local index", printed)

    def test_a_likely_duplicate_stops_the_preview_and_says_how_a_person_goes_on(self):
        printed = self.refused("the duplicate search reports acme-fixture/tracker#101 as a LIKELY DUPLICATE at high confidence", title="Out of memory when saving the March orders",
                               sections=MEMORY, sources=MEMORY_SOURCES, assignees=[], milestone=None)
        self.assertIn("a person runs the preview again with --despite-duplicate acme-fixture/tracker#101", printed)
        self.assertIn("The search recommends: close-as-duplicate", printed)

    def test_a_person_s_override_makes_it_ready_and_is_recorded(self):
        printed = self.ready(title="Out of memory when saving the March orders", sections=MEMORY, sources=MEMORY_SOURCES, assignees=[], milestone=None,
                             despite=["acme-fixture/tracker#101"])
        self.assertIn("OVERRIDDEN BY A PERSON: the preview was told to go on despite acme-fixture/tracker#101. That is recorded in the preview", printed)
        self.assertEqual(self.record()["duplicate"]["overridden"], ["acme-fixture/tracker#101"])
        self.assertEqual(self.record()["duplicate"]["result"], "close-as-duplicate")

    def test_an_override_must_name_the_issue_the_search_reported(self):
        self.refused("--despite-duplicate names acme-fixture/tracker#102, which the search did not report", title="Out of memory when saving the March orders",
                     sections=MEMORY, sources=MEMORY_SOURCES, assignees=[], milestone=None, despite=["acme-fixture/tracker#102"])
        self.refused("which the search did not report", despite=["acme-fixture/tracker#101"])
        self.assertIn("takes an issue as OWNER/NAME#NUMBER", self.go(despite=["101"])[1])

    def test_an_index_that_is_stale_stops_the_preview(self):
        folder = os.path.join(self.dir, "duplicates")
        self.index = duplicates_fixture(folder)
        self.addCleanup(setattr, self, "index", type(self).index)
        with open(os.path.join(folder, "records", "extra.md"), "w") as f:
            f.write("not a record")
        code, printed = self.go()
        self.assertEqual(code, 1)
        self.assertIn("the duplicate search could not run: the index is NOT what its records give now", printed)

    def test_the_permission_check_is_shown(self):
        printed = self.ready()
        self.assertIn("6. PERMISSION CHECK.", printed)
        self.assertIn("     GitHub says the ACCOUNT may: admin: no, maintain: no, pull: yes, push: yes, triage: yes", printed)
        self.assertIn("issues are turned on in this repository, and it is not archived", printed)
        self.assertIn("does not say what the TOKEN may do. Whether it may create an issue is known only when the write is tried. The preview does not try it", printed)

    def test_an_account_that_may_not_triage_cannot_set_labels_and_github_would_drop_them(self):
        self.fake.repo()["permissions"] = {"admin": False, "maintain": False, "push": False, "triage": False, "pull": True}
        self.refused("GitHub would create the issue and DROP them without saying")
        self.fake.repo()["templates"]["bug_report.md"] = fake_github.BUG_TEMPLATE.replace("labels: bug", "labels: ''")
        self.ready(labels=[], assignees=[], milestone=None, sources=SOURCES[:2])

    def test_an_archived_repository_issues_turned_off_and_no_stated_permissions_are_not_ready(self):
        self.fake.repo()["archived"] = True
        self.refused("the repository is archived")
        self.fake.repo().update(archived=False, has_issues=False)
        self.refused("issues are turned off in this repository")
        self.fake.repo().update(has_issues=True, permissions=None)
        self.refused("GitHub did not say what the account may do")

    def test_a_classic_token_s_scopes_are_reported(self):
        self.fake.store["scopes"] = "repo"
        self.assertIn('The token\'s scopes, as GitHub reports them: "repo"', self.ready())


class ExactPayload(Base):
    """Criterion 5: the preview contains the exact payload, not a summary."""

    def bytes_printed(self, printed):
        lines = printed.splitlines()
        start = next(number for number, line in enumerate(lines) if "the exact bytes" in line)
        return lines[start + 1].split("github-preview:      ", 1)[1]

    def test_the_bytes_printed_are_the_payload_s_bytes_and_their_checksum(self):
        printed = self.ready()
        shown = self.bytes_printed(printed)
        payload = self.record()["payload"]
        self.assertEqual(shown.encode("utf-8"), preview.payload_bytes(payload))
        self.assertEqual(json.loads(shown), payload)
        self.assertIn("the exact bytes, %d of them, SHA-256 %s:" % (len(shown.encode("utf-8")), hashlib.sha256(shown.encode("utf-8")).hexdigest()), printed)

    def test_the_payload_holds_exactly_the_fields_of_the_draft(self):
        self.ready()
        self.assertEqual(self.record()["payload"], {
            "title": "Export writes dates in two formats", "labels": ["bug", "export"], "assignees": ["robin-fixture"], "milestone": 3,
            "body": "### What happened\n\nThe export writes dates in two different formats in the same file.\n\n### Steps to reproduce\n\n1. Run the export.\n"
                    "2. Open the file.\n\n### What you expected\n\nEvery date written the same way.\n\n### Environment (optional)\n\nThe March file."})
        self.assertEqual(self.record()["request"], {"method": "POST", "path": "/repos/acme-fixture/tracker/issues"})

    def test_the_milestone_is_sent_as_its_number_and_shown_with_its_title(self):
        printed = self.ready(milestone="Sprint 14")
        self.assertIn('     milestone  4 ("Sprint 14")', printed)
        self.assertEqual(self.record()["payload"]["milestone"], 4)

    def test_the_body_is_the_draft_s_body_character_for_character(self):
        odd = "Tabs\there, two spaces at the end  \n\n```yaml\na: 1\n\n  b: |\n```\n\n| a | b |\n|---|---|\nÜnïcödé \U0001f9f5 \"quotes\" \\ backslash"
        self.ready(sections=[("What happened", odd)] + SECTIONS[1:3])
        body = self.record()["payload"]["body"]
        self.assertTrue(body.startswith("### What happened\n\n" + odd + "\n\n### Steps to reproduce"))
        self.assertEqual(json.loads(preview.payload_bytes(self.record()["payload"]).decode("utf-8"))["body"], body)

    def test_the_payload_file_shows_it_field_by_field_and_as_bytes(self):
        printed = self.ready()
        with open(self.payload_file, encoding="utf-8") as f:
            text = f.read()
        record = self.record()
        for line in ('- repository: "acme-fixture/tracker", id 401', "- request: `POST /repos/acme-fixture/tracker/issues`", "- preview fingerprint: `%s`" % record["fingerprint"],
                     "- SHA-256 of the payload's bytes: `%s`" % record["payload_sha256"], '| `title` | "Export writes dates in two formats" | text |',
                     '| `labels` | ["bug", "export"] | a list of the names of labels that exist |', '| `milestone` | 3, which is the number of "Sprint 13" | the milestone\'s number, not its title |',
                     self.bytes_printed(printed)):
            self.assertIn(line, text)
        self.assertIn("```\n" + record["payload"]["body"] + "\n```", text)

    def test_a_field_the_draft_does_not_set_is_not_sent_and_the_file_says_so(self):
        self.ready(assignees=[], milestone=None, sources=SOURCES[:3])
        with open(self.payload_file, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("| `assignees` | not sent: the draft has none |", text)
        self.assertIn("| `milestone` | not sent: the draft has none |", text)
        self.assertNotIn('"milestone"', text.split("## The exact bytes")[1])

    def test_the_bytes_do_not_depend_on_the_order_the_payload_is_held_in(self):
        self.ready()
        payload = self.record()["payload"]
        backwards = dict(reversed(list(payload.items())))
        self.assertNotEqual(list(backwards), list(payload))
        self.assertEqual(preview.payload_bytes(backwards), preview.payload_bytes(payload))
        self.assertTrue(preview.payload_bytes(payload).startswith(b'{"title":'))
        with self.assertRaises(preview.Stop):
            preview.payload_bytes(dict(payload, state="closed"))

    def test_the_payload_is_built_in_one_place(self):
        with open(os.path.join(SKILL, "preview.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertEqual(code.count("build_payload("), 2)             # its definition, and the one call
        self.assertEqual(code.count("def payload_bytes("), 1)
        self.assertEqual(code.count("separators="), 1)

    def test_the_fingerprint_changes_with_the_draft_the_payload_and_the_checks(self):
        marks = set()
        for more in ({}, {"title": "Another title"}, {"milestone": "Sprint 14"}, {"sections": SECTIONS[:3]}, {"labels": ["bug"]}):
            marks.add(re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", self.ready(**more)).group(1))
        self.assertEqual(len(marks), 5)

    def test_the_saved_preview_holds_the_payload_and_its_checksum(self):
        printed = self.ready()
        record = self.record()
        self.assertEqual(record["payload_sha256"], hashlib.sha256(preview.payload_bytes(record["payload"])).hexdigest())
        self.assertEqual(os.listdir(self.state), [record["fingerprint"] + ".json"])
        self.assertIn("Saved for a later write, good for 15 minutes from 2026-11-24T09:00:00Z by GitHub's clock", printed)


class NothingWritten(Base):
    """Criterion 6: running the preview changes nothing on GitHub."""

    def test_every_request_is_a_get_and_the_repository_is_as_it_was(self):
        before = self.fake.snapshot()
        printed = self.ready()
        self.assertEqual({method for method, _ in self.fake.calls}, {"GET"})
        self.assertEqual(self.fake.snapshot(), before)
        self.assertIn("Requests made by this command: %d, every one a GET" % len(self.fake.calls), printed)

    def test_the_preview_reads_the_repository_at_the_start_and_the_end_and_compares(self):
        printed = self.ready()
        self.assertIn("8. NOTHING WAS WRITTEN. The repository was read at the start and again at the end. Newest issue number: 107 then 107. "
                      "Labels: 6 then 6. Milestones: 3 then 3. The same", printed)

    def test_a_repository_that_changes_during_the_preview_is_not_ready(self):
        def meanwhile(method, path):
            if "/contents/" in path:
                self.fake.repo()["newest_issue"] = 108
        self.fake.before = meanwhile
        code, printed = self.go()
        self.assertEqual(code, 1)
        self.assertIn("Newest issue number: 107 then 108", printed)
        self.assertIn("DIFFERENT: someone changed the repository during the preview", printed)
        self.assertFalse(os.path.exists(self.state))

    def test_the_connection_has_no_way_to_write(self):
        conn = preview.Connection(self.fake.send)
        self.assertEqual([name for name in dir(conn) if not name.startswith("_")], ["asked", "get", "now", "scopes", "waits"])

    def test_the_live_sender_refuses_anything_but_get_before_contacting_anything(self):
        for method in ("POST", "PATCH", "PUT", "DELETE"):
            with self.assertRaises(RuntimeError):
                preview.live_send(method, "/repos/acme-fixture/tracker/issues", None, {"title": "x"})
        with self.assertRaises(RuntimeError):
            preview.live_send("GET", "/user", None, {"a": 1})

    def test_the_skill_has_no_code_that_sends_a_write(self):
        with open(os.path.join(SKILL, "preview.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertEqual(re.findall(r'method="([A-Z]+)"', code), ["GET"])
        self.assertEqual(code.count("self._send("), 1)
        self.assertIn('self._send("GET", path', code)
        for word in ("subprocess", "os.system", "eval(", "exec(", "shutil", "os.remove"):
            self.assertNotIn(word, code)

    def test_a_rejected_token_a_moved_repository_and_a_rate_limit_stop_it(self):
        self.fake.fail("/user", 401)
        self.assertIn("rejected the token (401)", self.go()[1])
        self.fake.fail("/repos/acme-fixture/tracker", 301)
        self.assertIn("the preview does not follow it", self.go()[1])
        self.fake.fail("/user", 429, times=9, headers={"Retry-After": "2"})
        self.assertEqual(self.go()[0], 2)
        self.assertEqual(self.conn.waits, [2, 2, 2])


class Sources(Base):
    """Criterion 7: source citations are included."""

    def test_each_citation_is_checked_and_shown(self):
        printed = self.ready()
        self.assertIn("4. SOURCES. 5 citations checked against the file and lines each one names:", printed)
        for line in ("title: notes.md, line 3. The words quoted are there", "body: notes.md, lines 4-5. The words quoted are there", "milestone: notes.md, line 7. The words quoted are there"):
            self.assertIn("     " + line, printed)

    def test_words_that_are_not_on_the_lines_named_are_refused(self):
        self.refused("the citation for title is NOT TRUE: the words quoted are not on line 3 of notes.md",
                     sources=['- title: notes.md line 3: "The export writes dates in three formats"'] + SOURCES[1:])
        self.refused("the citation for title is NOT TRUE", sources=['- title: notes.md line 4: "The export writes dates in two different formats"'] + SOURCES[1:])
        self.refused("the citation for body is NOT TRUE", sources=[SOURCES[0], '- body: notes.md lines 40-41: "2026-03-04"'] + SOURCES[2:])

    def test_a_source_that_changed_after_the_draft_was_written_fails(self):
        with open(os.path.join(self.dir, "notes.md"), "w", encoding="utf-8") as f:
            f.write(NOTES.replace("two different formats", "several formats"))
        self.refused("the citation for title is NOT TRUE")

    def test_a_field_with_no_citation_is_refused(self):
        self.refused("the draft gives no source for its title", sources=SOURCES[1:])
        self.refused("the draft gives no source for its milestone", sources=SOURCES[:4])
        self.refused("the draft gives no source for its body", sources=[SOURCES[0]] + SOURCES[2:])

    def test_a_source_outside_the_draft_s_folder_or_missing_is_refused(self):
        self.refused("the citation for title points outside the draft's folder", sources=['- title: ../notes.md line 3: "The export"'] + SOURCES[1:])
        self.refused("the citation for title points outside the draft's folder", sources=['- title: %s line 3: "The export"' % os.path.join(self.dir, "notes.md")] + SOURCES[1:])
        self.refused("names a file that cannot be read: gone.md", sources=['- title: gone.md line 3: "The export"'] + SOURCES[1:])

    def test_a_line_that_is_not_a_citation_and_empty_quoted_words_are_refused(self):
        self.refused("a line under Sources is not a citation this workflow can read", sources=SOURCES + ["- see the notes"])
        self.refused("not a citation this workflow can read", sources=SOURCES + ['- colour: notes.md line 3: "The export"'])
        self.refused("the citation for title is NOT TRUE", sources=['- title: notes.md line 3: " "'] + SOURCES[1:])

    def test_line_breaks_in_the_source_do_not_stop_a_quote_that_runs_over_two_lines(self):
        self.ready(sources=[SOURCES[0], '- body: notes.md lines 4-5: "in others.   They expected"'] + SOURCES[2:])


class AllowlistAndCommandLine(Base):
    def main(self, *argv, env=None):
        printed, old = io.StringIO(), dict(os.environ)
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.update(env or {})
        try:
            with contextlib.redirect_stdout(printed):
                code = preview.main(list(argv))
        finally:
            os.environ.clear()
            os.environ.update(old)
        return code, printed.getvalue()

    def test_a_repository_off_the_allowlist_is_refused_before_any_request(self):
        code, printed = self.go(repo=OTHER)
        self.assertEqual(code, 1)
        self.assertIn('the repository "acme-fixture/production" is NOT ON THE SANDBOX ALLOWLIST', printed)
        self.assertEqual(self.fake.calls, [])
        with open(self.allow, "w") as f:
            f.write("not json")
        self.assertIn("so no repository is allowed", self.go()[1])
        self.assertEqual(self.fake.calls, [])

    def test_from_the_command_line_with_a_made_up_github_kept_in_a_file(self):
        store = os.path.join(self.dir, "github.json")
        with contextlib.redirect_stdout(io.StringIO()):
            fake_github.main([store, "new"])
        path = os.path.join(self.dir, "draft.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(draft_text())
        before = fake_github.load(store).snapshot()
        code, printed = self.main("--source", "fake", "--fake-store", store, "--draft", path, "--index", self.index, "--allowlist", self.allow, "--payload-out", self.payload_file)
        self.assertEqual(code, 0, printed)
        after = fake_github.load(store)
        self.assertEqual(after.snapshot(), before)
        self.assertEqual(after.not_gets(), [])
        self.assertTrue(os.path.exists(self.payload_file))

    def test_a_live_run_keeps_its_files_outside_the_repository_and_needs_the_token(self):
        inside = os.path.join(SKILL, "draft.md")
        code, printed = self.main("--source", "live", "--draft", inside, "--index", self.index, "--allowlist", self.allow, env=dict([("GITHUB_TOKEN", PRETEND)]))
        self.assertEqual(code, 1)
        self.assertIn("outside this repository, because they name a real account. Give --draft", printed)
        outside = os.path.join(self.dir, "draft.md")
        code, printed = self.main("--source", "live", "--draft", outside, "--index", self.index, "--allowlist", self.allow, "--state", os.path.join(SKILL, "state"),
                                  env=dict([("GITHUB_TOKEN", PRETEND)]))
        self.assertIn("Give --state", printed)
        code, printed = self.main("--source", "live", "--draft", outside, "--index", self.index, "--allowlist", self.allow)
        self.assertEqual(code, 1)
        self.assertIn("GITHUB_TOKEN is not set", printed)
        self.assertNotIn(PRETEND, printed)


if __name__ == "__main__":
    unittest.main()

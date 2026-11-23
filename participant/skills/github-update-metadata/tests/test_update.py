"""Tests for the github-update-metadata skill. Every test runs against fake_github.py. None contacts GitHub."""
import argparse
import contextlib
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
import update  # noqa: E402
from fake_github import ISSUE, OTHER, PULL, REPO, FakeGitHub  # noqa: E402

PRETEND = "-".join(("made", "up", "value", "for", "the", "tests", "only"))
ADD = ["label.add=in progress"]
SWAP = ["label.add=in progress", "label.remove=needs triage"]
BASE = "/repos/acme-fixture/sandbox/issues/7"


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name
        self.allow = os.path.join(self.dir, "allow.json")
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": [REPO]}, f)
        self.state, self.results = os.path.join(self.dir, "state"), os.path.join(self.dir, "results")
        self.fake = FakeGitHub()

    def go(self, command, changes, repo=REPO, issue=ISSUE, **more):
        """Run one command. Returns (exit code, what it printed)."""
        args = argparse.Namespace(command=command, source="fake", repo=repo, issue=issue, change=list(changes), allowlist=self.allow,
                                  state=self.state, results=self.results, fingerprint=None, confirmed_by=None)
        for key, value in more.items():
            setattr(args, key, value)
        self.conn = update.Connection(self.fake.send, sleep=lambda seconds: None, clock=lambda: 0)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = update.run(args, self.conn)
        return code, printed.getvalue()

    def preview(self, changes, **more):
        """A preview that must come out READY. Returns its fingerprint."""
        code, printed = self.go("preview", changes, **more)
        self.assertEqual(code, 0, printed)
        self.assertIn("RESULT: READY", printed)
        return re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", printed).group(1)

    def confirm(self, changes, mark, name="the participant", **more):
        return self.go("confirm", changes, fingerprint=mark, confirmed_by=name, **more)

    def labels(self):
        return self.fake.issue()["labels"]

    def saved(self):
        return sorted(os.listdir(self.state)) if os.path.isdir(self.state) else []

    def record(self):
        with open(os.path.join(self.results, "update-metadata.md"), encoding="utf-8") as f:
            return f.read()


class OldAndNew(Base):
    """Criterion 1: the preview shows the old and new value of each field."""

    def test_the_preview_shows_all_three_fields_old_and_new(self):
        _, printed = self.go("preview", SWAP + ["milestone.set=Sprint 13", "assignee.add=kit-fixture"])
        lines = [line.split(": ", 1)[1] for line in printed.splitlines()]
        start = lines.index("4. OLD AND NEW VALUES of every field this workflow can change:")
        self.assertEqual(lines[start + 1:start + 7], [
            '     old:       labels     ["bug", "needs triage"]',
            '                assignees  ["robin-fixture"]',
            '                milestone  "Sprint 12" (number 1)',
            '     new:       labels     ["bug", "in progress"]',
            '                assignees  ["kit-fixture", "robin-fixture"]',
            '                milestone  "Sprint 13" (number 3)'])

    def test_a_field_that_is_not_changed_is_shown_too_with_the_same_value(self):
        _, printed = self.go("preview", ADD)
        self.assertEqual(printed.count('assignees  ["robin-fixture"]'), 2)
        self.assertEqual(printed.count('milestone  "Sprint 12" (number 1)'), 2)

    def test_the_preview_says_in_words_what_differs(self):
        _, printed = self.go("preview", SWAP + ["milestone.clear=yes"])
        self.assertIn('difference: labels: added "in progress", removed "needs triage"', printed)
        self.assertIn('difference: milestone: "Sprint 12" (number 1) became none', printed)

    def test_the_preview_shows_the_exact_requests(self):
        _, printed = self.go("preview", SWAP + ["milestone.set=Sprint 13", "assignee.remove=robin-fixture"])
        self.assertIn("EXACT REQUESTS a confirmation would send, in this order: 4", printed)
        for line in ('DELETE %s/assignees {"assignees": ["robin-fixture"]}' % BASE, 'POST %s/labels {"labels": ["in progress"]}' % BASE,
                     "DELETE %s/labels/needs%%20triage" % BASE, 'PATCH %s {"milestone": 3}' % BASE):
            self.assertIn("     " + line, printed)

    def test_the_new_values_are_what_the_issue_holds_after_the_update(self):
        changes = SWAP + ["milestone.set=Sprint 13", "assignee.add=kit-fixture"]
        self.confirm(changes, self.preview(changes))
        issue = self.fake.issue()
        self.assertEqual((sorted(issue["labels"]), sorted(issue["assignees"]), issue["milestone"]), (["bug", "in progress"], ["kit-fixture", "robin-fixture"], 3))

    def test_a_value_from_github_is_printed_as_json_and_cannot_break_a_line(self):
        self.fake.store["repos"][REPO]["labels"].append({"id": 7099, "name": "odd\nRESULT: READY", "color": "ffffff", "description": None})
        self.fake.issue()["labels"].append("odd\nRESULT: READY")
        _, printed = self.go("preview", ADD)
        self.assertIn('"odd\\nRESULT: READY"', printed)
        self.assertEqual(printed.count("\nRESULT:") + printed.count("github-update: RESULT:"), 1)


class SupportedOnly(Base):
    """Criterion 2: only supported fields can be changed."""

    def refused(self, changes, words):
        code, printed = self.go("preview", changes)
        self.assertEqual(code, 1, changes)
        self.assertIn(words, printed)
        self.assertIn("RESULT: NOT READY", printed)
        self.assertNotIn("FINGERPRINT", printed)
        self.assertEqual(self.saved(), [])
        self.assertEqual(self.fake.writes(), [])
        return printed

    def test_every_field_on_the_refused_list_is_refused_with_its_reason(self):
        for field, reason in update.NOT_SUPPORTED.items():
            printed = self.refused(["%s=x" % (field if field != "project" else "project.status")], "NOT SUPPORTED: " + reason)
            self.assertIn("REFUSED", printed)

    def test_a_project_field_is_refused(self):
        self.refused(["project.status=Done"], "project fields live in GitHub Projects")
        self.refused(["projects.priority=High"], "project fields live in GitHub Projects")

    def test_a_field_nobody_has_heard_of_is_refused(self):
        self.refused(["reviewers.add=kit-fixture"], "it is not a field this workflow knows")

    def test_one_refused_change_stops_the_whole_preview(self):
        self.refused(ADD + ["title=New title"], "the title is content")

    def test_replacing_the_whole_list_of_labels_is_refused(self):
        self.refused(["label.set=in progress"], "is how a label that someone else added gets removed")

    def test_a_label_the_repository_does_not_have_is_refused_and_not_created(self):
        self.refused(["label.add=brand new"], "the repository has no label of that name")
        self.assertEqual(len(self.fake.store["repos"][REPO]["labels"]), 5)

    def test_a_person_who_cannot_be_assigned_is_refused(self):
        self.refused(["assignee.add=stranger-fixture"], "cannot be assigned to issues in this repository")

    def test_a_closed_or_missing_milestone_is_refused(self):
        self.refused(["milestone.set=Sprint 11"], "that milestone is closed")
        self.refused(["milestone.set=Sprint 99"], "has no milestone with exactly that title")
        self.refused(["milestone.set=sprint 13"], "has no milestone with exactly that title")

    def test_two_milestones_with_one_title_are_refused(self):
        self.fake.store["repos"][REPO]["milestones"].append({"number": 4, "title": "Sprint 13", "state": "open"})
        self.refused(["milestone.set=Sprint 13"], "more than one milestone with exactly that title")

    def test_asking_for_a_thing_and_its_opposite_is_refused(self):
        self.refused(["label.add=urgent", "label.remove=Urgent"], "also asks for the opposite")
        self.refused(["milestone.set=Sprint 13", "milestone.clear=yes"], "also asks for the opposite")

    def test_a_value_that_is_empty_too_long_or_not_one_line_is_refused(self):
        for change in ("label.add=", "label.add", "label.add=" + "x" * 101, "label.add=a\nb", "milestone.clear=no", "assignee.add=not a login"):
            self.refused([change], "REFUSED")

    def test_the_same_change_twice_and_too_many_changes_are_refused(self):
        self.refused(["label.add=urgent", "label.add=urgent"], "asked for twice")
        code, printed = self.go("preview", ["label.add=x%d" % n for n in range(11)])
        self.assertEqual(code, 1)
        self.assertIn("at most 10 changes", printed)

    def test_a_pull_request_is_refused(self):
        code, printed = self.go("preview", ADD, issue=PULL)
        self.assertEqual(code, 1)
        self.assertIn("is a pull request", printed)
        self.assertEqual(self.saved(), [])

    def test_a_label_is_matched_whatever_its_capitals_and_written_as_github_writes_it(self):
        _, printed = self.go("preview", ["label.add=docs", "label.remove=BUG"])
        self.assertIn('label.add="Docs": WILL CHANGE', printed)
        self.assertIn('label.remove="bug": WILL CHANGE', printed)
        self.assertIn('POST %s/labels {"labels": ["Docs"]}' % BASE, printed)

    def test_the_supported_fields_are_exactly_six(self):
        self.assertEqual(update.SUPPORTED, ("label.add", "label.remove", "assignee.add", "assignee.remove", "milestone.set", "milestone.clear"))


class Stale(Base):
    """Criterion 3: a field changed on GitHub after the preview stops the update."""

    def stale(self, meanwhile, changes=SWAP):
        mark = self.preview(changes)
        self.fake.someone_else(meanwhile)
        before = self.fake.snapshot()
        code, printed = self.confirm(changes, mark)
        self.assertEqual(code, 1, printed)
        self.assertIn("REFUSED: STALE: a field changed on GitHub after the preview", printed)
        self.assertIn("Nothing was written.", printed)
        self.assertEqual(self.fake.writes(), [])
        self.assertEqual(self.fake.snapshot(), before)
        return printed

    def test_the_scenario_a_label_added_by_a_maintainer_after_the_preview_stops_the_update_and_stays(self):
        printed = self.stale("label.add=urgent")
        self.assertIn('MOVED since the preview: labels: added "urgent"', printed)
        self.assertEqual(self.labels(), ["bug", "needs triage", "urgent"])

    def test_the_refusal_shows_the_preview_s_values_and_the_values_now(self):
        printed = self.stale("label.add=urgent")
        self.assertIn('preview:   labels     ["bug", "needs triage"]', printed)
        self.assertIn('now:       labels     ["bug", "needs triage", "urgent"]', printed)

    def test_a_label_removed_meanwhile_stops_the_update(self):
        self.assertIn('labels: removed "bug"', self.stale("label.remove=bug"))

    def test_a_change_to_a_field_the_update_does_not_touch_stops_it_too(self):
        self.assertIn('MOVED since the preview: milestone: "Sprint 12" (number 1) became "Sprint 13" (number 3)', self.stale("milestone.set=3"))
        self.assertIn('MOVED since the preview: assignees: added "kit-fixture"', self.stale("assignee.add=kit-fixture"))

    def test_the_very_change_asked_for_made_by_someone_else_meanwhile_stops_it(self):
        self.stale("label.add=in progress", changes=ADD)

    def test_a_new_comment_is_not_metadata_and_does_not_stop_the_update(self):
        mark = self.preview(ADD)
        self.fake.someone_else("comment")
        code, printed = self.confirm(ADD, mark)
        self.assertEqual(code, 0, printed)
        self.assertIn("HAS ANYTHING MOVED? No.", printed)

    def test_after_a_stale_refusal_a_new_preview_shows_the_issue_as_it_is_now(self):
        self.stale("label.add=urgent", changes=ADD)
        mark = self.preview(ADD)
        code, _ = self.confirm(ADD, mark)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(self.labels()), ["bug", "in progress", "needs triage", "urgent"])

    def test_a_change_in_the_moment_between_the_check_and_the_write_is_not_overwritten_and_is_reported(self):
        mark = self.preview(SWAP)

        def meanwhile(method, path):
            if method == "POST" and self.fake.before:
                self.fake.before = None
                self.fake.someone_else("label.add=urgent")
        self.fake.before = meanwhile
        code, printed = self.confirm(SWAP, mark)
        self.assertEqual(code, 3, printed)
        self.assertIn("RESULT: NEEDS LOOKING", printed)
        self.assertIn('THIS IS NOT what the preview promised: labels: added "urgent"', printed)
        self.assertEqual(sorted(self.labels()), ["bug", "in progress", "urgent"])
        self.assertIn("- outcome: NEEDS LOOKING", self.record())

    def test_no_request_ever_carries_the_whole_list_of_labels(self):
        mark = self.preview(SWAP + ["milestone.set=Sprint 13"])
        self.confirm(SWAP + ["milestone.set=Sprint 13"], mark)
        for method, path, body in self.fake.writes():
            self.assertFalse(method == "PATCH" and "labels" in (body or {}))
            self.assertNotEqual(method, "PUT")
            if body and "labels" in body:
                self.assertEqual(len(body["labels"]), 1)


class PreviewWritesNothing(Base):
    """Criterion 4: a preview shows the repository and the exact changes, and nothing is written before the human confirms."""

    def test_a_preview_sends_only_get_and_changes_nothing(self):
        before = self.fake.snapshot()
        _, printed = self.go("preview", SWAP + ["milestone.clear=yes", "assignee.add=kit-fixture"])
        self.assertEqual({method for method, _, _ in self.fake.calls}, {"GET"})
        self.assertEqual(self.fake.snapshot(), before)
        self.assertIn("Requests made by this command: %d, every one a GET" % len(self.fake.calls), printed)

    def test_the_preview_names_the_repository_the_issue_and_the_account(self):
        _, printed = self.go("preview", ADD)
        self.assertIn('1. WHERE. Repository "acme-fixture/sandbox", id 401, private. Issue 7, node ID I_kwFX4010007, state open. '
                      'The connection acts as login "robin-fixture"', printed)

    def test_the_preview_reads_the_issue_again_at_the_end_and_says_it_is_the_same(self):
        _, printed = self.go("preview", ADD)
        found = re.search(r"before: ([0-9a-f]{16})\. After: ([0-9a-f]{16})\. The same", printed)
        self.assertEqual(found.group(1), found.group(2))

    def test_an_issue_that_changes_during_the_preview_is_not_ready(self):
        def meanwhile(method, path):
            if path.endswith("/milestones") and self.fake.before:
                self.fake.before = None
                self.fake.someone_else("label.add=urgent")
        self.fake.before = meanwhile
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("DIFFERENT: someone changed the issue during this preview", printed)
        self.assertEqual(self.saved(), [])

    def test_a_connection_cannot_write_until_one_issue_is_allowed(self):
        conn = update.Connection(self.fake.send)
        with self.assertRaises(update.Refused):
            conn.write("POST", BASE + "/labels", {"labels": ["urgent"]})
        self.assertEqual(self.fake.calls, [])

    def test_a_write_outside_the_one_issue_is_not_sent(self):
        conn = update.Connection(self.fake.send)
        conn.allow_writes(REPO, ISSUE)
        for method, path in (("POST", "/repos/acme-fixture/sandbox/issues/70/labels"), ("PATCH", "/repos/acme-fixture/sandbox"),
                             ("DELETE", "/repos/acme-fixture/production/issues/7/labels/bug"), ("PUT", BASE + "/labels"),
                             ("POST", "/repos/acme-fixture/sandbox/labels")):
            with self.assertRaises(update.Refused):
                conn.write(method, path, {})
        self.assertEqual(self.fake.calls, [])

    def test_the_live_sender_made_for_a_preview_refuses_anything_but_get_before_contacting_anything(self):
        send = update.make_live(may_write=False)
        for method in ("POST", "PATCH", "DELETE", "PUT"):
            with self.assertRaises(RuntimeError):
                send(method, BASE, None, {})
        with self.assertRaises(RuntimeError):
            update.make_live(may_write=True)("PUT", BASE, None, {})

    def test_the_preview_command_has_no_code_path_to_a_write(self):
        with open(os.path.join(SKILL, "update.py"), encoding="utf-8") as f:
            code = f.read()
        preview = code[code.index("def cmd_preview"):code.index("# ---------------------------------------------------------------- confirm")]
        self.assertNotIn(".write(", preview)
        self.assertNotIn("allow_writes", preview)
        self.assertEqual(code.count("conn.allow_writes("), 1)
        self.assertEqual(code.count("conn.write("), 1)
        for word in ("subprocess", "os.system", "eval(", "exec(", "shutil"):
            self.assertNotIn(word, code)

    def test_without_a_ready_preview_there_is_no_fingerprint_to_confirm(self):
        self.go("preview", ["label.add=bug"])
        self.assertEqual(self.saved(), [])


class Checks(Base):
    """Criterion 5: the preview records the permission check and the duplicate check, or states where GitHub cannot perform one."""

    def test_the_preview_reports_what_the_account_may_do(self):
        _, printed = self.go("preview", ADD)
        self.assertIn("6. PERMISSION CHECK. GitHub says the ACCOUNT may change issues here (admin: no, maintain: no, pull: yes, push: yes, triage: yes)", printed)

    def test_the_preview_says_github_does_not_report_what_a_fine_grained_token_may_do(self):
        _, printed = self.go("preview", ADD)
        self.assertIn("does not say what the TOKEN may do", printed)
        self.assertIn("refused by GitHub with status 403, and nothing changes", printed)

    def test_the_scopes_of_a_classic_token_are_reported(self):
        self.fake.store["scopes"] = "repo, workflow"
        _, printed = self.go("preview", ADD)
        self.assertIn('The token\'s scopes, as GitHub reports them: "repo, workflow"', printed)

    def test_an_account_that_may_only_read_is_not_ready(self):
        self.fake.store["repos"][REPO]["permissions"] = {"admin": False, "maintain": False, "push": False, "triage": False, "pull": True}
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("the ACCOUNT MAY NOT change issues here", printed)
        self.assertIn("NOT READY. the account may not change issues here", printed)
        self.assertEqual(self.saved(), [])

    def test_triage_alone_is_enough(self):
        self.fake.store["repos"][REPO]["permissions"] = {"admin": False, "maintain": False, "push": False, "triage": True, "pull": True}
        self.preview(ADD)

    def test_a_repository_that_does_not_say_what_the_account_may_do_is_not_ready(self):
        del self.fake.store["repos"][REPO]["permissions"]
        real = self.fake._answer

        def without(method, path, params, body):
            status, headers, answer = real(method, path, params, body)
            if isinstance(answer, dict):
                answer.pop("permissions", None)
            return status, headers, answer
        self.fake._answer = lambda method, path, params, body: without(method, path, params, body) if path == "/repos/" + REPO else real(method, path, params, body)
        self.fake.store["repos"][REPO]["permissions"] = {}
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("GitHub did not say what the account may do", printed)

    def test_an_archived_repository_is_not_ready(self):
        self.fake.store["repos"][REPO]["archived"] = True
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("The repository is ARCHIVED", printed)

    def test_a_change_that_is_already_so_is_reported_and_not_sent(self):
        code, printed = self.go("preview", ["label.add=bug", "label.add=urgent", "assignee.add=robin-fixture"])
        self.assertEqual(code, 0)
        self.assertIn('label.add="bug": ALREADY SO, nothing is sent for it. the issue already has this label', printed)
        self.assertIn("7. DUPLICATE CHECK. Each change was compared with the issue as it is now. Already so, and not sent: 2.", printed)
        self.assertIn("in this order: 1", printed)
        self.assertIn("GitHub does not refuse a repeated change of this kind itself", printed)

    def test_every_kind_of_change_has_its_already_so(self):
        self.fake.issue()["milestone"] = None
        code, printed = self.go("preview", ["label.add=BUG", "label.remove=urgent", "assignee.add=Robin-Fixture", "assignee.remove=kit-fixture", "milestone.clear=yes"])
        self.assertEqual(code, 0)
        self.assertEqual(printed.count("ALREADY SO"), 5)
        self.assertIn("RESULT: NOTHING TO CHANGE", printed)
        self.fake.issue()["milestone"] = 3
        self.assertIn("the issue is already in this milestone", self.go("preview", ["milestone.set=Sprint 13"])[1])


class Allowlist(Base):
    """Criterion 6: the workflow writes only to a repository on an explicit sandbox allowlist and refuses any other."""

    def test_a_repository_off_the_allowlist_is_refused_before_any_request(self):
        for command in ("preview", "confirm"):
            code, printed = self.go(command, ADD, repo=OTHER, fingerprint="0" * 32, confirmed_by="the participant")
            self.assertEqual(code, 1)
            self.assertIn('the repository "acme-fixture/production" is NOT ON THE SANDBOX ALLOWLIST', printed)
            self.assertIn("No request was sent to GitHub", printed)
            self.assertEqual(self.fake.calls, [])

    def test_a_preview_made_for_the_sandbox_cannot_be_confirmed_against_another_repository(self):
        mark = self.preview(ADD)
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": [REPO, OTHER]}, f)
        calls = len(self.fake.calls)
        code, printed = self.confirm(ADD, mark, repo=OTHER)
        self.assertEqual(code, 1)
        self.assertIn("THE CHANGE DIFFERS FROM THE PREVIEW: the preview with this fingerprint is for another repository", printed)
        self.assertEqual(len(self.fake.calls), calls)
        self.assertEqual(self.fake.snapshot(repo=OTHER), FakeGitHub().snapshot(repo=OTHER))

    def test_a_repository_taken_off_the_allowlist_after_the_preview_is_refused(self):
        mark = self.preview(ADD)
        with open(self.allow, "w") as f:
            json.dump({"sandbox_repositories": []}, f)
        code, printed = self.confirm(ADD, mark)
        self.assertEqual(code, 1)
        self.assertIn("NOT ON THE SANDBOX ALLOWLIST", printed)
        self.assertEqual(self.fake.writes(), [])

    def test_an_allowlist_that_cannot_be_read_allows_nothing(self):
        for text in ("", "not json", "[]", '{"sandbox_repositories": "acme-fixture/sandbox"}', '{"other": []}'):
            with open(self.allow, "w") as f:
                f.write(text)
            code, printed = self.go("preview", ADD)
            self.assertEqual(code, 1, text)
            self.assertEqual(self.fake.calls, [])
        os.remove(self.allow)
        self.assertEqual(self.go("preview", ADD)[0], 1)

    def test_the_name_must_be_exactly_the_one_on_the_list(self):
        code, _ = self.go("preview", ADD, repo="Acme-Fixture/Sandbox")
        self.assertEqual(code, 1)
        self.assertEqual(self.fake.calls, [])

    def test_the_preview_says_which_list_and_how_many_it_names(self):
        _, printed = self.go("preview", ADD)
        self.assertIn("2. ALLOWLIST. The repository is on the sandbox allowlist", printed)
        self.assertIn("which names 1 repository", printed)


class Confirmation(Base):
    """Criterion 7: tied to a fingerprint of the exact preview, refused when missing or when the change differs, and it expires."""

    def refused(self, words, changes=ADD, **more):
        calls = len(self.fake.writes())
        before = self.fake.snapshot()
        code, printed = self.go("confirm", changes, **more)
        self.assertEqual(code, 1, printed)
        self.assertIn(words, printed)
        self.assertIn("Nothing was written.", printed)
        self.assertEqual(len(self.fake.writes()), calls)
        self.assertEqual(self.fake.snapshot(), before)
        return printed

    def test_a_missing_confirmation_is_refused_before_any_request(self):
        mark = self.preview(ADD)
        calls = len(self.fake.calls)
        for more in ({}, {"fingerprint": mark}, {"confirmed_by": "the participant"}, {"fingerprint": mark, "confirmed_by": ""}):
            self.refused("NO CONFIRMATION was given", **more)
        self.assertEqual(len(self.fake.calls), calls)

    def test_the_confirmer_must_be_a_plain_name(self):
        mark = self.preview(ADD)
        for name in ("   ", "x" * 61, "a\nb", "@".join(("someone", "example.invalid"))):
            self.refused("must be a short plain name", fingerprint=mark, confirmed_by=name)

    def test_a_fingerprint_no_preview_has_is_refused(self):
        self.preview(ADD)
        self.refused("there is no preview with the fingerprint", fingerprint="0" * 32, confirmed_by="the participant")

    def test_a_fingerprint_cannot_name_a_file_elsewhere(self):
        for mark in ("../allow", "..%2fallow", "a" * 31, "A" * 32, "a" * 32 + "/x"):
            self.refused("not the shape of a preview fingerprint", fingerprint=mark, confirmed_by="the participant")

    def test_a_change_that_differs_from_the_preview_is_refused(self):
        mark = self.preview(ADD)
        for changes in (ADD + ["label.remove=bug"], ["label.add=urgent"], [], ADD + ["title=x"], ["label.add=In Progress"]):
            printed = self.refused("THE CHANGE DIFFERS FROM THE PREVIEW", changes=changes, fingerprint=mark, confirmed_by="the participant")
        self.assertEqual(self.labels(), ["bug", "needs triage"])
        self.assertIn("A confirmation covers exactly what its preview showed", printed)

    def test_the_refusal_names_what_differs(self):
        mark = self.preview(ADD)
        printed = self.refused('Asked for now and not in the preview: ["label.remove=bug"]. In the preview and not asked for now: []',
                               changes=ADD + ["label.remove=bug"], fingerprint=mark, confirmed_by="the participant")
        self.assertIn("REFUSED", printed)

    def test_a_preview_for_another_issue_is_refused(self):
        self.fake.store["repos"][REPO]["issues"]["8"] = dict(self.fake.issue(), node_id="I_kwFX4010008")
        mark = self.preview(ADD)
        self.refused("is for another repository, issue or source", issue=8, fingerprint=mark, confirmed_by="the participant")

    def test_a_saved_preview_that_was_altered_is_refused(self):
        mark = self.preview(ADD)
        path = os.path.join(self.state, mark + ".json")
        with open(path) as f:
            saved = json.load(f)
        saved["record"]["requests"].append({"method": "DELETE", "path": BASE + "/labels/bug", "body": None})
        with open(path, "w") as f:
            json.dump(saved, f)
        self.refused("It was altered after it was made", fingerprint=mark, confirmed_by="the participant")
        self.assertIn("bug", self.labels())

    def test_a_preview_older_than_the_limit_is_refused(self):
        mark = self.preview(ADD)
        self.fake.advance(16)
        printed = self.refused("THE PREVIEW HAS EXPIRED", fingerprint=mark, confirmed_by="the participant")
        self.assertIn("16 minutes, and the limit is 15", printed)

    def test_a_preview_at_the_limit_is_still_good(self):
        mark = self.preview(ADD)
        self.fake.advance(15)
        code, printed = self.confirm(ADD, mark)
        self.assertEqual(code, 0, printed)
        self.assertIn("15 minutes. The limit is 15", printed)

    def test_the_age_is_measured_on_github_s_clock_not_this_machine_s(self):
        with open(os.path.join(SKILL, "update.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn("datetime.now", code)
        self.assertNotIn("utcnow", code)
        self.assertEqual(len(re.findall(r"\btime\.time\b", code)), 1)          # only the default clock for rate-limit waits

    def test_the_fingerprint_changes_with_any_part_of_the_preview(self):
        first = self.preview(ADD)
        self.fake.advance(1)
        later = self.preview(ADD)
        other = self.preview(["label.add=urgent"])
        self.fake.someone_else("assignee.add=kit-fixture")
        moved = self.preview(ADD)
        self.assertEqual(len({first, later, other, moved}), 4)

    def test_the_approved_run_says_who_confirmed_and_for_which_fingerprint(self):
        mark = self.preview(ADD)
        code, printed = self.confirm(ADD, mark, name="the participant")
        self.assertEqual(code, 0)
        self.assertIn('1. CONFIRMATION. Given by "the participant", for the preview with fingerprint %s, in this same command' % mark, printed)
        self.assertIn("This workflow cannot check who typed it", printed)

    def test_another_account_or_a_recreated_issue_is_refused(self):
        mark = self.preview(ADD)
        self.fake.store["me"]["login"] = "kit-fixture"
        self.refused("is not the one of the preview", fingerprint=mark, confirmed_by="the participant")
        self.fake.store["me"]["login"] = "robin-fixture"
        self.fake.issue()["node_id"] = "I_kwFXother"
        self.refused("is not the one of the preview", fingerprint=mark, confirmed_by="the participant")


class ResultRecord(Base):
    """Criterion 8: a result record holds the repository, the number, the identifier of what was changed, the timestamp and the confirmer."""

    def test_the_record_holds_everything_the_criterion_names(self):
        changes = SWAP + ["milestone.set=Sprint 13"]
        mark = self.preview(changes)
        self.fake.advance(2)
        self.confirm(changes, mark)
        text = self.record()
        for line in ("## Update %s" % mark, "- outcome: DONE", '- repository: "acme-fixture/sandbox", id 401', "- issue: number 7, node ID I_kwFX4010007",
                     '- confirmed by: "the participant", as typed with the fingerprint in the command that wrote.',
                     "- written at: 2026-11-23T09:02:00Z by GitHub's clock", "- event 9100: `labeled`, at 2026-11-23T09:02:00Z",
                     "- event 9101: `unlabeled`", "- event 9102: `milestoned`", '- label "in progress": id 7003',
                     '| labels | `["bug", "needs triage"]` | `["bug", "in progress"]` | `["bug", "in progress"]` |',
                     "- `PATCH %s {\"milestone\": 3}` -> status 200" % BASE):
            self.assertIn(line, text)

    def test_the_record_keeps_the_old_values_and_how_to_put_them_back(self):
        changes = SWAP + ["milestone.clear=yes", "assignee.remove=robin-fixture"]
        self.confirm(changes, self.preview(changes))
        text = self.record()
        for line in ('- `--change "label.remove=in progress"`', '- `--change "label.add=needs triage"`', '- `--change "milestone.set=Sprint 12"`',
                     '- `--change "assignee.add=robin-fixture"`'):
            self.assertIn(line, text)

    def test_putting_the_old_values_back_works(self):
        changes = SWAP + ["milestone.clear=yes"]
        before = self.fake.issue().copy()
        self.confirm(changes, self.preview(changes))
        back = re.findall(r'- `--change "(.*)"`', self.record())
        self.assertEqual(self.confirm(back, self.preview(back))[0], 0)
        after = self.fake.issue()
        self.assertEqual((sorted(after["labels"]), after["assignees"], after["milestone"]), (sorted(before["labels"]), before["assignees"], before["milestone"]))

    def test_a_second_update_adds_a_section_and_keeps_the_first(self):
        first = self.preview(ADD)
        self.confirm(ADD, first)
        second = self.preview(["label.add=urgent"])
        self.confirm(["label.add=urgent"], second)
        text = self.record()
        self.assertLess(text.index("## Update " + first), text.index("## Update " + second))
        self.assertEqual(text.count("# Result records: metadata updates"), 1)

    def test_events_that_were_there_before_or_made_by_someone_else_s_comment_are_not_claimed(self):
        mark = self.preview(ADD)
        self.fake.someone_else("comment")
        self.confirm(ADD, mark)
        self.assertNotIn("event 9001", self.record())
        self.assertNotIn("commented", self.record())
        self.assertEqual(self.record().count("- event "), 1)

    def test_a_refused_confirmation_writes_no_record(self):
        mark = self.preview(ADD)
        self.fake.advance(60)
        self.confirm(ADD, mark)
        self.assertFalse(os.path.exists(os.path.join(self.results, "update-metadata.md")))


class Rerun(Base):
    """Criterion 9: running the approved workflow again creates no duplicate, repeated or conflicting change."""

    def test_the_same_confirmation_a_second_time_is_refused_and_writes_nothing(self):
        mark = self.preview(SWAP)
        self.assertEqual(self.confirm(SWAP, mark)[0], 0)
        writes, events = len(self.fake.writes()), len(self.fake.store["repos"][REPO]["events"]["7"])
        code, printed = self.confirm(SWAP, mark)
        self.assertEqual(code, 1)
        self.assertIn("this preview was ALREADY USED, at 2026-11-23T09:00:00Z by GitHub's clock, confirmed by \"the participant\"", printed)
        self.assertEqual(len(self.fake.writes()), writes)
        self.assertEqual(len(self.fake.store["repos"][REPO]["events"]["7"]), events)
        self.assertEqual(self.record().count("## Update "), 1)

    def test_a_new_preview_of_the_same_change_finds_nothing_to_do(self):
        self.confirm(SWAP, self.preview(SWAP))
        saved = self.saved()
        code, printed = self.go("preview", SWAP)
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NOTHING TO CHANGE", printed)
        self.assertIn("in this order: 0", printed)
        self.assertNotIn("FINGERPRINT", printed)
        self.assertEqual(self.saved(), saved)

    def test_the_preview_is_spent_before_the_first_write(self):
        mark = self.preview(SWAP)
        seen = []

        def at_write(method, path):
            if method != "GET" and not seen:
                with open(os.path.join(self.state, mark + ".json")) as f:
                    seen.append(json.load(f)["status"])
        self.fake.before = at_write
        self.confirm(SWAP, mark)
        self.assertEqual(seen, ["used"])

    def test_a_refused_confirmation_does_not_spend_the_preview(self):
        mark = self.preview(ADD)
        self.go("confirm", ADD, fingerprint=mark)
        self.go("confirm", ["label.add=urgent"], fingerprint=mark, confirmed_by="the participant")
        self.assertEqual(self.confirm(ADD, mark)[0], 0)


class WhenGitHubRefuses(Base):
    def test_a_token_that_may_not_write_changes_nothing_and_says_so(self):
        mark = self.preview(SWAP)
        self.fake.store["token_may_write"] = False
        before = self.fake.issue().copy()
        code, printed = self.confirm(SWAP, mark)
        self.assertEqual(code, 1)
        self.assertIn("-> status 403. GITHUB REFUSED THIS. No further request is sent", printed)
        self.assertIn("This is what the issue held before. NOTHING WAS CHANGED", printed)
        self.assertIn("RESULT: NOT DONE. GitHub refused the write (status 403) and the issue is as it was", printed)
        self.assertEqual(len(self.fake.writes()), 1)
        self.assertEqual(self.fake.issue(), before)
        self.assertIn("- outcome: NOT DONE, NOTHING CHANGED", self.record())

    def test_a_write_refused_part_way_stops_the_rest_and_needs_looking(self):
        mark = self.preview(SWAP)
        self.fake.fail("DELETE", BASE + "/labels/", 500)
        code, printed = self.confirm(SWAP, mark)
        self.assertEqual(code, 3)
        self.assertIn("RESULT: NEEDS LOOKING", printed)
        self.assertEqual(sorted(self.labels()), ["bug", "in progress", "needs triage"])
        self.assertIn("- outcome: NEEDS LOOKING", self.record())
        self.assertIn("-> status 500", self.record())

    def test_a_rate_limit_before_any_write_writes_nothing(self):
        self.fake.fail("GET", "/user", 429, times=9, headers={"Retry-After": "2"})
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 2)
        self.assertIn("Nothing was written", printed)
        self.assertEqual(self.conn.waits, [2, 2, 2])

    def test_a_short_rate_limit_is_waited_for(self):
        self.fake.fail("GET", "/user", 429, times=1, headers={"Retry-After": "2"})
        self.preview(ADD)
        self.assertEqual(self.conn.waits, [2])

    def test_a_rejected_token_and_a_moved_repository_stop_the_run(self):
        self.fake.fail("GET", "/user", 401)
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("rejected the token (401)", printed)
        self.fake.fail("GET", "/repos/" + REPO, 301, headers={"Location": "https://api.github.com/repositories/401"})
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("this workflow does not follow it", printed)

    def test_a_repository_github_knows_under_another_name_is_refused(self):
        real = self.fake._answer
        self.fake._answer = lambda method, path, params, body: (200, {}, dict(real(method, path, params, body)[2], full_name="acme-fixture/renamed")) \
            if path == "/repos/" + REPO else real(method, path, params, body)
        code, printed = self.go("preview", ADD)
        self.assertEqual(code, 1)
        self.assertIn("under another name", printed)


class CommandLine(Base):
    def main(self, *argv, env=None):
        printed, old = io.StringIO(), dict(os.environ)
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.update(env or {})
        try:
            with contextlib.redirect_stdout(printed):
                code = update.main(list(argv))
        finally:
            os.environ.clear()
            os.environ.update(old)
        return code, printed.getvalue()

    def common(self, store):
        return ["--source", "fake", "--fake-store", store, "--repo", REPO, "--issue", "7", "--allowlist", self.allow, "--state", self.state, "--results", self.results]

    def test_preview_then_confirm_as_two_separate_commands(self):
        store = os.path.join(self.dir, "github.json")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fake_github.main([store, "new"]), 0)
        code, printed = self.main("preview", *self.common(store), "--change", "label.add=in progress")
        self.assertEqual(code, 0)
        mark = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", printed).group(1)
        self.assertEqual(fake_github.load(store).writes(), [])
        code, printed = self.main("confirm", *self.common(store), "--change", "label.add=in progress", "--fingerprint", mark, "--confirmed-by", "the participant")
        self.assertEqual(code, 0, printed)
        self.assertEqual(fake_github.load(store).issue()["labels"], ["bug", "needs triage", "in progress"])
        code, printed = self.main("confirm", *self.common(store), "--change", "label.add=in progress")
        self.assertEqual(code, 1)
        self.assertIn("NO CONFIRMATION was given", printed)

    def test_the_made_up_world_can_change_between_the_two_commands(self):
        store = os.path.join(self.dir, "github.json")
        with contextlib.redirect_stdout(io.StringIO()):
            fake_github.main([store, "new"])
        _, printed = self.main("preview", *self.common(store), "--change", "label.add=in progress")
        mark = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", printed).group(1)
        with contextlib.redirect_stdout(io.StringIO()):
            fake_github.main([store, "someone-else", "label.add=urgent"])
        code, printed = self.main("confirm", *self.common(store), "--change", "label.add=in progress", "--fingerprint", mark, "--confirmed-by", "the participant")
        self.assertEqual(code, 1)
        self.assertIn("STALE", printed)

    def test_a_live_run_keeps_its_files_outside_the_repository_and_needs_the_token(self):
        inside = os.path.join(SKILL, "state")
        live = ["--source", "live", "--repo", REPO, "--issue", "7", "--allowlist", self.allow]
        code, printed = self.main("preview", *live, "--state", inside, "--results", self.results, env=dict([("GITHUB_TOKEN", PRETEND)]))
        self.assertEqual(code, 1)
        self.assertIn("outside this repository. Give --state", printed)
        code, printed = self.main("preview", *live, "--state", self.state, env=dict([("GITHUB_TOKEN", PRETEND)]))
        self.assertEqual(code, 1)
        self.assertIn("Give --results", printed)
        code, printed = self.main("preview", *live, "--state", self.state, "--results", self.results)
        self.assertEqual(code, 1)
        self.assertIn("GITHUB_TOKEN is not set", printed)
        self.assertNotIn(PRETEND, printed)

    def test_a_bad_repository_name_or_number_is_refused(self):
        for repo, issue in (("../x", 7), ("nameonly", 7), (REPO, 0), (REPO, None)):
            code, _ = self.go("preview", ADD, repo=repo, issue=issue)
            self.assertEqual(code, 1)
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()

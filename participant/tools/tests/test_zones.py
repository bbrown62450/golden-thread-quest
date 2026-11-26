"""Tests for participant/tools/zones.py. Every write is aimed at a sandbox: a temporary folder laid out like the
repository, holding made-up files. No test writes to, or deletes from, the real repository."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, TOOLS)
import zones   # noqa: E402


def make_sandbox(root):
    """A small folder laid out like the repository. Returns the folder that stands for the repository, and one beside
    it that stands for everything outside."""
    repo, outside = os.path.join(root, "repo"), os.path.join(root, "outside")
    files = {"content/quests/sample-quest.md": "# A made-up quest\n", "quest_app/app.py": "# made-up application code\n", "docs/GUIDE.md": "# A made-up guide\n",
             "README.md": "# A made-up readme\n", "generated/index.html": "<p>built</p>\n", "local-data/raw-response.json": "{\"made_up\": true}\n",
             "participant/context/notes.md": "My notes.\n", "participant/progress.yaml": "made_up: true\n", "participant/ACTIVITY.md": "- made up\n",
             "participant/evidence/a-quest/attempt-1/manifest.yaml": "made_up: true\n", "participant/evidence/a-quest/attempt-1/validation/result.yaml": "made_up: true\n",
             "participant/evidence/a-quest/attempt-1/PROOF.md": "# Proof\n", ".git/HEAD": "ref: made-up\n", ".claude/settings.json": "{}\n"}
    for name, text in files.items():
        os.makedirs(os.path.dirname(os.path.join(repo, name)), exist_ok=True)
        with open(os.path.join(repo, name), "w", encoding="utf-8") as f:
            f.write(text)
    os.makedirs(outside)
    with open(os.path.join(outside, "elsewhere.txt"), "w", encoding="utf-8") as f:
        f.write("a file outside the repository\n")
    links = {"participant/context/link-to-curriculum": os.path.join(repo, "content", "quests"),          # a folder link into the program's zone
             "participant/context/link-out": outside,                                                     # a folder link out of the repository
             "participant/context/link-to-readme.md": os.path.join(repo, "README.md"),                    # a file link to a program file
             "participant/context/link-to-nowhere.md": os.path.join(outside, "not-there-yet.txt"),        # a link whose target does not exist
             "participant/context/link-to-my-notes.md": os.path.join(repo, "participant", "context", "notes.md")}   # a link that stays in the zone
    for name, target in links.items():
        os.symlink(target, os.path.join(repo, name))
    os.link(os.path.join(repo, "docs", "GUIDE.md"), os.path.join(repo, "participant", "context", "second-name-of-the-guide.md"))   # a hard link
    return repo, outside


def snapshot(root):
    """Every name under a folder, with the bytes of each file, without following links."""
    found = {}
    for folder, names, files in os.walk(root):
        for name in names + files:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root)
            if os.path.islink(path):
                found[rel] = "link to " + os.readlink(path)
            elif os.path.isfile(path):
                with open(path, "rb") as f:
                    found[rel] = f.read()
            else:
                found[rel] = "folder"
    return found


class Case(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-zones-test-")
        self.repo, self.outside = make_sandbox(self.root)
        self.before = snapshot(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_it(self, *args, stdin=None, cwd=None):
        done = subprocess.run([sys.executable, os.path.join(TOOLS, "zones.py"), "--root", self.repo] + list(args), capture_output=True, text=True, input=stdin, cwd=cwd or self.repo)
        return done.returncode, done.stdout, done.stderr

    def write(self, to, text="new content", cwd=None):
        code, out, _ = self.run_it("write", "--to", to, "--text", text, cwd=cwd)
        return code, out

    def refused(self, to, rule, *parts, cwd=None):
        code, out = self.write(to, cwd=cwd)
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED by rule %s." % rule, out)
        self.assertIn("Nothing was written, and nothing was created.", out)
        for part in parts:
            self.assertIn(part, out)
        self.assertEqual(snapshot(self.root), self.before, "a refused write changed something")
        return out

    def hook(self, tool, path, cwd=None, key="file_path"):
        call = {"tool_name": tool, "tool_input": {key: path, "content": "x"}, "cwd": cwd or self.repo}
        code, _, err = self.run_it("hook", stdin=json.dumps(call))
        return code, err


class AnAllowedWrite(Case):
    """Criterion 5."""

    def test_a_new_file_in_the_participants_notes_is_written(self):
        code, out = self.write("participant/context/new-note.md", "hello")
        self.assertEqual(code, 0, out)
        self.assertIn("ALLOWED by rule R9.", out)
        self.assertIn("WRITTEN: 6 bytes to `participant/context/new-note.md`.", out)
        with open(os.path.join(self.repo, "participant/context/new-note.md")) as f:
            self.assertEqual(f.read(), "hello\n")

    def test_nothing_else_changes_and_no_temporary_file_is_left(self):
        self.write("participant/context/new-note.md")
        after = snapshot(self.root)
        self.assertEqual(sorted(set(after) - set(self.before)), [os.path.join("repo", "participant", "context", "new-note.md")])
        self.assertEqual({k: v for k, v in after.items() if k in self.before}, self.before)

    def test_new_folders_are_made_inside_the_zone(self):
        code, out = self.write("participant/skills/a-new-skill/SKILL.md")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, "participant/skills/a-new-skill/SKILL.md")))

    def test_an_existing_file_of_the_participants_is_replaced(self):
        code, out = self.write("participant/context/notes.md", "changed")
        self.assertEqual(code, 0, out)
        with open(os.path.join(self.repo, "participant/context/notes.md")) as f:
            self.assertEqual(f.read(), "changed\n")

    def test_an_absolute_path_and_a_path_with_dots_that_stay_inside_are_allowed(self):
        self.assertEqual(self.write(os.path.join(self.repo, "participant", "context", "a.md"))[0], 0)
        self.assertEqual(self.write("participant/context/../context/./b.md")[0], 0)
        self.assertEqual(self.write("content/../participant/context/c.md")[0], 0)   # judged by where it lands, not by how it starts

    def test_a_link_that_stays_inside_the_zone_is_followed_and_the_link_is_kept(self):
        code, out = self.write("participant/context/link-to-my-notes.md", "through the link")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.islink(os.path.join(self.repo, "participant/context/link-to-my-notes.md")))
        with open(os.path.join(self.repo, "participant/context/notes.md")) as f:
            self.assertEqual(f.read(), "through the link\n")

    def test_there_is_no_way_to_copy_a_file_in(self):
        """A reader's finding: copying from a file would let private data be copied into the hand-in. The option is gone."""
        code, _, err = self.run_it("write", "--to", "participant/context/copied.md", "--text", "x", "--from", os.path.join(self.repo, "local-data", "raw-response.json"))
        self.assertEqual(code, 2)
        self.assertIn("unrecognized arguments", err)
        self.assertEqual(snapshot(self.root), self.before)

    def test_an_existing_files_permissions_are_kept(self):
        path = os.path.join(self.repo, "participant", "context", "run-me.sh")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(path, 0o755)
        self.assertEqual(self.write("participant/context/run-me.sh", "#!/bin/sh\necho hi")[0], 0)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o755)


class ARefusedWrite(Case):
    """Criteria 2, 3 and 4. Every one of these also checks that nothing at all was created or changed."""

    def test_the_curriculum(self):
        self.refused("content/quests/sample-quest.md", "R10", "Program-owned")

    def test_a_new_file_in_the_curriculum(self):
        self.refused("content/quests/new-quest.md", "R10")

    def test_the_application_and_the_documentation(self):
        self.refused("quest_app/app.py", "R10")
        self.refused("docs/GUIDE.md", "R10")
        self.refused("README.md", "R10")

    def test_the_built_site(self):
        self.refused("generated/index.html", "R6", "Generated and tool-managed")

    def test_gits_own_folder(self):
        self.refused(".git/HEAD", "R6")
        self.refused(".git/hooks/pre-commit", "R6")

    def test_private_data(self):
        self.refused("local-data/raw-response.json", "R5", "Private data")
        self.refused("local-data/new-folder/saved.json", "R5")

    def test_a_credential_name_anywhere_even_in_the_participants_folder(self):
        for name in (".env", ".env.local", ".env-local", "server.pem", "key.pem.bak", "id_rsa", "id_ecdsa", "credentials.json", "credentials.json.txt",
                     "credentials.yaml", "my.token", "token.json", "secrets.json", ".git-credentials", ".pypirc", ".npmrc", ".netrc", "server.KEY"):
            self.refused("participant/context/" + name, "R2", "Private data")

    def test_the_example_environment_file_is_not_taken_for_a_credential(self):
        self.refused(".env.example", "R10")

    def test_the_files_the_application_writes(self):
        for path in ("participant/progress.yaml", "participant/ACTIVITY.md", "participant/evidence/a-quest/attempt-1/manifest.yaml",
                     "participant/evidence/a-quest/attempt-1/submission.yaml", "participant/evidence/a-quest/attempt-1/review.yaml",
                     "participant/evidence/a-quest/attempt-1/validation/result.yaml", "participant/evidence/a-quest/attempt-1/validation/new.yaml"):
            self.refused(path, "R7")

    def test_the_proof_beside_them_is_the_participants(self):
        self.assertEqual(self.write("participant/evidence/a-quest/attempt-1/PROOF.md")[0], 0)
        self.assertEqual(self.write("participant/evidence/a-quest/attempt-1/logs/run.txt")[0], 0)

    def test_what_the_application_writes_cannot_be_reached_by_going_inside_it(self):
        """A reader's finding: a path below an application file's name was allowed, and made a folder at that name."""
        for path in ("participant/.progress.lock/x.md", "participant/progress.yaml/..namedfork/data", "participant/evidence/a-quest/attempt-2/manifest.yaml/x",
                     "participant/evidence/a-quest/attempt-2/validation", "participant/evidence/a-quest/attempt-1/validation/deep/er/x.yaml", "participant/.progress.lock"):
            self.refused(path, "R7")

    def test_a_file_named_like_them_elsewhere_is_the_participants(self):
        self.assertEqual(self.write("participant/evidence/a-quest/attempt-1/notes/sub/manifest.yaml")[0], 0)
        self.assertEqual(self.write("participant/context/progress.yaml")[0], 0)

    def test_what_steers_the_agent_or_git_inside_the_participants_folder(self):
        """A reader's finding: the guard and the agent's settings sat in the zone the agent may write."""
        for path in ("participant/tools/zones.py", "participant/.claude/settings.json", "participant/.claude/settings.local.json", "participant/CLAUDE.md",
                     "participant/skills/x/CLAUDE.md", "participant/.mcp.json", "participant/.git/hooks/pre-commit", "participant/.gitattributes", "participant/TOOLS/ZONES.PY"):
            self.refused(path, "R3")
        self.assertEqual(self.write("participant/tools/another-tool.py")[0], 0)

    def test_a_path_through_a_file(self):
        self.refused("participant/context/notes.md/x.md", "R11", "is a file and not a folder")

    def test_a_link_that_loops(self):
        os.symlink("loop-b", os.path.join(self.repo, "participant", "context", "loop-a"))
        os.symlink("loop-a", os.path.join(self.repo, "participant", "context", "loop-b"))
        self.before = snapshot(self.root)
        code, out = self.write("participant/context/loop-a/x.md")
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED", out)
        self.assertEqual(snapshot(self.root), self.before)

    def test_a_letter_that_some_disks_treat_as_another(self):
        self.refused("participant/progre\u017f\u017f.yaml", "R7")

    def test_tool_folders_inside_the_participants_folder(self):
        self.refused("participant/node_modules/pkg/index.js", "R4")
        self.refused("participant/skills/x/__pycache__/x.pyc", "R4")

    def test_a_path_in_no_zone(self):
        out = self.refused("notes.txt", "R11", "no zone")
        self.assertNotIn("capitals", out)      # refused because it is in no zone, and for no other reason
        self.assertTrue(out.splitlines()[0].endswith("before it is written."))
        self.refused("a-new-top-folder/file.md", "R11")

    def test_dots_that_climb_out_of_the_repository(self):
        out = self.refused("../outside/escaped.txt", "R1", "it uses `..` to climb out of the repository")
        self.assertFalse(os.path.exists(os.path.join(self.outside, "escaped.txt")))
        self.assertIn("outside the repository", out)

    def test_dots_that_start_in_the_participants_folder_and_climb_out(self):
        self.refused("participant/context/../../../outside/escaped.txt", "R1", "it uses `..` to climb out")

    def test_dots_that_start_in_the_participants_folder_and_land_in_the_curriculum(self):
        self.refused("participant/context/../../content/quests/sample-quest.md", "R10", "as written it starts in the participant zone, and its `..` leads to `content/quests/sample-quest.md`")
        self.refused("participant/../content/quests/new.md", "R10")

    def test_an_absolute_path_outside(self):
        self.refused(os.path.join(self.outside, "escaped.txt"), "R1", "it is outside the repository")

    def test_a_folder_link_that_leads_out_of_the_repository(self):
        self.refused("participant/context/link-out/escaped.txt", "R1", "it goes through a symbolic link that leads out of the repository")
        self.assertEqual(sorted(os.listdir(self.outside)), ["elsewhere.txt"])

    def test_a_folder_link_that_leads_into_the_curriculum(self):
        self.refused("participant/context/link-to-curriculum/sample-quest.md", "R10", "as written it seemed to be in the participant zone", "a symbolic link on the way leads there")
        self.refused("participant/context/link-to-curriculum/new-quest.md", "R10")

    def test_a_file_link_to_a_program_file(self):
        self.refused("participant/context/link-to-readme.md", "R10", "resolves to `README.md`")

    def test_a_link_whose_target_does_not_exist_yet(self):
        self.refused("participant/context/link-to-nowhere.md", "R1", "symbolic link")
        self.assertFalse(os.path.exists(os.path.join(self.outside, "not-there-yet.txt")))

    def test_a_second_name_of_a_program_file(self):
        """A hard link cannot be seen by resolving the path. The file's count of names gives it away."""
        self.refused("participant/context/second-name-of-the-guide.md", "R8", "the file has 2 names on the disk")
        with open(os.path.join(self.repo, "docs", "GUIDE.md")) as f:
            self.assertEqual(f.read(), "# A made-up guide\n")

    def test_a_folder_in_place_of_a_file(self):
        self.refused("participant/context", "R11", "it is a folder")

    def test_the_participants_folder_in_other_capitals(self):
        out = self.refused("Participant/context/x.md", "R11")
        self.assertTrue("in other capitals" in out or "no zone" in out)      # which, depends on whether this disk sets capitals aside
        self.refused("CONTENT/quests/x.md", "R10")

    def test_the_repository_named_by_another_spelling_of_its_path_is_still_the_repository(self):
        """A reader's finding. On a disk that sets capitals aside, the same folder has many spellings."""
        other = os.path.join(os.path.dirname(self.repo), "REPO")
        if not os.path.exists(other):
            self.skipTest("this disk does not set capitals aside")
        self.refused(os.path.join(other, "content", "quests", "sample-quest.md"), "R10")
        self.refused(os.path.join(other, "README.md"), "R10")

    def test_a_root_inside_the_real_repository_is_refused(self):
        """NO WRITE IS ATTEMPTED HERE. An earlier form of this test ran a real `write` with such a root, trusting it to be
        refused. When a planted bug took the refusal out, the write went through and made a file in the real
        curriculum folder. The test now asks the tool only what it thinks of the root, and runs a command that only reads."""
        inside = os.path.join(zones.REPO, "content")
        self.assertIn("a folder inside the real repository", zones.root_problem(inside) or "")
        self.assertIsNone(zones.root_problem(zones.REPO))
        self.assertIsNone(zones.root_problem(self.repo))
        done = subprocess.run([sys.executable, os.path.join(TOOLS, "zones.py"), "--root", inside, "where", "participant/x.md"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("a folder inside the real repository", done.stdout)

    def test_a_path_swapped_for_a_link_between_the_check_and_the_write(self):
        """The folder the write needs is replaced, as it is made, by a link out of the repository."""
        target_folder = os.path.join(self.repo, "participant", "context", "new-folder")
        real = os.makedirs

        def swap(path, exist_ok=False):
            os.symlink(self.outside, target_folder)
        try:
            zones.os.makedirs = swap
            code, lines = zones.write_checked("participant/context/new-folder/x.md", self.repo, b"x")
        finally:
            zones.os.makedirs = real
        self.assertEqual(code, 1)
        self.assertIn("REFUSED after the check", lines[-1])
        self.assertEqual(sorted(os.listdir(self.outside)), ["elsewhere.txt"])

    def test_folders_made_for_a_write_that_then_fails_are_taken_away(self):
        real = os.open
        try:
            zones.os.open = lambda *a, **k: (_ for _ in ()).throw(OSError(28, "made up: no space"))
            code, lines = zones.write_checked("participant/context/deep/er/x.md", self.repo, b"x")
        finally:
            zones.os.open = real
        self.assertEqual(code, 1)
        self.assertEqual(snapshot(self.root), self.before)

    def test_a_temporary_name_already_taken_is_a_refusal_and_not_a_crash(self):
        stale = os.path.join(self.repo, "participant", "context", ".x.md.tmp-1")
        real = os.getpid
        with open(stale, "w") as f:
            f.write("stale")
        try:
            zones.os.getpid = lambda: 1
            code, lines = zones.write_checked("participant/context/x.md", self.repo, b"x")
        finally:
            zones.os.getpid = real
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "participant", "context", "x.md")))
        with open(stale) as f:
            self.assertEqual(f.read(), "stale")

    def test_an_empty_path(self):
        code, out = self.write("")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED by rule R1", out)

    def test_the_refusal_names_the_rule_and_quotes_it(self):
        out = self.refused("content/quests/sample-quest.md", "R10")
        self.assertIn(zones.RULE_TEXT["R10"], out)

    def test_a_relative_path_is_taken_from_the_root_whatever_folder_the_command_is_run_in(self):
        self.refused("content/quests/sample-quest.md", "R10", cwd=os.path.join(self.repo, "participant"))
        self.assertEqual(self.write("participant/context/from-elsewhere.md", cwd=self.outside)[0], 0)

    def test_the_check_comes_before_anything_is_created(self):
        """Criterion 2: the order. The check is made with nothing yet created, so a refusal has nothing to undo."""
        import builtins
        made = []
        real = (os.makedirs, os.open, os.mkdir, os.replace, os.symlink, builtins.open)

        def opened(path, mode="r", *a, **k):
            if any(letter in mode for letter in "wax+"):
                made.append(("open for writing", path))
            return real[5](path, mode, *a, **k)
        try:
            os.makedirs = lambda *a, **k: made.append(("makedirs", a[0]))
            os.open = lambda *a, **k: made.append(("open", a[0]))
            os.mkdir = lambda *a, **k: made.append(("mkdir", a[0]))
            os.replace = lambda *a, **k: made.append(("replace", a[0]))
            os.symlink = lambda *a, **k: made.append(("symlink", a[0]))
            builtins.open = opened
            with contextlib.redirect_stdout(io.StringIO()):
                code = zones.main(["--root", self.repo, "write", "--to", "content/deep/new/folders/x.md", "--text", "x"])
        finally:
            os.makedirs, os.open, os.mkdir, os.replace, os.symlink, builtins.open = real
        self.assertEqual(code, 1)
        self.assertEqual(made, [])


class TheHook(Case):
    """Criterion 2, for the agent's own file-editing tools."""

    def test_an_edit_in_the_participants_folder_is_let_through(self):
        for tool in ("Edit", "Write", "MultiEdit"):
            code, err = self.hook(tool, os.path.join(self.repo, "participant", "context", "notes.md"))
            self.assertEqual((code, err), (0, ""), tool)

    def test_an_edit_of_the_curriculum_is_stopped_with_exit_code_2_and_the_rule(self):
        code, err = self.hook("Edit", os.path.join(self.repo, "content", "quests", "sample-quest.md"))
        self.assertEqual(code, 2)
        self.assertIn("zones: REFUSED by rule R10.", err)
        self.assertIn("The edit was not made.", err)

    def test_the_hooks_own_answer_is_2_before_the_last_line_of_defence_sees_it(self):
        """The command turns any answer but 0 into 2 at the very end. That would hide a wrong answer from the hook
        itself, so the hook's own function is called here directly."""
        import argparse
        call = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(self.repo, "content", "quests", "sample-quest.md")}, "cwd": self.repo}
        real_in, real_err = sys.stdin, sys.stderr
        try:
            sys.stdin, sys.stderr = io.StringIO(json.dumps(call)), io.StringIO()
            self.assertEqual(zones.cmd_hook(argparse.Namespace(root=self.repo)), 2)
            sys.stdin = io.StringIO("not json")
            self.assertEqual(zones.cmd_hook(argparse.Namespace(root=self.repo)), 2)
        finally:
            sys.stdin, sys.stderr = real_in, real_err

    def test_each_zone_but_the_participants_is_stopped(self):
        for path, rule in (("generated/index.html", "R6"), ("local-data/x.json", "R5"), ("participant/progress.yaml", "R7"), ("notes.txt", "R11"),
                           ("participant/context/.env", "R2"), ("participant/context/link-to-curriculum/x.md", "R10"),
                           ("participant/context/link-out/x.md", "R1"), ("participant/../README.md", "R10"), ("participant/context/second-name-of-the-guide.md", "R8")):
            code, err = self.hook("Write", os.path.join(self.repo, path))
            self.assertEqual(code, 2, path)
            self.assertIn("rule %s." % rule, err, path)

    def test_a_notebook_edit_is_checked_by_its_own_field(self):
        self.assertEqual(self.hook("NotebookEdit", os.path.join(self.repo, "content", "x.ipynb"), key="notebook_path")[0], 2)
        self.assertEqual(self.hook("NotebookEdit", os.path.join(self.repo, "participant", "context", "x.ipynb"), key="notebook_path")[0], 0)

    def test_a_relative_path_is_taken_from_the_folder_the_agent_is_working_in(self):
        self.assertEqual(self.hook("Write", "notes.md", cwd=os.path.join(self.repo, "participant", "context"))[0], 0)
        self.assertEqual(self.hook("Write", "../content/x.md", cwd=os.path.join(self.repo, "participant"))[0], 2)

    def test_a_file_outside_the_repository_altogether_is_not_its_business(self):
        self.assertEqual(self.hook("Write", os.path.join(self.outside, "scratch.txt"))[0], 0)

    def test_a_link_outside_the_repository_that_leads_into_it_is_its_business(self):
        os.symlink(os.path.join(self.repo, "content"), os.path.join(self.outside, "way-in"))
        code, err = self.hook("Write", os.path.join(self.outside, "way-in", "quests", "x.md"))
        self.assertEqual(code, 2)
        self.assertIn("rule R10.", err)

    def test_the_repository_by_another_spelling_of_its_path_is_stopped(self):
        other = os.path.join(os.path.dirname(self.repo), "REPO")
        if not os.path.exists(other):
            self.skipTest("this disk does not set capitals aside")
        code, err = self.hook("Write", os.path.join(other, "README.md"))
        self.assertEqual(code, 2, "the hook let an edit of a program file through because the path was spelt in other capitals")
        self.assertIn("rule R10.", err)

    def test_the_hook_and_the_agents_settings_cannot_be_edited_through_the_hook(self):
        for path in ("participant/tools/zones.py", "participant/.claude/settings.local.json", "participant/CLAUDE.md", ".claude/settings.json", ".claude/settings.local.json"):
            self.assertEqual(self.hook("Edit", os.path.join(self.repo, path))[0], 2, path)

    def test_its_only_answers_are_0_and_2(self):
        for stdin in ("", "[]", "null", '{"tool_name": "Write", "tool_input": "not an object"}', '{"tool_name": 5}'):
            code, _, _ = self.run_it("hook", stdin=stdin)
            self.assertIn(code, (0, 2), stdin)
        self.assertEqual(self.run_it("hook", stdin='{"tool_name": "Write", "tool_input": "not an object"}')[0], 2)
        self.assertEqual(self.run_it("hook", stdin='{"tool_name": "Read", "tool_input": "not an object"}')[0], 0)
        done = subprocess.run([sys.executable, os.path.join(TOOLS, "zones.py"), "--root", os.path.join(self.root, "no-such-folder"), "hook"], capture_output=True, text=True, input="{}")
        self.assertEqual(done.returncode, 2)
        done = subprocess.run([sys.executable, os.path.join(TOOLS, "zones.py"), "hook", "--no-such-option"], capture_output=True, text=True, input="{}")
        self.assertEqual(done.returncode, 2)

    def test_a_tool_that_does_not_edit_files_is_let_through(self):
        for tool in ("Read", "Bash", "Grep"):
            self.assertEqual(self.hook(tool, os.path.join(self.repo, "content", "x.md"))[0], 0, tool)

    def test_an_edit_call_with_no_file_is_stopped(self):
        code, _, err = self.run_it("hook", stdin=json.dumps({"tool_name": "Write", "tool_input": {}}))
        self.assertEqual(code, 2)
        self.assertIn("names no file", err)

    def test_input_that_cannot_be_read_stops_the_edit(self):
        code, _, err = self.run_it("hook", stdin="not json")
        self.assertEqual(code, 2)
        self.assertIn("The zone check itself failed", err)

    def test_the_hook_writes_nothing(self):
        self.hook("Write", os.path.join(self.repo, "participant", "context", "new.md"))
        self.hook("Write", os.path.join(self.repo, "content", "new.md"))
        self.assertEqual(snapshot(self.root), self.before)


class WhereAndAudit(Case):
    """The stretch goals."""

    def test_where_names_the_zone_the_writer_and_the_git_status(self):
        code, out, _ = self.run_it("where", "local-data/raw-response.json", "participant/context/notes.md", "participant/context/link-to-curriculum/x.md")
        self.assertEqual(code, 0)
        self.assertIn("zone:         Private data", out)
        self.assertIn("zone:         Participant-owned", out)
        self.assertIn("resolves to:  content/quests/x.md", out)
        self.assertIn("zone:         Program-owned", out)
        self.assertIn("Git:          Not tracked.", out)
        self.assertEqual(snapshot(self.root), self.before)

    def test_the_audit_passes_when_every_file_is_in_a_zone(self):
        code, out, _ = self.run_it("audit")
        self.assertEqual(code, 0, out)
        self.assertIn("EVERY FILE IS IN A ZONE.", out)

    def test_the_audit_fails_and_names_a_file_in_no_zone(self):
        with open(os.path.join(self.repo, "stray-notes.txt"), "w") as f:
            f.write("made up\n")
        os.makedirs(os.path.join(self.repo, "new-top-folder"))
        with open(os.path.join(self.repo, "new-top-folder", "file.md"), "w") as f:
            f.write("made up\n")
        code, out, _ = self.run_it("audit")
        self.assertEqual(code, 1)
        self.assertIn("IN NO ZONE:                  2", out)
        self.assertIn("    stray-notes.txt", out)
        self.assertIn("    new-top-folder/file.md", out)

    def test_every_zone_and_every_rule_is_in_the_document(self):
        text = zones.rules_document()
        for zone in zones.ZONES:
            self.assertIn("| **%s** |" % zone["name"], text)
            self.assertIn(zone["writer"], text)
            self.assertIn(zone["git"], text)
        for rule, _, words in zones.RULES:
            self.assertIn("| %s |" % rule, text)
            self.assertIn(words, text)
        self.assertEqual(len(zones.ZONES), 4)

    def test_only_one_rule_allows_a_write(self):
        self.assertEqual([zone["id"] for zone in zones.ZONES if zone["agent"]], ["participant"])
        self.assertEqual([rule for rule, result, _ in zones.RULES if result != "refused"], ["R9"])
        self.assertEqual(zones.ALLOW, "R9")
        for rule in zones.RULE_TEXT:                       # and in the code: only a verdict by that rule is allowed
            self.assertEqual(zones.Verdict("x", "x", "x", "participant", rule).allowed, rule == "R9")

    def test_the_rules_document_is_written_and_checked(self):
        self.assertEqual(self.run_it("rules", "--check")[0], 1)
        self.assertEqual(self.run_it("rules", "--write")[0], 0)
        self.assertEqual(self.run_it("rules", "--check")[0], 0)
        with open(os.path.join(self.repo, zones.RULES_DOC), "a") as f:
            f.write("edited by hand\n")
        self.assertEqual(self.run_it("rules", "--check")[0], 1)


class TheRealRepository(unittest.TestCase):
    """Reads only. Nothing here writes to the real repository."""

    def test_every_file_in_the_real_repository_is_in_a_zone(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = zones.main(["audit"])
        self.assertEqual(code, 0, out.getvalue())

    def test_the_rules_document_in_the_real_repository_is_what_the_rules_give(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = zones.main(["rules", "--check"])
        self.assertEqual(code, 0, out.getvalue())

    def test_this_tool_and_its_tests_are_in_the_participants_zone(self):
        self.assertEqual(zones.judge(os.path.join(TOOLS, "zones.py"), zones.REPO).rule, "R3")     # in the participant's zone, and not the agent's to write
        self.assertTrue(zones.judge(os.path.join(TOOLS, "tests", "test_zones.py"), zones.REPO).allowed)
        self.assertFalse(zones.judge(os.path.join(zones.REPO, "CLAUDE.md"), zones.REPO).allowed)

    def test_the_folders_the_rules_list_are_what_git_says_they_are(self):
        """The Git column of the rules is written by hand. This asks Git."""
        def git(*args):
            return subprocess.run(["git", "-C", zones.REPO] + list(args), capture_output=True, text=True)
        tracked = set(line.split("/")[0] for line in git("ls-files").stdout.splitlines())
        self.assertEqual(sorted(tracked - {"participant"}), sorted(zones.PROGRAM_TOP))      # every tracked top-level name but the participant's is program-owned
        self.assertIn("participant", tracked)
        for name in ("generated", "generated.lock", "local-data", ".venv", ".claude/settings.local.json", ".env", "participant/node_modules"):
            self.assertEqual(git("check-ignore", "-q", name).returncode, 0, "%s is not ignored by Git" % name)


if __name__ == "__main__":
    unittest.main()

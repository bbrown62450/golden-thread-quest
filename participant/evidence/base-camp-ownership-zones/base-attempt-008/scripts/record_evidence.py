#!/usr/bin/env python3
"""Records logs/refused-write.txt, logs/allowed-write.txt and logs/hook-and-audit.txt for the quest base-camp-ownership-zones.

Every write here is aimed at a SANDBOX: a temporary folder laid out like the repository, holding made-up files and the
links the trials need. It is made by make_sandbox in participant/tools/tests/test_zones.py and deleted at the end. No
write is aimed at the real repository. Nothing is deleted to show a refusal: a refusal is shown by a listing of the
sandbox, before and after, being the same.

SANDBOX stands for the temporary folder. SANDBOX/repo stands for the repository, and SANDBOX/outside for everything
outside it.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
TOOL = os.path.join(PARTICIPANT, "tools", "zones.py")
sys.path.insert(0, os.path.join(PARTICIPANT, "tools", "tests"))
from test_zones import make_sandbox, snapshot   # noqa: E402
sys.path.insert(0, os.path.join(PARTICIPANT, "tools"))
from zones import PROGRAM_TOP, RULE_TEXT   # noqa: E402

HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.\n"
        "Every write is aimed at a sandbox of made-up files, shown as SANDBOX. Nothing here is from a real system.")


class Log:
    def __init__(self, title, root):
        self.lines, self.problems, self.count, self.root = [title, HEAD, ""], [], 0, root

    def out(self, *lines):
        self.lines += list(lines) if lines else [""]

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(os.path.realpath(self.root), "SANDBOX").replace(self.root, "SANDBOX")

    def run(self, *args, stdin=None, shown=None):
        repo = os.path.join(self.root, "repo")
        done = subprocess.run([sys.executable, TOOL, "--root", repo] + list(args), capture_output=True, text=True, input=stdin, cwd=repo)
        said = (done.stdout + done.stderr).rstrip("\n")
        self.lines += ["$ %spython3 participant/tools/zones.py --root SANDBOX/repo %s" % (shown or "", " ".join(json.dumps(self.tidy(a)) if " " in a or not a else self.tidy(a) for a in args)),
                       "-" * 78, self.tidy(said), "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, said

    def listing(self, title):
        self.out(title)
        found = snapshot(self.root)
        for name in sorted(found):
            what = found[name]
            self.out("  %-66s %s" % (name, self.tidy(what) if isinstance(what, str) else "%d bytes" % len(what)))
        return found

    def save(self, name):
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.problems), self.count) if self.problems else "ALL CHECKS PASSED. %d checks." % self.count)]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.problems:
            print("  FAILED: " + label)
        return not self.problems


TEXT = "A note written by the zone tool."


def main():
    ok = True
    # ------------------------------------------------------------ refused-write.txt
    root = tempfile.mkdtemp(prefix="gtq-zones-")
    try:
        make_sandbox(root)
        log = Log("Writes that were refused. base-camp-ownership-zones, attempt base-attempt-008", root)
        log.part("THE SANDBOX BEFORE ANY WRITE")
        before = log.listing("Every name under SANDBOX. A link is shown with where it leads:")
        log.part("THE REFUSED WRITES")
        log.out("The command is the same each time. Only the path changes.")
        trials = (
            ("1. Into the program-owned zone: an existing curriculum file.", "content/quests/sample-quest.md", "R10", "Program-owned"),
            ("2. Into the private-data zone: a raw response.", "local-data/raw-response.json", "R5", "Private data"),
            ("3. Using `..` to leave the allowed folder and land outside the repository.", "participant/context/../../../outside/escaped.txt", "R1", "it uses `..` to climb out of the repository"),
            ("4. Using `..` to leave the allowed folder and land in the curriculum.", "participant/context/../../content/quests/new-quest.md", "R10", "its `..` leads to `content/quests/new-quest.md`"),
            ("5. Through a symbolic link, in the participant's folder, that leads out of the repository.", "participant/context/link-out/escaped.txt", "R1", "it goes through a symbolic link that leads out of the repository"),
            ("6. Through a symbolic link, in the participant's folder, that leads into the curriculum.", "participant/context/link-to-curriculum/sample-quest.md", "R10", "a symbolic link on the way leads there"),
            ("7. Through a link to a file that does not exist yet, outside the repository.", "participant/context/link-to-nowhere.md", "R1", "symbolic link"),
            ("8. A second name (a hard link), in the participant's folder, of a program file.", "participant/context/second-name-of-the-guide.md", "R8", "the file has 2 names on the disk"),
            ("9. A file the application writes, inside the participant's folder.", "participant/progress.yaml", "R7", "Participant-owned"),
            ("10. The built site.", "generated/index.html", "R6", "Generated and tool-managed"),
            ("11. A credential's name, in the participant's own notes.", "participant/context/.env", "R2", "Private data"),
            ("12. A path that is in no zone.", "stray-notes.txt", "R11", "no zone"),
            ("13. The zone tool itself, which is in the participant's folder.", "participant/tools/zones.py", "R3", "Participant-owned"),
            ("14. The agent's own settings, if they were put in the participant's folder.", "participant/.claude/settings.local.json", "R3", "Participant-owned"),
            ("15. A path that goes inside a file the application writes.", "participant/progress.yaml/x", "R7", "Participant-owned"),
        )
        heard = {}
        for label, path, rule, part in trials:
            log.out("", label)
            code, said = log.run("write", "--to", path, "--text", TEXT)
            heard[label.split(".")[0]] = said
            now = snapshot(root)
            log.check("refused, with exit code 1, by rule %s: the output names the rule and gives its words in full" % rule, code == 1 and ("REFUSED by rule %s." % rule) in said and RULE_TEXT[rule] in said)
            log.check("and it says what this path was: %s" % part.replace("`", "'"), part in said.split(RULE_TEXT[rule])[-1] or part in said.split("which is in: ")[-1].split(".")[0])
            log.check("criterion 4: nothing was created and nothing changed: every name and every byte under SANDBOX is what it was", now == before and "Nothing was written, and nothing was created." in said)
        log.part("THE SANDBOX AFTER THE FIFTEEN REFUSED WRITES")
        after = log.listing("Every name under SANDBOX:")
        log.out()
        log.check("criterion 4: the listing after is the listing before, name for name and byte for byte: no file, no partial file, no temporary file, no new folder", after == before)
        log.check("the file outside the repository that three of the writes aimed at does not exist", not os.path.exists(os.path.join(root, "outside", "escaped.txt")) and not os.path.exists(os.path.join(root, "outside", "not-there-yet.txt")))
        log.check("criterion 3: the two paths using `..` (3 and 4) and the three through a symbolic link (5, 6 and 7) were each refused for where they resolve to, and the output of each says which it was",
                  all("symbolic link" in heard[n].split("Here: ")[-1] for n in ("5", "6", "7")) and all("`..`" in heard[n].split("Here: ")[-1] for n in ("3", "4"))
                  and "resolves to `content/quests/sample-quest.md`" in heard["6"] and "resolves to `content/quests/new-quest.md`" in heard["4"])
        ok = log.save("refused-write.txt") and ok

        # -------------------------------------------------------- allowed-write.txt
        log = Log("The same write, allowed. base-camp-ownership-zones, attempt base-attempt-008", root)
        log.out("The same sandbox as refused-write.txt left, unchanged. The same command, with the same text. Only the path differs:",
                "it is in the participant's folder.")
        log.part("THE ALLOWED WRITE")
        code, said = log.run("write", "--to", "participant/context/new-note.md", "--text", TEXT)
        now = snapshot(root)
        new = sorted(set(now) - set(before))
        target = os.path.join("repo", "participant", "context", "new-note.md")
        log.check("criterion 5: the same command, aimed at a participant-owned folder, succeeds: exit code 0, allowed by rule R9", code == 0 and "ALLOWED by rule R9." in said and "WRITTEN: %d bytes" % (len(TEXT) + 1) in said)
        log.check("the file is there, and holds the text that was given", new == [target] and now[target] == (TEXT + "\n").encode())
        log.check("it is the only thing that changed: nothing is gone, every other name and byte under SANDBOX is what it was, and no temporary file is left", {k: v for k, v in now.items() if k != target} == before)
        log.out("", "More writes the rules allow:")
        for label, path in (("A new folder inside the participant's zone, made as needed.", "participant/skills/a-new-skill/SKILL.md"),
                            ("A path that begins in the curriculum and whose `..` lands in the participant's folder. It is judged by where it lands.", "content/../participant/context/landed-here.md"),
                            ("Through a link that stays inside the participant's folder. The link is kept, and the file it leads to is written.", "participant/context/link-to-my-notes.md")):
            log.out("", label)
            code, said = log.run("write", "--to", path, "--text", TEXT)
            log.check("allowed, by rule R9", code == 0 and "ALLOWED by rule R9." in said)
        now = snapshot(root)
        log.check("the link is still a link, and the notes it leads to hold the new text", str(now[os.path.join("repo", "participant", "context", "link-to-my-notes.md")]).startswith("link to ") and now[os.path.join("repo", "participant", "context", "notes.md")] == (TEXT + "\n").encode())
        log.part("THE SANDBOX AFTERWARDS")
        log.listing("Every name under SANDBOX:")
        changed = sorted(k for k in set(now) | set(before) if now.get(k) != before.get(k))
        log.out("", "What differs from the listing in refused-write.txt:", *["  " + name for name in changed])
        log.check("everything that changed is inside SANDBOX/repo/participant, and nothing was removed", bool(changed) and all(name.startswith(os.path.join("repo", "participant") + os.sep) for name in changed) and set(before) <= set(now))
        ok = log.save("allowed-write.txt") and ok
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ------------------------------------------------------------ hook-and-audit.txt
    root = tempfile.mkdtemp(prefix="gtq-zones-")
    try:
        repo, outside = make_sandbox(root)
        log = Log("The hook, where, and the audit. base-camp-ownership-zones, attempt base-attempt-008", root)
        before = snapshot(root)
        log.part("THE HOOK: the same check, for the agent's own file-editing tools (criterion 2)")
        log.out("Claude Code can run a command before each use of a file-editing tool, giving it the tool call as JSON on standard input.",
                "If the command exits with 2, the edit is not made and the agent is shown what the command wrote to standard error.",
                "Below, `zones.py hook` is given tool calls made up here, in the shape Claude Code sends. No agent is running in this record.", "")
        calls = (("Write", os.path.join(repo, "participant", "context", "new-note.md"), 0, ""),
                 ("Edit", os.path.join(repo, "participant", "context", "notes.md"), 0, ""),
                 ("Edit", os.path.join(repo, "content", "quests", "sample-quest.md"), 2, "R10"),
                 ("Write", os.path.join(repo, "local-data", "saved-response.json"), 2, "R5"),
                 ("Write", os.path.join(repo, "generated", "index.html"), 2, "R6"),
                 ("Write", os.path.join(repo, "participant", "context", "..", "..", "README.md"), 2, "R10"),
                 ("Write", os.path.join(repo, "participant", "context", "link-to-curriculum", "new.md"), 2, "R10"),
                 ("MultiEdit", os.path.join(repo, "participant", "progress.yaml"), 2, "R7"),
                 ("Edit", os.path.join(repo, "participant", "tools", "zones.py"), 2, "R3"),
                 ("Write", os.path.join(repo, ".claude", "settings.local.json"), 2, "R5"),
                 ("Write", os.path.join(outside, "scratch.txt"), 0, ""),
                 ("Bash", "", 0, ""))
        for tool, path, want, rule in calls:
            call = {"tool_name": tool, "tool_input": {"file_path": path} if tool != "Bash" else {"command": "echo x > content/quests/sample-quest.md"}, "cwd": repo}
            log.out("Tool call: %s" % log.tidy(json.dumps(call)))
            code, said = log.run("hook", stdin=json.dumps(call), shown="(the tool call on standard input) ")
            log.check("%s: %s" % (tool, "let through, with exit code 0 and nothing said" if want == 0 else "stopped, with exit code 2, by rule %s" % rule),
                      code == want and (said == "" if want == 0 else ("REFUSED by rule %s." % rule) in said))
            log.out()
        log.out("THE LAST CALL ABOVE IS THE LIMIT. A shell command that writes into the curriculum is a Bash call, not a file edit, and the hook",
                "lets it through. The hook checks the agent's file-editing tools. It does not check what a command the agent runs writes.",
                "The call before it is let through for another reason: the file is not in the repository at all.", "")
        other = os.path.join(root, "REPO")
        if os.path.exists(other):
            log.out("The repository named by another spelling of its path. This disk sets capitals aside, so SANDBOX/REPO is SANDBOX/repo:")
            call = {"tool_name": "Write", "tool_input": {"file_path": os.path.join(other, "README.md")}, "cwd": repo}
            log.out("Tool call: %s" % log.tidy(json.dumps(call)))
            code, said = log.run("hook", stdin=json.dumps(call), shown="(the tool call on standard input) ")
            log.check("Write, by another spelling of the repository's path: stopped, with exit code 2, by rule R10", code == 2 and "REFUSED by rule R10." in said)
        else:
            log.out("This disk does not set capitals aside, so the repository has one spelling and that trial is not made here.")
        log.check("the hook wrote nothing: every name and byte under SANDBOX is what it was", snapshot(root) == before)

        log.part("WHERE: which zone a path belongs to (stretch goal)")
        code, said = log.run("where", "participant/context/notes.md", "content/quests/sample-quest.md", "generated/index.html", "local-data/raw-response.json",
                             "participant/context/link-to-curriculum/sample-quest.md", "stray-notes.txt")
        log.check("stretch goal: it names the zone of each of the four kinds of path, the zone a link really leads to, and a path in no zone",
                  code == 0 and all(part in said for part in ("zone:         Participant-owned", "zone:         Program-owned", "zone:         Generated and tool-managed",
                                                              "zone:         Private data", "resolves to:  content/quests/sample-quest.md", "zone:         NONE. It fits no zone")))

        log.part("THE AUDIT: a check that fails when a file is in no zone (stretch goal)")
        code, said = log.run("audit")
        log.check("stretch goal: with every file of the sandbox in a zone, the audit passes", code == 0 and "EVERY FILE IS IN A ZONE." in said)
        log.out("", "A file is then put where no zone covers it, by this script, in the sandbox:")
        with open(os.path.join(repo, "stray-notes.txt"), "w", encoding="utf-8") as f:
            f.write("made up\n")
        code, said = log.run("audit")
        log.check("stretch goal: the audit fails, with exit code 1, and names the file", code == 1 and "    stray-notes.txt" in said and "FILES IN NO ZONE: 1." in said)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    log.part("THE REAL REPOSITORY. Read only: nothing is written")
    done = subprocess.run([sys.executable, TOOL, "audit"], capture_output=True, text=True)
    log.lines += ["$ python3 participant/tools/zones.py audit", "-" * 78, done.stdout.rstrip("\n"), "-" * 78, "exit code: %d" % done.returncode]
    log.check("every file at the top of the real repository is in a zone. (Anything inside participant/ is in the participant's zone by being there, so this cannot fail for it.)", done.returncode == 0 and "IN NO ZONE:                  0" in done.stdout)
    def git(*args):
        return subprocess.run(["git", "-C", os.path.dirname(PARTICIPANT)] + list(args), capture_output=True, text=True)
    tracked = sorted(set(line.split("/")[0] for line in git("ls-files").stdout.splitlines()))
    ignored = [name for name in ("generated", "generated.lock", "local-data", ".venv", ".claude/settings.local.json", ".env", "participant/node_modules") if git("check-ignore", "-q", name).returncode == 0]
    log.out("", "What Git itself says, asked here and not taken from the rules:", "  top-level names Git tracks: %s" % ", ".join(tracked), "  of the names the rules call not tracked, Git ignores: %s" % ", ".join(ignored))
    log.check("criterion 1, the Git status: every top-level name Git tracks is `participant` or is listed as program-owned, and nothing listed as program-owned is missing from Git", sorted(set(tracked) - {"participant"}) == sorted(PROGRAM_TOP))
    log.check("criterion 1, the Git status: Git ignores each of the seven generated and private names asked about", len(ignored) == 7)
    done = subprocess.run([sys.executable, TOOL, "rules", "--check"], capture_output=True, text=True)
    log.lines += ["$ python3 participant/tools/zones.py rules --check", "-" * 78, done.stdout.rstrip("\n"), "-" * 78, "exit code: %d" % done.returncode]
    log.check("criterion 1: participant/context/zone-rules.md is what the tool writes from its rules today: it was not edited by hand since", done.returncode == 0)
    with open(os.path.join(PARTICIPANT, "context", "zone-rules.md"), encoding="utf-8") as f:
        rules = f.read()
    rows = [line for line in rules.split("\n") if line.startswith("| **")]
    log.check("criterion 1: the rules name four zones, and the row of each has what it holds, who may write, whether the agent may, and its Git status",
              len(rows) == 4 and all(len([cell for cell in row.split("|")[1:-1] if cell.strip()]) == 5 for row in rows)
              and all(name in rules for name in ("**Program-owned**", "**Participant-owned**", "**Generated and tool-managed**", "**Private data**"))
              and rules.count("Tracked.") >= 2 and rules.count("Not tracked.") >= 2)
    ok = log.save("hook-and-audit.txt") and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

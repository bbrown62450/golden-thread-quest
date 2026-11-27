#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/tools/zones.py, in the part added after the review (the settings
for the shell's sandbox and the check of a settings file), and runs the tests of that part against the copy.
Records logs/planted-bugs-sandbox.txt.

WHY A SECOND SCRIPT. scripts/planted_bugs.py, from before the review, rewrote the real zones.py while it ran. The
agent can no longer do that: the sandbox refuses the agent's shell any write to that file, and the hook refuses its
file edits. So this script copies the tool and its tests to a temporary folder and plants each bug in the copy. The
real tool is never changed. The first script's record, logs/planted-bugs.txt, stands as it was made, before the review.

WHAT THESE BUGS CAN AND CANNOT SHOW. They are bugs in how the list of refused places is worked out and how a settings
file is compared with it. A test can catch those. No test here can show that the operating system REFUSES a write:
that is shown by logs/shell-sandbox.txt, which tries.

Run from anywhere:  python3 scripts/planted_bugs_sandbox.py        Exit code 0 if every bug was caught, 1 if not.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
REPO = os.path.dirname(PARTICIPANT)
TOOLS = os.path.join(PARTICIPANT, "tools")
LIMIT = 120

BUGS = [
    # the list
    ("the program-owned folders are left off the list", "    denied = list(PROGRAM_TOP)  ", "    denied = []  "),
    ("the generated and tool-managed places, `.venv/` and `.git/` among them, are left off", "    denied += [name for name in GENERATED_TOP if name not in denied]", "    pass"),
    ("the private-data folder is left off the list", '    denied += [name for name in PRIVATE_TOP if "/" not in name]', "    pass"),
    ("every other name at the top is left off: a new top-level folder is writable", "    denied += [pattern for pattern in all_but(TOP_ALLOWED) if pattern not in denied]", "    pass"),
    ("the application's record files are left off the list", '    denied += ["participant/" + name for name in APPLICATION_TOP]', "    pass"),
    ("the zone tool itself is left off the list", "    denied += [THE_TOOL]  ", "    pass  "),
    ("the attempt folders' files are listed by pattern only, so a folder can be moved from under them: a reader's find",
     '        denied += ["%s/%s" % (folder, name) for name in APPLICATION_IN_AN_ATTEMPT]', "        pass"),
    ("the pattern for an attempt folder made later is left off", '    denied += ["participant/evidence/**/" + name for name in APPLICATION_IN_AN_ATTEMPT]', "    pass"),
    ("the names that steer the agent are refused at the top only, not inside participant/: a reader's find", '    denied += ["participant/**/" + name for name in CONTROL_NAMES]', "    pass"),
    ("files with a credential's name are left off the list", '    denied += ["**/" + name for name in CREDENTIAL_NAMES]', "    pass"),
    ("the tool-managed names are left off the list", '    denied += ["**/" + name for name in TOOL_NAMES_ANYWHERE]', "    pass"),
    ("the participant's whole folder is put on the list", "    denied += [THE_TOOL]  ", '    denied += [THE_TOOL, "participant"]  '),
    # everything but participant
    ("the patterns for the top use square brackets, which the real sandbox does not match: what my own check found", '        patterns += [prefix + ch + "*" for ch in NAME_CHARACTERS if ch not in goes_on]',
     '        patterns += [prefix + "[" + "".join(ch for ch in NAME_CHARACTERS if ch not in goes_on) + "]*"]'),
    ("a name that leaves `participant` partway is not matched (part..., particle)", '    prefixes = sorted(set(name[:n] for name in allowed for n in range(len(name) + 1)))', '    prefixes = [""]'),
    ("a name longer than `participant` is not matched (participant2)", '    prefixes = sorted(set(name[:n] for name in allowed for n in range(len(name) + 1)))', '    prefixes = sorted(set(name[:n] for name in allowed for n in range(len(name))))'),
    ("a name that stops short of `participant` is not matched (p, pa)", "        if prefix and prefix not in allowed:\n            patterns.append(prefix)", "        pass"),
    ("names beginning with a digit, a dot, an underscore or a dash are not matched", 'NAME_CHARACTERS = "abcdefghijklmnopqrstuvwxyz0123456789._-"', 'NAME_CHARACTERS = "abcdefghijklmnopqrstuvwxyz"'),
    ("`participant` itself is matched and refused", "if ch not in goes_on]      # leaves the allowed names here", "]      # leaves the allowed names here"),
    # the settings
    ("the settings leave the sandbox off", '{"sandbox": {"enabled": True, "failIfUnavailable": True,', '{"sandbox": {"enabled": False, "failIfUnavailable": True,'),
    ("the settings let a command run when the sandbox cannot start", '"failIfUnavailable": True, "allowUnsandboxedCommands": False,', '"failIfUnavailable": False, "allowUnsandboxedCommands": False,'),
    ("the settings let a command be run outside the sandbox", '"failIfUnavailable": True, "allowUnsandboxedCommands": False,', '"failIfUnavailable": True, "allowUnsandboxedCommands": True,'),
    ("the settings do not deny the tools that run a command elsewhere", '            "permissions": {"deny": list(UNSANDBOXED_TOOLS)}}', '            "permissions": {"deny": []}}'),
    ("the settings are made for the path as it was typed, not the real one", "def sandbox_settings(root):\n    root = os.path.realpath(root)", "def sandbox_settings(root):"),
    # the check
    ("the check accepts settings with no sandbox block", '        return ["the settings have no `sandbox` block, so the shell is not sandboxed by them"]', "        return []"),
    ("the check does not look at the three switches", "        if box.get(key) is not wanted:", "        if False:"),
    ("the check takes a missing switch for one that is set right", "        if box.get(key) is not wanted:", "        if key in box and box.get(key) is not wanted:"),
    ("the check accepts a setting it does not know, such as one that exempts commands", "    extra = sorted(set(box) - KNOWN_SANDBOX_KEYS)\n    if extra:", "    extra = sorted(set(box) - KNOWN_SANDBOX_KEYS)\n    if False:"),
    ("the check accepts an unknown setting about files", "    extra = sorted(set(files) - KNOWN_FILESYSTEM_KEYS)\n    if extra:", "    extra = sorted(set(files) - KNOWN_FILESYSTEM_KEYS)\n    if False:"),
    ("the check does not notice a place missing from the list", "    if missing:\n        wrong.append(", "    if False:\n        wrong.append("),
    ("the check does not look at the disk for attempt folders, so a new one is not missed", "    wanted = sandbox_denied(root)\n    missing", "    wanted = sandbox_denied(os.path.join(root, 'no-such-folder'))\n    missing"),
    ("the check accepts an allowed place that is not one full path", '        if not isinstance(path, str) or not os.path.isabs(path) or any(ch in path for ch in "*?[~"):', "        if not isinstance(path, str):"),
    ("the check does not notice an allowed place inside the repository", "        if (real + os.sep).startswith(root + os.sep):", "        if False:"),
    ("the check does not notice an allowed folder that the repository is inside", "        elif (root + os.sep).startswith(real.rstrip(os.sep) + os.sep):", "        elif False:"),
    ("the check does not look for the denial of the tools that run a command elsewhere", "    if lacking:\n        wrong.append(", "    if False:\n        wrong.append("),
    ("the command says the settings are fine when they are not", '        print("Make them again with `zones.py sandbox`. The participant puts them in place, by hand.")\n        return 1',
     '        print("Make them again with `zones.py sandbox`. The participant puts them in place, by hand.")\n        return 0'),
    ("a settings file that cannot be read passes", '        print("NOT CHECKED: the settings file could not be read as JSON.")\n        return 1', '        print("NOT CHECKED: the settings file could not be read as JSON.")\n        return 0'),
    # the rules document
    ("the rules document does not say how the shell is covered", '''            "## The agent's shell: refused by the operating system", "",''', ""),
    ("the rules document leaves a rule out of the table for the shell", '''            "| R8 a hard link | Partly | A hard link TO a refused file cannot be made. A file that already has two names is not noticed |",''', ""),
    ("the rules document does not say that the sandbox is not the rules", "It does not apply the rules; it refuses places.", "It applies the rules."),
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-m", "unittest", "tests.test_zones.TheShellSandbox"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(TOOLS, "zones.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/tools/zones.py: the settings for the shell's sandbox. base-camp-ownership-zones, attempt base-attempt-008",
             "Recorded by scripts/planted_bugs_sandbox.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the tests",
             "of that part (tests.test_zones.TheShellSandbox) are run against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "tools")
        os.makedirs(os.path.join(work, "tests"))
        shutil.copy(os.path.join(TOOLS, "tests", "test_zones.py"), os.path.join(work, "tests"))
        copy = os.path.join(work, "zones.py")
        shutil.copy(os.path.join(TOOLS, "zones.py"), copy)
        passed, said = run_tests(work)
        lines.append("First, with no bug planted, the tests against the copy: %s" % said)
        if not passed:
            lines.append("THE TESTS DO NOT PASS WITHOUT A BUG, so nothing below would mean anything. Stopped.")
            problems.append("the tests fail with no bug planted")
        else:
            lines.append("")
            for number, (what, old, new) in enumerate(BUGS, 1):
                if source.count(old) != 1:
                    lines.append("%2d. NOT PLANTED  %s: the text to change was found %d times, not once" % (number, what, source.count(old)))
                    problems.append("bug %d could not be planted" % number)
                    continue
                with open(copy, "w", encoding="utf-8") as f:
                    f.write(source.replace(old, new))
                passed, said = run_tests(work)
                lines.append("%2d. %-7s %s" % (number, "MISSED" if passed else "CAUGHT", what))
                lines.append("            %s" % said)
                if passed:
                    missed.append(what)
            with open(copy, "w", encoding="utf-8") as f:
                f.write(source)
            passed, said = run_tests(work)
            lines += ["", "Last, with the copy put back as it was: %s" % said]
            if not passed:
                problems.append("the tests fail after the copy was put back")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    with open(os.path.join(TOOLS, "zones.py"), encoding="utf-8") as f:
        same = f.read() == source
    unchanged = git_state() == before
    lines.append("The real tool is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    planted = len(BUGS) - sum(1 for p in problems if "could not be planted" in p)
    result = "RESULT: %d OF %d PLANTED BUGS CAUGHT." % (planted - len(missed), len(BUGS)) + ("" if not missed and not problems else " NOT ALL: " + "; ".join(missed + problems))
    lines += ["", result]
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs-sandbox.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(result)
    for line in lines:
        if "MISSED" in line or "NOT PLANTED" in line:
            print(line)
    return 0 if not missed and not problems else 1


if __name__ == "__main__":
    sys.exit(main())

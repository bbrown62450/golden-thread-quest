#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the quest base-camp-ownership-zones.

Puts one bug at a time into participant/tools/zones.py, runs every test, notes which tests fail, and takes the bug out
again. At the end it checks that the file is the same as when it started, byte for byte.

It changes zones.py while it runs. Do not use the tool, or let the hook run, at the same time: while a bug is planted the tool is wrong on purpose.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
TARGET = os.path.join(PARTICIPANT, "tools", "zones.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. `..` is worked out and links are not followed (criterion 3)',
     '        resolved = os.path.realpath(absolute)                # where a write would really land',
     '        resolved = lexical'),
    ('B. A path that resolves outside the repository is judged by the path as it was written (criterion 3)',
     '        relative = below(resolved, root_stat)\n        as_written',
     '        relative = below(resolved, root_stat) or below(lexical, root_stat)\n        as_written'),
    ('C. A folder is the root only under the exact spelling of its name, so another spelling of the repository is outside (a reader\'s finding)',
     '        return os.path.samestat(os.stat(path), stat)',
     '        return os.path.samestat(os.stat(path), stat) and os.path.basename(path) in os.listdir(os.path.dirname(path))'),
    ('D. The zone is taken from the path as written, not from where it resolves (criterion 3)',
     '        zone, rule = zone_of(relative)\n        why = ""',
     '        zone, rule = zone_of(as_written or relative)\n        why = ""'),
    ('E. The program-owned zone may be written (criterion 2)',
     '        self.allowed = rule == ALLOW',
     '        self.allowed = rule in (ALLOW, "R10")'),
    ('F. Private data may be written (criterion 2)',
     '        self.allowed = rule == ALLOW',
     '        self.allowed = rule in (ALLOW, "R5")'),
    ('G. A path in no zone may be written (criterion 2)',
     '        self.allowed = rule == ALLOW',
     '        self.allowed = rule in (ALLOW, "R11")'),
    ('H. The files the application writes are not excepted (the rules)',
     '        return ("participant", "R7") if application else ("participant", ALLOW)',
     '        return ("participant", ALLOW)'),
    ('H2. An application file is matched by its exact name only, so a path inside it passes (a reader\'s finding)',
     '        application = (len(low) >= 2 and low[1] in [fold(name) for name in APPLICATION_TOP]) or (\n            len(low) >= 5 and low[1] == "evidence" and low[4] in [fold(name) for name in APPLICATION_IN_AN_ATTEMPT])',
     '        application = (len(low) == 2 and low[1] in [fold(name) for name in APPLICATION_TOP]) or (\n            len(low) == 5 and low[1] == "evidence" and low[4] in [fold(name) for name in APPLICATION_IN_AN_ATTEMPT])'),
    ('I. A credential\'s name is not looked for (the rules)',
     '    if any(matches(part, CREDENTIAL_NAMES) and fold(part) != ".env.example" for part in parts):',
     '    if False:'),
    ('I2. The agent may write what steers it, and this tool (a reader\'s finding)',
     '    if low[0] == "participant" and (any(matches(part, CONTROL_NAMES) for part in parts[1:]) or joined == fold(THE_TOOL) or joined.startswith(fold(THE_TOOL) + "/")):',
     '    if False:'),
    ('I3. Names are compared without setting capitals aside (the rules)',
     '    return unicodedata.normalize("NFKC", text).casefold()',
     '    return text'),
    ('J. A hard link is not noticed (criterion 3)',
     '                if os.stat(resolved).st_nlink > 1:',
     '                if False:'),
    ('J2. A path through a file is not noticed (a reader\'s finding)',
     '                if os.path.lexists(parent) and not os.path.isdir(parent):',
     '                if False:'),
    ('K. Folders are made before the check (criteria 2 and 4)',
     '    verdict = judge(given, root)             # THE CHECK. Nothing has been created or opened for writing yet',
     '    os.makedirs(os.path.dirname(os.path.join(root, given)), exist_ok=True)\n    verdict = judge(given, root)             # THE CHECK. Nothing has been created or opened for writing yet'),
    ('L. A refused write is made all the same (criterion 4)',
     '    if not verdict.allowed:\n        return 1, lines + ["Nothing was written, and nothing was created."]\n    target = verdict.resolved',
     '    target = verdict.resolved or os.path.join(root, given)'),
    ('M. A refusal does not say which rule (criterion 4)',
     '        "ALLOWED by" if verdict.allowed else "REFUSED by", verdict.rule,',
     '        "ALLOWED by" if verdict.allowed else "REFUSED by", "a",'),
    ('M2. A refusal does not give the rule\'s words (criterion 4)',
     'where, zone, RULE_TEXT[verdict.rule])',
     'where, zone, "")'),
    ('N. The path is not resolved again after its folders are made (the moment between check and write)',
     '        if not again.allowed or again.resolved != target:',
     '        if False:'),
    ('N2. Folders made for a write that fails are left behind (criterion 4)',
     '        for path in made:                    # deepest first. rmdir takes away an empty folder and nothing else',
     '        for path in []:                      # deepest first. rmdir takes away an empty folder and nothing else'),
    ('N3. A temporary name that is taken is written over (the write)',
     'os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)',
     'os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)'),
    ('N4. An existing file\'s permissions are lost (the write)',
     '        mode = os.stat(target).st_mode & 0o777 if os.path.exists(target) else 0o644',
     '        mode = 0o644'),
    ('O. Nothing in the participant\'s folder may be written (criterion 5)',
     '        return ("participant", "R7") if application else ("participant", ALLOW)',
     '        return ("participant", "R7")'),
    ('O2. A root inside the real repository is accepted (a reader\'s finding)',
     '    if inside:\n        return "the root is',
     '    if False:\n        return "the root is'),
    ('P. The hook lets every edit through (criterion 2)',
     '        verdict = judge(given, args.root, cwd)\n        if verdict.allowed:\n            return 0',
     '        verdict = judge(given, args.root, cwd)\n        if True:\n            return 0'),
    ('Q. The hook stops an edit with exit code 1, which Claude Code does not treat as a refusal (criterion 2)',
     '        sys.stderr.write("zones: %s The edit was not made. The zone rules are in participant/context/zone-rules.md.\\n" % explain(verdict))\n        return 2',
     '        sys.stderr.write("zones: %s The edit was not made. The zone rules are in participant/context/zone-rules.md.\\n" % explain(verdict))\n        return 1'),
    # NOT PLANTED: taking out the last line of the file, which turns any answer of the hook but 0 into 2. No test can
    # see that line work, because nothing before it gives another answer unless it is itself broken. It is a backstop
    # with no test of its own, and PROOF.md says so.
    ('R. The hook lets an edit through when it cannot read the call (criterion 2)',
     '        sys.stderr.write("zones: REFUSED. The zone check itself failed (%s), so the edit was not made.\\n" % type(failure).__name__)\n        return 2',
     '        return 0'),
    ('S. The hook does not look at a notebook edit (criterion 2)',
     'if tool not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):',
     'if tool not in ("Edit", "Write", "MultiEdit"):'),
    ('T. The hook takes a relative path from the repository\'s top, not from where the agent is working (criterion 3)',
     '        verdict = judge(given, args.root, cwd)\n        if verdict.allowed:',
     '        verdict = judge(given, args.root)\n        if verdict.allowed:'),
    ('U. The hook lets through anything that resolves outside, even a path written inside the repository (criterion 3)',
     '            if below(os.path.normpath(absolute), os.stat(args.root)) is None:\n                return 0',
     '            if True:\n                return 0'),
    ('V. The audit does not report a file in no zone (stretch goal)',
     '        if zone == "none":\n            homeless.append(relative)',
     '        if False:\n            homeless.append(relative)'),
    ('X. `Participant/` in other capitals is taken for the participant\'s folder (the rules)',
     '        if rule == ALLOW and relative.split("/")[0] != "participant":',
     '        if False:'),
    ('Y. A folder is accepted as a file to write (the rules)',
     '                if os.path.isdir(resolved):\n                    return Verdict(given, resolved, relative, zone, "R11", "it is a folder, not a file")',
     '                if False:\n                    return None'),
    ('Z. The rules document leaves out who may write (criteria 1 and 6)',
     'out.append("| **%s** | %s | %s | %s | %s |" % (zone["name"], zone["what"], zone["writer"],',
     'out.append("| **%s** | %s | %s | %s | %s |" % (zone["name"], zone["what"], "",'),
    ('Z2. A folder is left off the program-owned list, so the rules and Git disagree (criterion 1)',
     '"prototype", "deploy", "docs",',
     '"prototype", "docs",'),
]


def run_tests():
    try:
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=os.path.join(PARTICIPANT, "tools"), capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return "THE TESTS DID NOT FINISH IN 3 MINUTES: the bug made the tool hang", ["(the whole run).it_hung"]
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_zones\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def outside_participant():
    """What `git status` lists in the real repository outside participant/: changed, new and deleted files."""
    done = subprocess.run(["git", "-C", os.path.dirname(PARTICIPANT), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True)
    return [line for line in done.stdout.splitlines() if not line[3:].startswith("participant/")]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    at_start = outside_participant()
    out = ["Do the tests notice a broken zone check? base-camp-ownership-zones, attempt base-attempt-008",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/tools/zones.py, every test was run, and the bug was taken out again.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            out += ["PLANTED BUG %s" % title]
            if good.count(old) != 1:
                out += ["  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good)
            out += ["  tests that failed: %d" % len(failed)] + ["    %s" % name for name in failed[:6]] + (["    ... and %d more" % (len(failed) - 6)] if len(failed) > 6 else [])
            if not failed:
                out += ["    NONE. THIS BUG WAS NOT CAUGHT."]
                missed.append(title)
            out += [""]
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    out += ["After the last bug was taken out: zones.py is byte for byte what it was at the start. %s" % ("OK" if restored else "NOT RESTORED"), ""]
    # While a bug is planted the tool is wrong on purpose. So: did any test, run against a broken tool, touch the real
    # repository outside the participant's folder? Git is asked what it sees there, before and after.
    untouched = outside_participant() == at_start
    out += ["What Git sees outside participant/ in the real repository is what it saw before the first bug: %s"
            % ("yes, nothing there changed" if untouched else "NO. SOMETHING OUTSIDE participant/ WAS CREATED OR CHANGED: %s" % sorted(set(outside_participant()) ^ set(at_start))), ""]
    ok = clean and restored and not missed and untouched
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored." % len(BUGS) if ok
                            else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "the tests did not pass before any bug, or the file was not restored"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

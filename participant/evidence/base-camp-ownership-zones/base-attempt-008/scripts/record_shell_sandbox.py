#!/usr/bin/env python3
"""Records logs/shell-sandbox.txt: what happens when a shell command, and a program the shell starts, try to write
where the agent may not. For the quest base-camp-ownership-zones, after the review that asked for the shell to be closed.

THIS IS RUN BY THE AI AGENT, IN THE AGENT'S OWN SHELL, AGAINST THE REAL REPOSITORY. That is the only place the thing
being tested exists: the sandbox the operating system keeps around the agent's shell. A sandbox folder of made-up
files would prove nothing about it.

SO IT IS WRITTEN TO BE SAFE IF THE SANDBOX IS NOT THERE.

    1. It first asks a question that cannot change anything: it opens existing files for writing, writes nothing,
       and closes them (participant/tools/zone_probe.py). If even ONE of the protected files opens, this shell is not
       sandboxed, and THE SCRIPT STOPS THERE. It makes no attempt to create anything.
    2. Only if every one of those is refused does it try real writes. Each one tries to CREATE a new file or folder
       with a name that says what it is ("zone-probe-not-a-real-..."). None changes or removes a file that exists.
    3. After each attempt it looks whether the thing now exists. If one does, the check fails, the script says so in
       capitals, and it leaves the thing where it is for a person to see and remove.
    4. It asks Git, before and after, what has changed outside participant/.

It never deletes anything outside participant/. Inside it, it creates one temporary file and removes it, to show
that the shell can still write where the agent is allowed to.

Run from anywhere, by the agent:  python3 scripts/record_shell_sandbox.py
Exit code 0 if every check came out as expected, 1 if not, 2 if the shell is not sandboxed and nothing was tried.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
REPO = os.path.dirname(PARTICIPANT)
PROBE = os.path.join("participant", "tools", "zone_probe.py")
ZONES = os.path.join("participant", "tools", "zones.py")
HERE_IN_REPO = os.path.relpath(ATTEMPT, REPO)

# Existing files that the rules say the agent may not write. Opened for writing, and nothing written.
PROTECTED = ["quest_app/cli.py", "content/site.yaml", "docs/PARKING-LOT.md", "tools/secret_scan.py", "tests/unit/test_secret_patterns.py", "CLAUDE.md", "Makefile", ".gitignore",
             ".git/HEAD", "generated/build-manifest.json", ".venv/pyvenv.cfg", "participant/progress.yaml", "participant/ACTIVITY.md", "participant/tools/zones.py",
             HERE_IN_REPO + "/manifest.yaml", HERE_IN_REPO + "/review.yaml", HERE_IN_REPO + "/submission.yaml"]
# Existing files the agent MAY write: the same question must be answered the other way, or the probe proves nothing.
OPEN = ["participant/tools/zone_probe.py", "participant/context/zone-rules.md", HERE_IN_REPO + "/PROOF.md"]
MOVED = HERE_IN_REPO + "-moved"          # where part 4 tries to rename this attempt folder to

# Real attempts to create something. (what it shows, the shell command, the path that must not exist afterwards)
ATTEMPTS = [
    ("a redirection into the curriculum, the reviewer's own example", "echo x > content/zone-probe-not-a-real-file.txt", "content/zone-probe-not-a-real-file.txt"),
    ("a PROGRAM started by the shell, writing into the application. No reading of the command's text could see this",
     "python3 -c \"open('quest_app/zone_probe_not_a_real_file.py', 'w').write('x')\"", "quest_app/zone_probe_not_a_real_file.py"),
    ("touch, in the program's documentation", "touch docs/zone-probe-not-a-real-file.md", "docs/zone-probe-not-a-real-file.md"),
    ("a new folder, among the program's tools", "mkdir tools/zone-probe-not-a-real-folder", "tools/zone-probe-not-a-real-folder"),
    ("a copy of a participant's file into the curriculum", "cp participant/context/zone-rules.md content/zone-probe-not-a-real-copy.md", "content/zone-probe-not-a-real-copy.md"),
    ("a new file at the top of Git's own folder", "echo x > .git/zone-probe-not-a-real-file", ".git/zone-probe-not-a-real-file"),
    ("a new file in the private-data folder", "echo x > local-data/zone-probe-not-a-real-file.txt", "local-data/zone-probe-not-a-real-file.txt"),
    ("a new file where the application keeps an attempt's validation results", "echo x > %s/validation/zone-probe-not-a-real-file" % HERE_IN_REPO, HERE_IN_REPO + "/validation/zone-probe-not-a-real-file"),
    ("a file with a credential's name, inside the participant's own folder", "echo x > participant/context/.env", "participant/context/.env"),
    ("a file with a key file's name, by a program", "python3 -c \"open('participant/context/zone-probe-not-a-real.pem', 'w').write('x')\"", "participant/context/zone-probe-not-a-real.pem"),
    ("a file named CLAUDE.md, which steers the agent, inside the participant's own folder. The first version of the list missed this; a reader found it",
     "echo x > participant/context/CLAUDE.md", "participant/context/CLAUDE.md"),
    ("a folder named .claude inside the participant's folder", "mkdir participant/context/.claude", "participant/context/.claude"),
    ("a NEW file at the top of the repository, in no zone. The second version of the list let this through; my own check found it",
     "echo x > zone-probe-not-a-real-file.txt", "zone-probe-not-a-real-file.txt"),
    ("a new folder at the top of the repository", "mkdir zone-probe-not-a-real-folder", "zone-probe-not-a-real-folder"),
    ("a file a test runner would load from the top of the repository", "python3 -c \"open('conftest.py', 'w').write('x')\"", "conftest.py"),
    ("a neighbour of `participant` with a longer name", "mkdir participant-zone-probe", "participant-zone-probe"),
    ("a new file in the built site", "echo x > generated/zone-probe-not-a-real-file.html", "generated/zone-probe-not-a-real-file.html"),
    ("a new file among the installed packages, where the participant's own commands would run it", "echo x > .venv/zone-probe-not-a-real-file.pth", ".venv/zone-probe-not-a-real-file.pth"),
]


class Log:
    def __init__(self):
        self.lines, self.problems, self.count = [], [], 0

    def out(self, *lines):
        self.lines += list(lines) if lines else [""]

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def run(self, command):
        """Runs a command in a shell, from the top of the repository, and writes down what it printed."""
        done = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=REPO)
        said = (done.stdout + done.stderr).rstrip("\n").replace(REPO, "REPO")
        self.lines += ["$ " + command, "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        return done.returncode, said


def outside_participant():
    listed = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all", "--ignored=matching"], capture_output=True, text=True).stdout.split("\n")
    return sorted(line for line in listed if line and not line[3:].startswith("participant/"))


def main():
    log = Log()
    log.out("The agent's shell, and what the operating system lets it write. base-camp-ownership-zones, attempt base-attempt-008",
            "Recorded by scripts/record_shell_sandbox.py, run by the AI agent in its own shell, against the real repository.",
            "Each block between dashed lines is what a command printed. REPO stands for the repository's top folder.",
            "Every command is run from REPO.")
    before = outside_participant()

    log.part("1. THE SETTINGS, compared with the list the zone rules give")
    code, said = log.run("python3 %s sandbox --check .claude/settings.local.json" % ZONES)
    log.check("this one settings file turns the sandbox on, has none of the settings that let a command out of it, denies the two tools that run a command elsewhere, and lists every place the rules give",
              code == 0 and "THIS FILE HAS EVERY PLACE" in said)
    log.out("  That compares a file with a list. Whether the settings are HONOURED is what the rest of this record shows.")

    log.part("2. A QUESTION THAT CHANGES NOTHING: may a program started by this shell open these files for writing?")
    log.out("participant/tools/zone_probe.py opens each file for reading and writing, writes nothing, closes it, and compares the file's",
            "checksum and last-changed time before and after. These %d files are ones the rules say the agent may not write." % len(PROTECTED))
    code, said = log.run("python3 %s %s" % (PROBE, " ".join(PROTECTED)))
    refused = said.count("REFUSED BY THE OPERATING SYSTEM")
    log.check("the operating system refuses all %d with \"operation not permitted\", and every file is unchanged" % len(PROTECTED),
              code == 0 and refused == len(PROTECTED) and "OPENED FOR WRITING" not in said and said.count("(the file is unchanged: yes)") == len(PROTECTED))
    if refused != len(PROTECTED):
        log.out("", "THIS SHELL IS NOT SANDBOXED, or not for every one of these files. NOTHING FURTHER IS TRIED: no file is created anywhere.",
                "The settings may be missing, or this script may have been run outside the agent's shell.")
        save(log)
        return 2

    log.out("", "The same question about files the agent MAY write. If these were refused too, the answers above would mean nothing.")
    code, said = log.run("python3 %s %s" % (PROBE, " ".join(OPEN)))
    log.check("the check can come out the other way: all %d files in the participant's zone open for writing, and are unchanged" % len(OPEN),
              code == 1 and said.count("OPENED FOR WRITING") == len(OPEN) and said.count("(the file is unchanged: yes)") == len(OPEN))

    log.part("3. REAL WRITES: a shell command, or a program it starts, tries to CREATE something where the agent may not")
    log.out("Reached only because every file in part 2 was refused. Each attempt makes a new, plainly named file or folder, and changes",
            "nothing that exists. After each, the script looks whether the thing is there.")
    for what, command, target in ATTEMPTS:
        log.out("", "%s%s:" % (what[0].upper(), what[1:]))
        existed = os.path.lexists(os.path.join(REPO, target))
        code, said = log.run(command)
        there = os.path.lexists(os.path.join(REPO, target))
        log.out("Is `%s` there afterwards: %s" % (target, "YES. IT WAS CREATED. IT IS LEFT WHERE IT IS FOR A PERSON TO REMOVE" if there else "no"))
        log.check("refused with \"operation not permitted\". The command failed, and nothing was created: %s" % what.split(". ")[0], not existed and code != 0 and not there
                  and "not permitted" in said.lower())

    log.part("4. MOVING A FOLDER: the way round that a reader found")
    log.out("A file refused by a PATTERN can still be reached if the folder above it can be renamed: the pattern then no longer fits. Tried on made-up",
            "files, that worked (logs/sandbox-trials.txt). So this attempt folder's four application files are in the settings by their EXACT paths.",
            "This tries to rename THIS attempt folder. If the rename went through, the script would rename it straight back and fail the check.")
    code, said = log.run("mv %s %s" % (HERE_IN_REPO, MOVED))
    went = os.path.isdir(os.path.join(REPO, MOVED))
    if went:
        os.rename(os.path.join(REPO, MOVED), os.path.join(REPO, HERE_IN_REPO))
    log.check("refused: the attempt folder that holds a review cannot be renamed by the shell, so its review cannot be moved out from under its protection", code != 0 and not went and "not permitted" in said.lower())
    code, said = log.run("mv participant/evidence/base-camp-ownership-zones participant/evidence/base-camp-ownership-zones-moved")
    went = os.path.isdir(os.path.join(REPO, "participant/evidence/base-camp-ownership-zones-moved"))
    if went:
        os.rename(os.path.join(REPO, "participant/evidence/base-camp-ownership-zones-moved"), os.path.join(REPO, "participant/evidence/base-camp-ownership-zones"))
    log.check("refused: nor can the quest's folder above it", code != 0 and not went and "not permitted" in said.lower())

    log.part("5. WHERE THE SHELL MAY WRITE, IT STILL CAN")
    allowed = os.path.join(HERE_IN_REPO, "logs", "zone-probe-allowed-write.tmp")
    code, said = log.run("echo x > %s && cat %s && rm %s" % (allowed, allowed, allowed))
    log.check("a shell command writes a file in this attempt's own folder, reads it back and removes it", code == 0 and said.strip() == "x" and not os.path.exists(os.path.join(REPO, allowed)))
    log.out("", "WHAT THIS RECORD DOES NOT SHOW. That a write is judged by the zone rules: it is not. The operating system refuses listed places.",
            "It was not tried here: deleting or overwriting a real protected file (the harmless question in part 2 stands in for that, and the",
            "made-up files in logs/sandbox-trials.txt were deleted and renamed for real); a name at the top beginning with a character other",
            "than a letter, a digit or one of . _ -; and an attempt folder made after the settings were.")

    log.part("6. WHAT GIT SAYS CHANGED OUTSIDE participant/")
    after = outside_participant()
    log.out("Lines Git gives for files outside participant/, ignored ones included. Before this script: %d. After: %d." % (len(before), len(after)))
    log.check("Git lists the same changed, new and ignored files outside participant/ as before. (It compares names, not contents. Each attempt above was also looked for directly.)", before == after)
    return save(log)


def save(log):
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.problems), log.count) if log.problems else "ALL CHECKS PASSED. %d checks." % log.count)]
    with open(os.path.join(ATTEMPT, "logs", "shell-sandbox.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(log.lines) + "\n")
    print(log.lines[-1])
    for label in log.problems:
        print("  FAILED: " + label)
    return 1 if log.problems else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Records logs/verify-run.txt and logs/denied-run.txt for the github-verify-connection quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-verify-connection/fake_github.py,
and the account, its repositories and its tokens are invented. That is why
repository full names can be shown here.

The check writes no file, so there is nothing to clear first. Two parts need a
made-up GitHub the command line cannot make. They run in this script's own
process.

This script checks for itself. It reads from the made-up GitHub what the token
was granted and how many issues a repository holds, counts the request lines,
and scans each output with its own pattern, rather than taking the check's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/github-verify-connection"
VERIFY = SKILL + "/verify.py"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_github  # noqa: E402
import verify  # noqa: E402
from fake_github import EMPTY, ME, PAYROLL, TRACKER, FakeGitHub  # noqa: E402

# This script's own idea of what a GitHub token looks like, written apart from the check's.
LOOKS_LIKE_A_TOKEN = re.compile(r"gh[a-z]_[0-9A-Za-z]{16,}|github_pat_[0-9A-Za-z_]{16,}|Bearer\s+\S{16,}")


class Log:
    def __init__(self, title):
        self.lines, self.problems = [title], []
        self.out("Recorded by scripts/record_evidence.py. No request was sent to GitHub. The account, repositories and tokens are made up.")

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def block(self, title, code, text):
        self.out(title)
        self.lines += ["-" * 78, text.rstrip("\n"), "-" * 78, "exit code: %s" % code]

    def command(self, *args):
        done = subprocess.run([sys.executable, VERIFY] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.block("$ python3 %s" % " ".join([VERIFY] + list(args)), done.returncode, done.stdout)
        return done.returncode, done.stdout

    def in_process(self, what, fake, expect, token=None):
        """The check started inside this script, for a made-up GitHub that the command line cannot make."""
        report, code, printed = verify.Report(), 1, io.StringIO()
        try:
            code = verify.run(verify.Client(fake.get), report, expect)
        except verify.Stop as stop:
            report.say("STOPPED: %s." % stop)
        with contextlib.redirect_stdout(printed):
            code = code if report.finish(token) else 3
        self.block("(inside this script) %s" % what, code, printed.getvalue())
        return code, printed.getvalue()

    def save(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.out()
        self.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems else "%d OF %d CHECKS FAILED." % (len(self.problems), count)))
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


def row(text, start):
    return next((line for line in text.splitlines() if start in line), "")


def requests_in(text):
    return [line.split(":", 1)[1].strip() for line in text.splitlines() if re.match(r"github-verify:      [A-Z]+ /", line)]


def verify_run():
    log = Log("Verifying a GitHub connection. github-verify-connection, attempt github-attempt-003")
    fake = FakeGitHub()
    log.out("Known to this script from the made-up GitHub: the account is %s, user id %d. The made-up fine-grained token was"
            % (ME["login"], ME["id"]))
    log.out("granted %s. %s holds %d issues and %d pull requests."
            % (" and ".join(sorted(fake.granted)), TRACKER, fake.repos[TRACKER]["issues"], fake.repos[TRACKER]["pulls"]))
    log.out("The account also has one public repository, %s, which any token can see." % fake_github.NOTES_REPO)

    log.part("PART 1. The verification, with a read-only fine-grained token")
    code, text = log.command("--source", "fake", "--expect", TRACKER, "--expect", EMPTY)
    made = requests_in(text)
    log.check("exit code 0", code == 0)
    log.check("criterion 1: the identity reported is the one the made-up GitHub answers with, and no login is in the command or in verify.py",
              "acts as login %s, user id %d" % (ME["login"], ME["id"]) in text
              and ME["login"] not in open(os.path.join(ROOT, VERIFY), encoding="utf-8").read())
    log.check("criterion 2: the run says what GitHub reports about the token's permissions, and when the token expires",
              "2. WHAT IT MAY DO. GitHub reports no scopes for this token" in text and "the token expires: 2026-11-27 09:00:00 UTC" in text)
    log.check("criterion 2: it says plainly that whether the token may write was not tested", "Whether it may write is NOT tested" in text)
    listed = sorted(re.findall(r"^github-verify:      (\S+/\S+), (?:private|public)\.", text, re.M))
    log.check("criterion 3: the repositories listed, by full name, are the 2 the token was granted and the account's 1 public one: %s" % ", ".join(listed),
              listed == sorted(fake.visible()) and len(listed) == 3)
    log.check("the run says that a public repository is listed whatever the token was given", "Being listed here does not show that the token was granted it" in text)
    log.check("one safe read: the number of issues reported for %s is the number the made-up GitHub holds, %d"
              % (TRACKER, fake.repos[TRACKER]["issues"]), "GitHub returned %d. Only the count was used" % fake.repos[TRACKER]["issues"] in text)
    log.check("criterion 5: the run states that only reads were issued, and lists its %d requests" % len(made),
              "6. ONLY READS. %d requests were made, and every one was a GET" % len(made) in text and len(made) == 10)
    log.check("criterion 5: counted by this script, every listed request is a GET",
              all(line.startswith("GET /") for line in made) and not re.search(r"\b(POST|PUT|PATCH|DELETE)\b", text))
    log.check("criterion 6: the run says its output was scanned before printing and nothing was found",
              "7. SCAN OF THIS OUTPUT." in text and "Nothing was found" in text)
    log.check("criterion 6: scanned again by this script with its own pattern, the output holds nothing that looks like a token",
              not LOOKS_LIKE_A_TOKEN.search(text))

    log.part("PART 2. The same verification with an older kind of token, whose scopes are wider than reading needs (criteria 2 and 7)")
    code, text = log.command("--source", "fake", "--fake-case", "classic-wide", "--expect", TRACKER)
    log.check("exit code 0: the repository can be read", code == 0)
    log.check("criterion 2: the four scopes GitHub reports are listed", "The scopes GitHub reports for this connection are: delete_repo, read:org, repo, workflow" in text)
    log.check("criterion 7: three of them are flagged as broader than needed, and one as read-only",
              text.count("ALLOWS MORE THAN READING") == 3 and "scope read:org: read-only" in text
              and "RESULT: every expected repository can be read. 3 scopes are broader than reading needs" in text)
    log.check("criterion 3: this token reaches all 4 of the account's repositories, and they are listed by full name",
              sorted(re.findall(r"^github-verify:      (\S+/\S+), (?:private|public)\.", text, re.M)) == sorted(FakeGitHub("classic-wide").repos))

    log.part("PART 3. GitHub echoes back something shaped like a token (criterion 6)")
    fake = FakeGitHub()
    planted = "github" + "_pat_" + "Q7" * 20
    fake.leak = planted
    log.out("The made-up GitHub is made to answer \"who am I?\" with a login that is shaped like a token. The value is")
    log.out("made up here, is not a token, and is not written in this log.")
    code, text = log.in_process("the verification against that made-up GitHub", fake, [TRACKER])
    log.check("exit code 3", code == 3)
    log.check("the value is nowhere in the output, and [REDACTED] is in its place", planted not in text and "acts as login [REDACTED]" in text)
    log.check("the run says a credential-shaped value was found and replaced", "FOUND in 1 line, and replaced with [REDACTED]" in text)

    log.part("PART 4. A token GitHub no longer accepts")
    code, text = log.command("--source", "fake", "--fake-case", "rejected", "--expect", TRACKER)
    log.check("exit code 1: the check could not be made", code == 1)
    log.check("it says so, and does not say the connection is fine or the repository empty",
              "GitHub rejected the token (401)" in text and "That is not the same as the connection being fine" in text and "REACHABLE" not in text)
    return log.save("verify-run.txt")


def denied_run():
    log = Log("A repository outside the token's scope. github-verify-connection, attempt github-attempt-003")
    fake = FakeGitHub()
    log.out("Known to this script from the made-up GitHub: %s exists, is private, holds %d issues, and was NOT granted to the"
            % (PAYROLL, fake.repos[PAYROLL]["issues"]))
    log.out("made-up fine-grained token. %s was granted, and is truly empty: no issues, no pull requests, no files." % EMPTY)

    log.part("PART 1. Three expected repositories: one with issues, one truly empty, one outside the token (criterion 4)")
    code, text = log.command("--source", "fake", "--expect", TRACKER, "--expect", EMPTY, "--expect", PAYROLL)
    empty, denied = row(text, EMPTY + ":"), row(text, PAYROLL + ":")
    log.check("exit code 3: an expected repository cannot be read", code == 3)
    log.check("the repository outside the token is reported as INACCESSIBLE, with GitHub's status",
              "INACCESSIBLE (status 404). Nothing in it could be read. This is NOT an empty repository" in denied)
    log.check("it is not given a count of issues, of 0 or of anything else", "issues" not in denied and "(0)" not in denied)
    log.check("the truly empty repository is reported as REACHABLE, with issues (0)", "REACHABLE" in empty and "issues (0)" in empty)
    log.check("so inaccessible and empty are different words on different lines", "INACCESSIBLE" not in empty and "REACHABLE" not in denied)
    log.check("the run does not claim to know more than it does: 404 is also what a repository that does not exist gives",
              "the two cannot be told apart from here" in denied)
    log.check("after the refusal, no other read was tried on that repository", [r for r in requests_in(text) if PAYROLL in r] == ["GET /repos/%s" % PAYROLL])
    log.check("it is not in the list of reachable repositories either", not re.search(r"^github-verify:      %s," % re.escape(PAYROLL), text, re.M))
    log.check("the result names it", "RESULT: 1 expected repository CANNOT be read: %s" % PAYROLL in text)

    log.part("PART 2. A week later: the same token, after %s was taken out of it" % TRACKER)
    log.out("In part 1 this repository was REACHABLE with 12 issues. A sync that treated a refusal as \"nothing there\" would now")
    log.out("report 0 issues and carry on.")
    code, text = log.command("--source", "fake", "--fake-case", "lost-access", "--expect", TRACKER, "--expect", EMPTY)
    log.check("exit code 3: the check fails on the very next run", code == 3)
    log.check("the lost repository is INACCESSIBLE, not empty", "INACCESSIBLE (status 404)" in row(text, TRACKER + ":") and "issues (0)" not in row(text, TRACKER + ":"))
    log.check("the repository that is still granted is still REACHABLE", "REACHABLE" in row(text, EMPTY + ":"))
    log.check("GitHub's own list now has 2 repositories where it had 3", "LISTS FOR THIS CONNECTION: 2" in text)

    log.part("PART 3. The token keeps the repository and loses the permission to read issues")
    code, text = log.command("--source", "fake", "--fake-case", "issues-refused", "--expect", TRACKER)
    log.check("exit code 3", code == 3)
    log.check("the read of issues is reported as REFUSED (status 403), and the run says that is not the same as having no issues",
              "issues: REFUSED (status 403)" in text and "This is not the same as having no issues" in text and "issues (0)" not in text)

    log.part("PART 4. GitHub refuses the list of repositories itself")
    fake = FakeGitHub()
    fake.list_status = 403
    code, text = log.in_process("the verification, against a made-up GitHub that answers 403 for the list", fake, [TRACKER])
    log.check("the list is reported as not readable, and not as empty",
              "THE LIST COULD NOT BE READ (status 403). This is not the same as an empty list" in text and "its list is empty" not in text)

    log.part("PART 5. The expected repository was renamed")
    code, text = log.command("--source", "fake", "--fake-case", "renamed", "--expect", TRACKER)
    log.check("exit code 3, and the repository is reported as MOVED, not as empty and not as readable",
              code == 3 and "MOVED (status 301)" in row(text, TRACKER + ":") and "REACHABLE" not in row(text, TRACKER + ":"))
    return log.save("denied-run.txt")


def main():
    os.chdir(ROOT)
    ok = verify_run()
    ok = denied_run() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

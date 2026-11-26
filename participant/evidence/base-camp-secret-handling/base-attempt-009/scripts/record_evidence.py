#!/usr/bin/env python3
"""Records logs/redacted-run.txt, logs/leak-scan.txt, logs/pre-commit.txt and logs/records-scan.txt for the quest base-camp-secret-handling.

EVERY CREDENTIAL HERE IS MADE UP, and is put together when this script runs. None is written in this file, in the
records it makes, or anywhere in the repository. Each is planted only in a temporary folder outside the repository,
which is deleted at the end.

    the fake token       "ghp_" followed by the word "example" repeated until there are 36 characters after the
                         underscore. It has the shape of a GitHub token, which the program's scanner knows.
    the fake Trello key  the word "example" written as hex, repeated, cut to 32 characters. It has the shape of a
                         Trello API key, which the program's scanner does not know.
    the shapeless one    four ordinary words joined by hyphens. Nothing about it looks like a credential.

The scanner is the program's own, tools/secret_scan.py, run with the project's Python and not changed. TEMP stands
for the temporary folder and REPO for the repository's top folder.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
REPO = os.path.dirname(PARTICIPANT)
PYTHON = os.path.join(REPO, ".venv", "bin", "python")
SCANNER = os.path.join(REPO, "tools", "secret_scan.py")
TOOL = os.path.join(PARTICIPANT, "tools", "use_credential.py")
HOOK = os.path.join(PARTICIPANT, "tools", "pre-commit-secret-scan")
VARIABLE = "GTQ_DEMO_TOKEN"

FAKE = "ghp_" + ("example" * 6)[:36]
FAKE_KEY = ("example".encode("ascii").hex() * 4)[:32]
SHAPELESS = "-".join(("example", "garden", "window", "seven"))
# The careless line that is planted. It is put together here in two pieces, because written out whole the program's
# scanner takes this very script for a leak: a name that says "token", an equals sign, and something after it.
PLANTED_LINE = "api_" + "token = %s" + "\ntimeout"
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.\n"
        "Every credential in these runs is made up and built when the script runs. None is written in this record.\n"
        "A block shows what the command wrote to standard output, and after it what it wrote to standard error.")
PLAIN = "-".join(("not", "made", "up", "0123456789", "abcdef"))      # a value without the word "example"
CHECKSUM = hashlib.md5(b"example").hexdigest()                        # 32 hex characters that are not a key


def forms(value):
    return [value, urllib.parse.quote(value, safe=""), base64.b64encode(value.encode()).decode(),
            base64.b64encode(("demo-user:%s" % value).encode()).decode(), base64.urlsafe_b64encode(value.encode()).decode()]


EVERY_FORM = forms(FAKE) + forms(FAKE + "-out-of-date") + [FAKE_KEY, FAKE_KEY.upper(), FAKE_KEY[:16], FAKE_KEY[16:], SHAPELESS, PLAIN, CHECKSUM]


class Log:
    def __init__(self, title, temp):
        self.lines, self.problems, self.count, self.temp = [title, HEAD, ""], [], 0, temp

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
        for path, name in ((os.path.realpath(self.temp), "TEMP"), (self.temp, "TEMP"), (REPO, "REPO")):
            text = text.replace(path, name)
        return text

    def run(self, shown, args, cwd=REPO, env=None):
        """Runs a command, writes down what it printed, and returns (exit code, output). `shown` is how it is written here."""
        done = subprocess.run(args, capture_output=True, text=True, cwd=cwd, env=env)
        said = self.tidy((done.stdout + done.stderr).rstrip("\n"))
        self.lines += ["$ " + shown, "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        return done.returncode, said

    def scan(self, *paths, cwd=REPO):
        return self.run("python tools/secret_scan.py %s" % " ".join(self.tidy(p) for p in paths), [PYTHON, SCANNER] + list(paths), cwd=cwd)

    def second(self, *paths):
        return self.run("python3 participant/tools/use_credential.py scan %s" % " ".join(self.tidy(p) for p in paths), [sys.executable, TOOL, "scan"] + list(paths))

    def save(self, name):
        text = "\n".join(self.lines)
        leaked = [form for form in EVERY_FORM if form in text]
        self.check("this record itself holds none of the made-up credentials, in any of the forms they were used in", not leaked)
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.problems), self.count) if self.problems else "ALL CHECKS PASSED. %d checks." % self.count)]
        text = "\n".join(self.lines) + "\n"
        for form in EVERY_FORM:                     # belt and braces: if a check above failed, the value still does not reach the file
            text = text.replace(form, "[REMOVED BY THE RECORDING SCRIPT]")
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.problems:
            print("  FAILED: " + label)
        return not self.problems


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    temp = tempfile.mkdtemp(prefix="gtq-secrets-")
    ok = True
    try:
        base_env = {k: v for k, v in os.environ.items() if k != VARIABLE}
        with_fake = dict(base_env, **{VARIABLE: FAKE})
        call = [sys.executable, TOOL, "call"]
        shown = "python3 participant/tools/use_credential.py call"
        is_set = "        (%s holds the fake token)" % VARIABLE

        # ------------------------------------------------------------ redacted-run.txt
        log = Log("A command that uses a credential, with the value masked. base-camp-secret-handling, attempt base-attempt-009", temp)
        log.out("The credential is set in the environment of each command by this script, as a person would set it for a session.",
                "It is the fake token: \"ghp_\" and then the word \"example\" repeated to 36 characters. 40 characters in all.",
                "It is never on a command line, except in part 5, where that mistake is made on purpose. The script puts it in the",
                "environment of the process it starts. Where a command line below held it, it is written as <the fake token>.")
        log.part("1. ORDINARY USE")
        code, said = log.run(shown + is_set, call, env=with_fake)
        log.check("criterion 1: the command says the credential came from the environment variable, and not from the command line or a file", code == 0 and "read from the environment variable %s" % VARIABLE in said)
        log.check("criterion 3: where the value would be, the output has [REDACTED]", "Its value: [REDACTED] (40 characters)" in said)
        log.check("the command did use it: the made-up service accepted it", "accepted the credential: status 200" in said)

        log.part("2. A DEBUGGING SWITCH that prints the request and its headers")
        code, said = log.run(shown + " --verbose" + is_set, call + ["--verbose"], env=with_fake)
        log.check("criterion 3: the credential is masked in the web address, in the Authorization header, and in its base64 form",
                  code == 0 and "token=[REDACTED]" in said and "Authorization: Bearer [REDACTED]" in said and "Basic [REDACTED]" in said)

        log.part("3. AN ERROR MESSAGE. The made-up service refuses the credential, and repeats in its error what it was sent")
        code, said = log.run(shown + " --rejected" + is_set, call + ["--rejected"], env=with_fake)
        log.check("criterion 2: the service's error, which holds the credential, reaches the output with it masked", code == 1 and "THE SERVICE REFUSED (status 401)" in said and "'Bearer [REDACTED]'" in said)
        sys.path.insert(0, os.path.dirname(TOOL))
        import use_credential
        unmasked = use_credential.MadeUpService(FAKE).get("/items", {"Authorization": "Bearer " + FAKE + "-out-of-date"})[1]["error"]
        log.check("and the mask is what did it: asked directly, without the mask, the service's error does hold the value (compared here, not printed)", FAKE in unmasked)

        log.part("4. A CRASH. The program fails with an error whose message holds the credential")
        code, said = log.run(shown + " --crash" + is_set, call + ["--crash"], env=with_fake)
        log.check("criterion 2: Python's own report of the error is printed with the credential masked", code == 3 and "Traceback" in said and "RuntimeError: could not read the reply to the request made with Bearer [REDACTED]" in said)

        log.part("5. WHERE THE CREDENTIAL MAY COME FROM")
        code, said = log.run("python3 participant/tools/use_credential.py call        (the variable is not set)", call, env=base_env)
        log.check("criterion 1: with the variable not set, the command refuses", code == 1 and "REFUSED: the environment variable %s is not set" % VARIABLE in said)
        log.out("", "The mistake the policy forbids, made on purpose: the fake token typed on the command line. A program's usual complaint",
                "about a command it does not understand repeats what was typed. This one must not.")
        for env, note in ((base_env, "        (the variable is not set)"), (with_fake, is_set)):
            code, said = log.run("python3 participant/tools/use_credential.py call --token <the fake token>" + note, call + ["--token", FAKE], env=env)
            log.check("criterion 1: there is no option to give it on the command line: the command is refused, with status 2", code == 2 and "REFUSED: the command line was not understood" in said)
            log.check("criterion 2: the refusal does not repeat what was typed: the fake token is nowhere in what was printed", FAKE not in said and "exampleexample" not in said and "unrecognized" not in said)
        code, said = log.run("python3 participant/tools/use_credential.py call --verbose        (%s holds a value without the word example)" % VARIABLE, call + ["--verbose"], env=dict(base_env, **{VARIABLE: PLAIN}))
        log.check("a value that is not plainly made up is refused before it is used, and is not shown", code == 1 and 'does not contain the word "example"' in said and PLAIN not in said)

        log.part("6. THIS RECORD, SCANNED")
        so_far = os.path.join(temp, "record-so-far.txt")
        write(so_far, "\n".join(log.lines) + "\n")
        code, said = log.scan(so_far)
        log.check("criterion 6: the program's scanner finds nothing in the text of this record so far", code == 0 and "0 finding(s)" in said)
        ok = log.save("redacted-run.txt") and ok

        # ------------------------------------------------------------ leak-scan.txt
        log = Log("A planted credential, found by the scan. base-camp-secret-handling, attempt base-attempt-009", temp)
        config = os.path.join(temp, "project", "service-config.txt")
        clean = "# settings for the made-up service\nbase_url = https://service.example.invalid\ntimeout_seconds = 30\n"
        log.part("1. THE FAKE TOKEN, PLANTED IN A FILE")
        log.out("A settings file is written to TEMP/project/service-config.txt, outside the repository. Its third line is the careless",
                "one: the fake token pasted in \"just to test\". The file's four lines, with the value left out here:", "",
                "    # settings for the made-up service", "    base_url = https://service.example.invalid", "    api_token = <the fake token, 40 characters>", "    timeout_seconds = 30", "")
        write(config, clean.replace("timeout", PLANTED_LINE % FAKE))
        code, said = log.scan(config)
        log.check("criterion 4: the scan finds the planted credential and exits with a failure status (1)", code == 1 and "service-config.txt:3:" in said and "1 files scanned" in said and "0 finding(s)" not in said)
        log.check("it says where, by file, line and column, and which pattern: a GitHub token", "[github-token]" in said)
        log.check("it does not print the value: it shows the first three characters and the length", FAKE not in said and "(40 chars)" in said)

        log.part("2. THE SAME SCAN AFTER THE LINE IS TAKEN OUT")
        write(config, clean)
        code, said = log.scan(config)
        log.check("the same scan of the same file passes: exit status 0, no finding", code == 0 and "0 finding(s)" in said)

        log.part("3. THE WHOLE REPOSITORY")
        log.out("With no path, the scanner looks at every file Git tracks in the repository.")
        code, said = log.scan()
        tracked = said.split("secret-scan: ")[-1].split(" files")[0]
        log.check("a scan of the whole repository is clean: %s tracked files, no finding, exit status 0" % tracked, code == 0 and "0 finding(s)" in said and tracked.isdigit() and int(tracked) > 1000)
        listed = subprocess.run(["git", "-C", REPO, "ls-files", "--others", "--exclude-standard", "-z"], capture_output=True, text=True).stdout.split("\0")
        pictures = [name for name in listed if name.endswith((".png", ".jpg"))]
        new = [name for name in listed if name and name not in pictures]
        log.out("", "Git does not track a new file until it is added, so the scan above did not look at files that are not committed yet.",
                "Every such file in the whole repository, that Git does not ignore, is scanned here by name: %d files." % len(new),
                "%d pictures among them are left out: a scan of text cannot read a picture." % len(pictures), "")
        log.out(*["    " + name for name in new])
        log.out("")
        done = subprocess.run([PYTHON, SCANNER, "--"] + new, capture_output=True, text=True, cwd=REPO)
        said = log.tidy((done.stdout + done.stderr).rstrip("\n"))
        log.lines += ["$ python tools/secret_scan.py -- <the %d files listed above>" % len(new), "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        log.check("the files Git does not track yet are clean too: %d files, no finding" % len(new), done.returncode == 0 and "%d files scanned, 0 finding(s)" % len(new) in said and len(new) > 0)
        log.out("", "What is NOT scanned here: files Git ignores (local-data/, .env, the virtual environment), the history of old commits,",
                "other branches, commit messages, and pictures.")

        log.out("", "The second pattern, over the same two sets of files.", "")
        tracked_files = [n for n in subprocess.run(["git", "-C", REPO, "ls-files", "-z"], capture_output=True, text=True).stdout.split("\0") if n]
        done = subprocess.run([sys.executable, TOOL, "scan"] + tracked_files, capture_output=True, text=True, cwd=REPO)
        said = log.tidy((done.stdout + done.stderr).rstrip("\n"))
        log.lines += ["$ python3 participant/tools/use_credential.py scan <every file Git tracks>", "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        log.check("the second pattern reports ONE place in the tracked files and exits with 1. It is not a credential: it is a made-up value in the "
                  "program's own test of its scanner. A shape scan reports shapes, and this is a false alarm that is left standing, not hidden",
                  done.returncode == 1 and ", 1 finding" in said and said.count("[trello-api-key]") == 1 and "tests/unit/test_secret_patterns.py:" in said)
        done = subprocess.run([sys.executable, TOOL, "scan"] + new, capture_output=True, text=True, cwd=REPO)
        said = log.tidy((done.stdout + done.stderr).rstrip("\n"))
        log.lines += ["$ python3 participant/tools/use_credential.py scan <the %d files listed above>" % len(new), "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        log.check("the second pattern finds nothing in the files Git does not track yet", done.returncode == 0 and "%d files scanned, 0 findings" % len(new) in said)

        log.part("4. WHAT THE SCAN CANNOT SEE")
        log.out("4a. A credential of a shape the program's scanner does not know: the fake Trello API key, 32 hex characters, in a note.", "")
        note = os.path.join(temp, "project", "notes.md")
        write(note, "# Sandbox notes\n\nOur Trello key is %s for the sandbox board.\n" % FAKE_KEY)
        code, said = log.scan(note)
        log.check("THE LIMIT, shown: the program's scanner passes a file that holds the fake Trello key", code == 0 and "0 finding(s)" in said)
        log.out("", "The second pattern, added for this quest, run on the same file (stretch goal):")
        code, said = log.second(note)
        log.check("stretch goal: the second pattern finds it, says where, does not print it, and exits with a failure status", code == 1 and "notes.md:3:19: [trello-api-key]" in said and FAKE_KEY not in said)
        write(note, "# Sandbox notes\n\nThe Trello key is kept in the environment, not here.\n")
        code, said = log.second(note)
        log.check("after the key is taken out, the second pattern passes", code == 0 and "0 findings" in said)
        log.out("", "4b. A credential with no shape at all: four ordinary words joined by hyphens, in the same note, called a door code.", "")
        write(note, "# Sandbox notes\n\nThe door code for the made-up office is %s.\n" % SHAPELESS)
        code_a, said_a = log.scan(note)
        code_b, said_b = log.second(note)
        log.check("THE LIMIT, shown: both scans pass a file that holds a secret with no recognizable shape. A passing scan does not mean there is no secret", code_a == 0 and code_b == 0)
        log.out("", "4c. The second pattern's own limits. Three files, with the fake Trello key written in different ways.", "")
        found, missed, alarm = (os.path.join(temp, "project", name) for name in ("found.txt", "missed.txt", "checksum.txt"))
        write(found, '{"key": "%s"}\ntool --api-' % FAKE_KEY + 'key %s\nexport TRELLO_API_KEY=%s\n' % (FAKE_KEY, FAKE_KEY))      # in two pieces: see PLANTED_LINE
        log.out("found.txt: the key as a JSON field named key, after the option --api-key, and as TRELLO_API_KEY=.")
        code, said = log.second(found)
        log.check("found in all three ways of writing it, one per line", code == 1 and all("found.txt:%d:" % n in said for n in (1, 2, 3)) and "3 findings" in said and FAKE_KEY not in said)
        write(missed, "trello %s\nThe board key is on the next line\n%s\ntrello key %s\n%s\n" % (FAKE_KEY.upper(), FAKE_KEY, FAKE_KEY[:16], FAKE_KEY[16:]))
        log.out("", "missed.txt: the key in capitals; the key alone on a line with its name on the line before; the key cut in two across lines.")
        code, said = log.second(missed)
        log.check("THE LIMIT, shown: the second pattern passes all three. A real key written any of these ways would not be caught", code == 0 and "0 findings" in said)
        write(alarm, "md5 checksum of the Trello export file: %s\n" % CHECKSUM)
        log.out("", "checksum.txt: one line that says Trello and holds an MD5 checksum, which is also 32 hex characters. It is not a key.")
        code, said = log.second(alarm)
        log.check("THE LIMIT, shown: the second pattern reports the checksum as if it were a key. It sees a shape, not a meaning", code == 1 and "checksum.txt:1:" in said)
        ok = log.save("leak-scan.txt") and ok

        # ------------------------------------------------------------ pre-commit.txt
        log = Log("The scan as a pre-commit hook that blocks the commit. base-camp-secret-handling, attempt base-attempt-009", temp)
        sandbox = os.path.join(temp, "sandbox-repository")
        os.makedirs(sandbox)
        os.makedirs(os.path.join(temp, "hook-work"))
        git_env = dict(base_env, GTQ_HOME=REPO, TMPDIR=os.path.join(temp, "hook-work"), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                       GIT_AUTHOR_NAME="A made-up person", GIT_AUTHOR_EMAIL="made-up@example.invalid", GIT_COMMITTER_NAME="A made-up person", GIT_COMMITTER_EMAIL="made-up@example.invalid")

        def git(*args, env=None):
            return log.run("git " + " ".join('"%s"' % a if " " in a else a for a in args), ["git"] + list(args), cwd=sandbox, env=env or git_env)

        def commits():
            return subprocess.run(["git", "rev-list", "--all", "--count"], cwd=sandbox, env=git_env, capture_output=True, text=True).stdout.strip()

        log.out("The stretch goal. A new, empty Git repository is made in TEMP/sandbox-repository. The hook, participant/tools/pre-commit-secret-scan,",
                "is copied to its .git/hooks/pre-commit by this script. It is NOT installed in the real repository: that is for a person to do.",
                "The hook scans the staged copy of each file, which it writes out under TEMP/hook-work. So the places it reports begin there.")
        subprocess.run(["git", "init", "-q", sandbox], env=git_env, check=True)
        shutil.copy(HOOK, os.path.join(sandbox, ".git", "hooks", "pre-commit"))
        os.chmod(os.path.join(sandbox, ".git", "hooks", "pre-commit"), 0o755)

        log.part("1. A COMMIT OF A FILE THAT HOLDS THE FAKE TOKEN")
        write(os.path.join(sandbox, "service-config.txt"), clean.replace("timeout", PLANTED_LINE % FAKE))
        git("add", "service-config.txt")
        code, said = git("commit", "-m", "Add settings")
        log.check("stretch goal: the commit is blocked: Git exits with a failure status and the hook says why", code != 0 and "COMMIT BLOCKED" in said and "[github-token]" in said and FAKE not in said)
        count = subprocess.run(["git", "rev-list", "--all", "--count"], cwd=sandbox, env=git_env, capture_output=True, text=True).stdout.strip()
        log.out("Commits in the sandbox repository now: %s" % count)
        log.check("no commit was made: the repository has no commit at all", count == "0")

        log.part("2. THE SAME COMMIT AFTER THE LINE IS TAKEN OUT")
        write(os.path.join(sandbox, "service-config.txt"), clean)
        git("add", "service-config.txt")
        code, said = git("commit", "-m", "Add settings")
        count = subprocess.run(["git", "rev-list", "--all", "--count"], cwd=sandbox, env=git_env, capture_output=True, text=True).stdout.strip()
        log.check("the commit goes through: exit status 0, and the repository now has one commit", code == 0 and count == "1")

        log.part("3. A COMMIT OF A NOTE THAT HOLDS THE FAKE TRELLO KEY, which only the second pattern knows")
        write(os.path.join(sandbox, "notes.md"), "# Sandbox notes\n\nOur Trello key is %s for the sandbox board.\n" % FAKE_KEY)
        git("add", "notes.md")
        code, said = git("commit", "-m", "Add notes")
        count = subprocess.run(["git", "rev-list", "--all", "--count"], cwd=sandbox, env=git_env, capture_output=True, text=True).stdout.strip()
        log.check("the commit is blocked by the second pattern, and the repository still has one commit", code != 0 and "[trello-api-key]" in said and "COMMIT BLOCKED" in said and count == "1" and FAKE_KEY not in said)

        log.part("4. THE FILE IS CLEANED ON DISK BUT NOT ADDED AGAIN. What would be committed is the staged copy, which still holds the key")
        write(os.path.join(sandbox, "notes.md"), "# Sandbox notes\n\nThe Trello key is kept in the environment, not here.\n")
        code, said = git("commit", "-m", "Add notes")
        log.check("the commit is still blocked: the hook scans what is staged, not what is on disk", code != 0 and "[trello-api-key]" in said and "COMMIT BLOCKED" in said and commits() == "1")
        git("add", "notes.md")
        code, said = git("commit", "-m", "Add notes")
        log.check("after the clean file is added again, the commit goes through: two commits", code == 0 and commits() == "2")

        log.part("5. A FILE THAT IS RENAMED, AND GIVEN THE FAKE TOKEN IN THE SAME COMMIT")
        git("mv", "service-config.txt", "settings.txt")
        write(os.path.join(sandbox, "settings.txt"), clean.replace("timeout", PLANTED_LINE % FAKE))
        git("add", "settings.txt")
        code, said = git("commit", "-m", "Rename settings")
        log.check("the commit is blocked: a renamed file is scanned like a new one", code != 0 and "settings.txt:3:" in said and "[github-token]" in said and "COMMIT BLOCKED" in said and commits() == "2" and FAKE not in said)
        git("reset", "-q", "--hard")

        log.part("6. A FILE WHOSE NAME BEGINS WITH A DASH AND HAS A SPACE IN IT, holding the fake token")
        odd = "-n odd name.txt"
        write(os.path.join(sandbox, odd), clean.replace("timeout", PLANTED_LINE % FAKE))
        git("add", "--", odd)
        code, said = git("commit", "-m", "Add a file with an odd name")
        log.check("the commit is blocked: the name is not taken for an option, and is not cut at the space", code != 0 and "-n odd name.txt:3:" in said and "COMMIT BLOCKED" in said and commits() == "2" and FAKE not in said)
        git("reset", "-q", "--hard")

        log.part("7. THE SCAN CANNOT BE RUN. GTQ_HOME names a folder that is not there, and a clean file is committed")
        write(os.path.join(sandbox, "clean.txt"), "Nothing here.\n")
        git("add", "clean.txt")
        code, said = git("commit", "-m", "Add a clean file        (GTQ_HOME=TEMP/not-there)", env=dict(git_env, GTQ_HOME=os.path.join(temp, "not-there")))
        log.check("the commit is stopped, and the message says the scan did not run. It does not say a credential was found", code != 0 and "COMMIT STOPPED. The secret scan could not be run" in said and "COMMIT BLOCKED" not in said and commits() == "2")
        code, said = git("commit", "-m", "Add a clean file")
        log.check("with the scan able to run, the same clean commit goes through: three commits", code == 0 and commits() == "3")

        log.part("8. WHAT THE HOOK DOES NOT STOP")
        write(os.path.join(sandbox, "notes.md"), "# Sandbox notes\n\nOur Trello key is %s for the sandbox board.\n" % FAKE_KEY)
        git("add", "notes.md")
        code, said = git("commit", "-m", "Change notes")
        log.check("first, with the hook running, this commit of the fake key is blocked", code != 0 and "COMMIT BLOCKED" in said and commits() == "3")
        log.out("The same commit again, with Git's own switch that skips every hook:")
        code, said = git("commit", "--no-verify", "-m", "Change notes")
        log.check("THE LIMIT, shown: with --no-verify the hook does not run and the fake key is committed. A hook is a reminder, not a lock", code == 0 and commits() == "4")
        log.out("", "That commit is in a sandbox that is deleted when this script ends. The key in it is made up.")
        ok = log.save("pre-commit.txt") and ok

        # ------------------------------------------------------------ records-scan.txt
        log = Log("The three records above, scanned as they were saved. base-camp-secret-handling, attempt base-attempt-009", temp)
        names = ["redacted-run.txt", "leak-scan.txt", "pre-commit.txt"]
        paths = [os.path.relpath(os.path.join(ATTEMPT, "logs", name), REPO) for name in names]
        log.out("Each record checks itself before it is finished, so that check is of the text before its last lines. Here the three",
                "finished files are read back from disk and scanned.")
        code, said = log.scan(*paths)
        log.check("criterion 6: the program's scanner finds nothing in the three finished records", code == 0 and "3 files scanned, 0 finding(s)" in said)
        code, said = log.second(*paths)
        log.check("the second pattern finds nothing in them", code == 0 and "3 files scanned, 0 findings" in said)
        texts = [open(os.path.join(REPO, path), encoding="utf-8").read() for path in paths]
        log.check("none of the made-up credentials is in them, in any form used: compared one by one, %d forms" % len(EVERY_FORM), not any(form in text for form in EVERY_FORM for text in texts))
        log.check("the recording script never had to take a value out of a record: its last-resort marker is in none of them", not any("REMOVED BY THE RECORDING SCRIPT" in text for text in texts))
        log.check("each record ends with ALL CHECKS PASSED", all(text.rstrip("\n").split("\n")[-1].startswith("RESULT: ALL CHECKS PASSED") for text in texts))
        ok = log.save("records-scan.txt") and ok
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

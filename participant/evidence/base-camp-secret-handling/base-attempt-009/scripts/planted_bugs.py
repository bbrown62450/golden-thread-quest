#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/tools/use_credential.py and runs its tests against the copy.
Records logs/planted-bugs.txt. A test suite that still passes with a bug planted is not testing that behaviour.

The real tool is never changed: the tool and its tests are copied to a temporary folder outside the repository, and
each bug is planted in the copy. Each run of the tests is stopped after two minutes. At the end the script asks Git
whether anything in the repository changed while it ran.

No credential is written here. The tests build their made-up values when they run.

Run from anywhere:  python3 scripts/planted_bugs.py        Exit code 0 if every bug was caught, 1 if not.
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
    ("the mask does nothing", "        text = text.replace(secret, MARKER)\n", "        pass\n"),
    ("the value is not written down before the command line is read", "    value = load_credential()              #", "    value = os.environ.get(VARIABLE)       #"),
    ("the main parser is Python's ordinary one, which repeats what was typed", "parser = QuietParser(description", "parser = argparse.ArgumentParser(description"),
    ("the parsers of `call` and `scan` are Python's ordinary ones", "parser_class=QuietParser", "parser_class=argparse.ArgumentParser"),
    ("the base64 form after the account name is not masked", 'base64.b64encode(raw).decode("ascii"), base64.b64encode(paired).decode("ascii"),', 'base64.b64encode(raw).decode("ascii"),'),
    ("the base64 form of the value alone is not masked", 'base64.b64encode(raw).decode("ascii"), base64.b64encode(paired).decode("ascii"),', 'base64.b64encode(paired).decode("ascii"),'),
    ("the URL-encoded forms are not masked", 'encodings = [value, urllib.parse.quote_from_bytes(raw, safe=""), urllib.parse.quote_from_bytes(raw, safe="/"), urllib.parse.quote_plus(raw),', "encodings = [value, value, value, value,"),
    ("percent-escapes in small letters are not masked", "    encodings += [e.lower() for e in encodings[1:4]]", "    pass"),
    ("a value that is not proper text cannot be written down", 'raw = value.encode("utf-8", "surrogateescape")', 'raw = value.encode("utf-8")'),
    ("a value without the word example is accepted", '    if "example" not in value.lower():', "    if False:"),
    ("a short value is accepted", "    if len(value) < SHORTEST or any(ch.isspace() for ch in value):", "    if any(ch.isspace() for ch in value):"),
    ("a variable that is not set is not refused", "    if not value:\n", "    if False:\n"),
    ("a failure is reported without the mask", '        say("  " + line, sys.stderr)', '        sys.stderr.write("  " + line + "\\n")'),
    ("a failure escapes main() to whoever called it", "    except BaseException:", "    except ZeroDivisionError:"),
    ("what is sent is not written down when it differs from the value", "    remember(sending)  ", "    pass  "),
    ("the made-up service accepts anything", '        if sent != "Bearer " + self.good:', "        if False:"),
    ("the service's refusal is printed without the mask", '''        say("THE SERVICE REFUSED (status %d). Its own words, which repeat what it was sent: %s" % (status, body.get("error")), sys.stderr)''',
     '''        sys.stderr.write("THE SERVICE REFUSED (status %d). Its own words, which repeat what it was sent: %s\\n" % (status, body.get("error")))'''),
    ("scan: a longer run of hex is taken for a key", "([0-9a-f]{32})", "([0-9a-f]{32,})"),
    ("scan: any 32 hex characters are reported, whatever the line says", '        if "trello" not in line.lower() and not KEY_NAMED.search(line):', "        if False:"),
    ("scan: a line that only names a key is not looked at", '        if "trello" not in line.lower() and not KEY_NAMED.search(line):', '        if "trello" not in line.lower():'),
    ("scan: the option --key is not known as naming a key", r'''|--(?:[a-z0-9-]*-)?key\b)""")''', ''')""")'''),
    ("scan: a finding does not make the scan fail", "    return 1 if findings or unread else 0", "    return 1 if unread else 0"),
    ("scan: a path that cannot be read is passed as clean", "    return 1 if findings or unread else 0", "    return 1 if findings else 0"),
    ("scan: a scan that looked at no file passes", '''That is not a pass.")\n        return 1''', '''That is not a pass.")\n        return 0'''),
    ("scan: a folder is not looked into", "    if not os.path.isdir(path):", "    if True:"),
    ("scan: a file that is not text is scanned and counted", '            if b"\\x00" in raw[:4096]:', "            if False:"),
    ("scan: the finding prints the line it found", '''32 hex characters (not shown)" % (path, line, column))''', '''32 hex characters (not shown)" % (path, line, column) + raw.decode("utf-8", "replace"))'''),
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-m", "unittest", "tests.test_use_credential"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = [line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))]
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(sorted(set(failed))[:3]) + (" ..." if len(set(failed)) > 3 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(TOOLS, "use_credential.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/tools/use_credential.py. base-camp-secret-handling, attempt base-attempt-009",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the",
             "tool's tests are run against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        os.makedirs(os.path.join(temp, "tests"))
        shutil.copy(os.path.join(TOOLS, "tests", "test_use_credential.py"), os.path.join(temp, "tests"))
        copy = os.path.join(temp, "use_credential.py")
        shutil.copy(os.path.join(TOOLS, "use_credential.py"), copy)
        passed, said = run_tests(temp)
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
                passed, said = run_tests(temp)
                lines.append("%2d. %-7s %s" % (number, "MISSED" if passed else "CAUGHT", what))
                lines.append("            %s" % said)
                if passed:
                    missed.append(what)
            with open(copy, "w", encoding="utf-8") as f:
                f.write(source)
            passed, said = run_tests(temp)
            lines += ["", "Last, with the copy put back as it was: %s" % said]
            if not passed:
                problems.append("the tests fail after the copy was put back")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    with open(os.path.join(TOOLS, "use_credential.py"), encoding="utf-8") as f:
        same = f.read() == source
    lines.append("The real tool is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    unchanged = git_state() == before
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    lines += ["", "NOT COVERED: the commit hook, participant/tools/pre-commit-secret-scan, has no planted bugs. It is exercised by",
              "logs/pre-commit.txt only. One behaviour of the tool has no planted bug because no test can tell: a short value is kept",
              "out of the mask AND its refusal is printed without the mask, so either one alone gives the same output."]
    caught = len(BUGS) - len(missed)
    result = "RESULT: %d OF %d PLANTED BUGS CAUGHT." % (caught, len(BUGS)) + ("" if not missed and not problems else " NOT ALL: " + "; ".join(missed + problems))
    lines += ["", result]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(result)
    for line in lines:
        if "MISSED" in line or "NOT PLANTED" in line:
            print(line)
    return 0 if not missed and not problems else 1


if __name__ == "__main__":
    sys.exit(main())

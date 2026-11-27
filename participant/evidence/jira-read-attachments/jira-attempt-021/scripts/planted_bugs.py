#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-read-attachments/attachments.py and runs the tests against
the copy. Records logs/planted-bugs.txt. The real tool is never changed: the copy is in a temporary folder.

A bug that is CAUGHT made at least one test fail. A bug that is MISSED left every test passing: the tests would not
notice that mistake. Some mistakes are deliberately not planted, because a second check in the tool catches what the
first lets through, so no test can tell them apart from the outside. They are listed at the end of the record.

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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-read-attachments")
CONFIG = os.path.join(PARTICIPANT, "context", "jira", "attachments.md")
LIMIT = 120

BUGS = [
    # a sync downloads nothing
    ("a sync fetches a file: the quest's scenario", "    me = read_me(conn)\n    story, listed = read_story(conn, args.issue)", "    me = read_me(conn)\n    story, listed = read_story(conn, args.issue)\n    conn.content(\"41001\")"),
    ("a sync asks for one attachment's details", "    me = read_me(conn)\n    story, listed = read_story(conn, args.issue)", "    me = read_me(conn)\n    story, listed = read_story(conn, args.issue)\n    conn.get(\"/rest/api/3/attachment/41001\")"),
    ("a story with no list of attachments is recorded as having none", "    if not isinstance(listed, list):", "    if not isinstance(listed, list):\n        listed = []\n    if False:"),
    ("an attachment listed twice is accepted", "    if len(set(numbers)) != len(numbers):", "    if False:"),
    ("me and someone else are the wrong way round", "\"me\" if author == me else \"someone else\"", "\"me\" if author != me else \"someone else\""),
    ("an author Jira does not name is called someone else", "\"attached_by\": \"unknown\" if not (isinstance(author, str) and author) else ", "\"attached_by\": "),
    ("a sync prints the names of the attachments", "        say(\"    %s  %-12s %-22s %-13s %s\" % (a[\"id\"],", "        say(\"    %s  %-12s %-22s %-13s %s\" % (a[\"name\"],"),
    ("Jira's times are labelled UTC without being turned into UTC", "datetime.datetime.strptime(value, shape).astimezone(datetime.timezone.utc).strftime(", "datetime.datetime.strptime(value, shape).strftime("),
    ("a size Jira does not state is recorded as stated", "\"stated_size\": size if type(size) is int and size >= 0 else None,", "\"stated_size\": size if type(size) is int and size >= 0 else 0,"),
    ("characters that cannot be seen are kept in a name", "    return UNSEEN.sub(\"?\", text)[:limit] if isinstance(text, str) else None", "    return text[:limit] if isinstance(text, str) else None"),
    ("a name can break out of its place on the page", "        name = \"`%s`\" % a[\"name\"].replace(\"`\", \"'\").replace(\"|\", \"¦\")", "        name = \"`%s`\" % a[\"name\"]"),
    ("the files are written even when nothing changed", "        if before[0] != hashlib.sha256(index_text.encode(\"utf-8\")).hexdigest():", "        if True:"),
    # an explicit request
    ("an identifier that is not one of the story's is asked for anyway", "        if args.id not in [raw.get(\"id\") for raw in listed if isinstance(raw, dict)]:", "        if False:"),
    ("the attachment described is not checked to be the one asked for", "raw.get(\"id\") != args.id or ", ""),
    # the name
    ("a name with a slash in it passes the name check", "    if \"/\" in name or \"\\\\\" in name:", "    if False:"),
    ("a name with `..` in it passes", "    if \"..\" in name:", "    if False:"),
    ("a name with a character that cannot be seen passes", "    if UNSEEN.search(name):", "    if False:"),
    ("a name that ends in a space or a dot passes", "    if name != name.strip() or name.endswith(\".\"):", "    if False:"),
    ("the file is saved under the name Jira gave it", "        target = os.path.join(downloads, saved_name(args.id, name, extension))", "        target = os.path.join(downloads, name)"),
    ("the saved name does not carry the identifier, so two attachments of one name share a file", "    return \"%s-%s.%s\" % (number, slug or \"attachment\", ", "    return \"%s%s.%s\" % (\"\", slug or \"attachment\", "),
    ("the letters taken from Jira's name are not cleaned", "re.sub(r\"[^a-z0-9]+\", \"-\", stem)", "stem"),
    # the type
    ("the FIRST extension of the name is taken, so invoice.pdf.exe is a PDF", "    extension = name.rsplit(\".\", 1)[1]", "    extension = name.split(\".\")[1]"),
    ("the type Jira states is not compared with the extension", "    if stated not in ALLOWED[extension][0]:", "    if False:"),
    ("an archive is on the allowed list", "    \"txt\": ((\"text/plain\",), \"text\"),", "    \"txt\": ((\"text/plain\",), \"text\"),\n    \"zip\": ((\"application/zip\",), b\"PK\"),"),
    # the size
    ("the size Jira states is not compared with the limit before the file is asked for", "    if stated_size > SIZE_LIMIT:", "    if False:"),
    ("the bytes are not counted as they arrive, so a file is read to its end however large", "            if count > SIZE_LIMIT or count > stated_size:", "            if False:"),
    ("a file of another size than Jira stated is accepted", "        if len(data) != stated_size:", "        if False:"),
    ("a size that is not a whole number is accepted", "    if type(stated_size) is not int or stated_size < 0:", "    if stated_size is None:"),
    # what the bytes are
    ("the bytes are not looked at", "        check_bytes(extension, data)", "        pass"),
    ("a picture or PDF need not begin as one does", "        if not data.startswith(how):", "        if False:"),
    ("text may have a zero byte in it", "    if b\"\\x00\" in data:", "    if False:"),
    ("text may begin the way an archive or a program begins", "        if data.startswith(start):\n            raise Check(\"what the bytes are\", \"the file is named as text and begins", "        if False:\n            raise Check(\"what the bytes are\", \"the file is named as text and begins"),
    ("a file named .json need not be JSON", "            json.loads(text)", "            pass"),
    # the scan
    ("the scan is not run", "        scan(extension, data)", "        pass"),
    ("the scan misses the antivirus test string", "    if TEST_STRING_HALVES[0] + TEST_STRING_HALVES[1] in data:", "    if False:"),
    ("the scan misses everything in a PDF", "            if re.search(re.escape(mark) + rb\"(?![A-Za-z])\", undone):", "            if False:"),
    ("the scan takes any word that starts like a PDF's marks for one", "            if re.search(re.escape(mark) + rb\"(?![A-Za-z])\", undone):", "            if re.search(re.escape(mark), undone):"),
    ("the scan misses a private key", "    if re.search(rb\"-----BEGIN [A-Z ]*PRIVATE KEY( BLOCK)?-----|PuTTY-User-Key-File\", data):", "    if False:"),
    ("the scan misses a script's first line", "        if text.lstrip(\"\\ufeff \\t\\r\\n\").startswith(\"#!\"):", "        if False:"),
    ("the scan misses a script tag", "        if re.search(r\"<\\s*script\\b\", text, re.I):", "        if False:"),
    ("the scan misses a formula in a CSV", "                if bare[:1] in (", "                if False and bare[:1] in ("),
    ("the scan misses a program inside a file", "    if b\"This program cannot be run in DOS mode\" in data or b\"\\x7fELF\" in data:", "    if False:"),
    ("the scan misses an archive inside a file", "    if b\"PK\\x03\\x04\" in data:", "    if False:"),
    # where it is saved
    ("a downloads folder Git would commit from is accepted", "    if asked.returncode != 0:", "    if False:"),
    ("when Git cannot be asked, a folder inside a repository is accepted", "        raise Refused(\"--downloads is inside a Git repository, and Git could not be asked whether it ignores that folder\")", "        return \"it could not be checked\""),
    ("a saved file is marked as a program", "        os.chmod(temporary, 0o600 if private else 0o644)", "        os.chmod(temporary, 0o755)"),
    ("a save that fails leaves its temporary file", "        try:\n            os.unlink(temporary)\n        except OSError:", "        try:\n            pass\n        except OSError:"),
    ("a save that fails is not logged", "            raise Refused(\"every check passed and the file could not be written to the downloads folder\")", "            raise RuntimeError(\"x\")"),
    # the log
    ("no line is added to the log", "        written = log_line(log, entry)", "        written = \"(nothing)\""),
    ("the log has no time", "    entry = {\"time\": now_utc(),", "    entry = {\"time\": None,"),
    ("the log has no checksum", "sha256=hashlib.sha256(data).hexdigest())", "sha256=None)"),
    # a real Jira
    ("a download from a real Jira is not refused", "            if args.command == \"download\" and args.source == \"live\":", "            if False:"),
    ("a real connection will send a GET for an attachment or a file", "        if not (path == \"/rest/api/3/myself\" or re.fullmatch(r\"/rest/api/3/issue/[A-Za-z0-9_-]+\", path)):", "        if False:"),
    ("a live sync may write anywhere", "    if live and \"local-data\" not in folder.split(os.sep):", "    if False:"),
    ("the index is written before the search for credentials", "    if any(secret and secret in \"\\n\".join(LINES) + index_text + page_text for secret in secrets):", "    if False:"),
    ("any request is reported as a plain GET", "        return all(method.split(\" \")[0] == \"GET\" and \"BODY\" not in method for method, _ in self.sent)", "        return True"),
    ("the method reported is the word GET, not the request's own", "        return status, headers, parsed, request.get_method(), request.data is not None", "        return status, headers, parsed, \"GET\", False"),
    ("the made-up Jira's folder is accepted for a real Jira", "                if args.state:\n                    raise Refused(\"--state is for the made-up Jira only\")", "                if False:\n                    raise Refused(\"--state is for the made-up Jira only\")"),
    ("the output is not searched for the credentials", "    if any(secret and secret in text for secret in secrets):", "    if False:"),
    ("only the token is searched for", "    return Connection(get, host), [token, email, encoded]", "    return Connection(get, host), [token]"),
    ("the site's address is left in the saved output", "        kept = kept.replace(\"https://\" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept", "        kept = kept"),
    ("a real server's refusal is not read for its status", "            status, headers, raw = err.code, dict(err.headers), err.read()\n            err.close()", "            raise"),
    ("redirects are followed", "    opener = opener or urllib.request.build_opener(NoRedirect)", "    opener = opener or urllib.request.build_opener()"),
    ("an address with a path or a port, or without https, is accepted", "    if not host or base.lower() != \"https://\" + host:", "    if not host:"),
    ("a request may wait for ever", "            with opener.open(request, timeout=30) as response:", "            with opener.open(request) as response:"),
    # the files
    ("an index this tool did not write is used anyway", "    if not good_index(index):", "    if False:"),
    ("a page of the same name that is someone else's file is written over", "    if os.path.exists(page_path) and not os.path.exists(index_path):", "    if False:"),
    ("--log may be a place in the downloads folder", " or any(same_file(log_to, path) for path in own) or inside\n", " or any(same_file(log_to, path) for path in own)\n"),
    ("--log is written over a file that is not an output of the tool", "                        or (os.path.lexists(log_to) and not already.startswith(tuple(start.encode(\"utf-8\") for start in LOG_STARTS)))):", "                        ):"),
    ("something unforeseen is a crash", "    except Exception as surprise:           # anything unforeseen\n", "    except KeyboardInterrupt as surprise:\n"),
    # found by the independent readers, or shown by them to be mistakes the first tests would not notice
    ("a file that was saved stays when its line cannot be written to the log: found by both readers", "                os.unlink(target)", "                pass"),
    ("Git is asked about a made-up file name in the folder, not about the folder: a reader's find", "[\"git\", \"-C\", git_at, \"check-ignore\", \"-q\", \"--\", folder]", "[\"git\", \"-C\", git_at, \"check-ignore\", \"-q\", \"--\", os.path.join(folder, \"probe\")]"),
    ("Git's settings in the environment are left to change its answer", "capture_output=True, timeout=20, env=clean)", "capture_output=True, timeout=20)"),
    ("a repository of another kind is not looked for", "            if os.path.lexists(os.path.join(at, mark)):", "            if False:"),
    ("a file that appears under the saved name while the fetch runs is written over", "            os.link(temporary, path)\n            os.unlink(temporary)", "            os.replace(temporary, path)"),
    ("a PDF's hidden marks are not undone before they are looked for", "            if re.search(re.escape(mark) + rb\"(?![A-Za-z])\", undone):", "            if re.search(re.escape(mark) + rb\"(?![A-Za-z])\", data):"),
    ("the scan misses a frame or a javascript address", "        if re.search(r\"<\\s*iframe\\b|javascript\\s*:\", text, re.I):", "        if False:"),
    ("a name of any length is accepted", "    if len(name) > 255:", "    if False:"),
    ("a live index says an attachment could be asked for", " if live else\n                   \"could be asked for:", " if False else\n                   \"could be asked for:"),
    ("something unforeseen during a download leaves no line in the log", "    except Exception as surprise:           # anything unforeseen is still an attempt, and is still logged", "    except KeyboardInterrupt as surprise:"),
    ("a real connection is given a way to ask for a file", "    return Connection(get, host), [token, email, encoded]          # no", "    return Connection(get, host, lambda number: (200, iter(()))), [token, email, encoded]          # no"),
    ("the type Jira states must match to the letter, capitals and all", "    stated = stated_type.split(\";\")[0].strip().casefold() if isinstance(stated_type, str) else \"\"", "    stated = stated_type if isinstance(stated_type, str) else \"\""),
    ("a live sync asks Jira for every field of the story", "    status, body = conn.get(\"/rest/api/3/issue/%s\" % key, {\"fields\": \"attachment\"})", "    status, body = conn.get(\"/rest/api/3/issue/%s\" % key, {\"fields\": \"*all\"})"),
    ("the address Jira gives for a file's contents is kept in the index", "            \"attached\": created, \"if_asked_for\": verdict}", "            \"attached\": created, \"if_asked_for\": verdict + \" \" + str(raw.get(\"content\"))}"),
]

NOT_PLANTED = [
    "An identifier that is not a number, accepted: it is then not one of the story's attachments, and is refused for that.",
    "An extension with letters of another alphabet, accepted by its own check: it is then on no list, and is refused for that.",
    "The check that the log is a plain file, taken out: a test that makes the log a pipe would then wait for ever, and so would this run.",
    "The limit on how many pieces a file may arrive in, taken out: the test that sends pieces without end would run without end.",
    "The look for a file already under the saved name, taken out: giving the file its name then fails, because the name is taken, and it is refused for that.",
    "In the first two and the last a second check stops what the first lets through, so no test can tell from the outside which one did.",
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_attachments"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "attachments.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-read-attachments/attachments.py. jira-read-attachments, attempt jira-attempt-021",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the tests are run",
             "against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "skills", "jira-read-comments-history")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(temp, "participant", "context", "jira"))
        shutil.copy(CONFIG, os.path.join(temp, "participant", "context", "jira"))
        copy = os.path.join(work, "attachments.py")
        passed, said = run_tests(work)
        lines.append("First, with no bug planted, the tests against the copy: %s" % said)
        if not passed:
            lines.append("THE TESTS DO NOT PASS WITHOUT A BUG, so nothing below would mean anything. Stopped.")
            problems.append("the tests fail with no bug planted")
        else:
            lines.append("")
            for number, (what, old, new) in enumerate(BUGS, 1):
                if source.count(old) != 1 or old == new:
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
    with open(os.path.join(SKILL, "attachments.py"), encoding="utf-8") as f:
        same = f.read() == source
    unchanged = git_state() == before
    lines.append("The real tool is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    lines += ["", "NOT PLANTED, AND WHY"] + ["  " + line for line in NOT_PLANTED]
    planted = len(BUGS) - sum(1 for p in problems if "could not be planted" in p)
    result = "RESULT: %d OF %d PLANTED BUGS CAUGHT." % (planted - len(missed), len(BUGS)) + ("" if not missed and not problems else " NOT ALL: " + "; ".join(missed + problems))
    lines += ["", result]
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(result)
    for line in lines:
        if "MISSED" in line or "NOT PLANTED " in line:
            print(line)
    return 0 if not missed and not problems else 1


if __name__ == "__main__":
    sys.exit(main())

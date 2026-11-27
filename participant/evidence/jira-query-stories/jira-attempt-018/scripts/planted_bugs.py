#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-query-stories/run_query.py and runs the tests against
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-query-stories")
CONFIG = os.path.join(PARTICIPANT, "context", "jira", "queries.yaml")
LIMIT = 120

BUGS = [
    # knowing when the pages ended
    ("a page shorter than was asked for is taken for the last", "        if not following:\n            if body.get", "        if not following or len(page) < size:\n            if False and body.get"),
    ("Jira saying there is more, with no marker, is taken for the end", "            if body.get(\"isLast\", True) is not True:", "            if False:"),
    ("the marker for the next page is not sent, so page 1 is asked for again", "            params[\"nextPageToken\"] = marker", "            pass"),
    ("there is no limit to the number of pages", "        if len(page_sizes) >= MAX_PAGES:", "        if False:"),
    # comparing with what Jira stated
    ("a different number arriving than Jira stated is not a failure", "        if len(items) != before:", "        if False:"),
    ("Jira's count moving during the run is not noticed", "        if before != after:", "        if False:"),
    ("the count is not asked for again after the pages", "        after = ask_count(conn, jql, \"after\")", "        after = before"),
    ("an item that comes twice is counted twice", "            if marks & (seen | fresh_seen):", "            if False:"),
    ("an item of another project is kept", "    if found.group(1).upper() != project:", "    if False:"),
    ("a count of zero is treated as no count", "isinstance(count, bool) or count < 0:", "isinstance(count, bool) or count <= 0:"),
    # nothing that looks complete
    ("the result file is written whether or not the run was complete", "    if failure is None:\n        result = {", "    if True:\n        result = {"),
    ("an incomplete run exits with 0", "            say(older)\n        code = 2", "            say(older)\n        code = 0"),
    ("a result that could not be written is still called complete", "            failure = \"the result file could not be written where --out said\"", "            pass"),
    ("a write that fails halfway leaves its temporary file", "            os.unlink(temporary)", "            pass"),
    ("the shortfall is given as the whole total", "say(\"SHORTFALL: Jira stated %d and %d arrived. %d did not.\" % (before, arrived[0], before - arrived[0]))",
     "say(\"SHORTFALL: Jira stated %d and %d arrived. %d did not.\" % (before, arrived[0], before))"),
    ("the items that arrived before a failure are reported as none", "        failure, arrived = str(problem), problem.arrived or arrived", "        failure = str(problem)"),
    # the configuration
    ("the page size in the configuration is ignored", "    size = config[\"page_size\"]", "    size = 50"),
    ("a filter may close the bracket that keeps it in the project", "            if depth < 0:", "            if False:"),
    ("a filter may carry its own ORDER BY", "    if re.search(r\"\\border\\s+by\\b\", text, re.I):", "    if False:"),
    ("a query needs no purpose", "        if len(query.get(\"purpose\", \"\").strip()) < 10 or UNSEEN.search(query[\"purpose\"]):", "        if False:"),
    ("a blank may sit inside quotes, and be quoted twice", "        if re.search(r\"[\\\"']\\s*\\{%s\\}|\\{%s\\}\\s*[\\\"']\" % (name, name), text):", "        if False:"),
    ("an unknown setting in the configuration is ignored", "                raise Refused(\"%s: `%s` is not a setting this tool knows\" % (where, shown(key)))", "                continue"),
    # what may be put into a query
    ("a project that is not on the allowed list is accepted", "    if not PROJECT.fullmatch(args.project) or project not in config[\"projects\"]:", "    if not PROJECT.fullmatch(args.project):"),
    ("the shape of a date is not checked", "            if not re.fullmatch(r\"[0-9]{4}-[0-9]{2}-[0-9]{2}\", value):", "            if False:"),
    ("digits of other scripts pass for a date: the bug the tests found in the first version", "            if not re.fullmatch(r\"[0-9]{4}-[0-9]{2}-[0-9]{2}\", value):", "            if not re.fullmatch(r\"\\d{4}-\\d{2}-\\d{2}\", value):"),
    ("a date that is not on the calendar is accepted", "            datetime.date(int(value[:4]), int(value[5:7]), int(value[8:]))", "            pass"),
    ("a parameter may be left out or added", "    if sorted(given) != sorted(query[\"parameters\"]):", "    if False:"),
    # only reads, and nothing private
    ("titles are asked for", "FIELDS = \"issuetype,status,updated\"", "FIELDS = \"issuetype,status,updated,summary\""),
    ("the connection will send a POST anywhere", "        if path != COUNT_PATH or set(body) != {\"jql\"}:", "        if False:"),
    ("the connection will send a GET anywhere", "        if path != SEARCH_PATH:\n            raise Refused(\"this tool sends GET to one path only\")", "        if False:\n            raise Refused(\"this tool sends GET to one path only\")"),
    ("any request is reported as one of the two reads", "        return all((method.split(\" \")[0], path) in", "        return all(True or (method.split(\" \")[0], path) in"),
    ("the made-up Jira's switches are accepted for a real Jira", "            if args.fixture or args.fault:", "            if False:"),
    ("the output is not searched for the credentials", "    if any(secret and secret in text for secret in secrets):", "    if False:"),
    ("the site's address is left in the saved output", "        kept = kept.replace(\"https://\" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept", "        kept = kept"),
    ("names chosen by the site's administrators are saved as they come", "    return \"\".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else \"?\" for ch in value)[:limit].strip() or None", "    return value[:limit].strip() or None"),
    ("an address with a path or without https is accepted", "    if not host or base.lower() != \"https://\" + host:", "    if not host:"),
    # found by the independent readers, or shown by them to be mistakes the first tests would not notice
    ("a backslash is allowed in a filter, so a hidden quote can take it out of the project: found by both readers", "    if \"\\\\\" in text:", "    if False:"),
    ("more arriving than Jira stated is not a failure", "        if len(items) != before:", "        if len(items) < before:"),
    ("a page with a status other than 200 is read as a page", "        page = body.get(\"issues\") if status == 200 and isinstance(body, dict) else None", "        page = body.get(\"issues\") if isinstance(body, dict) else None"),
    ("a count with a status other than 200 is read as a count", "    count = body.get(\"count\") if status == 200 and isinstance(body, dict) else None", "    count = body.get(\"count\") if isinstance(body, dict) else None"),
    ("a count of `true` is taken for 1", "    if not isinstance(count, int) or isinstance(count, bool) or count < 0:", "    if not isinstance(count, int) or count < 0:"),
    ("an empty page that says there is more is accepted", "        if not page and following:", "        if False:"),
    ("the same marker given back is accepted", "        if following and following == marker:", "        if False:"),
    ("a page that could not be reached is taken for the end of the pages", "            raise stop(str(failure))", "            return items, page_sizes"),
    ("the last page is believed unless it says exactly `false`", "            if body.get(\"isLast\", True) is not True:", "            if body.get(\"isLast\") is False:"),
    ("two items with one key and different ids are both kept", "            marks = {\"id \" + item[\"id\"], \"key \" + item[\"key\"]}", "            marks = {\"id \" + item[\"id\"]}"),
    ("an item's id is not checked", "    if not found or not (isinstance(ident, str) and ident.isascii() and ident.isdigit() and len(ident) <= 20) or not isinstance(fields, dict):", "    if not found or not isinstance(fields, dict):"),
    ("an item missing what was asked for is saved with blanks", "    if None in (item[\"issuetype\"], item[\"status\"], item[\"updated\"]):", "    if False:"),
    ("the items of a page that fails in its middle are counted as arrived", "            fresh.append(item)", "            fresh.append(item)\n            items.append(item)"),
    ("a count that moved is also called a shortfall", "        if before is not None and arrived[0] < before and not count_moved:", "        if before is not None and arrived[0] < before:"),
    ("--log may name the result file, and the result is asked for anyway", "    if getattr(args, \"log\", None) and os.path.realpath(args.log) == os.path.realpath(args.out):\n        raise Refused(", "    if False:\n        raise Refused("),
    ("--log may name the result file, and is written over it", "    if getattr(args, \"log\", None) and not (getattr(args, \"out\", None) and os.path.realpath(args.log) == os.path.realpath(args.out)):", "    if getattr(args, \"log\", None):"),
    ("the result is written before the search for credentials", "        if any(secret and secret in \"\\n\".join(LINES) + json.dumps(result) for secret in secrets):", "        if False:"),
    ("a file name is printed as it comes, line breaks and all", "shown(os.path.basename(args.out))))", "os.path.basename(args.out)))"),
    ("something unforeseen is a crash, not an incomplete run", "    except Exception as surprise:", "    except KeyboardInterrupt as surprise:"),
    ("a real server's refusal is not read for its status", "            status, headers, raw = err.code, dict(err.headers), err.read()\n            err.close()", "            raise"),
    ("an answer that is not JSON is a crash", "        except (ValueError, RecursionError):", "        except RecursionError:"),
    ("only the token is searched for, not the email address or the encoded form", "    return Connection(get, post, host), [token, email, encoded]", "    return Connection(get, post, host), [token]"),
    ("redirects are followed", "    opener = opener or urllib.request.build_opener(NoRedirect)", "    opener = opener or urllib.request.build_opener()"),
    ("the sign-in is not sent", "        request.add_header(\"Authorization\", \"Basic \" + encoded)", "        pass"),
    ("a base address in capitals is refused", "    if not host or base.lower() != \"https://\" + host:", "    if not host or base != \"https://\" + host:"),
    ("`parameters` may be given twice in one query", " or key == \"parameters\" and current.get(\"has_parameters\"):", ":"),
    ("a value YAML would read as true, false or nothing is taken as text", "    if text.lower() in NOT_TEXT_IN_YAML or ", "    if "),
    ("`key:value` with no space is read as a setting", "    if not colon or rest[:1] not in (\"\", \" \"):", "    if not colon:"),
    ("names in other scripts are turned into question marks", "ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else \"?\"", "ch if (ch.isascii() and ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else \"?\""),
    ("unseen characters from the configuration are printed in a refusal", "    return \"\".join(\"?\" if UNSEEN.match(ch) else ch for ch in str(text))[:limit]", "    return str(text)[:limit]"),
]

NOT_PLANTED = [
    "A marker for the next page that is not text, accepted: Jira's answer then comes again and its items are seen to come twice.",
    "A page size written 010, accepted by the size check: the reading of the value has already refused it as a number YAML reads differently.",
    "A `---` at the top, accepted by its own check: the line is then refused as not being `key: value`.",
    "In each, a second check catches what the first lets through, so no test can tell from the outside which one did.",
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_run_query"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "run_query.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-query-stories/run_query.py. jira-query-stories, attempt jira-attempt-018",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the tests are run",
             "against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "skills", "jira-query-stories")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(temp, "participant", "context", "jira"))
        shutil.copy(CONFIG, os.path.join(temp, "participant", "context", "jira"))
        copy = os.path.join(work, "run_query.py")
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
    with open(os.path.join(SKILL, "run_query.py"), encoding="utf-8") as f:
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

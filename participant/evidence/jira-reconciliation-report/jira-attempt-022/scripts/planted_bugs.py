#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-reconciliation-report/reconcile.py and runs the tests against
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-reconciliation-report")
CONFIG = os.path.join(PARTICIPANT, "context", "jira", "reconciliation")
LIMIT = 120

BUGS = [
    # exactly one state, and the order of the states
    ("an item changed on both sides is not called conflicted", "    if jira_changed and locally_changed:                                                        # 3", "    if False:"),
    ("an item changed locally only is called synchronized", "    if locally_changed:                                                                         # 4", "    if False:"),
    ("an item Jira has changed is called synchronized: the stale ones hide in the largest number", "    if jira_changed:                                                                            # 5", "    if False:"),
    ("a failed fetch gives way to a local change", "    if kind == \"failed\":                                                                        # 1", "    if kind == \"failed\" and not locally_changed:"),
    ("an item Jira no longer has gives way to a local change", "    if kind == \"gone\":                                                                          # 2", "    if kind == \"gone\" and not locally_changed:"),
    ("items Jira has that were never copied are not counted: the quest's scenario", "        for number in sorted(set(listed) - held, key=int):                                      # 6", "        for number in []:"),
    ("a new key, or a new last-changed time, is not taken as a change in Jira", "    jira_changed = (value[\"key\"], value[\"issuetype\"], value[\"status\"], value[\"updated\"]) != (copied[\"key\"], copied[\"issuetype\"], copied[\"status\"], copied[\"updated\"])",
     "    jira_changed = (value[\"issuetype\"], value[\"status\"]) != (copied[\"issuetype\"], copied[\"status\"])"),
    ("an item that fits a second state does not say so", "        out[\"also\"].append(\"stale: %s\" % lag)", "        pass"),
    # the counts add up
    ("the tool's own check is not acted on", "    if problems:\n        say(\"  CHECK FAILED:\")", "    if False:\n        say(\"  CHECK FAILED:\")"),
    ("the check does not look for an item given two states", "        if numbers.count(number) != 1:", "        if False:"),
    ("the check does not compare the sum of the counts with the total", "    if sum(counts.values()) != total:", "    if False:"),
    ("the check does not look for an item given no state", "    if set(numbers) != considered:", "    if False:"),
    ("the total leaves out the items that are in Jira only", "    considered = set(i[\"id\"] for i in copy[\"items\"]) | set(listed or [])", "    considered = set(i[\"id\"] for i in copy[\"items\"])"),
    ("the check counts what the tool itself made, and not the numbers the copy and Jira's list gave", "    considered = set(i[\"id\"] for i in copy[\"items\"]) | set(listed or [])", "    considered = set(numbers)"),
    ("the check does not compare an item's state with what was found for it", "        if not agrees or (entry[\"state\"] == \"not yet copied\") != (entry[\"id\"] not in held):", "        if False:"),
    # names
    ("two names that clean to the same thing are called the same", "    jira_changed = jira_changed or renamed", "    jira_changed = jira_changed"),
    ("the checksum of the names is taken after they are cleaned", "\"names_checksum\": names_checksum(kind, state)}", "\"names_checksum\": names_checksum(clean(kind), clean(state))}"),
    ("an item now in another project is taken as still in this one", "    if found.group(1).upper() != project:\n        return \"gone\", \"moved\"", "    if False:\n        return \"gone\", \"moved\""),
    # stale
    ("an item exactly at the limit is over it", "    over = behind > STALE_LIMIT_HOURS * 3600", "    over = behind >= STALE_LIMIT_HOURS * 3600"),
    ("a stale item's age is counted from when it was copied, not from when Jira changed it", "    behind = seconds_between(value[\"updated\"], as_of)", "    behind = seconds_between(item[\"copied_at\"], as_of)"),
    ("the limit is 48 hours", "STALE_LIMIT_HOURS = 24", "STALE_LIMIT_HOURS = 48"),
    ("an item over the limit is told to wait for the next sync", "next=\"Sync it now, and find out why the last sync missed it.\" if over else", "next=\"Sync it now, and find out why the last sync missed it.\" if False else"),
    # a failed item
    ("a failed item repeats what Jira said in refusing", "        return \"failed\", failure_class(status, problem)", "        return \"failed\", str(body)[:80]"),
    ("an item Jira will not show (403) is called missing", "    if status == 404:\n        return \"gone\", None", "    if status in (403, 404):\n        return \"gone\", None"),
    ("an answer for another item is taken as this item's", "    if not found or body.get(\"id\") != number or clean(kind) is None", "    if not found or clean(kind) is None"),
    ("rejected credentials are counted as a failed item each", "        raise Refused(\"Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN\")\n    if status == 404:", "        pass\n    if status == 404:"),
    ("a request that times out is called a network error", "            self.sent.append((\"GET (no answer)\", path, \"timed out\"))\n            return None, {}, \"timed out\"", "            self.sent.append((\"GET (no answer)\", path, \"network error\"))\n            return None, {}, \"network error\""),
    ("a server error is called an unexpected status", "    if isinstance(status, int) and 500 <= status <= 599:", "    if False:"),
    # when the list cannot be read
    ("a report that could not count Jira's own items exits with 0", "    return 2 if list_failure else 0", "    return 0"),
    ("a report that could not count Jira's own items does not say so", "    if list_failure:\n        out += [\"**INCOMPLETE.**", "    if False:\n        out += [\"**INCOMPLETE.**"),
    ("an item listed twice is accepted", " or raw[\"id\"] in listed or ", " or "),
    ("the last page of the list is believed whatever it says", "            return (listed, None) if body.get(\"isLast\", True) is True else (None, \"unreadable answer\")", "            return listed, None"),
    ("the marker for the next page of the list is not sent", "            params[\"nextPageToken\"] = marker", "            pass"),
    ("there is no limit to the pages of the list", "        if pages >= MAX_PAGES or len(listed) > MAX_ITEMS:", "        if False:"),
    # the same input, the same report
    ("the items are asked about in the order the copy holds them", "    for item in sorted(copy[\"items\"], key=lambda i: int(i[\"id\"])):", "    for item in copy[\"items\"]:"),
    ("a run is added to the history every time", "    added = not any(run[\"input\"] == mark for run in history[\"runs\"])", "    added = True"),
    ("the order of the items in the copy's file is part of the input", "    in_order = dict(copy, items=sorted(copy[\"items\"], key=lambda i: int(i[\"id\"])))", "    in_order = copy"),
    ("the history is in the order the reports were run, not the order of their times", "sorted(history[\"runs\"], key=lambda run: (run[\"as_of\"], run[\"input\"]))[-HISTORY_KEEPS:]", "history[\"runs\"][-HISTORY_KEEPS:]"),
    ("the history grows without limit", "[-HISTORY_KEEPS:]", ""),
    ("a report is made as of a time before the copy was taken", "    if any(i[\"copied_at\"] > as_of for i in copy[\"items\"]):", "    if False:"),
    ("a span of days drops its minutes", "if minutes else \"\"]", "if minutes and not days else \"\"]"),
    ("an incomplete run shows a count of not-yet-copied in the trend", "        cells = [\"not known\" if run.get(\"incomplete\") and name == \"not yet copied\" else str(run[\"counts\"][name]) for name in STATE_NAMES]", "        cells = [str(run[\"counts\"][name]) for name in STATE_NAMES]"),
    ("an incomplete report shows 0 not yet copied in its table", "        shown_count = \"NOT KNOWN\" if list_failure and name == \"not yet copied\" else \"%d\" % counts[name]", "        shown_count = \"%d\" % counts[name]"),
    ("the copy's file name goes into the report as it is", "    files = {\"copy\": file_label(args.copy),", "    files = {\"copy\": os.path.basename(args.copy),"),
    ("a write that fails part way says nothing was written", "\"Nothing was written\" if not wrote else", "\"Nothing was written\" if True else"),
    ("the trend shows every run, not the last five", "history[\"runs\"][-5:]", "history[\"runs\"]"),
    ("the files are written even when nothing changed", "            if before[which] != hashlib.sha256(texts[which].encode(\"utf-8\")).hexdigest():", "            if True:"),
    ("a made-up run takes the time from the clock", "                if args.as_of is None:", "                if False:"),
    # the log
    ("every exception cites the first line of the log", "        entry[\"log_line\"] = len(conn.sent)", "        entry[\"log_line\"] = 1"),
    # what is asked for, and other people's text
    ("titles are asked for", "FIELDS = \"issuetype,status,updated\"", "FIELDS = \"issuetype,status,updated,summary\""),
    ("a status or type name is kept as it comes", "    return \"\".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else \"?\" for ch in value)[:limit].strip() or None", "    return value[:limit].strip() or None"),
    # the local copy and the files
    ("a local copy that is not in the form the tool reads is used anyway", "    if not good:\n        raise Refused(\"the local copy is not in the form", "    if False:\n        raise Refused(\"the local copy is not in the form"),
    ("a number or key held twice in the copy is accepted", "    if len(set(numbers)) != len(numbers) or len(set(keys)) != len(keys):", "    if False:"),
    ("a copy made from another Jira is compared", "    if (copy[\"source\"], copy[\"site_fingerprint\"]) != (source, site):", "    if False:"),
    ("a file of the same name that is someone else's is written over", "                if f.read(len(starts[which].encode(\"utf-8\"))) != starts[which].encode(\"utf-8\"):", "                if False:"),
    ("one of the report's files may be the local copy itself", "        if same_file(path, copy_path):", "        if False:"),
    ("a file that is a link, or has a second name, is written through", "        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):", "        if os.path.isdir(path):"),
    ("a history this tool did not write is used anyway", "    if not good:\n        raise Refused(\"the history beside the report is not one this tool wrote", "    if False:\n        raise Refused(\"the history beside the report is not one this tool wrote"),
    ("a write that fails halfway leaves its temporary file", "            os.unlink(temporary)", "            pass"),
    ("--log is written over a file that is not an output of the tool", "(os.path.lexists(log_to) and not any(start.match(already) for start in LOG_STARTS))", "False"),
    ("--log is written over anything that begins with the first word of an output", "LOG_STARTS = (re.compile(rb\"Project: [A-Z][A-Z0-9_]{0,30}\\nCompared: the local copy given with --copy\"), re.compile(rb\"REFUSED: \"),", "LOG_STARTS = (re.compile(rb\"Project: \"), re.compile(rb\"REFUSED\"),"),
    ("--log may name a place in a folder that is not there", " or not os.path.isdir(os.path.dirname(os.path.abspath(log_to)))):", "):"),
    ("something unforeseen is a crash", "    except Exception as surprise:", "    except KeyboardInterrupt as surprise:"),
    # adopting
    ("a result that was not complete is adopted", "result.get(\"complete\") is True and ", ""),
    ("adopting writes a copy without checking that the report would read it", "        check_copy(copy)                    # what is written", "        pass                    # what is written"),
    ("a copy may say anything about which Jira it came from", "((copy.get(\"source\") == \"fake\" and copy[\"site_fingerprint\"] is None) or (copy.get(\"source\") == \"live\" and isinstance(copy[\"site_fingerprint\"], str) and re.fullmatch(r\"[0-9a-f]{16}\", copy[\"site_fingerprint\"])))", "copy.get(\"source\") in (\"fake\", \"live\")"),
    ("adopting writes over what is there", "    if os.path.lexists(out):", "    if False:"),
    # only reads, and nothing private
    ("the files are written before the search for credentials", "    if any(secret and secret in \"\\n\".join(LINES) + \"\".join(texts.values()) for secret in secrets):", "    if False:"),
    ("the connection will send a GET anywhere", "        if not (path == SEARCH_PATH or re.fullmatch(r\"/rest/api/3/issue/[0-9]{1,20}\", path)):", "        if False:"),
    ("any request is reported as a plain GET", "        return all(method.split(\" \")[0] == \"GET\" and \"BODY\" not in method for method, _, _ in self.sent)", "        return True"),
    ("the method reported is the word GET, not the request's own", "        return status, headers, parsed, request.get_method(), request.data is not None", "        return status, headers, parsed, \"GET\", False"),
    ("the output is not searched for the credentials", "    if any(secret and secret in text for secret in secrets):", "    if False:"),
    ("only the token is searched for", "    return Connection(get, host), [token, email, encoded]", "    return Connection(get, host), [token]"),
    ("the site's address is left in the saved output", "        kept = kept.replace(\"https://\" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept", "        kept = kept"),
    ("a real server's refusal is not read for its status", "            status, headers, raw = err.code, dict(err.headers), b\"\"", "            raise"),
    ("redirects are followed", "    opener = opener or urllib.request.build_opener(NoRedirect)", "    opener = opener or urllib.request.build_opener()"),
    ("an address with a path or a port, or without https, is accepted", "    if not host or base.lower() != \"https://\" + host:", "    if not host:"),
    ("a request may wait for ever", "            with opener.open(request, timeout=30) as response:", "            with opener.open(request) as response:"),
]

NOT_PLANTED = [
    "--log allowed to name one of the tool's own files or the copy: none of those begins as an output of this tool begins, so the next check refuses it for that.",
    "The body of a real server's refusal read after all: it is then parsed and still never used, because only the status of a refusal is looked at.",
    "In those two a second check stops what the first lets through, so no test can tell from the outside which one did.",
    "The states tried in another order altogether: not one line to change. A test works out, for each combination of what Jira and the copy can say, which state the order gives, and compares.",
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_reconcile"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "reconcile.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-reconciliation-report/reconcile.py. jira-reconciliation-report, attempt jira-attempt-022",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the tests are run",
             "against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "skills", "jira-reconciliation-report")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(CONFIG, os.path.join(temp, "participant", "context", "jira", "reconciliation"))
        copy = os.path.join(work, "reconcile.py")
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
    with open(os.path.join(SKILL, "reconcile.py"), encoding="utf-8") as f:
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

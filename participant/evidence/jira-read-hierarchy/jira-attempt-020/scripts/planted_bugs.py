#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-read-hierarchy/hierarchy.py and runs the tests against
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-read-hierarchy")
CONFIG = os.path.join(PARTICIPANT, "context", "jira", "hierarchy.md")
LIMIT = 120

BUGS = [
    # the tree, from identifiers
    ("an item whose parent was not retrieved is shown as an item with no parent", "        else:\n            unresolved.setdefault(item[\"parent_id\"], []).append(item[\"id\"])", "        else:\n            roots.append(item[\"id\"])"),
    ("an item whose parent was not retrieved is dropped from the tree", "        else:\n            unresolved.setdefault(item[\"parent_id\"], []).append(item[\"id\"])", "        else:\n            pass"),
    ("children are put in order by key, so the tree depends on keys", "    for item in sorted(items, key=lambda i: int(i[\"id\"])):\n        if item[\"parent_id\"] is None:", "    for item in sorted(items, key=lambda i: i[\"key\"]):\n        if item[\"parent_id\"] is None:"),
    ("a parent Jira names without a number is taken for no parent", "    if parent is not None:\n        if not isinstance(parent, dict) or not ident(parent.get(\"id\")):", "    if isinstance(parent, dict) and ident(parent.get(\"id\")):\n        if False:"),
    # a loop or a self-parent
    ("an item that is its own parent is not rejected", "        if item[\"parent_id\"] == item[\"id\"]:", "        if False:"),
    ("a loop is not rejected", "        if at in on_path and len(path[path.index(at):]) > 1:", "        if False:"),
    ("a loop is named once for every item it is met from", "            loops.add(tuple(loop[start:] + loop[:start]))", "            loops.add(tuple(loop))"),
    ("a number or key held by two items is accepted", "        for value in sorted(v for v, n in held.items() if n > 1):", "        for value in []:"),
    ("a rejected build exits with 0", "        say(older)\n    return 2", "        say(older)\n    return 0"),
    ("a rejected build does not say the files on disk are older", "    older = None if old is None else \"The records already on disk", "    older = None if True else \"The records already on disk"),
    # a moved item
    ("a moved item is not reported", "if n in before and before[n][\"parent_id\"] != now[n][\"parent_id\"]]", "if n in before and before[n][\"parent_id\"] != before[n][\"parent_id\"]]"),
    ("items are matched with the earlier records by key, so one given a new key is a new item and a gone one", "    before, now = {i[\"id\"]: i for i in old[\"items\"]}, {i[\"id\"]: i for i in items}", "    before, now = {i[\"key\"]: i for i in old[\"items\"]}, {i[\"key\"]: i for i in items}"),
    # estimates
    ("an estimate is counted twice on the way up: the scenario", "            seconds, missing, count = seconds + s, missing + m, count + c", "            seconds, missing, count = seconds + 2 * s, missing + m, count + c"),
    ("an item with no estimate is not counted as lacking one", "1 if by_id[number][\"estimate_seconds\"] is None else 0, 1", "0, 1"),
    ("no estimate is shown as zero hours", "    return \"no estimate\" if seconds is None else", "    return \"0 h\" if seconds is None else"),
    ("what is under a parent not retrieved is added to the main total", "    in_tree, apart = group(tree[\"roots\"]), group(", "    in_tree, apart = group(tree[\"roots\"] + [n for g in tree[\"unresolved\"].values() for n in g]), group("),
    ("an estimate below zero is accepted", "    if estimate is not None and (type(estimate) is not int or estimate < 0 or estimate > 10 ** 9):", "    if False:"),
    # links
    ("a link is listed once for each end it is read from", "                if links.setdefault(link[\"id\"], link) != link:", "                if links.setdefault(link[\"id\"] + item[\"id\"], link) != link:"),
    ("a link read from its far end is turned round", "        source, target = (mine, theirs) if outward else (theirs, mine)", "        source, target = (mine, theirs)"),
    # the same across two runs
    ("the items are kept in the order Jira sent them", "    return sorted(first, key=lambda i: int(i[\"id\"])), links, pages", "    return first, links, pages"),
    ("the files are written even when nothing changed", "        if before[0] != hashlib.sha256(records_text.encode(\"utf-8\")).hexdigest():", "        if True:"),
    ("a page that was changed is not put right", "        if before[1] != hashlib.sha256(page_text.encode(\"utf-8\")).hexdigest():", "        if wrote:"),
    # the whole project, or nothing
    ("the project is read once, not twice", "    second, links_again, _ = read_once(conn, project)", "    second, links_again = first, links"),
    ("Jira's count is not compared with what was read", "    if not before == after == len(first):", "    if False:"),
    ("the count is not asked for again after the readings", "    after = ask_count(conn, project)", "    after = before"),
    ("an item that comes twice in the pages is accepted", "            if marks & seen:", "            if False:"),
    ("the last page is believed whatever it says about being the last", "            if body.get(\"isLast\", True) is not True:", "            if False:"),
    ("the marker for the next page is not sent", "            params[\"nextPageToken\"] = marker", "            pass"),
    ("there is no limit to the pages", "        if pages >= MAX_PAGES:", "        if False:"),
    ("a page with a status other than 200 is read as a page", "        page = body.get(\"issues\") if status == 200 and isinstance(body, dict) else None", "        page = body.get(\"issues\") if isinstance(body, dict) else None"),
    ("a count with a status other than 200 is read as a count", "    count = body.get(\"count\") if status == 200 and isinstance(body, dict) else None", "    count = body.get(\"count\") if isinstance(body, dict) else None"),
    ("an item of another project is kept", "    if found.group(1).upper() != project:", "    if False:"),
    # what is asked for, and other people's text
    ("titles are asked for", "FIELDS = \"issuetype,parent,timeoriginalestimate,issuelinks\"", "FIELDS = \"issuetype,parent,timeoriginalestimate,issuelinks,summary\""),
    ("a type's name is kept as it comes", "    return \"\".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else \"?\" for ch in value)[:limit].strip() or None", "    return value[:limit].strip() or None"),
    ("an epic is known only by the word epic", "        if item[\"level\"] == 1 or (not marked and name == \"epic\"):", "        if not marked and name == \"epic\":"),
    ("a parent link Jira does not usually allow is not pointed out", "        if parent and item[\"level\"] is not None and parent[\"level\"] is not None and item[\"level\"] >= parent[\"level\"]:", "        if False:"),
    ("a subtask for which Jira names no parent is not pointed out: seen on the real project", "        if item[\"parent_id\"] is None and (item[\"subtask\"] or item[\"level\"] == -1):", "        if False:"),
    ("a total over items that have no estimate is shown as 0 h: seen on the real project", "    if missing == count:\n        return \"no estimate on any of the %d\" % count", "    if missing == count and False:\n        return \"no estimate on any of the %d\" % count"),
    # the files
    ("records of another project, or from another Jira, are written over", "    if old is not None and (old.get(\"project\"), old.get(\"source\"), old.get(\"site_fingerprint\")) != (project, source, site):", "    if False:"),
    ("a records file this tool did not write is used anyway", "    if not good:", "    if False:"),
    ("--log is compared with the two files by its spelling, so the same file in other capitals is written", "                if os.path.islink(log_to) or (os.path.isfile(log_to) and os.stat(log_to).st_nlink > 1) or any(same_file(log_to, path) for path in own):",
     "                if any(os.path.realpath(log_to) == os.path.realpath(path) for path in own):"),
    ("a refusal is saved over the file --log was refused for", "                    log_to = None           # and", "                    pass           # and"),
    ("a records file or page that is a link, or has a second name, is written through", "        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):", "        if os.path.isdir(path):"),
    ("a write that fails halfway leaves its temporary file", "            os.unlink(temporary)", "            pass"),
    ("something unforeseen is a crash", "    except Exception as surprise:", "    except KeyboardInterrupt as surprise:"),
    # only reads, and nothing private
    ("the connection will send a GET anywhere", "        if path != SEARCH_PATH:\n            raise Refused(\"this tool sends GET to one path only, the search\")", "        if False:\n            raise Refused(\"this tool sends GET to one path only, the search\")"),
    ("the connection will send a POST anywhere", "        if path != COUNT_PATH or set(body) != {\"jql\"}:", "        if False:"),
    ("any request is reported as one of the two reads", "        return all((method.split(\" \")[0], path) in", "        return all(True or (method.split(\" \")[0], path) in"),
    ("the method reported is the word GET, not the request's own", "        return status, headers, parsed, request.get_method()", "        return status, headers, parsed, \"GET\""),
    ("the made-up Jira's folder is accepted for a real Jira", "                if args.state:\n                    raise Refused(\"--state is for the made-up Jira only\")", "                if False:\n                    raise Refused(\"--state is for the made-up Jira only\")"),
    ("the output is not searched for the credentials", "    if any(secret and secret in text for secret in secrets):", "    if False:"),
    ("only the token is searched for", "    return Connection(get, post, host), [token, email, encoded]", "    return Connection(get, post, host), [token]"),
    ("the site's address is left in the saved output", "        kept = kept.replace(\"https://\" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept", "        kept = kept"),
    ("a real server's refusal is not read for its status", "            status, headers, raw = err.code, dict(err.headers), err.read()\n            err.close()", "            raise"),
    ("redirects are followed", "    opener = opener or urllib.request.build_opener(NoRedirect)", "    opener = opener or urllib.request.build_opener()"),
    ("an address with a path or a port, or without https, is accepted", "    if not host or base.lower() != \"https://\" + host:", "    if not host:"),
    # found by the independent readers, or shown by them to be mistakes the first tests would not notice
    ("the tree is printed flat: every item at one depth", "            stack.extend((child, depth + 1) for child in reversed(tree[\"children\"][number]))", "            stack.extend((child, depth) for child in reversed(tree[\"children\"][number]))"),
    ("a move is judged by the parent's key, so a new key on a parent looks like a move of its children", "if n in before and before[n][\"parent_id\"] != now[n][\"parent_id\"]]", "if n in before and before[n][\"parent_key\"] != now[n][\"parent_key\"]]"),
    ("children are put in order by the text of their numbers, so 100 comes before 9", "    for item in sorted(items, key=lambda i: int(i[\"id\"])):\n        if item[\"parent_id\"] is None:", "    for item in sorted(items, key=lambda i: i[\"id\"]):\n        if item[\"parent_id\"] is None:"),
    ("a page of the same name that is someone else's file is written over", "    if os.path.exists(page_path) and not os.path.exists(records_path):", "    if False:"),
    ("a records file is taken on trust, so text in it can forge a line of the output", "            and all(good_item(i) for i in records[\"items\"]) and all(good_link(link) for link in records[\"links\"]))", "            and all(isinstance(i, dict) and ident(i.get(\"id\")) for i in records[\"items\"]))"),
    ("a number with a leading zero is taken as another number", "    return isinstance(value, str) and re.fullmatch(r\"0|[1-9][0-9]{0,19}\", value) is not None", "    return isinstance(value, str) and re.fullmatch(r\"[0-9]{1,20}\", value) is not None"),
    ("large totals are printed in a form with an exponent", "(\"%.2f\" % (seconds / 3600.0)).rstrip(\"0\").rstrip(\".\") + \" h\"", "\"%g h\" % round(seconds / 3600.0, 2)"),
    ("a link that names two other items is read as naming one", "        if outward and \"inwardIssue\" in link:", "        if False:"),
    ("a link described differently at its two ends is kept as first seen", "                if links.setdefault(link[\"id\"], link) != link:", "                if links.setdefault(link[\"id\"], link) != link and False:"),
    ("links that differ between the two readings are accepted", " or links != links_again:", ":"),
    ("a link's name is kept as it comes", "\"phrase\": clean(link[\"type\"].get(\"outward\")) or \"is linked to\",", "\"phrase\": link[\"type\"].get(\"outward\") or \"is linked to\","),
    ("a parent's key that is not a key is kept", "        parent_key = parent[\"key\"].upper() if isinstance(parent.get(\"key\"), str) and REF.fullmatch(parent[\"key\"]) else None", "        parent_key = parent[\"key\"].upper() if isinstance(parent.get(\"key\"), str) else None"),
    ("--log is written over a file that is not an output of the tool", "                    if not already.startswith(tuple(start.encode(\"utf-8\") for start in LOG_STARTS)):", "                    if False:"),
    ("a page that could not be written is reported with the words nothing was written", "        raise WriteFailed(\"a file could not be written%s.", "        raise Refused(\"a file could not be written%s."),
    ("the files are left readable by their owner only", "        os.chmod(temporary, 0o644)", "        pass"),
    ("the files are written before the search for credentials", "    if any(secret and secret in \"\\n\".join(LINES) + records_text + page_text for secret in secrets):", "    if False:"),
    ("a project that is not a key is sent to Jira", "    if not PROJECT.fullmatch(args.project):", "    if False:"),
    ("an empty page that says there is more is accepted", "        if (not page and following) or (following and following == marker):", "        if following and following == marker:"),
    ("the marker given back is accepted", "        if (not page and following) or (following and following == marker):", "        if not page and following:"),
    ("Jira's own mark for a subtask is ignored", "        elif item[\"subtask\"] or item[\"level\"] == -1 or (not marked and name in (\"subtask\", \"sub-task\")):", "        elif item[\"level\"] == -1 or (not marked and name in (\"subtask\", \"sub-task\")):"),
    ("a type merely named Epic is an epic, whatever Jira's mark says", "        if item[\"level\"] == 1 or (not marked and name == \"epic\"):", "        if item[\"level\"] == 1 or name == \"epic\":"),
    ("an estimate that is a fraction is accepted", "    if estimate is not None and (type(estimate) is not int or estimate < 0 or estimate > 10 ** 9):", "    if estimate is not None and (not isinstance(estimate, (int, float)) or estimate < 0 or estimate > 10 ** 9):"),
    ("the count of items with no parent named is wrong", "sum(1 for i in items if i[\"parent_id\"] is not None), sum(1 for i in items if i[\"parent_id\"] is None)))", "sum(1 for i in items if i[\"parent_id\"] is not None), len(items)))"),
    ("a request may wait for ever", "            with opener.open(request, timeout=30) as response:", "            with opener.open(request) as response:"),
    ("a group with no estimates at all is totalled as 0 h", "    if count == 0:\n        return \"no items\"\n    if missing == count:", "    if count == 0:\n        return \"no items\"\n    if False:"),
]

NOT_PLANTED = [
    "A count of `true` taken for 1: it then differs from the number of items read, unless exactly one item was read.",
    "An estimate in words accepted: adding it up then fails, and the build is refused as something unforeseen. Nothing is written either way.",
    "Links used to build the tree: there is no single line to change that would do it. A test adds a link and requires the tree's checksum not to move.",
    "The check that a records file is a plain file, taken out: the test that feeds it a pipe would then wait for ever, and so would this run.",
    "Adding up the tree by a function that calls itself: not one line to change. A test builds a chain of 3,000 and requires a tree.",
    "In the first two a second check stops what the first lets through, so no test can tell from the outside which one did.",
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_hierarchy"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "hierarchy.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-read-hierarchy/hierarchy.py. jira-read-hierarchy, attempt jira-attempt-020",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the tests are run",
             "against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "skills", "jira-read-comments-history")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(temp, "participant", "context", "jira"))
        shutil.copy(CONFIG, os.path.join(temp, "participant", "context", "jira"))
        copy = os.path.join(work, "hierarchy.py")
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
    with open(os.path.join(SKILL, "hierarchy.py"), encoding="utf-8") as f:
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

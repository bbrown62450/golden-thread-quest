#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-next-work (rank.py or sync.py) and runs the tests
against the copy. Records logs/planted-bugs.txt. A test suite that still passes with a bug planted is not testing it.

The real skill is never changed: it is copied to a temporary folder outside the repository, and each bug is planted
in the copy. Each run of the tests is stopped after two minutes. At the end the script asks Git whether anything in
the repository changed while it ran. No network is used: the tests run against the fake Jira.

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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-next-work")
LIMIT = 120
R, S = "rank.py", "sync.py"

BUGS = [
    # the three lists
    (R, "a done item is ranked", '            if item["status"]["category"] == "done":', '            if False:'),
    (R, "an item someone else has is offered", '            elif item["assignee"] == "someone else":', '            elif False:'),
    (R, "a blocked item is ranked", '            elif self.open_blockers(key):', '            elif False:'),
    (R, "an item is taken as blocked by the items IT blocks", 'mine = set(l["other"] for l in self.items[key]["links"] if l["type"] == self.blocks and l["this_item_is"] == "target")', 'mine = set(l["other"] for l in self.items[key]["links"] if l["type"] == self.blocks)'),
    (R, "a link of any type blocks", 'mine = set(l["other"] for l in self.items[key]["links"] if l["type"] == self.blocks and l["this_item_is"] == "target")', 'mine = set(l["other"] for l in self.items[key]["links"] if l["this_item_is"] == "target")'),
    (R, "only the item's own record is read for its blockers: the reader's find", '        for blocker in sorted(mine | theirs, key=key_order):', '        for blocker in sorted(mine, key=key_order):'),
    (R, "a blocker that is done still blocks", '                blocking = not done.pop()', '                blocking = True'),
    (R, "a blocker whose status is not recorded does not block", '            if not views:\n                blocking, doubt = True, True', '            if not views:\n                blocking, doubt = False, True'),
    (R, "when the copies of a blocker's status disagree, the newest is simply believed", '            elif len(done) > 1:\n                blocking, doubt = True, True', '            elif len(done) > 1:\n                blocking, doubt = views[-1][1]["category"] != "done", False'),
    (R, "the blocker's own record is not read for its status", '        if blocker in self.items:\n            views.append(', '        if False:\n            views.append('),
    (R, "what the blocked item showed of its blocker is not read", 'and link["other"] == blocker and link.get("other_status"):', 'and link["other"] == blocker and False:'),
    (R, "a link only the OLDER record shows is not put in doubt", '                    doubt = doubt or newer\n            else:', '                    pass\n            else:'),
    (R, "a stale blocker record puts nothing in doubt", '            if blocker in self.items and self.stale(blocker):\n                doubt = True', '            if blocker in self.items and self.stale(blocker):\n                pass'),
    (R, "doubt about a blocker does not lower confidence", '        if any(blocker["doubt"] for blocker in self.blockers(key)):', '        if False:'),
    (R, "a site with no link type named Blocks is treated as if it had one", '        self.blocks = BLOCKS if any(kind["name"] == BLOCKS for kind in data["link_types"]) else None', '        self.blocks = BLOCKS'),
    (R, "started work is not listed", "        return [key for key in self.ranked if self.items[key][\"assignee\"] == \"me\" and self.items[key][\"status\"][\"category\"] == \"indeterminate\"]", "        return []"),
    (R, "a blocked item that would outrank the start is not pointed out", '        ahead = [key for key in r.blocked if r.sort_key(key) < r.sort_key(start)]', '        ahead = []'),
    (R, "an overdue date is not marked", '"OVERDUE: %d day%s BEFORE the UTC date of the clock value" % (-days, "" if days == -1 else "s"))', '"%d day%s before the UTC date of the clock value" % (-days, "" if days == -1 else "s"))'),
    (R, "a due date of the wrong shape is let through", '                      and (i["duedate"] is None or datetime.datetime.strptime(i["duedate"], "%Y-%m-%d"))\n', ''),
    (R, "a name with characters that break a Markdown table is let through", '        return (optional and value is None) or (isinstance(value, str) and bool(NAME.fullmatch(value)))', '        return (optional and value is None) or isinstance(value, str)'),
    (R, "two keys that differ by a leading zero are left in the order of the file", '    return project, int(number), key', '    return project, int(number)'),
    # stale
    (R, "the stale limit is ten days", 'LIMIT_HOURS = 24', 'LIMIT_HOURS = 240'),
    (R, "a copy exactly at the limit is called stale", '> datetime.timedelta(hours=LIMIT_HOURS)', '>= datetime.timedelta(hours=LIMIT_HOURS)'),
    (R, "a stale item is offered as the thing to start", '            if not self.stale(key):\n                return key', '            if True:\n                return key'),
    (R, "a stale copy does not lower confidence", '        if self.stale(key):\n            why.append("the copy is stale")', '        pass'),
    (R, "the ranked table does not mark a stale item", '"STALE" if r.stale(key) else "-"))', '"-"))'),
    (R, "a ranked item's stale warning is not written", '        if r.stale(key):\n            w("- WARNING: %s." % r.stale_words(key))\n    w("")\n    w("## Blocked")', '    w("")\n    w("## Blocked")'),
    # missing fields
    (R, "missing fields do not lower confidence", 'for gone in self.missing(key)]\n        if self.stale(key):', 'for gone in []]\n        if self.stale(key):'),
    (R, "an item with no priority is ranked first", 'if item["priority"] in self.priorities else len(self.priorities)\n        if criterion == "due"', 'if item["priority"] in self.priorities else -1\n        if criterion == "due"'),
    (R, "an item with no due date is ranked first on due", '            return item["duedate"] or NEVER', '            return item["duedate"] or ""'),
    (R, "an item with no created date is ranked first on created", '            return created_utc(item["created"]) or NEVER', '            return created_utc(item["created"]) or ""'),
    (R, "a priority name the site does not list is not reported as missing", '        elif item["priority"] not in self.priorities:\n            gone.append(', '        elif False:\n            gone.append('),
    # the order
    (R, "priorities are ordered by the alphabet", '            return self.priorities.index(item["priority"]) if item["priority"] in self.priorities else len(self.priorities)', '            return item["priority"] or "zzz"'),
    (R, "the item that blocks the FEWEST comes first", '            return -len(self.waiters(key))', '            return len(self.waiters(key))'),
    (R, "a done item counts as waiting", 'if other["key"] != key and other["status"]["category"] != "done" and any(', 'if other["key"] != key and any('),
    (R, "waiters named only in the other item's record are not counted", '                waiting.add(other["key"])', '                pass'),
    (R, "keys are ordered as text, so DEMO-12 comes before DEMO-2", '    return project, int(number), key', '    return project, number, key'),
    (R, "created is compared as text, whatever its offset", '            return created_utc(item["created"]) or NEVER', '            return item["created"] or NEVER'),
    (R, "the rule due-first is the same as priority-first", '"due-first": ("due", "priority", "waiters", "created", "key")', '"due-first": ("priority", "due", "waiters", "created", "key")'),
    (R, "a reason is written without naming its field", '            return "`priority` is `%s`, number %d of the site\'s %d"', '            return "priority is `%s`, number %d of the site\'s %d"'),
    # the clock and the files
    (R, "with no clock value, a made-up one is used", '        raise Stopped("--now is the clock value, as', '        return datetime.datetime(2026, 12, 1)\n        raise Stopped("--now is the clock value, as'),
    (R, "a clock value earlier than a copy is accepted", '            if datetime.datetime.strptime(item["copied_at"], "%Y-%m-%dT%H:%M:%SZ") > now:', '            if False:'),
    (R, "the recommendation may be written over the records file", '        if os.path.abspath(args.out) == os.path.abspath(args.records):', '        if False:'),
    (R, "records holding one key twice are accepted", '              and len(set(i["key"] for i in items)) == len(items))', '              )'),
    # the copy
    (S, "the copy can send something other than a read", 'urllib.request.Request(url, method="GET")', 'urllib.request.Request(url, method="POST")'),
    (S, "titles are asked for", 'FIELDS = "status,priority,assignee,duedate,created,updated,issuelinks,issuetype"', 'FIELDS = "summary,status,priority,assignee,duedate,created,updated,issuelinks,issuetype"'),
    (S, "the account id of whoever has an item is kept", '        who = "me" if assignee["accountId"] == me else "someone else"', '        who = assignee["accountId"]'),
    (S, "'me' and 'someone else' are exchanged", '        who = "me" if assignee["accountId"] == me else "someone else"', '        who = "someone else" if assignee["accountId"] == me else "me"'),
    (S, "a link's source and target are exchanged", '        end = "source" if out is not None else "target"', '        end = "target" if out is not None else "source"'),
    (S, "a link's phrase is the other item's", '        phrase = word(kind.get("outward") if out is not None else kind.get("inward"))', '        phrase = word(kind.get("inward") if out is not None else kind.get("outward"))'),
    (S, "only the first page of a long answer is read", '        token = body.get("nextPageToken")\n        if not token:', '        token = None\n        if not token:'),
    (S, "an answer that says there is more is taken as whole", '            if body.get("isLast") is False:', '            if False:'),
    (S, "a copy that is not whole is written", '    elif len(records) != count_before:', '    elif False:'),
    (S, "a refresh throws the other items away", '        records += [item for item in kept["items"] if item["key"] not in dropped and item["id"] not in fresh_ids]', '        pass'),
    (S, "a refresh keeps an item Jira no longer returns", '        dropped = set(gone) | set(old for old, _ in moved)', '        dropped = set(old for old, _ in moved)'),
    (S, "a refresh keeps an item Jira now returns under another key", '        dropped = set(gone) | set(old for old, _ in moved)', '        dropped = set(gone)'),
    (S, "an item answered under another key is copied as if it were the one asked for", '            elif issue.get("key") != key:', '            elif False:'),
    (S, "a refresh keeps the old copy beside the new one", ' and item["id"] not in fresh_ids]', ']'),
    (S, "a refresh does not say what else has changed in Jira", "        drifted = sorted((k for k in have if k in listed_after and listed_after[k] != have[k]), key=key_order)", "        drifted = []"),
    (S, "times keep the site's own offset", '    stamps = {name: in_utc(fields.get(name)) for name in ("created", "updated")}', '    stamps = {name: fields.get(name) for name in ("created", "updated")}'),
    (S, "names the site chose are copied as they are", '    return SAFE.sub("?", UNSEEN.sub("?", value))[:limit].strip() or None if isinstance(value, str) and value.strip() else None', '    return value[:limit] if isinstance(value, str) and value.strip() else None'),
    (S, "what the output says about the requests is assumed, not read back", '        return status, headers, parsed, request.get_method(), request.data is not None', '        return status, headers, parsed, "GET", False'),
    (S, "a request with a body still counts as a read", '        return all(method.startswith("GET") and body is False for method, _, body in self.sent)', '        return all(method.startswith("GET") for method, _, body in self.sent)'),
    (S, "an empty page that says there is more is followed for ever", '        if isinstance(page, list) and not page and body.get("nextPageToken"):\n            raise Refused(', '        if False:\n            raise Refused('),
    (S, "the site's link types are not copied", '"priorities": priorities, "link_types": link_types, "items": records,', '"priorities": priorities, "items": records,'),
    (S, "a refresh may name an item of another project", '        if any(key.rsplit("-", 1)[0] != project["key"] for key in refresh):', '        if False:'),
    (S, "the test clock is accepted against a real Jira", '            if args.source != "fake":\n                raise Refused("--pretend-now', '            if False:\n                raise Refused("--pretend-now'),
    (S, "a change during the copy is not reported", '    if before == after:\n        say("The two are the same', '    if True:\n        say("The two are the same'),
    (S, "the saved log keeps the site's address", '        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept', '        pass'),
    (S, "the time of the copy ignores the clock it was given", '    copied_at = stamp(clock())', '    copied_at = stamp(now_utc())'),
    (S, "an item whose links cannot be read is copied as having none", '    if not isinstance(listed, list):\n        raise Refused("Jira did not list the links', '    if not isinstance(listed, list):\n        listed = []\n    if False:\n        raise Refused("Jira did not list the links'),
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-m", "unittest", "tests.test_next_work"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    sources = {}
    for name in (R, S):
        with open(os.path.join(SKILL, name), encoding="utf-8") as f:
            sources[name] = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-next-work. jira-next-work, attempt jira-attempt-017",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of rank.py or sync.py, in a temporary folder,",
             "and the tests are run against the copy, with the fake Jira. CAUGHT means at least one test failed. The real skill is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "skill")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        passed, said = run_tests(work)
        lines.append("First, with no bug planted, the tests against the copy: %s" % said)
        if not passed:
            lines.append("THE TESTS DO NOT PASS WITHOUT A BUG, so nothing below would mean anything. Stopped.")
            problems.append("the tests fail with no bug planted")
        else:
            lines.append("")
            for number, (name, what, old, new) in enumerate(BUGS, 1):
                source = sources[name]
                if source.count(old) != 1:
                    lines.append("%2d. NOT PLANTED  %s: the text to change was found %d times in %s, not once" % (number, what, source.count(old), name))
                    problems.append("bug %d could not be planted" % number)
                    continue
                with open(os.path.join(work, name), "w", encoding="utf-8") as f:
                    f.write(source.replace(old, new))
                passed, said = run_tests(work)
                with open(os.path.join(work, name), "w", encoding="utf-8") as f:
                    f.write(source)
                lines.append("%2d. %-7s %s: %s" % (number, "MISSED" if passed else "CAUGHT", name, what))
                lines.append("            %s" % said)
                if passed:
                    missed.append(what)
            passed, said = run_tests(work)
            lines += ["", "Last, with the copy put back as it was: %s" % said]
            if not passed:
                problems.append("the tests fail after the copy was put back")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    same = True
    for name in (R, S):
        with open(os.path.join(SKILL, name), encoding="utf-8") as f:
            same = same and f.read() == sources[name]
    unchanged = git_state() == before
    lines.append("The real skill is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    lines += ["", "NOT PLANTED, because no test can tell: leaving the key out of the sort. The items are sorted by key before they are",
              "  ranked, and the sort keeps equal items in the order it found them, so the key decides ties either way."]
    result = "RESULT: %d OF %d PLANTED BUGS CAUGHT." % (len(BUGS) - len(missed) - sum(1 for p in problems if "could not be planted" in p), len(BUGS)) \
        + ("" if not missed and not problems else " NOT ALL: " + "; ".join(missed + problems))
    lines += ["", result]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(result)
    for line in lines:
        if "MISSED" in line or "NOT PLANTED " in line:
            print(line)
    return 0 if not missed and not problems else 1


if __name__ == "__main__":
    sys.exit(main())

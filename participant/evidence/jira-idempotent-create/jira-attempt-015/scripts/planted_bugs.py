#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-idempotent-create/create_once.py and runs the tests
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-idempotent-create")
LIMIT = 120

BUGS = [
    # the key
    ("the key is made new at every preview", "    if not os.path.exists(path):\n        if not make:", "    if make or not os.path.exists(path):\n        if not make:"),
    ("the key is worked out from the title, so an edit changes it", "KEY_PREFIX + random_source.token_hex(8)", 'KEY_PREFIX + sha_of(draft["summary"])[:16]'),
    ("the record with the key is not saved when it is made", '''"not_found": [], "issue": None}
        save_json(path, record)''', '''"not_found": [], "issue": None}'''),
    ("the key is not sent to Jira", '"summary": summary, "labels": [key]}}', '"summary": summary, "labels": []}}'),
    # write-ahead
    ("the record is not marked 'sending' before the request goes", '''    record["status"], record["not_found"] = "sending", []
    save_json(record_file, record)''', '''    record["status"], record["not_found"] = "sending", []'''),
    ("a run that finds an unknown outcome previews anyway", '    if record["status"] in ("sending", "uncertain"):\n        last = record["attempts"][-1]\n        raise Refused("a request', '    if record["status"] in ("uncertain",):\n        last = record["attempts"][-1]\n        raise Refused("a request'),
    ("an unknown outcome does not stop a preview or a confirmation at all", '    if record["status"] in ("sending", "uncertain"):\n        last = record["attempts"][-1]\n        raise Refused("a request', '    if False:\n        last = record["attempts"][-1]\n        raise Refused("a request'),
    ("a task already recorded is created again on confirmation", '''    if record["status"] == "linked":
        raise Refused("this draft's task already exists''', '''    if False:
        raise Refused("this draft's task already exists'''),
    # no answer
    ("no answer is recorded as nothing written", '''stamp(now_utc())
        record["status"] = "uncertain"''', '''stamp(now_utc())
        record["status"] = "new"'''),
    ("a write with no answer is sent a second time", '''    except (OSError, TimeoutError) as err:
        attempt["outcome"], attempt["ended_at"]''', '''    except (OSError, TimeoutError) as err:
        try:
            conn.post_issue(proposal["project_id"], proposal["type_id"], draft["summary"], record["key"])
        except Exception:
            pass
        attempt["outcome"], attempt["ended_at"]'''),
    ("a server error is taken to mean nothing was written", "REFUSALS = (400, 401, 403, 404)", "REFUSALS = (400, 401, 403, 404, 429, 500, 502, 503)"),
    ("a refusal is believed without a search for the key", "        if status in REFUSALS and found == []:", "        if status in REFUSALS:"),
    ("a refusal is believed when the search after it failed", "        if status in REFUSALS and found == []:", "        if status in REFUSALS and not found:"),
    ("the new issue is not recorded until after it is read back", '''    save_json(record_file, record)       # kept at once, so that the new issue's id is not lost''', '''    pass'''),
    # resolve
    ("one empty search that counts is enough to release the record", "    if len(counted) >= 2 and parse(counted[-1]) - parse(counted[0]) >= datetime.timedelta(seconds=GAP_SECONDS):", "    if len(counted) >= 1:"),
    ("two empty searches release the record however close together", "    if len(counted) >= 2 and parse(counted[-1]) - parse(counted[0]) >= datetime.timedelta(seconds=GAP_SECONDS):", "    if len(counted) >= 2:"),
    ("an empty search counts however soon after the request", "    counted = [moment for moment in record[\"not_found\"] if parse(moment) >= counts_from]", "    counted = list(record[\"not_found\"])"),
    ("the wait is zero seconds", "WAIT_SECONDS = 60      #", "WAIT_SECONDS = 0       #"),
    ("a killed run's request is taken to have ended the moment it was sent", "parse(last[\"sent_at\"]) + datetime.timedelta(seconds=TIMEOUT_SECONDS)\n    counts_from", "parse(last[\"sent_at\"])\n    counts_from"),
    ("the time the request ended is ignored, and the wait counted from when it was sent", "    ended = parse(last[\"ended_at\"]) if last.get(\"ended_at\") else parse(last[\"sent_at\"]) + datetime.timedelta(seconds=TIMEOUT_SECONDS)", "    ended = parse(last[\"sent_at\"])"),
    ("the test clock is accepted against a real Jira", "    if args.pretend_seconds_later and args.source != \"fake\":", "    if False:"),
    ("a clock that has gone backwards is not noticed", "    if any(parse(earlier) > now for earlier in record[\"not_found\"] + [last[\"sent_at\"]]):", "    if False:"),
    ("an empty answer is believed without asking whether the project can still be seen", "        if not found and last:\n            can_be_seen(conn, last[\"project_id\"])", "        pass"),
    ("an empty answer is believed when Jira no longer says the identity may see the project", "(found.get(\"BROWSE_PROJECTS\") or {}).get(\"havePermission\") is not True:", "False:"),
    ("an empty answer is believed when a search of the project returns no issue at all", "    if not isinstance(issues, list) or not issues:\n        raise SearchFailed(\"an empty answer cannot be believed: a search", "    if False:\n        raise SearchFailed(\"an empty answer cannot be believed: a search"),
    ("two runs can hold the claim on one draft at once", "os.O_CREAT | os.O_EXCL | os.O_WRONLY", "os.O_CREAT | os.O_WRONLY"),
    ("a claim held by a running run is taken over at once", "            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):", "            if False:"),
    ("a claim left by a killed run is never given up", "            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):", "            if True:"),
    ("a confirmation keeps its claim after it ends", "        try:\n            os.remove(claim)\n        except OSError:\n            pass", "        pass"),
    ("the record is read before the claim is taken and not again", "    record_file, record, _ = load_record(args.state, draft, make=False)     # read AFTER the claim, so it is what stands now\n    refuse_if_unknown(record)", "    record_file, record, _ = load_record(args.state, draft, make=False)     # read AFTER the claim, so it is what stands now"),
    ("another draft with the same file name shares the record", "    if record.get(\"folder\") != draft[\"folder\"]:", "    if False:"),
    ("check says 'found by its key' when the search did not find it", "    if ok and by_key == \"yes\":", "    if ok:"),
    ("a search that is behind just after the write fails the write", "    if not ok or by_key == \"many\":", "    if not ok or by_key != \"yes\":"),
    ("resolve records an issue with the key that is not a task", " or item[\"type_id\"] != last[\"type_id\"]:", ":"),
    ("the interrupted run does not say what Jira answered", "    say(\"The request was sent, and Jira answered %d.\" % status)\n", ""),
    ("Jira's own words about a refusal are saved in the log", ", \"Jira's own words were shown on screen and are not saved: %d characters.\" % len(words))", ")"),
    ("a real write does not need a terminal", "            if writes and not person_present(sys.stdin):", "            if False:"),
    ("the live connection is always given a way to write", "            conn, secrets = make_live(writes)", "            conn, secrets = make_live(True)"),
    ("a failed search is counted as an empty one", '''        raise NeedsLooking("the search failed, so this run cannot say whether the task exists")''', '''        found = []'''),
    ("a failed search changes the record", '''        say("THE SEARCH FOR THE KEY FAILED: %s." % failure)''', '''        record["status"] = "uncertain"
        save_json(record_file, record)
        say("THE SEARCH FOR THE KEY FAILED: %s." % failure)'''),
    ("resolve records the first of several issues carrying the key", "    if len(found) > 1:\n        say(\"MORE THAN ONE", "    if False:\n        say(\"MORE THAN ONE"),
    ("resolve records an issue found in another project", '        if one["project_id"] != last["project_id"]:', "        if False:"),
    ("resolve records an issue when nothing was ever sent", "        if not last:\n            requests_line(conn)", "        if False:\n            requests_line(conn)"),
    ("resolve finds the issue and does not record it", '''        record["status"] = "linked"
        save_json(record_file, record)
        say("FOUND BY ITS KEY''', '''        record["status"] = "linked"
        say("FOUND BY ITS KEY'''),
    ("resolve is given a way to write", 'writes = args.command == "confirm" ', 'writes = args.command in ("confirm", "resolve") '),
    # the search
    ("a search answered with an error is read as empty", '''    if status != 200:
        raise SearchFailed("Jira answered %d" % status)''', '''    if status != 200:
        return []'''),
    ("a search with no answer is read as empty", '''        raise SearchFailed("no answer came back (%s)" % type(getattr(err, "reason", err)).__name__)''', '''        return []'''),
    ("a search answer that is not a list of issues is read as empty", '''        raise SearchFailed("Jira's answer was not a list of issues")''', '''        return []'''),
    ("a search answer that was cut short is accepted", '''    if body.get("nextPageToken") or body.get("isLast") is False or len(issues) >= limit:''', '''    if False:'''),
    ("a full page of results is accepted as the whole answer", ''' or len(issues) >= limit:''', ''':'''),
    ("an issue returned without the key among its labels is accepted", '''        if not isinstance(labels, list) or key not in labels or not isinstance(project, dict)''', '''        if not isinstance(labels, list) or not isinstance(project, dict)'''),
    # preview and confirm
    ("a preview is issued when the key search fails", '''        raise Refused("THE SEARCH FOR THE KEY FAILED (%s). The duplicate check cannot be made, so no preview is issued" % failure)''', '''        keyed = []'''),
    ("a fingerprint is issued when an issue already carries the key", "    if keyed:\n        say(\"An issue already carries", "    if False:\n        say(\"An issue already carries"),
    ("the write goes ahead when the search just before it fails", '''        raise Refused("THE SEARCH FOR THE KEY FAILED just before the write (%s). Whether the task already exists cannot be told, so nothing is sent" % failure)''', '''        keyed = []'''),
    ("the write goes ahead when an issue carries the key by then", "    if keyed:\n        moved.append", "    if False:\n        moved.append"),
    ("a same-titled issue that appeared after the preview is ignored", '''    if (None if titled is None else sorted(i["id"] for i in titled)) != before["titled"]:''', '''    if False:'''),
    ("the title check calls a longer title the same title", '''if same_title(i["fields"].get("summary"), summary)]''', ''']'''),
    ("a missing fingerprint is not refused", '''    if not code:
        raise Refused("no confirmation was given. A confirmation names''', '''    if False:
        raise Refused("no confirmation was given. A confirmation names'''),
    ("a missing name is not refused", '''    if not name:
        raise Refused''', '''    if False:
        raise Refused'''),
    ("a changed title is not noticed", '''("the title is not the title the preview showed", "summary"), ''', ''''''),
    ("a rewritten draft file is not noticed", '''("the draft is not the file the preview showed", "source_sha"),''', ''''''),
    ("a changed allowlist is not noticed", '''("the allowlist file is not the one the preview used", "allowlist")''', ''''''),
    ("a preview never expires", "    if age > datetime.timedelta(minutes=LIMIT_MINUTES):", "    if False:"),
    ("a preview expires a minute early", "    if age > datetime.timedelta(minutes=LIMIT_MINUTES):", "    if age > datetime.timedelta(minutes=LIMIT_MINUTES - 1):"),
    ("the allowlist is not consulted", "    if (site, project[\"id\"]) not in allowed:", "    if False:"),
    ("the allowlist is checked by project id alone, whatever the site", "    if (site, project[\"id\"]) not in allowed:", "    if project[\"id\"] not in [p for _, p in allowed]:"),
    ("the permission check is not acted on", '''    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:''', '''    if False:'''),
    ("an altered saved preview is accepted", '''    if genuine != saved.get("fingerprint") or genuine[:12] != code:''', '''    if False:'''),
    ("a preview from before an earlier attempt can be confirmed", ''' or before["attempt"] != len(record["attempts"]) + 1:''', ''':'''),
    ("a preview made against another site can be confirmed", '''    if site_fingerprint(conn.host) != before["site"]:''', '''    if False:'''),
    ("every command is given a way to write", 'writes = args.command == "confirm" ', 'writes = True '),
    ("the live connection sends any body it is given", '''        if (path != WRITE_PATH or params or set(body) != {"fields"} or set(fields) != {"project", "issuetype", "summary", "labels"}
                or not isinstance(labels, list) or len(labels) != 1 or not isinstance(labels[0], str) or not KEY.fullmatch(labels[0])):''', '''        if False:'''),
    ("the live connection accepts a label that is not the key", " or not KEY.fullmatch(labels[0])):", "):"),
    ("a title that looks like it holds a secret is sent", '''    for what, pattern in SECRETS:
        if pattern.search(text):''', '''    for what, pattern in SECRETS:
        if False:'''),
    # check
    ("a removed label is not noticed by check", '''    ok = key in item["labels"] and item["project_id"] == last["project_id"]''', '''    ok = item["project_id"] == last["project_id"]'''),
    ("a recorded task that Jira no longer returns is treated as fine", '''"NOTHING IS CREATED IN ITS PLACE. Whether to create it again is for a person to decide."], False, "none"''', '''"NOTHING IS CREATED IN ITS PLACE. Whether to create it again is for a person to decide."], True, "none"'''),
    ("the saved log keeps the site's address", '''        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept''', '''        pass'''),
    ("the interruption after sending never happens", '''    interrupt(args, "after-send")''', '''    pass'''),
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-m", "unittest", "tests.test_create_once"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "create_once.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-idempotent-create/create_once.py. jira-idempotent-create, attempt jira-attempt-015",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the skill, in a temporary folder, and the",
             "tests are run against the copy, with the fake Jira. CAUGHT means at least one test failed. The real skill is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "skill")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        copy = os.path.join(work, "create_once.py")
        passed, said = run_tests(work)
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
    with open(os.path.join(SKILL, "create_once.py"), encoding="utf-8") as f:
        same = f.read() == source
    unchanged = git_state() == before
    lines.append("The real skill is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    lines += ["", "NOT PLANTED, because no test can tell: three places where the skill checks the same thing twice.",
              "  Two issues carrying the key after a write are reported by the read-back, and again by the line that ends the run.",
              "  A used preview is refused by its own 'used' mark, and also because the draft's record has moved on to a later attempt.",
              "  The saved result record has the site's address taken out, and its lines are also built without the address.",
              "  Removing either check of a pair alone changes nothing a test can see."]
    result = "RESULT: %d OF %d PLANTED BUGS CAUGHT." % (len(BUGS) - len(missed) - sum(1 for p in problems if "could not be planted" in p), len(BUGS)) \
        + ("" if not missed and not problems else " NOT ALL: " + "; ".join(missed + problems))
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

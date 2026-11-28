#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-transition-status/transition.py and runs the tests against
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-transition-status")
LIMIT = 120

BUGS = [
    # the allowed moves are read from the workflow
    ("a move Jira does not offer is previewed anyway, with a guessed id", "    if not leading:\n        offered =", "    if False:\n        offered ="),
    ("a status name is matched without regard to capitals", "    leading = [move for move in moves if move[\"to\"][\"name\"] == request[\"to\"]]", "    leading = [move for move in moves if move[\"to\"][\"name\"].lower() == request[\"to\"].lower()]"),
    ("a move Jira marks as not available is offered", "        if raw.get(\"isAvailable\") is False:\n            continue\n", ""),
    ("two moves to one status: the first is taken", "    if len(leading) > 1:", "    if False:"),
    ("a list that names one move twice is accepted", "    if len(set(move[\"id\"] for move in moves)) != len(moves):", "    if False:"),
    ("a field that does not say whether it is required is taken as optional", "isinstance(field.get(\"required\"), bool) for name, field in fields.items())):", "True for name, field in fields.items())):"),
    # refused before the preview
    ("a move with a required field is previewed", "    if move[\"required\"]:\n        return False,", "    if False:\n        return False,"),
    ("closing an item with an open subtask is previewed: the quest's scenario", "        if still_open:\n            return False,", "        if False:\n            return False,"),
    ("a subtask whose status cannot be read counts as not open", "        if not item[\"subtasks_listed\"] or unread:", "        if False:"),
    ("an open subtask stops every move, not only one to a done status", "    if move[\"to\"][\"category\"] == \"done\":\n        still_open, unread = open_subtasks(item)", "    if True:\n        still_open, unread = open_subtasks(item)"),
    ("a subtask that is in progress counts as done", "s[\"status\"][\"category\"] != \"done\"],", "s[\"status\"][\"category\"] == \"new\"],"),
    ("the tool's judgement of a move is not asked", "    if not supported:\n        raise Refused(\"THIS WORKFLOW DOES NOT MAKE THIS MOVE.", "    if False:\n        raise Refused(\"THIS WORKFLOW DOES NOT MAKE THIS MOVE."),
    ("an item that already has the status is given a preview to confirm", "    if item[\"status\"][\"name\"] == request[\"to\"]:\n        proposal.update(action=\"nothing\"", "    if False:\n        proposal.update(action=\"nothing\""),
    ("a refused preview is saved anyway", "    request = read_request(args.request)\n    proposal, item = build_proposal(conn, request, args.allowlist)\n    total_before", "    request = read_request(args.request)\n    save_json(os.path.join(args.state, \"previews\", \"early.json\"), {})\n    proposal, item = build_proposal(conn, request, args.allowlist)\n    total_before"),
    # the allowlist and permission
    ("a project that is not on the allowlist is written to", "    if (site, item[\"project_id\"]) not in allowed:", "    if False:"),
    ("the allowlist is matched by project only, on any site", "    if (site, item[\"project_id\"]) not in allowed:", "    if item[\"project_id\"] not in [p for _, p in allowed]:"),
    ("an allowlist entry that is not a fingerprint and a project id is accepted", "        if not (isinstance(site, str) and re.fullmatch(r\"[0-9a-f]{16}\", site) and ident(project)):", "        if False:"),
    ("the permission check is not acted on", "    if not all(permissions.values()):", "    if False:"),
    ("a permission Jira does not mention counts as granted", "found[name].get(\"havePermission\") is True for name in names}", "found[name].get(\"havePermission\") is not False for name in names}"),
    # the preview
    ("the preview command is given a way to write", "    writes = args.command == \"confirm\"       #", "    writes = args.command in (\"confirm\", \"preview\")       #"),
    ("the preview is made from one look at Jira", "    if after != before or canonical(again) != canonical(proposal):", "    if False:"),
    ("the snapshot leaves out the item's status", "item[\"updated\"], item[\"status\"][\"id\"], item[\"resolution\"],", "item[\"updated\"], item[\"resolution\"],"),
    ("the snapshot leaves out the number of history entries", "for s in item[\"subtasks\"]], history_total])", "for s in item[\"subtasks\"]]])"),
    ("the item's title is saved", "    say(\"            | %s\" % item[\"title\"], \"            | [the title was shown on screen and is not saved: %d characters]\" % len(item[\"title\"]))", "    say(\"            | %s\" % item[\"title\"])"),
    ("the site's address is left in the saved output", "        kept = kept.replace(\"https://\" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept", "        kept = kept"),
    ("optional fields are not named in the preview", "(\", \".join(proposal[\"not_sent\"]) or \"none\"))", "\"none\")"),
    # the confirmation
    ("a write with no fingerprint: the newest preview is taken", "    if not code:\n        raise Refused(\"no confirmation was given. A confirmation names", "    if not code:\n        code = sorted(os.listdir(os.path.join(args.state, \"previews\")))[-1][:12]\n    if False:\n        raise Refused(\"no confirmation was given. A confirmation names"),
    ("a confirmation with no name is accepted", "    if not name:\n        raise Refused(\"no confirmation was given. A confirmation gives the name", "    if False:\n        raise Refused(\"no confirmation was given. A confirmation gives the name"),
    ("a used preview can be confirmed again", "    if status != \"open\":", "    if False:"),
    ("a preview never expires", "    if age > datetime.timedelta(minutes=LIMIT_MINUTES):", "    if False:"),
    ("a preview exactly at the limit is too old", "    if age > datetime.timedelta(minutes=LIMIT_MINUTES):", "    if age >= datetime.timedelta(minutes=LIMIT_MINUTES):"),
    ("the limit is 60 minutes", "LIMIT_MINUTES = 15", "LIMIT_MINUTES = 60"),
    ("the test clock is not used", "    now = confirmed + datetime.timedelta(minutes=args.pretend_minutes_later or 0)", "    now = confirmed"),
    ("a preview dated in the future is accepted", "    if age < datetime.timedelta(0):", "    if False:"),
    ("an altered saved preview is confirmed", "    if genuine != saved.get(\"fingerprint\") or genuine[:12] != code:", "    if False:"),
    ("the fingerprint does not cover the time the preview was made", "    return sha_of(canonical({\"proposal\": proposal, \"made_at\": made_at}))", "    return sha_of(canonical({\"proposal\": proposal}))"),
    ("a preview made against another site is confirmed", "    if site_fingerprint(conn.host) != before[\"site\"]:", "    if False:"),
    ("a preview made for another request file is confirmed", "    if before.get(\"request\") != request[\"name\"]:", "    if False:"),
    ("a request file changed since the preview is confirmed", "    if (before[\"source\"], before[\"source_sha\"]) != (request[\"source\"], request[\"source_sha\"]):", "    if False:"),
    ("what Jira holds differing from the preview is not looked for", "    if differs:\n        raise Refused(\"the change is not the one that was previewed: %s. Make", "    if False:\n        raise Refused(\"the change is not the one that was previewed: %s. Make"),
    ("another allowlist than the preview used is accepted", "    if before[\"allowlist\"] != now[\"allowlist\"]:", "    if False:"),
    ("a move with other fields than the preview showed is sent", "    if (before[\"move\"], before[\"to\"], before[\"not_sent\"]) != (now[\"move\"], now[\"to\"], now[\"not_sent\"]):", "    if False:"),
    ("two runs may confirm one request at once", "            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):", "            if False:"),
    ("a run releases another run's claim", "    if holds(claim):            # never another run's", "    if True:            # never another run's"),
    # running it again
    ("an item that already has the status is moved again where Jira allows", "    if item[\"status\"][\"id\"] == end[\"id\"] and item[\"status\"][\"id\"] != start[\"id\"]:", "    if False:"),
    ("a preview found not needed is left open", "        saved[\"state\"] = \"not needed: the item already had the status\"\n        save_json(preview_file, saved)\n", ""),
    ("an item moved elsewhere since the preview is not noticed at the first look", "    if item[\"status\"][\"id\"] != start[\"id\"]:\n        raise Refused(\"THE ITEM HAS BEEN MOVED SINCE THE PREVIEW.", "    if False:\n        raise Refused(\"THE ITEM HAS BEEN MOVED SINCE THE PREVIEW."),
    ("the preview is not marked as used before the write", "    saved[\"state\"] = \"writing\"\n    save_json(preview_file, saved)\n", ""),
    # the write and the read back
    ("the status read back is not compared with the one intended", "    moved, unmoved = item[\"status\"][\"id\"] == end[\"id\"], item[\"status\"][\"id\"] == start[\"id\"]", "    moved, unmoved = True, item[\"status\"][\"id\"] == start[\"id\"]"),
    ("the status is not read back: the tool believes Jira's answer", "    accepted = answered in (200, 204)\n    item = read_item(conn, issue[\"id\"], issue[\"key\"])", "    accepted = answered in (200, 204)\n    item = dict(item, status=end) if accepted else read_item(conn, issue[\"id\"], issue[\"key\"])"),
    ("a write Jira accepted that does not show yet is sent again", "        pause()\n        item = read_item(conn, issue[\"id\"], issue[\"key\"])", "        pause()\n        conn.post_move(issue[\"id\"], move[\"id\"])\n        item = read_item(conn, issue[\"id\"], issue[\"key\"])"),
    ("the item is read only once after the write", "    for _ in range(READ_AGAIN):\n        if not accepted", "    for _ in range(0):\n        if not accepted"),
    ("a server error is taken as a refusal", "REFUSALS = (400, 401, 403, 404, 409)", "REFUSALS = (400, 401, 403, 404, 409, 500)"),
    ("a refusal is believed without looking at the item", "        if answered in REFUSALS and unmoved:", "        if answered in REFUSALS:"),
    ("what Jira said in refusing is repeated", "so it was not moved. What Jira said in \"\n                             \"refusing is not repeated here\" % (answered, issue[\"key\"], quoted(start[\"name\"])))", "so it was not moved. What Jira said in \"\n                             \"refusing is not repeated here %s\" % (answered, issue[\"key\"], quoted(start[\"name\"]), body))"),
    ("the body sent holds more than the move's id", "        return self._post(path, None, {\"transition\": {\"id\": move_id}})", "        return self._post(path, None, {\"transition\": {\"id\": move_id}, \"fields\": {}})"),
    ("an empty resolution after a move to done is not reported", "bool(item[\"resolution\"])))\n    elif", "True))\n    elif"),
    ("a resolution still set after a move out of done is not reported", "quoted(item[\"resolution\"])), not item[\"resolution\"]))", "quoted(item[\"resolution\"])), True))"),
    ("the identifier is any new history entry, whatever it records", "if entry[\"id\"] not in known and int(entry[\"id\"]) > newest and (start[\"id\"], end[\"id\"]) in entry[\"moves\"]]", "if entry[\"id\"] not in known]"),
    ("the identifier may be an older entry of the same move", "        return [entry for entry in entries_after if entry[\"id\"] not in known and int(entry[\"id\"]) > newest and ", "        return [entry for entry in entries_after[-1:] if "),
    ("a failed read back still ends with ALL DONE", "    if not all(ok for _, ok in checks):\n        problem =", "    if False:\n        problem ="),
    ("a read that fails after the write is called a refusal", "            if self.posted():\n                raise NeedsLooking(\"after a write was sent, a read failed: %s\" % reason)", "            if False:\n                raise NeedsLooking(\"after a write was sent, a read failed: %s\" % reason)"),
    ("a failure after the write says nothing was written", "            if conn.posted():\n                raise NeedsLooking(\"a write was sent, and the program then failed", "            if False:\n                raise NeedsLooking(\"a write was sent, and the program then failed"),
    # the result record
    ("the result record leaves out who confirmed", "            \"Confirmed by: %s, at %s\" % (result[\"confirmed_by\"], result[\"confirmed_at\"]),", "            \"Confirmed at %s\" % result[\"confirmed_at\"],"),
    ("the result record keeps the site's address", "        PENDING[\"result\"] = (args.result, text.replace(conn.host, SITE_MARK))", "        PENDING[\"result\"] = (args.result, text.replace(SITE_MARK, conn.host))"),
    ("a result record is written for a refused run", "            PENDING.clear()\n            return refused(refusal)\n        except NeedsLooking:", "            PENDING[\"result\"] = (getattr(args, \"result\", None) or os.devnull, \"x\")\n            return refused(refusal)\n        except NeedsLooking:"),
    ("the check command does not compare the status", "    good = item[\"status\"][\"id\"] == end[\"id\"]", "    good = True"),
    # the request, and a real Jira
    ("a request may carry more than an item and a status", "    if not isinstance(data, dict) or set(data) != {\"issue\", \"to\"}:", "    if not isinstance(data, dict) or not set(data) >= {\"issue\", \"to\"}:"),
    ("a name given twice in a file is accepted", "        if names.count(name) > 1:", "        if False:"),
    ("a real write does not need a terminal", "            if writes and not person_present(sys.stdin):", "            if False:"),
    ("the live connection will post anything", "        if not ok:\n            raise Refused(\"the only write this workflow sends is one move", "        if False:\n            raise Refused(\"the only write this workflow sends is one move"),
    ("the live connection will post to an item named by its key", "WRITE_PATH = re.compile(r\"/rest/api/3/issue/[0-9]{1,20}/transitions\")", "WRITE_PATH = re.compile(r\"/rest/api/3/issue/[A-Z0-9-]{1,20}/transitions\")"),
    ("the output is not searched for the credentials", "    if any(secret and secret in text + \"\".join(pending[1] for pending in PENDING.values()) for secret in secrets):", "    if False:"),
    ("only the token is searched for", "    return Connection(get, post if may_write else None, host), [token, email, encoded]", "    return Connection(get, post if may_write else None, host), [token]"),
    ("redirects are followed", "    opener = opener or urllib.request.build_opener(NoRedirect)", "    opener = opener or urllib.request.build_opener()"),
    ("an address with a path or a port, or without https, is accepted", "    if not host or base != \"https://\" + host:", "    if not host:"),
    ("a request may wait for ever", "            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:", "            with opener.open(request) as response:"),
    ("something unforeseen is a crash", "        except Exception as failure:  # nothing may hide", "        except KeyboardInterrupt as failure:  # nothing may hide"),
    # found by the independent readers, or added with the fixes for what they found
    ("done is judged by the status's name", "    if move[\"to\"][\"category\"] == \"done\":\n        still_open, unread = open_subtasks(item)", "    if move[\"to\"][\"name\"] == \"Done\":\n        still_open, unread = open_subtasks(item)"),
    ("a missing list of subtasks counts as no subtasks", "\"subtasks_listed\": isinstance(listed, list),", "\"subtasks_listed\": True,"),
    ("a history of more than 100 entries is read at its start", "    if type(total) is int and total > 100:", "    if False:"),
    ("a refusal raised after the write says nothing was written", "            if conn.posted():\n                raise NeedsLooking(\"a write was sent, and a step after it could not be done", "            if False:\n                raise NeedsLooking(\"a write was sent, and a step after it could not be done"),
    ("the write is not written down before it is sent", "    save_json(written_file, result)        # written down BEFORE the request goes\n", ""),
    ("the check command ignores the history entry", "        good = good and there", "        pass"),
    ("the check command reads any site", "    if site_fingerprint(conn.host) != site:\n        raise Refused(\"this is not the Jira site the move was written to\")", "    if False:\n        raise Refused(\"this is not the Jira site the move was written to\")"),
    ("several new history entries count as one", "\" (found: %d)\" % len(new)), len(new) == 1))", "\" (found: %d)\" % len(new)), True))"),
    ("the last comparison with the preview, of everything, is not made", "    if not said and canonical(before) != canonical(now):", "    if False:"),
    ("a change to the subtasks or the resolution since the preview is not looked for", "    if before[\"subtasks\"] != now[\"subtasks\"] or before[\"resolution_before\"] != now[\"resolution_before\"]:", "    if False:"),
    ("another item behind the same reference is not looked for", "    if before[\"issue\"] != now[\"issue\"]:", "    if False:"),
    ("another status than the preview showed is not looked for", "    if before[\"from\"] != now[\"from\"]:", "    if False:"),
    ("an item that changed and came back since the preview is confirmed", "    if not said and before.get(\"seen\") != now.get(\"seen\"):", "    if False:"),
    ("a status is also matched by a move's name", "    leading = [move for move in moves if move[\"to\"][\"name\"] == request[\"to\"]]", "    leading = [move for move in moves if request[\"to\"] in (move[\"to\"][\"name\"], move[\"name\"])]"),
    ("the confirming name may be long or hold unseen characters", "    if len(name) > 60 or \"@\" in name or UNSEEN.search(name):", "    if \"@\" in name:"),
    ("a resolution that cannot be read counts as none", "    if resolution is not None and not (", "    if False and not ("),
    ("unseen characters in a title are shown as they are", "\" \".join(UNSEEN.sub(\"?\", title).split())[:100]", "\" \".join(title.split())[:100]"),
    ("runs of spaces in a title are kept", "\" \".join(UNSEEN.sub(\"?\", title).split())[:100]", "UNSEEN.sub(\"?\", title)[:100]"),
    ("only 204 counts as accepted", "    accepted = answered in (200, 204)", "    accepted = answered == 204"),
    ("a 401 to the write is not taken as a refusal", "REFUSALS = (400, 401, 403, 404, 409)", "REFUSALS = (400, 403, 404, 409)"),
    ("a saved preview is not tied to its file's name", "    if genuine != saved.get(\"fingerprint\") or genuine[:12] != code:", "    if genuine != saved.get(\"fingerprint\"):"),
    ("the rules call one of two moves to a status supported", "            if supported and twins > 1:", "            if False:"),
    ("the rules take any number of items", "    if not 1 <= len(args.issue) <= MAX_RULES or ", "    if not 1 <= len(args.issue) or "),
    ("the rules say they were read from a real Jira", "% (\"a real Jira\" if args.source == \"live\" else \"the made-up Jira (every item here is made up)\",", "% (\"a real Jira\" if True else \"the made-up Jira (every item here is made up)\","),
    ("the site fingerprint depends on capitals", "    return hashlib.sha256(host.lower().encode(\"utf-8\")).hexdigest()[:16]", "    return hashlib.sha256(host.encode(\"utf-8\")).hexdigest()[:16]"),
    ("a killed run's claim is never cleared", "                os.remove(path)\n            except OSError:\n                pass\n    raise Refused(\"another run took", "                pass\n            except OSError:\n                pass\n    raise Refused(\"another run took"),
    ("only the permission to move is acted on", "    if not all(permissions.values()):", "    if not permissions[\"TRANSITION_ISSUES\"]:"),
    ("the item is read again though the write was not accepted", "        if not accepted or item[\"status\"][\"id\"] != start[\"id\"]:", "        if item[\"status\"][\"id\"] != start[\"id\"]:"),
    ("after Jira refuses, the record of the write still says sending", "            stop(\"Jira refused it (%d) and nothing was written\" % answered)", "            pass"),
    ("the status read back is compared by name", "    moved, unmoved = item[\"status\"][\"id\"] == end[\"id\"],", "    moved, unmoved = item[\"status\"][\"name\"] == end[\"name\"],"),
    ("fields given as nothing count as no fields", "        fields = raw.get(\"fields\", {}) if isinstance(raw, dict) else None", "        fields = (raw.get(\"fields\") or {}) if isinstance(raw, dict) else None"),
    ("a status category that is not a plain word is accepted", "isinstance(key, str) and re.fullmatch(r\"[a-z]{1,20}\", key)):", "isinstance(key, str)):"),
    ("a write that fails in the network, other than by timing out, is a crash", "    except (OSError, TimeoutError) as err:\n        say(\"The write was sent and NO ANSWER", "    except TimeoutError as err:\n        say(\"The write was sent and NO ANSWER"),
    ("the time of the confirmation is the test clock's", "\"confirmed_at\": stamp(confirmed),", "\"confirmed_at\": stamp(now),"),
    ("a missing email address is accepted", "    for name, value in ((\"JIRA_BASE_URL\", base), (\"JIRA_EMAIL\", email), (\"JIRA_API_TOKEN\", token)):", "    for name, value in ((\"JIRA_BASE_URL\", base), (\"JIRA_API_TOKEN\", token)):"),
    ("a move whose fields Jira does not tell is taken to have none", "    if not move.get(\"fields_told\", True):", "    if False:"),
    ("a preview is made though Jira gave no history", "    if history_total is None:", "    if False:"),
    ("an entry older than the newest known may be taken for this move's", " and int(entry[\"id\"]) > newest and ", " and "),
    ("the history is read once after the move", "    for _ in range(READ_AGAIN):\n        if new:", "    for _ in range(0):\n        if new:"),
    ("a stale resolution fails a move between two open statuses", "        same = item[\"resolution\"] == proposal[\"resolution_before\"]", "        same = not item[\"resolution\"]"),
    ("the places files are saved to are not looked at", "        check_places(args)\n", ""),
    ("a file may be saved inside the state folder", "        elif state and (full == state or full.startswith(state + os.sep)):", "        elif False:"),
    ("a stranger's file is written over", "                if not OWN_FILES[kind].match(f.read(200)):", "                if False:"),
    ("a file is written through a link or a second name", "        elif os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and (not os.path.isfile(path) or os.stat(path).st_nlink > 1)):", "        elif os.path.isdir(path):"),
    ("the request or the allowlist may be written over", "        elif any(same_file(path, other) for other in inputs) or any(", "        elif any("),
    ("a refusal for the place of the log is saved in that place", "            args.log = None                 # the refusal", "            pass                 # the refusal"),
    ("output the terminal cannot show is a crash", "    except UnicodeEncodeError:\n        encoding =", "    except ZeroDivisionError:\n        encoding ="),
    ("a terminal that has gone away is a crash", "    except (BrokenPipeError, ValueError):\n        pass", "    except ZeroDivisionError:\n        pass"),
    ("an interruption is a crash with no output", "        except KeyboardInterrupt:\n            if conn.posted():", "        except ZeroDivisionError:\n            if conn.posted():"),
    ("a saved preview that names things in another shape is used", "    if not (isinstance(status, str) and good_record(saved[\"proposal\"]) and saved[\"proposal\"].get(\"action\") == \"move\"):", "    if False:"),
    ("a saved write that names things in another shape is used by the check", "        if not good_record(result) or not (entry is None or ident(entry)) or not isinstance(site, str):", "        if False:"),
    ("a claim dated in the future blocks the request for ever", "            if since is None or since > now_utc():", "            if since is None:"),
    ("names keep the characters that mean something to a page", "    return json.dumps(MARKUP.sub(\"?\", UNSEEN.sub(\"?\", str(text)))[:limit], ensure_ascii=False)", "    return json.dumps(UNSEEN.sub(\"?\", str(text))[:limit], ensure_ascii=False)"),
]

NOT_PLANTED = [
    "A write sent though Jira gave no history just before it: the same run has already been refused for that when it worked the request out again.",
    "The search for credentials not covering the result record or the rules page: both are made from the same text as the output, so a credential in one is in the other.",
    "The first look at confirm reading the item by its key and not its id: a re-keyed item is refused either way.",
    "The bare site name left in a saved log: the tool prints the name only after https://, so both replacements remove the same thing.",
    "The second look at the item, just before the write, taken away: the first look and the comparison with the preview catch the same change, so no test can tell from outside which did.",
    "The claim not checked just before the write (`holds`): a second run is already refused when it tries to make its own claim.",
    "The gap between the last read and the write: it is a stated limit, not a check that could be removed.",
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_transition"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "transition.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-transition-status/transition.py. jira-transition-status, attempt jira-attempt-023",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a fresh copy of the tool's folder, in a temporary folder, and the tests are run",
             "against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "skills", "jira-transition-status")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        copy = os.path.join(work, "transition.py")
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
                shutil.rmtree(work)                 # a fresh copy for every bug: a planted bug may let a test damage the copy's own files
                shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
                with open(copy, "w", encoding="utf-8") as f:
                    f.write(source.replace(old, new))
                passed, said = run_tests(work)
                lines.append("%2d. %-7s %s" % (number, "MISSED" if passed else "CAUGHT", what))
                lines.append("            %s" % said)
                if passed:
                    missed.append(what)
            shutil.rmtree(work)
            shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
            passed, said = run_tests(work)
            lines += ["", "Last, with the copy put back as it was: %s" % said]
            if not passed:
                problems.append("the tests fail after the copy was put back")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    with open(os.path.join(SKILL, "transition.py"), encoding="utf-8") as f:
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

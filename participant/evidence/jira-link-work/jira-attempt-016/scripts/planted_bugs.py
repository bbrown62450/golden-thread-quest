#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-link-work/link_work.py and runs the tests
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-link-work")
LIMIT = 120

BUGS = [
    # direction
    ("the two items are put in Jira's slots the other way round", '"inwardIssue": {"id": source_id}, "outwardIssue": {"id": target_id}}', '"inwardIssue": {"id": target_id}, "outwardIssue": {"id": source_id}}'),
    ("an inward phrase, such as 'is blocked by', is read as if it were the outward one", '    return kind, symmetric, ("outward" if symmetric else found[0][1])', '    return kind, symmetric, "outward"'),
    ("the item named first is always taken as the source", '        source, target = (start, end) if side == "outward" else (end, start)', '        source, target = start, end'),
    ("reading an item, `outwardIssue` is taken to mean the OTHER item is the source", '"source": issue["id"] if out is not None else other["id"],', '"source": other["id"] if out is not None else issue["id"],'),
    ("a link the other way round counts as the same link", '    return there == asked or (want["symmetric"] and there == asked[::-1])', '    return there == asked or there == asked[::-1]'),
    ("a link of another type between the same items counts as the same link", '    if link["type_id"] != want["type"]["id"]:\n        return False\n    there', '    there'),
    ("the opposite link is never recognised", 'def opposite_link(link, want):\n    return not want["symmetric"] and', 'def opposite_link(link, want):\n    return False and'),
    ("a type with one phrase is treated as having a direction", '    symmetric = kind["inward"] == kind["outward"]', '    symmetric = False'),
    ("what an item shows is not compared with the sentence wanted", '        right = bool(held) and held[0]["type_id"] == kind["id"] and (shown ==', '        right = bool(held) or (shown =='),
    ("the link read by its own id is not compared with what was sent", '                   ends == wanted or (want["symmetric"] and ends == wanted[::-1])))', '                   True))'),
    ("a link that reads backwards after the write is not noticed", '        if backwards and (answered is None or answered in (200, 201)):', '        if False:'),
    ("an opposite link is called this workflow's mistake even when Jira refused the write", '        if backwards and (answered is None or answered in (200, 201)):', '        if backwards:'),
    ("the id of a backwards link is not kept in the record", '            entry["link_id"] = backwards[0]\n', ''),
    ("after a backwards link the advice is still to preview again", '    except Backwards as problem:\n        say("")\n        say("A PERSON NEEDS TO LOOK: %s." % problem)\n        return 2\n', ''),
    # which links
    ("any link type the site has may be created", '    if kind["name"] not in ALLOWED_TYPES:', '    if False:'),
    ("Duplicate links may be created", 'ALLOWED_TYPES = ("Blocks", "Relates")', 'ALLOWED_TYPES = ("Blocks", "Relates", "Duplicate")'),
    ("a phrase shared by two link types is accepted", '    if len(kinds) > 1:', '    if False:'),
    # which items
    ("an item may be linked to itself", '        if start["id"] == end["id"]:', '        if False:'),
    ("only the first item is checked against the allowlist and for permission", '        for item in (start, end):\n            if (site,', '        for item in (start,):\n            if (site,'),
    ("the allowlist is not consulted", '            if (site, item["project_id"]) not in allowed:', '            if False:'),
    ("the allowlist is checked by project id alone, whatever the site", '            if (site, item["project_id"]) not in allowed:', '            if item["project_id"] not in [p for _, p in allowed]:'),
    ("the permission check is not acted on", '            if not all(permissions[item["id"]].values()):', '            if False:'),
    # existing links
    ("a link that is already there is created again", '        want["action"] = "exists" if on_source else "create"', '        want["action"] = "create"'),
    ("the opposite link already there is not a conflict", '        if against:', '        if False:'),
    ("two items that disagree about their links are accepted", '        if on_source != on_target:', '        if False:'),
    ("the same link twice in one request is accepted", '            if earlier["type"]["id"] == kind["id"] and {', '            if False and {'),
    ("more than five links are accepted", 'MAX_LINKS = 5', 'MAX_LINKS = 50'),
    # circles
    ("a link that closes a circle is created", '            if leads_back(reader, want, planned):', '            if False:'),
    ("the circle check ignores the other links of the same request", '        onward += [target for kind, source, target in planned if kind == type_id and source == node]', '        pass'),
    ("the circle check follows links of every type", 'if link["type_id"] == type_id and link["source"] == node]', 'if link["source"] == node]'),
    ("the circle check follows links backwards", 'if link["type_id"] == type_id and link["source"] == node]', 'if link["type_id"] == type_id and link["target"] == node]'),
    ("a chain too long to follow is assumed clear", '        if len(seen) > MAX_FOLLOWED:', '        if False:'),
    # confirm
    ("a missing fingerprint is not refused", '    if not code:\n        raise Refused("no confirmation was given. A confirmation names', '    if False:\n        raise Refused("no confirmation was given. A confirmation names'),
    ("a missing name is not refused", '    if not name:\n        raise Refused', '    if False:\n        raise Refused'),
    ("a preview never expires", '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):', '    if False:'),
    ("a preview expires a minute early", '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):', '    if age > datetime.timedelta(minutes=LIMIT_MINUTES - 1):'),
    ("a rewritten request file is not noticed as such", '    if before["source_sha"] != now["source_sha"] or before["source"] != now["source"]:', '    if False:'),
    ("a changed allowlist is not noticed", '    if before["allowlist"] != now["allowlist"]:', '    if False:'),
    ("a reference that now leads to another item is not noticed as such", '        if (old["type"]["id"], old["source"]["id"], old["target"]["id"]) != (new["type"]["id"], new["source"]["id"], new["target"]["id"]):', '        if False:'),
    ("a link that appeared since the preview is not noticed when the request is compared", '        elif old["action"] != new["action"] or old["existing"] != new["existing"]:', '        elif False:'),
    ("the read just before each write is not acted on", '        if new[0] or new[1] or backwards:\n            stop_batch(written_file, result, entry, "not sent")', '        if False:\n            stop_batch(written_file, result, entry, "not sent")'),
    ("an altered saved preview is accepted", '    if genuine != saved.get("fingerprint") or genuine[:12] != code:', '    if False:'),
    ("a used preview can be confirmed again", '    if status != "open":', '    if False:'),
    ("a preview made against another site can be confirmed", '    if site_fingerprint(conn.host) != before["site"]:', '    if False:'),
    ("a preview made for another request file can be confirmed as such", '    if before.get("request") != request["name"]:', '    if False:'),
    ("a change in the site's words for the link type is not noticed", '        elif old["type"] != new["type"]:', '        elif False:'),
    ("an item that moved project just before the write is not noticed", '        if (source["project_id"], target["project_id"]) != (want["source"]["project_id"], want["target"]["project_id"]):', '        if False:'),
    ("a link Jira is slow to show is not read again", '        for _ in range(READ_AGAIN):', '        for _ in range(0):'),
    ("the reads are repeated even when Jira refused or gave no answer", '            if answered not in (200, 201) or new[0] or new[1] or backwards:\n                break', '            if new[0] or new[1] or backwards:\n                break'),
    ("the record is not marked 'sending' before the request goes", '        entry["status"] = "sending"\n        save_json(written_file, result)        # written down BEFORE the request goes', '        entry["status"] = "sending"'),
    # the write and after
    ("a write with no answer is sent a second time", '        except (OSError, TimeoutError) as err:\n            say("  The write was sent and NO ANSWER', '        except (OSError, TimeoutError) as err:\n            try:\n                conn.post_link(want["type"]["id"], want["source"]["id"], want["target"]["id"])\n            except Exception:\n                pass\n            say("  The write was sent and NO ANSWER'),
    ("a server error is taken to mean nothing was written", 'REFUSALS = (400, 401, 403, 404)', 'REFUSALS = (400, 401, 403, 404, 429, 500, 503)'),
    ("a refusal is believed without reading the items back", '            if answered in REFUSALS and not new[0] and not new[1]:', '            if answered in REFUSALS:'),
    ("two new links where one was wanted are not noticed as such", '        if len(new[0]) != 1 or new[0] != new[1]:', '        if not new[0]:'),
    ("the count of links after the write is not checked", 'len(same[0]) == 1 and len(same[1]) == 1))', 'True))'),
    ("check does not report an opposite link", '        if backwards:\n            say("  A LINK THE OPPOSITE WAY ROUND', '        if False:\n            say("  A LINK THE OPPOSITE WAY ROUND'),
    # one run at a time, and who may write
    ("two runs can hold the claim on one request at once", 'os.O_CREAT | os.O_EXCL | os.O_WRONLY', 'os.O_CREAT | os.O_WRONLY'),
    ("a claim held by a running run is taken over at once", '            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):', '            if False:'),
    ("a claim left by a killed run is never given up", '            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):', '            if True:'),
    ("a confirmation keeps its claim after it ends", "    if holds(claim):            # never another run's", "    if False:"),
    ("a confirmation removes another run's claim when it ends", "    if holds(claim):            # never another run's", "    if True:"),
    ("a run whose claim was taken goes on to write", "    if not holds(claim):\n        raise Refused(\"this run's claim", "    if False:\n        raise Refused(\"this run's claim"),
    ("the claim is not renewed before each write", '        renew(claim)\n', ''),
    ("a result record that cannot be saved ends the run with an error", '    try:\n        write_pending()\n    except OSError:', '    try:\n        write_pending()\n    except ZeroDivisionError:'),
    ("every command is given a way to write", 'writes = args.command == "confirm" ', 'writes = True '),
    ("the live connection is always given a way to write", '            conn, secrets = make_live(writes)', '            conn, secrets = make_live(True)'),
    ("a real write does not need a terminal", '            if writes and not person_present(sys.stdin):', '            if False:'),
    ("the live connection sends any body it is given", '        if not ok:\n            raise Refused("the only write this workflow sends', '        if False:\n            raise Refused("the only write this workflow sends'),
    # what is saved
    ("the items' titles are saved in the log", ', "    | [the title was shown on screen and is not saved: %d characters]" % len(items[end["id"]]["title"]))', ')'),
    ("the saved log keeps the site's address", '        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept', '        pass'),
    ("Jira's own words about a refusal are saved in the log", ', "  Jira\'s own words were shown on screen and are not saved: %d characters." % len(words))', ')'),
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-m", "unittest", "tests.test_link_work"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "link_work.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-link-work/link_work.py. jira-link-work, attempt jira-attempt-016",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the skill, in a temporary folder, and the",
             "tests are run against the copy, with the fake Jira. CAUGHT means at least one test failed. The real skill is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "skill")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        copy = os.path.join(work, "link_work.py")
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
    with open(os.path.join(SKILL, "link_work.py"), encoding="utf-8") as f:
        same = f.read() == source
    unchanged = git_state() == before
    lines.append("The real skill is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    lines += ["", "HOW TO READ 'CAUGHT'. A test failed. For some bugs the run was STILL REFUSED, by a second check, and the test failed",
              "  because the refusal gave another reason than the one it looks for. Those show that the first check is the one that",
              "  speaks, and not that the behaviour would have gone wrong without it. They are the bugs about: a missing fingerprint,",
              "  the opposite link, an altered preview, a preview for another site or another request file, a rewritten request,",
              "  a reference that leads elsewhere, a link that appeared since the preview, and two new links where one was wanted.",
              "  Two bugs about Jira's slots are caught by tests that share the fake Jira's own belief about those slots: they show",
              "  the workflow is consistent with the fake, and say nothing about a real Jira."]
    lines += ["", "NOT PLANTED, because no test can tell: a phrase with capitals is refused by the shape a phrase must have, and again",
              "  because it is not, letter for letter, one of the site's phrases. Removing either check alone changes nothing."]
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

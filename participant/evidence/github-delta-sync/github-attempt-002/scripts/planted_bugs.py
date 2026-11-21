#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-delta-sync quest.

Puts one bug at a time into participant/skills/github-delta-sync/sync.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes sync.py while it runs. Do not run a sync at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, "participant", "skills", "github-delta-sync")
TARGET = os.path.join(SKILL, "sync.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The cursor is taken from this machine's clock, not GitHub's (criteria 2 and 3, clock differences)",
     '"private": bool(body.get("private"))}, github_clock(head)', '"private": bool(body.get("private"))}, utc_now()'),
    ("B. With no Date header, this machine's clock is used in its place (clock differences)",
     '    except (KeyError, TypeError, ValueError):\n        raise Stop("GitHub\'s answer carried no usable Date header, so its clock cannot be read. This machine\'s "\n                   "clock is never used in its place")',
     '    except (KeyError, TypeError, ValueError):\n        return utc_now()'),
    ("C. The cursor is saved as soon as the changed issues are listed, before they are fetched: the scenario (criteria 2 and 3)",
     '        fetched, comment_requests = {}, 0\n',
     '        if state["cursor"]:\n            state["cursor"]["time"] = started\n'
     '            write_text(os.path.join(out_dir, "state.json"), json.dumps(state), out_dir)\n        fetched, comment_requests = {}, 0\n'),
    ("D. An issue whose comments cannot be fetched is skipped, and the sync carries on and moves the cursor (criteria 2, 3 and 4)",
     '            comments, requests = read_comments(client, repo, issue)',
     '            try:\n                comments, requests = read_comments(client, repo, issue)\n            except Stop:\n                continue'),
    ("E. The cursor is written before the issues (criterion 2)",
     '    write_text(os.path.join(out_dir, "issues.md"), render_issues(state, notes_before), out_dir)\n'
     '    write_text(os.path.join(out_dir, "state.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\\n", out_dir)  # the cursor\n',
     '    write_text(os.path.join(out_dir, "state.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\\n", out_dir)  # the cursor\n'
     '    write_text(os.path.join(out_dir, "issues.md"), render_issues(state, notes_before), out_dir)\n'),
    ("F. The margin is not applied: a delta asks from the cursor exactly (the hint, criterion 7)",
     '    return (parse(cursor_time) - datetime.timedelta(seconds=margin)).strftime(STAMP)', '    return cursor_time'),
    ("G. The margin is added to the cursor, not taken from it (the hint, criterion 4)",
     '(parse(cursor_time) - datetime.timedelta(seconds=margin))', '(parse(cursor_time) + datetime.timedelta(seconds=margin))'),
    ("H. `since` is not sent, so every issue is fetched at every sync (criterion 1)",
     '        params["since"] = since', '        params["since_"] = since'),
    ("I. A delta reads every issue, ignoring the cursor (criterion 1)",
     '        whole = full or verify or cursor is None', '        whole = True'),
    ("J. Pull requests are kept as issues (criterion 1)",
     'if "pull_request" not in row]', 'if True]'),
    ("K. Reading stops after the first page (criteria 1 and 4)",
     '        if not has_next(head):', '        if True:'),
    ("L. The same page returned again is taken as the end (criterion 1)",
     '            raise Stop("GitHub kept returning the same of %s, so the skill cannot tell whether it has them all" % what)',
     '            return rows, sizes'),
    ("M. A new issue is counted as changed (criterion 5)",
     '        if old is None:\n            found["new"].append(node)', '        if old is None:\n            found["changed"].append((node, []))'),
    ("N. Issues that were not fetched are left out of the unchanged count (criterion 5)",
     '    not_fetched = held_before - len(found["changed"]) - len(found["same"]) - len(gone)', '    not_fetched = 0'),
    ("O. An issue fetched again and found the same is counted as changed (criterion 5)",
     '        elif kept(old) != kept(record):', '        elif True:'),
    ("P. Reading a notes file adds a line to it (criterion 6)",
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()',
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()\n'
     '                with open(path, "a") as f:\n                    f.write("\\n")'),
    ("Q. Writing in the notes folder is no longer refused (criterion 6)",
     '    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:', '    if False:'),
    ("R. The digest does not cover the issues' fields or comments (criterion 7)",
     '    present = sorted((kept(r) for r in issues.values()', '    present = sorted(({"node_id": r["node_id"]} for r in issues.values()'),
    ("S. The digest covers when an issue was fetched, so two copies of the same repository differ (criterion 7)",
     '    present = sorted((kept(r) for r in issues.values()', '    present = sorted((dict(kept(r), at=r.get("last_fetched")) for r in issues.values()'),
    ("T. --verify always says the local copy and a full read are the same (second stretch goal)",
     '        same = digest(state["issues"]) == digest(theirs)', '        same = True'),
    ("U. --verify moves the cursor (criterion 2)",
     '        theirs = {node: dict(record, status="present") for node, record in fetched.items()}',
     '        theirs = {node: dict(record, status="present") for node, record in fetched.items()}\n'
     '        state["cursor"] = {"time": started, "taken_from": CURSOR_SOURCE}\n'
     '        write_text(os.path.join(out_dir, "state.json"), json.dumps(state), out_dir)'),
    ("V. The time a comment was last edited is not kept (criterion 7)",
     '"updated_at": row.get("updated_at")} for row in rows]', '"updated_at": None} for row in rows]'),
    ("W. A deleted issue is not recognised (first stretch goal)",
     '    if status == 410:', '    if status == 4100:'),
    ("X. A transferred issue is not recognised (first stretch goal)",
     '    if now_in != repo or now["node_id"] != old["node_id"]:', '    if False:'),
    ("Y. An issue no longer in the repository is deleted locally (first stretch goal)",
     '        held[node].update(status="gone", since=started, **why)', '        del held[node]'),
    ("Z. A folder holding another repository's issues is synced into (safety)",
     '    if state.get("repo_id") != info["id"]:', '    if False:'),
    ("AA. A folder holding made-up issues may be synced from live GitHub (safety)",
     '    if state.get("source") != source:', '    if False:'),
    ("AB. An issue's body is kept (safety: only the fields needed)",
     '    return {"node_id": row["node_id"], "number": row["number"], "title": str(row.get("title") or ""),',
     '    return {"body": row.get("body"), "node_id": row["node_id"], "number": row["number"], "title": str(row.get("title") or ""),'),
    ("AC. The token is put in the address (safety)",
     '    url = "https://%s%s" % (API_HOST, path)',
     '    url = "https://%s%s?access_token=%s" % (API_HOST, path, os.environ.get("GITHUB_TOKEN"))'),
    ("AD. The request is not a GET (safety)",
     'method="GET"', 'method="POST"'),
    ("AE. A redirect to a host other than GitHub's API is followed (safety)",
     '            if where.scheme != "https" or where.netloc != API_HOST or hops == MAX_REDIRECTS:', '            if hops == MAX_REDIRECTS:'),
    ("AF. A vertical bar in a title is not escaped (safety)",
     '.replace("|", "\\\\|")', ''),
    ("AG. A sync that is long overdue is not called stale",
     'if hours > stale_hours else ""', 'if False else ""'),
    ("AH. The state description is rewritten by a sync that only verifies",
     '        say("requests made: %d, every one a GET. Nothing was written, and the cursor was not moved" % client.count)',
     '        write_text(state_doc_path(out_dir), "verified\\n", out_dir)'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_sync\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken sync? github-delta-sync, attempt github-attempt-002",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-delta-sync/sync.py, every test was run, and the",
           "bug was taken out again. Only local files are used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            out += ["PLANTED BUG %s" % title]
            if good.count(old) != 1:
                out += ["  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good)
            out += ["  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + test for test in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: sync.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-read-comments-events quest.

Puts one bug at a time into participant/skills/github-read-comments-events/sync.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes sync.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-read-comments-events")
TARGET = os.path.join(SKILL, "sync.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. Comments are matched by their text, not by GitHub's identifier: the quest's hint, the wrong way round (criterion 1)",
     '    return {"key": row["node_id"], "id": row["id"],', '    return {"key": "text-" + hashlib.sha256((row.get("body") or "").encode("utf-8")).hexdigest()[:16], "id": row["id"],'),
    ("B. Every sync takes every comment for a new one: the quest's scenario (criterion 2)",
     '        if old is None:', '        if True:'),
    ("C. Every sync takes every event for a new one (criterion 2)",
     '        if event["key"] not in state["events"]:', '        if True:'),
    ("D. The time of the last sync is written into the file, so it changes at every sync (criterion 2)",
     '        "- issue: number %d, node ID `%s`" % (state["issue"], state["node_id"]),',
     '        "- issue: number %d, node ID `%s`" % (state["issue"], state["node_id"]), "- last sync: %s" % state.get("last_sync"),'),
    ("E. An edited comment keeps its old text (criterion 3)",
     '        if old["body"] != comment["body"]:', '        if False:'),
    ("F. An edit replaces the text and the earlier version is thrown away (criterion 3)",
     '            old["versions"].append({"body": old["body"], "updated_at": old["updated_at"], "replaced_seen": now})', '            pass'),
    ("G. Only the first page of comments is read (criterion 4)",
     '        if not any(\'rel="next"\' in part for part in head.get("link", "").split(",")):', '        if True:'),
    ("H. Noise is recorded along with the material events (criterion 5)",
     '        if kind in NOISE:', '        if False:'),
    ("I. An event of a kind the rules do not name is dropped without a word (criterion 5)",
     '            unknown.add(kind)', '            unknown.add(kind)\n            continue'),
    ("J. An event of a kind the rules do not name is passed off as material (criterion 5)",
     '"class": "material" if kind in MATERIAL else "unclassified",', '"class": "material",'),
    ("K. Each comment is recorded a second time, as a timeline event (criterion 5)",
     '    "commented": "it is a comment', '    "commented_": "it is a comment'),
    ("L. The sync may write in the notes folder (criterion 6)",
     '    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:', '    if False:'),
    ("M. A notes file that changed during the sync is not reported (criterion 6)",
     '    return 0 if notes_before == notes_after else 1', '    return 0'),
    ("N. A deleted comment is removed from the local copy (criterion 7)",
     '        held[key].update(status="deleted", deleted_seen=now, deleted_check=why)', '        del held[key]'),
    ("O. A comment missing from the list is flagged as deleted without asking GitHub for it (criterion 7)",
     '    status, _, _ = client.get("/repos/%s/issues/comments/%d" % (repo, comment["id"]))', '    status = 404'),
    ("P. A comment GitHub failed to return is flagged as deleted (criterion 7)",
     '    if status == 404:\n        return "GitHub answered 404', '    if status != 200:\n        return "GitHub answered 404'),
    ("Q. A comment already flagged as deleted is flagged again at every sync (criteria 2 and 7)",
     'if one["status"] == "present" and key not in fetched]', 'if key not in fetched]'),
    ("R. A list of comments that could not be read is taken for an empty list",
     '            raise Stop("GitHub did not return %s (status %d). A part may be missing, so nothing is saved. A comment that could "\n                       "not be read is never taken for a comment that was deleted" % (what, status))',
     '            return rows, page'),
    ("S. A comment's text is tidied on the way in",
     '"updated_at": row.get("updated_at"), "body": row.get("body") or ""}', '"updated_at": row.get("updated_at"), "body": (row.get("body") or "").strip()}'),
    ("T. A pull request is synced as if it were an issue",
     '    if "pull_request" in issue:', '    if False:'),
    ("U. An issue whose node ID changed is synced into the old one's copy (criterion 1)",
     '        if state is not None and state["node_id"] != thread["node_id"]:', '        if False:'),
    ("V. The sync prints the text of a comment",
     '% (key, state["comments"][key]["id"]))', '% (key, state["comments"][key]["id"]) + state["comments"][key]["body"])'),
    ("W. A label or a title is written into the events table as it is",
     '        detail = "; ".join("%s: %s" % (key, q(value))', '        detail = "; ".join("%s: %s" % (key, json.dumps(value))'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_sync\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken sync? github-read-comments-events, attempt github-attempt-010",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-read-comments-events/sync.py, every test was run, and the",
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

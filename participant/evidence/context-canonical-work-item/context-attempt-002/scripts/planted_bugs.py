#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-canonical-work-item quest.

Puts one bug at a time into participant/skills/context-work-item-model/normalize.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes normalize.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-work-item-model")
TARGET = os.path.join(SKILL, "normalize.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. Identity is made from the Jira key, which changes when a story moves project (criterion 2)",
     '"identity": "jira:" + issue_id, "system": "jira"', '"identity": "jira:" + str(key), "system": "jira"'),
    ("B. Identity is made from the GitHub repository and number, which change on transfer (criteria 2 and 10)",
     '"identity": "github:" + node, "system": "github"', '"identity": "github:%s#%s" % (issue.get("full_name"), issue.get("number")), "system": "github"'),
    ("C. Identity is made from the Trello short link and title (criterion 2)",
     '"identity": "trello:" + card_id, "system": "trello"', '"identity": "trello:" + str(card.get("name")), "system": "trello"'),
    ("D. A record is looked up by its file's name, not by the identity inside it (criterion 2)",
     '        found[canonical["identity"]] = (name, text)\n    return found', '        found[name[:-3].replace("-", ":", 1)] = (name, text)\n    return found'),
    ("E. An updated item is written to a file named after it, not to the file that holds it, so a second file appears (criterion 10)",
     "        writes.append((name, text))                                          # the file that already holds this identity, whatever it is called",
     "        writes.append((file_name(identity), text))"),
    ("F. A Jira record with no retrieval time is given the time of the run (criteria 8 and 11)",
     'retrieved = utc(story.get("retrieved_at"), "retrieval time: the skill that saved it did not record when it read Jira", required=True)',
     'retrieved = utc(story.get("retrieved_at"), "retrieval time") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")'),
    ("G. A Jira record with no issue id falls back to its key (criteria 2 and 11)",
     "    if not issue_id:\n        raise Unmappable(", "    if not issue_id:\n        issue_id = key\n    if not issue_id:\n        raise Unmappable("),
    ("H. A Jira status with no category and not in the status map is taken to be open (criteria 4 and 11)",
     '    else:\n        raise Unmappable("Jira\'s status %s (id %s) was saved without its category',
     '    elif True:\n        value, basis, source = "open", "assumed", "unknown"\n    else:\n        raise Unmappable("Jira\'s status %s (id %s) was saved without its category'),
    ("I. A Jira status is read by its name, not by Jira's category (criterion 4)",
     'category = (status.get("statusCategory") or {}).get("key")', 'category = {"Done": "done", "To Do": "new"}.get(status.get("name"), (status.get("statusCategory") or {}).get("key"))'),
    ("J. A Trello card in a list called Done is done, whatever the status map says (criterion 4)",
     "    if archived:\n        status, basis, source = \"dropped\", \"stated\", \"the card is archived in Trello\"",
     "    if archived:\n        status, basis, source = \"dropped\", \"stated\", \"the card is archived in Trello\"\n    elif list_name == \"Done\":\n        status, basis, source = \"done\", \"inferred\", \"its list is called Done\""),
    ("K. A Trello card in a list the status map does not name is said to be inferred, not assumed (criterion 4)",
     'status, basis, source = "open", "assumed", "the card is open, in the list', 'status, basis, source = "open", "inferred", "the card is open, in the list'),
    ("L. A card Trello no longer returns is written as an open card (criterion 11)",
     '    if card.get("state") == "not_returned":\n        raise Unmappable(', '    if card.get("state") == "not_returned_":\n        raise Unmappable('),
    ("M. A GitHub issue closed as not planned is counted as done (criterion 4)",
     'elif state == "closed" and reason in ("not_planned", "duplicate"):', 'elif state == "closed" and reason in ("duplicate",):'),
    ("N. A GitHub issue closed with no reason is said to be stated, not inferred (criterion 4)",
     'status, basis, source = "done", "inferred", "GitHub says the issue is closed and gives no reason. Counted as done"',
     'status, basis, source = "done", "stated", "GitHub says the issue is closed and gives no reason. Counted as done"'),
    ("O. Blocked is worked out from the words of the title (the safety rule on untrusted text)",
     '    hit = sorted(set(names) & set(cfg.get("github", {}).get("blocked_labels", [])))',
     '    hit = sorted(set(names) & set(cfg.get("github", {}).get("blocked_labels", []))) or (["title"] if "blocked" in str(issue.get("title")).lower() else [])'),
    ("P. A Jira link saying this story blocks another makes this story blocked",
     'in inward and link.get("inwardIssue")]', 'in inward]'),
    ("Q. A Jira story with no saved links is said to be not blocked, where the answer is unknown",
     '    if isinstance(story.get("issuelinks"), list):\n        inward', '    if True:\n        story.setdefault("issuelinks", [])\n        inward'),
    ("R. The people's identifiers are written into the record (non-goal 2, and the rule on personal data)",
     '"assigned_to_me": ("yes" if me in assignees else "no") if me else "unknown", "assignee_count": len(assignees),',
     '"assigned_to_me": ("yes" if me in assignees else "no") if me else "unknown", "assignee_count": len(assignees), "assignees": assignees,'),
    ("S. Trello's place in the list is merged into a canonical-looking field name, outside the trello. prefix (criterion 5)",
     '"trello.position": {"place_in_list"', '"position": {"place_in_list"'),
    ("T. GitHub's links to pull requests and commits are dropped (criterion 5)",
     '"github.earlier_references": issue.get("previously") or [], "github.delivery_links": links,', '"github.earlier_references": issue.get("previously") or [], "github.delivery_links": [],'),
    ("U. Jira's parent is dropped from the source block and the canonical field (criterion 5)",
     '    parent = story.get("parent") if isinstance(story.get("parent"), dict) else None', '    parent = None'),
    ("V. Labels that were not saved are written as an empty list, as if the item had none",
     'names = label_names(card["labels"]) if "labels" in card else None', 'names = label_names(card.get("labels"))'),
    ("W. The record holds the time it was normalized, so every run rewrites every file (criterion 7's quiet re-run)",
     '"sync_source": sync_source, "source_record": record, "model": MODEL,\n    }\n    milestone',
     '"sync_source": sync_source, "source_record": record + "?" + datetime.datetime.now().isoformat(), "model": MODEL,\n    }\n    milestone'),
    ("X. A record that does not fit the model is written anyway (criterion 11)",
     "                if wrong:\n                    raise Unmappable(", "                if wrong and False:\n                    raise Unmappable("),
    ("Y. An item that can no longer be mapped has its earlier record deleted",
     "    not_seen = sorted(set(before) - set(good))\n", "    not_seen = sorted(set(before) - set(good))\n    for identity in not_seen:\n        os.remove(os.path.join(items, before[identity][0]))\n"),
    ("Z. Writing in the notes folder is allowed (criterion 7)",
     'if inside.startswith("..") or inside.split("/")[0] == "notes" or inside == "mappings/status-map.json":', 'if inside.startswith(".."):'),
    ("AA. A status outside the four values passes the model's check (criterion 4)",
     '(canonical["status"] in STATUSES, "status is %s, not one of %s"', '(True, "status is %s, not one of %s"'),
    ("AB. The check does not notice a record written to another model version (stretch goal)",
     "    if json.loads(head.group(1)) != MODEL:\n", "    if False:\n"),
    ("AC. The same item saved twice keeps the older copy",
     'if identity in good and good[identity][1]["retrieved_at"] >= provenance["retrieved_at"]:', 'if identity in good:'),
    ("AD. A time is copied as the source wrote it, in its own zone and format (criterion 1: the type of a time)",
     '    return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")', '    return value'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_normalize\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken model? context-canonical-work-item, attempt context-attempt-002",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-work-item-model/normalize.py, every test was run, and the",
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
    out += ["After the last bug was taken out: normalize.py is %s it was at the start. %s"
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

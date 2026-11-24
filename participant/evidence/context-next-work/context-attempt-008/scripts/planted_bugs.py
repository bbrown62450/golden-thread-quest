#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-next-work quest.

Puts one bug at a time into participant/skills/context-next-work/rank.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes rank.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-next-work")
TARGET = os.path.join(SKILL, "rank.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. Votes decide first: the most-voted item is ranked first (the scenario's mistake, criterion 1)",
     '        return tuple(values[c] for c in RULES[rule])',
     '        return (-(item["votes"] or 0),) + tuple(values[c] for c in RULES[rule])'),
    ('B. A blocked item is ranked like any other (criterion 2)',
     '            item["list"] = "blocked" if item["blockers"] else "ranked"',
     '            item["list"] = "ranked"'),
    ('C. A blocker with no record is taken as finished, so the item is not blocked (criterion 2)',
     '                if waiter == identity and not finished(target):',
     '                if waiter == identity and target in records and not finished(target):'),
    ("D. A link recorded only on the blocker's record is ignored (criterion 2)",
     '                elif field == "blocks":\n                    links.append((named, identity, field, identity))',
     '                elif field == "blocks":\n                    pass'),
    ('E. A dropped blocker counts as finished (criterion 2)',
     'record.get("status") == ("decided" if record["kind"] == "decision" else "done")',
     'record.get("status") in ("decided", "done", "dropped")'),
    ('F. An undecided decision does not block (criterion 2)',
     '        return record is not None and record.get("status") ==',
     '        return record is not None and record["kind"] == "decision" or record is not None and record.get("status") =='),
    ('G. A stale item gets no warning (criterion 3)',
     '        if stale:\n            item["warnings"].insert(0,',
     '        if False:\n            item["warnings"].insert(0,'),
    ('H. Exactly the limit counts as stale, and so the boundary moves (criterion 3)',
     '        if old > limit:',
     '        if old >= limit:'),
    ('I. A copy with no retrieved_at is taken as fresh (criterion 3)',
     '        if "retrieved_at" not in record:\n            return True,',
     '        if "retrieved_at" not in record:\n            return False,'),
    ('J. A copy retrieved after the clock value is taken as fresh (criterion 3)',
     '        if got > now:\n            return True,',
     '        if got > now:\n            return False,'),
    ('K. Start here is simply the first place, stale or not (criterion 3)',
     '    pick = next((i for i in ranked if not i["stale"]), None)',
     '    pick = ranked[0] if ranked else None'),
    ('L. The limit is fixed at 48 hours, not read from the policy (criterion 3)',
     '        out[kind] = int(number) * (24 if unit == "days" else 1)',
     '        out[kind] = 48'),
    ('M. The last tie-break is dropped, so level items keep whatever order they arrived in (criteria 4 and 6)',
     'RULES = {"priority-first": ["priority", "due", "waiters", "created", "identity"],',
     'RULES = {"priority-first": ["priority", "due", "waiters", "created"],'),
    ('N. Fewest waiters first, where the rule says most (criterion 4)',
     '"waiters": -item["waiters"],',
     '"waiters": item["waiters"],'),
    ('O. Due date is looked at before priority under the rule that says priority first (the conflict between criteria)',
     'RULES = {"priority-first": ["priority", "due", "waiters", "created", "identity"],',
     'RULES = {"priority-first": ["due", "priority", "waiters", "created", "identity"],'),
    ('P. A missing priority is filled in as medium (criterion 5)',
     '            item["priority"] = len(PRIORITIES)\n',
     '            item["priority"] = 1\n'),
    ('Q. A missing due date is placed before every due date (criterion 5)',
     '        for field, far in (("due", datetime.date.max), ("created", datetime.date.max)):',
     '        for field, far in (("due", datetime.date.min), ("created", datetime.date.max)):'),
    ('R. Missing data does not lower confidence (criterion 5)',
     '        drops = len(item["missing"]) + (1 if stale else 0)',
     '        drops = (1 if stale else 0)'),
    ('S. A stale copy does not lower confidence (criteria 3 and 5)',
     '        drops = len(item["missing"]) + (1 if stale else 0)',
     '        drops = len(item["missing"])'),
    ('T. A missing value is not reported as missing (criterion 5)',
     '                item["missing"].append(field)\n',
     '                pass\n'),
    ('U. A date that does not exist is accepted as a date (criterion 5)',
     '    try:\n        return datetime.date.fromisoformat(value)\n    except ValueError:\n        return None',
     '    try:\n        return datetime.date.fromisoformat(value)\n    except ValueError:\n        return datetime.date(2026, 1, 1)'),
    ('V. The ranked items are left in the order of a set, which changes from run to run (criterion 6)',
     '    ranked = sorted((i for i in items.values() if i["list"] == "ranked"), key=key)',
     '    ranked = list({i["identity"]: i for i in items.values() if i["list"] == "ranked"}.values())'),
    ('W. With no clock value, a fixed date is quietly used (criterion 6)',
     '        if now is None:\n            raise InputError("No clock value was given.',
     '        if now is None:\n            now = "2026-12-01T09:00:00Z"\n        if now is None:\n            raise InputError("No clock value was given.'),
    ('X. The deciding criterion reported is always the first one, whether or not the two items differ on it (criteria 1 and 7)',
     '        return next(c for c, x, y in zip(RULES[rule], key(a), key(b)) if x != y)',
     '        return RULES[rule][0]'),
    ("Y. An assigned item is offered (it is somebody's already)",
     '        elif record.get("assigned_to"):',
     '        elif False:'),
    ('Z. An item in progress is offered',
     '        if status != "open":',
     '        if status in ("done", "dropped"):'),
    ('AA. A finished waiter still counts as waiting',
     'records[waiter].get("status") in ("open", "in_progress"):',
     'True:'),
    ('AB. Two records with one identity are accepted',
     '        if heading in records:',
     '        if False:'),
    ('AC. The recommendation may be written over the inputs',
     '    if os.path.realpath(out) == os.path.realpath(inputs):',
     '    if False:'),
    ('AD. A link that is not an identity is silently ignored, with no warning',
     '        item["warnings"] += unreadable.get(identity, [])',
     '        pass'),
    ('AE. The change report does not say which field differs between the two inputs',
     '            if a.get(field) != b.get(field):',
     '            if False:'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_rank\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken ranking? context-next-work, attempt context-attempt-008",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-next-work/rank.py, every test was run, and the",
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
    out += ["After the last bug was taken out: rank.py is %s it was at the start. %s"
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

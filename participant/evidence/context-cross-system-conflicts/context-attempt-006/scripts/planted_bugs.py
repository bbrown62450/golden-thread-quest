#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-cross-system-conflicts quest.

Puts one bug at a time into participant/skills/context-cross-system-conflicts/conflicts.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes conflicts.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-cross-system-conflicts")
TARGET = os.path.join(SKILL, "conflicts.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The allowance is measured from today, not between the two records, so the report changes as days pass (criteria 3 and 6)",
     "    gap = abs((when_a - when_b).total_seconds())", "    gap = abs((datetime.datetime.now(datetime.timezone.utc) - max(when_a, when_b)).total_seconds())"),
    ("B. The allowance is 48 hours where the stated rule is 24 (criterion 3)",
     "    if gap > LAG_HOURS * 3600:", "    if gap > 2 * LAG_HOURS * 3600:"),
    ("C. Exactly 24 hours counts as outside the allowance (criterion 3)",
     "    if gap > LAG_HOURS * 3600:", "    if gap >= LAG_HOURS * 3600:"),
    ("D. Any difference within 24 hours is lag, even when the later record is the one LESS far along (criterion 3)",
     '    if field == "status" and ALONG[value_of(newer, field)] < ALONG[value_of(older, field)]:', '    if False:'),
    ("E. Done against dropped within 24 hours is called lag (criterion 3)",
     '    if field == "status" and ALONG[value_of(newer, field)] == ALONG[value_of(older, field)]:', '    if False:'),
    ("F. Two records changed at the same moment that differ are not reported (criterion 2)",
     '    if gap == 0:\n        return "conflict",', '    if gap == 0:\n        return "agree",'),
    ("G. A record with no time of last change is given the benefit of the doubt, and the difference is called lag (criterion 3)",
     '        return "conflict", "%s does not say when it last changed', '        return "lag", "%s does not say when it last changed'),
    ("H. GitHub's \"open\" against \"in progress\" is reported as a conflict (criterion 7)",
     '    if isinstance(limits, dict) and limits.get(other_value) == value_of(record, field):', '    if False:'),
    ("I. GitHub's \"open\" against \"done\" is waved through as not comparable, so the scenario is not reported (criterion 2)",
     '    if isinstance(limits, dict) and limits.get(other_value) == value_of(record, field):', '    if isinstance(limits, dict) and value_of(record, field) == "open":'),
    ("J. Records are linked by matching title when no link names them (criterion 1)",
     "    linked = set(identity for work in works for identity in work[\"members\"])\n",
     "    linked = set(identity for work in works for identity in work[\"members\"])\n    for a in sorted(records):\n        for b in sorted(records):\n            if a < b and a not in linked and b not in linked and records[a][\"system\"] != records[b][\"system\"] and records[a][\"title\"] == records[b][\"title\"]:\n                works.append({\"work\": \"W-title\", \"members\": [a, b], \"stated\": \"same title\", \"pairs\": [dict(zip((\"class\", \"why\", \"find_out\"), compare(records[a], records[b], f)), field=f, a=a, b=b) for f in FIELDS]})\n                linked |= {a, b}\n"),
    ("K. A record with no counterpart is reported as a conflict (criterion 5)",
     "    conflicts.sort(key=lambda one:", "    for identity in unlinked:\n        conflicts.append({\"work\": \"none\", \"field\": \"status\", \"a\": identity, \"b\": identity, \"class\": \"conflict\", \"why\": \"it has no counterpart\", \"find_out\": \"x\", \"key\": (identity,), \"affects\": [], \"seen_before\": None})\n    conflicts.sort(key=lambda one:"),
    ("L. A link naming a record that is not there is compared anyway, with what there is (criterion 5)",
     "        if missing:\n            problems.append(", "        if missing and False:\n            problems.append("),
    ("M. One record named by two links is compared in both (criterion 1)",
     "        elif shared:\n            problems.append(", "        elif shared and False:\n            problems.append("),
    ("N. The later value is written over the earlier one when a difference is lag: a winner is chosen (criterion 4)",
     '    extra = ", and it is the one further along" if field == "status" else ""', '    older["status"] = newer["status"]\n    extra = ", and it is the one further along" if field == "status" else ""'),
    ("O. The report adds a line saying which system is probably right (criterion 4)",
     '                  "- **Why it is a conflict:** %s." % one["why"],', '                  "- **Why it is a conflict:** %s." % one["why"],\n                  "- **The newer value is probably right.**",'),
    ("P. The report will write over the records file if told to (criterion 4)",
     "    if os.path.abspath(path) == os.path.abspath(records_path):", "    if False:"),
    ("Q. The report's order follows the order of the input, so the same records in another order give another report (criterion 6)",
     "    for link in sorted(links, key=lambda one: one[\"work\"]):", "    for link in links:"),
    ("R. A conflict shows only the first system's value (criterion 2)",
     'row(one["a"], one["field"]), row(one["b"], one["field"]), "",', 'row(one["a"], one["field"]), "",'),
    ("S. Conflicts are not ordered by what depends on them (stretch goal)",
     '    conflicts.sort(key=lambda one: (-len(one["affects"]), one["work"],', '    conflicts.sort(key=lambda one: (one["work"],'),
    ("T. Every conflict is said to have been seen before (stretch goal)",
     'seen_before=None if previous is None else key in before))', 'seen_before=None if previous is None else True))'),
    ("U. A title that differs is reported as a conflict (criterion 7)",
     '        return "different", "the two systems name the work differently", None', '        return "conflict", "the two systems name the work differently", "which title is meant"'),
    ("V. Whether anyone is assigned is compared by the number of people, so 1 against 3 is a difference",
     '        return None if count is None else ("someone" if count > 0 else "nobody")', '        return count'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_conflicts\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken conflict report? context-cross-system-conflicts, attempt context-attempt-006",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-cross-system-conflicts/conflicts.py, every test was run, and the",
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
    out += ["After the last bug was taken out: conflicts.py is %s it was at the start. %s"
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

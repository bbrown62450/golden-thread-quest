#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-preserve-source-fields quest.

Puts one bug at a time into participant/skills/context-preserve-source-fields/fidelity.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes fidelity.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-preserve-source-fields")
TARGET = os.path.join(SKILL, "fidelity.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A field no canonical field uses is dropped. This is the quest's scenario (criterion 2)",
     "        else:\n            preserved.append((path, raw))                  # translated, preserved only, unknown, or a copy that would not come back exactly",
     "        elif outcome != \"preserved\":\n            preserved.append((path, raw))"),
    ("B. A translated field's original is not preserved, because a canonical field \"has it\" (criterion 6)",
     "        else:\n            preserved.append((path, raw))                  # translated, preserved only, unknown, or a copy that would not come back exactly",
     "        elif outcome != \"translated\":\n            preserved.append((path, raw))"),
    ("C. A copied field is never preserved, even when the canonical value would not write back the same characters (criterion 6)",
     '        if outcome == "copied" and write_value(canonical[name]) == raw:', '        if outcome == "copied":'),
    ("D. A preserved value is parsed and written out again (criterion 3)",
     "            preserved.append((path, raw))                  # translated, preserved only, unknown, or a copy that would not come back exactly",
     "            preserved.append((path, write_value(json.loads(raw))))"),
    ("E. A preserved value is written out compactly, with no spaces (criterion 3)",
     "            preserved.append((path, raw))                  # translated, preserved only, unknown, or a copy that would not come back exactly",
     "            preserved.append((path, json.dumps(json.loads(raw), separators=(\",\", \":\"))))"),
    ("F. A field the mapping has never heard of is dropped (criterion 2)",
     "        if path not in listed:\n            unlisted.append(path)", "        if path not in listed:\n            unlisted.append(path)\n            continue"),
    ("G. The order of the fields is not kept (criterion 6)",
     '"field_order": [path for path, _ in pairs], "preserved"', '"field_order": sorted(path for path, _ in pairs), "preserved"'),
    ("H. The check does not report a field that cannot be rebuilt (criteria 4 and 5)",
     '        if path not in record["field_order"] or path in missing:', '        if False:'),
    ("I. The check does not look at what a preserved value holds (criterion 4)",
     "        elif path in held and held[path] != raw:", "        elif False:"),
    ("J. The check compares values as data, not as characters, so 3.0 and 3.00 are the same to it (criterion 3)",
     "        elif path in held and held[path] != raw:", "        elif path in held and json.loads(held[path]) != json.loads(raw):"),
    ("K. The check does not look at a field that is rebuilt from a canonical value (criterion 4)",
     "            if back != raw:\n                found.append(\"CHANGED FIELD: %s is rebuilt", "            if False:\n                found.append(\"CHANGED FIELD: %s is rebuilt"),
    ("L. The check passes when there is nothing to check",
     "    return wrong or (0 if sources else 1)", "    return wrong"),
    ("M. A source record with no normalized record is not reported (criterion 4)",
     '        found = ["MISSING RECORD: the source record has no normalized record"] if record is None else compare(system, block, record)',
     '        if record is None:\n            continue\n        found = compare(system, block, record)'),
    ("N. A normalized record with no source record is not reported",
     "        if record[\"source_record\"] not in [heading for heading, _, _ in sources]:\n            wrong += 1", "        if False:\n            wrong += 1"),
    ("O. A preserved field the source never had is not reported",
     "    for path in held:\n        if path not in [one for one, _ in source]:", "    for path in []:\n        if path not in [one for one, _ in source]:"),
    ("P. Trailing spaces are trimmed from a Trello card's canonical title (criterion 1)",
     '"reference": get("shortLink"), "title": get("name"), "status": value,', '"reference": get("shortLink"), "title": (get("name") or "").strip(), "status": value,'),
    ("Q. A Trello label with an empty name is left out of the canonical labels (criterion 1)",
     '"assignee_count": len(get("idMembers") or []), "labels": [one.get("name") for one in get("labels") or []],',
     '"assignee_count": len(get("idMembers") or []), "labels": [one.get("name") for one in get("labels") or [] if one.get("name")],'),
    ("R. A Jira issue closed as \"Won't Do\" is counted as done (criterion 1)",
     "        if value == \"done\" and (get(\"fields.resolution\") or {}).get(\"name\") in", "        if False and (get(\"fields.resolution\") or {}).get(\"name\") in"),
    ("S. Mapping version 1 has the canonical due date too, so the two versions do not differ (stretch goal)",
     "    if version < 2:\n        fields.pop(\"due_at\")", "    if False:\n        fields.pop(\"due_at\")"),
    ("T. A preserved field that only one system has is reported as shared (stretch goal)",
     "        if len(set(one.split(\" \")[0] for one in shared[meaning])) > 1:\n            say(", "        if len(set(one.split(\" \")[0] for one in shared[meaning])) > 0:\n            say("),
    ("U. A time is copied without being put in UTC (criterion 1)",
     "    return datetime.datetime.fromisoformat(text).astimezone(datetime.timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%SZ\")", "    return value"),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_fidelity\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken normalizer or a broken check? context-preserve-source-fields, attempt context-attempt-004",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-preserve-source-fields/fidelity.py, every test was run, and the",
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
    out += ["After the last bug was taken out: fidelity.py is %s it was at the start. %s"
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

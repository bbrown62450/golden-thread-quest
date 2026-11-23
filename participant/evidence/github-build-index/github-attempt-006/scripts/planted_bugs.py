#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-build-index quest.

Puts one bug at a time into participant/skills/github-build-index/index.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes index.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-build-index")
TARGET = os.path.join(SKILL, "index.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The index does not say it is generated and is not the source of truth (criteria 1 and 7)",
     '"**This file is generated. It is not the source of truth, and it must not be edited by hand.** The source of",', '"The source of",'),
    ("B. A build leaves an existing index as it is, hand edits and all (criterion 1)",
     '    if old == data:', '    if old is not None:'),
    ("C. The check compares only the list of records, so a hand edit to a row is not found (criterion 1)",
     '    if held == fresh:', '    if dict(rows_in(held)) == now:'),
    ("D. A record with a gap is left out of the table (criteria 2 and 4)",
     '    for one in records:\n        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (',
     '    for one in records:\n        if gaps_of(one):\n            continue\n        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % ('),
    ("E. A file that is not a record is dropped without a word (criterion 2)",
     '            unreadable.append(dict(why.args[1], why=why.args[0]))', '            pass'),
    ("F. The check that every file has exactly one row is skipped (criterion 2)",
     '    if sorted(name for name, _ in rows) != files or len(set(files)) != len(files):', '    if False:'),
    ("G. The check that the counts in the index agree with the files is skipped (criterion 2)",
     '    if header_number(text, "record files found") != len(files) or header_number(text, "indexed, one row each") != len(records):', '    if False:'),
    ("H. Hidden files are counted as records (criterion 2)",
     'if name.endswith(".md") and not name.startswith(".") and os.path.isfile(os.path.join(folder, name)))', 'if name.endswith(".md") and os.path.isfile(os.path.join(folder, name)))'),
    ("I. One issue held in two files is not flagged (criterion 2)",
     'for key, files in groups.items() if len(files) > 1}', 'for key, files in groups.items() if len(files) > 2}'),
    ("J. A file in another format is indexed as if it were a record (criterion 2)",
     '    if "format" in damaged or front.get("format") != RECORD_FORMAT:', '    if False:'),
    ("K. Only the first label of an issue is indexed (criterion 3)",
     'keys = sorted(set(key_text(name) for name in value)) or [NONE_GROUP[kind]]', 'keys = sorted(set(key_text(name) for name in value[:1])) or [NONE_GROUP[kind]]'),
    ("L. A lookup finds a value only when its capitals match (criterion 3)",
     'key_from(key).casefold() == (args.value or "").casefold()', 'key_from(key) == (args.value or "")'),
    ("M. A lookup of the issues with none returns the ones with a gap (criteria 3 and 4)",
     '        wanted, words = NONE_GROUP[args.kind], "records with %s"', '        wanted, words = GAP_GROUP, "records with %s"'),
    ("N. A label named like a special group is mixed in with that group (criterion 3)",
     '    return name if PLAIN_KEY.match(name) else json.dumps(name, ensure_ascii=False)', '    return name'),
    ("O. A missing line is taken to mean none (criterion 4)",
     '            return Gap("the line is missing")', '            return None'),
    ("P. A field that holds the wrong kind of thing is accepted (criterion 4)",
     '        return front[key] if good(front[key]) else Gap("it does not hold %s" % what)', '        return front[key]'),
    ("Q. A gap is shown in the table as none (criterion 4)",
     '    shown = lambda value, many=False: "**GAP**" if isinstance(value, Gap) else (', '    shown = lambda value, many=False: "*none*" if isinstance(value, Gap) else ('),
    ("R. A record with a gap is looked up under none (criterion 4)",
     '            keys = [GAP_GROUP]', '            keys = [NONE_GROUP.get(kind, GAP_GROUP)]'),
    ("S. A body that no longer matches its checksum is not noticed (criterion 4)",
     '            if tag == digest[:16] and hashlib.sha256(body.encode("utf-8")).hexdigest() == digest:', '            if True:'),
    ("T. The index holds the time it was built (criterion 5)",
     '        "- format of this index: `%s`" % INDEX_FORMAT,', '        "- format of this index: `%s`" % INDEX_FORMAT, "- built at: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),'),
    ("U. The rows are not in a fixed order (criterion 5)",
     '    records.sort(key=lambda r: (not known(r["repository"]),', '    records.sort(key=lambda r: (r["digest"], not known(r["repository"]),'),
    ("V. Every build writes the file again (criterion 5)",
     '    if old == data:', '    if False:'),
    ("W. A stale index is reported as edited by hand, and the records that changed are not named (criterion 6)",
     '    if added or removed or changed:', '    if False:'),
    ("X. A record that changed is not noticed by the check (criterion 6)",
     '    changed = sorted(name for name in set(now) & set(then) if now[name] != then[name])', '    changed = []'),
    ("Y. A pipe in a title is not escaped, so a title can break a row",
     '(("\\\\", "\\\\\\\\"), ("|", "\\\\|"), ("`", "\\\\`"),', '(("\\\\", "\\\\\\\\"), ("`", "\\\\`"),'),
    ("Z. A line break in a title is kept, so a title can add a line to the index",
     '    text = "".join(char if char >= " " and char != "\\x7f" else " " for char in str(text))', '    text = str(text)'),
    ("AA. Brackets are not escaped, so a title can add a link",
     '("[", "\\\\["), ("]", "\\\\]"), ', ''),
    ("AB. The link to a record file with an odd name is not made safe",
     'urllib.parse.quote("%s/%s" % (records_rel, record["file"])))', '"%s/%s" % (records_rel, record["file"]))'),
    ("AC. The search does not look in comments",
     '            if wanted in text.casefold():', '            if wanted in text.casefold() and name == "body":'),
    ("AD. The search minds capitals",
     '    wanted = args.text.casefold()', '    wanted = args.text'),
    ("AE. The search looks through the whole file, fields and all",
     '        for name, _, text in blocks(one["text"]):', '        for name, _, text in [("body", "", one["text"])]:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_index\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken generator? github-build-index, attempt github-attempt-006",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-build-index/index.py, every test was run, and the",
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
    out += ["After the last bug was taken out: index.py is %s it was at the start. %s"
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

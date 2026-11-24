#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-extract-work-items quest.

Puts one bug at a time into participant/skills/ba-extract-work-items/extract.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes extract.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "ba-extract-work-items")
TARGET = os.path.join(SKILL, "extract.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. A cited identifier that is not in the record is not reported (criterion 1)',
     '        if utterance not in lines:\n            where = [',
     '        if False:\n            where = ['),
    ('B. Only identifiers on citation lines are looked up, so one written in a note is never checked (criteria 1 and 7)',
     '    everywhere = set(re.findall(r"\\bU-\\d+\\b", items_text)) - {"U-0001"} | {c["u"] for e in entries for c in e["cites"]}',
     '    everywhere = {c["u"] for e in entries for c in e["cites"]}'),
    ('C. An item with no citation at all passes (criterion 1)',
     '        if not item["cites"]:\n            say("%s cites no line of the source record. An item',
     '        if False:\n            say("%s cites no line of the source record. An item'),
    ('D. An item needs no mention of the work itself, only any cited line (criterion 1)',
     '        elif not mentions:',
     '        elif False:'),
    ('E. Quoted words are not compared with the record (criterion 7)',
     '            if c["words"] != lines[c["u"]]["words"]:',
     '            if False:'),
    ('F. The speaker given for a line is not compared with the record (criterion 7)',
     '            if c["speaker"] != who(record, c["u"]):',
     '            if False:'),
    ('G. A citation into a different transcript is accepted (criterion 7)',
     '    for other in sorted(set(re.findall(r"\\b(tr-[\\w-]+)#U-\\d+", items_text)) - {record["id"]}):',
     '    for other in []:'),
    ('H. An owner, size or date may be stated with no line behind it: a gap filled in (criteria 2 and 3)',
     '            elif state.startswith("said") and not answering:',
     '            elif False:'),
    ('I. One of the six things may be left out altogether (criterion 3)',
     '            if state is None:\n                say("%s does not say whether the meeting stated',
     '            if False:\n                say("%s does not say whether the meeting stated'),
    ('J. NOT SAID may stand beside a line cited as answering (criterion 3)',
     '            elif state.startswith("NOT SAID") and answering:',
     '            elif False:'),
    ("K. The count of things said is not compared with the item's own lines (stretch goal)",
     '        if item["stated_count"] != count:',
     '        if False:'),
    ('L. The number of mentions in the heading is not compared with the mentions cited (criterion 4)',
     '        if count != len(groups) or groups != ["Mention %d" % n for n in range(1, len(groups) + 1)]:',
     '        if False:'),
    ('M. The same line may be the mention of two items, so one piece of work can become two (criterion 4)',
     '        if len(owners) > 1:',
     '        if False:'),
    ('N. Two items may have the same title (criterion 4)',
     '    for title in sorted({t for t in titles if titles.count(t) > 1}):',
     '    for title in []:'),
    ('O. The same item may appear twice (criterion 4)',
     '        if ids.count(name) > 1:',
     '        if False:'),
    ('P. A record changed since it was ingested is not noticed (criterion 5)',
     '    elif recorded.group(1) != sha(record_text):',
     '    elif False:'),
    ('Q. A file made from another version of the record is accepted (criterion 5)',
     '    if not stated or stated.group(1) != sha(record_text):',
     '    if not stated:'),
    ('R. One file serving as both record and work-items file is accepted (criterion 5)',
     '    if same_file:\n',
     '    if False:\n'),
    ('S. Work items written into the record are not noticed (criterion 5)',
     '    if re.search(r"^### [WR]-\\d+", record_text, re.M) or "**Intent:**" in record_text:',
     '    if False:'),
    ('T. The record copied into the work-items file is not noticed (criterion 5)',
     '    if re.search(r"^### U-\\d{4} · ", items_text, re.M) or re.search(r"^<a id=\\"U-", items_text, re.M):',
     '    if False:'),
    ('U. A proposal may be marked decided (criterion 2)',
     '            if ref[0] not in mark[1]:',
     '            if False:'),
    ('V. An item may rest on a decision the meeting reversed (criterion 2)',
     '            if ref.startswith("D-") and "REVERSED" in status:',
     '            if False:'),
    ('W. An item may rest on a decision none of whose lines it cites (criterion 2)',
     '            if not cited & {c["u"] for c in item["cites"]}:',
     '            if False:'),
    ('X. An item may rest on something that is not in the decisions file',
     '            if ref not in decisions:\n                say("%s rests on %s, which is not in the decisions file." % (name, ref))\n                continue',
     '            if ref not in decisions:\n                continue'),
    ('Y. An item may be made from a line that reads like an instruction (safety rule)',
     '            if c["u"] in instruction:',
     '            if False:'),
    ('Z. A refusal need not say why (the refused item)',
     '        if not entry["why"]:',
     '        if False:'),
    ('AA. A line of the record that is neither cited nor listed is not noticed (criterion 7)',
     '    for u in sorted(set(lines) - cited - set(listed)):',
     '    for u in []:'),
    ('AB. The one-speaker flag is not compared with the speakers cited (stretch goal)',
     '        if item["one_speaker"] != (len(speakers) == 1):',
     '        if False:'),
    ('AG. A plain "decided" heading may sit on an item that has a part not settled (criterion 2)',
     '        if mark[0] in ("decided", "decided-part", "decided-reopened") and unsettled != (mark[0] == "decided-part"):',
     '        if False:'),
    ('AH. A plain "decided" heading may rest on a decision that was reopened (criterion 2)',
     '            if ref.startswith("D-") and ("reopened" in status) != (mark[0] == "decided-reopened") and mark[0] != "follow-up":',
     '            if False:'),
    ('AC. The check ends with exit code 0 when it found problems',
     '"" if len(problems) == 1 else "s"))\n        return 1',
     '"" if len(problems) == 1 else "s"))\n        return 0'),
    ('AD. An empty work-items file passes',
     '    if not items:\n        say("The work-items file has no items that could be read.")',
     '    if False:\n        say("The work-items file has no items that could be read.")'),
    ('AE. An intent of two sentences passes',
     '        elif item["intent"].count(". ") > 0 or not item["intent"].endswith("."):',
     '        elif False:'),
    ('AF. build ranks the table by item number, not by how much was said (stretch goal)',
     '    for item in sorted(items, key=lambda i: (-specified(i), i["id"])):',
     '    for item in items:'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_extract\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken extraction check? ba-extract-work-items, attempt ba-attempt-006",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/ba-extract-work-items/extract.py, every test was run, and the",
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
    out += ["After the last bug was taken out: extract.py is %s it was at the start. %s"
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

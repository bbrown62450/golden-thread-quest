#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-extract-decisions quest.

Puts one bug at a time into participant/skills/ba-extract-decisions/decisions.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes decisions.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "ba-extract-decisions")
TARGET = os.path.join(SKILL, "decisions.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. A cited identifier that is not in the record is not reported (criterion 6)',
     '        if utterance not in lines:\n            where = [',
     '        if False:\n            where = ['),
    ('B. Only identifiers on citation lines are looked up, so one written in a note is never checked (criterion 6)',
     'sorted(set(re.findall(r"\\bU-\\d+\\b", decisions_text)) - {"U-0001"} | {c["u"] for i in entries for c in i["cites"]})',
     'sorted({c["u"] for i in entries for c in i["cites"]})'),
    ('C. A citation into a different transcript is accepted (criterion 6)',
     '    for other in sorted(set(re.findall(r"\\b(tr-[\\w-]+)#U-\\d+", decisions_text)) - {record["id"]}):',
     '    for other in []:'),
    ('D. Quoted words are not compared with the record (criterion 7)',
     '            if c["words"] != lines[c["u"]]["words"]:',
     '            if False:'),
    ('E. The speaker given for a line is not compared with the record (criteria 3 and 7)',
     '            if c["speaker"] != who(record, c["u"]):',
     '            if False:'),
    ('F. A record changed since it was ingested is not noticed (criterion 5)',
     '    elif recorded.group(1) != sha(record_text):',
     '    elif False:'),
    ('G. A decisions file made from another version of the record is accepted (criterion 5)',
     '    if not stated or stated.group(1) != sha(record_text):',
     '    if not stated:'),
    ('H. One file serving as both record and decisions file is accepted (criterion 5)',
     '    if same_file:\n',
     '    if False:\n'),
    ('I. Decision items written into the record are not noticed (criterion 5)',
     '    if re.search(r"^### [DPON]-\\d+", record_text, re.M) or "**Decision:**" in record_text:',
     '    if False:'),
    ('J. The record copied into the decisions file is not noticed (criterion 5)',
     '    if re.search(r"^### U-\\d{4} · ", decisions_text, re.M) or re.search(r"^<a id=\\"U-", decisions_text, re.M):',
     '    if False:'),
    ('K. A decision with nobody accepting it passes (criterion 2)',
     '            if not agreers:',
     '            if False:'),
    ('L. The proposer\'s own "agreed" counts as acceptance (criterion 2)',
     '            for name in sorted(set(agreers) & set(proposers)):',
     '            for name in []:'),
    ('M. Agreement from a speaker of uncertain identity counts (criteria 2 and 3)',
     '                if c["label"] == "Agreed by" and c["u"] in lines and lines[c["u"]]["uncertain"]:',
     '                if False:'),
    ("N. A ruling outside the speaker's role counts as a decision (criterion 2)",
     '                elif OWNS[role][0] != item["area"]:',
     '                elif False:'),
    ('O. A ruled decision need not say that agreement was not stated (criterion 3)',
     '            if not item["not_stated"]:',
     '            if False:'),
    ('P. An item under the wrong heading is accepted, so a proposal can sit among the decisions (criteria 2 and 4)',
     '        if kind not in prefix or not re.fullmatch(r"%s-\\d+" % prefix.get(kind, "X"), item["id"]):',
     '        if kind not in prefix:'),
    ('Q. An item that is not a decision may carry an "Agreed by" line (criterion 2)',
     '            if any(c["label"] in ("Agreed by", "Ruled by") for c in item["cites"]):',
     '            if False:'),
    ('R. Acceptance in a line before the proposal passes',
     '            if proposers and agreers and min(numbers(item, "Agreed by")) < min(numbers(item, "Proposed by")):',
     '            if False:'),
    ('S. A decision with a reversing line may still be marked in force (the reversed decision)',
     '        elif reversing:',
     '        elif False:'),
    ('T. A reversed decision need not name a decision in force that replaced it',
     '            if target is None or target["section"] != "decision" or (len(target["tags"]) > 1 and target["tags"][1].startswith("REVERSED")):',
     '            if False:'),
    ('U. A reversal by a line before the decision passes',
     '            elif settled and min(reversing) <= max(settled):',
     '            elif False:'),
    ('V. The reopened mark and the reopening line need not match (stretch goal)',
     '        if ("reopened" in status) != bool(numbers(item, "Reopened by")):',
     '        if False:'),
    ('W. A decision may rest on a line listed as reading like an instruction (safety rule)',
     '            for u in sorted(instruction & {c["u"] for c in item["cites"]}):',
     '            for u in []:'),
    ('X. A line of the record that is neither cited nor listed is not noticed (criterion 7)',
     '    for u in sorted(set(lines) - cited - set(listed)):',
     '    for u in []:'),
    ('Y. The counts in the file are not compared with its items (stretch goal)',
     '        if "| %s | %d |" % (label, count) not in decisions_text:',
     '        if False:'),
    ('Z. The check ends with exit code 0 when it found problems',
     '"" if len(problems) == 1 else "s"))\n        return 1',
     '"" if len(problems) == 1 else "s"))\n        return 0'),
    ('AA. build counts a reversed decision as in force',
     '    in_force = [d for d in decisions if not d.get("reversed")]',
     '    in_force = list(decisions)'),
    ("AB. The record's mark for an uncertain speaker is not read",
     '"uncertain": "*Speaker uncertain" in body}',
     '"uncertain": False}'),
    ('AC. Only the first line of an utterance written on two lines is read, so its quotation is cut short (criterion 7)',
     '        words = " ".join(line[2:].strip() for line in body.splitlines() if line.startswith("> "))',
     '        words = next((line[2:].strip() for line in body.splitlines() if line.startswith("> ")), "")'),
    ('AD. The same item twice is accepted',
     '        if ids.count(item["id"]) > 1:',
     '        if False:'),
    ('AE. A line both cited and listed as not sorted is accepted',
     '    for u in sorted(set(listed) & cited):',
     '    for u in []:'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_decisions\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken citation check? ba-extract-decisions, attempt ba-attempt-005",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/ba-extract-decisions/decisions.py, every test was run, and the",
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
    out += ["After the last bug was taken out: decisions.py is %s it was at the start. %s"
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

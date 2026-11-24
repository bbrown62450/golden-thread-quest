#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-slice-story quest.

Puts one bug at a time into participant/skills/ba-slice-story/slice.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes slice.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "ba-slice-story")
TARGET = os.path.join(SKILL, "slice.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. A criterion in no slice is not reported (criterion 3)',
     '        if not got:\n            say("%s is covered by no slice."',
     '        if False:\n            say("%s is covered by no slice."'),
    ('B. A criterion in two slices is not reported (criterion 3)',
     '        elif len(got) > 1:',
     '        elif False:'),
    ('C. A criterion reworded in a slice is not reported (criterion 6)',
     '            elif cid in text_of and said != text_of[cid]:',
     '            elif False:'),
    ('D. A criterion with no number, written into a slice, is not reported (criterion 6)',
     '            if cid is None:',
     '            if False:'),
    ('E. A slice may cover a criterion the original does not have (criterion 6)',
     '            if cid not in text_of:\n                say("%s covers %s, which is not',
     '            if False:\n                say("%s covers %s, which is not'),
    ('F. The Covers line and the criteria written out need not agree',
     '        if [c for c in listed if c] != s["covers"]:',
     '        if False:'),
    ('G. A slice may depend on itself (criterion 4)',
     '            elif d >= n:',
     '            elif d > n:'),
    ('H. A slice may say it depends on a later slice (criterion 4)',
     '            elif d >= n:',
     '            elif False:'),
    ('I. A criterion may need one in a later slice (criterion 4)',
     '                if m > n:',
     '                if False:'),
    ('J. A needed earlier slice need not be declared (criterion 4)',
     '                elif m not in reach(n):',
     '                elif False:'),
    ('K. Slice 1 may depend on another slice (criterion 5)',
     '        if declared.get(1) or re.findall(r"Slice (\\d+)", slices[0]["depends_text"]):',
     '        if False:'),
    ('L. Slice 1 may rely on a later slice (criterion 5)',
     '        if re.search(r"\\bSlice [2-9]\\d*\\b", slices[0]["relies"]):',
     '        if False:'),
    ('M. Slices cut from another version of the original pass',
     '    if head["sha"] != sha(original_text):',
     '    if False:'),
    ('N. Wrong counts at the head pass (criterion 7)',
     '    if not head["counts"] or [int(x)',
     '    if not head["counts"] and [int(x)'),
    ('O. A wrong coverage table passes (criterion 7)',
     '    if table != [',
     '    if False and table != ['),
    ('P. A slice with no value passes (criterion 1)',
     '        if len(s["value"].split()) < 6:',
     '        if len(s["value"].split()) < 0:'),
    ('Q. A slice need not say what a user would notice (criterion 2)',
     '        if len(s["notice"].split()) < 4:',
     '        if len(s["notice"].split()) < 0:'),
    ('R. A slice need not say what it relies on (the safety rule)',
     '        if len(s["relies"].split()) < 2:',
     '        if len(s["relies"].split()) < 0:'),
    ('S. A slice need not say what holds if released early',
     '        if len(s["alone"].split()) < 3:',
     '        if len(s["alone"].split()) < 0:'),
    ('T. A slice need not justify its place in the order',
     '        if len(s["why"].split()) < 6:',
     '        if len(s["why"].split()) < 0:'),
    ("U. A layer word in a slice's value passes (criterion 2)",
     '        for word in layer_words(s["title"] + " " + s["value"]):',
     '        for word in layer_words(s["title"]):'),
    ('V. No word counts as a layer word (criterion 2)',
     '    return [word for word in LAYER_WORDS if',
     '    return [word for word in [] if'),
    ('W. Needs that go round in a circle pass',
     '    if circle:',
     '    if False:'),
    ('X. A criterion may need itself',
     '            if need == c["id"]:',
     '            if False:'),
    ('Y. A criterion may need one that does not exist',
     '            elif need not in text_of:',
     '            elif False:'),
    ('Z. The original criteria may be numbered in any order',
     '    if [c["id"] for c in criteria] != ["OC-%02d"',
     '    if False and [c["id"] for c in criteria] != ["OC-%02d"'),
    ('AA. The slices may be numbered in any order',
     '    if [s["number"] for s in slices] != ',
     '    if False and [s["number"] for s in slices] != '),
    ('AB. A criterion listed twice in one slice passes',
     's["covers"].count(c) > 1)):',
     's["covers"].count(c) > 2)):'),
    ('AC. The first slice is always said to stand alone (criterion 5)',
     'all(where.get(need) == 1 for',
     'all(True for'),
    ('AD. The rejected slicing counts a criterion as holding when any one of its layers is done',
     'set(needed[cid]) <= done]',
     'set(needed[cid]) & done]'),
    ('AE. "Covered exactly once" counts a criterion covered twice (criterion 3)',
     '    once = sum(1 for c in criteria if len(covered_by.get(c["id"], [])) == 1)',
     '    once = sum(1 for c in criteria if len(covered_by.get(c["id"], [])) >= 1)'),
    ('AF. A slice need not have a Depends on line',
     '        if not wanted and s["depends_text"].strip().lower() != "none":',
     '        if False:'),
    ('AG. A missing section of the original story passes',
     '        if not original["parts"].get(title, "").strip():',
     '        if False:'),
    ('AH. A dependency is not followed through another slice',
     '                queue.extend(declared.get(d, []))',
     '                pass'),
    ('AI. The slicing by area never finds a need in a later area',
     'if where.get(need, 0) > where[c["id"]]]',
     'if where.get(need, 0) < 0]'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_slice\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken slicing check? ba-slice-story, attempt ba-attempt-008",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/ba-slice-story/slice.py, every test was run, and the",
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
    out += ["After the last bug was taken out: slice.py is %s it was at the start. %s"
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

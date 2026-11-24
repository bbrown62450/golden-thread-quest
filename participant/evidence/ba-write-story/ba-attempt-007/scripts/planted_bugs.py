#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-write-story quest.

Puts one bug at a time into participant/skills/ba-write-story/story.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes story.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "ba-write-story")
TARGET = os.path.join(SKILL, "story.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A missing section is not reported (the check's first job)",
     '        if title not in parts:\n            say("The story has no section',
     '        if False:\n            say("The story has no section'),
    ('B. Sections may be in any order',
     '    if [t for t in order if t in SECTIONS] != [t for t in SECTIONS if t in order]:',
     '    if False:'),
    ('C. A user who is only "a user" passes (criterion 1)',
     '        if not got or len(got.group(1).split()) < 3:',
     '        if not got:'),
    ('D. A vague word in the value passes (criterion 1)',
     '        elif vague_in(got.group(1), defined):',
     '        elif False:'),
    ('E. An empty in-scope or out-of-scope list passes (criterion 2)',
     '        if not entries:\n            say("\\"%s\\" lists nothing." % title)',
     '        if False:\n            say("\\"%s\\" lists nothing." % title)'),
    ('F. An out-of-scope entry need not say why (criterion 2)',
     '        if not re.search(r"^   - Why it is out: \\S", entry, re.M):',
     '        if False:'),
    ('G. An out-of-scope entry may go to an item that does not exist (criterion 2)',
     '                if ref not in known:',
     '                if False:'),
    ('H. Criteria need not be numbered in order (criterion 3)',
     '    if [c["id"] for c in criteria] != expected:',
     '    if False:'),
    ('I. A criterion may have no Then, or two (criterion 3)',
     '            if len(c[key]) != 1:',
     '            if False:'),
    ('J. A Then of two sentences passes (criterion 3)',
     '            elif c[key][0].rstrip(".").count(". ") or not c[key][0].endswith("."):',
     '            elif False:'),
    ('K. Vague words in a criterion are not looked for (criterion 6)',
     '        for word in vague_in(words, defined):\n            say("%s uses the word',
     '        for word in []:\n            say("%s uses the word'),
    ('L. A vague word is allowed whether or not the story defines it (criterion 6)',
     '        if word in defined:\n            continue',
     '        if word == "valid":\n            continue'),
    ('M. The list of vague words has lost the three the quest names (criterion 6)',
     'VAGUE = ["fast", "faster", "quick", "quickly", "slow", "easy", "easily", "simple", "simply", "intuitive",',
     'VAGUE = ["faster", "quick", "quickly", "slow", "easily", "simple", "simply",'),
    ('N. Words are matched inside other words, so "breakfast" is "fast" (criterion 6)',
     '        if re.search(r"(?<![\\w-])%s(?![\\w-])" % re.escape(word), bare):',
     '        if word in bare:'),
    ('O. A SAID criterion with no citation passes (criterion 5)',
     '            if not c["cites"]:\n                say("%s is marked SAID and cites no line',
     '            if False:\n                say("%s is marked SAID and cites no line'),
    ('P. An ASSUMED criterion may cite the meeting as its source (the two are never mixed)',
     '            if c["cites"]:\n                say("%s is marked ASSUMED and cites',
     '            if False:\n                say("%s is marked ASSUMED and cites'),
    ('Q. An ASSUMED criterion need not name the question it answers',
     '            if not c["question"]:',
     '            if False:'),
    ('R. A criterion with neither basis passes',
     '            say("%s does not say whether it is SAID or ASSUMED." % c["id"])',
     '            pass'),
    ('S. A SAID criterion need not name the writer-defined words it leans on',
     '            if c["leans"] is None:',
     '            if False:'),
    ("T. The list of writer-defined words on a SAID criterion is not checked against the story's own definitions",
     '            elif [w.strip() for w in c["leans"].split(",")] != (leaning or ["none"]):',
     '            elif False:'),
    ('U. An in-scope entry need not name a criterion that tests it (criterion 7)',
     '        if not named:\n            say("In-scope entry %s does not say which criteria test it." % number)',
     '        if False:\n            say("In-scope entry %s does not say which criteria test it." % number)'),
    ('V. Dependencies may be neither listed nor stated as none (criterion 4)',
     '    if not re.search(r"^\\d+\\. ", deps, re.M) and not re.search(r"^None\\.", deps.strip(), re.M):',
     '    if False:'),
    ('W. A cited identifier that is not in the record is not reported (criterion 5)',
     '        if utterance not in lines:\n            say("%s is cited and is not in the source record." % utterance)',
     '        if False:\n            say("%s is cited and is not in the source record." % utterance)'),
    ('X. Only identifiers on citation lines are looked up (criterion 5)',
     '    everywhere = set(re.findall(r"\\bU-\\d+\\b", story_text)) - {"U-0001"} | {c["u"] for c in cites}',
     '    everywhere = {c["u"] for c in cites}'),
    ('Y. Quoted words are not compared with the record (criterion 5)',
     '            if c["words"] != lines[c["u"]]["words"]:',
     '            if False:'),
    ('Z. The speaker given for a line is not compared with the record',
     '            if c["speaker"] != who(record, c["u"]):',
     '            if False:'),
    ('AA. A record changed since it was ingested is not noticed',
     '    if not recorded or recorded.group(1) != sha(record_text):',
     '    if not recorded:'),
    ('AB. The count at the head is not compared with the criteria',
     '    if "Acceptance criteria: %d. SAID by the meeting: %d. ASSUMED by the writer: %d." % (len(criteria), said_count, assumed_count) not in story_text:',
     '    if False:'),
    ('AC. A line of the record that is neither cited nor listed as not used is not noticed',
     '    for u in sorted(set(lines) - set(used) - set(listed)):',
     '    for u in []:'),
    ('AD. The definition of done may hold acceptance criteria (stretch goal)',
     '    if re.search(r"^### AC-", done, re.M) or re.search(r"^- \\[ \\] ", parts.get("Acceptance criteria", ""), re.M):',
     '    if False:'),
    ('AE. An assumption may answer a question that does not list it back (stretch goal)',
     '            elif c["id"] not in questions[c["question"]]:',
     '            elif False:'),
    ('AF. The check ends with exit code 0 when it found problems',
     '"" if len(problems) == 1 else "s"))\n        return 1',
     '"" if len(problems) == 1 else "s"))\n        return 0'),
    ('AG. A story with no test data passes',
     'if row.strip() not in ("Name", "---")]:',
     'if row.strip() not in ("---",)]:'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_story\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken story check? ba-write-story, attempt ba-attempt-007",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/ba-write-story/story.py, every test was run, and the",
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
    out += ["After the last bug was taken out: story.py is %s it was at the start. %s"
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

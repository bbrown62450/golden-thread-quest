#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-clarification-questions quest.

Puts one bug at a time into participant/skills/ba-clarification-questions/questions.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes questions.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "ba-clarification-questions")
TARGET = os.path.join(SKILL, "questions.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A question is kept as soon as any two answers differ, so two answers with the same work can stay in it (criterion 3)",
     "    if len(sets) >= 2 and len(set(sets)) == len(sets):", "    if len(sets) >= 2 and len(set(sets)) > 1:"),
    ("B. A question whose answers all lead to the same work is never called dropped (criterion 4)",
     "    if len(sets) >= 2 and len(set(sets)) == 1:\n        return \"dropped\"", "    if len(sets) >= 2 and len(set(sets)) == 1:\n        return \"kept\""),
    ("C. Work that every answer needs anyway is counted as depending on the answer (criterion 6)",
     "    return set().union(*sets) - set(sets[0]).intersection(*sets[1:])", "    return set().union(*sets)"),
    ("D. A question does not carry the work of the question that waits for it (criterion 6)",
     "                found |= own_dependent(other[\"answers\"])", "                pass"),
    ("E. The order is least work first (criterion 6)",
     "    return (-len(all_dependent(question, questions)),", "    return (len(all_dependent(question, questions)),"),
    ("F. Equal counts ignore the finding's effort (criterion 6)",
     "EFFORT.get(finding.get(\"effort\"), 9),", "0,"),
    ("G. The word limit is 30 where the stated rule is 25 (criterion 5)",
     "MAX_WORDS, MAX_ANSWERS, MAX_LABEL_WORDS, MIN_WORK_WORDS = 25, 4, 15, 5", "MAX_WORDS, MAX_ANSWERS, MAX_LABEL_WORDS, MIN_WORK_WORDS = 30, 4, 15, 5"),
    ("H. Two questions in one pass as one (criterion 5)",
     "    if not text.endswith(\"?\") or text.count(\"?\") != 1:", "    if not text.endswith(\"?\"):"),
    ("I. More than one sentence passes (criterion 5)",
     "    if re.search(r\"[.!;]\\s\", text):", "    if False:"),
    ("J. Any finding number is accepted, whether or not the review has it (criterion 1)",
     "        if entry[\"finding\"] not in findings:  ", "        if not entry[\"finding\"]:  "),
    ("K. The quoted words are not looked for in the finding (criterion 1)",
     "        elif not entry[\"from\"] or entry[\"from\"] not in findings[entry[\"finding\"]][\"question\"]:", "        elif not entry[\"from\"]:"),
    ("L. The quoted words may come from any finding, not the one linked (criterion 1)",
     "entry[\"from\"] not in findings[entry[\"finding\"]][\"question\"]:", "entry[\"from\"] not in \" \".join(f[\"question\"] for f in findings.values()):"),
    ("M. One answer is enough (criterion 2)",
     "        if len(entry[\"answers\"]) < 2:  ", "        if len(entry[\"answers\"]) < 1:  "),
    ("N. An answer with no stated work passes (criterion 3)",
     "            if words(a[\"work\"]) < MIN_WORK_WORDS:", "            if False:"),
    ("O. A piece of work that is not in the list is accepted (criterion 3)",
     "                if piece not in pieces:", "                if False:"),
    ("P. A question whose answers all lead to the same work is not reported (criteria 3 and 4)",
     "        if kind == \"dropped\":  ", "        if kind == \"never\":  "),
    ("Q. Two of three answers with the same work are not reported (criterion 3)",
     "        elif kind == \"mixed\":", "        elif kind == \"never\":"),
    ("R. The same sentence for two answers is not reported (criterion 3)",
     "        if len(set(works)) != len(works):", "        if False:"),
    ("S. A dropped question whose answers differ is not reported (criterion 4)",
     "        if len(d[\"answers\"]) >= 2 and classify(d[\"answers\"]) != \"dropped\":", "        if False:"),
    ("T. A dropped question with no reason is not reported (criterion 4)",
     "        if words(d[\"why\"]) < MIN_WORK_WORDS:", "        if False:"),
    ("U. A candidate in neither list is not reported (criterion 4)",
     "    if missing:", "    if False:"),
    ("V. A candidate in both lists is not reported (criterion 4)",
     "        if ids.count(candidate) > 1:", "        if ids.count(candidate) > 2:"),
    ("W. A wrong order is not reported (criterion 6)",
     "    if [q[\"id\"] for q in ordered] != [q[\"id\"] for q in questions]:", "    if False:"),
    ("X. A question before the one it waits for is not reported (criterion 6)",
     "                if questions.index(parent) > questions.index(q):", "                if False:"),
    ("Y. A stated count that the answers do not give is not reported (criterion 6)",
     "        if not re.match(r\"%d piece\" % count, q[\"stated_count\"]):", "        if False:"),
    ("Z. A question that waits for every answer of another is accepted",
     " or set(q[\"only_if\"][1]) == set(letters):", ":"),
    ("AA. A default that is not one of the answers is accepted",
     "        elif q[\"default\"][0] not in [a[\"letter\"] for a in q[\"answers\"]]:", "        elif False:"),
    ("AB. An empty question list passes",
     "    if not questions:\n", "    if False:\n"),
    ("AC. The check ends with exit code 0 when it found problems",
     "\"\" if len(problems) == 1 else \"s\"))\n            return 1", "\"\" if len(problems) == 1 else \"s\"))\n            return 0"),
    ("AD. The check ends with exit code 0 when a file is missing",
     "os.path.basename(error.filename or \"?\"))\n            return 1", "os.path.basename(error.filename or \"?\"))\n            return 0"),
    ("AE. build writes the questions in the order of the candidates, not ordered by work (criterion 6)",
     "    kept = sorted(kept, key=lambda q: order_key(q, kept, findings))", "    kept = list(kept)"),
    ("AF. build puts a candidate whose answers do not differ in the question list (criterion 4)",
     "    kept = [c for c in candidates if classify(c[\"answers\"]) == \"kept\"]", "    kept = [c for c in candidates if classify(c[\"answers\"]) != \"mixed\"]"),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_conflicts\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken question check? ba-clarification-questions, attempt ba-attempt-004",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/ba-clarification-questions/questions.py, every test was run, and the",
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
    out += ["After the last bug was taken out: questions.py is %s it was at the start. %s"
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

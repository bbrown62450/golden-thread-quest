#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-dependency-map quest.

Puts one bug at a time into participant/skills/context-dependency-map/depmap.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes depmap.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-dependency-map")
TARGET = os.path.join(SKILL, "depmap.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A link is made from any identity mentioned in a title or description (criterion 1)",
     "    for identity in sorted(records):\n        record = records[identity]\n        for field in LINK_FIELDS:",
     "    for identity in sorted(records):\n        record = records[identity]\n        for named in re.findall(r\"(?:jira|trello|github|decision):[A-Za-z0-9_-]*[A-Za-z0-9]\", \"%s %s\" % (record.get(\"title\"), record.get(\"description\"))):\n            if named != identity:\n                links.setdefault((identity, named), set()).add((\"title\", identity))\n        for field in LINK_FIELDS:"),
    ("B. The related field is counted as a dependency (criterion 1)",
     "LINK_FIELDS = (\"blocked_by\", \"blocks\", \"needs_decision\")  ", "LINK_FIELDS = (\"blocked_by\", \"blocks\", \"needs_decision\", \"related\")  "),
    ("C. blocks is read the wrong way round, as if the record waited on the one named (criteria 1 and 2)",
     "                pair = (named, identity) if field == \"blocks\" else (identity, named)", "                pair = (identity, named)"),
    ("D. A link to an item with no record is dropped without a word (criterion 4)",
     "                pair = (named, identity) if field == \"blocks\" else (identity, named)",
     "                if named not in records:\n                    continue\n                pair = (named, identity) if field == \"blocks\" else (identity, named)"),
    ("E. Text that is not an identity is taken as one, so a link is guessed (criterion 4)",
     "                if not isinstance(named, str) or not IDENTITY.match(named):", "                if not isinstance(named, str):"),
    ("F. The reverse index is a second copy of the forward index (criterion 2)",
     "    waited_by = {n: sorted(w for (w, t) in links if t == n) for n in nodes}", "    waited_by = {n: sorted(t for (w, t) in links if w == n) for n in nodes}"),
    ("G. A cycle of two is not reported (criterion 3)",
     "    cycles = sorted(c for c in components if len(c) > 1)", "    cycles = sorted(c for c in components if len(c) > 2)"),
    ("H. Cycle detection forgets what a deeper item reached, so longer cycles are missed (criterion 3)",
     "                low[n] = min(low[n], low[t])", "                pass"),
    ("I. Cycle detection treats any item seen before as part of the current path, so shared prerequisites look like cycles (criterion 3)",
     "            elif t in on_stack:", "            else:"),
    ("J. An item that names itself is not reported (criterion 3)",
     "    self_links = sorted(n for n in nodes if (n, n) in links)", "    self_links = []"),
    ("K. A decided decision still counts as holding work up (criterion 5)",
     "FINISHED = {\"work\": (\"done\",), \"decision\": (\"decided\",)}", "FINISHED = {\"work\": (\"done\",), \"decision\": ()}"),
    ("L. Waiting on a proposal or a question is not reported (criterion 5)",
     "\"undecided\": sorted((w, t) for (w, t) in links if state[t] == \"undecided\" and active(w)),", "\"undecided\": [],"),
    ("M. A link to something finished still counts as holding work up (criterion 6)",
     "        return state[target] != \"finished\"", "        return True"),
    ("N. Only the items waiting directly are counted (criterion 6)",
     "                    found.add(w)\n                    queue.append(w)", "                    found.add(w)"),
    ("O. In a cycle an item is counted as blocking itself (criterion 6)",
     "                if w not in found and w != n and active(w) and open_link(w, current):", "                if w not in found and active(w) and open_link(w, current):"),
    ("P. A dropped item is counted among those blocked (criterion 6)",
     "        return state[n] in (\"waiting\", \"undecided\")", "        return state[n] != \"finished\""),
    ("Q. Four items are listed, not five (criterion 6)",
     "TOP = 5", "TOP = 4"),
    ("R. The list is the items blocking the least (criterion 6)",
     "key=lambda n: (-len(blocked[n]), -len(direct[n]), n))", "key=lambda n: (len(blocked[n]), -len(direct[n]), n))"),
    ("S. Equal totals ignore the direct count (criterion 6)",
     "key=lambda n: (-len(blocked[n]), -len(direct[n]), n))", "key=lambda n: (-len(blocked[n]), n))"),
    ("T. The items are listed in whatever order Python's set gives, which changes from run to run (criterion 7)",
     "    nodes = sorted(set(records) | {n for pair in links for n in pair})", "    nodes = list(set(records) | {n for pair in links for n in pair})"),
    ("U. Problems are found and the build still ends with exit code 0",
     "    return 1 if count else 0", "    return 0"),
    ("V. A missing target is in the index and is not printed by the build (criterion 4)",
     "        say(\"NOT FOUND: %s, named by %s\" % (n, \", \".join(waiters)))", "        pass"),
    ("W. A cycle is in the index and is not printed by the build (criterion 3)",
     "        say(\"CYCLE: %s\" % \" waits on \".join(way))", "        pass"),
    ("X. Two records with one identity are accepted, the second replacing the first",
     "        if heading in records:", "        if False:"),
    ("Y. The index may be written over the data file",
     "    if os.path.abspath(out) == os.path.abspath(data):", "    if False:"),
    ("Z. The longest chain follows links into a cycle (stretch goal)",
     "                if t not in in_cycle and open_link(n, t) and state[t] != \"gone\":", "                if open_link(n, t) and state[t] != \"gone\":"),
    ("AA. A slip ignores slack and moves every dependent to the day after its prerequisite (stretch goal)",
     "            if got and got[1] >= start:", "            if got:"),
    ("AB. A slip is not applied at all (stretch goal)",
     "            finish = finish + datetime.timedelta(days=days)", "            pass"),
    ("AC. Starting on the day a prerequisite finishes is not reported as too early",
     "            if start and finish and start <= finish:", "            if start and finish and start < finish:"),
    ("AD. needs_decision that names a work item is not reported (criterion 5)",
     "if any(f == \"needs_decision\" for f, _ in sources) and t in records and records[t][\"kind\"] != \"decision\"),", "if False),"),
    ("AE. Waiting on something dropped or superseded is not reported",
     "\"gone\": sorted((w, t) for (w, t) in links if state[t] == \"gone\" and active(w)),", "\"gone\": [],"),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_depmap\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken dependency index? context-dependency-map, attempt context-attempt-007",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-dependency-map/depmap.py, every test was run, and the",
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
    out += ["After the last bug was taken out: depmap.py is %s it was at the start. %s"
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

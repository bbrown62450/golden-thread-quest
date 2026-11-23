#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-duplicate-search quest.

Puts one bug at a time into participant/skills/github-duplicate-search/search.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes search.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-duplicate-search")
TARGET = os.path.join(SKILL, "search.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The title counts toward the signals a candidate needs (criteria 1 and 3)",
     '    beyond = sum(found[name][0] == "match" for name, _, _ in SIGNALS)', '    beyond = sum(found[name][0] == "match" for name, _, _ in SIGNALS) + (found["title"][0] == "match")'),
    ("B. Two signals beyond the title are enough (criterion 1)",
     'NEEDED = 3                 # an issue', 'NEEDED = 2                 # an issue'),
    ("C. A signal with nothing to compare counts as a match (criterion 1)",
     'found["error"] = ("not comparable", "one of the two quotes no error") if not ours or not theirs else (',
     'found["error"] = ("match", "one of the two quotes no error") if not ours or not theirs else ('),
    ("D. One shared file name is enough for the named-things signal (criterion 1)",
     'NAMED_NEEDED = 2 ', 'NAMED_NEEDED = 1 '),
    ("E. A label that only says what kind of issue it is counts as a signal (criterion 1)",
     '    telling = lambda labels: {name.casefold() for name in labels} - CATCH_ALL', '    telling = lambda labels: {name.casefold() for name in labels}'),
    ("F. An error name is counted a second time as a named thing (criterion 1)",
     '    return {one.strip().lower() for one in found if one.strip()} - errors_in(text)', '    return {one.strip().lower() for one in found if one.strip()}'),
    ("G. Any shared word is enough for the body-wording signal (criterion 1)",
     '        if len(both) >= WORDS_NEEDED and part >= WORDS_SHARE else', '        if len(both) >= 1 else'),
    ("H. Every candidate is given high confidence (criterion 2)",
     '    return beyond, points, next(name for name, low, high in SCALE if low <= points <= high)', '    return beyond, points, "high"'),
    ("I. The steps of the confidence scale are in the wrong places (criterion 2)",
     'SCALE = (("high", 11, MOST), ("medium", 9, 10), ("low", 6, 8))', 'SCALE = (("high", 10, MOST), ("medium", 9, 9), ("low", 6, 8))'),
    ("J. Candidates are listed weakest first (criterion 2)",
     '    order = lambda row: (-row["points"], -row["beyond"],', '    order = lambda row: (row["points"], -row["beyond"],'),
    ("K. Comments on an existing issue are not searched (criterion 4)",
     'for _, _, block in indexer.blocks(one["text"]))', 'for part, _, block in indexer.blocks(one["text"]) if part == "body")'),
    ("L. An issue that matched on one signal is reported as a low-confidence duplicate, so a search never says none (criteria 3 and 5)",
     '        return beyond, points, None', '        return beyond, points, ("low" if beyond else None)'),
    ("M. Closing as a duplicate is recommended against a closed issue (criterion 6)",
     '    if confidence == "high" and issue["state"] == "open" and same_repo:', '    if confidence == "high" and same_repo:'),
    ("N. Closing as a duplicate is recommended at any confidence (criterion 6)",
     '    if confidence == "high" and issue["state"] == "open" and same_repo:', '    if issue["state"] == "open" and same_repo:'),
    ("O. Closing as a duplicate is recommended across repositories (criterion 6)",
     '    if confidence == "high" and issue["state"] == "open" and same_repo:', '    if confidence == "high" and issue["state"] == "open":'),
    ("P. A fourth recommendation is given (criterion 6)",
     '        return "close-as-duplicate", "high confidence', '        return "merge", "high confidence'),
    ("Q. The result does not say that a person decides (criterion 6)",
     'Recommendation: proceed. A person decides")', 'Recommendation: proceed")'),
    ("R. The search touches the index (criterion 7)",
     '    result = search(proposal, index, args.equal_weights)', '    result = search(proposal, index, args.equal_weights); os.utime(here_index)'),
    ("S. The report can be written over the index or a record (criterion 7)",
     '        if os.path.realpath(args.report) in {os.path.realpath(path) for path in before}:', '        if False:'),
    ("T. An index that is stale or edited is searched anyway (criterion 7)",
     '    if indexer.render(records, unreadable, where.group(1)) != text:', '    if False:'),
    ("U. A record with a gap is compared as if it were whole",
     '        if not issue["usable"]:', '        if False:'),
    ("V. The equal-weights option changes nothing it should",
     '    if equal_weights:\n        return beyond, points, {5: "high", 4: "medium"}.get(beyond, "low")', '    if False:\n        return beyond, points, {5: "high", 4: "medium"}.get(beyond, "low")'),
    ("W. A title from a record is written into the report as it is",
     '    q = lambda text: cell(json.dumps(text, ensure_ascii=False))', '    q = lambda text: json.dumps(text, ensure_ascii=False)'),
    ("X. What was found is written into the report's table as it is",
     'result_word.upper() if result_word == "match" else result_word, cell(evidence)))', 'result_word.upper() if result_word == "match" else result_word, evidence))'),
    ("Y. A proposed issue with no title is accepted",
     '    if not isinstance(title, str) or not title.strip():', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_search\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken search? github-duplicate-search, attempt github-attempt-007",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-duplicate-search/search.py, every test was run, and the",
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
    out += ["After the last bug was taken out: search.py is %s it was at the start. %s"
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

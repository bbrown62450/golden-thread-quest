#!/usr/bin/env python3
"""Records logs/duplicate-run.txt for the github-duplicate-search quest, and writes the report.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts anything: the search
reads local files only, and every issue and proposed issue is made up.

The three searches run against participant/context/github/duplicates/fixture.md
and its records, as they are. The first also writes
participant/context/github/duplicates/report.md. Two further parts need a
changed fixture or a changed proposal. They run in a scratch copy that is
thrown away, shown here as SCRATCH.

This script checks for itself. It takes its own SHA-256 of the index and of
every record before and after, reads titles from the files with its own code,
and looks for the shared error text and file names in the two texts itself,
rather than taking the search's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SEARCH = "participant/skills/github-duplicate-search/search.py"
INDEX_PY = "participant/skills/github-build-index/index.py"
FOLDER = "participant/context/github/duplicates"
FIXTURE, RECORDS, REPORT = FOLDER + "/fixture.md", FOLDER + "/records", FOLDER + "/report.md"
MEMORY, LOGIN, DARK = (FOLDER + "/proposals/proposed-%s.md" % name for name in ("out-of-memory", "login-page", "dark-mode"))
BEYOND = ("Error text", "Named things", "Body wording", "Labels", "Repository")


class Log:
    def __init__(self, title):
        self.lines, self.problems, self.scratch = [title], [], None
        self.out("Recorded by scripts/record_evidence.py. Nothing was contacted. Every repository, person, label and issue is made up.")

    def tidy(self, text):
        return text.replace(os.path.realpath(self.scratch), "SCRATCH").replace(self.scratch, "SCRATCH") if self.scratch else text

    def out(self, text=""):
        self.lines.append(self.tidy(text))

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def run(self, script, *args):
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.out("$ python3 " + " ".join(shlex.quote(part) for part in [script] + list(args)))
        self.lines += ["-" * 78, self.tidy(done.stdout.rstrip("\n")), "-" * 78, "exit code: %s" % done.returncode]
        return done.returncode, done.stdout

    def save(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.out()
        self.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems else "%d OF %d CHECKS FAILED." % (len(self.problems), count)))
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


def text_of(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def fingerprints():
    """This script's own SHA-256 and last-written time of the index and of every record."""
    found = {}
    for path in [FIXTURE] + sorted(os.path.join(RECORDS, name) for name in os.listdir(RECORDS)):
        with open(path, "rb") as f:
            found[path] = (hashlib.sha256(f.read()).hexdigest(), os.stat(path).st_mtime_ns)
    return found


def title_in(path):
    """The title in a file's front matter, read by this script."""
    return json.loads(re.search(r"^title: (.*)$", text_of(path), re.M).group(1))


def candidates(text):
    return re.findall(r"CANDIDATE \d+: (\S+#\d+)", text)


def block(text, issue):
    lines = text.splitlines()
    start = next(number for number, line in enumerate(lines) if "CANDIDATE" in line and issue + " " in line and "NOT A" not in line)
    return lines[start:start + 8]


def matched(lines):
    """The signals beyond the title that one candidate's lines show as MATCH."""
    return [name for name in BEYOND if any(re.search(r": +%s +MATCH " % re.escape(name), line) for line in lines)]


def main():
    os.chdir(ROOT)
    log = Log("Searching for likely duplicates before an issue is filed. github-duplicate-search, attempt github-attempt-007")
    if os.path.exists(REPORT):
        os.remove(REPORT)
    log.out("Before part 1 this script removed %s, left by the last recording." % REPORT)

    log.part("PART 1. The fixture: an index, and the records behind it")
    before = fingerprints()
    listing = sorted(os.listdir(FOLDER))
    code, text = log.run(INDEX_PY, "check", "--records", RECORDS, "--out", FIXTURE)
    log.check("the fixture is an index the github-build-index skill wrote, and that skill's check says it is UP TO DATE", code == 0 and "RESULT: UP TO DATE" in text)
    log.out("This script took the SHA-256 and the last-written time of the index and of each of its %d records." % (len(before) - 1))
    record = lambda number: os.path.join(RECORDS, "acme-fixture__tracker__issue-%d.md" % number)
    log.out("The three issues the quest asks the fixture to hold, with their titles as this script read them from the records:")
    log.out("  the true duplicate, under a different title:  tracker 101, %s" % json.dumps(title_in(record(101))))
    log.out("  a near duplicate:                             tracker 102, %s" % json.dumps(title_in(record(102))))
    log.out("  an unrelated issue with the same title:       tracker 103, %s" % json.dumps(title_in(record(103))))
    log.check("all three are rows of the index", all("| acme-fixture/tracker | %d |" % number in text_of(FIXTURE) for number in (101, 102, 103)))

    log.part("PART 2. A proposed duplicate. The existing issue has a different title, and is found (criterion 4)")
    log.out("The proposed issue is titled %s. The issue it duplicates is titled %s." % (json.dumps(title_in(MEMORY)), json.dumps(title_in(record(101)))))
    code, text = log.run(SEARCH, MEMORY, "--report", REPORT)
    first = block(text, "acme-fixture/tracker#101")
    log.check("exit code 0, and tracker 101 is the first candidate", code == 0 and candidates(text)[:1] == ["acme-fixture/tracker#101"])
    words = lambda title: set(re.findall(r"[a-z]{4,}", title.lower()))
    log.check("the two titles share no word of four letters or more: this script compared them", not words(title_in(MEMORY)) & words(title_in(record(101))))
    log.check("the search says so too: the title signal did not match", any(re.search(r"Title +no ", line) for line in first))
    log.check("it lists the signals beyond the title that matched: all 5 of them, where 3 are needed (criterion 1)", matched(first) == list(BEYOND))
    both = [thing for thing in ("MemoryError", "orders-march.csv", "export.py", "v2.3.1") if thing in text_of(MEMORY) and thing in text_of(record(101))]
    log.check("what it says was found is really in both texts: this script looked for the error name and the three named things in the proposal and in the record",
              len(both) == 4 and "both quote: memoryerror" in "\n".join(first) and "both name: export.py, orders-march.csv, v2.3.1" in "\n".join(first))
    log.check("it gives a confidence on the stated scale: high, 13 of 14 points (criterion 2)", "confidence high, 13 points" in first[1]
              and "high is 11 to 14 points; medium is 9 to 10 points; low is 6 to 8 points, of 14" in text)
    log.check("its recommendation is close-as-duplicate, and it says a person decides (criterion 6)",
              "Recommendation: close-as-duplicate" in first[1] and text.rstrip().endswith("Recommendation: close-as-duplicate. A person decides"))
    near = block(text, "acme-fixture/tracker#102")
    log.check("the near duplicate, tracker 102, is found at low confidence with 3 signals, and is to be linked, not closed: it is slow, it does not crash",
              matched(near) == ["Named things", "Labels", "Repository"] and "confidence low, 6 points" in near[1] and "Recommendation: link" in near[1]
              and any("Error text" in line and "not comparable" in line for line in near))
    closed = block(text, "acme-fixture/tracker#106")
    log.check("tracker 106 has the same error and is closed: medium confidence, to be linked, with the reason that the problem may have come back",
              "confidence medium, 10 points" in closed[1] and "Recommendation: link (the existing issue is closed" in closed[1])
    log.check("every candidate matched on at least 3 signals beyond the title", all(len(matched(block(text, issue))) >= 3 for issue in candidates(text)) and len(candidates(text)) == 3)
    log.check("issues that share less are listed as NOT A CANDIDATE with their count, and not as duplicates",
              'NOT A CANDIDATE: acme-fixture/tracker#107 "Rename the --chunk-size option": 2 of the 3 signals needed' in text)

    log.part("PART 3. A proposed issue that shares its title with an unrelated one. It is not reported (criterion 3)")
    log.out("The proposed issue is titled %s, and so is tracker 103. The proposal is about a page of a printed handbook." % json.dumps(title_in(LOGIN)))
    log.out("Tracker 103 is about a sign-in screen that stays blank.")
    code, text = log.run(SEARCH, LOGIN)
    log.check("the two titles are the same, character for character: this script compared them", title_in(LOGIN) == title_in(record(103)))
    log.check("exit code 0, and there is no candidate at all", code == 0 and candidates(text) == [] and "RESULT: NONE." in text)
    log.check("tracker 103 is shown as looked at and NOT A CANDIDATE: the title matched, 0 of the 3 signals needed, and a title alone makes nothing a duplicate",
              'NOT A CANDIDATE: acme-fixture/tracker#103 "Login page is blank": 0 of the 3 signals needed (nothing beyond the title). The title matched: the titles are the same' in text)
    log.check("the recommendation is proceed", text.rstrip().endswith("Recommendation: proceed. A person decides"))

    log.part("PART 4. A proposed issue with no match. It reports none (criterion 5)")
    code, text = log.run(SEARCH, DARK)
    log.check("exit code 0, and the result says NONE plainly", code == 0 and "RESULT: NONE. No likely duplicate was found. Recommendation: proceed. A person decides" in text)
    log.check("no issue is offered as a candidate just for being the nearest", candidates(text) == [] and not re.search(r"CANDIDATE \d", text))
    log.check("the two issues that share only the repository are shown as not candidates, and 7 matched on nothing", text.count("NOT A CANDIDATE") == 2 and "matched on nothing at all: 7" in text)

    log.part("PART 5. The index is unchanged (criterion 7)")
    after = fingerprints()
    log.out("This script took the SHA-256 and last-written time of the index and its records again, after the three searches.")
    log.check("the index fixture.md has the same SHA-256 as before the searches: %s" % before[FIXTURE][0], after[FIXTURE][0] == before[FIXTURE][0])
    log.check("each of the %d records has the same SHA-256 as before" % (len(before) - 1), all(after[path][0] == before[path][0] for path in before) and set(after) == set(before))
    log.check("none of them was even written again: every last-written time is the same", all(after[path][1] == before[path][1] for path in before))
    log.check("the only new file in %s is the report" % FOLDER, sorted(os.listdir(FOLDER)) == sorted(listing + ["report.md"]))
    code, text = log.run(INDEX_PY, "check", "--records", RECORDS, "--out", FIXTURE)
    log.check("the github-build-index check still says UP TO DATE", code == 0 and "RESULT: UP TO DATE" in text)

    log.part("PART 6. The report for the proposed issue of part 2")
    report = text_of(REPORT)
    for line in report.split("\n")[:13]:
        log.out("  | " + line)
    sections = report.split("\n### ")[1:]
    log.check("the report has 3 candidates, each with its own table of signals", len(sections) == 3 and report.count("| Signal | Points | Result | What was found |") == 3)
    log.check("each candidate's table shows at least 3 signals beyond the title as MATCH",
              all(sum(bool(re.search(r"^\| %s \| \d \| MATCH \|" % re.escape(name), part, re.M)) for name in BEYOND) >= 3 for part in sections))
    log.check("each candidate has a confidence on the stated scale and one of the three recommendations",
              [re.match(r"\d\. \S+: (\w+) confidence, (\d+) of 14 points\. Recommendation: ([a-z-]+)", part).groups() for part in sections]
              == [("high", "13", "close-as-duplicate"), ("medium", "10", "link"), ("low", "6", "link")])
    log.check("the report states the scale, says it only recommends and a person decides, and says nothing was created, linked or closed",
              "high is 11 to 14 points; medium is 9 to 10 points; low is 6 to 8 points, of 14" in report
              and "**This report is generated. It recommends, and a person decides.** Nothing was created, linked or closed." in report)

    with tempfile.TemporaryDirectory() as scratch:
        log.scratch = scratch
        copy = os.path.join(scratch, "duplicates")
        shutil.copytree(FOLDER, copy)
        copy_index = os.path.join(copy, "fixture.md")

        log.part("PART 7. Stretch goal: the weights, and what they change")
        with open(os.path.join(copy, "proposals", "no-labels.md"), "w", encoding="utf-8") as f:
            f.write(re.sub(r"^repository: .*\nlabels: .*\n", "", text_of(MEMORY), flags=re.M))
        log.out("In a scratch copy, the proposal of part 2 with its repository and labels lines taken out, as a hurried person might file it.")
        log.out("Only the three strongest signals can match now: error text, named things and body wording.")
        code, weighted = log.run(SEARCH, os.path.join(copy, "proposals", "no-labels.md"), "--index", copy_index)
        code, equal = log.run(SEARCH, os.path.join(copy, "proposals", "no-labels.md"), "--index", copy_index, "--equal-weights")
        log.check("with the weights, three strong signals give medium confidence: 10 points", candidates(weighted) == ["acme-fixture/tracker#101"] and "confidence medium, 10 points" in weighted)
        log.check("with every signal counted as 1, the same match is low: 3 points, the same as three weak signals would get", "confidence low, 3 points" in equal)
        log.check("the weights change the confidence, not which issues are candidates", candidates(weighted) == candidates(equal))

        log.part("PART 8. An index that is out of date is not searched")
        shutil.copy(os.path.join(copy, "records", "acme-fixture__tracker__issue-104.md"), os.path.join(copy, "records", "a-record-the-index-does-not-know.md"))
        log.out("In the scratch copy a record file is added and the index is not built again.")
        code, text = log.run(SEARCH, os.path.join(copy, "proposals", "proposed-out-of-memory.md"), "--index", copy_index)
        log.check("exit code 1: the search stops, and says the index is not what its records give and that a search could miss an issue",
                  code == 1 and "the index is NOT what its records give now" in text and "A search of it could miss an issue" in text and "RESULT" not in text)
        log.scratch = None

    return 0 if log.save("duplicate-run.txt") else 1


if __name__ == "__main__":
    sys.exit(main())

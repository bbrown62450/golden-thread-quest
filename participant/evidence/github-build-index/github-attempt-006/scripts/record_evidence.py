#!/usr/bin/env python3
"""Records logs/index-run.txt for the github-build-index quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts anything: the
generator reads local files only, and every issue record is made up.

Part 1 builds participant/context/github/index.md from the twelve records in
participant/context/github/issues/, after removing the index left by the last
recording. Everything that adds, damages or edits a file is done in a scratch
copy that is thrown away, shown here as SCRATCH.

This script checks for itself. It counts the record files, reads each record's
front matter with its own few lines of code, and reads the index's table with
its own pattern, rather than taking the generator's word.

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
SKILL = "participant/skills/github-build-index"
INDEX_PY, MAKE = SKILL + "/index.py", SKILL + "/make_records.py"
RECORDS, INDEX = "participant/context/github/issues", "participant/context/github/index.md"


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


def data(path):
    with open(path, "rb") as f:
        return f.read()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------- this script's own reading of records and index


def own_records(folder):
    """Each record file's fields, read from its front matter by this script. A file that cannot be read this way maps to None."""
    found = {}
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        text = data(os.path.join(folder, name)).decode("utf-8", "replace")
        head = text[4:].split("\n---\n")[0] if text.startswith("---\n") else None
        try:
            found[name] = dict((line.split(": ", 1)[0], json.loads(line.split(": ", 1)[1])) for line in head.split("\n"))
        except (AttributeError, IndexError, ValueError):
            found[name] = None
    return found


def own_rows(index_text):
    """The rows of the index's main table: [(repository, number, file name)], read with this script's own pattern."""
    section = index_text.split("\n## All records")[1].split("\n## ")[0]
    rows = []
    for line in section.split("\n"):
        found = re.match(r"^\| (\S+) \| (\S+) \| .* \| \[.*\]\(([^)]+)\) \| [0-9a-f]{12} \|$", line)
        if found:
            rows.append((found.group(1), found.group(2), found.group(3).split("/")[-1]))
    return rows


def answers(text):
    return sorted(re.findall(r"^github-index:   (\S+#\d+)", text, re.M))


def expected(records, test):
    return sorted("%s#%d" % (front["repository"], front["number"]) for front in records.values() if front and test(front))


def main():
    os.chdir(ROOT)
    log = Log("Building the index of local issue records. github-build-index, attempt github-attempt-006")
    if os.path.exists(INDEX):
        os.remove(INDEX)
    records = own_records(RECORDS)
    log.out("Before part 1 this script removed %s, left by the last recording." % INDEX)
    log.out("The records folder %s holds %d files, counted by this script." % (RECORDS, len(records)))

    log.part("PART 1. Build the index twice. The results are identical (criterion 5)")
    code, text = log.run(INDEX_PY, "build")
    first, made = data(INDEX), os.stat(INDEX).st_mtime_ns
    log.check("exit code 0, and the build says it WROTE the index", code == 0 and "index: WROTE " in text and "RESULT: built" in text)
    code, text = log.run(INDEX_PY, "build")
    log.out("This script read the index after each build: %d bytes, SHA-256 %s, both times." % (len(first), digest(first)))
    log.check("exit code 0, and the second build says UNCHANGED", code == 0 and "UNCHANGED" in text and "WROTE" not in text)
    log.check("the two results are byte for byte identical: this script compared all %d bytes" % len(first), data(INDEX) == first and len(first) > 0)
    log.check("the second build did not even write the file again: its last-written time is the same", os.stat(INDEX).st_mtime_ns == made)
    log.check("the index holds no date and no time of day", not re.search(r"\b20\d\d-\d\d|\d\d:\d\d", first.decode("utf-8")))

    with tempfile.TemporaryDirectory() as scratch:
        log.scratch = scratch
        copy, copy_index = os.path.join(scratch, "issues"), os.path.join(scratch, "index.md")
        os.makedirs(copy)
        for number, name in enumerate(sorted(records, reverse=True)):
            shutil.copy(os.path.join(RECORDS, name), os.path.join(copy, name))
            os.utime(os.path.join(copy, name), (1700000000 + number * 97, 1700000000 + number * 97))
        there = ("--records", copy, "--out", copy_index)
        log.out("The same %d records copied to a scratch folder, in the reverse order and with other file dates, and built there:" % len(records))
        log.run(INDEX_PY, "build", *there)
        log.check("the index built from the copies is byte for byte the one built above: it does not depend on file dates or order", data(copy_index) == first)

        log.part("PART 2. The row count equals the record count, and no record is repeated (criterion 2)")
        index_text = first.decode("utf-8")
        rows = own_rows(index_text)
        log.out("Counted by this script, with its own reading of the folder and of the index:")
        log.out("  record files in the folder:                 %d" % len(records))
        log.out("  rows in the index's table:                  %d" % len(rows))
        log.out("  different record files those rows link to:  %d" % len({row[2] for row in rows}))
        log.out("  different issues (repository and number):   %d" % len({row[:2] for row in rows}))
        log.check("the index has %d rows and the folder has %d record files" % (len(rows), len(records)), len(rows) == len(records) == 12)
        log.check("every record file is linked from exactly one row, and every row links to a file that is there", sorted(row[2] for row in rows) == sorted(records))
        log.check("no issue is in the index twice: %d rows, %d different issues" % (len(rows), len({row[:2] for row in rows})), len({row[:2] for row in rows}) == len(rows))
        log.check("each row's repository and number are the ones in its record's front matter, read by this script",
                  all((records[name]["repository"], str(records[name]["number"])) == (repo, number) for repo, number, name in rows))
        log.check("the index's own header gives the same counts: 12 found, 12 indexed, 0 with a gap, 0 that could not be indexed",
                  "- record files found: 12\n- indexed, one row each: 12\n- of those, with a gap: 0\n- could not be indexed: 0\n" in index_text)

        log.part("PART 3. Lookups by repository, label, milestone and assignee, from the index (criterion 3)")
        log.out("For each lookup this script worked out the answer itself from the records' front matter, and compared.")
        lookups = (("repository", "acme-fixture/website", lambda front: front["repository"] == "acme-fixture/website"),
                   ("label", "bug", lambda front: "bug" in front["labels"]),
                   ("milestone", "Launch", lambda front: front["milestone"] == "Launch"),
                   ("assignee", "kit-fixture", lambda front: "kit-fixture" in front["assignees"]))
        for kind, value, test in lookups:
            code, text = log.run(INDEX_PY, "lookup", kind, value)
            want = expected(records, test)
            log.check("by %s: the lookup gives the %d issues this script found in the records: %s" % (kind, len(want), ", ".join(want)),
                      code == 0 and answers(text) == want and len(want) > 0)
        code, text = log.run(INDEX_PY, "lookup", "assignee", "--none")
        want = expected(records, lambda front: not front["assignees"])
        log.check("issues with nobody assigned can be looked up too: %s" % ", ".join(want), answers(text) == want and len(want) == 2)
        code, text = log.run(INDEX_PY, "lookup", "label", "--list")
        counts = {}
        for front in records.values():
            for name in front["labels"] or [None]:
                counts[name] = counts.get(name, 0) + 1
        log.check("the list of labels has every label in the records with the count this script got: %d labels, and %d issues with none"
                  % (len(counts) - 1, counts[None]), all(("  %s: %d\n" % (json.dumps(name) if not re.match(r"^[\w ]+$", name) else name, count)) in text
                                                          for name, count in counts.items() if name) and "  (no label): %d\n" % counts[None] in text)
        log.check("the lookups read the index and say so, not the records", text.count("looking in the INDEX") == 1)
        hidden = os.path.join(scratch, "index-alone")
        os.makedirs(hidden)
        shutil.copy(INDEX, os.path.join(hidden, "index.md"))
        code, text = log.run(INDEX_PY, "lookup", "label", "docs", "--out", os.path.join(hidden, "index.md"))
        log.check("a copy of the index in a folder with no records beside it still answers: the lookup works from the index alone",
                  code == 0 and answers(text) == expected(records, lambda front: "docs" in front["labels"]))

        log.part("PART 4. Adding a record changes the index without a hand edit (criterion 6)")
        log.out("In the scratch copy, so that the handed-in index stays as part 1 built it.")
        before = data(copy_index)
        log.run(INDEX_PY, "check", *there)
        log.out("A new made-up record is written, as a sync would write one. It is website issue 14:")
        log.run(MAKE, copy, "--one")
        code, text = log.run(INDEX_PY, "check", *there)
        log.check("before the index is built again, the check says it is STALE and names the added record",
                  code == 3 and "RESULT: STALE" in text and "ADDED since the index was built: acme-fixture\\_\\_website\\_\\_issue-14.md" in text)
        log.check("the index file itself has not been touched yet: same bytes as before", data(copy_index) == before)
        code, text = log.run(INDEX_PY, "build", *there)
        after = data(copy_index)
        log.check("exit code 0, and the build now counts 13 rows for 13 files", code == 0 and "the index has 13 rows for 13 files" in text)
        log.check("the index changed, and the only thing that wrote to it was the build command", after != before and "index: WROTE" in text)
        new_rows = own_rows(after.decode("utf-8"))
        log.check("the new record has one row: acme-fixture/website, number 14", new_rows.count(("acme-fixture/website", "14", "acme-fixture__website__issue-14.md")) == 1 and len(new_rows) == 13)
        log.check("every row that was there before is still there, unchanged", all(line in after.decode("utf-8") for line in before.decode("utf-8").split("\n") if line.startswith("| acme")))
        code, text = log.run(INDEX_PY, "lookup", "assignee", "robin-fixture", *there)
        log.check("the new issue is found by a lookup", "acme-fixture/website#14" in answers(text))
        code, text = log.run(INDEX_PY, "check", *there)
        log.check("the check now says UP TO DATE", code == 0 and "RESULT: UP TO DATE" in text)

        log.part("PART 5. A record with a missing field is reported as a gap (criterion 4)")
        damaged = os.path.join(copy, "acme-fixture__tracker__issue-12.md")
        text_12 = data(damaged).decode("utf-8")
        with open(damaged, "w", encoding="utf-8") as f:
            f.write(text_12.replace('milestone: "Sprint 12: exports"\n', ""))
        with open(os.path.join(copy, "meeting-notes.md"), "w", encoding="utf-8") as f:
            f.write("# Notes from a made-up meeting\n\nNot an issue record.\n")
        log.out("This script damaged one scratch record: it deleted the line `milestone: ...` from tracker issue 12. It also put a")
        log.out("file in the folder that is not a record at all, meeting-notes.md.")
        code, text = log.run(INDEX_PY, "build", *there)
        gapped = data(copy_index).decode("utf-8")
        log.check("exit code 3: built, and a person should look", code == 3 and "RESULT: built, and a person should look" in text)
        log.check("the missing field is reported as a gap, naming the file and the field",
                  "GAP: acme-fixture__tracker__issue-12.md: the field `milestone`: the line is missing" in text)
        log.check("the record keeps its row, with GAP where the milestone would be, not a blank and not \"none\"",
                  "| acme-fixture/tracker | 12 | Import fails on an empty file | open | bug | **GAP** | robin-fixture |" in gapped)
        log.check("the index lists it under \"Gaps (1)\"", "## Gaps (1)" in gapped and "`milestone`: the line is missing" in gapped.split("## Gaps (1)")[1])
        log.check("the file that is not a record is counted and listed under \"Could not be indexed (1)\", with the reason",
                  "COULD NOT BE INDEXED: meeting-notes.md: it has no front matter" in text and "## Could not be indexed (1)" in gapped)
        log.check("the counts still add up: 14 files found, 13 indexed and 1 that could not be",
                  "the index has 14 rows for 14 files (13 indexed and 1 that could not be)" in text and len(own_rows(gapped)) == 13)
        code, text = log.run(INDEX_PY, "lookup", "milestone", "--gap", *there)
        log.check("the record with the gap can be looked up as one", answers(text) == ["acme-fixture/tracker#12"])
        code, text = log.run(INDEX_PY, "lookup", "milestone", "--none", *there)
        want = expected(own_records(RECORDS), lambda front: front["milestone"] is None)
        log.check("it is not mixed in with the issues that truly have no milestone (%s): a gap is not \"none\"" % ", ".join(want), answers(text) == want)
        code, text = log.run(INDEX_PY, "lookup", "label", "bug", *there)
        log.check("it is still found by its label, which the record does have", "acme-fixture/tracker#12" in answers(text))

        log.part("PART 6. The index is generated, never hand-edited (criterion 1)")
        with open(damaged, "w", encoding="utf-8") as f:
            f.write(text_12)
        os.remove(os.path.join(copy, "meeting-notes.md"))
        log.out("The damaged record is put back and the stray file removed. The index is built again, and is clean:")
        log.run(INDEX_PY, "build", *there)
        clean = data(copy_index)
        with open(copy_index, "w", encoding="utf-8") as f:
            f.write(clean.decode("utf-8").replace("| acme-fixture/website | 5 | Fix the footer year | open |", "| acme-fixture/website | 5 | Fix the footer year | closed |"))
        log.out("Now this script edits the scratch index by hand: in the row of website issue 5 it changes \"open\" to \"closed\".")
        code, text = log.run(INDEX_PY, "check", *there)
        log.check("exit code 3: the check says EDITED BY HAND, and not stale, because the records are the ones it was built from",
                  code == 3 and "RESULT: EDITED BY HAND" in text and "STALE" not in text)
        code, text = log.run(INDEX_PY, "build", *there)
        log.check("the next build writes the whole file again and says what was there was not kept", "What was there before was not kept" in text)
        log.check("the hand edit is gone: the index is byte for byte what it was before the edit", data(copy_index) == clean)

        log.part("PART 7. Stretch goals: a text search, and the index's age")
        code, text = log.run(INDEX_PY, "find", "footer", *there)
        log.check("the search finds the two issues that mention a footer, and says it searched the records, not the index",
                  answers(text) == ["acme-fixture/website#14", "acme-fixture/website#5"] and "searching the RECORDS" in text)
        code, text = log.run(INDEX_PY, "check", *there)
        log.check("the check reports the index's age, and how many records were written after it: 0",
                  bool(re.search(r"age: the index file was last written \d+ seconds? ago\. Record files written after it: 0", text)))
        log.out("The age is reported by the check and is not stored in the index, so that two builds stay identical.")
        log.scratch = None

    log.part("PART 8. The handed-in index, and its statement (criterion 7)")
    for line in first.decode("utf-8").split("\n")[:14]:
        log.out("  | " + line)
    head = first.decode("utf-8").split("\n")
    log.check("the index is headed by the statement that it is generated and is not the source of truth, and names the records as the source",
              head[2].startswith("**This file is generated. It is not the source of truth, and it must not be edited by hand.**") and "truth is the issue records in `issues/`" in head[3])
    log.check("%s is still byte for byte what part 1 built: SHA-256 %s" % (INDEX, digest(first)), data(INDEX) == first)
    log.check("the twelve records were not changed by any of this: this script read them again", own_records(RECORDS) == records)
    return 0 if log.save("index-run.txt") else 1


if __name__ == "__main__":
    sys.exit(main())

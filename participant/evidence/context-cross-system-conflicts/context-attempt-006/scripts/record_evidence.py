#!/usr/bin/env python3
"""Records logs/conflict-run.txt for the quest context-cross-system-conflicts. It contacts nothing.

    python3 participant/evidence/context-cross-system-conflicts/context-attempt-006/scripts/record_evidence.py

It runs the report on the handed-in records, writing to a scratch folder, SCRATCH, which is deleted at the end. It
changes nothing in participant/context/conflicts, and it checks that.
"""
import copy
import hashlib
import json
import os
import random
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "participant", "skills", "context-cross-system-conflicts"))
import conflicts      # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FOLDER = conflicts.FOLDER
COMMAND = "python3 participant/skills/context-cross-system-conflicts/conflicts.py report"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def digests():
    return {name: hashlib.sha256(read(os.path.join(FOLDER, name)).encode()).hexdigest() for name in sorted(os.listdir(FOLDER))}


class Log:
    def __init__(self):
        self.lines = ["The conflict run. context-cross-system-conflicts, attempt context-attempt-006",
                      "Recorded by scripts/record_evidence.py. No request was sent anywhere. Every record is made up."]
        self.failed, self.count = [], 0

    def out(self, *lines):
        self.lines.extend(lines or [""])

    def part(self, title, *lines):
        self.lines += ["", "=" * 78, title, *lines]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %s %s" % ("ok  " if ok else "FAIL", label))
        if not ok:
            self.failed.append(label)


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-conflicts-")
    records_path, previous_path = os.path.join(FOLDER, "records.md"), os.path.join(FOLDER, "previous-run.json")
    try:
        log.part("PART 1. The run, on participant/context/conflicts/records.md (criterion 4: no value is overwritten)")
        before = digests()
        log.out("SHA-256 of every file in participant/context/conflicts before the run:", *["  %s  %s" % (value, name) for name, value in before.items()])
        said = []
        out = os.path.join(scratch, "report.md")
        code = conflicts.main(["report", "--records", records_path, "--previous", previous_path, "--out", out], say=said.append)
        log.out("$ %s --previous participant/context/conflicts/previous-run.json --out SCRATCH/report.md" % COMMAND, "-" * 78, *said, "-" * 78, "exit code: %d" % code)
        after = digests()
        log.out("SHA-256 after the run:", *["  %s  %s  %s" % (value, name, "same" if before[name] == value else "CHANGED") for name, value in after.items()])
        log.check("the run finished: exit code 0", code == 0)
        log.check("records.md is byte for byte what it was. No record was changed", after["records.md"] == before["records.md"])
        log.check("no file in the folder was changed, added or removed by the run", after == before)
        refused = conflicts.main(["report", "--records", records_path, "--out", records_path], say=said.append)
        log.out("Told to write its report over the records file itself:", "  " + said[-1])
        log.check("it refuses, with exit code 1, and the records file is still unchanged", refused == 1 and "refused to write over the records file" in said[-1] and digests() == before)
        report = read(out)
        log.check("the report it wrote is the handed-in report, participant/context/conflicts/report.md, byte for byte", report == read(os.path.join(FOLDER, "report.md")))

        records, links, depends = conflicts.read_records(read(records_path))
        previous = json.loads(read(previous_path))
        found = conflicts.analyse(records, links, depends, previous)

        log.part("PART 2. What the report says, case by case (criteria 1, 2, 3, 5 and 7)",
                 "Each piece of work in records.md was made up to be one case. The answer the report gives for each pair of systems, for the field the case is about:")
        about = dict(re.findall(r"^#### (W-\d+)\n\n(.+)$", read(records_path), re.M))
        wanted = {"W-01": ("status", ["agree"] * 3), "W-02": ("status", ["conflict", "conflict", "not comparable"]), "W-03": ("status", ["lag", "agree", "lag"]), "W-04": ("status", ["conflict"]),
                  "W-05": ("status", ["not comparable"]), "W-06": ("status", ["conflict"]), "W-07": ("status", ["conflict"]), "W-08": ("status", ["conflict"]), "W-09": ("status", ["lag"]),
                  "W-10": ("status", ["lag"]), "W-11": ("status", ["conflict"]), "W-12": ("due", ["conflict", "not comparable", "not comparable"]), "W-13": ("assigned", ["lag"])}
        for work in found["works"]:
            field, answers = wanted[work["work"]]
            pairs = [pair for pair in work["pairs"] if pair["field"] == field]
            log.out("  %s  %s" % (work["work"], about.get(work["work"], "")))
            for pair in pairs:
                log.out("        %s: %s %s against %s %s -> %s" % (field, pair["a"].split(":")[0], json.dumps(conflicts.value_of(records[pair["a"]], field)), pair["b"].split(":")[0],
                                                                 json.dumps(conflicts.value_of(records[pair["b"]], field)), pair["class"].upper()), "            %s" % pair["why"])
            log.check("%s: %s" % (work["work"], ", ".join(answers)), [pair["class"] for pair in pairs] == answers)
        log.check("the quest's scenario, W-02, is reported as a conflict: done in the tracker against in progress on the board, and against open in the repository",
                  [one["work"] for one in found["conflicts"]].count("W-02") == 2)
        blocks = report.split("## Differences judged to be lag")[0].split("\n### ")[1:]
        rows = lambda block: [line for line in block.split("\n") if line.startswith("| ") and not line.startswith("| System")]
        log.check("each of the %d conflicts shows two rows: two systems, two values, what each source itself wrote, and when each last changed (criterion 2)" % len(blocks),
                  len(blocks) == 8 and all(len(rows(block)) == 2 and len(set(row.split(" | ")[0] for row in rows(block))) == 2 for block in blocks))
        log.check("each conflict says why it is one, and what a person would need to find out to settle it (the quest's hint)",
                  all("**Why it is a conflict:**" in block and "**To settle it, a person would need to find out:**" in block for block in blocks))
        log.check("every pair compared is two records from different systems that one link names, by identity (criterion 1)",
                  all(pair["a"] in work["members"] and pair["b"] in work["members"] and pair["a"].split(":")[0] != pair["b"].split(":")[0] for work in found["works"] for pair in work["pairs"]))
        total = sum(len(work["pairs"]) for work in found["works"])
        table = report.split("## Every comparison made")[1].split("## The links used")[0]
        log.check("all %d comparisons are listed in the report with the answer and the reason, so a reader can see why each was or was not a conflict (criterion 7)" % total,
                  len(re.findall(r"^\| W-\d+ \|", table, re.M)) == total and all(len(pair["why"]) > 10 for work in found["works"] for pair in work["pairs"]))

        log.part("PART 3. The lag rule at its edges (criterion 3)")
        rec = lambda system, status, updated: {"identity": system + ":x", "system": system, "title": "t", "status": status, "assignee_count": 1, "due_at": None, "updated_at": updated, "as_sent": {}}
        trials = [("exactly 24 hours apart, the later one further along", rec("jira", "in_progress", "2026-11-19T09:00:00Z"), rec("trello", "done", "2026-11-20T09:00:00Z"), "lag"),
                  ("24 hours and 1 second apart", rec("jira", "in_progress", "2026-11-19T09:00:00Z"), rec("trello", "done", "2026-11-20T09:00:01Z"), "conflict"),
                  ("5 minutes apart, the later one LESS far along", rec("jira", "done", "2026-11-17T09:00:00Z"), rec("trello", "in_progress", "2026-11-17T09:05:00Z"), "conflict"),
                  ("the same moment, written in two time zones", rec("trello", "done", "2026-11-15T12:00:00Z"), rec("jira", "open", "2026-11-15T07:00:00-05:00"), "conflict"),
                  ("done against dropped, one second apart", rec("jira", "done", "2026-11-16T10:00:00Z"), rec("github", "dropped", "2026-11-16T10:00:01Z"), "conflict"),
                  ("one record with no time of last change", rec("jira", "in_progress", None), rec("trello", "done", "2026-11-14T16:00:00Z"), "conflict"),
                  ("in progress against GitHub's open, a year apart", rec("jira", "in_progress", "2026-11-12T11:00:00Z"), rec("github", "open", "2025-11-12T11:00:00Z"), "not comparable")]
        for title, first, second, answer in trials:
            kind, why, _ = conflicts.compare(first, second, "status")
            back = conflicts.compare(second, first, "status")[0]
            log.out("  %s: %s" % (title, kind.upper()), "      %s" % why)
            log.check("%s: %s, whichever record is given first" % (title, answer), kind == answer and back == answer)
        log.check("the allowance is measured between the two records' own times. The skill reads no clock, so the answer is the same on any day",
                  not re.search(r"\.now\(|\.today\(|utcnow|\btime\.time\(|getmtime", read(os.path.join(REPO, "participant", "skills", "context-cross-system-conflicts", "conflicts.py"))))

        log.part("PART 4. No winner is chosen (criterion 4)")
        body = report.split("## Summary")[1].lower().replace("which side is right", "")
        words = ("winner", "correct value", "should be", "is right", "is wrong", "stale", "authoritative", "resolved", "true state", "probably", "trust ")
        log.check("below its introduction the report uses none of the words that would pick a side: %s" % ", ".join(words), not any(word in body for word in words))
        log.check("no piece of work is given one resolved value: what is kept for each is its records, its link and its comparisons, and nothing else",
                  all(sorted(work) == ["members", "pairs", "stated", "work"] for work in found["works"]))
        lag = report.split("## Differences judged to be lag")[1].split("## Differences that are not comparable")[0]
        log.check("a difference judged to be lag still shows both values and both times: 5 lags, 10 rows", len(re.findall(r"^\| ", lag, re.M)) == 11 and found and lag.count("2026-11-") >= 10)

        log.part("PART 5. Records with no counterpart (criterion 5)")
        log.out("Unlinked records: %s" % ", ".join(found["unlinked"]), "Links that could not be used:", *["  %s: %s" % problem for problem in found["problems"]],
                "Same title, not linked: %s" % "; ".join("%s: %s" % (json.dumps(title), ", ".join(names)) for title, names in found["same_title"]))
        log.check("the story with no counterpart, jira:41050, is listed as unlinked and appears in no conflict, lag or comparison",
                  "jira:41050" in found["unlinked"] and "jira:41050" not in report.split("## Unlinked records")[0])
        log.check("no unlinked record is in any conflict", not [one for one in found["conflicts"] if one["a"] in found["unlinked"] or one["b"] in found["unlinked"]])
        log.check("a card and an issue with the same title and no link were not compared. They are listed as a hint for a person, marked as not a link", len(found["same_title"]) == 1
                  and "**This is a hint for a person, not a link.**" in report and not [work for work in found["works"] if "github:I_kwFIX0450" in work["members"]])
        log.check("three faulty links are reported and not used: one names a record that is not there, and two name the same card", len(found["problems"]) == 3)

        log.part("PART 6. The same input gives the same report (criterion 6)")
        again = os.path.join(scratch, "again.md")
        conflicts.main(["report", "--records", records_path, "--previous", previous_path, "--out", again], say=lambda line: None)
        log.out("SHA-256 of the first report:  %s" % hashlib.sha256(report.encode()).hexdigest(), "SHA-256 of the second report: %s" % hashlib.sha256(read(again).encode()).hexdigest())
        log.check("a second run on the same input gives a report that is byte for byte the same", read(again) == report)
        same = 0
        for seed in range(10):
            order = list(records)
            random.Random(seed).shuffle(order)
            shuffled_links = [dict(link, members=list(reversed(link["members"]))) for link in links]
            random.Random(seed + 50).shuffle(shuffled_links)
            shuffled = {identity: records[identity] for identity in order}
            if conflicts.render(shuffled, conflicts.analyse(shuffled, shuffled_links, depends, previous), previous["run"]) == report:
                same += 1
        log.check("with the records and the links given in 10 other orders, the report is the same every time: the order of the input plays no part", same == 10)
        changed = copy.deepcopy(records)
        changed["jira:41001"]["status"] = "open"
        log.check("and it is not the same whatever the input: with one status changed, the report differs", conflicts.render(changed, conflicts.analyse(changed, links, depends, previous), previous["run"]) != report)

        log.part("PART 7. Ranking, and conflicts that have lasted (stretch goals)")
        log.out("Conflicts in the order the report gives them, with the work that depends on each:",
                *["  %d. %s %s: %d other piece%s of work depend on it%s. Seen in the previous run: %s" % (
                    number, one["work"], one["field"], len(one["affects"]), "" if len(one["affects"]) == 1 else "s", " (%s)" % ", ".join(one["affects"]) if one["affects"] else "",
                    "yes" if one["seen_before"] else "no") for number, one in enumerate(found["conflicts"], 1)])
        counts = [len(one["affects"]) for one in found["conflicts"]]
        log.check("the conflicts are ordered by how many other pieces of work depend on them, most first", counts == sorted(counts, reverse=True) and counts[0] == 3)
        earlier = conflicts.read_records(read(os.path.join(FOLDER, "earlier-records.md")))
        earlier_keys = [list(one["key"]) for one in conflicts.analyse(*earlier)["conflicts"]]
        log.check("previous-run.json is exactly what a run on earlier-records.md writes: the %d conflicts of 16 November" % len(earlier_keys), previous == {"run": "2026-11-16", "conflicts": earlier_keys})
        log.check("6 of the 8 conflicts were already there in the previous run, and 2 are new: W-04 and W-11",
                  sorted(one["work"] for one in found["conflicts"] if not one["seen_before"]) == ["W-04", "W-11"] and sum(1 for one in found["conflicts"] if one["seen_before"]) == 6)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "conflict-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("conflict-run.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())

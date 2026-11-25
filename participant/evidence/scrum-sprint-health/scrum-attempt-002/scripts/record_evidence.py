#!/usr/bin/env python3
"""Records logs/health-run.txt for the quest scrum-sprint-health. It contacts nothing.

    python3 participant/evidence/scrum-sprint-health/scrum-attempt-002/scripts/record_evidence.py

It generates the report twice from the same snapshot, and once more from a copy kept elsewhere under another name,
into a scratch folder, and compares every byte. Then it works each number of the handed-in report out again from the
snapshot's rows, by its own short code and not by the generator's, and lists the gaps. Then it spoils the report and
the snapshot, one thing at a time. The scratch folder, SCRATCH, is deleted at the end. The snapshot and the report are
not changed, and it checks that.

What "worked out again here" covers: this script reads the table by splitting lines on the bar, and counts with its own
few lines. It does not cover a snapshot in another shape: it reads only this one.

The snapshot is made up: the project, the items, the dates and the four people are invented.
"""
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "scrum-sprint-health")
sys.path.insert(0, SKILL)
import health as hl  # noqa: E402

SCRUM = os.path.join(REPO, "participant", "context", "scrum")
SNAPSHOT = os.path.join(SCRUM, "sprint-snapshot.md")
PREVIOUS = os.path.join(SCRUM, "health", "day-06", "sprint-snapshot.md")
REPORT = os.path.join(SCRUM, "sprint-health.md")
DAY6 = os.path.join(SCRUM, "health", "day-06", "sprint-health.md")
LOGS = os.path.join(HERE, "..", "logs")
REL = lambda p: os.path.relpath(p, REPO)  # noqa: E731


def raw(path):
    with open(path, "rb") as f:
        return f.read()


def digest(path):
    return hashlib.sha256(raw(path)).hexdigest()


class Log:
    def __init__(self):
        self.lines = ["The health run. scrum-sprint-health, attempt scrum-attempt-002",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere and nothing was posted to any tracker.",
                      "The snapshot is made up. Paths are from the repository's top folder. SCRATCH is a temporary folder, deleted at the end."]
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


def section(text, number):
    return dict(re.findall(r"^## (\d)\. [^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)).get(str(number), "")


def ids(text):
    return re.findall(r"`([A-Z]+-\d+)`", text)


def line_of(text, start):
    return next((l for l in text.split("\n") if l.startswith(start)), "")


def own_reading(snapshot_text):
    """The rows of the snapshot, read here with no help from health.py: a list of dicts, a blank cell as ''."""
    rows = []
    for line in snapshot_text.split("## Items")[1].split("## ")[0].strip().split("\n")[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(dict(zip(["id", "title", "status", "assignee", "created", "updated", "blocked_by", "depends_on"], cells)))
    return rows


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-health-")
    before = {p: digest(p) for p in (SNAPSHOT, PREVIOUS, REPORT, DAY6)}
    snapshot, report = hl.read(SNAPSHOT), hl.read(REPORT)
    command = ["participant/skills/scrum-sprint-health/health.py", "generate", "--snapshot", REL(SNAPSHOT), "--previous", REL(PREVIOUS)]

    log.part("PART 1. The report generated twice from the same snapshot (criterion 7)")
    runs = []
    for which in ("first", "second"):
        out = os.path.join(scratch, which, "sprint-health.md")
        done = subprocess.run([sys.executable] + command + ["--out", out], cwd=REPO, capture_output=True, text=True)
        log.out("$ python3 %s --out SCRATCH/%s/sprint-health.md" % (" ".join(command), which), *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
        runs.append(raw(out))
        if which == "first":
            time.sleep(2)
    log.out("The two runs were started 2 seconds apart.", "  first:  %d bytes, sha256 %s" % (len(runs[0]), hashlib.sha256(runs[0]).hexdigest()), "  second: %d bytes, sha256 %s" % (len(runs[1]), hashlib.sha256(runs[1]).hexdigest()))
    log.check("the two reports are byte for byte the same, and are not empty", runs[0] == runs[1] and len(runs[0]) > 0)
    log.check("the handed-in report, participant/context/scrum/sprint-health.md, is byte for byte what these runs wrote", raw(REPORT) == runs[0])
    elsewhere = os.path.join(scratch, "elsewhere", "deep")
    os.makedirs(elsewhere)
    shutil.copyfile(SNAPSHOT, os.path.join(elsewhere, "today.md"))
    shutil.copyfile(PREVIOUS, os.path.join(elsewhere, "before.md"))
    done = subprocess.run([sys.executable, os.path.join(SKILL, "health.py"), "generate", "--snapshot", "today.md", "--previous", "before.md", "--out", "out.md"], cwd=elsewhere, capture_output=True, text=True)
    log.out("", "A third run, from copies of the two snapshots under other names in another folder, started from that folder:",
            "$ python3 health.py generate --snapshot today.md --previous before.md --out out.md", *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode)
    log.check("the third report is byte for byte the same as the first: the bytes do not depend on where the files are or what they are called", done.returncode == 0 and raw(os.path.join(elsewhere, "out.md")) == runs[0])
    log.check("the snapshots were not changed by generating", digest(SNAPSHOT) == before[SNAPSHOT] and digest(PREVIOUS) == before[PREVIOUS])
    source = hl.read(os.path.join(SKILL, "health.py"))
    log.check("health.py has none of the calls that ask for the time: datetime.now, utcnow, time.time, today(), date.today, localtime, gmtime",
              not any(call in source for call in ("datetime.now", "utcnow", "today()", "date.today", "localtime", "gmtime", "import time")) and not re.search(r"(?<![a-z])time\.time", source))
    imports = sorted(set(re.findall(r"^(?:import|from) (\w+)", source, re.M)))
    log.out("Modules health.py imports: %s." % ", ".join(imports))
    log.check("it imports only these six, and has no call that starts a program or imports by name", imports == ["argparse", "datetime", "hashlib", "os", "re", "sys"] and not re.search(r"os\.(system|popen|exec\w*|spawn\w*|fork)|__import__|importlib|subprocess", source))
    later = hl.build(snapshot.replace("- snapshot_date: 2026-11-17", "- snapshot_date: 2026-11-18"))
    log.out("", "A contrast: the same snapshot with its own snapshot_date changed to the next day, in memory.")
    log.check("with the snapshot's date a day later, the age of FERRY-203 goes from 6 to 7. So the day counted to is the snapshot's field", later["info"]["FERRY-203"]["age"] == 7 and hl.build(snapshot)["info"]["FERRY-203"]["age"] == 6)

    rows = own_reading(snapshot)
    by_id = {r["id"]: r for r in rows}
    day = lambda text: datetime.date(*map(int, text.split("-")))  # noqa: E731
    today = day(re.search(r"^- snapshot_date: (\S+)$", snapshot, re.M).group(1))
    threshold = int(re.search(r"^- aging_after_days: (\d+)$", snapshot, re.M).group(1))
    limit = int(re.search(r"^- wip_limit_per_person: (\d+)$", snapshot, re.M).group(1))

    log.part("PART 2. The snapshot (the first required item)")
    blank = {name: sorted(r["id"] for r in rows if r[name] == "") for name in ("status", "assignee", "created", "updated", "blocked_by", "depends_on")}
    log.out("%s, sha256 %s" % (REL(SNAPSHOT), before[SNAPSHOT]), "Rows: %d. Columns: id, title, status, assignee, created, updated, blocked_by, depends_on." % len(rows),
            "Blank cells, by column: " + "; ".join("%s: %s" % (name, ", ".join(found) or "none") for name, found in blank.items()) + ".")
    log.check("the snapshot has at least twenty work items: %d" % len(rows), len(rows) >= 20)
    log.check("every row has eight cells, and %d cells in all are blank" % sum(len(v) for v in blank.values()), all(len(r) == 8 for r in rows) and sum(len(v) for v in blank.values()) >= 4)
    log.check("the snapshot says it is made up, and records its own date, an aging threshold of 3 and a limit on work in progress of 2", "**Made up.**" in snapshot.split("## ")[0] and threshold == 3 and limit == 2)
    log.check("the report gives the checksum of the bytes of this snapshot, and no path to it", "sha256 is `%s`" % before[SNAPSHOT] in report and "sprint-snapshot.md" not in report)

    log.part("PART 3. Each number of the report, worked out again here from the snapshot's rows (criteria 1 to 5)",
             "The counts below are made by this script's own few lines, not by health.py. Each is compared with what the report lists.")
    for status, start in (("done", "- Done ("), ("in_progress", "- In progress ("), ("todo", "- Not started (")):
        mine = sorted(r["id"] for r in rows if r["status"] == status)
        theirs = sorted(ids(line_of(section(report, 1), start)))
        log.out("  status %-11s here: %2d   in the report: %2d   %s" % (status, len(mine), len(theirs), ", ".join(mine)))
        log.check("criterion 1: the report lists as %s exactly the %d items whose status is %s" % (status, len(mine), status), mine == theirs)
    odd = sorted(r["id"] for r in rows if r["status"] not in ("todo", "in_progress", "done"))
    counts = [sum(1 for r in rows if r["status"] == s) for s in ("done", "in_progress", "todo")]
    log.check("criterion 1: the first line of section 1 gives these totals: %d of %d with a usable status, %d done, %d in progress, %d not started" % (sum(counts), len(rows), counts[0], counts[1], counts[2]),
              "- Items with a status the report can use: %d of %d. Done: %d. In progress: %d. Not started: %d." % (sum(counts), len(rows), counts[0], counts[1], counts[2]) in section(report, 1))
    log.check("criterion 1: the %d items with a blank or unrecognised status are in none of the three lists, and are named as in none: %s" % (len(odd), ", ".join(odd)),
              sorted(ids(line_of(section(report, 1), "- In none of the three"))) == odd and all(i not in "".join(line_of(section(report, 1), s) for s in ("- Done (", "- In progress (", "- Not started (")) for i in odd))
    log.check("criterion 1: section 1 names every one of the %d items exactly once" % len(rows), sorted(ids(section(report, 1))) == sorted(by_id))

    def usable(r, to):
        try:
            return r["updated"] != "" and day(r["updated"]) <= to and (r["created"] == "" or day(r["created"]) <= day(r["updated"]))
        except ValueError:
            return False

    def weekend(first, last):
        count, at = 0, first
        while at < last:
            at += datetime.timedelta(days=1)
            count += 1 if at.strftime("%a") in ("Sat", "Sun") else 0
        return count
    aged = {r["id"]: (today - day(r["updated"])).days for r in rows if r["status"] == "in_progress" and usable(r, today)}
    mine = sorted(i for i, days in aged.items() if days > threshold)
    fresh = sorted(i for i, days in aged.items() if days <= threshold)
    log.out("", "  in progress, with a usable update date, and the days from it to %s: %s" % (today, ", ".join("%s %d" % pair for pair in sorted(aged.items()))))
    log.check("criterion 2: the report shows the threshold, %d days, says it is the snapshot's own, and says the days are calendar days" % threshold,
              "- Aging threshold: %d days, the snapshot's own `aging_after_days`." % threshold in report and "**Calendar days: a Saturday and a Sunday count.**" in report)
    log.check("criterion 2: the report lists as aging exactly the %d items in progress last updated more than %d days before the snapshot: %s" % (len(mine), threshold, ", ".join(mine)), sorted(ids(line_of(section(report, 2), "- Aging ("))) == mine)
    log.check("criterion 2: it lists as not aging exactly the other %d with a usable date: %s" % (len(fresh), ", ".join(fresh)), sorted(ids(line_of(section(report, 2), "- In progress and not aging ("))) == fresh)
    shown = {i: (name, when, int(days), int(ends)) for i, name, when, days, ends in
             re.findall(r"^  - `([A-Z0-9-]+)`: `updated` is (\w+) (\S+), (\d+) days? before the snapshot\. Of those days, (\d+) (?:is|are) a Saturday or Sunday\.$", section(report, 2), re.M)}
    expected = {i: (day(by_id[i]["updated"]).strftime("%a"), by_id[i]["updated"], aged[i], weekend(day(by_id[i]["updated"]), today)) for i in aged}
    log.out("  the same, with the weekday and the Saturdays and Sundays inside each age, worked out here: %s" % ", ".join("%s %s %dd %dwe" % (i, v[0], v[2], v[3]) for i, v in sorted(expected.items())))
    log.check("criterion 2: all %d of these items are shown with their update date, its weekday, the number of days and how many of them are a Saturday or Sunday, and all four are what is worked out here" % len(aged), shown == expected and len(aged) == 10)
    day6 = hl.read(DAY6)
    earlier = {r["id"]: r for r in own_reading(hl.read(PREVIOUS))}
    on_it = sorted(i for i, r in earlier.items() if r["status"] == "in_progress" and usable(r, today - datetime.timedelta(days=1)) and (today - datetime.timedelta(days=1) - day(r["updated"])).days == threshold)
    log.out("  in the snapshot of the day before, items in progress at exactly %d days: %s" % (threshold, ", ".join(on_it) or "none"))
    log.check("criterion 2: an item at exactly the threshold is not aging. In the report of the day before, FERRY-209 is at exactly 3 days and is listed as not aging",
              on_it == ["FERRY-209"] and "FERRY-209" in ids(line_of(section(day6, 2), "- In progress and not aging (")) and "FERRY-209" not in ids(line_of(section(day6, 2), "- Aging (")))

    mine_blocked = sorted(r["id"] for r in rows if r["blocked_by"] not in ("", "none") and r["status"] != "done")
    log.out("", "  rows not done whose blocked_by names something: %s" % ", ".join("%s (%s)" % (i, by_id[i]["blocked_by"]) for i in mine_blocked))
    log.check("criterion 3: the report lists as blocked exactly those %d items" % len(mine_blocked), sorted(ids(line_of(section(report, 3), "- Recorded as blocked, and not done ("))) == mine_blocked)
    said = dict(re.findall(r"^  - `([A-Z0-9-]+)`: `blocked_by` is ([^.]*)\.", section(report, 3), re.M))
    log.check("criterion 3: beside each it gives the blocker, and it is the one in the item's blocked_by cell", said == {i: by_id[i]["blocked_by"] for i in mine_blocked})
    titled = [r["id"] for r in rows if "block" in r["title"].lower()]
    log.out("  rows whose TITLE has the word blocked in it: %s. Its blocked_by is: %s." % (", ".join(titled), ", ".join(by_id[i]["blocked_by"] for i in titled)))
    log.check("criterion 3: the item whose title begins \"BLOCKED:\" is not in the blocked section, and its blocked_by says none", titled == ["FERRY-211"] and by_id["FERRY-211"]["blocked_by"] == "none" and "FERRY-211" not in section(report, 3))

    people = {}
    for r in rows:
        if r["status"] == "in_progress" and r["assignee"] not in ("", "unassigned"):
            people.setdefault(r["assignee"], []).append(r["id"])
    log.out("", *("  %-17s %d in progress: %s" % (person, len(found), ", ".join(sorted(found))) for person, found in sorted(people.items())))
    lines = {m.group(1): m for m in re.finditer(r"^- \"([^\"]*)\": (\d+) in progress \(([^)]*)\)\.(.*)$", section(report, 4), re.M)}
    log.check("criterion 4: for each of the %d names the report gives the number of items in progress and lists them, and both are these" % len(people),
              {p: (int(m.group(2)), sorted(ids(m.group(3)))) for p, m in lines.items()} == {p: (len(f), sorted(f)) for p, f in people.items()})

    def beside(n):
        return "this is %d more than the limit" % (n - limit) if n > limit else "this is at the limit" if n == limit else "this is %d under the limit" % (limit - n)
    log.out("  each count set beside the limit of %d, worked out here: %s" % (limit, "; ".join("%s: %s" % (p, beside(len(f))) for p, f in sorted(people.items()))))
    log.check("criterion 4: the limit is stated, %d, as the snapshot's own, and each of the %d counts is set beside it as worked out here" % (limit, len(people)),
              "- Limit on work in progress: %d for each person, the snapshot's own `wip_limit_per_person`." % limit in report and len(lines) == len(people)
              and all(" The recorded limit is %d: %s. Of these," % (limit, beside(len(people[p]))) in m.group(4) for p, m in lines.items()))
    log.check("each count also says which of its items are recorded as blocked and which are aging, and those are the ones worked out above",
              all("Of these, recorded as blocked: %s. Aging: %s." % (", ".join("`%s`" % i for i in sorted(people[p]) if i in mine_blocked) or "none", ", ".join("`%s`" % i for i in sorted(people[p]) if i in mine) or "none") in m.group(4) for p, m in lines.items()))
    untold = lambda p: ", ".join("`%s`" % i for i in sorted(people[p]) if by_id[i]["updated"] == "" or by_id[i]["blocked_by"] == "") or "none"  # noqa: E731
    log.check("and where an item's update date or blocked_by is blank, the count says it cannot be told for that item, and does not say none: FERRY-218, beside the name it is recorded against",
              all("One or the other cannot be told for: %s." % untold(p) in m.group(4) for p, m in lines.items()) and [untold(p) for p in sorted(people)].count("none") == 3 and "`FERRY-218`" in untold(by_id["FERRY-218"]["assignee"]))
    nolimit = hl.render(hl.build(re.sub(r"^- wip_limit_per_person: .*\n", "", snapshot, flags=re.M)), "x" * 64)
    log.check("criterion 4: with the limit line taken out of the snapshot, in memory, the report says none is set, compares no count with one, and adds no gap",
              "- Limit on work in progress: none is set: the snapshot records no `wip_limit_per_person`." in nolimit and "the limit" not in section(nolimit, 4).replace("No limit on work in progress can be used", "") and "Entries: 8." in nolimit)
    badlimit = hl.render(hl.build(snapshot.replace("- wip_limit_per_person: 2", "- wip_limit_per_person: two")), "x" * 64)
    log.check("criterion 4: with the limit written as \"two\", in memory, the report does not say none is set. It says one is recorded and cannot be used, and lists a gap",
              "none is set" not in badlimit and "- Limit on work in progress: one is recorded, as \"two\", and cannot be used" in badlimit and "- [GAP] `the snapshot`, field `wip_limit_per_person`: it is \"two\"" in badlimit)
    log.check("criterion 4: the item in progress whose assignee is blank is counted for nobody", "FERRY-219" not in sum(people.values(), []) and ids(line_of(section(report, 4), "- In progress, with an `assignee` that cannot be used")) == ["FERRY-219"])

    live = ("todo", "in_progress")
    waits = sorted({(r["id"], y) for r in rows if r["status"] in live for field in ("blocked_by", "depends_on") for y in ([] if r[field] in ("", "none") else [p.strip() for p in r[field].split(",")])
                    if y in by_id and by_id[y]["status"] in live})
    s5 = section(report, 5)
    risky, rest = s5.split("- Waits where none of D1")[0], "- Waits where none of D1" + s5.split("- Waits where none of D1")[1]
    risk_lines = [l for l in risky.split("\n") if l.startswith("  - `") and "(in its" in l]
    theirs = [re.match(r"  - `([A-Z0-9-]+)` waits on `([A-Z0-9-]+)` \(in its `(blocked_by|depends_on)`(?: and `(depends_on)`)?\)\.", l).groups() for l in risk_lines]
    others = re.findall(r"`([A-Z0-9-]+)` (?:waits )?on `([A-Z0-9-]+)`", rest.split("- Links that could not")[0])
    log.out("", "  waits, worked out here: an item not done whose blocked_by or depends_on names an item not done: %s" % ", ".join("%s on %s" % w for w in waits))
    log.check("criterion 5: the %d waits worked out here are exactly the waits in the report, each once, as a risk or under one of the two headings for waits that are not" % len(waits), sorted([(x, y) for x, y, _, _ in theirs] + others) == waits)
    on = sorted({y for _, y in waits})
    log.check("criterion 5: the report gives the total as %d waits on %d different items, and names those items" % (len(waits), len(on)), "- Waits in all: %d, on %d different items: %s." % (len(waits), len(on), ", ".join("`%s`" % i for i in on)) in s5)

    def reasons(y):
        return sorted(n for n, holds in (("D1", by_id[y]["status"] == "todo"), ("D2", by_id[y]["assignee"] == "unassigned"), ("D3", y in mine), ("D4", any(x == y for x, _ in waits))) if holds)
    mine_risks = {(x, y): reasons(y) for x, y in waits if reasons(y)}
    log.out("  the reasons, worked out here for each wait: %s" % "; ".join("%s on %s: %s" % (x, y, " ".join(why)) for (x, y), why in sorted(mine_risks.items())))
    log.check("criterion 5: the report calls a risk exactly the %d waits for which one of D1 to D4 holds here, and gives each exactly the reasons worked out here" % len(mine_risks),
              {(m[0], m[1]): sorted(re.findall(r"\b(D[1-4]): ", l)) for m, l in zip(theirs, risk_lines)} == mine_risks and len(mine_risks) == len(risk_lines) > 0)
    fields = {(x, y): [f for f in ("blocked_by", "depends_on") if y in [p.strip() for p in by_id[x][f].split(",")]] for x, y in mine_risks}
    log.check("criterion 5: each risk names both items and the field or fields the link is in, and those are the cells that hold it", {(m[0], m[1]): [f for f in m[2:] if f] for m in theirs} == fields)
    log.check("criterion 5: every reason given names the field it is read from", all(re.search(r"D1: [^.]*`status`", l) or "D1: " not in l for l in risk_lines) and all(re.search(r"D2: [^.]*`assignee`", l) or "D2: " not in l for l in risk_lines)
              and all(re.search(r"D3: [^.]*`updated`", l) or "D3: " not in l for l in risk_lines) and all(re.search(r"D4: [^.]*\(in its `", l) or "D4: " not in l for l in risk_lines))
    log.check("the scenario's case is reported: FERRY-208 and FERRY-209 both wait on FERRY-207, whose status is todo and whose assignee is unassigned",
              "  - `FERRY-207` is waited on by 2 items: `FERRY-208`, `FERRY-209`." in s5 and by_id["FERRY-207"]["assignee"] == "unassigned" and by_id["FERRY-207"]["status"] == "todo")
    log.check("stretch: a chain of three is reported whole: FERRY-210 waits on FERRY-208 waits on FERRY-207, and each of the two links is among the waits worked out here",
              "  - `FERRY-210` waits on `FERRY-208` waits on `FERRY-207`." in s5 and ("FERRY-210", "FERRY-208") in waits and ("FERRY-208", "FERRY-207") in waits)
    log.check("the two items that depend on each other are reported as a loop and not as a chain", "  - `FERRY-216`, `FERRY-224`. By the snapshot, each of them is recorded as waiting on another of them." in s5 and "- Chains of three items or more (1):" in s5)

    log.part("PART 4. The gaps the report gives for items with missing fields (criterion 6)")
    gap_lines = [l for l in section(report, 6).split("\n") if l.startswith("- [GAP]")]
    log.out(*("  " + l for l in gap_lines), "")
    blank_cells = sorted((r["id"], name) for r in rows for name in ("status", "assignee", "created", "updated", "blocked_by", "depends_on") if r[name] == "")
    log.out("  blank cells in the snapshot, found here: %s" % ", ".join("%s %s" % pair for pair in blank_cells))
    log.check("criterion 6: each of the %d blank cells in the snapshot has its own gap entry, naming the item and the field" % len(blank_cells), len(blank_cells) == 4 and all(sum(1 for l in gap_lines if l.startswith("- [GAP] `%s`, field `%s`: it is blank" % pair)) == 1 for pair in blank_cells))
    log.check("criterion 6: the section holds %d entries, says so, and the top of the report gives the same number" % len(gap_lines), "Entries: %d." % len(gap_lines) in section(report, 6) and "Gaps reported in section 6: %d." % len(gap_lines) in report and len(gap_lines) == 8)
    log.check("criterion 6: every gap entry says what the item is left out of", all(re.search(r"\. Left out of: \S", l) for l in gap_lines))
    log.check("criterion 6, not estimated. FERRY-217, no status: in the line for none of the three statuses, and in no other line of section 1",
              "FERRY-217" in ids(line_of(section(report, 1), "- In none of the three")) and section(report, 1).count("FERRY-217") == 1)
    log.check("criterion 6, not estimated. FERRY-218, no update date: in the line for cannot be told, and in neither the aging nor the not aging line",
              ids(line_of(section(report, 2), "- In progress, and whether it is aging cannot be told")) == ["FERRY-218"] and section(report, 2).count("FERRY-218") == 1)
    log.check("criterion 6, not estimated. FERRY-220, no blocked_by: in the line for cannot be told, and not in the blocked list",
              ids(line_of(section(report, 3), "- Whether it is blocked cannot be told")) == ["FERRY-220"] and section(report, 3).count("FERRY-220") == 1)
    log.check("the item the report could not classify is named as that: FERRY-222, whose status is \"in_review\"", sum(1 for l in gap_lines if "`FERRY-222`, field `status`: it is \"in_review\"" in l and "The report cannot classify it" in l) == 1 and by_id["FERRY-222"]["status"] == "in_review")
    log.check("a field that is recorded as empty is not a gap: FERRY-207 is recorded as unassigned, and has no gap entry", by_id["FERRY-207"]["assignee"] == "unassigned" and not any("`FERRY-207`" in l for l in gap_lines))
    s8 = section(report, 8)
    log.check("all %d titles are in section 8, each between double quotes beside its identifier, and none is anywhere before it" % len(rows),
              all("- `%s`: \"%s\"" % (r["id"], r["title"]) in s8 for r in rows) and not any(r["title"] in report.split("## 8.")[0] for r in rows))

    log.part("PART 5. Stretch: what changed since the day before")
    change_lines = [l for l in section(report, 7).split("\n") if l.startswith("- [CHANGE]")]
    log.out(*("  " + l for l in change_lines))
    yesterday = today - datetime.timedelta(days=1)
    both = sorted(set(by_id) & set(earlier))
    mine_changes = [("ADDED", i) for i in sorted(set(by_id) - set(earlier))] + [("REMOVED", i) for i in sorted(set(earlier) - set(by_id))]
    mine_changes += [("STATUS", i) for i in both if earlier[i]["status"] != by_id[i]["status"]]
    mine_changes += [("BLOCKED_BY", i) for i in both if earlier[i]["blocked_by"] != by_id[i]["blocked_by"]] + [("DEPENDS_ON", i) for i in both if earlier[i]["depends_on"] != by_id[i]["depends_on"]]
    mine_changes += [("NEWLY AGING", i) for i in both if i in mine and earlier[i]["status"] == "in_progress" and usable(earlier[i], yesterday) and (yesterday - day(earlier[i]["updated"])).days <= threshold]
    log.out("", "  the differences between the two snapshots in the fields the section says it compares, found here: %s" % ", ".join("%s %s" % c for c in sorted(mine_changes)))
    log.check("the %d changes reported are exactly these, by kind and by item" % len(change_lines), sorted(re.match(r"- \[CHANGE\] ([A-Z_ ]+): .*?`([A-Z]+-\d+)`", l).groups() for l in change_lines) == sorted(mine_changes) and len(mine_changes) == 5)
    log.check("the section names the previous snapshot by the checksum of its bytes, and says what it compares and what it does not", "sha256 is `%s`" % before[PREVIOUS] in section(report, 7) and "**Compared:**" in section(report, 7) and "**Not compared:**" in section(report, 7))

    log.part("PART 6. The check, and that it can fail")
    done = subprocess.run([sys.executable, os.path.join(SKILL, "health.py"), "check", "--snapshot", SNAPSHOT, "--previous", PREVIOUS, "--report", REPORT], capture_output=True, text=True)
    log.out("$ python3 participant/skills/scrum-sprint-health/health.py check --snapshot %s --previous %s --report %s" % (REL(SNAPSHOT), REL(PREVIOUS), REL(REPORT)), *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
    log.check("the check reports no problem on the handed-in report", done.returncode == 0 and "CHECK PASSED" in done.stdout)
    log.out("That pass shows little by itself: the check reads the snapshot with the generator's own code.", "So the report is spoiled in memory, one thing at a time, written to SCRATCH, and the check is run on it.")

    def trial(label, expect, old, new):
        found = report.count(old)
        path = os.path.join(scratch, "spoiled.md")
        hl.write(path, report.replace(old, new, 1))
        got = hl.check(SNAPSHOT, PREVIOUS, path)
        log.out("Spoiled: %s" % label, *(["    THE TEXT TO SPOIL WAS NOT FOUND"] if not found else []), *("    PROBLEM: %s" % p for p in got[:2]))
        log.check("reported: \"%s\"" % expect, found > 0 and any(expect in p for p in got))

    risk = next(l for l in report.split("\n") if l.startswith("  - `FERRY-210` waits on"))
    gap = next(l for l in report.split("\n") if l.startswith("- [GAP] `FERRY-218`"))
    trial("a count raised by one, with the same items listed", "gives the number 5 and lists 4 items", "- Done (4):", "- Done (5):")
    trial("a total in the first line of section 1 changed", "first line of section 1 does not give the counts", "can use: 22 of 24. Done: 4.", "can use: 22 of 24. Done: 9.")
    trial("an item that is not started listed as done", "does not list as done exactly", "`FERRY-214`, `FERRY-215`.", "`FERRY-214`, `FERRY-207`.")
    trial("the item with no status left out of section 1", "does not account for every item", "`FERRY-217`, `FERRY-222`. See section 6.", "`FERRY-222`. See section 6.")
    trial("an item updated the day before called aging", "does not list as aging, and as not aging, exactly", "- Aging (5): `FERRY-203`,", "- Aging (5): `FERRY-202`,")
    trial("the number of days on an aging item changed", "an update date or a number of days that is not the snapshot's", "Wed 2026-11-11, 6 days before the snapshot.", "Wed 2026-11-11, 9 days before the snapshot.")
    trial("the item with BLOCKED in its title put in the blocked list", "does not list as blocked exactly", "- Recorded as blocked, and not done (4): `FERRY-205`,", "- Recorded as blocked, and not done (4): `FERRY-211`,")
    trial("an item counted for another name", "does not count, for each person", "(`FERRY-202`, `FERRY-211`)", "(`FERRY-202`, `FERRY-219`)")
    trial("a count that is over the limit said to be at it", "does not set the count for", "The recorded limit is 2: this is 1 more than the limit.", "The recorded limit is 2: this is at the limit.")
    trial("a dependency risk taken out", "does not list as risks exactly", risk + "\n", "")
    trial("a dependency risk with its reason taken out", "does not say why it is one", " D4: `FERRY-208` is itself waiting, on `FERRY-207` (in its `blocked_by` and `depends_on`).", "")
    trial("a gap taken out", "field updated, is not in section 6", gap + "\n", "")
    trial("a judgement of a person written in", "uses the word \"overloaded\"", "this is 1 more than the limit", "is overloaded")
    trial("the number of risks changed", "does not give the number of waits", "- Waits that are a risk (7):", "- Waits that are a risk (3):")
    trial("the threshold at the top of the report changed", "does not show the aging threshold", "- Aging threshold: 3 days,", "- Aging threshold: 9 days,")
    trial("an item that is not in the snapshot named", "which is not in the snapshot", "## 2. Aging\n", "## 2. Aging\n\nSee also `FERRY-777`.\n")
    edited = os.path.join(scratch, "edited-snapshot.md")
    hl.write(edited, snapshot.replace("| FERRY-203 | Import the operator's winter timetable | in_progress |", "| FERRY-203 | Import the operator's winter timetable | done |"))
    got = hl.check(edited, PREVIOUS, REPORT)
    log.out("Spoiled: the snapshot changed after the report was made (one status), in a copy", *("    PROBLEM: %s" % p for p in got[:2]))
    log.check("reported: \"it was made from another\"", any("it was made from another" in p for p in got))
    log.out("", "What the check does not look at: the wording of each reason, the chains, the loops, the items others wait on, the weekend days,",
            "sections 7 and 8, and the lines that say what could not be told. Parts 3 to 5 above look at those, on this one report.")

    log.part("PART 7. A snapshot that is wrong in its form, tried in memory",
             "Each is the handed-in snapshot with one thing changed. Nothing is written. The claim in each is about what the generator then reports.")

    def wrong(label, text, ok):
        model = hl.build(text)
        log.out("Changed: %s" % label, "    items read: %d. gaps: %d. aging: %d." % (len(model["info"]), len(model["gaps"]), len(model["aging"])))
        log.check(ok[0], ok[1](model, hl.render(model, "x" * 64)))
    row213 = "| FERRY-213 |"
    dashes = "|" + "---|" * 8 + "\n"
    wrong("a blank line put inside the table, before the row of FERRY-213", snapshot.replace(row213, "\n" + row213),
          ("the rows after the blank line are still read: 24 items, and the same 8 gaps", lambda m, r: snapshot.count(row213) == 1 and len(m["info"]) == 24 and len(m["gaps"]) == 8))
    wrong("a line of prose put inside the table", snapshot.replace(row213, "Note: the rest are old\n" + row213),
          ("the line is a gap, quoted, and the rows after it are still read", lambda m, r: len(m["info"]) == 24 and "a line in the Items section is not a row of the table: \"Note: the rest are old\"" in r))
    wrong("the line of dashes under the table's headings taken out", snapshot.replace(dashes, ""),
          ("no row is read, no row is taken for the missing line, and it is a gap", lambda m, r: snapshot.count(dashes) == 1 and len(m["info"]) == 0 and "it is not the line of dashes" in r))
    wrong("the threshold written as \"3 days\"", snapshot.replace("- aging_after_days: 3", "- aging_after_days: 3 days"),
          ("nothing is called aging, the report does not say none is set, and it is a gap", lambda m, r: m["aging"] == [] and "Aging threshold: none is set" not in r and "- [GAP] `the snapshot`, field `aging_after_days`: it is \"3 days\"" in r))
    wrong("the threshold given twice, as 3 and as 9", snapshot.replace("- aging_after_days: 3\n", "- aging_after_days: 3\n- aging_after_days: 9\n"),
          ("neither value is used, nothing is called aging, and it is a gap", lambda m, r: m["threshold"] is None and m["aging"] == [] and "it is recorded more than once. Neither value is used" in r))
    wrong("a line \"- aging_after_days: 99\" added at the end of the file, outside the section headed The sprint", snapshot + "\n- aging_after_days: 99\n",
          ("it is not read: the threshold is still 3 and the same 5 items are aging", lambda m, r: m["threshold"] == 3 and len(m["aging"]) == 5))
    wrong("the assignee of FERRY-202 written as \"TBD\"", snapshot.replace("| FERRY-202 | Route page shows sailings | in_progress | Tamsin Okoro |", "| FERRY-202 | Route page shows sailings | in_progress | TBD |"),
          ("TBD is not counted as a person, and it is a gap", lambda m, r: "TBD" not in m["people"] and "- [GAP] `FERRY-202`, field `assignee`: it is \"TBD\"" in r and "- \"TBD\"" not in r))
    row207 = "| FERRY-207 | Agree the booking API contract |"
    wrong("a bar put inside the title of FERRY-207, so that its row has nine cells", snapshot.replace(row207, "| FERRY-207 | Agree the booking | API contract |"),
          ("FERRY-207 is not said to be absent from the snapshot: the report says its row cannot be used", lambda m, r: snapshot.count(row207) == 1 and "FERRY-207" not in m["info"] and "it names FERRY-207, whose row cannot be used" in r and "FERRY-207` is not in the snapshot" not in r))
    wrong("the heading of the header section written as \"## The Sprint\"", snapshot.replace("## The sprint\n", "## The Sprint\n"),
          ("it is a gap, and the report does not say that no threshold or limit is set", lambda m, r: snapshot.count("## The sprint\n") == 1 and m["threshold"] is None and "none is set" not in r and "it has 0 sections headed The sprint" in r))
    wrong("FERRY-217, whose status is blank, given a blocked_by of FERRY-207", snapshot.replace("| 2026-11-11 | 2026-11-16 | none | none |\n| FERRY-218", "| 2026-11-11 | 2026-11-16 | FERRY-207 | none |\n| FERRY-218"),
          ("it is not listed as blocked and not done. It is listed apart, as an item whose status cannot be used", lambda m, r: "FERRY-217" not in dict(m["blocked"]) and m["blocked_unknown"] == ["FERRY-217"]))
    wrong("FERRY-204 made to depend on FERRY-219, whose assignee is blank", snapshot.replace("| none | FERRY-203 |\n| FERRY-205", "| none | FERRY-219 |\n| FERRY-205"),
          ("the wait is not filed under \"none of D1 to D4 holds\". It is listed as one that cannot be told", lambda m, r: [(w["x"], w["y"]) for w in m["undecided"]] == [("FERRY-204", "FERRY-219")] and m["plain"] == [] and "D2 cannot be told: the `assignee` of `FERRY-219` cannot be used" in r))

    shutil.rmtree(scratch, ignore_errors=True)
    log.part("AT THE END")
    log.check("the two snapshots and the two reports are byte for byte what they were at the start, and the scratch folder is gone", {p: digest(p) for p in before} == before and not os.path.exists(scratch))
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "health-run.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(line.replace(scratch, "SCRATCH") for line in log.lines) + "\n")
    print("health-run.txt: " + log.lines[-1])
    for label in log.failed:
        print("  FAILED: " + label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())

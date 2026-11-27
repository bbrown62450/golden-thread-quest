#!/usr/bin/env python3
"""Makes the fixture and the report, twice, and records what was printed. Makes logs/reconciliation-run.txt:

    0. the fixture written: a made-up local copy, and the page that says what state each item should be given
    1. the states, as the tool states them
    2. the report generated
    3. the report generated again from the same input, in place, and then a third time into an empty temporary folder
    4. the counts of the states added up BY THIS SCRIPT, from the report, and compared with the total

It leaves the results where the quest asks for them, in participant/context/jira/reconciliation/:
fixture.md, fixture-copy.json, report.md, report.log.md and report.history.json. The last three are deleted at the
start, so that the first report below is a first report.

Each command is run as a person would run it, from the `participant` folder, and its output is copied in whole.
NO REAL JIRA IS CONTACTED: the made-up Jira is part of the tool's folder, and every item is made up.

Every check reads the output or the files. The expected state of each item is taken from the FIXTURE, which was
written beside the made-up Jira, not from the report tool. So are each stale item's age, each failed item's class
of error, the line of the fetch log each item should cite, and which items fit a second state: this script works
each out from the fixture's rows and compares. The record ends with RESULT: ALL CHECKS PASSED, or says
which did not.

Run from anywhere:  python3 scripts/record_run.py        Exit code 0 if every check passed, 1 if not.
"""
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
TOOL = "skills/jira-reconciliation-report/reconcile.py"
FAKE = "skills/jira-reconciliation-report/fake_jira.py"
OUT = "context/jira/reconciliation"
BAR = "-" * 78
sys.path.insert(0, os.path.join(PARTICIPANT, os.path.dirname(FAKE)))
ORDER = ["failed to fetch", "missing from Jira", "conflicted", "changed locally only", "stale", "not yet copied", "synchronized"]
PRIVATE_WORDS = ("Made-up private title", "Example Ltd", "example.invalid", "made-up.person", "never asked for")


class Record:
    def __init__(self):
        self.checks, self.failed = 0, []
        self.lines = ["Generating the reconciliation report twice, and checking that the counts of the states add up to the total",
                      "jira-reconciliation-report, attempt jira-attempt-022. Recorded by scripts/record_run.py.",
                      "Compared with the made-up Jira (skills/jira-reconciliation-report/fake_jira.py). Every item is made up. No real Jira was contacted.",
                      "Commands are run from the `participant` folder.", ""]

    def say(self, text=""):
        self.lines.append(text)

    def run(self, tool, arguments):
        done = subprocess.run([sys.executable, "-B", tool] + arguments, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        output = done.stdout + done.stderr
        self.say("$ python3 %s %s" % (tool, " ".join(arguments)))
        self.say(BAR)
        self.lines += output.rstrip("\n").split("\n")
        self.say(BAR)
        self.say("exit code: %d" % done.returncode)
        return done.returncode, output

    def part(self, title):
        self.say("")
        self.say("=" * 78)
        self.say(title)

    def check(self, passed, what):
        self.checks += 1
        self.say("  %s %s" % ("ok  " if passed else "FAIL", what))
        if not passed:
            self.failed.append(what)

    def close(self):
        self.say("")
        self.say("RESULT: ALL CHECKS PASSED. %d checks." % self.checks if not self.failed else "RESULT: %d OF %d CHECKS FAILED: %s" % (len(self.failed), self.checks, "; ".join(self.failed)))
        with open(os.path.join(ATTEMPT, "logs", "reconciliation-run.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("reconciliation-run.txt: %s" % self.lines[-1])
        return not self.failed


def path_of(name):
    return os.path.join(PARTICIPANT, OUT, name)


def read(name):
    with open(path_of(name), encoding="utf-8") as f:
        return f.read()


def sums(folder=None):
    out = {}
    for name in ("report.md", "report.log.md", "report.history.json"):
        with open(os.path.join(folder, name) if folder else path_of(name), "rb") as f:
            out[name] = hashlib.sha256(f.read()).hexdigest()
    return out


def sections(report):
    """The report's exception sections: {state in small letters: text}."""
    body = report[report.index("## 3. "):report.index("## 4. ")]
    out = {}
    for part in body.split("\n### ")[1:]:
        title, _, rest = part.partition("\n")
        out[title.split(":")[0].lower()] = rest
    return out


def block_for(section, number):
    """The lines of the report about one item, within its state's section."""
    found = [b for b in section.split("\n- **") if "[%s]" % number in b.split("\n")[0]]
    return found[0] if len(found) == 1 else None


def age_from(when, now):
    """How long before `now` the time `when` was, in the words the report uses. Written here, not taken from the tool."""
    shape = "%Y-%m-%dT%H:%M:%SZ"
    minutes = int((datetime.datetime.strptime(now, shape) - datetime.datetime.strptime(when, shape)).total_seconds()) // 60
    parts = [(minutes // 1440, "day"), (minutes % 1440 // 60, "hour"), (minutes % 60, "minute")]
    return " ".join("%d %s%s" % (n, word, "" if n == 1 else "s") for n, word in parts if n), minutes > 24 * 60


CLASS_OF = {("refuses", 429): "rate limited (429)", ("refuses", 500): "server error (5xx)", ("refuses", 403): "forbidden (403)", ("garbled",): "unreadable answer", ("unreachable",): "timed out"}


def main():
    import fake_jira
    r = Record()
    want = {row[0]: row[6] for row in fake_jira.ROWS}
    want.update({only[0]: "not yet copied" for only in fake_jira.ONLY_IN_JIRA})
    want_counts = {state: sum(1 for s in want.values() if s == state) for state in ORDER}
    for name in ("report.md", "report.log.md", "report.history.json"):
        if os.path.exists(path_of(name)):
            os.unlink(path_of(name))

    r.part("0. THE FIXTURE. A made-up local copy, and the page that says, item by item, what state each should be given and why.")
    code, out = r.run(FAKE, ["fixture", "--copy", OUT + "/fixture-copy.json", "--describe", OUT + "/fixture.md"])
    fixture = read("fixture.md")
    r.check(code == 0 and all("**%s**" % state in fixture for state in ("synchronized", "missing from Jira", "stale", "conflicted", "failed to fetch")),
            "the fixture's page has items it says should be synchronized, missing from Jira, stale, conflicted and failed to fetch: the five the quest names")
    r.say("  note What the fixture says the counts should be, in the order of the states: %s. All: %d." % (", ".join("%s %d" % (s, want_counts[s]) for s in ORDER), len(want)))

    r.part("1. THE STATES, as the tool states them")
    r.run(TOOL, ["states"])

    r.part("2. THE REPORT, generated")
    command = ["report", "--source", "fake", "--copy", OUT + "/fixture-copy.json", "--out-dir", OUT, "--name", "report", "--as-of", fake_jira.NOW]
    code, out1 = r.run(TOOL, command)
    report = read("report.md")
    first = sums()
    r.check(code == 0 and "RESULT: REPORT WRITTEN. 18 items considered, 15 not simply in sync." in out1, "exit code 0, and the output says the report was written: 18 considered, 15 not simply in sync")
    r.check([line for line in report.split("\n") if line.startswith("## ")][0] == "## 1. The check that comes first" and report.index("CHECK: ") < report.index("## 2. "),
            "the check is the first section of the report, before any count")
    by_section = sections(report)
    placed = {}                             # number: every place it is listed, one entry for each time. A LIST, so that twice under one state is seen
    for state, text in by_section.items():
        for number in re.findall(r"^- \*\*[A-Z]+-[0-9]+\*\* \[([0-9]+)\]", text, re.M):
            placed.setdefault(number, []).append(state)
    in_sync = re.findall(r"\[([0-9]+)\]", report[report.index("## 4. "):report.index("## 5. ")])
    for number in in_sync:
        placed.setdefault(number, []).append("synchronized")
    times = sum(len(places) for places in placed.values())
    r.say("  note Listed in the report, counted by this script: %d numbers, in %d places." % (len(placed), times))
    r.check(set(placed) == set(want) and all(len(places) == 1 for places in placed.values()) and times == len(want),
            "EVERY ITEM IN EXACTLY ONE STATE (criterion 1): this script read the report and found each of the fixture's 18 numbers listed once, under one state")
    r.check({number: places[0] for number, places in placed.items()} == {number: state.lower() for number, state in want.items()},
            "and it is the state the FIXTURE says it should be, for all 18, compared one by one")
    headings = dict((name.lower(), int(count)) for name, count in re.findall(r"^### ([A-Za-z ]+): ([0-9]+)$", report, re.M))
    headings["synchronized"] = int(re.search(r"^## 4\. Synchronized: ([0-9]+)$", report, re.M).group(1))
    under = {state.lower(): sum(1 for places in placed.values() if places == [state.lower()]) for state in ORDER}
    r.check(headings == under == {state.lower(): want_counts[state] for state in ORDER},
            "each state's heading gives the number of items this script counted under it, and the number the fixture says: %s" % ", ".join("%s %d" % (state, headings.get(state.lower(), -1)) for state in ORDER))
    listed = 0
    complete = True
    for number, state in want.items():
        if state == "synchronized":
            continue
        block = block_for(by_section.get(state.lower(), ""), number)
        listed += 1
        if not (block and re.search(r"  - Reason: .{20,}", block) and re.search(r"  - Next: .{20,}", block) and re.search(r"  - Log: line L[0-9]{3} of `report\.log\.md`\.", block)):
            complete = False
    r.check(complete and listed == 15, "EACH LISTED WITH A REASON (criterion 3) AND WHAT TO DO NEXT (criterion 7): each of the 15 items not in sync has a Reason line, a Next line and a Log line under its state")
    stale = by_section.get("stale", "")
    ages, right = [], stale.count("  - Age: **") == want_counts["stale"]
    for row in fake_jira.ROWS:
        if row[6] != "stale":
            continue
        age, over = age_from(row[4][2], fake_jira.NOW)          # worked out here, from the time the fixture says Jira changed it
        line = "  - Age: **%s**. Limit: **24 hours**. %s." % (age, "**Over the limit**" if over else "Within the limit")
        ages.append("%s %s, %s" % (row[1], age, "over" if over else "within"))
        right = right and line in (block_for(stale, row[0]) or "")
    r.check(right and len(ages) == 3 and len(set(a.split(", ")[1] for a in ages)) == 2,
            "A STALE ITEM NAMES ITS AGE AND THE LIMIT (criterion 4): each of the 3 has, on its own lines, the age this script worked out from the fixture, the limit of 24 hours, and the right side of it: %s" % "; ".join(ages))
    failed = by_section.get("failed to fetch", "")
    classes, right = [], failed.count("  - Error class: **") == want_counts["failed to fetch"]
    for row in fake_jira.ROWS:
        block = block_for(by_section.get(row[6].lower(), ""), row[0]) or ""
        if row[6] == "failed to fetch":
            classes.append("%s %s" % (row[1], CLASS_OF[row[4]]))
            right = right and "  - Error class: **%s**." % CLASS_OF[row[4]] in block
        elif row[6] != "synchronized":
            right = right and "Error class: **" not in block and "  - Error class: none." in block
    r.check(right and len(classes) == 5,
            "A FAILED ITEM NAMES ITS ERROR CLASS (criterion 5): each of the 5 has, on its own lines, the class that follows from what the fixture has Jira answer: %s. No other item names one" % "; ".join(classes))
    everything = out1 + report + read("report.log.md") + read("report.history.json")
    sent = str(fake_jira.FakeJira().get("/rest/api/3/issue/30010")[2])
    r.check(not any(word in everything for word in PRIVATE_WORDS) and any(word in sent for word in PRIVATE_WORDS),
            "WITHOUT PRIVATE CONTENT: the made-up Jira's refusals carry a made-up title and email address (this script asked it and looked). "
            "None of five such words is in the output, the report, the fetch log or the history")
    two = sorted(row[0] for row in fake_jira.ROWS if row[5] is not None and row[4] != ("same",))       # changed locally, and Jira did not simply have the same: from the fixture
    have = sorted(number for number, state in want.items() if state != "synchronized" and "  - Also: " in (block_for(by_section.get(state.lower(), ""), number) or ""))
    r.check(have == two and len(two) == 4 and report.count("  - Also: ") == 4 and "4 items also fit a later state than the one given." in report,
            "the four items the fixture makes fit two states (%s) each say what else they fit, on their own lines, and no other item does" % ", ".join(two))
    log = read("report.log.md")
    log_lines = dict(re.findall(r"^- \*\*(L[0-9]{3})\*\* GET `([^`]+)` — (.+)$", log, re.M) and [(m[0], (m[1], m[2])) for m in re.findall(r"^- \*\*(L[0-9]{3})\*\* GET `([^`]+)` — (.+)$", log, re.M)])
    answered = {("gone",): "status 404", ("refuses", 429): "status 429", ("refuses", 500): "status 500", ("refuses", 403): "status 403", ("unreachable",): "timed out"}
    right, cited = True, 0
    for number, state in want.items():
        if state == "synchronized":
            continue
        found = re.search(r"  - Log: line (L[0-9]{3}) of `report\.log\.md`\.", block_for(by_section.get(state.lower(), ""), number) or "")
        path, came_back = log_lines.get(found.group(1), ("", "")) if found else ("", "")
        cited += 1 if found else 0
        row = [r_ for r_ in fake_jira.ROWS if r_[0] == number]
        if state == "not yet copied":
            right = right and path == "/rest/api/3/search/jql" and came_back == "status 200"
        else:
            right = right and path == "/rest/api/3/issue/%s" % number and came_back == answered.get(row[0][4][:2] if row[0][4][0] == "refuses" else row[0][4][:1], "status 200")
    r.check(right and cited == 15 and len(log_lines) == 17,
            "each of the 15 items cites the line of the fetch log on which ITS OWN number was asked for (for the two not yet copied, the line of the list), and that line says what the fixture has Jira answer")
    mark = re.search(r"Run mark: `([0-9a-f]{16})`", report)
    r.check(mark is not None and "Run mark: `%s`." % mark.group(1) in log, "the report and the fetch log carry the same run mark")

    r.part("3. THE REPORT, generated again from the same input")
    code, out2 = r.run(TOOL, command)
    second = sums()
    r.say("sha256, taken by this script, after the first run and after the second:")
    for name in sorted(first):
        r.say("  %-22s %s   %s" % (name, first[name][:32], second[name][:32]))
    r.check(code == 0 and first == second, "THE SAME INPUT GIVES THE SAME REPORT (criterion 6): the report, the fetch log and the history have the same sha256 after the second run as after the first")
    r.check("RESULT: REPORT UNCHANGED" in out2 and out2.count("not written: byte for byte the same") == 3, "the tool says it wrote none of the three")
    fresh = tempfile.mkdtemp(prefix="gtq-reconcile-record-")
    try:
        self_command = ["report", "--source", "fake", "--copy", OUT + "/fixture-copy.json", "--out-dir", fresh, "--name", "report", "--as-of", fake_jira.NOW]
        done = subprocess.run([sys.executable, "-B", TOOL] + self_command, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        third = sums(fresh)
        r.say("A third time, into an empty temporary folder, so that all three files HAD to be written afresh (the folder's path is left out of this record):")
        for line in done.stdout.split("\n"):
            if line.startswith(("  the report", "  the fetch log", "  the history", "RESULT:")):
                r.say("  | " + line)
        for name in sorted(first):
            r.say("  %-22s %s" % (name, third[name][:32]))
        r.check(done.returncode == 0 and done.stdout.count("   WRITTEN") == 3 and third == first,
                "written afresh in another folder, all three files are byte for byte what they are here. So the second run above wrote nothing because nothing differed, not because it did not look")
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
    strip = lambda text: [line for line in text.split("\n") if not line.startswith(("  the report", "  the fetch log", "  the history", "  Runs in the history", "RESULT:"))]       # noqa: E731
    r.check(strip(out1) == strip(out2), "and the two outputs are the same, line for line, apart from the lines that say whether a file was written")

    r.part("4. THE COUNTS ADDED UP BY THIS SCRIPT, from the report's own table")
    table = report[report.index("## 2. "):report.index("## 3. ")]
    rows = re.findall(r"^\| ([0-9]) \| ([^|]+) \| \*\*([0-9]+)\*\* \|", table, re.M)
    total_row = re.search(r"^\| \| \*\*All\*\* \| \*\*([0-9]+)\*\* \|", table, re.M)
    counts = {name.strip(): int(count) for _, name, count in rows}
    r.say("The report's table: %s. All: %s." % (", ".join("%s %d" % (name, counts.get(name, -1)) for name in ORDER), total_row.group(1) if total_row else "NOT FOUND"))
    r.say("Added up here: %s = %d." % (" + ".join(str(counts.get(name, 0)) for name in ORDER), sum(counts.values())))
    r.check([name.strip() for _, name, _ in rows] == ORDER, "the table has the seven states, in their order, and no other row")
    r.check(total_row is not None and sum(counts.values()) == int(total_row.group(1)), "THE COUNTS SUM TO THE TOTAL (criterion 2): the seven counts in the report add up to the figure in its All row")
    r.check(total_row is not None and int(total_row.group(1)) == len(want) == len(fake_jira.ROWS) + len(fake_jira.ONLY_IN_JIRA),
            "and that total is the number of items considered: the %d the local copy holds and the %d the made-up Jira has besides, counted from the fixture" % (len(fake_jira.ROWS), len(fake_jira.ONLY_IN_JIRA)))
    r.check(counts == want_counts, "each count is the count the fixture says it should be")
    r.check(times == sum(counts.values()), "the number of places this script found items listed in the report is the same number")
    r.say("")
    r.say("WHAT THIS DOES NOT SHOW. A real Jira: that is one real run, of a project in which little is out of step.")
    r.say("What happens when Jira's list of the project cannot be read, or the tool's own check fails: those are tests, not this record.")
    return 0 if r.close() else 1


if __name__ == "__main__":
    sys.exit(main())

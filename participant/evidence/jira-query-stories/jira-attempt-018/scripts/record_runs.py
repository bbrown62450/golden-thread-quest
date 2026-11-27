#!/usr/bin/env python3
"""Runs the query tool against the made-up Jira and records what it printed. Makes three records in logs/:

    query-run.txt           a query that spans three pages, complete
    shortfall-run.txt       the same query when a page fails partway, and when the pages end early
    config-change-run.txt   the saved queries listed; a run after changing a query in a copy of the configuration,
                            with the tool's checksum before and after; and a query that matches nothing

Each command is run as a person would run it, from the `participant` folder, and its output is copied in whole.
Result files go to a temporary folder, which is listed after each run and then deleted. NO REAL JIRA IS CONTACTED.

Every check below reads the output or the folder. A record ends with RESULT: ALL CHECKS PASSED, or says which did not.

Run from anywhere:  python3 scripts/record_runs.py        Exit code 0 if every check passed, 1 if not.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
TOOL = "skills/jira-query-stories/run_query.py"
FIXTURE = "skills/jira-query-stories/fixtures/demo.json"
CONFIG = "context/jira/queries.yaml"
BAR = "-" * 78


class Record:
    def __init__(self, name, title):
        self.name, self.lines, self.checks, self.failed = name, [title, "jira-query-stories, attempt jira-attempt-018. Recorded by scripts/record_runs.py.",
                                                                   "Asked of the made-up Jira (skills/jira-query-stories/fake_jira.py) with made-up items. No real Jira was contacted.",
                                                                   "Commands are run from the `participant` folder. RESULTS is a temporary folder, deleted afterwards.", ""], 0, []
        self.temp = tempfile.mkdtemp(prefix="gtq-query-record-")
        self.results = os.path.join(self.temp, "results")
        os.makedirs(self.results)

    def say(self, text=""):
        self.lines.append(text)

    def run(self, arguments, config=CONFIG, out="result.json"):
        """Runs the tool. Returns (exit code, output)."""
        shown = "python3 %s %s" % (TOOL, " ".join(arguments))
        real = [sys.executable, "-B", TOOL] + [a.replace("CONFIG", config).replace("RESULTS", self.results) for a in arguments]
        done = subprocess.run(real, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        output = (done.stdout + done.stderr).replace(self.temp, "TEMP")
        self.say("$ " + shown.replace("CONFIG", "TEMP/queries.yaml" if config != CONFIG else CONFIG))
        self.say(BAR)
        self.lines += output.rstrip("\n").split("\n")
        self.say(BAR)
        self.say("exit code: %d" % done.returncode)
        return done.returncode, output

    def folder(self):
        names = sorted(os.listdir(self.results))
        self.say("What is in RESULTS now: %s" % (", ".join(names) if names else "nothing"))
        return names

    def saved(self, out="result.json"):
        with open(os.path.join(self.results, out), encoding="utf-8") as f:
            return json.load(f)

    def check(self, passed, what):
        self.checks += 1
        self.say("  %s %s" % ("ok  " if passed else "FAIL", what))
        if not passed:
            self.failed.append(what)

    def close(self):
        shutil.rmtree(self.temp, ignore_errors=True)
        self.say("")
        self.say("RESULT: ALL CHECKS PASSED. %d checks." % self.checks if not self.failed else "RESULT: %d OF %d CHECKS FAILED: %s" % (len(self.failed), self.checks, "; ".join(self.failed)))
        with open(os.path.join(ATTEMPT, "logs", self.name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (self.name, self.lines[-1]))
        return not self.failed


BASE = ["run", "--config", "CONFIG", "--project", "DEMO", "--source", "fake", "--fixture", FIXTURE, "--out", "RESULTS/result.json"]


def fixture():
    with open(os.path.join(PARTICIPANT, FIXTURE), encoding="utf-8") as f:
        return json.load(f)["issues"]


def fixture_stories():
    return [i["key"] for i in fixture() if i["issuetype"] == "Story"]


def result_lines(out):
    return [line for line in out.split("\n") if line.startswith("RESULT:")]


def query_run():
    r = Record("query-run.txt", "A saved query that spans three pages")
    stories = fixture_stories()
    r.say("The made-up project's fixture has %d items, %d of them stories, counted by this script. The configuration's page size is 10." % (len(fixture()), len(stories)))
    r.say("")
    code, out = r.run(BASE + ["--query", "all-stories"])
    names = r.folder()
    r.check(code == 0, "the exit code is 0")
    r.check("Pages answered:     3" in out, "the output gives the page count: 3")
    r.check("Total Jira stated:  %d" % len(stories) in out, "the output gives the total Jira stated: %d" % len(stories))
    r.check("Items saved locally: %d" % len(stories) in out, "the output gives the number saved locally: %d" % len(stories))
    r.check(names == ["result.json"], "the results folder holds the result file and nothing else")
    if names == ["result.json"]:
        saved = r.saved()
        r.check([i["key"] for i in saved["items"]] == stories, "the file holds every story of the made-up project, each once, read from the fixture and compared key by key")
        r.check((saved["pages"], saved["saved"], saved["total_jira_stated"], saved["complete"]) == (3, len(stories), len(stories), True), "the file itself records 3 pages, the total stated and the number saved")
        r.check("summary" not in json.dumps(saved) and "Made-up item" not in json.dumps(saved),
                "the file has no `summary` field and none of the fixture's made-up titles. (That titles are not ASKED for is a test, not this check.)")
    r.say("")
    r.say("WHAT THIS DOES NOT SHOW. That a real Jira pages this way. The made-up Jira is a model of it.")
    return r.close()


def shortfall_run():
    r = Record("shortfall-run.txt", "Runs that are not complete: a page fails partway, and the pages end early")
    r.say("=" * 78)
    r.say("1. THE THIRD PAGE FAILS. The made-up Jira answers the third page with status 500.")
    code, out = r.run(BASE + ["--query", "all-stories", "--fault", "fail_page=3"])
    names = r.folder()
    r.check(code == 2, "the exit code is 2, which is this tool's code for an incomplete run")
    r.check(len(result_lines(out)) == 1 and result_lines(out)[0].startswith("RESULT: INCOMPLETE") and "COMPLETE means" not in out,
            "the output has one RESULT line, it begins RESULT: INCOMPLETE, and the paragraph that explains COMPLETE is absent")
    r.check("SHORTFALL: Jira stated 28 and 20 arrived. 8 did not." in out, "the shortfall is reported in numbers: 28 stated, 20 arrived, 8 did not")
    r.check("Items saved locally: 0" in out, "the output says 0 items were saved")
    r.check(names == [], "the results folder is empty: no result file, and no temporary file")
    r.say("")
    r.say("=" * 78)
    r.say("2. THE SAME FAILURE WHEN AN OLDER, COMPLETE RESULT IS ALREADY THERE. First a complete run, then the failing one.")
    code0, _ = r.run(BASE + ["--query", "all-stories"])
    r.check(code0 == 0 and r.folder() == ["result.json"], "the first run is complete and leaves its result")
    with open(os.path.join(r.results, "result.json"), "rb") as f:
        older = f.read()
    code, out = r.run(BASE + ["--query", "all-stories", "--fault", "fail_page=2"])
    names = r.folder()
    with open(os.path.join(r.results, "result.json"), "rb") as f:
        same = f.read() == older
    r.check(code == 2 and "RESULT: INCOMPLETE" in out, "the second run is INCOMPLETE, with exit code 2")
    r.check(same and names == ["result.json"], "the older file is byte for byte what it was, and nothing was added beside it")
    r.check("IT IS NOT THIS RUN'S RESULT" in out, "the output says the file at that place is older and is not this run's")
    os.unlink(os.path.join(r.results, "result.json"))
    r.say("")
    r.say("=" * 78)
    r.say("3. THE QUEST'S SCENARIO. The first page says it is the last. Ten items arrive. There are 28.")
    code, out = r.run(BASE + ["--query", "all-stories", "--fault", "early_last=1"])
    names = r.folder()
    r.check(code == 2 and "MISMATCH: Jira stated 28 and 10 arrived, 18 short" in out, "the mismatch between the total stated and the number that arrived is reported as a failure")
    r.check(names == [], "the results folder is empty")
    r.say("")
    r.say("=" * 78)
    r.say("4. THE RIGHT NUMBER OF WRONG ITEMS. The second page starts one item early: one item comes twice, another never comes.")
    r.say("   28 would arrive and Jira states 28. Comparing the two numbers would pass this.")
    code, out = r.run(BASE + ["--query", "all-stories", "--fault", "repeat_on_page=2"])
    names = r.folder()
    r.check(code == 2 and "came a second time" in out, "the repeated item is noticed, and the run is INCOMPLETE")
    r.check(names == [], "the results folder is empty")
    r.say("")
    r.say("WHAT THIS DOES NOT SHOW. How a real Jira fails. These failures are the made-up Jira's, switched on with --fault.")
    return r.close()


def config_change_run():
    r = Record("config-change-run.txt", "The saved queries; a query changed with no code change; a query that matches nothing")
    r.say("=" * 78)
    r.say("1. THE SAVED QUERIES, each with its name and purpose, as the tool reads them from %s" % CONFIG)
    code, out = r.run(["list", "--config", "CONFIG"])
    with open(os.path.join(PARTICIPANT, CONFIG), encoding="utf-8") as f:
        names = [line.split(":", 1)[1].strip() for line in f if line.startswith("  - name:")]
    blocks = out.split("\n\n")[1:]
    r.check(code == 0 and len(names) >= 4 and len(blocks) == len(names) and all(
        block.split("\n")[0].strip() == name and "purpose:" in block and "filter:" in block for name, block in zip(names, blocks)),
        "each of the %d names this script finds in the configuration file is listed, in order, with a purpose and a filter" % len(names))
    r.say("")
    r.say("=" * 78)
    r.say("2. A QUERY CHANGED, AND NO CODE CHANGED. The configuration is copied to TEMP/queries.yaml, so that the real one is not edited.")
    copy = os.path.join(r.temp, "queries.yaml")
    shutil.copy(os.path.join(PARTICIPANT, CONFIG), copy)

    def tool_sum():
        digest = hashlib.sha256()
        for name in ("run_query.py", "fake_jira.py"):
            with open(os.path.join(PARTICIPANT, os.path.dirname(TOOL), name), "rb") as f:
                digest.update(f.read())
        return digest.hexdigest()
    before = tool_sum()
    r.say("sha256 of run_query.py and fake_jira.py together, before: %s" % before)
    r.say("")
    r.say("Before the change:")
    code1, out1 = r.run(BASE + ["--query", "open-stories"], config=copy)
    first = r.saved()["saved"] if code1 == 0 else None
    with open(copy, encoding="utf-8") as f:
        text = f.read()
    old, new = "filter: 'issuetype = Story AND statusCategory != Done'", "filter: 'issuetype = Story AND status = \"In Review\"'"
    r.say("")
    r.say("The change, made in TEMP/queries.yaml and nowhere else. One line:")
    r.say("    was:  %s" % old)
    r.say("    now:  %s" % new)
    r.check(text.count(old) == 1, "the line to change is in the configuration exactly once")
    with open(copy, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new))
    r.say("")
    r.say("After the change, the same command:")
    code2, out2 = r.run(BASE + ["--query", "open-stories"], config=copy)
    second = r.saved() if code2 == 0 else None
    after = tool_sum()
    r.say("sha256 of run_query.py and fake_jira.py together, after:  %s" % after)
    r.check(code1 == 0 and code2 == 0, "both runs are complete")
    r.check('status = "In Review"' in out2 and 'status = "In Review"' not in out1, "the query sent is the changed one")
    r.check(second is not None and second["saved"] != first and all(i["status"] == "In Review" for i in second["items"]) and second["saved"] > 0,
            "the result changed with it: %s items before, %s after, every one In Review" % (first, second["saved"] if second else "?"))
    r.say("  note The two checksums are equal: %s. This is not counted as a check. Nothing in this script writes those files, so it" % ("yes" if before == after else "NO"))
    r.say("       could not have come out otherwise. What shows that no code change was needed is that the only thing edited")
    r.say("       between the two runs was one line of TEMP/queries.yaml, and the result changed.")
    if before != after:
        r.check(False, "the code files changed during the record")
    r.say("")
    r.say("=" * 78)
    r.say("3. A QUERY THAT MATCHES NOTHING")
    code, out = r.run(BASE + ["--query", "stories-with-no-such-label"])
    names = r.folder()
    r.check(code == 0, "the exit code is 0: it is not an error")
    r.check("Total Jira stated:  0" in out and "Items saved locally: 0" in out, "it reports zero stated and zero saved")
    r.check("REFUSED" not in out and "INCOMPLETE" not in out, "nothing in the output calls it a failure")
    r.check(names == ["result.json"] and r.saved()["items"] == [] and r.saved()["complete"] is True, "a result file is written, complete, with no items")
    r.say("")
    r.say("=" * 78)
    r.say("4. A QUERY WITH A DATE GIVEN ON THE COMMAND LINE, and a value that is not a date")
    code, out = r.run(BASE + ["--query", "stories-updated-since", "--set", "since=2026-11-15"])
    r.check(code == 0 and 'updated >= "2026-11-15"' in out, "the date is put into the query, quoted")
    os.unlink(os.path.join(r.results, "result.json"))
    code, out = r.run(BASE + ["--query", "stories-updated-since", "--set", "since=2026-02-30"])
    names = r.folder()
    r.check(code == 1 and "REFUSED" in out and "Requests sent to Jira" not in out and names == [],
            "a date that is not on the calendar is refused with exit code 1, the output lists no requests, and nothing is written. "
            "(That no request is MADE is a test, which puts a tripwire where the made-up Jira is. This check reads the output.)")
    return r.close()


if __name__ == "__main__":
    results = [query_run(), shortfall_run(), config_change_run()]
    sys.exit(0 if all(results) else 1)

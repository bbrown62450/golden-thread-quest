#!/usr/bin/env python3
"""Runs the hierarchy tool against the made-up Jira, in order, and records what it printed. Makes logs/tree-run.txt:

    1. the tree built from a fresh made-up project
    2. the tree built again from unchanged data, and rebuilt twice from the records with no Jira at all
    3. an item that is its own parent, rejected
    4. a loop, rejected
    5. an item moved under another parent AND given another key, matched by its number
    6. built once more from unchanged data
   (the item whose parent was not retrieved is in every build: the made-up project has one)

It also leaves the result where the quest asks for it: participant/context/jira/hierarchy.md, with the records it is
written from beside it, hierarchy.json. Both are deleted at the start, so that the first build is a first build.

Each command is run as a person would run it, from the `participant` folder, and its output is copied in whole.
The made-up Jira lives in temporary folders, shown as JIRA, JIRA-SELF and JIRA-LOOP, deleted afterwards.
NO REAL JIRA IS CONTACTED.

Every check reads the output or the files. The record ends with RESULT: ALL CHECKS PASSED, or says which did not.

Run from anywhere:  python3 scripts/record_tree.py        Exit code 0 if every check passed, 1 if not.
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
TOOL = "skills/jira-read-hierarchy/hierarchy.py"
FAKE = "skills/jira-read-hierarchy/fake_jira.py"
OUT = "context/jira"
NAME = "hierarchy"
BAR = "-" * 78


def path_of(ending):
    return os.path.join(PARTICIPANT, OUT, NAME + ending)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def both():
    return {e: (sha(path_of(e)) if os.path.exists(path_of(e)) else None) for e in (".json", ".md")}


class Record:
    def __init__(self, temp):
        self.temp, self.checks, self.failed = temp, 0, []
        self.lines = ["Building the tree of a project: twice the same, a self-parent and a loop rejected, an unresolved link kept, a moved item matched by its number",
                      "jira-read-hierarchy, attempt jira-attempt-020. Recorded by scripts/record_tree.py.",
                      "Read from the made-up Jira (skills/jira-read-hierarchy/fake_jira.py): one made-up project of 11 made-up items. No real Jira was contacted.",
                      "Commands are run from the `participant` folder. JIRA, JIRA-SELF and JIRA-LOOP are temporary folders that hold made-up Jiras, deleted afterwards.", ""]

    def say(self, text=""):
        self.lines.append(text)

    def run(self, tool, arguments):
        real = [sys.executable, "-B", tool] + [a.replace("JIRA", os.path.join(self.temp, "JIRA")) for a in arguments]
        done = subprocess.run(real, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        output = (done.stdout + done.stderr).replace(os.path.join(self.temp, "JIRA"), "JIRA")
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
        with open(os.path.join(ATTEMPT, "logs", "tree-run.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("tree-run.txt: %s" % self.lines[-1])
        return not self.failed


def records_now():
    with open(path_of(".json"), encoding="utf-8") as f:
        return json.load(f)


def page_now():
    with open(path_of(".md"), encoding="utf-8") as f:
        return f.read()


def made_up():
    """The made-up project as it starts out, read from the made-up Jira's own file: {key: (number, type, parent's number)}."""
    sys.path.insert(0, os.path.join(PARTICIPANT, os.path.dirname(FAKE)))
    import fake_jira
    return {i["key"]: (i["id"], i["type"], i["parent"]["id"] if i["parent"] else None) for i in fake_jira.fresh()["issues"]}


def checksum_line(output):
    return [line for line in output.split("\n") if line.startswith("Checksum of the tree")]


def tree_block(page):
    """The lines of the tree on the page, between its fence lines."""
    section = page[page.index("## The tree"):page.index("## Unresolved links")]
    return section[section.index("~~~text\n") + 8:section.rindex("\n~~~")].split("\n")


def nesting(lines):
    """{number: [numbers set in directly under it]}, read back from printed tree lines by their indentation alone."""
    told, stack = {}, []
    for line in lines:
        if line.startswith("PARENT NOT RETRIEVED"):
            stack = [(-1, line.split("number ")[1].split(" ")[0])]
            continue
        depth, number = (len(line) - len(line.lstrip(" "))) // 2, line.split("[")[1].split("]")[0]
        if stack and stack[0][0] == -1 and depth == 0:
            stack = []
        stack = [s for s in stack if s[0] < depth]
        if stack:
            told.setdefault(stack[-1][1], []).append(number)
        stack.append((depth, number))
    return told


def children_from_records(records):
    """{number: [numbers of the items whose parent number it is]}, worked out here from the records, not by the tool."""
    out = {}
    for it in sorted(records["items"], key=lambda i: int(i["id"])):
        if it["parent_id"] is not None:
            out.setdefault(it["parent_id"], []).append(it["id"])
    return out


def main():
    temp = tempfile.mkdtemp(prefix="gtq-hierarchy-record-")
    r = Record(temp)
    build = ["build", "--source", "fake", "--project", "DEMO", "--out-dir", OUT, "--name", NAME, "--state", "JIRA"]
    try:
        for ending in (".json", ".md"):
            if os.path.exists(path_of(ending)):
                os.unlink(path_of(ending))
        r.part("0. A FRESH MADE-UP PROJECT. The two files a build writes were deleted first, so the first build below is a first build.")
        r.run(FAKE, ["new", "--state", "JIRA"])

        r.part("1. THE FIRST BUILD")
        code, out1 = r.run(TOOL, build)
        records, page = records_now(), page_now()
        want = made_up()
        got = {i["key"]: (i["id"], i["type"], i["parent_id"]) for i in records["items"]}
        r.check(code == 0 and "RESULT: BUILT. 11 items" in out1, "exit code 0, and the output says 11 items were built into a tree")
        r.check(got == want, "for each of the 11 items the records hold the number, the type and the PARENT'S NUMBER that the made-up Jira has for it, compared item by item (criterion 1)")
        index = page[page.index("## Index"):page.index("## The tree")]
        r.check(all("| %s | %s | `%s` | %s |" % (number, key, kind, parent or "none") in index for key, (number, kind, parent) in want.items()),
                "the index on the page has a row for each item with its identifier, key, type and parent identifier")
        kinds = sorted(set(kind for _, kind, _ in got.values()))
        r.check(all(kind in kinds for kind in ("Epic", "Story", "Task", "Subtask")) and "all four are here" in out1, "an epic, a story, a task and a subtask are all among them (criterion 5)")
        r.check("UNRESOLVED LINKS: 1." in out1 and got.get("DEMO-10") == ("30010", "Story", "40003") and "40003" not in [i["id"] for i in records["items"]]
                and "| 30010 | DEMO-10 | `Story` | 40003 | OTHER-3 | **NO: unresolved link** |" in index
                and "| 30010 | DEMO-10 | `Story` | 40003 | OTHER-3 |" in page[page.index("## Unresolved links"):],
                "AN UNRESOLVED LINK (criterion 3): no item in the records has the number 40003, which DEMO-10 gives as its parent. DEMO-10 is still in the records and the index, "
                "with that parent number, and is listed under Unresolved links")
        lines = tree_block(page)
        at = [n for n, line in enumerate(lines) if line.strip().startswith("DEMO-10 ")]
        r.check(len(at) == 1 and lines[at[0]].startswith("  ") and lines[at[0] - 1].startswith("PARENT NOT RETRIEVED: number 40003"),
                "in the tree it stands once, set in under a line naming the parent that is missing, and not among the items that have no parent")
        r.check("Made-up title" not in json.dumps(records) + page + out1, "no title is in the records, the page or the output")

        r.part("2. BUILT AGAIN FROM UNCHANGED DATA, AND REBUILT TWICE FROM THE RECORDS ALONE")
        first = both()
        code, out2 = r.run(TOOL, build)
        r.check(code == 0 and both() == first, "the records and the page have the same sha256 after the second build as after the first, taken by this script (criterion 7)")
        r.check(checksum_line(out1) == checksum_line(out2) and len(checksum_line(out1)) == 1, "both builds print the same checksum of the tree: %s" % (checksum_line(out1) or ["?"])[0].split(": ")[-1])
        code_a, tree_a = r.run(TOOL, ["tree", "--records", OUT + "/" + NAME + ".json"])
        code_b, tree_b = r.run(TOOL, ["tree", "--records", OUT + "/" + NAME + ".json"])
        r.check(code_a == code_b == 0 and tree_a == tree_b, "the tree rebuilt twice from the records, with no Jira, gives the same output twice, character for character")
        r.check(checksum_line(tree_a) == checksum_line(out1), "and its checksum is the one the builds printed")
        mine = children_from_records(records)
        told = nesting(tree_block(page))
        r.check(told == mine and len(mine) >= 4, "the tree on the page agrees with the records: under each item are exactly the items whose parent number is its number. "
                                                 "This script works that out again from the records and reads the page's indentation, for %d parents, one of them the parent that is missing" % len(mine))
        r.say("")
        r.say("The same records with EVERY KEY CHANGED: each item's key replaced by another, and each parent's key by a wrong one. The numbers are left alone.")
        r.say("This script makes that copy, in a temporary folder shown as JIRA/scrambled.json. The made-up project's keys and numbers run in step,")
        r.say("so without this a tree built from keys would look the same as one built from numbers.")
        scrambled = dict(records, items=[dict(i, key="ZZ-%d" % (900 - n), parent_key=None if i["parent_id"] is None else "QQ-1") for n, i in enumerate(records["items"])],
                         links=[dict(l, from_key="ZZ-1", to_key="ZZ-2") for l in records["links"]])
        os.makedirs(os.path.join(r.temp, "JIRA"), exist_ok=True)
        with open(os.path.join(r.temp, "JIRA", "scrambled.json"), "w", encoding="utf-8") as f:
            json.dump(scrambled, f)
        code_s, tree_s = r.run(TOOL, ["tree", "--records", "JIRA/scrambled.json"])
        printed = lambda output: [line[2:] for line in output[output.index("THE TREE"):output.index("Estimates, added up")].split("\n")[1:] if line.strip()]       # noqa: E731
        r.check(code_s == 0 and nesting(printed(tree_s)) == nesting(printed(tree_a)) == mine and "ZZ-" in tree_s and "DEMO-" not in tree_s[tree_s.index("THE TREE"):],
                "BUILT FROM IDENTIFIERS, NOT FROM KEYS OR TITLES (criterion 2): with every key changed, the printed tree nests the same numbers under the same numbers as before")

        r.part("3. AN ITEM THAT IS ITS OWN PARENT. A second made-up Jira, JIRA-SELF, the same project with DEMO-5 made its own parent.")
        before = both()
        r.run(FAKE, ["new", "--state", "JIRA-SELF"])
        r.run(FAKE, ["break", "--state", "JIRA-SELF", "--how", "self"])
        code, out = r.run(TOOL, build[:-1] + ["JIRA-SELF"])
        r.check(code == 2 and "REJECTED" in out and "DEMO-5 [30005] is its own parent" in out and "RESULT:" not in out, "REJECTED (criterion 6): exit code 2, the item is named, and there is no RESULT line")
        r.check(both() == before and "THEY ARE NOT THIS BUILD'S" in out, "the files from the earlier build are byte for byte what they were, and the output says they are not this build's")

        r.part("4. A LOOP. A third made-up Jira, JIRA-LOOP: the epic DEMO-1 put under the subtask DEMO-6, which is under the story DEMO-2, which is under DEMO-1.")
        r.run(FAKE, ["new", "--state", "JIRA-LOOP"])
        r.run(FAKE, ["break", "--state", "JIRA-LOOP", "--how", "loop"])
        code, out = r.run(TOOL, build[:-1] + ["JIRA-LOOP"])
        r.check(code == 2 and "REJECTED" in out and "RESULT:" not in out and all(name in out for name in ("DEMO-1 [30001]", "DEMO-6 [30006]", "DEMO-2 [30002]")) and out.count("a loop:") == 1,
                "REJECTED (criterion 6): exit code 2, and the loop is named once with all three items in it")
        r.check(both() == before, "the files from the earlier build are byte for byte what they were")

        r.part("5. AN ITEM IS MOVED IN THE MADE-UP JIRA, AND GIVEN ANOTHER KEY: the subtask DEMO-7, from under the story DEMO-2 to under the story DEMO-3, and now called DEMO-70.")
        old = {i["id"]: i for i in records_now()["items"]}
        row = lambda text, number: [line for line in text.split("\n") if line.startswith("| %s |" % number)][0].split(" | ")[-1].rstrip(" |")       # noqa: E731
        totals_before = [row(page_now(), n) for n in ("30001", "30002", "30003")]
        r.run(FAKE, ["move", "--state", "JIRA", "--key", "DEMO-7", "--under", "DEMO-3"])
        r.run(FAKE, ["rekey", "--state", "JIRA", "--key", "DEMO-7", "--to", "DEMO-70"])
        code, out5 = r.run(TOOL, build)
        records, page = records_now(), page_now()
        new = {i["id"]: i for i in records["items"]}
        mine = children_from_records(records)
        r.check(code == 0 and "MOVED: DEMO-70 [30007] was under DEMO-2 [30002], and is now under DEMO-3 [30003]." in out5
                and "NEW KEY: the item with the number 30007 had the key DEMO-7 and now has DEMO-70. It is the same item." in out5
                and "by number: 1 moved, 1 with a new key, 0 new, 0 no longer returned" in out5,
                "MATCHED BY ITS IDENTIFIER: the key DEMO-7 is gone and DEMO-70 is new, and the output does not call either an item gone or an item new. "
                "It says the item with the number 30007 moved and has a new key")
        r.check(old["30007"]["parent_id"] == "30002" and old["30007"]["key"] == "DEMO-7" and new["30007"]["parent_id"] == "30003" and new["30007"]["key"] == "DEMO-70" and sorted(old) == sorted(new),
                "the records agree: the same 11 numbers before and after, and under the number 30007 the key and the parent number both changed")
        told = nesting(tree_block(page))
        r.check(told.get("30003") == ["30007", "30008"] and told.get("30002") == ["30006"] and sum(1 for line in tree_block(page) if "[30007]" in line) == 1 and told == mine,
                "UNDER ITS NEW PARENT (criterion 4): read from the indentation of the tree on the page, 30007 is set in under 30003, is no longer under 30002, and is in the tree once")
        totals_after = [row(page, n) for n in ("30001", "30002", "30003")]
        r.say("  note Totals of the epic and the two stories, read from the index before the move: %s. After: %s." % (", ".join(totals_before), ", ".join(totals_after)))
        r.check(totals_before == ["25 h (2 of the 8 without an estimate)", "13 h", "9 h"] and totals_after == ["25 h (2 of the 8 without an estimate)", "11 h", "11 h"],
                "THE SCENARIO: its 2 hours left the old parent (13 h to 11 h) and joined the new (9 h to 11 h), and the epic above both is 25 h before and after. Nothing is counted twice")
        r.check(checksum_line(out5) != checksum_line(out1), "the checksum of the tree changed, as it should when the tree does")

        r.part("6. BUILT ONCE MORE FROM UNCHANGED DATA")
        after_move = both()
        code, out6 = r.run(TOOL, build)
        r.check(code == 0 and both() == after_move and "nothing was written" in out6 and checksum_line(out6) == checksum_line(out5), "nothing was written, both files have the same sha256, and the tree's checksum is the same")
        r.check("by number: 0 moved" in out6, "and nothing is reported as moved this time")
        r.say("")
        r.say("WHAT THIS DOES NOT SHOW. That a real Jira reports a parent this way, or what it sends when an item is moved. No change was made in a real Jira.")
        r.say("A real Jira is not supposed to allow a loop or an item that is its own parent; parts 3 and 4 show what the tool does if it is ever sent one.")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0 if r.close() else 1


if __name__ == "__main__":
    sys.exit(main())

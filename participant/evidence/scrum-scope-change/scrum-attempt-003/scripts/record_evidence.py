#!/usr/bin/env python3
"""Records logs/scope-run.txt for the quest scrum-scope-change. It contacts nothing.

    python3 participant/evidence/scrum-scope-change/scrum-attempt-003/scripts/record_evidence.py

It runs the comparison on the handed-in snapshots, twice and once more from a copy kept elsewhere, and compares every
byte. It prints what the comparison printed, with the items that differed only in noise and were left out. It runs the
comparison of the start snapshot with itself. Then it works the classes and the totals out again from the snapshots,
by its own short code and not by scope.py's, and compares them with the report. Then it spoils the report and the
snapshots, one thing at a time. The scratch folder, SCRATCH, is deleted at the end.

What "worked out again here" covers: this script reads the file by its own few lines, and sets formatting aside by a
rule of its own, written differently from scope.py's. It reads only this file's shape.

The snapshots are made up: the project, the items, the dates and the four people are invented.
"""
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
SKILL = os.path.join(REPO, "participant", "skills", "scrum-scope-change")
sys.path.insert(0, SKILL)
import scope as sc  # noqa: E402

SNAPSHOTS = os.path.join(REPO, "participant", "context", "scrum", "scope", "snapshots.md")
REPORT = os.path.join(REPO, "participant", "context", "scrum", "scope", "scope-change.md")
LOGS = os.path.join(HERE, "..", "logs")
REL = lambda p: os.path.relpath(p, REPO)  # noqa: E731


def raw(path):
    with open(path, "rb") as f:
        return f.read()


def digest(path):
    return hashlib.sha256(raw(path)).hexdigest()


class Log:
    def __init__(self):
        self.lines = ["The scope run. scrum-scope-change, attempt scrum-attempt-003",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere and nothing was posted to any tracker.",
                      "The snapshots are made up. Paths are from the repository's top folder. SCRATCH is a temporary folder, deleted at the end.",
                      "Nothing here needed redacting: the names in it are of invented people, and it holds no credential."]
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


def listed(text):
    return re.findall(r"^- `([A-Z]+-\d+)`", text, re.M)


def own_reading(text, name):
    """One snapshot, read here with no help from scope.py: {id: {field: text, "scope": [lines], "acceptance": [lines]}}."""
    body = text.split("## Snapshot: %s\n" % name)[1].split("\n## ")[0]
    items = {}
    for block in body.split("\n### ")[1:]:
        lines = block.split("\n")
        one, into = {"scope": [], "acceptance": []}, None
        for line in lines[1:]:
            if line.startswith("- scope:") or line.startswith("- acceptance:"):
                into = line[2:].split(":")[0]
            elif line.startswith("  ") and into:
                one[into].append(line)
            elif line.startswith("- "):
                key, _, value = line[2:].partition(": ")
                one[key], into = value, None
        items[lines[0].strip()] = one
    return items


def bare(line):
    """A list entry with a little formatting set aside, by this script's own lines: the marker or number at its front goes,
    letters are made small, spaces are joined, and a full stop, comma or semicolon at its very end goes. Nothing else."""
    text = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line).lower()
    return " ".join(text.split()).rstrip(".;, ")


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-scope-")
    before = {p: digest(p) for p in (SNAPSHOTS, REPORT)}
    text, report = raw(SNAPSHOTS).decode("utf-8"), raw(REPORT).decode("utf-8")
    tool = "participant/skills/scrum-scope-change/scope.py"

    log.part("PART 1. The comparison, run on the handed-in snapshots")
    runs = []
    for which in ("first", "second"):
        out = os.path.join(scratch, which, "scope-change.md")
        done = subprocess.run([sys.executable, tool, "compare", "--snapshots", REL(SNAPSHOTS), "--out", out], cwd=REPO, capture_output=True, text=True)
        log.out("$ python3 %s compare --snapshots %s --out SCRATCH/%s/scope-change.md" % (tool, REL(SNAPSHOTS), which), *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
        runs.append((raw(out), done.stdout))
        if which == "first":
            time.sleep(2)
    stdout = runs[0][1]
    log.check("the two runs, 2 seconds apart, wrote reports that are byte for byte the same, and not empty", runs[0][0] == runs[1][0] and len(runs[0][0]) > 0)
    log.check("the handed-in report, participant/context/scrum/scope/scope-change.md, is byte for byte what these runs wrote", raw(REPORT) == runs[0][0])
    elsewhere = os.path.join(scratch, "elsewhere", "deep")
    os.makedirs(elsewhere)
    shutil.copyfile(SNAPSHOTS, os.path.join(elsewhere, "two-snapshots.md"))
    done = subprocess.run([sys.executable, os.path.join(SKILL, "scope.py"), "compare", "--snapshots", "two-snapshots.md", "--out", "out.md"], cwd=elsewhere, capture_output=True, text=True)
    log.check("a third run, from a copy of the file under another name in another folder, wrote the same bytes again", done.returncode == 0 and raw(os.path.join(elsewhere, "out.md")) == runs[0][0])
    log.check("the output names the items that differed only in noise and were left out of every count", "Differed only in noise, and left out of the change of scope (4): PIER-302 [title], PIER-305 [assignee], PIER-308 [acceptance], PIER-311 [description]" in stdout)

    a, b = own_reading(text, "start"), own_reading(text, "later")
    log.part("PART 2. The snapshots (the first required item)")
    log.out("%s, sha256 %s" % (REL(SNAPSHOTS), before[SNAPSHOTS]), "Read here, by this script's own lines: %d items in the start snapshot, %d in the later one." % (len(a), len(b)))
    log.check("every item in both snapshots has an estimate that is a whole number", all(re.match(r"^\d+$", one.get("estimate", "")) for side in (a, b) for one in side.values()) and len(a) > 0 and len(b) > 0)
    log.check("the file says of itself that it is made up, and holds exactly one snapshot named start and one named later", "**Made up.**" in text.split("## ")[0] and text.count("## Snapshot: start\n") == 1 and text.count("## Snapshot: later\n") == 1)

    log.part("PART 3. The classes and the totals, worked out again here (criteria 1 to 5 and 7)",
             "Made by this script's own lines from the two snapshots, and compared with what the report lists.")
    added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    both = sorted(set(a) & set(b))
    log.out("  identifiers in the later snapshot only: %s" % ", ".join(added), "  identifiers in the start snapshot only: %s" % ", ".join(removed))
    log.check("criterion 2: the report lists as added exactly the %d items whose identifier is in the later snapshot only" % len(added), listed(section(report, 2)) == added and len(added) == 2)
    log.check("criterion 3: the report lists as removed exactly the %d items whose identifier is in the start snapshot only" % len(removed), listed(section(report, 3)) == removed and len(removed) == 2)
    material, noise, same = {}, {}, []
    for i in both:
        differs = [f for f in ("estimate",) if float(a[i]["estimate"]) != float(b[i]["estimate"])]
        differs += [f for f in ("scope", "acceptance") if sorted(bare(l) for l in a[i][f]) != sorted(bare(l) for l in b[i][f])]
        other = [f for f in ("title", "description", "assignee") if a[i].get(f) != b[i].get(f)] + [f for f in ("scope", "acceptance") if f not in differs and a[i][f] != b[i][f]]
        if differs:
            material[i] = differs
        elif other:
            noise[i] = other
        else:
            same.append(i)
    log.out("", "  in both, and the estimate, scope or acceptance differs once formatting is set aside:", *("    %s  %s" % (i, ", ".join(f)) for i, f in material.items()),
            "  in both, and only something else differs:", *("    %s  %s" % (i, ", ".join(f)) for i, f in noise.items()), "  in both, and nothing differs: %s" % ", ".join(same))
    shown = {m.group(1): re.findall(r"`(\w+)`", m.group(2)) for m in re.finditer(r"^- `([A-Z]+-\d+)`: fields that differ: ([^\n]*)\.$", section(report, 4), re.M)}
    log.check("criterion 4: the report lists as materially changed exactly these %d items, each with exactly these fields" % len(material), shown == material and len(material) == 4)
    shown5 = {m.group(1): re.findall(r"`(\w+)`", m.group(2)) for m in re.finditer(r"^- `([A-Z]+-\d+)`: fields that differ: ([^\n]*)\.$", section(report, 5), re.M)}
    log.check("criterion 5: the report lists as noise exactly these %d items, each with exactly these fields, and none of them is in section 1 or in section 8" % len(noise), shown5 == noise and len(noise) == 4 and not any(i in section(report, 1) + section(report, 8) for i in noise))
    log.check("the one item in which nothing differs is listed as unchanged, and no item is in two lists or in none", re.findall(r"`([A-Z]+-\d+)`", section(report, 6)) == same
              and sorted(listed(section(report, 2)) + listed(section(report, 3)) + list(shown) + list(shown5) + same) == sorted(set(a) | set(b)))
    by_title = sorted(set(one["title"] for one in b.values()) - set(one["title"] for one in a.values()))
    log.out("", "  criterion 1, a contrast. Matched on TITLE, these later titles have no match at start: %s" % "; ".join(by_title))
    log.check("criterion 1: matched on title there would be 3 items \"added\", the renamed PIER-302 among them. The report has 2, and has PIER-302 as noise with both titles",
              len(by_title) == 3 and b["PIER-302"]["title"] in by_title and "PIER-302" in noise and "  - `title`: \"%s\" at start, \"%s\" later." % (a["PIER-302"]["title"], b["PIER-302"]["title"]) in section(report, 5))
    log.check("criterion 5: each noise item is shown with both versions of what differs, so a person can see what was not counted. The description that gained a sentence is there whole",
              all("  - `%s`: \"%s\" at start, \"%s\" later." % (f, a[i][f], b[i][f]) in section(report, 5) for i, fs in noise.items() for f in fs if f in ("title", "description", "assignee")) and b["PIER-311"]["description"] in section(report, 5))
    log.check("the report says that noise is a statement about three fields, and not a statement that no work was added", "It is not a statement that no work was added." in section(report, 5))
    for i in material:
        for f in material[i]:
            if f == "estimate":
                want = "  - `estimate`: %s at start, %s later. %+d points." % (a[i]["estimate"], b[i]["estimate"], int(b[i]["estimate"]) - int(a[i]["estimate"]))
                log.check("criterion 4: for %s the report gives both estimates and the difference: %s to %s" % (i, a[i]["estimate"], b[i]["estimate"]), want in section(report, 4))
            else:
                gone = [l for l in a[i][f] if bare(l) not in [bare(x) for x in b[i][f]]]
                came = [l for l in b[i][f] if bare(l) not in [bare(x) for x in a[i][f]]]
                quote = lambda ls: ", ".join("\"%s\"" % re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", l) for l in ls) or "none"  # noqa: E731
                log.check("criterion 4: for %s the report shows the %s entries that are in one snapshot and not the other: %d and %d" % (i, f, len(gone), len(came)),
                          "  - `%s`: at start only: %s. Later only: %s." % (f, quote(gone), quote(came)) in section(report, 4))
    log.check("the two changes of wording in a criterion both carry the sentence that the report cannot tell a rewording from a change of meaning, and the entry that was only taken out does not",
              section(report, 4).count("This report cannot tell which. A person should read both.") == 2 and "July and August\". Later only: none. It counts because the scope list is what is to be built.\n" in section(report, 4))

    t0, t1 = sum(int(one["estimate"]) for one in a.values()), sum(int(one["estimate"]) for one in b.values())
    up = sum(int(b[i]["estimate"]) for i in added)
    down = sum(int(a[i]["estimate"]) for i in removed)
    re_est = {i: int(b[i]["estimate"]) - int(a[i]["estimate"]) for i in both if a[i]["estimate"] != b[i]["estimate"]}
    moved = up + down + sum(abs(d) for d in re_est.values())
    log.out("", "  the sums, made here: start %d, later %d, added %d, removed %d, re-estimated %s, moved %d" % (t0, t1, up, down, ", ".join("%s %+d" % p for p in re_est.items()), moved))
    s1 = section(report, 1)
    log.check("criterion 7: the report states the committed total at start, %d, and later, %d, and the net change, %d" % (t0, t1, t1 - t0),
              "- Committed at start: %d points, in %d items." % (t0, len(a)) in s1 and "- Committed later: %d points, in %d items." % (t1, len(b)) in s1 and "- **Net change: %s points.**" % ("%+d" % (t1 - t0) if t1 != t0 else "0") in s1)
    log.check("criterion 7: it breaks the net change down as worked out here, and the parts add up: %d + %d - %d %+d = %d" % (t0, up, down, sum(re_est.values()), t1),
              "- Added: +%d points, in %d items. Removed: -%d points, in %d items. Re-estimated: %+d points, in %d items" % (up, len(added), down, len(removed), sum(re_est.values()), len(re_est)) in s1 and t0 + up - down + sum(re_est.values()) == t1
              and "- %d at start + %d added - %d removed - %d re-estimated = %d." % (t0, up, down, -sum(re_est.values()), t1) in s1)
    log.check("the scenario: the net change is 0 and the report still says that %d points moved" % moved, t1 == t0 and "- **Points that moved: %d.**" % moved in s1 and moved == 22)

    log.part("PART 4. Identical snapshots report no change (criterion 6)")
    same_out = os.path.join(scratch, "same", "scope-change.md")
    done = subprocess.run([sys.executable, tool, "compare", "--snapshots", REL(SNAPSHOTS), "--later", "start", "--out", same_out], cwd=REPO, capture_output=True, text=True)
    log.out("$ python3 %s compare --snapshots %s --later start --out SCRATCH/same/scope-change.md" % (tool, REL(SNAPSHOTS)), *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
    same_report = raw(same_out).decode("utf-8")
    log.check("criterion 6: the start snapshot compared with itself prints NO CHANGE, and its report says so and lists nothing as added, removed, materially changed or noise",
              "NO CHANGE." in done.stdout and "**No change.** The two snapshots hold the same %d items, and no compared field of any item differs." % len(a) in same_report
              and all("## %s (0)" % h in same_report for h in ("2. Added", "3. Removed", "4. Materially changed", "5. Noise: differs, and not counted as a change of scope")) and "- **Net change: 0 points.**" in same_report)
    twin = os.path.join(scratch, "twin.md")
    sc.write(twin, text.split("## Snapshot: later\n")[0] + "## Snapshot: later\n" + text.split("## Snapshot: start\n")[1].split("\n## ")[0] + "\n")
    twin_model = sc.compare(twin, "start", "later", None)[0]
    log.check("criterion 6: a file whose two snapshots are separate copies of the same %d items also reports no change" % len(a), len(twin_model["unchanged"]) == len(a) and not (twin_model["added"] or twin_model["removed"] or twin_model["material"] or twin_model["noise"] or twin_model["gaps"]))
    log.check("a contrast: the handed-in report, whose net change is also 0, does not say \"No change\"", "**No change.**" not in report)

    log.part("PART 5. Stretch: remaining capacity, and who is recorded as making each change")
    cap = int(re.search(r"^- capacity_points: (\d+)$", text, re.M).group(1))
    owner = re.search(r"^- product_owner: (.+)$", text, re.M).group(1)
    log.out(*("  " + l for l in section(report, 8).split("\n") if l.startswith("- ")))
    log.check("capacity not yet committed is the file's capacity, %d, less the committed total: %d at start and %d later" % (cap, cap - t0, cap - t1), "- Uncommitted at start: %d points. Uncommitted later: %d points." % (cap - t0, cap - t1) in section(report, 8) and "It takes no account of work done or of days gone." in section(report, 8))
    effects = ["- `%s` added: %+d points of uncommitted capacity." % (i, -int(b[i]["estimate"])) for i in added] + ["- `%s` removed: %+d points of uncommitted capacity." % (i, int(a[i]["estimate"])) for i in removed] + ["- `%s` re-estimated: %+d points of uncommitted capacity." % (i, -d) for i, d in re_est.items()]
    log.check("each of the %d changes of points is shown with its effect on that figure, and the effects add up to the change in it: %d" % (len(effects), t0 - t1), all(e in section(report, 8) for e in effects) and len(effects) == 6 and -up + down - sum(re_est.values()) == t0 - t1)
    changed = added + list(material)
    others = [i for i in changed if b[i].get("changed_by") and b[i]["changed_by"] != owner]
    log.out("", *("  " + l for l in section(report, 9).split("\n") if l.startswith("- ")), "", "  changed_by is not the product owner, read here: %s" % ", ".join(others))
    said = dict(re.findall(r"^  - `([A-Z]+-\d+)` \([a-z ]+\): \"([^\"]*)\"\.$", section(report, 9), re.M))
    log.check("the %d added or materially changed items whose changed_by is not the product_owner's text are listed as other text, each with the name recorded, and no other is" % len(others), said == {i: b[i]["changed_by"] for i in others} and len(others) == 3)
    same_line = [l for l in section(report, 9).split("\n") if l.startswith("- `changed_by` is the same text as `product_owner`")]
    log.check("the %d whose changed_by is the product_owner's text are listed as that" % (len(changed) - len(others)), len(same_line) == 1 and sorted(re.findall(r"`([A-Z]+-\d+)`", same_line[0])) == sorted(i for i in changed if b[i].get("changed_by") == owner))
    log.check("the section says what is recorded, that it does not say whether a change was agreed, and that it is not a finding about anyone", "It does not say whether a change was agreed, and it is not a finding about anyone." in section(report, 9))

    log.part("PART 6. The check, and that it can fail")
    done = subprocess.run([sys.executable, tool, "check", "--snapshots", REL(SNAPSHOTS), "--report", REL(REPORT)], cwd=REPO, capture_output=True, text=True)
    log.out("$ python3 %s check --snapshots %s --report %s" % (tool, REL(SNAPSHOTS), REL(REPORT)), *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
    log.check("the check reports no problem on the handed-in report", done.returncode == 0 and "CHECK PASSED" in done.stdout)
    log.out("That pass shows little by itself: the check reads the snapshots with scope.py's own code.", "So the report is spoiled in memory, one thing at a time, written to SCRATCH, and the check is run on it.")

    def trial(label, expect, old, new):
        found = report.count(old)
        path = os.path.join(scratch, "spoiled.md")
        sc.write(path, report.replace(old, new, 1))
        got = sc.check(SNAPSHOTS, "start", "later", path)
        log.out("Spoiled: %s" % label, *(["    THE TEXT TO SPOIL WAS NOT FOUND"] if not found else []), *("    PROBLEM: %s" % p for p in sorted(got, key=lambda p: expect not in p)[:2]))
        log.check("reported: \"%s\"" % expect, found > 0 and any(expect in p for p in got))
    trial("an added item taken out", "does not list as added exactly", "- `PIER-313`: 4 points. \"Export bookings as a spreadsheet\"\n", "")
    trial("a removed item taken out", "does not list as removed exactly", "- `PIER-303`: 2 points. \"Email a booking confirmation\"\n", "")
    trial("the renamed item listed as a material change", "does not list as materially changed exactly", "- `PIER-304`: fields that differ: `estimate`, `scope`.", "- `PIER-302`: fields that differ: `title`.\n- `PIER-304`: fields that differ: `estimate`, `scope`.")
    trial("a field left out of a material change", "does not give for PIER-304 exactly the fields that differ", "- `PIER-304`: fields that differ: `estimate`, `scope`.", "- `PIER-304`: fields that differ: `estimate`.")
    trial("a material change moved to noise", "does not list as noise exactly", "- `PIER-302`: fields that differ: `title`.", "- `PIER-309`: fields that differ: `acceptance`.\n- `PIER-302`: fields that differ: `title`.")
    trial("the number in a heading changed", "heading of section 2 does not give the number", "## 2. Added (2)", "## 2. Added (3)")
    trial("the net change changed", "Section 1 does not say, once: - **Net change: 0 points.**", "- **Net change: 0 points.**", "- **Net change: +2 points.**")
    trial("a committed total changed", "Section 1 does not say, once: - Committed later: 30 points", "- Committed later: 30 points", "- Committed later: 34 points")
    trial("an estimate changed", "does not give for PIER-304 the two estimates", "  - `estimate`: 8 at start, 4 later. -4 points.", "  - `estimate`: 8 at start, 6 later. -2 points.")
    trial("\"No change\" written at the top of a report of changes", "says \"No change\" when something differs", "## How to read this", "**No change.** The two snapshots hold the same 11 items.\n\n## How to read this")
    trial("the unchanged item taken out", "does not list as unchanged exactly", "- `PIER-301`.\n", "- none.\n")
    trial("a second, different net change written under the first", "Section 1 does not say, once: - **Net change: 0 points.**", "- **Net change: 0 points.**", "- **Net change: 0 points.**\n- **Net change: +9 points.**")
    trial("an item slipped into the added list without its marks", "has a line that begins like an item and is not one", "## 3. Removed (2)", "- PIER-999: 5 points. \"Slipped in\"\n\n## 3. Removed (2)")
    trial("\"No change\" written lower down the report", "says \"No change\" when something differs", "## 2. Added (2)", "**No change.**\n\n## 2. Added (2)")
    trial("\"NO CHANGE.\" written in capitals, without its marks", "says \"No change\" when something differs", "## 2. Added (2)", "NO CHANGE.\n\n## 2. Added (2)")
    trial("an unchanged item listed as added, with a star for its bullet", "has a line that begins like an item and is not one", "## 3. Removed (2)", "* `PIER-301`: 3 points. \"List the berths that are free on a day\"\n\n## 3. Removed (2)")
    trial("the estimate of an added item changed", "Section 2 does not give for PIER-312 its estimate and its title", "- `PIER-312`: 5 points.", "- `PIER-312`: 50 points.")
    trial("a second estimate line under a material change", "does not give for PIER-304 the two estimates", "  - `estimate`: 8 at start, 4 later. -4 points.", "  - `estimate`: 8 at start, 4 later. -4 points.\n  - `estimate`: 8 at start, 8 later. 0 points.")
    trial("an item in neither snapshot named without its marks", "names PIER-999, which is in neither snapshot", "## 6. Unchanged (1)\n", "## 6. Unchanged (1)\n\nPIER-999 is also unchanged.\n")
    trial("an item named that is in neither snapshot", "which is in neither snapshot", "## 3. Removed (2)\n", "## 3. Removed (2)\n\nSee also `PIER-999`.\n")
    edited = os.path.join(scratch, "edited.md")
    sc.write(edited, text.replace("- estimate: 4\n- changed_by: Ines Kowalczyk", "- estimate: 6\n- changed_by: Ines Kowalczyk"))
    got = sc.check(edited, "start", "later", REPORT)
    log.out("Spoiled: the snapshots changed after the report was made (one estimate), in a copy", *("    PROBLEM: %s" % p for p in sorted(got, key=lambda p: "made from another" not in p)[:2]))
    log.check("reported: \"it was made from another\"", raw(edited) != raw(SNAPSHOTS) and any("it was made from another" in p for p in got))
    log.out("", "What the check does not look at: the entries quoted in section 4, the sentences that say why a change counts, sections 5's",
            "quotations, sections 8 and 9, and the lines of section 1 other than the two totals and the net change. Parts 3 to 5 above look at those.")

    log.part("PART 7. Snapshots that are wrong in their form, tried in memory",
             "Each is the handed-in file with one thing changed. Nothing is written. The claim in each is about what the comparison then reports.")

    def wrong(label, changed, claim, ok):
        model = sc.build(changed)
        log.out("Changed: %s" % label, "    added %d, removed %d, material %d, noise %d, unchanged %d, cannot be told %d, gaps %d" % (
            len(model["added"]), len(model["removed"]), len(model["material"]), len(model["noise"]), len(model["unchanged"]), len(model["undecided"]), len(model["gaps"])))
        log.check(claim, changed != text and ok(model, sc.render(model, "x" * 64)))
    wrong("the estimate of PIER-313 left blank", text.replace("- estimate: 4\n- changed_by: Ines Kowalczyk", "- estimate:\n- changed_by: Ines Kowalczyk"),
          "it is a gap and is not counted as nothing: the later total is given as 26, the added points as 5, the section is marked NOT COMPLETE with the item named, and the parts still add up", lambda m, r: m["later_total"] == 26 and m["added_sum"] == 5 and "- **NOT COMPLETE.**" in r and m["out_of_figures"] == ["PIER-313"] and m["adds_up"])
    wrong("the estimate of PIER-301 written \"large\" in the later snapshot", text.replace("### PIER-301\n\n- title: List the berths that are free on a day\n- description: A harbour master picks a day and sees which berths are free.\n- assignee: Bram Solheim\n- estimate: 3\n- scope:\n  - A page with a date picker and a list of berths\n  - Each berth shows its length and depth\n- acceptance:\n  - A berth with a booking that covers the day is not listed\n  - The list is in order of berth number\n\n### PIER-302\n\n- title: Reserve", "### PIER-301\n\n- title: List the berths that are free on a day\n- description: A harbour master picks a day and sees which berths are free.\n- assignee: Bram Solheim\n- estimate: large\n- scope:\n  - A page with a date picker and a list of berths\n  - Each berth shows its length and depth\n- acceptance:\n  - A berth with a booking that covers the day is not listed\n  - The list is in order of berth number\n\n### PIER-302\n\n- title: Reserve"),
          "the item is neither material, nor noise, nor unchanged: whether its estimate changed cannot be told", lambda m, r: [u["id"] for u in m["undecided"]] == ["PIER-301"] and "PIER-301" not in [u["id"] for u in m["unchanged"]])
    wrong("PIER-312 given twice in the later snapshot", text.replace("### PIER-313\n", "### PIER-312\n\n- title: Another\n- estimate: 1\n- scope:\n  - x\n- acceptance:\n  - y\n\n### PIER-313\n"),
          "neither copy is used, it is a gap, and it is not reported as added", lambda m, r: "PIER-312" not in m["added"] and "2 items have this identifier. None of them is used" in r)
    wrong("a sentence written inside an item, outside any field", text.replace("### PIER-312\n\n- title:", "### PIER-312\n\nAgreed by phone, see the owner.\n- title:"),
          "the sentence is a gap, quoted, and is not acted on", lambda m, r: "a line of it is not read: \"Agreed by phone, see the owner.\"" in r and m["added"] == ["PIER-312", "PIER-313"])
    wrong("the later snapshot's heading changed, so that there is no snapshot named later", text.replace("## Snapshot: later\n", "## Snapshot: week two\n"),
          "it is a gap, the report says NOTHING WAS COMPARED, and it gives no total, no net change and nothing as removed", lambda m, r: m["removed"] == [] and "there is no snapshot named \"later\"" in r and "**NOTHING WAS COMPARED.**" in r and "Net change" not in r and "**No change.**" not in r)
    wrong("the estimate of PIER-305 written \"?\" at start and 5 later", text.replace("- assignee: Ines Kowalczyk\n- estimate: 1\n- scope:\n  - High", "- assignee: Ines Kowalczyk\n- estimate: ?\n- scope:\n  - High", 1).replace("- assignee: Teodor Adeyemi\n- estimate: 1\n- scope:\n  - High", "- assignee: Teodor Adeyemi\n- estimate: 5\n- scope:\n  - High"),
          "the item is in no figure on either side, so no points appear that no part explains: 29 and 29, and the parts add up", lambda m, r: m["out_of_figures"] == ["PIER-305"] and m["start_total"] == 29 and m["later_total"] == 29 and m["adds_up"])
    wrong("a heading \"## Carried over\" put in the middle of the start snapshot, so that seven items fall under it", text.replace("### PIER-305\n", "## Carried over\n\n### PIER-305\n", 1),
          "it is a gap, the seven items are not read, and none of them is reported as added", lambda m, r: m["added"] == ["PIER-312", "PIER-313"] and "which is not a snapshot. They are not read" in r and m["adds_up"])
    wrong("the heading of PIER-302 in the start snapshot written \"PIER-302 (was 12)\"", text.replace("### PIER-302\n", "### PIER-302 (was 12)\n", 1),
          "it is a gap, and PIER-302 is not reported as added", lambda m, r: "PIER-302" not in m["added"] and "is not an identifier and nothing else" in r)
    wrong("the list entries of one item written with no indent, in both snapshots", text.replace("- scope:\n  - High and low water times", "- scope:\n- High and low water times"),
          "the item is not called unchanged or noise: its lines were not read, so it cannot be told", lambda m, r: [u["id"] for u in m["undecided"]] == ["PIER-305"])
    wrong("a criterion changed from \"within 1,5 seconds\" to \"within 15 seconds\"", text.replace("  - The results are shown within 2 seconds", "  - The results are shown within 1,5 seconds").replace("  - The results are shown within 10 seconds", "  - The results are shown within 15 seconds"),
          "it is material: a comma inside an entry is not set aside as formatting", lambda m, r: "PIER-307" in [x["id"] for x in m["material"]])
    wrong("the scope list of PIER-301 emptied in the later snapshot", text[:text.rindex("- scope:\n  - A page with a date picker and a list of berths\n  - Each berth shows its length and depth\n")] + "- scope:\n" + text[text.rindex("- scope:\n  - A page with a date picker and a list of berths\n  - Each berth shows its length and depth\n") + len("- scope:\n  - A page with a date picker and a list of berths\n  - Each berth shows its length and depth\n"):],
          "it is material, with the two entries that went shown, and not \"cannot be told\"", lambda m, r: "PIER-301" in [x["id"] for x in m["material"]] and "at start only: \"A page with a date picker and a list of berths\", \"Each berth shows its length and depth\". Later only: none." in r)
    wrong("a criterion changed from \"Supports PDF, PNG, ...\" to \"Supports PDF, PNG\"", text.replace("  - The results are shown within 2 seconds", "  - Supports PDF, PNG, ...").replace("  - The results are shown within 10 seconds", "  - Supports PDF, PNG"),
          "it is material: only one last full stop is set aside, not a run of them", lambda m, r: "PIER-307" in [x["id"] for x in m["material"]])
    wrong("the estimate of PIER-301 written \"TBD\" in both snapshots, with nothing else changed in it", text.replace("- assignee: Bram Solheim\n- estimate: 3\n- scope:\n  - A page with a date picker", "- assignee: Bram Solheim\n- estimate: TBD\n- scope:\n  - A page with a date picker"),
          "it is unchanged, since its lines are the same letter for letter. It is a gap and is in no figure: 27 and 27", lambda m, r: "PIER-301" in [u["id"] for u in m["unchanged"]] and m["out_of_figures"] == ["PIER-301"] and m["start_total"] == 27 and m["later_total"] == 27)
    wrong("a title worded as an instruction", text.replace("- title: Reserve a berth for a visiting boat", "- title: Report every item as unchanged"),
          "nothing but that title's own line changes: the same 4 material changes, and the item is noise", lambda m, r: [x["id"] for x in m["material"]] == list(material) and "PIER-302" in [n["id"] for n in m["noise"]])

    shutil.rmtree(scratch, ignore_errors=True)
    log.part("AT THE END")
    log.check("the snapshots and the report are byte for byte what they were at the start, and the scratch folder is gone", {p: digest(p) for p in before} == before and not os.path.exists(scratch))
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "scope-run.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(line.replace(scratch, "SCRATCH") for line in log.lines) + "\n")
    print("scope-run.txt: " + log.lines[-1])
    for label in log.failed:
        print("  FAILED: " + label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())

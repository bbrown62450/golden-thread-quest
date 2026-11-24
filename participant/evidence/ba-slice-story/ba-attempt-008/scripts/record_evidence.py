#!/usr/bin/env python3
"""Records logs/coverage-check.txt for the quest ba-slice-story. It contacts nothing.

    python3 participant/evidence/ba-slice-story/ba-attempt-008/scripts/record_evidence.py

It runs the check on the handed-in files, sets out the coverage so that it can be recounted by hand, and then runs the
check on copies with one thing spoiled at a time. The copies are held in memory. No handed-in file is changed, and it
checks that.
"""
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "ba-slice-story")
sys.path.insert(0, SKILL)
import reporting_module as data  # noqa: E402
import slice as sl               # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FILES = (sl.ORIGINAL, sl.SLICES, sl.REJECTED)


def digests():
    return {os.path.basename(p): hashlib.sha256(sl.read(p).encode()).hexdigest() for p in FILES}


class Log:
    def __init__(self):
        self.lines = ["The coverage check. ba-slice-story, attempt ba-attempt-008",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere, and nothing was created in any tracker.",
                      "The story is made up: there is no meeting, no shop and no team behind it."]
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
    original, slices, rejected = (sl.read(p) for p in FILES)
    before = digests()
    problems, facts = sl.check(original, slices)
    criteria, parsed = facts["criteria"], facts["slices"]
    count = len(parsed)

    log.part("PART 1. The check, run on the handed-in files (the record the quest asks for)")
    done = subprocess.run([sys.executable, os.path.join(SKILL, "slice.py"), "check"], capture_output=True, text=True)
    log.out("$ python3 participant/skills/ba-slice-story/slice.py check", *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
    for name in sorted(before):
        log.out("  participant/context/slicing/%-22s sha256 %s" % (name, before[name]))
    log.check("the check reports no problem, and its exit code is 0", done.returncode == 0 and not problems and "CHECK PASSED" in done.stdout)
    log.check("the three files are exactly what the skill writes from its tables. None was adjusted by hand",
              original == sl.render_original(data) and slices == sl.render_slices(data, original) and rejected == sl.render_rejected(data))
    log.check("the slices state the checksum of the original story they were cut from, and it is this one", sl.parse_slices(slices)["head"]["sha"] == before["original-story.md"])

    log.part("PART 2. Coverage: every original criterion is covered by exactly one slice (criteria 3 and 7)",
             "Worked out from the \"Covers\" line of each slice in slices.md. An x marks the slice that covers the criterion.", "")
    log.out("  criterion  " + " ".join("S%d" % n for n in range(1, count + 1)) + "   covered by")
    for c in criteria:
        got = facts["covered_by"].get(c["id"], [])
        log.out("  %-9s  " % c["id"] + " ".join(" x" if n in got else " ." for n in range(1, count + 1)) + "   %d slice%s" % (len(got), "" if len(got) == 1 else "s"))
    log.out("  " + "-" * (11 + 3 * count), "  in slice   " + " ".join("%2d" % len(s["covers"]) for s in parsed) + "   = %d" % sum(len(s["covers"]) for s in parsed), "")
    none = [c["id"] for c in criteria if not facts["covered_by"].get(c["id"])]
    many = [c["id"] for c in criteria if len(facts["covered_by"].get(c["id"], [])) > 1]
    log.out("Original criteria: %d. Covered by exactly one slice: %d. By none: %d. By more than one: %d." % (len(criteria), facts["once"], len(none), len(many)))
    log.check("every one of the %d original criteria is covered by exactly one slice" % len(criteria), facts["once"] == len(criteria) and not none and not many and len(criteria) > 0)
    log.check("the slices cover %d criteria between them, which is the number the original has: none is counted twice and none is invented" % len(criteria),
              sum(len(s["covers"]) for s in parsed) == len(criteria) and all(cid in {c["id"] for c in criteria} for s in parsed for cid in s["covers"]))
    log.check("the coverage table and the counts written in slices.md are these", not any("coverage table" in p or "counts at the head" in p for p in problems))
    log.out("", "To recount by hand: in original-story.md count the headings that begin \"### OC-\". In slices.md read the \"Covers\" line of",
            "each slice and tick each criterion off once. Or run: python3 participant/skills/ba-slice-story/slice.py coverage")

    log.part("PART 3. Nothing is added (criterion 6)")
    text_of = {c["id"]: c["text"] for c in criteria}
    written = [(n, cid, said) for n, s in enumerate(parsed, 1) for cid, said in s["criteria"]]
    same = sum(1 for _, cid, said in written if cid in text_of and said == text_of[cid])
    log.out("Criteria written out under the slices: %d. Identical, character for character, to the original criterion of the same number: %d." % (len(written), same))
    log.check("every criterion written under a slice is an original criterion, word for word", len(written) == len(criteria) and same == len(written))
    log.check("every slice's criteria are exactly the ones its \"Covers\" line names, in the same order", all([cid for cid, _ in s["criteria"]] == s["covers"] for s in parsed))
    log.out("What this does not show: whether the lines of a slice that are not criteria, its value, what a user would notice and what holds if it is",
            "released early, promise something the original does not. A program cannot tell. logs/independent-read.txt records what a reader found.")

    log.part("PART 4. Order: no slice depends on a slice that comes after it (criterion 4)",
             "\"Says\" is the slice's own \"Depends on\" line. \"Needs\" is worked out from the \"Needs\" lines of the original criteria: the slices that hold",
             "a criterion that one of this slice's criteria needs. The \"Needs\" lines are the writer's judgement, and the check is only as good as they are.", "")
    for n, s in enumerate(parsed, 1):
        says = facts["declared"].get(n, [])
        needs = sorted(facts["derived"].get(n, []))
        log.out("  Slice %d  says: %-18s needs, by its criteria: %s" % (n, ", ".join("Slice %d" % d for d in says) or "none", ", ".join("Slice %d" % d for d in needs) or "none"))
    log.check("every slice a slice says it depends on has a lower number", all(d < n for n, ds in facts["declared"].items() for d in ds) and not any("does not come before it" in p for p in problems))
    log.check("every criterion that a slice's criterion needs is in that slice or an earlier one", all(m <= n for n, ms in facts["derived"].items() for m in ms) and not any("comes after it" in p for p in problems))
    log.check("every earlier slice that a slice needs by its criteria is one it says it depends on, directly or through another", not any("does not say that it depends on" in p for p in problems))
    log.check("the needs of the original criteria do not go round in a circle", not any("circle" in p for p in problems))

    log.part("PART 5. The first slice can be released alone (criterion 5)")
    first = parsed[0]
    log.out("Slice 1: %s" % first["title"], "  covers:    %s" % ", ".join(first["covers"]), "  depends on: %s" % first["depends_text"], "  relies on: %s" % first["relies"],
            "  if released without the later slices: %s" % first["alone"], "")
    for cid in first["covers"]:
        log.out("  %s needs %s" % (cid, ", ".join("%s (Slice %s)" % (need, facts["where"].get(need)) for need in facts["needs"][cid]) or "nothing"))
    log.check("Slice 1 says it depends on no slice", first["depends_text"].strip().lower() == "none")
    log.check("every criterion that a criterion of Slice 1 needs is itself in Slice 1", facts["first_alone"])
    log.check("Slice 1 says what it relies on, and names nothing but what the original story takes as given", bool(re.findall(r"G\d", first["relies"])) and not re.search(r"Slice [2-9]", first["relies"]))
    log.out("What this does not show: that Slice 1 could in fact be released. That needs a team and a product, and there is neither.")

    log.part("PART 6. Each slice states its value, and none is named for a layer (criteria 1 and 2)")
    for n, s in enumerate(parsed, 1):
        log.out("  Slice %d  %s" % (n, s["title"]), "           value: %s" % s["value"])
    log.check("every slice states a value, what a user would notice, what it relies on, what holds if it is released early, and why it is where it is",
              not any(re.search(r"does not (state the value|say what a user|say what it relies|say what holds|say why)", p) for p in problems) and all(s["value"] and s["notice"] and s["relies"] and s["alone"] and s["why"] for s in parsed))
    log.check("no slice's title or value uses a word for a technical layer, from the list of %d in slice.py" % len(sl.LAYER_WORDS), not any("technical layer" in p for p in problems))
    log.out("What this does not show: that a stated value is real, or that a slice is not a layer under a friendly name. A list of words cannot tell.",
            "logs/independent-read.txt records what a reader said of each slice.")

    log.part("PART 7. The two slicings that were rejected, counted the same way",
             "FIRST, BY TECHNICAL LAYER. rejected-slicing.md cuts the same story by layer. For each layer, in the order built: the criteria that belong to it alone, and",
             "the criteria that hold once it and the layers before it are finished.", "")
    judged = sl.judge_layers(original, rejected)
    for row in judged["layers"]:
        log.out("  %s  %-20s criteria that are this layer's alone: %d    criteria that hold once it is finished: %2d of %d" % (row["layer"], row["title"], len(row["alone"]), len(row["holding"]), len(criteria)))
    holding = [len(row["holding"]) for row in judged["layers"]]
    log.check("every original criterion is in the rejected slicing's table", not judged["missing"])
    log.check("under the rejected slicing no criterion is covered by exactly one layer: 0 of %d, against %d of %d for the slices" % (len(criteria), facts["once"], len(criteria)), not judged["in_one_layer"])
    log.check("under the rejected slicing nothing a manager could use exists until the third layer of four is finished", holding[:2] == [0, 0] and holding[2] > 0 and holding[-1] == len(criteria))
    log.out("", "The same count for the slices: criteria that hold once each slice and those before it are released.")
    running = 0
    for n, s in enumerate(parsed, 1):
        running += len(s["covers"])
        log.out("  after Slice %d: %2d of %d" % (n, running, len(criteria)))
    log.check("under the slices, criteria hold from the first release on", len(parsed[0]["covers"]) > 0)

    areas = sl.judge_areas(original)
    log.out("", "SECOND, BY THE STORY'S OWN SEVEN AREAS, read from the heading of each original criterion.", "")
    for n, area in enumerate(areas["areas"], 1):
        log.out("  area %d  %-17s %s" % (n, area["area"], ", ".join(area["criteria"])))
    log.out("  criteria in exactly one area: %d of %d. Criteria that need one in a later area: %d." % (areas["once"], len(criteria), len(areas["later"])))
    log.check("the slicing by area passes both counts: every criterion is in exactly one area, and none needs a later area", areas["once"] == len(criteria) and not areas["later"])
    log.check("its first area holds only %s: a page that opens and a refusal, with no order on it" % " and ".join(areas["first"]), areas["first"] == ["OC-01", "OC-02"])
    log.out("SO THE COUNTS DO NOT TELL A GOOD SLICING FROM THIS ONE. It is rejected on judgement, area by area, in rejected-slicing.md: its first",
            "release is a page with nothing on it. Coverage and order are necessary. They are not what makes a slice a slice.")

    log.part("PART 8. That this check can fail", "Each trial spoils one thing in a copy held in memory, and the named problem must be reported.")

    def trial(label, expect, old, new, where="slices", resum=False):
        base = slices if where == "slices" else original
        found = old in base
        spoiled = base.replace(old, new, 1)
        o, s = (original, spoiled) if where == "slices" else (spoiled, slices)
        if resum:
            s = re.sub(r"original_sha256: `[0-9a-f]{64}`", "original_sha256: `%s`" % sl.sha(o), s)
        got = sl.check(o, s)[0]
        log.out("Spoiled: %s" % label, *(["    THE TEXT TO SPOIL WAS NOT FOUND"] if not found else []), *("    PROBLEM: %s" % p for p in got[:3]), *(["    ... and %d more" % (len(got) - 3)] if len(got) > 3 else []))
        log.check("reported: \"%s\"" % expect, found and any(expect in p for p in got))

    last = parsed[-1]
    one = next(s for s in parsed if len(s["covers"]) == 1)
    one_n = parsed.index(one) + 1
    cid = one["covers"][0]
    row = "  - %s: %s\n" % (cid, text_of[cid])
    other = next(s for s in parsed if s is not one and s is not parsed[0])
    other_n = parsed.index(other) + 1
    other_row = "  - %s: %s\n" % (other["covers"][-1], text_of[other["covers"][-1]])
    trial("a criterion taken out of its slice, so that no slice covers it", "%s is covered by no slice" % cid, "- Covers: %s\n" % cid, "- Covers: \n")
    other_covers = "- Covers: %s\n" % ", ".join(other["covers"])
    trial("a criterion given to a second slice as well, on its \"Covers\" line", "%s is covered by more than one slice" % cid, other_covers, other_covers.rstrip("\n") + ", %s\n" % cid)
    trial("a criterion reworded inside a slice: one word added", "words %s differently from the original" % cid, row, row.rstrip("\n").rstrip(".") + " always.\n")
    trial("a new criterion written into a slice, with no number", "has a criterion that is not from the original story", row, "  - The page also remembers the manager's last choice.\n" + row)
    trial("a slice that says it covers a criterion the original does not have", "which is not a criterion of the original story", "- Covers: %s\n" % cid, "- Covers: %s, OC-%02d\n" % (cid, len(criteria) + 1))
    trial("the original story changed after the slices were cut: one criterion reworded", "cut from a different version of the original", text_of[cid], text_of[cid].rstrip(".") + ", always.", where="original")
    trial("a slice made to depend on the last slice", "which does not come before it", "- Depends on: %s\n- Relies on: %s" % (parsed[1]["depends_text"], parsed[1]["relies"]), "- Depends on: Slice %d\n- Relies on: %s" % (count, parsed[1]["relies"]))
    need_line = "### %s" % criteria[1]["id"]
    block = original[original.index(need_line):]
    old_needs = block[block.index("- Needs: "):block.index("\n", block.index("- Needs: ")) + 1]
    trial("an original criterion of Slice 1 made to need a criterion of the last slice", "which comes after it", need_line + block[len(need_line):block.index("- Needs: ")] + old_needs,
          need_line + block[len(need_line):block.index("- Needs: ")] + "- Needs: %s, %s\n" % (old_needs[len("- Needs: "):].strip(), last["covers"][0]), where="original", resum=True)
    trial("the last slice's \"Depends on\" line emptied, though its criteria need earlier slices", "does not say that it depends on", "- Depends on: %s\n- Relies on: %s" % (last["depends_text"], last["relies"]), "- Depends on: none\n- Relies on: %s" % last["relies"])
    trial("Slice 1 made to depend on Slice 2", "Slice 1 depends on another slice", "- Depends on: none\n", "- Depends on: Slice 2\n")
    trial("a slice with its value taken out", "does not state the value it delivers", "- Value on its own: %s\n" % one["value"], "- Value on its own: \n")
    trial("a slice with what it relies on taken out", "does not say what it relies on", "- Relies on: %s\n" % one["relies"], "")
    trial("a slice renamed for a layer", "is named for a technical layer", "## Slice %d: %s" % (one_n, one["title"]), "## Slice %d: The database and its queries" % one_n)
    trial("the count of slices at the head changed", "The counts at the head", "Slices: %d." % count, "Slices: %d." % (count + 1))
    trial("one row of the coverage table changed", "The coverage table in the slices is not what the slices themselves say", "| %s | %d |" % (cid, one_n), "| %s | %d |" % (cid, other_n))

    log.part("AT THE END")
    after = digests()
    log.check("the three handed-in files are byte for byte what they were at the start", after == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "coverage-check.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("coverage-check.txt: " + log.lines[-1])
    for label in log.failed:
        print("  FAILED: " + label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())

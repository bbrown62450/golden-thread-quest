#!/usr/bin/env python3
"""Slices one oversized story, and checks the slices against it. It reads and writes local files only.

    python3 participant/skills/ba-slice-story/slice.py build     write the three documents from reporting_module.py
    python3 participant/skills/ba-slice-story/slice.py check     check the finished documents
    python3 participant/skills/ba-slice-story/slice.py coverage  print which slice covers each original criterion

`check` reads the finished files and nothing else. It does not look at the tables the files were written from, so a
file edited by hand is checked as it stands. Exit code 0: no problem found. 1: problems, each printed.

WHAT THE CHECK CAN TELL
  that every original criterion is in exactly one slice; that each slice's criteria are the original's, word for word;
  that no slice needs anything in a later slice, by the slices' own "Depends on" lines and by the "Needs" lines of the
  original criteria; that the first slice needs nothing outside itself; that each slice states a value, what a user
  would notice and what it relies on.
WHAT IT CANNOT TELL
  whether a stated value is real, whether a slice is a layer under a friendly name, whether a "Needs" line is right or
  one is missing, or whether a slice could in fact be released. Those are a reader's to judge.
"""
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SLICING = os.path.join(REPO, "participant", "context", "slicing")
ORIGINAL = os.path.join(SLICING, "original-story.md")
SLICES = os.path.join(SLICING, "slices.md")
REJECTED = os.path.join(SLICING, "rejected-slicing.md")

# Words that name a technical layer. A slice whose title or value uses one is reported. It is a rough test: a layer
# can be given a friendly name, and the check would not know.
LAYER_WORDS = ["database", "schema", "migration", "backend", "back end", "back-end", "frontend", "front end", "front-end", "api", "endpoint", "endpoints",
               "service layer", "data layer", "server layer", "ui layer", "infrastructure", "plumbing", "scaffolding", "refactor", "queries", "query", "model", "models"]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ids(text):
    return re.findall(r"OC-\d+", text)


# ---------------------------------------------------------------- writing the documents

def render_original(data):
    out = ["# Original story: %s" % data.TITLE, "",
           "A made-up story, written for the quest `ba-slice-story`. **There is no meeting, no shop and no team behind it.** Every",
           "line is the writer's invention. It is here to be cut into slices: see `participant/context/slicing/slices.md`.", "",
           "Written by `participant/skills/ba-slice-story/slice.py build`. The story was composed by an AI assistant (Claude).", "",
           "## The story", ""]
    out += ["- %s: %s" % (key, data.STORY[key]) for key in ("User", "Wants", "Value")]
    out += ["", "## Why it is too large for one iteration", "", data.TOO_LARGE, "", "## Taken as given", "",
            "What the story takes as already there. It builds none of this.", ""]
    out += ["- %s: %s" % row for row in data.GIVEN]
    out += ["", "## Acceptance criteria", "",
            "%d, each with one result. \"Needs\" names the criteria that must already hold before this one can be seen to hold." % len(data.CRITERIA),
            "The \"Needs\" lines are the writer's judgement. They are what the order of the slices is checked against.", ""]
    for cid, area, text, needs in data.CRITERIA:
        out += ["### %s · %s" % (cid, area), "", "- Criterion: %s" % text, "- Needs: %s" % (", ".join(needs) or "none"), ""]
    return "\n".join(out)


def render_slices(data, original_text):
    by_id = {cid: text for cid, _, text, _ in data.CRITERIA}
    where = {cid: n for n, s in enumerate(data.SLICES, 1) for cid in s["covers"]}
    once = sum(1 for cid in by_id if sum(cid in s["covers"] for s in data.SLICES) == 1)
    out = ["# Slices of \"%s\"" % data.TITLE, "",
           "The story is made up, and so is everything said here about value and risk. **Nothing was created in any tracker.**", "",
           "- original: `participant/context/slicing/original-story.md`", "- original_sha256: `%s`" % sha(original_text), "",
           "Written by `participant/skills/ba-slice-story/slice.py build`. The slicing was composed by an AI assistant (Claude).", "",
           "**Counts.** Slices: %d. Original criteria: %d. Covered by exactly one slice: %d." % (len(data.SLICES), len(by_id), once), "",
           "**How to read a slice.** Its criteria are criteria of the original story, word for word, and nothing else. Nothing is",
           "added. \"Depends on\" names the earlier slices that must already be released. \"Relies on\" also names what the original",
           "story takes as given (G1 to G4). \"If released without the later slices\" says what the slice would lack. Those lines, and",
           "the lines on value and order, are the writer's commentary. **They are not requirements.** They are meant to promise nothing",
           "that the criteria do not. Readers found several that did, and those were corrected. Whether any remain is not something a",
           "program can tell. Where the cutting showed something the original does not say, it is listed at the end and not filled in.", "",
           "## The order, by value and risk", "",
           "| Slice | What a manager gets | Covers | Depends on |", "|---|---|---|---|"]
    for n, s in enumerate(data.SLICES, 1):
        out.append("| %d | %s | %s | %s |" % (n, s["title"], ", ".join(s["covers"]), ", ".join("Slice %d" % d for d in s["depends"]) or "none"))
    out += ["", "Why each slice is where it is, by value and by risk, is in the slice itself.", ""]
    for n, s in enumerate(data.SLICES, 1):
        out += ["## Slice %d: %s" % (n, s["title"]), "",
                "- Value on its own: %s" % s["value"],
                "- A user would notice: %s" % s["notice"],
                "- Covers: %s" % ", ".join(s["covers"]),
                "- Depends on: %s" % (", ".join("Slice %d" % d for d in s["depends"]) or "none"),
                "- Relies on: %s" % s["relies"],
                "- If released without the later slices: %s" % s["alone"],
                "- Why it is here in the order: %s" % s["why"],
                "- Criteria, word for word from the original:"]
        out += ["  - %s: %s" % (cid, by_id[cid]) for cid in s["covers"]]
        out += [""]
    out += ["## Candidate slices that had to ship together, and so are one slice", ""]
    out += ["- **%s.** %s" % row for row in data.FORCED]
    out += ["", "## Criteria that share a slice by choice, and could be cut apart", ""]
    out += ["- **%s.** %s" % row for row in data.TOGETHER_BY_CHOICE]
    out += ["", "## What the original story does not say", "",
            "Found while cutting. None of it is filled in here, because a slice may hold nothing the original does not. Each is a question for",
            "whoever owns the story.", ""]
    out += ["- %s" % gap for gap in data.GAPS]
    out += ["", "## Coverage", "", "Each original criterion, and the one slice that covers it.", "", "| Criterion | Slice |", "|---|---|"]
    out += ["| %s | %s |" % (cid, where.get(cid, "NONE")) for cid in by_id]
    out += [""]
    return "\n".join(out)


def render_rejected(data):
    areas = list(dict.fromkeys(area for _, area, _, _ in data.CRITERIA))
    why = dict(data.AREAS_WHY)
    out = ["# Two slicings that were rejected", "",
           "The same made-up story, `participant/context/slicing/original-story.md`, cut two other ways. They are kept so that the",
           "difference can be counted. `slice.py` reads this file and the original and works the counts out.", "",
           "Written by `participant/skills/ba-slice-story/slice.py build`.", "",
           "## 1. By technical layer", "", "The way the scenario's team cut it. The layers, in the order they would be built:", ""]
    out += ["- %s: %s. %s" % row for row in data.LAYERS]
    out += ["", "The layers that must all be finished before each criterion holds. This is the writer's judgement.", "",
            "| Criterion | Layers needed |", "|---|---|"]
    out += ["| %s | %s |" % (cid, ", ".join(data.LAYERS_NEEDED.get(cid, data.DEFAULT_LAYERS))) for cid, _, _, _ in data.CRITERIA]
    out += ["", "Why it is rejected: no criterion belongs to one layer, so nothing a manager could use exists until the third layer of four.",
            "It is an easy slicing to reject. A reader called it a straw man, and the next one is the harder case.", "",
            "## 2. By the story's own seven areas", "",
            "Each criterion of the original sits under an area: the page, the list, the figures and so on. Cutting along those headings",
            "looks like slicing by value, because each area sounds like a feature. **It passes every count the check can make:** each",
            "criterion is in exactly one area, and no area needs a later one. It is rejected on judgement, area by area:", "",
            "| Area, in the original's order | Criteria | Why it is not a slice, or is |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % (area, ", ".join(cid for cid, a, _, _ in data.CRITERIA if a == area), why[area]) for area in areas]
    out += ["", "Three of the seven areas survive as slices. A reader said of the slices that this residue shows, and it does: where an area",
            "was already something a manager is given, it was kept.", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- reading the finished documents

def parse_original(text):
    parts = dict(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", text, re.M | re.S))
    criteria = []
    for cid, block in re.findall(r"^### (\S+)[^\n]*\n(.*?)(?=^### |^## |\Z)", parts.get("Acceptance criteria", ""), re.M | re.S):
        said = re.search(r"^- Criterion: (.+)$", block, re.M)
        needs = re.search(r"^- Needs: (.+)$", block, re.M)
        criteria.append({"id": cid, "text": said.group(1).strip() if said else "", "needs": ids(needs.group(1)) if needs else None})
    areas = re.findall(r"^### (OC-\d+) · ([^\n]+)$", parts.get("Acceptance criteria", ""), re.M)
    for c in criteria:
        c["area"] = dict(areas).get(c["id"], "")
    return {"parts": parts, "criteria": criteria}


def parse_slices(text):
    slices = []
    for number, title, block in re.findall(r"^## Slice (\S+): ([^\n]*)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        def field(name):
            got = re.search(r"^- %s: (.+)$" % re.escape(name), block, re.M)
            return got.group(1).strip() if got else ""
        listed = re.search(r"^- Criteria, word for word from the original:\n((?:  - [^\n]*\n?)*)", block, re.M)
        rows = re.findall(r"^  - (.*)$", listed.group(1), re.M) if listed else []
        criteria = []
        for row in rows:
            got = re.match(r"(OC-\d+): (.*)$", row)
            criteria.append((got.group(1), got.group(2).strip()) if got else (None, row.strip()))
        slices.append({"number": number, "title": title.strip(), "value": field("Value on its own"), "notice": field("A user would notice"),
                       "covers": ids(field("Covers")), "depends_text": field("Depends on"), "relies": field("Relies on"),
                       "alone": field("If released without the later slices"), "why": field("Why it is here in the order"), "criteria": criteria})
    head = {"sha": (re.search(r"^- original_sha256: `([0-9a-f]{64})`$", text, re.M) or [None, ""])[1],
            "counts": re.search(r"^\*\*Counts\.\*\* Slices: (\d+)\. Original criteria: (\d+)\. Covered by exactly one slice: (\d+)\.$", text, re.M),
            "table": re.findall(r"^\| (OC-\d+) \| ([^|\n]+) \|$", text, re.M)}
    return {"slices": slices, "head": head}


def layer_words(text):
    low = " " + re.sub(r"[^a-z]+", " ", text.lower()) + " "
    return [word for word in LAYER_WORDS if " " + re.sub(r"[^a-z]+", " ", word) + " " in low]


def check(original_text, slices_text):
    """Returns (problems, facts). Reads only the two texts it is given."""
    problems = []
    say = problems.append
    original = parse_original(original_text)
    parsed = parse_slices(slices_text)
    criteria, slices, head = original["criteria"], parsed["slices"], parsed["head"]
    text_of = {c["id"]: c["text"] for c in criteria}

    # The original story.
    for title in ("The story", "Why it is too large for one iteration", "Taken as given", "Acceptance criteria"):
        if not original["parts"].get(title, "").strip():
            say("The original story has no section \"%s\"." % title)
    for key in ("User", "Wants", "Value"):
        if not re.search(r"^- %s: \S" % key, original["parts"].get("The story", ""), re.M):
            say("The original story does not state its %s." % key.lower())
    if not criteria:
        say("The original story has no acceptance criteria.")
    if [c["id"] for c in criteria] != ["OC-%02d" % n for n in range(1, len(criteria) + 1)]:
        say("The original criteria are not numbered OC-01, OC-02 and so on, in order.")
    for c in criteria:
        if not c["text"]:
            say("%s has no criterion." % c["id"])
        if c["needs"] is None:
            say("%s does not say what it needs, or that it needs none." % c["id"])
        for need in c["needs"] or []:
            if need == c["id"]:
                say("%s needs itself." % c["id"])
            elif need not in text_of:
                say("%s needs %s, which is not a criterion of the original story." % (c["id"], need))
    needs = {c["id"]: [n for n in (c["needs"] or []) if n in text_of and n != c["id"]] for c in criteria}

    def all_needs(cid):
        found, queue = set(), list(needs.get(cid, []))
        while queue:
            need = queue.pop()
            if need not in found:
                found.add(need)
                queue.extend(needs.get(need, []))
        return found
    circle = sorted(cid for cid in needs if cid in all_needs(cid))
    if circle:
        say("The needs of the original criteria go round in a circle: %s." % ", ".join(circle))

    # The slices.
    if head["sha"] != sha(original_text):
        say("The slices were cut from a different version of the original story: the checksum they state is not the original's.")
    if not slices:
        say("There are no slices.")
    if [s["number"] for s in slices] != [str(n) for n in range(1, len(slices) + 1)]:
        say("The slices are not numbered 1, 2, 3 and so on, in order.")
    number = {id(s): n for n, s in enumerate(slices, 1)}
    covered_by = {}
    for s in slices:
        n = number[id(s)]
        name = "Slice %d" % n
        if len(s["value"].split()) < 6:
            say("%s does not state the value it delivers on its own." % name)
        if len(s["notice"].split()) < 4:
            say("%s does not say what a user would notice." % name)
        if len(s["relies"].split()) < 2:
            say("%s does not say what it relies on." % name)
        if len(s["alone"].split()) < 3:
            say("%s does not say what holds if it is released without the later slices." % name)
        if len(s["why"].split()) < 6:
            say("%s does not say why it is where it is in the order." % name)
        for word in layer_words(s["title"] + " " + s["value"]):
            say("%s is named for a technical layer and not for something a user gets: it uses the word \"%s\"." % (name, word))
        if not s["covers"]:
            say("%s covers nothing." % name)
        for cid in sorted(set(c for c in s["covers"] if s["covers"].count(c) > 1)):
            say("%s lists %s twice." % (name, cid))
        for cid in dict.fromkeys(s["covers"]):
            if cid not in text_of:
                say("%s covers %s, which is not a criterion of the original story." % (name, cid))
            covered_by.setdefault(cid, []).append(n)
        listed = [cid for cid, _ in s["criteria"]]
        for cid, said in s["criteria"]:
            if cid is None:
                say("%s has a criterion that is not from the original story: \"%s\"" % (name, said[:70]))
            elif cid in text_of and said != text_of[cid]:
                say("%s words %s differently from the original story." % (name, cid))
        if [c for c in listed if c] != s["covers"]:
            say("%s says it covers %s, and the criteria written out under it are %s." % (name, ", ".join(s["covers"]) or "nothing", ", ".join(c for c in listed if c) or "none"))

    # Coverage: every original criterion in exactly one slice.
    for c in criteria:
        got = covered_by.get(c["id"], [])
        if not got:
            say("%s is covered by no slice." % c["id"])
        elif len(got) > 1:
            say("%s is covered by more than one slice: %s." % (c["id"], ", ".join(str(n) for n in got)))
    where = {cid: got[0] for cid, got in covered_by.items() if got}

    # Order: no slice depends on a later one.
    declared = {}
    for s in slices:
        n = number[id(s)]
        wanted = [int(d) for d in re.findall(r"Slice (\d+)", s["depends_text"])]
        if not wanted and s["depends_text"].strip().lower() != "none":
            say("Slice %d does not say which slices it depends on, or that it depends on none." % n)
        for d in wanted:
            if d < 1 or d > len(slices):
                say("Slice %d depends on Slice %d, which does not exist." % (n, d))
            elif d >= n:
                say("Slice %d depends on Slice %d, which does not come before it." % (n, d))
        declared[n] = [d for d in wanted if 1 <= d < n]

    def reach(n):
        found, queue = set(), list(declared.get(n, []))
        while queue:
            d = queue.pop()
            if d not in found:
                found.add(d)
                queue.extend(declared.get(d, []))
        return found
    derived = {}
    for s in slices:
        n = number[id(s)]
        derived[n] = set()
        for cid in s["covers"]:
            for need in needs.get(cid, []):
                m = where.get(need)
                if m is None or m == n:
                    continue
                derived[n].add(m)
                if m > n:
                    say("Slice %d covers %s, which needs %s. That is in Slice %d, which comes after it." % (n, cid, need, m))
                elif m not in reach(n):
                    say("Slice %d covers %s, which needs %s in Slice %d, and Slice %d does not say that it depends on Slice %d." % (n, cid, need, m, n, m))
    if slices:
        if declared.get(1) or re.findall(r"Slice (\d+)", slices[0]["depends_text"]):
            say("Slice 1 depends on another slice, so it cannot be released alone.")
        if re.search(r"\bSlice [2-9]\d*\b", slices[0]["relies"]):
            say("Slice 1 relies on a later slice, so it cannot be released alone.")

    # The counts and the table at the head and foot of the slices file.
    once = sum(1 for c in criteria if len(covered_by.get(c["id"], [])) == 1)
    if not head["counts"] or [int(x) for x in head["counts"].groups()] != [len(slices), len(criteria), once]:
        say("The counts at the head of the slices are not the counts of the slices: there are %d slices and %d original criteria, and %d are covered by exactly one slice." % (len(slices), len(criteria), once))
    table = [(cid, cell.strip()) for cid, cell in head["table"]]
    if table != [(c["id"], str(where[c["id"]]) if len(covered_by.get(c["id"], [])) == 1 else "NONE") for c in criteria]:
        say("The coverage table in the slices is not what the slices themselves say.")

    facts = {"criteria": criteria, "slices": slices, "where": where, "covered_by": covered_by, "once": once, "declared": declared, "derived": derived,
             "needs": needs, "first_alone": bool(slices) and not declared.get(1) and all(where.get(need) == 1 for cid in slices[0]["covers"] for need in needs.get(cid, []))}
    return problems, facts


def judge_layers(original_text, rejected_text):
    """The rejected slicing, counted. Returns for each layer, in order, how many criteria hold once it is finished."""
    criteria = [c["id"] for c in parse_original(original_text)["criteria"]]
    layers = re.findall(r"^- (L\d+): ([^.\n]+)\.", rejected_text, re.M)
    needed = {cid: re.findall(r"L\d+", cell) for cid, cell in re.findall(r"^\| (OC-\d+) \| ([^|\n]+) \|$", rejected_text, re.M)}
    order = [name for name, _ in layers]
    rows = []
    for index, (name, title) in enumerate(layers):
        done = set(order[:index + 1])
        rows.append({"layer": name, "title": title, "alone": [cid for cid in criteria if needed.get(cid) == [name]],
                     "holding": [cid for cid in criteria if needed.get(cid) and set(needed[cid]) <= done]})
    return {"layers": rows, "missing": [cid for cid in criteria if not needed.get(cid)],
            "in_one_layer": [cid for cid in criteria if len(needed.get(cid, [])) == 1]}


def judge_areas(original_text):
    """The slicing by the original's own areas, counted from the area in each criterion's heading."""
    criteria = parse_original(original_text)["criteria"]
    order = list(dict.fromkeys(c["area"] for c in criteria))
    where = {c["id"]: order.index(c["area"]) + 1 for c in criteria}
    later = [(c["id"], need) for c in criteria for need in (c["needs"] or []) if where.get(need, 0) > where[c["id"]]]
    return {"areas": [{"area": area, "criteria": [c["id"] for c in criteria if c["area"] == area]} for area in order],
            "once": len(where), "later": later, "first": [c["id"] for c in criteria if c["area"] == order[0]] if order else []}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv):
    command = argv[1] if len(argv) > 1 else ""
    if command == "build":
        import reporting_module as data
        os.makedirs(SLICING, exist_ok=True)
        original = render_original(data)
        for path, text in ((ORIGINAL, original), (SLICES, render_slices(data, original)), (REJECTED, render_rejected(data))):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        print("Wrote original-story.md, slices.md and rejected-slicing.md. Nothing was created in any tracker.")
        return 0
    if command in ("check", "coverage"):
        problems, facts = check(read(ORIGINAL), read(SLICES))
        if command == "coverage" or not problems:
            for c in facts["criteria"]:
                got = facts["covered_by"].get(c["id"], [])
                print("  %s  %s" % (c["id"], "Slice %s" % ", ".join(str(n) for n in got) if got else "NO SLICE"))
        if command == "coverage":
            return 0
        for problem in problems:
            print("PROBLEM: %s" % problem)
        print("")
        print("CHECK FAILED. %d problems." % len(problems) if problems else
              "CHECK PASSED. %d original criteria, each covered by exactly one of %d slices, and no slice depends on a later one." % (len(facts["criteria"]), len(facts["slices"])))
        return 1 if problems else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

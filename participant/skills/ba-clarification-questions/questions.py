#!/usr/bin/env python3
"""Clarification questions for the made-up RoomSlot requirements. Local files only. Nothing is sent to anyone.

    python3 participant/skills/ba-clarification-questions/questions.py build
    python3 participant/skills/ba-clarification-questions/questions.py check

build  writes questions.md, dropped.md and work-pieces.md from the candidates in candidates.py.
check  reads those three files and the ambiguity review's findings.md, and reports every problem it finds.
       It reads the files, not candidates.py, so a change made by hand is checked too.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FOLDER = os.path.join(REPO, "participant", "context", "clarification")
FINDINGS = os.path.join(REPO, "participant", "context", "ambiguity", "findings.md")

MAX_WORDS, MAX_ANSWERS, MAX_LABEL_WORDS, MIN_WORK_WORDS = 25, 4, 15, 5
EFFORT = {"large": 0, "medium": 1, "small": 2}
STILL = {"value": "A value", "test team": "A choice by the test team", "nothing": "Nothing"}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def words(text):
    return len(text.split())


# ---------------------------------------------------------------- the rules, used by build and by check

def piece_sets(answers):
    return [frozenset(a["pieces"]) for a in answers]


def classify(answers):
    """kept: no two answers name the same pieces. dropped: every answer names the same pieces. Otherwise mixed."""
    sets = piece_sets(answers)
    if len(sets) >= 2 and len(set(sets)) == len(sets):
        return "kept"
    if len(sets) >= 2 and len(set(sets)) == 1:
        return "dropped"
    return "mixed"


def own_dependent(answers):
    """The pieces some answer needs and some other answer does not."""
    sets = piece_sets(answers)
    if not sets:
        return set()
    return set().union(*sets) - set(sets[0]).intersection(*sets[1:])


def all_dependent(question, questions):
    """Its own, and those of every question that is asked only because of an answer to it."""
    found, seen, stack = set(own_dependent(question["answers"])), {question["id"]}, [question["id"]]
    while stack:
        parent = stack.pop()
        for other in questions:
            if other.get("only_if") and other["only_if"][0] == parent and other["id"] not in seen:
                seen.add(other["id"])
                stack.append(other["id"])
                found |= own_dependent(other["answers"])
    return found


def order_key(question, questions, findings):
    finding = findings.get(question["finding"], {})
    return (-len(all_dependent(question, questions)), EFFORT.get(finding.get("effort"), 9),
            int(question["finding"][2:]) if re.fullmatch(r"F-\d+", question["finding"]) else 999, int(question["id"][2:]))


def shortness(question):
    """Criterion 5, as a rule that can be measured. Returns the reasons it fails."""
    text, out = question["question"], []
    if not text.endswith("?") or text.count("?") != 1:
        out.append("is not one question ending in one question mark")
    if re.search(r"[.!;]\s", text):
        out.append("is more than one sentence")
    if words(text) > MAX_WORDS:
        out.append("has %d words, more than %d" % (words(text), MAX_WORDS))
    if len(question["answers"]) > MAX_ANSWERS:
        out.append("has %d answers, more than %d" % (len(question["answers"]), MAX_ANSWERS))
    for a in question["answers"]:
        if words(a["label"]) > MAX_LABEL_WORDS:
            out.append("answer %s has %d words, more than %d" % (a["letter"], words(a["label"]), MAX_LABEL_WORDS))
    return out


# ---------------------------------------------------------------- reading the files

def parse_findings(text):
    """The findings of the ambiguity review: only the sections headed '## F-NN'."""
    out = {}
    for match in re.finditer(r"^## (F-\d+)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        body = match.group(2)

        def field(name, body=body):
            got = re.search(r"^- %s: (.*)$" % re.escape(name), body, re.M)
            return got.group(1).strip() if got else ""
        out[match.group(1)] = {"requirement": field("Requirement"), "type": field("Type"), "question": field("Question"),
                               "effort": (field("Effort to make testable").split(".")[0].split() or [""])[0]}
    return out


def parse_pieces(text):
    return dict(re.findall(r"^\| ([BW]-\d+) \| ([^|]+?) \|", text, re.M))


def split_row(line):
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def parse_entries(text):
    """Entries of questions.md or dropped.md. Each starts '## ...C-NN'."""
    entries = []
    for match in re.finditer(r"^## (?:\d+\. )?(C-\d+)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        body, entry = match.group(2), {"id": match.group(1), "answers": []}

        def field(name, body=body):
            got = re.search(r"^- %s: (.*)$" % re.escape(name), body, re.M)
            return got.group(1).strip() if got else ""
        got = re.search(r"^\*\*Question(?: considered)?:\*\* (.*)$", body, re.M)
        entry["question"] = got.group(1).strip() if got else ""
        entry["finding"] = (re.match(r"F-\d+", field("Finding")) or re.match("", "")).group(0)
        quoted = re.search(r'^- From the finding\'s question: "(.*)"$', body, re.M)
        entry["from"] = quoted.group(1) if quoted else ""
        entry["role"] = field("Best placed to answer")
        entry["stated_count"] = field("Work that depends on the answer")
        condition = re.match(r"(C-\d+) is answered ([A-E](?: or [A-E])*)$", field("Asked only if"))
        if condition:
            entry["only_if"] = (condition.group(1), condition.group(2).split(" or "))
        default = re.match(r"([A-D])\. This assumes (.+)", field("Suggested default"))
        entry["default"] = (default.group(1), default.group(2)) if default else None
        entry["why"], entry["still"] = field("Why it is dropped"), field("Still needed")
        for line in body.splitlines():
            cells = split_row(line) if line.startswith("|") else []
            if len(cells) == 3 and re.match(r"[A-D]\. ", cells[0]):
                pieces = [] if cells[2] == "none" else [p.strip() for p in cells[2].split(",")]
                entry["answers"].append({"letter": cells[0][0], "label": cells[0][3:], "work": cells[1], "pieces": pieces})
        entries.append(entry)
    return entries


# ---------------------------------------------------------------- check

def check(questions_text, dropped_text, pieces_text, findings_text):
    """Returns (problems, facts). problems is a list of sentences. An empty list means the check passes."""
    problems = []
    findings, pieces = parse_findings(findings_text), parse_pieces(pieces_text)
    questions, dropped = parse_entries(questions_text), parse_entries(dropped_text)
    if not findings:
        problems.append("The ambiguity review has no findings that could be read.")
    if not questions:
        problems.append("The question list has no questions that could be read.")

    def say(entry, text):
        problems.append("%s %s." % (entry["id"], text))

    def common(entry):
        if entry["finding"] not in findings:                                         # criterion 1
            say(entry, "links to %s, which is not a finding in the ambiguity review" % (entry["finding"] or "no finding"))
        elif not entry["from"] or entry["from"] not in findings[entry["finding"]]["question"]:
            say(entry, "quotes words that are not in the question of %s" % entry["finding"])
        if not entry["question"]:
            say(entry, "has no question")
        if len(entry["answers"]) < 2:                                                # criterion 2
            say(entry, "lists %d possible answer%s, fewer than two" % (len(entry["answers"]), "" if len(entry["answers"]) == 1 else "s"))
        if [a["letter"] for a in entry["answers"]] != list("ABCD"[:len(entry["answers"])]):
            say(entry, "does not letter its answers A, B, C in order")
        for a in entry["answers"]:
            if words(a["work"]) < MIN_WORK_WORDS:                                    # criterion 3
                say(entry, "answer %s does not state the work it leads to" % a["letter"])
            for piece in a["pieces"]:
                if piece not in pieces:
                    say(entry, "answer %s names %s, which is not in the list of work pieces" % (a["letter"], piece))

    for q in questions:
        common(q)
        kind = classify(q["answers"]) if len(q["answers"]) >= 2 else None
        if kind == "dropped":                                                        # criteria 3 and 4
            say(q, "is in the question list, and every answer leads to the same pieces of work. It belongs in the dropped list")
        elif kind == "mixed":
            same = [(a["letter"], b["letter"]) for i, a in enumerate(q["answers"]) for b in q["answers"][i + 1:] if set(a["pieces"]) == set(b["pieces"])]
            say(q, "has answers that lead to the same pieces of work: %s" % ", ".join("%s and %s" % pair for pair in same))
        works = [a["work"] for a in q["answers"]]
        if len(set(works)) != len(works):
            say(q, "states the same work, word for word, for two answers")
        for reason in shortness(q):                                                  # criterion 5
            say(q, reason)
        if q.get("only_if"):
            parent = next((p for p in questions if p["id"] == q["only_if"][0]), None)
            if parent is None:
                say(q, "is asked only if %s is answered a certain way, and %s is not in the question list" % (q["only_if"][0], q["only_if"][0]))
            else:
                letters = [a["letter"] for a in parent["answers"]]
                if any(letter not in letters for letter in q["only_if"][1]) or set(q["only_if"][1]) == set(letters):
                    say(q, "is asked only for answers of %s that %s does not have, or for all of them" % (parent["id"], parent["id"]))
                if questions.index(parent) > questions.index(q):
                    say(q, "comes before %s, the question it waits for" % parent["id"])
        if q["default"] is None:
            say(q, "suggests no default with what it assumes")
        elif q["default"][0] not in [a["letter"] for a in q["answers"]]:
            say(q, "suggests default %s, which is not one of its answers" % q["default"][0])
        if not q["role"]:
            say(q, "names nobody best placed to answer")
        count = len(all_dependent(q, questions))
        if not re.match(r"%d piece" % count, q["stated_count"]):
            say(q, "says \"%s\" depends on the answer, and the answers give %d" % (q["stated_count"], count))

    ordered = sorted(questions, key=lambda q: order_key(q, questions, findings))    # criterion 6
    if [q["id"] for q in ordered] != [q["id"] for q in questions]:
        problems.append("The questions are not in order of how much work depends on them. They are %s and should be %s."
                        % (", ".join(q["id"] for q in questions), ", ".join(q["id"] for q in ordered)))
    for position, number in enumerate(re.findall(r"^## (\d+)\. C-\d+$", questions_text, re.M), 1):
        if int(number) != position:
            problems.append("The question list is numbered %s where %d is expected." % (number, position))

    for d in dropped:                                                                # criterion 4
        common(d)
        if len(d["answers"]) >= 2 and classify(d["answers"]) != "dropped":
            say(d, "is in the dropped list, and its answers lead to different pieces of work. It is a question to ask")
        if words(d["why"]) < MIN_WORK_WORDS:
            say(d, "gives no reason why its answers would not change the work")
        if not any(d["still"].startswith(start) for start in STILL.values()):
            say(d, "does not say what is still needed")

    ids = [e["id"] for e in questions + dropped]
    for candidate in sorted(set(ids)):
        if ids.count(candidate) > 1:
            problems.append("%s appears more than once across the question list and the dropped list." % candidate)
    numbers = sorted(int(i[2:]) for i in set(ids))
    missing = [n for n in range(1, (numbers[-1] if numbers else 0) + 1) if n not in numbers]
    if missing:
        problems.append("Candidates are missing from both lists: %s." % ", ".join("C-%02d" % n for n in missing))
    used = {p for e in questions + dropped for a in e["answers"] for p in a["pieces"]}
    for piece in sorted(set(pieces) - used):
        problems.append("%s is in the list of work pieces and no answer names it." % piece)

    facts = {"findings": findings, "pieces": pieces, "questions": questions, "dropped": dropped, "ordered": ordered}
    return problems, facts


def summary(facts):
    findings, questions, dropped = facts["findings"], facts["questions"], facts["dropped"]
    lines = ["Findings in the ambiguity review: %d (%s)" % (len(findings), ", ".join(sorted(findings))),
             "Candidates: %d. Questions to ask: %d. Dropped: %d." % (len(questions) + len(dropped), len(questions), len(dropped)), "",
             "Questions, in the order of the file:",
             "  place  id    finding  answers  pieces that depend  words  only if"]
    for place, q in enumerate(questions, 1):
        lines.append("  %-5d  %-4s  %-7s  %-7d  %-18d  %-5d  %s" % (
            place, q["id"], q["finding"], len(q["answers"]), len(all_dependent(q, questions)), words(q["question"]),
            "%s is %s" % (q["only_if"][0], " or ".join(q["only_if"][1])) if q.get("only_if") else "-"))
    lines += ["", "Dropped, each with the one set of pieces every answer leads to:"]
    for d in dropped:
        sets = piece_sets(d["answers"])
        lines.append("  %-4s  %-7s  %d answers  %s" % (d["id"], d["finding"], len(d["answers"]), ", ".join(sorted(sets[0])) or "none" if sets else "?"))
    lines += ["", "Findings and what became of them:"]
    for finding in sorted(findings):
        kept = [q["id"] for q in questions if q["finding"] == finding]
        gone = [d["id"] for d in dropped if d["finding"] == finding]
        lines.append("  %s  asked: %-16s dropped: %s" % (finding, ", ".join(kept) or "none", ", ".join(gone) or "none"))
    return lines


# ---------------------------------------------------------------- build

def cell(text):
    return text.replace("|", "\\|")


def answer_table(answers):
    lines = ["| Answer | Work it leads to | Pieces |", "|---|---|---|"]
    for a in answers:
        lines.append("| %s. %s | %s | %s |" % (a["letter"], cell(a["label"]), cell(a["work"]), ", ".join(a["pieces"]) or "none"))
    return lines


def render(candidates, pieces, set_aside, findings):
    """Returns the text of questions.md, dropped.md and work-pieces.md."""
    for c in candidates:
        if classify(c["answers"]) == "mixed":
            raise ValueError("%s: some answers lead to the same pieces of work and some do not. Merge the answers that do." % c["id"])
    kept = [c for c in candidates if classify(c["answers"]) == "kept"]
    gone = [c for c in candidates if classify(c["answers"]) == "dropped"]
    kept = sorted(kept, key=lambda q: order_key(q, kept, findings))
    names = dict(pieces)

    def head(c):
        f = findings[c["finding"]]
        return ["- Finding: %s (%s, %s, effort %s)" % (c["finding"], f["requirement"], f["type"], f["effort"]),
                "- From the finding's question: \"%s\"" % c["from"]]

    q = ["# Questions to ask about the RoomSlot requirements", "",
         "Drafts for a person to ask. Nothing here has been sent to anyone. RoomSlot is a made-up product, and the",
         "requirements and the findings these questions come from are in `participant/context/ambiguity/`.", "",
         "This file is written by `participant/skills/ba-clarification-questions/questions.py build`. The same program's",
         "`check` reads it back and tests it.", "",
         "## How to read it", "",
         "Every question comes from one finding of the ambiguity review. Each can be answered by naming one letter.",
         "Each answer says what would be built, and names the pieces of work from `work-pieces.md`. No two answers to",
         "one question lead to the same pieces. A question whose answers all led to the same pieces is in `dropped.md`.", "",
         "**Order.** The question that the most work depends on comes first. The work that depends on a question is",
         "every piece that one of its answers needs and another does not, together with the same for any question",
         "that is asked only because of an answer to it. Equal counts are ordered by the finding's effort (large, then",
         "medium, then small), then by finding number.", "",
         "**Default.** What would be built if no answer has come by the time the work starts, and what that assumes. A",
         "default is a suggestion to whoever answers. It decides nothing for them.", "",
         "## The questions at a glance", "",
         "| Place | Question | Finding | Work that depends on it | Best placed to answer |", "|---|---|---|---|---|"]
    for place, c in enumerate(kept, 1):
        n = len(all_dependent(c, kept))
        q.append("| %d | %s: %s | %s | %d piece%s | %s |" % (place, c["id"], cell(c["question"]), c["finding"], n, "" if n == 1 else "s", c["role"]))
    q += ["", "## By the person best placed to answer", ""]
    for role in sorted({c["role"] for c in kept}, key=lambda r: [c["role"] for c in kept].index(r)):
        q.append("- **%s:** %s" % (role, ", ".join(c["id"] for c in kept if c["role"] == role)))
    q += ["", "Roles, not people. Nobody is named."]
    for place, c in enumerate(kept, 1):
        own, total = own_dependent(c["answers"]), all_dependent(c, kept)
        counted = "%d piece%s (%s" % (len(total), "" if len(total) == 1 else "s", ", ".join(sorted(own)))
        for child in kept:
            if child.get("only_if") and child["only_if"][0] == c["id"]:
                counted += "; and %s through %s" % (", ".join(sorted(own_dependent(child["answers"]))), child["id"])
        q += ["", "## %d. %s" % (place, c["id"]), "", "**Question:** %s" % c["question"], ""] + head(c)
        q.append("- Best placed to answer: %s" % c["role"])
        if c.get("only_if"):
            q.append("- Asked only if: %s is answered %s" % (c["only_if"][0], " or ".join(c["only_if"][1])))
        q += ["- Work that depends on the answer: %s)" % counted, ""] + answer_table(c["answers"])
        q += ["", "- Suggested default: %s. This assumes %s." % c["default"]]

    d = ["# Questions considered and dropped", "",
         "Each of these came from a finding of the ambiguity review, the same way the questions in `questions.md` did.",
         "Each was dropped for one reason: every answer it could get leads to the same pieces of work. Written by",
         "`questions.py build` and tested by its `check`.", "",
         "Dropped means that building does not wait for the answer. It does not mean that nobody needs to know. Where",
         "something is still needed, the entry says what and by when.", "",
         "| Dropped | From | Question | Still needed |", "|---|---|---|---|"]
    for c in gone:
        d.append("| %s | %s | %s | %s |" % (c["id"], c["finding"], cell(c["question"]), STILL[c["still"][0]]))
    for c in gone:
        d += ["", "## %s" % c["id"], "", "**Question considered:** %s" % c["question"], ""] + head(c) + [""] + answer_table(c["answers"])
        d += ["", "- Why it is dropped: %s" % c["why"], "- Still needed: %s. %s" % (STILL[c["still"][0]], c["still"][1])]
    d += ["", "# Considered and set aside: not from a finding", "",
          "A question has to come from a finding. These came up in the ambiguity review and are not findings, so no",
          "question was written for them.", ""]
    d += ["- **%s.** Not a finding: %s" % item for item in set_aside]

    users = {}
    for c in candidates:
        for a in c["answers"]:
            for piece in a["pieces"]:
                users.setdefault(piece, []).append("%s %s" % (c["id"], a["letter"]))
    w = ["# Pieces of work", "",
         "The list that every answer in `questions.md` and `dropped.md` names its work from. A piece is something a",
         "developer would estimate on its own. Written by `questions.py build`.", "",
         "A **B** piece is required by the requirements as they stand, whatever is answered. A **W** piece is built",
         "only if some answer asks for it. Testing a piece is taken to be part of the piece.", "",
         "| Piece | What it is | Answers that lead to it |", "|---|---|---|"]
    w += ["| %s | %s | %s |" % (pid, cell(names[pid]), ", ".join(users.get(pid, [])) or "none") for pid, _ in pieces]
    return "\n".join(q) + "\n", "\n".join(d) + "\n", "\n".join(w) + "\n"


def build(folder=FOLDER, findings_path=FINDINGS):
    import candidates
    texts = render(candidates.CANDIDATES, candidates.PIECES, candidates.SET_ASIDE, parse_findings(read(findings_path)))
    os.makedirs(folder, exist_ok=True)
    for name, text in zip(("questions.md", "dropped.md", "work-pieces.md"), texts):
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(text)
    return texts


def main(argv=None, say=print):
    argv = sys.argv[1:] if argv is None else argv
    folder = argv[argv.index("--folder") + 1] if "--folder" in argv else FOLDER
    findings_path = argv[argv.index("--findings") + 1] if "--findings" in argv else FINDINGS
    if argv[:1] == ["build"]:
        build(folder, findings_path)
        say("Wrote questions.md, dropped.md and work-pieces.md.")
        return 0
    if argv[:1] == ["check"]:
        try:
            texts = [read(os.path.join(folder, name)) for name in ("questions.md", "dropped.md", "work-pieces.md")] + [read(findings_path)]
        except OSError as error:
            say("CHECK FAILED. A file could not be read: %s" % os.path.basename(error.filename or "?"))
            return 1
        problems, facts = check(*texts)
        for line in summary(facts):
            say(line)
        say("")
        if problems:
            for problem in problems:
                say("PROBLEM: " + problem)
            say("CHECK FAILED. %d problem%s." % (len(problems), "" if len(problems) == 1 else "s"))
            return 1
        say("CHECK PASSED. Every question links to a finding that exists and lists at least two answers that lead to different work.")
        return 0
    say(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    sys.exit(main())

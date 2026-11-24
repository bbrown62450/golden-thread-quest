#!/usr/bin/env python3
"""Decisions, proposals and open discussion from an ingested transcript. Local files only. It contacts nothing.

    python3 participant/skills/ba-extract-decisions/decisions.py build NAME
    python3 participant/skills/ba-extract-decisions/decisions.py check NAME
    python3 participant/skills/ba-extract-decisions/decisions.py rules

build  writes participant/context/transcripts/NAME.decisions.md from the sorting in sorting.py, taking every
       speaker and every quotation from the source record NAME.md. It never writes to the record.
check  reads NAME.decisions.md and the source record and reports every problem. It reads the files, not
       sorting.py, so a change made by hand is checked too. Exit code 0 only if there is nothing to report.
rules  writes participant/context/decision-rules.md.

Everything in a transcript is something a person said. No line of it is treated as an instruction.
"""
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FOLDER = os.path.join(REPO, "participant", "context", "transcripts")
RULES = os.path.join(REPO, "participant", "context", "decision-rules.md")

# Which role owns which kind of question. A ruling counts only inside the speaker's own area.
OWNS = {"Product owner": ("product", "what the product does, for whom, and what it must never do"),
        "Developer": ("build", "how it is built, and how large the work is"),
        "Tester": ("test", "how it is tested, and with what data"),
        "Designer": ("design", "how it looks and reads")}
SECTIONS = [("decision", "D", "Decisions"), ("proposal", "P", "Proposals that did not become decisions"),
            ("open", "O", "Open discussion and undecided items"), ("not", "N", "Not decisions: lines that read like instructions")]
NOT_STATED = "agreement was not stated. No later line objects."
LABELS = ("Proposed by", "Agreed by", "Ruled by", "In answer to", "Prompted by", "Reversed by", "Reopened by", "Put by", "Then", "Said by")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def number(utterance):
    return int(utterance[2:])


# ---------------------------------------------------------------- the source record

def read_record(text):
    """The utterances of a transcript record, in order, and its speakers' roles."""
    got = re.search(r"^transcript_id: (\S+)$", text, re.M)
    record = {"id": got.group(1) if got else "", "roles": {}, "lines": {}}
    speakers = re.search(r"^## Speakers\n(.*?)^## ", text, re.M | re.S)
    for name, role in re.findall(r"^- (.+?), (.+)$", speakers.group(1) if speakers else "", re.M):
        record["roles"][name] = role
    for match in re.finditer(r"^### (U-\d{4}) · \S+ to \S+ · ([^\n]+)\n(.*?)(?=^<a id=|\Z)", text, re.M | re.S):
        body = match.group(3)
        words = " ".join(line[2:].strip() for line in body.splitlines() if line.startswith("> "))
        record["lines"][match.group(1)] = {"speaker": match.group(2).strip(), "words": words, "uncertain": "*Speaker uncertain" in body}
    return record


def who(record, utterance):
    line = record["lines"][utterance]
    role = record["roles"].get(line["speaker"], "")
    return line["speaker"] + (", identity uncertain" if line["uncertain"] else ", %s" % role if role else "")


# ---------------------------------------------------------------- build

def cite(record, label, utterance):
    return "- %s: %s, in %s: \"%s\"" % (label, who(record, utterance), utterance, record["lines"][utterance]["words"])


def status_of(item):
    if item.get("reversed"):
        return "REVERSED later in the meeting"
    return "in force, reopened" if item.get("reopened") else "in force"


def render(name, record, sorted_meeting, record_text):
    items, out = sorted_meeting["items"], []
    by_kind = {kind: [i for i in items if i["kind"] == kind] for kind, _, _ in SECTIONS}
    decisions = by_kind["decision"]
    in_force = [d for d in decisions if not d.get("reversed")]
    out += ["# Decisions: %s" % name, "",
            "Derived from the transcript record `%s.md`. This file is an interpretation. The record is what was said, and it" % name,
            "was not changed to make this file.", "",
            "- source_record: `%s.md`" % name, "- transcript_id: `%s`" % record["id"],
            "- source_sha256: `%s`" % sha(record_text), "",
            "Written by `participant/skills/ba-extract-decisions/decisions.py build`. The sorting was done by an AI assistant",
            "(Claude) under the rules in `participant/context/decision-rules.md`. Every speaker and every quotation below is",
            "copied from the record by the program. The meeting is made up.", "",
            "**How to check an item.** Each line cited is `U-` and four digits. Open `%s.md` and find the heading with that" % name,
            "number. The words quoted here are the words under it. In full, a line is cited as `%s#U-0001`." % record["id"], "",
            "## Counts", "",
            "| Kind | Count |", "|---|---|",
            "| Decisions in force | %d |" % len(in_force),
            "| Decisions reversed later in the meeting | %d |" % (len(decisions) - len(in_force)),
            "| Proposals that did not become decisions | %d |" % len(by_kind["proposal"]),
            "| Open or undecided items | %d |" % len(by_kind["open"]),
            "| Lines that read like instructions, not decisions | %d |" % len(by_kind["not"]),
            "", "Decisions in force that a second person agreed to: %d. Ruled by the person whose role owns the question: %d." % (
                sum(1 for d in in_force if d["basis"] == "agreed"), sum(1 for d in in_force if d["basis"] == "ruled")),
            "Decisions in force that a later line reopened: %d." % sum(1 for d in in_force if d.get("reopened"))]
    for kind, letter, title in SECTIONS:
        out += ["", "## %s" % title, ""]
        if not by_kind[kind]:
            out += ["None."]
        for item in by_kind[kind]:
            if kind == "decision":
                out += ["### %s · %s · %s" % (item["id"], item["basis"], status_of(item)), "", "**Decision:** %s" % item["text"], ""]
                if item["basis"] == "agreed":
                    out += [cite(record, "Proposed by", u) for u in item["proposed"]] + [cite(record, "Agreed by", u) for u in item["accepted"]]
                else:
                    out += ["- Area: %s" % item["area"]] + [cite(record, "In answer to", u) for u in item.get("asked", [])]
                    out += [cite(record, "Ruled by", u) for u in item["ruled"]] + ["- Agreed by: %s" % NOT_STATED]
                if item.get("reversed"):
                    out += [cite(record, "Prompted by", u) for u in item["reversed"].get("prompted", [])]
                    out += [cite(record, "Reversed by", u) for u in item["reversed"]["by"]] + ["- Replaced by: %s" % item["reversed"]["replaced_by"]]
                out += [cite(record, "Reopened by", u) for u in item.get("reopened", [])]
            elif kind == "proposal":
                out += ["### %s · proposal, not a decision" % item["id"], "", "**Proposed:** %s" % item["text"], ""]
                out += [cite(record, "Put by" if u in item["put"] else "Then", u) for u in sorted(item["put"] + item["after"])]
                out += ["- Why it is not a decision: %s" % item["why"]]
            elif kind == "open":
                out += ["### %s · open" % item["id"], "", "**Undecided:** %s" % item["text"], ""]
                out += [cite(record, "Said by", u) for u in item["lines"]] + ["- Where it was left: %s" % item["left"]]
            else:
                out += ["### %s · not a decision" % item["id"], "", "**What it is:** %s" % item["text"], ""]
                out += [cite(record, "Said by", u) for u in item["lines"]] + ["- Why it is not a decision: %s" % item["why"]]
            if item.get("note"):
                out += ["- Note: %s" % item["note"]]
            out += [""]
        out.pop() if out[-1] == "" else None
    out += ["", "## Lines not sorted", "",
            "Every line of the record is either cited above or listed here with the reason, so that nothing was passed over", "unseen.", ""]
    out += ["- %s · %s: %s." % (u, record["lines"][u]["speaker"], why) for u, why in sorted(sorted_meeting["unsorted"].items())] or ["None."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- check

def parse(text):
    """The items of a decisions file, as written."""
    items, section = [], None
    titles = {title: kind for kind, _, title in SECTIONS}
    chunks = re.split(r"^(## .+|### .+)$", text, flags=re.M)
    for heading, body in zip(chunks[1::2], chunks[2::2]):
        if heading.startswith("## "):
            section = titles.get(heading[3:].strip(), heading[3:].strip())
            if section == "Lines not sorted":
                items.append({"id": "unsorted", "section": section, "head": heading, "cites": [],
                              "listed": re.findall(r"^- (U-\d{4}) · (.+?): (.+)$", body, re.M)})
            continue
        parts = [p.strip() for p in heading[4:].split(" · ")]
        item = {"id": parts[0], "head": heading, "tags": parts[1:], "section": section, "cites": [], "body": body}
        for label, speaker, utterance, words in re.findall(r"^- (%s): (.+?), in (U-\d+): \"(.*)\"$" % "|".join(LABELS), body, re.M):
            item["cites"].append({"label": label, "speaker": speaker, "u": utterance, "words": words})
        item["not_stated"] = ("- Agreed by: %s" % NOT_STATED) in body
        got = re.search(r"^- Area: (.+)$", body, re.M)
        item["area"] = got.group(1).strip() if got else ""
        got = re.search(r"^- Replaced by: (\S+)$", body, re.M)
        item["replaced_by"] = got.group(1) if got else ""
        item["why"] = bool(re.search(r"^- (Why it is not a decision|Where it was left): \S", body, re.M))
        items.append(item)
    return items


def check(decisions_text, record_text, provenance_text, same_file=False):
    """Returns (problems, facts). An empty list of problems means the check passes."""
    problems, record = [], read_record(record_text)
    lines, items = record["lines"], parse(decisions_text)
    entries = [i for i in items if i["id"] != "unsorted"]

    def say(text):
        problems.append(text)

    # Criterion 5: separate from the source, which is not edited.
    if same_file:
        say("The decisions file and the source record are the same file.")
    if not lines:
        say("The source record has no utterances that could be read.")
    recorded = re.search(r"^record_sha256: (\S+)$", provenance_text, re.M)
    if not recorded:
        say("The provenance file does not give the record's SHA-256, so it cannot be shown that the record is as it was ingested.")
    elif recorded.group(1) != sha(record_text):
        say("The source record has been changed since it was ingested: its SHA-256 is not the one in its provenance file.")
    stated = re.search(r"^- source_sha256: `(\S+)`$", decisions_text, re.M)
    if not stated or stated.group(1) != sha(record_text):
        say("The decisions file was not made from the source record as it is now: the SHA-256 it states is not the record's.")
    stated_id = re.search(r"^- transcript_id: `(\S+)`$", decisions_text, re.M)
    if not stated_id or stated_id.group(1) != record["id"]:
        say("The decisions file does not name the source record's transcript ID, %s." % record["id"])
    if re.search(r"^### U-\d{4} · ", decisions_text, re.M) or re.search(r"^<a id=\"U-", decisions_text, re.M):
        say("The decisions file holds utterance headings, as if the record had been copied into it.")
    if re.search(r"^### [DPON]-\d+", record_text, re.M) or "**Decision:**" in record_text:
        say("The source record holds decision items. Analysis does not belong in the record.")

    # Criterion 6: every identifier cited anywhere in the file exists in the record.
    for utterance in sorted(set(re.findall(r"\bU-\d+\b", decisions_text)) - {"U-0001"} | {c["u"] for i in entries for c in i["cites"]}):
        if utterance not in lines:
            where = [i["id"] for i in entries if any(c["u"] == utterance for c in i["cites"])] or ["the file"]
            say("%s is cited by %s and is not in the source record." % (utterance, ", ".join(where)))
    for other in sorted(set(re.findall(r"\b(tr-[\w-]+)#U-\d+", decisions_text)) - {record["id"]}):
        say("A line is cited from %s, which is not this record." % other)
    for item in entries:
        for c in item["cites"]:
            if c["u"] not in lines:
                continue
            if c["speaker"] != who(record, c["u"]):
                say("%s gives %s to \"%s\". The record gives it to \"%s\"." % (item["id"], c["u"], c["speaker"], who(record, c["u"])))
            if c["words"] != lines[c["u"]]["words"]:
                say("%s quotes %s in words that are not the record's." % (item["id"], c["u"]))

    def speakers(item, label):
        return [lines[c["u"]]["speaker"] for c in item["cites"] if c["label"] == label and c["u"] in lines]

    def numbers(item, *labels):
        return [number(c["u"]) for c in item["cites"] if c["label"] in labels and c["u"] in lines]

    prefix = {kind: letter for kind, letter, _ in SECTIONS}
    ids = [i["id"] for i in entries]
    for item in entries:
        kind = item["section"]
        if kind not in prefix or not re.fullmatch(r"%s-\d+" % prefix.get(kind, "X"), item["id"]):
            say("%s is under \"%s\", where it does not belong." % (item["id"], kind))
            continue
        if ids.count(item["id"]) > 1:
            say("%s appears more than once." % item["id"])
        if not item["cites"]:
            say("%s cites no line of the source record." % item["id"])       # criterion 1 for decisions, and the same for the rest
        if kind != "decision":
            if any(c["label"] in ("Agreed by", "Ruled by") for c in item["cites"]):
                say("%s is not a decision and has an \"Agreed by\" or \"Ruled by\" line." % item["id"])
            if not item["why"]:
                say("%s does not say why it is not a decision, or where it was left." % item["id"])
            continue
        basis = item["tags"][0] if item["tags"] else ""
        if basis == "agreed":                                                # criteria 2 and 3
            proposers, agreers = speakers(item, "Proposed by"), speakers(item, "Agreed by")
            if not proposers:
                say("%s is an agreed decision and cites no line that proposed it." % item["id"])
            if not agreers:
                say("%s is listed as a decision, and no line is cited in which anyone accepted it. It is a proposal." % item["id"])
            for name in sorted(set(agreers) & set(proposers)):
                say("%s is \"agreed\" only by %s, who proposed it. A proposer's own agreement is not acceptance." % (item["id"], name))
            for c in item["cites"]:
                if c["label"] == "Agreed by" and c["u"] in lines and lines[c["u"]]["uncertain"]:
                    say("%s is \"agreed\" in %s by a speaker whose identity is uncertain. Nobody can be named as having agreed." % (item["id"], c["u"]))
            if proposers and agreers and min(numbers(item, "Agreed by")) < min(numbers(item, "Proposed by")):
                say("%s is \"agreed\" in a line that comes before the line that proposed it." % item["id"])
            if item["not_stated"]:
                say("%s names who agreed and also says agreement was not stated." % item["id"])
        elif basis == "ruled":
            rulers = [c for c in item["cites"] if c["label"] == "Ruled by" and c["u"] in lines]
            if not rulers:
                say("%s is a ruled decision and cites no line in which it was ruled." % item["id"])
            for c in rulers:
                role = record["roles"].get(lines[c["u"]]["speaker"], "")
                if lines[c["u"]]["uncertain"] or role not in OWNS:
                    say("%s is \"ruled\" in %s by a speaker with no role that owns any kind of question." % (item["id"], c["u"]))
                elif OWNS[role][0] != item["area"]:
                    say("%s is \"ruled\" by a %s on a question of %s, which that role does not own. It is a proposal." % (item["id"], role, item["area"] or "no stated area"))
            if not item["not_stated"]:
                say("%s is a ruled decision and does not state that agreement was not stated." % item["id"])
            if speakers(item, "Agreed by"):
                say("%s is \"ruled\" and also names somebody as agreeing. It is one or the other." % item["id"])
        else:
            say("%s does not say whether it was agreed or ruled." % item["id"])
        status = item["tags"][1] if len(item["tags"]) > 1 else ""
        reversing, settled = numbers(item, "Reversed by"), numbers(item, "Agreed by", "Ruled by")
        if status.startswith("REVERSED"):
            if not reversing:
                say("%s is marked reversed and cites no line that reversed it." % item["id"])
            elif settled and min(reversing) <= max(settled):
                say("%s is \"reversed\" by a line that comes before the decision was made." % item["id"])
            target = next((i for i in entries if i["id"] == item["replaced_by"]), None)
            if target is None or target["section"] != "decision" or (len(target["tags"]) > 1 and target["tags"][1].startswith("REVERSED")):
                say("%s is marked reversed and does not name a decision in force that replaced it." % item["id"])
        elif reversing:
            say("%s cites a line that reversed it and is not marked reversed." % item["id"])
        if ("reopened" in status) != bool(numbers(item, "Reopened by")):
            say("%s is marked reopened without a line that reopened it, or the other way round." % item["id"])
        if status not in ("in force", "in force, reopened", "REVERSED later in the meeting"):
            say("%s does not say whether it is in force." % item["id"])

    # A line that reads like an instruction is never the ground for a decision or a proposal.
    instruction = {c["u"] for i in entries if i["section"] == "not" for c in i["cites"]}
    for item in entries:
        if item["section"] in ("decision", "proposal"):
            for u in sorted(instruction & {c["u"] for c in item["cites"]}):
                say("%s rests on %s, which is listed as a line that reads like an instruction." % (item["id"], u))

    # Every line of the record is cited or listed as not sorted, and never both.
    cited = {c["u"] for i in entries for c in i["cites"]}
    unsorted = next((i for i in items if i["id"] == "unsorted"), None)
    listed = [u for u, _, _ in unsorted["listed"]] if unsorted else []
    if unsorted is None:
        say("The decisions file has no list of the lines that were not sorted.")
    for u in sorted(set(lines) - cited - set(listed)):
        say("%s is in the source record, and the decisions file neither cites it nor lists it as not sorted." % u)
    for u in sorted(set(listed) & cited):
        say("%s is cited by an item and also listed as not sorted." % u)
    for u, speaker, _ in (unsorted["listed"] if unsorted else []):
        if u in lines and speaker != lines[u]["speaker"]:
            say("%s is listed as not sorted under \"%s\". The record gives it to \"%s\"." % (u, speaker, lines[u]["speaker"]))

    # The counts in the file are the counts of the items in it.
    decisions = [i for i in entries if i["section"] == "decision"]
    reversed_ = [d for d in decisions if len(d["tags"]) > 1 and d["tags"][1].startswith("REVERSED")]
    counts = {"Decisions in force": len(decisions) - len(reversed_), "Decisions reversed later in the meeting": len(reversed_),
              "Proposals that did not become decisions": sum(1 for i in entries if i["section"] == "proposal"),
              "Open or undecided items": sum(1 for i in entries if i["section"] == "open"),
              "Lines that read like instructions, not decisions": sum(1 for i in entries if i["section"] == "not")}
    for label, count in counts.items():
        if "| %s | %d |" % (label, count) not in decisions_text:
            say("The count of \"%s\" in the file is not %d, the number of such items in it." % (label, count))
    return problems, {"record": record, "items": entries, "counts": counts, "cited": cited, "listed": listed, "decisions": decisions}


def summary(name, facts):
    record, out = facts["record"], ["Source record: %s.md, transcript %s, %d utterances." % (name, facts["record"]["id"], len(facts["record"]["lines"]))]
    out += ["  %-52s %d" % (label, count) for label, count in facts["counts"].items()]
    out += ["Utterances cited by an item: %d. Listed as not sorted: %d. Neither: %d." % (
        len(facts["cited"] & set(record["lines"])), len(facts["listed"]), len(set(record["lines"]) - facts["cited"] - set(facts["listed"]))), "",
        "Each decision, the lines it cites, and who agreed:"]
    for d in facts["decisions"]:
        agreed = sorted({record["lines"][c["u"]]["speaker"] for c in d["cites"] if c["label"] == "Agreed by" and c["u"] in record["lines"]})
        out.append("  %s  %-6s  %-30s  cites %-30s  agreed by: %s" % (
            d["id"], d["tags"][0] if d["tags"] else "?", d["tags"][1] if len(d["tags"]) > 1 else "?",
            ", ".join(c["u"] for c in d["cites"]), ", ".join(agreed) or "not stated"))
    return out


# ---------------------------------------------------------------- rules

def rules_text():
    import sorting
    out = ["# Decision rules: when something said in a meeting is a decision", "",
           "Written by `participant/skills/ba-extract-decisions/decisions.py rules`, at the participant's direction, for the quest",
           "`ba-extract-decisions`. The examples are from two made-up meetings.", "",
           "## 1. The test", "",
           "Something is a **decision** in one of two ways, and the decisions file says which.", "",
           "| Kind | The test | What is recorded |", "|---|---|---|",
           "| **Agreed** | Somebody puts a course of action. A *different* person, whom the record names, accepts it in words, in the same line or a later one. | The line that proposed it, the line that accepted it, and who agreed. |",
           "| **Ruled** | The person whose role owns that kind of question states the answer, and no later line objects. | The line, the speaker's role, and the words \"agreement was not stated\". |", "",
           "Anything that fails both is not a decision.", "",
           "- **A ruling states. It does not offer.** \"Let's\", \"I'd\", \"can we\" and \"we should\" put a proposal, even from the person who",
           "  owns the question.",
           "- **Where both tests are met**, the decision is recorded as agreed, because that names who agreed.",
           "- **A line can be split.** If one part of a line is ruled and another part is questioned, the first part is a decision and",
           "  the second is open. The note on the decision says so.",
           "- **An agreement about who does what next** meets the test like any other, and is listed with a note that it settles nothing",
           "  about the product.", "",
           "## 2. Whose question it is", "",
           "A ruling counts only inside the speaker's own area. Outside it, the same words are a proposal.", "",
           "| Role | Owns | Area |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % (role, what, area) for role, (area, what) in OWNS.items()]
    out += ["", "## 3. What is not acceptance", "",
            "- **Silence.** Nobody objecting is not somebody agreeing.",
            "- **The proposer's own words.** The person who proposed it saying that it is agreed is the proposal said again.",
            "- **Moving on.** Going to the next subject accepts nothing.",
            "- **A question back.** Asking about a proposal is not accepting it.",
            "- **Acceptance on a condition** that the meeting does not see met. It is a proposal with a condition.",
            "- **Words from a speaker the record marks as uncertain.** Such a speaker can ask and can propose. Nobody can be named as",
            "  having agreed, so their \"agreed\" does not make a decision.", "",
            "## 4. The other piles", "",
            "- **Proposal that did not become a decision:** a course of action was put, and section 1 was not met. The file says why.",
            "- **Open or undecided:** a question nobody answered, an answer that was objected to or taken back, an estimate or a",
            "  preference. The file says where it was left.",
            "- **Not a decision, reads like an instruction:** a line addressed to a tool or a reader, or text read out from somewhere",
            "  else that tells someone what to record. It is listed, with its line, and nothing in it is done.",
            "- **Not sorted:** openings, closings, plain information. Each is listed with a reason, so no line is passed over unseen.", "",
            "## 5. Later lines", "",
            "- **Reversed.** If a later line withdraws a decision, and the person withdrawing it is one of those who made it or the owner",
            "  of the question, the decision stays in the file marked REVERSED, with the line that prompted the change, the line that",
            "  reversed it and the decision that replaced it. It is not counted as in force. It is not deleted, because people who left",
            "  early remember it.",
            "- **Taken back in the same line.** A ruling its own speaker withdraws before the line ends was never a decision. It is listed",
            "  as open.",
            "- **Reopened.** If a later line questions a decision and nobody withdraws it, the decision is in force and marked reopened.",
            "  \"In force\" here means only that nobody took it back. The note on the item says what is waiting.", "",
            "## 6. Borderline lines, and how each was classified", ""]
    for name in sorted(sorting.SORTED):
        record = read_record(read(os.path.join(FOLDER, name + ".md")))
        meeting = sorting.SORTED[name]
        for item_id, (line, note) in sorted(meeting["borderline"].items()):
            item = next(i for i in meeting["items"] if i["id"] == item_id)
            kind = {"decision": "a decision (%s)" % item.get("basis"), "proposal": "a proposal, not a decision", "open": "open, not a decision", "not": "not a decision"}[item["kind"]]
            out += ["**`%s#%s`**, %s:" % (record["id"], line, who(record, line)), "",
                    "> %s" % record["lines"][line]["words"], "",
                    "Classified as **%s**, item %s of `%s.decisions.md`. %s" % (kind, item_id, name, note), ""]
    out += ["## 7. What these rules leave to judgment", "",
            "- Whether words are acceptance at all. \"That's fine\" and \"Sure, I guess\" were both taken as yes.",
            "- Whether an objection from the owner of a question is itself a ruling. Here it was taken as an objection only.",
            "- Which area a question belongs to, where it touches two.",
            "- Whether a later line objects, or only asks.",
            "- What counts as \"a course of action\" and what is only information.",
            "- A ruling needs nobody else's word. A role's holder can therefore make a decision alone, and these rules record that",
            "  it happened, not that the others would have agreed."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- command

def paths(name, folder):
    return [os.path.join(folder, name + ext) for ext in (".md", ".provenance.yaml", ".decisions.md")]


def main(argv=None, say=print):
    argv = sys.argv[1:] if argv is None else argv
    folder = argv[argv.index("--folder") + 1] if "--folder" in argv else FOLDER
    if argv[:1] == ["rules"]:
        with open(RULES, "w", encoding="utf-8") as f:
            f.write(rules_text())
        say("Wrote decision-rules.md.")
        return 0
    if len(argv) < 2 or argv[0] not in ("build", "check") or not re.fullmatch(r"[a-z0-9-]+", argv[1]):
        say(__doc__.strip())
        return 2
    name = argv[1]
    record_path, provenance_path, out_path = paths(name, folder)
    try:
        record_text, provenance_text = read(record_path), read(provenance_path)
    except OSError:
        say("NOT DONE. The source record %s.md or its provenance file could not be read." % name)
        return 2
    if argv[0] == "build":
        import sorting
        if name not in sorting.SORTED:
            say("NOT DONE. sorting.py holds no sorting for %s." % name)
            return 2
        before = sha(record_text)
        text = render(name, read_record(record_text), sorting.SORTED[name], record_text)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        say("Wrote %s.decisions.md. The source record was %s." % (name, "not changed" if sha(read(record_path)) == before else "CHANGED"))
        return 0
    try:
        decisions_text = read(out_path)
    except OSError:
        say("CHECK FAILED. %s.decisions.md could not be read." % name)
        return 1
    problems, facts = check(decisions_text, record_text, provenance_text, os.path.realpath(out_path) == os.path.realpath(record_path))
    for line in summary(name, facts):
        say(line)
    say("")
    if problems:
        for problem in problems:
            say("PROBLEM: " + problem)
        say("CHECK FAILED. %d problem%s." % (len(problems), "" if len(problems) == 1 else "s"))
        return 1
    say("CHECK PASSED. Every cited utterance identifier exists in the source record, and the decisions file is separate from it.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    sys.exit(main())

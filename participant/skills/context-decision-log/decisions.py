#!/usr/bin/env python3
"""Keeps a decision log honest: every entry is a decision, a proposal or a question, and says which.

    decisions.py check [--log FILE]     check the log against the rules. Changes nothing
    decisions.py view  [--log FILE]     rewrite the generated part at the top of the log: what is decided now, and what is not
    decisions.py seal  [--log FILE]     record the checksum of each entry not yet recorded, so that a later edit is noticed
    decisions.py rules --out FILE       write the rules document from the tables in this file

The log is a Markdown file a person writes. It only ever grows: an entry is never edited after it is sealed. A change of
state is a NEW entry that points back at the old one with `promotes`, `rejects`, `supersedes` or `answers`. Whether an old
entry still stands is worked out from what points at it, and is never written into it.

This skill decides nothing and approves nothing. It reads what a person wrote and reports where it breaks the rules. It
never adds an entry, and it never reads the text of an entry for instructions. It contacts nothing.

Exit codes: 0 the log keeps every rule. 1 the command could not run. 2 the log breaks a rule.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_LOG = os.path.join(REPO, "participant", "context", "decisions", "log.md")
BEGIN, END = "<!-- generated:begin. Written by decisions.py view. Do not edit between these lines. -->", "<!-- generated:end -->"

STATUSES = ("decision", "proposal", "question")
OPENING = {"decision": "**Decision.**", "proposal": "**Proposal, not decided.**", "question": "**Question, not answered.**"}

# Who may approve what. The rules document is written from this.
KINDS = {
    "product": ("product owner", "What is built, for whom, and when it is delivered."),
    "technical": ("tech lead", "How it is built: the design, the tools, where it runs."),
    "security": ("security lead", "What data is kept, for how long, and who may see it."),
}
# Words that are an act of approval, and words that are only agreement. An approval must hold one of the first.
APPROVAL_WORDS = ("approved", "i approve", "we approve", "i sign this off", "signed off", "go ahead with", "not approved", "declined", "i decline")
AGREEMENT_ONLY = ("sounds good", "makes sense", "no objection", "no objections", "fine by me", "fine with me", "looks good", "ok", "okay", "agreed", "i agree", "nobody disagreed", "+1")
# Wording that presents a thing as settled. It may not appear in the title or the statement of a proposal or a question.
DECIDED_WORDING = (r"\bdecided\b", r"\bapproved\b", r"\bsigned off\b", r"\bfinal(?:ised|ized)?\b", r"\bwe will\b", r"\bit was agreed\b", r"\bhas been agreed\b", r"\bis agreed\b",
                   r"\bthe decision\b", r"\bsettled\b", r"\bconfirmed\b")

FIELDS = {
    # name: (which statuses may have it, required for which, meaning)
    "status": (STATUSES, STATUSES, "decision, proposal or question. Exactly one, and the same word as in the entry's heading."),
    "date": (STATUSES, STATUSES, "The day the entry was written, YYYY-MM-DD."),
    "title": (STATUSES, STATUSES, "One line. A question's title ends with a question mark."),
    "source": (STATUSES, STATUSES, "Where the entry comes from: a document, ticket or meeting record, with its reference."),
    "raised_by": (STATUSES, ("proposal", "question"), "The role of whoever proposed or asked. A role, not a person's name."),
    "kind": (("decision", "proposal"), ("decision",), "product, technical or security. It settles who may approve."),
    "approver": (("decision",), ("decision",), "The role that approved. It must be the role the rules allow for this kind."),
    "approved_in": (("decision",), ("decision",), "Where the approval is recorded, with its reference."),
    "approval_words": (("decision",), ("decision",), "The approver's own words of approval, quoted from that place."),
    "support": (("proposal", "question"), (), "Agreement that is not approval: who agreed, how, and where. Recorded so that it is not lost, and not mistaken."),
    "treated_as_decided_in": (("proposal",), (), "A place that wrongly presents this proposal as decided."),
    "built_on_it": (("proposal",), (), "Work items that were started on this proposal as if it were decided."),
    "affects": (STATUSES, (), "The work items the entry affects."),
    "promotes": (("decision",), (), "The proposal this decision approves."),
    "rejects": (("decision",), (), "The proposal this decision declines."),
    "supersedes": (("decision",), (), "The earlier decision this one replaces."),
    "answers": (("decision", "proposal"), (), "The question this entry answers. A proposal only offers an answer: the question stays open."),
}
REFERENCES = ("promotes", "rejects", "supersedes", "answers")
LISTS = ("affects", "built_on_it")
REFERENCE_SHAPE = re.compile(r"\b[A-Z]{2,5}-\d[\d-]*\b")


class Stop(Exception):
    pass


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as error:
        raise Stop("%s could not be read: %s" % (os.path.basename(path), error.strerror))


def ledger_path(log):
    return os.path.join(os.path.dirname(os.path.abspath(log)), "ledger.json")


def parse(text):
    """The log's entries, in the order they are written. Each: id, heading_status, fields, statement, text, problems."""
    entries = []
    pieces = re.split(r"^(?=### )", text, flags=re.M)
    for piece in pieces[1:]:
        heading = re.match(r"### (E-\d{3}) · (\S+)[ \t]*\n", piece)
        entry = {"id": heading.group(1) if heading else piece.split("\n")[0], "heading_status": heading.group(2) if heading else None, "fields": {}, "repeated": [], "unknown": [],
                 "statement": "", "text": piece.rstrip() + "\n", "malformed": not heading}
        lines = piece.split("\n")[1:]
        at = 0
        while at < len(lines) and not lines[at].strip():
            at += 1
        while at < len(lines) and lines[at].startswith("- "):
            name, found, value = lines[at][2:].partition(": ")
            if not found:
                entry["unknown"].append(lines[at])
            elif name in entry["fields"]:
                entry["repeated"].append(name)
            else:
                entry["fields"][name] = value.strip()
            at += 1
        entry["statement"] = "\n".join(lines[at:]).strip()
        entries.append(entry)
    return entries


def ids_in(value):
    return [one.strip() for one in value.split(",") if one.strip()]


def unquoted(text):
    """Text without what is inside double quotes. A proposal may quote someone else's wrong wording in order to report it."""
    return re.sub(r'"[^"\n]*"', '""', text)


def states(entries):
    """What became of each entry, worked out from the entries that point at it. id -> (state, by)."""
    by_id = {entry["id"]: entry for entry in entries}
    found = {}
    for entry in entries:
        status = entry["fields"].get("status")
        found[entry["id"]] = ({"decision": "current", "proposal": "open", "question": "open"}.get(status, "unknown"), None)
    for entry in entries:
        for name, new_state in (("promotes", "approved"), ("rejects", "declined"), ("supersedes", "superseded"), ("answers", "answered")):
            target = entry["fields"].get(name)
            if target not in by_id or target == entry["id"]:
                continue
            if name == "answers" and entry["fields"].get("status") != "decision":
                if found[target][0] == "open":
                    found[target] = ("open, with a proposed answer", entry["id"])
                continue
            found[target] = (new_state, entry["id"])
    return found


def check(text, ledger=None):
    """Every way the log breaks the rules, as (entry id or 'log', what is wrong). An empty list means it keeps them all."""
    wrong = []
    entries = parse(text)
    if not entries:
        return [("log", "the log has no entries")], entries
    by_id = {}
    earlier_date = None
    for number, entry in enumerate(entries, 1):
        here = entry["id"]
        say = lambda message, here=here: wrong.append((here, message))
        if entry["malformed"]:
            say("the heading is not of the form \"### E-000 · status\"")
            continue
        fields = entry["fields"]
        if here in by_id:
            say("this id is used by an earlier entry too")
        if here != "E-%03d" % number:
            say("entries are numbered in order with no gaps, and this one should be E-%03d" % number)
        by_id.setdefault(here, entry)
        for name in entry["repeated"]:
            say("the field %s is given more than once" % name)
        for line in entry["unknown"]:
            say("this line among the fields is not \"- name: value\": %s" % line[:60])
        for name in fields:
            if name not in FIELDS:
                say("the field %s is not one the rules define" % name)
        status = fields.get("status")
        if status not in STATUSES:
            say("the status is %s, and it must be exactly one of decision, proposal, question" % json.dumps(status))
            continue
        if entry["heading_status"] != status:
            say("the heading says %s and the status field says %s. An entry has one status" % (entry["heading_status"], status))
        for name, (allowed, required, _) in FIELDS.items():
            if status in required and not fields.get(name):
                say("a %s must have %s, and this one has none" % (status, name))
            if name in fields and status not in allowed:
                say("a %s may not have the field %s. Only a %s has it" % (status, name, " or a ".join(allowed)))
        try:
            date = datetime.date.fromisoformat(fields.get("date", ""))
            if earlier_date and date < earlier_date:
                say("its date is before the date of the entry above it. The log only grows, in order")
            earlier_date = date
        except ValueError:
            say("the date is not a day written as YYYY-MM-DD")
        for name in ("source", "approved_in"):
            if fields.get(name) and not REFERENCE_SHAPE.search(fields[name]):
                say("%s names no reference, such as DOC-4 or MN-2026-09-08, that a reader could look up" % name)
        if not entry["statement"].startswith(OPENING[status] + " "):
            say("the statement must begin with %s so that it says what it is when quoted on its own" % OPENING[status])
        if status == "question" and fields.get("title") and not fields["title"].endswith("?"):
            say("a question's title ends with a question mark")
        if status != "decision":
            shown = unquoted(fields.get("title", "") + "\n" + entry["statement"].replace(OPENING[status], "", 1))
            for pattern in DECIDED_WORDING:
                hit = re.search(pattern, shown, re.I)
                if hit:
                    say("a %s is worded as if it were settled: it says \"%s\" outside a quotation" % (status, hit.group(0)))
        if status == "decision":
            kind = fields.get("kind")
            if kind and kind not in KINDS:
                say("the kind is %s, and it must be one of %s" % (json.dumps(kind), ", ".join(KINDS)))
            elif kind and fields.get("approver") and fields["approver"] != KINDS[kind][0]:
                say("a %s decision is approved by the %s, and this one names the %s" % (kind, KINDS[kind][0], fields["approver"]))
            words = fields.get("approval_words", "")
            if words:
                quoted = re.fullmatch(r'"(.+)"', words)
                plain = (quoted.group(1) if quoted else words).lower()
                if not quoted:
                    say("approval_words must be the approver's own words, inside double quotes")
                elif not any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(word), plain) for word in APPROVAL_WORDS):
                    weak = [word for word in AGREEMENT_ONLY if re.search(r"(?<![a-z+])%s(?![a-z])" % re.escape(word), plain)]
                    say("the approval words are agreement, not approval%s. An approval says so in words such as \"approved\" or \"go ahead with\""
                        % (": they say \"%s\"" % weak[0] if weak else ""))
            if sum(1 for name in ("promotes", "rejects") if fields.get(name)) > 1:
                say("a decision either approves a proposal or declines one, not both")
        for name in REFERENCES:
            target = fields.get(name)
            if not target:
                continue
            if not re.fullmatch(r"E-\d{3}", target):
                say("%s must name one entry, such as E-003" % name)
            elif target not in by_id or target == here:
                say("%s points at %s, which is not an earlier entry" % (name, target))
            else:
                wanted = {"promotes": "proposal", "rejects": "proposal", "supersedes": "decision", "answers": "question"}[name]
                if by_id[target]["fields"].get("status") != wanted:
                    say("%s points at %s, which is a %s. It must point at a %s" % (name, target, by_id[target]["fields"].get("status"), wanted))
        for name in LISTS:
            for item in ids_in(fields.get(name, "")):
                if not REFERENCE_SHAPE.fullmatch(item):
                    say("%s holds %s, which is not a work item's identifier" % (name, json.dumps(item)))
        if fields.get("treated_as_decided_in") and not REFERENCE_SHAPE.search(fields["treated_as_decided_in"]):
            say("treated_as_decided_in names no reference a reader could look up")

    # one proposal is approved or declined once; one decision is superseded once; one question is answered by one decision
    taken = {}
    for entry in entries:
        fields = entry["fields"]
        for name, group in (("promotes", "settle"), ("rejects", "settle"), ("supersedes", "supersede"), ("answers", "answer")):
            target = fields.get(name)
            if not target or target not in by_id or (name == "answers" and fields.get("status") != "decision"):
                continue
            if (group, target) in taken:
                wrong.append((entry["id"], "%s was already %s by %s. A new entry must point at the entry that stands now"
                              % (target, {"settle": "approved or declined", "supersede": "superseded", "answer": "answered"}[group], taken[(group, target)])))
            else:
                taken[(group, target)] = entry["id"]

    # the generated part
    wanted = view_block(entries)
    if BEGIN not in text or END not in text or text.index(BEGIN) > text.index(END):
        wrong.append(("log", "the generated part, between its two marker lines, is missing. Run: decisions.py view"))
    elif text[text.index(BEGIN):text.index(END) + len(END)] != wanted:
        wrong.append(("log", "the view of current decisions at the top is not what the entries say. It is stale or was edited by hand. Run: decisions.py view"))
    elif text.index(END) > text.index("### " + entries[0]["id"]):
        wrong.append(("log", "the generated part must come before the first entry"))

    # the ledger: an entry is never edited or removed after it is sealed
    if ledger is not None:
        sealed = ledger.get("entries", {})
        for entry in entries:
            if entry["malformed"]:
                continue
            digest = hashlib.sha256(entry["text"].encode("utf-8")).hexdigest()
            if entry["id"] not in sealed:
                wrong.append((entry["id"], "the entry is not sealed yet, so a later edit to it would not be noticed. Run: decisions.py seal"))
            elif sealed[entry["id"]] != digest:
                wrong.append((entry["id"], "the entry was changed after it was sealed. An entry is never edited: write a new entry that points at it"))
        for gone in sorted(set(sealed) - set(by_id)):
            wrong.append((gone, "the entry was sealed and is no longer in the log. An entry is never removed"))
    return wrong, entries


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def view_block(entries):
    """The generated part of the log, from its entries alone."""
    state = states(entries)
    good = [entry for entry in entries if entry["fields"].get("status") in STATUSES]
    decisions = [entry for entry in good if entry["fields"]["status"] == "decision"]
    current = [entry for entry in decisions if state[entry["id"]][0] == "current"]
    field = lambda entry, name: cell(entry["fields"].get(name, "") or "none")
    lines = [BEGIN, "", "## What is decided now", "",
             "Only decisions that have not been superseded. Each was approved by the role the rules allow, in the place named. This list is worked out from the entries below,",
             "so it cannot say something they do not.", ""]
    if current:
        lines += ["| Entry | Date | Decision | Kind | Approved by | Approved in | Affects |", "|---|---|---|---|---|---|---|"]
        lines += ["| %s | %s | %s | %s | %s | %s | %s |" % (entry["id"], field(entry, "date"), field(entry, "title"), field(entry, "kind"), field(entry, "approver"),
                                                           field(entry, "approved_in"), field(entry, "affects")) for entry in current]
    else:
        lines.append("Nothing is decided.")
    undecided = [entry for entry in good if entry["fields"]["status"] != "decision" and state[entry["id"]][0].startswith("open")]
    lines += ["", "## What is NOT decided", "",
              "Open proposals and open questions. **None of these is a decision**, whatever any other document says. Do not build on one as if it were.", ""]
    if undecided:
        lines += ["| Entry | Date | Status | Title | Agreement so far, which is not approval |", "|---|---|---|---|---|"]
        lines += ["| %s | %s | %s | %s | %s |" % (entry["id"], field(entry, "date"), "PROPOSAL, not decided" if entry["fields"]["status"] == "proposal" else "QUESTION, " + (
            "not answered" if state[entry["id"]][0] == "open" else "not answered. %s proposes an answer" % state[entry["id"]][1]), field(entry, "title"), field(entry, "support"))
                  for entry in undecided]
    else:
        lines.append("Nothing is open.")
    misused = [entry for entry in good if entry["fields"]["status"] == "proposal" and state[entry["id"]][0] == "open"
               and (entry["fields"].get("treated_as_decided_in") or entry["fields"].get("built_on_it"))]
    lines += ["", "## Proposals that something else treats as decided", "",
              "A proposal that another document presents as a decision, or that work has been started on. Nobody has approved it."]
    lines += [""] + (["| Entry | Proposal | Presented as decided in | Work started on it |", "|---|---|---|---|"] +
                     ["| %s | %s | %s | %s |" % (entry["id"], field(entry, "title"), field(entry, "treated_as_decided_in"), field(entry, "built_on_it")) for entry in misused]
                     if misused else ["None."])
    idle = [entry for entry in current if not ids_in(entry["fields"].get("affects", ""))]
    lines += ["", "## Current decisions with no work item", "", "A decision that names no work item it affects. Either nothing needs doing, or something has been forgotten."]
    lines += [""] + (["- %s: %s" % (entry["id"], cell(entry["fields"].get("title", ""))) for entry in idle] if idle else ["None."])
    lines += ["", "## What became of every entry", "", "| Entry | Date | Status | Now | Title |", "|---|---|---|---|---|"]
    for entry in good:
        what, by = state[entry["id"]]
        now = {"current": "current", "open": "open", "approved": "approved, by %s" % by, "declined": "declined, by %s" % by, "superseded": "SUPERSEDED by %s" % by,
               "answered": "answered, by %s" % by, "open, with a proposed answer": "open. %s proposes an answer" % by}[what]
        lines.append("| %s | %s | %s | %s | %s |" % (entry["id"], field(entry, "date"), entry["fields"]["status"], now, field(entry, "title")))
    lines += ["", END]
    return "\n".join(lines)


def rules_document():
    lines = [
        "# The rules of the decision log", "",
        "Written by an AI assistant (Claude) at the participant's direction, for the quest `context-decision-log`. The tables in this document are written out from",
        "`participant/skills/context-decision-log/decisions.py` by its `rules` command, and that file is what checks the log. So the rules and the check cannot disagree.", "",
        "The log is `log.md`, beside this file. The project in it is made up.", "",
        "## 1. Every entry is one of three things", "",
        "An entry has exactly one status, written in its heading and again in its `status` field:", "",
        "- a **decision**: someone with the right to approve has approved it, and the entry shows who, where and in what words;",
        "- a **proposal**: someone has suggested it. It may be widely liked. It is not approved;",
        "- a **question**: someone has asked. Nobody has answered with a decision.", "",
        "So that an entry still says what it is when one sentence of it is copied into a ticket, its statement begins with a fixed opening:", ""]
    lines += ["- a %s begins `%s`" % (status, OPENING[status]) for status in STATUSES]
    lines += ["", "## 2. What makes an entry a decision", "",
              "An entry is a decision only if it records all four of these. If one is missing, it is a proposal.", "",
              "1. **An approver who may approve it.** A role, and the right role for the kind of decision:", "",
              "   | Kind of decision | What it covers | Approved by |", "   |---|---|---|"]
    lines += ["   | %s | %s | the %s |" % (kind, covers, role) for kind, (role, covers) in KINDS.items()]
    lines += ["", "2. **An act of approval, in the approver's own words**, quoted in `approval_words`. The words must say that this is approved or declined: one of",
              "   " + ", ".join("\"%s\"" % word for word in APPROVAL_WORDS) + ".",
              "3. **The place** those words are recorded, in `approved_in`, with a reference a reader can look up.",
              "4. **The date.**", "",
              "### What is not an approval", "",
              "- **Agreement in conversation.** Words such as " + ", ".join("\"%s\"" % word for word in AGREEMENT_ONLY[:8]) + ". They show that people like an idea. They do",
              "  not show that the person answerable for it has said yes to it.",
              "- **Silence**, or nobody objecting.",
              "- **Agreement from a role that cannot approve that kind of decision.** A tech lead who likes a retention period has not approved it: retention is a security",
              "  decision.",
              "- **A report of an approval.** \"The product owner said it was fine\" is somebody else's words. The entry needs the approver's own, and where they are.",
              "- **Approval of something nearby.** The words must be about this decision.", "",
              "Agreement is still worth keeping. A proposal records it in `support`: who agreed, how, and where. It stays a proposal.", "",
              "## 3. How a proposal becomes a decision", "",
              "The proposal's entry is not changed. A **new entry** is added, with the status decision, the four things in section 2, and `promotes:` naming the proposal.",
              "From then on the proposal is shown as \"approved, by\" that entry. A proposal that the approver declines gets a new decision entry with `rejects:`.",
              "A proposal is approved or declined once.", "",
              "## 4. How a decision is superseded", "",
              "The decision's entry is not changed. A **new decision** is added, approved in the same way, with `supersedes:` naming the decision it replaces. From then on",
              "the older one is shown as \"SUPERSEDED by\" the newer, and drops out of the list of current decisions. A decision is superseded once: a third decision",
              "supersedes the second, not the first. To withdraw a decision without replacing it, the approver approves a new decision that says so, and it supersedes the old one.", "",
              "## 5. How a question is answered", "",
              "By a decision with `answers:` naming the question. A proposal may also name a question it offers an answer to. The question stays open until a decision answers it.", "",
              "## 6. The log only grows", "",
              "- Entries are numbered `E-001`, `E-002` and so on, with no gaps, in the order they were written. Dates never go backwards.",
              "- An entry is never edited and never removed. `ledger.json` holds a checksum of each entry from the moment it is sealed, and the check reports an entry whose",
              "  text no longer matches, or that has gone.",
              "- Whether an entry still stands is never written into it. It is worked out from the entries that point at it.", "",
              "## 7. Finding what is decided now", "",
              "The top of `log.md` holds a part that `decisions.py view` writes from the entries: the current decisions, what is not decided, proposals that something else",
              "treats as decided, current decisions with no work item, and what became of every entry. Nobody edits it. The check fails if it is not exactly what the entries say.", "",
              "## 8. A proposal is never shown as a decision", "",
              "- A proposal or a question may not have the fields `approver`, `approved_in` or `approval_words`.",
              "- Its title and statement may not use wording that presents it as settled, outside a quotation: decided, approved, signed off, final, \"we will\", agreed,",
              "  \"the decision\", settled, confirmed.",
              "- If another document presents a proposal as decided, the proposal says so in `treated_as_decided_in`, and lists in `built_on_it` the work started on it. The",
              "  log reports these at the top. It does not turn the proposal into a decision.", "",
              "## 9. Every entry cites its source", "",
              "`source` says where the entry comes from, with a reference a reader can look up, such as `DOC-4, section 2`. A decision also has `approved_in`.", "",
              "## 10. The fields", "", "| Field | May appear on | Required on | Meaning |", "|---|---|---|---|"]
    lines += ["| `%s` | %s | %s | %s |" % (name, ", ".join(allowed), ", ".join(required) or "none", meaning) for name, (allowed, required, meaning) in FIELDS.items()]
    lines += ["", "## 11. What the check cannot know", "",
              "The check reads the log. It cannot open the document an entry cites, so it cannot tell whether the approver really wrote those words there. It checks that the",
              "words are given, quoted, and are words of approval. Whether they are true is for a person to check, by following the reference.", "",
              "This log is kept by a person. The skill adds no entry and approves nothing. **Nobody records a decision on someone else's behalf**: an entry is a decision",
              "because the approver's own words exist at the place it names."]
    return "\n".join(lines) + "\n"


def report(text, ledger, say):
    wrong, entries = check(text, ledger)
    state = states(entries)
    count = lambda status: sum(1 for entry in entries if entry["fields"].get("status") == status)
    decisions = [entry for entry in entries if entry["fields"].get("status") == "decision"]
    current = [entry["id"] for entry in decisions if state[entry["id"]][0] == "current"]
    say("decision-log: %d entries: %d decisions, %d proposals, %d questions" % (len(entries), count("decision"), count("proposal"), count("question")))
    say("decision-log: decisions current: %d (%s). Superseded: %d (%s)" % (
        len(current), ", ".join(current) or "none", len(decisions) - len(current),
        ", ".join("%s by %s" % (entry["id"], state[entry["id"]][1]) for entry in decisions if state[entry["id"]][0] == "superseded") or "none"))
    say("decision-log: proposals: %s" % (", ".join("%s %s" % (entry["id"], state[entry["id"]][0] + (" by %s" % state[entry["id"]][1] if state[entry["id"]][1] else ""))
                                                   for entry in entries if entry["fields"].get("status") == "proposal") or "none"))
    say("decision-log: questions: %s" % (", ".join("%s %s" % (entry["id"], state[entry["id"]][0] + (" by %s" % state[entry["id"]][1] if state[entry["id"]][1] and state[entry["id"]][0] == "answered" else ""))
                                                   for entry in entries if entry["fields"].get("status") == "question") or "none"))
    for entry in entries:
        fields = entry["fields"]
        if fields.get("status") == "proposal" and state[entry["id"]][0] == "open" and (fields.get("treated_as_decided_in") or fields.get("built_on_it")):
            say("decision-log: WARNING: %s is a proposal that something else treats as decided: %s. Work started on it: %s. It is not approved"
                % (entry["id"], fields.get("treated_as_decided_in", "not recorded"), fields.get("built_on_it", "none recorded")))
    for entry in decisions:
        if entry["id"] in current and not ids_in(entry["fields"].get("affects", "")):
            say("decision-log: NOTE: the current decision %s names no work item it affects" % entry["id"])
    for where, message in wrong:
        say("decision-log: RULE BROKEN: %s: %s" % (where, message))
    say("decision-log: RESULT: %s" % ("the log keeps every rule" if not wrong else "the log breaks the rules in %d place%s" % (len(wrong), "" if len(wrong) == 1 else "s")))
    return wrong


def load_ledger(log):
    path = ledger_path(log)
    if not os.path.exists(path):
        return {"entries": {}}
    try:
        return json.loads(read(path))
    except ValueError:
        raise Stop("ledger.json is not JSON")


def write(path, text):
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def main(argv=None, say=print):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("check", "view", "seal", "rules"))
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        if args.command == "rules":
            if not args.out:
                raise Stop("rules needs --out FILE")
            write(args.out, rules_document())
            say("decision-log: wrote the rules to %s" % os.path.basename(args.out))
            return 0
        text = read(args.log)
        if args.command == "check":
            return 2 if report(text, load_ledger(args.log), say) else 0
        entries = parse(text)
        if args.command == "view":
            if BEGIN not in text or END not in text:
                raise Stop("the log has no marker lines for the generated part. Nothing was written")
            new = text[:text.index(BEGIN)] + view_block(entries) + text[text.index(END) + len(END):]
            if new != text:
                write(args.log, new)
            say("decision-log: the generated part of the log %s" % ("was rewritten from the entries" if new != text else "already says what the entries say. Nothing was written"))
            return 0
        ledger = load_ledger(args.log)
        sealed = ledger.setdefault("entries", {})
        added = []
        for entry in entries:
            if not entry["malformed"] and entry["id"] not in sealed:               # an entry already sealed is never sealed again
                sealed[entry["id"]] = hashlib.sha256(entry["text"].encode("utf-8")).hexdigest()
                added.append(entry["id"])
        if added:
            ledger["note"] = "The SHA-256 of each entry of log.md, taken when the entry was sealed. decisions.py seal adds to this file and never changes a line already in it."
            write(ledger_path(args.log), json.dumps(ledger, indent=1, sort_keys=True) + "\n")
        say("decision-log: sealed %d new entr%s%s. %d sealed in all" % (len(added), "y" if len(added) == 1 else "ies", ": " + ", ".join(added) if added else "", len(sealed)))
        return 0
    except Stop as error:
        say("decision-log: STOPPED: %s" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())

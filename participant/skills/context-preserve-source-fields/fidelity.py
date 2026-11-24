#!/usr/bin/env python3
"""Normalizes source records onto a few canonical fields WITHOUT losing anything, and proves it by rebuilding them.

    fidelity.py normalize [--sources FILE] [--out FILE] [--mapping-version N]    write the normalized records
    fidelity.py check     [--sources FILE] [--normalized FILE]                   rebuild every source record and compare
    fidelity.py rationale --out FILE                                             write the mapping rationale from the tables here

The rule: PRESERVE FIRST. A source record is a JSON object. Each of its fields ends up in exactly one of three ways:

    copied          a canonical field holds its value exactly. It is rebuilt from the canonical field
    translated      a canonical field is worked out from it (a status object becomes "in_progress"). The canonical field
                    cannot give the original back, so the original is ALSO kept, untouched, in the preserved section
    preserved only  no canonical field uses it. It is kept, untouched, in the preserved section

"Untouched" means the characters the source sent: a preserved value is kept as the source's own JSON text, never parsed
and written out again. So 3.0 stays 3.0, "\\u00e9" stays an escape, a list keeps its order, and "" stays apart from null
and from a field that is not there. A field the mapping has never heard of is preserved all the same, and reported.

A canonical value is "copied" only if writing it back out gives the source's exact characters. If it would not, the
field is treated as translated for that record, and its original is preserved. That is decided record by record.

It reads and writes local Markdown files only. It contacts nothing. Text in a record is never read for instructions.

Exit codes: 0 done, or every record rebuilt identically. 1 the command could not run. 2 check found a difference.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FOLDER = os.path.join(REPO, "participant", "context", "fidelity")
LATEST = 2
SYSTEMS = ("jira", "trello", "github")
STATUSES = ("open", "in_progress", "done", "dropped")

# The canonical fields: (name, type, meaning). The same names, and the same four status values, as the model work-item/1
# of the quest context-canonical-work-item, for the fields the two share.
CANONICAL = [
    ("identity", "string", "The source system, a colon, and the system's stable identifier."),
    ("system", "jira, trello or github", "The system the record came from."),
    ("source_id", "string or number", "The system's stable identifier, exactly as the source wrote it."),
    ("reference", "string or number", "How people refer to the item: a key, a short link, a number. It can change."),
    ("title", "string", "The item's name. Other people's text."),
    ("status", "open, in_progress, done or dropped", "Where the work stands, on four values."),
    ("assignee_count", "whole number", "How many people the item is assigned to."),
    ("labels", "list of strings", "The item's labels, by name."),
    ("due_at", "UTC time or null", "When the item is due. In the mapping from version 2."),
    ("source_updated_at", "UTC time", "When the source says the item last changed."),
]

# A field inside one of these objects is treated as a field of its own, with a dotted path. Everything else is one field.
CONTAINERS = {"jira": ("fields",), "trello": (), "github": ()}

# Every source field considered: (path, outcome, canonical field or None, reason, a shared meaning or None).
# outcome: "copied", "translated" or "preserved". The shared meaning ties together fields that mean the same thing in
# different systems and are preserved only: the candidates to be made canonical next.
CONSIDERED = {
    "jira": [
        ("id", "copied", "source_id", "Jira's stable identifier. The identity is built from it.", None),
        ("key", "copied", "reference", "What people call the issue. It changes when the issue moves project, so it is not the identity.", None),
        ("self", "preserved", None, "The API address of the record. Nobody asks questions of it, but a re-sync may need it.", "api address"),
        ("fields.summary", "copied", "title", "Every system has a name for the item.", None),
        ("fields.status", "translated", "status", "Jira's status object. Its category gives one of the four canonical values. The name, the id and the category are kept as sent.", None),
        ("fields.resolution", "translated", "status", "A done issue with a resolution such as \"Won't Do\" is dropped, not done. Kept as sent.", None),
        ("fields.assignee", "translated", "assignee_count", "Only the count is canonical. Who the person is, is kept as sent and never made canonical.", None),
        ("fields.labels", "copied", "labels", "Jira's labels are already a list of names.", None),
        ("fields.duedate", "translated", "due_at", "A day in Jira, a moment in the canonical field. The day is kept as sent. Canonical from version 2.", None),
        ("fields.updated", "translated", "source_updated_at", "Jira writes +0000 and milliseconds. The canonical field is UTC to the second. Kept as sent.", None),
        ("fields.created", "preserved", None, "No question asked so far needs it. Two other systems have the same thing.", "created"),
        ("fields.description", "preserved", None, "Long text in another person's words. The canonical model does not carry the text of the work.", "description"),
        ("fields.issuetype", "preserved", None, "Story, bug, epic. Only Jira has types, and each site names its own.", "type"),
        ("fields.priority", "preserved", None, "A named priority. The other systems order work differently, so there is no one scale.", "priority or order"),
        ("fields.parent", "preserved", None, "The epic the story belongs to. Only Jira supplies a parent here.", "parent"),
        ("fields.timetracking", "preserved", None, "Estimates and time spent. Only Jira has them.", None),
        ("fields.customfield_10016", "preserved", None, "Story points on this made-up site. A custom field: its number and meaning differ from site to site.", "estimate"),
        ("fields.customfield_10020", "preserved", None, "The sprint, on this made-up site. A custom field.", None),
        ("fields.components", "preserved", None, "Which part of the product. Only Jira has components.", None),
    ],
    "trello": [
        ("id", "copied", "source_id", "Trello's stable identifier. The identity is built from it.", None),
        ("shortLink", "copied", "reference", "What a card's address is built from. Not the identity.", None),
        ("idShort", "preserved", None, "The card's number on its board. A second way people refer to it.", None),
        ("name", "copied", "title", "Every system has a name for the item.", None),
        ("closed", "translated", "status", "An archived card is dropped. Kept as sent.", None),
        ("idList", "translated", "status", "The list a card is in is the only status Trello has. Which list means what is the status map's decision. Kept as sent.", None),
        ("idMembers", "translated", "assignee_count", "Only the count is canonical. The member ids are kept as sent.", None),
        ("labels", "translated", "labels", "Trello's labels are objects with a colour. Only the names are canonical. The objects are kept as sent, in their order.", None),
        ("due", "translated", "due_at", "Trello writes milliseconds. The canonical field is UTC to the second. Kept as sent. Canonical from version 2.", None),
        ("dateLastActivity", "translated", "source_updated_at", "Trello's only time of change. Kept as sent.", None),
        ("dueComplete", "preserved", None, "A tick on the due date. It is not a status: a ticked card can sit in any list.", None),
        ("desc", "preserved", None, "The card's description. The canonical model does not carry the text of the work.", "description"),
        ("idBoard", "preserved", None, "The board. A canonical container may come later: all three systems have one.", "container"),
        ("pos", "preserved", None, "The card's place in its list, which is how a Trello team says what comes first. No one scale across systems.", "priority or order"),
        ("customFieldItems", "preserved", None, "The board's own fields, such as customer impact. Each board defines its own, so there is nothing to map them to yet.", None),
        ("idChecklists", "preserved", None, "The card's checklists, in order. A checklist item is not a work item here.", None),
        ("badges", "preserved", None, "Counts Trello shows on the card's face.", None),
        ("cover", "preserved", None, "How the card looks on the board. It says nothing about the work.", None),
    ],
    "github": [
        ("node_id", "copied", "source_id", "GitHub's stable identifier. The identity is built from it.", None),
        ("id", "preserved", None, "A second, numeric identifier of the same issue.", None),
        ("number", "copied", "reference", "The issue's number in its repository. It changes on transfer, so it is not the identity.", None),
        ("title", "copied", "title", "Every system has a name for the item.", None),
        ("state", "translated", "status", "open or closed. Kept as sent.", None),
        ("state_reason", "translated", "status", "Why it was closed: completed is done, not_planned is dropped. Kept as sent.", None),
        ("assignees", "translated", "assignee_count", "Only the count is canonical. The people are kept as sent.", None),
        ("labels", "translated", "labels", "GitHub's labels are objects. Only the names are canonical. The objects are kept as sent.", None),
        ("updated_at", "copied", "source_updated_at", "GitHub already writes UTC to the second, so the canonical field holds it exactly.", None),
        ("created_at", "preserved", None, "No question asked so far needs it. Two other systems have the same thing.", "created"),
        ("closed_at", "preserved", None, "When it was closed. Only GitHub states this as a field.", None),
        ("body", "preserved", None, "The issue's text. The canonical model does not carry the text of the work.", "description"),
        ("repository_url", "preserved", None, "The repository. A canonical container may come later.", "container"),
        ("url", "preserved", None, "The API address of the record. A re-sync may need it.", "api address"),
        ("milestone", "preserved", None, "A milestone, with its own due date. Not the issue's due date, so it is not mapped to due_at.", None),
        ("locked", "preserved", None, "Whether people may still comment.", None),
        ("author_association", "preserved", None, "The author's relation to the repository.", None),
        ("reactions", "preserved", None, "Counts of reactions. Nobody plans work from them, and only GitHub has them.", None),
        ("sub_issues_summary", "preserved", None, "Counts of sub-issues. A parent link may come from this later.", "parent"),
        ("type", "preserved", None, "GitHub's newer issue type. Jira has types too, each site naming its own.", "type"),
    ],
}
HISTORY = [
    (1, "The first mapping. Nine canonical fields. Every due date was preserved only."),
    (2, "due_at became canonical, for Jira's `fields.duedate` and Trello's `due`. Both were preserved-only in version 1. Their original values are still preserved, because the "
        "canonical field holds a moment in UTC and neither source writes it that way. No record changed in what it preserves: a record normalized under version 1 and one under "
        "version 2 both rebuild to the same original."),
]


class Stop(Exception):
    pass


def outcome_of(system, path, version=LATEST):
    for known, outcome, canonical, _, _ in CONSIDERED[system]:
        if known == path:
            if canonical == "due_at" and version < 2:
                return "preserved", None
            return outcome, canonical
    return "preserved", None              # a field the mapping has never heard of: preserved all the same


# ------------------------------------------------------------------ JSON, kept as the characters the source sent

def skip_space(text, at):
    while at < len(text) and text[at] in " \t\r\n":
        at += 1
    return at


def value_end(text, at):
    """Where the JSON value that starts at `at` ends. The value is not interpreted."""
    if text[at] == '"':
        at += 1
        while text[at] != '"':
            at += 2 if text[at] == "\\" else 1
        return at + 1
    if text[at] in "{[":
        depth = 0
        while True:
            if text[at] == '"':
                at = value_end(text, at)
                continue
            if text[at] in "{[":
                depth += 1
            elif text[at] in "}]":
                depth -= 1
                if depth == 0:
                    return at + 1
            at += 1
    while at < len(text) and text[at] not in ",}] \t\r\n":
        at += 1
    return at


def members(text):
    """The members of a JSON object, as (key, the value's own characters), in the order written."""
    at = skip_space(text, 0)
    if at >= len(text) or text[at] != "{":
        raise ValueError("not a JSON object")
    found = []
    at = skip_space(text, at + 1)
    while text[at] != "}":
        end = value_end(text, at)
        key = json.loads(text[at:end])
        at = skip_space(text, end)
        if text[at] != ":":
            raise ValueError("no colon after %s" % key)
        at = skip_space(text, at + 1)
        end = value_end(text, at)
        found.append((key, text[at:end]))
        at = skip_space(text, end)
        if text[at] == ",":
            at = skip_space(text, at + 1)
    if text[skip_space(text, at + 1):].strip():
        raise ValueError("text after the end of the object")
    return found


def fields_of(system, text):
    """A source record as (path, raw characters) pairs in source order. Members of a container get a dotted path."""
    found = []
    for key, raw in members(text):
        if key in CONTAINERS[system] and raw.startswith("{"):
            found.append((key, None))                                  # the container itself: a place in the order, no value
            found += [("%s.%s" % (key, inner), inner_raw) for inner, inner_raw in members(raw)]
        else:
            found.append((key, raw))
    if len(set(path for path, _ in found)) != len(found):
        raise ValueError("a field appears twice in the record")
    return found


def layout(pairs):
    """(path, raw) pairs back into the text of a JSON object: one field per line, two spaces of indent, four inside a container."""
    lines, at = ["{"], 0
    while at < len(pairs):
        path, raw = pairs[at]
        if raw is None:                                                 # a container: its members follow
            inner = []
            at += 1
            while at < len(pairs) and pairs[at][0].startswith(path + "."):
                inner.append("    %s: %s" % (json.dumps(pairs[at][0][len(path) + 1:], ensure_ascii=False), pairs[at][1]))
                at += 1
            lines.append("  %s: {\n%s\n  }," % (json.dumps(path, ensure_ascii=False), ",\n".join(inner)) if inner else "  %s: {}," % json.dumps(path, ensure_ascii=False))
        else:
            lines.append("  %s: %s," % (json.dumps(path, ensure_ascii=False), raw))
            at += 1
    if len(lines) > 1:
        lines[-1] = lines[-1][:-1]
    return "\n".join(lines + ["}"])


def write_value(value):
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


# ------------------------------------------------------------------ the canonical fields

def utc(value):
    if value is None:
        return None
    text = value + "T00:00:00+00:00" if re.fullmatch(r"\d{4}-\d\d-\d\d", value) else value
    text = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", re.sub(r"Z$", "+00:00", text))
    return datetime.datetime.fromisoformat(text).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_of(system, record, status_map, version=LATEST):
    """The canonical fields of one source record, from its parsed values."""
    get = record.get
    if system == "jira":
        status = get("fields.status") or {}
        value = {"new": "open", "indeterminate": "in_progress", "done": "done"}.get((status.get("statusCategory") or {}).get("key"))
        if value == "done" and (get("fields.resolution") or {}).get("name") in ("Won't Do", "Duplicate"):
            value = "dropped"
        fields = {"source_id": get("id"), "reference": get("key"), "title": get("fields.summary"), "status": value,
                  "assignee_count": 1 if get("fields.assignee") else 0, "labels": get("fields.labels") or [],
                  "due_at": utc(get("fields.duedate")), "source_updated_at": utc(get("fields.updated"))}
    elif system == "trello":
        value = "dropped" if get("closed") else status_map.get(get("idList"), "open")
        fields = {"source_id": get("id"), "reference": get("shortLink"), "title": get("name"), "status": value,
                  "assignee_count": len(get("idMembers") or []), "labels": [one.get("name") for one in get("labels") or []],
                  "due_at": utc(get("due")), "source_updated_at": utc(get("dateLastActivity"))}
    else:
        state, reason = get("state"), get("state_reason")
        value = "open" if state == "open" else "dropped" if reason in ("not_planned", "duplicate") else "done"
        fields = {"source_id": get("node_id"), "reference": get("number"), "title": get("title"), "status": value,
                  "assignee_count": len(get("assignees") or []), "labels": [one.get("name") for one in get("labels") or []],
                  "due_at": None, "source_updated_at": utc(get("updated_at"))}
    if value not in STATUSES:
        raise Stop("a %s record has a status the mapping cannot place" % system)
    if version < 2:
        fields.pop("due_at")
    ordered = {"identity": "%s:%s" % (system, fields["source_id"]), "system": system}
    ordered.update((name, fields[name]) for name, _, _ in CANONICAL if name in fields)
    return ordered


# ------------------------------------------------------------------ the two files

def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as error:
        raise Stop("%s could not be read: %s" % (os.path.basename(path), error.strerror))


def source_records(text):
    """The source file's records: (heading, system, the record's text exactly as written)."""
    found = re.findall(r"^### (\S+) (\S+)[ \t]*\n(?:(?!### )[^\n]*\n)*?```json\n(.*?)\n```", text, re.M | re.S)
    return [("%s %s" % (system, name), system, block) for system, name, block in found if system in SYSTEMS]


def status_map_of(text):
    """Which Trello list means what, from the table in the source file. A person's decision, kept with the made-up data."""
    return dict(re.findall(r"^\| `([0-9a-f]{24})` \| [^|]* \| (open|in_progress|done|dropped) \|", text, re.M))


def normalize_one(heading, system, block, status_map, version=LATEST):
    pairs = fields_of(system, block)
    if any(raw is not None and "\n" in raw for _, raw in pairs):
        raise Stop("%s: a field's value is written over more than one line. A source record is one field per line" % heading)
    parsed = {path: json.loads(raw) for path, raw in pairs if raw is not None}
    canonical = canonical_of(system, parsed, status_map, version)
    preserved, from_canonical, unlisted = [], {}, []
    listed = set(path for path, _, _, _, _ in CONSIDERED[system])
    for path, raw in pairs:
        if raw is None:
            continue
        if path not in listed:
            unlisted.append(path)
        outcome, name = outcome_of(system, path, version)
        if outcome == "copied" and write_value(canonical[name]) == raw:
            from_canonical[path] = name                    # the canonical field gives back the source's exact characters
        else:
            preserved.append((path, raw))                  # translated, preserved only, unknown, or a copy that would not come back exactly
    return {"source_record": heading, "mapping_version": version, "canonical": canonical, "rebuilt_from_canonical": from_canonical,
            "field_order": [path for path, _ in pairs], "preserved": preserved, "unlisted": unlisted}


def render(records, version):
    lines = ["# Normalized records", "",
             "Written by `participant/skills/context-preserve-source-fields/fidelity.py normalize` from `source-records.md`. Do not edit this file: the next run replaces it.",
             "Mapping version %d. Every record here is made up." % version, "",
             "Each record has three parts:", "",
             "- **Canonical fields**: the same names for every system. Each value is JSON.",
             "- **How to rebuild the source record**: the order its fields came in, and which of them a canonical field gives back exactly.",
             "- **Preserved source fields**: every other field of the source record, under the source's own name, **in the characters the source sent**. Nothing here was",
             "  parsed, tidied, reordered or shortened. A value may look odd, such as `3.0`, a trailing space inside a string, or `\\u00e9`. That is how it arrived.", ""]
    for record in records:
        lines += ["## %s" % record["canonical"]["identity"], "", "- source_record: %s" % json.dumps(record["source_record"]), "- mapping_version: %d" % record["mapping_version"], "",
                  "### Canonical fields", "", "```text"] + ["%s: %s" % (name, write_value(value)) for name, value in record["canonical"].items()] + ["```", "",
                  "### How to rebuild the source record", "", "```text", "field_order: %s" % write_value(record["field_order"]),
                  "rebuilt_from_canonical: %s" % write_value(record["rebuilt_from_canonical"]), "```", "",
                  "### Preserved source fields (%d), exactly as sent" % len(record["preserved"]), "", "```text"]
        lines += ["%s: %s" % (path, raw) for path, raw in record["preserved"]] + ["```", ""]
    return "\n".join(lines)


def normalized_records(text):
    found = []
    for piece in re.split(r"^(?=## )", text, flags=re.M)[1:]:
        blocks = re.findall(r"^### (Canonical fields|How to rebuild the source record|Preserved source fields)[^\n]*\n\n```text\n(.*?)^```", piece, re.M | re.S)
        named = dict(blocks)
        if len(blocks) != 3 or len(named) != 3:
            raise Stop("a normalized record does not have its three parts: %s" % piece.split("\n")[0])
        pair = lambda line: (line.partition(": ")[0], line.partition(": ")[2])
        rebuild = dict(pair(line) for line in named["How to rebuild the source record"].split("\n") if line)
        heading = re.search(r"^- source_record: (.*)$", piece, re.M)
        found.append({"source_record": json.loads(heading.group(1)) if heading else None,
                      "canonical": {name: json.loads(value) for name, value in (pair(line) for line in named["Canonical fields"].split("\n") if line)},
                      "field_order": json.loads(rebuild.get("field_order", "[]")), "rebuilt_from_canonical": json.loads(rebuild.get("rebuilt_from_canonical", "{}")),
                      "preserved": [pair(line) for line in named["Preserved source fields"].split("\n") if line]})
    return found


def rebuild(system, record):
    """The source record's text, from a normalized record alone. Returns (text, the fields that could not be rebuilt)."""
    preserved = dict(record["preserved"])
    pairs, missing = [], []
    for path in record["field_order"]:
        if path in CONTAINERS[system]:
            pairs.append((path, None))
        elif path in preserved:
            pairs.append((path, preserved[path]))
        elif path in record["rebuilt_from_canonical"] and record["rebuilt_from_canonical"][path] in record["canonical"]:
            pairs.append((path, write_value(record["canonical"][record["rebuilt_from_canonical"][path]])))
        else:
            missing.append(path)
    return layout(pairs), missing


def compare(system, original, record):
    """Every difference between a source record and what its normalized record rebuilds to. An empty list: identical."""
    found = []
    rebuilt, missing = rebuild(system, record)
    source = fields_of(system, original)
    held = dict(record["preserved"])
    for path, raw in source:
        if raw is None:
            continue
        if path not in record["field_order"] or path in missing:
            found.append("MISSING FIELD: %s is in the source record and cannot be rebuilt: it is neither preserved nor given back by a canonical field" % path)
        elif path in held and held[path] != raw:
            found.append("CHANGED FIELD: %s was preserved as %s and the source sent %s" % (path, show(held[path]), show(raw)))
        elif path in record["rebuilt_from_canonical"] and path not in held:
            name = record["rebuilt_from_canonical"][path]
            back = write_value(record["canonical"].get(name))
            if back != raw:
                found.append("CHANGED FIELD: %s is rebuilt from the canonical field %s as %s and the source sent %s" % (path, name, show(back), show(raw)))
    for path in record["field_order"]:
        if path not in [one for one, _ in source]:
            found.append("EXTRA FIELD: %s is in the normalized record's field order and not in the source record" % path)
    for path in held:
        if path not in [one for one, _ in source]:
            found.append("EXTRA FIELD: %s is preserved and not in the source record" % path)
    if not found and [path for path, _ in source] != record["field_order"]:
        found.append("ORDER: the fields are all there and the order they came in was not kept")
    if not found and rebuilt != original:
        found.append("NOT IDENTICAL: every field matches and the rebuilt text still differs from the original, character for character")
    return found


def show(raw):
    return raw if len(raw) <= 70 else raw[:60] + "... (%d characters)" % len(raw)


def check(source_text, normalized_text, say):
    sources = source_records(source_text)
    records = normalized_records(normalized_text)
    by_heading = {record["source_record"]: record for record in records}
    wrong = 0
    for heading, system, block in sources:
        record = by_heading.get(heading)
        found = ["MISSING RECORD: the source record has no normalized record"] if record is None else compare(system, block, record)
        count = len([1 for _, raw in fields_of(system, block) if raw is not None])
        if found:
            wrong += 1
            say("fidelity: %s: NOT IDENTICAL. %d difference%s:" % (heading, len(found), "" if len(found) == 1 else "s"))
            for one in found:
                say("fidelity:     %s" % one)
        else:
            say("fidelity: %s: rebuilt, and identical to the original, character for character. %d fields: %d preserved as sent, %d given back by canonical fields"
                % (heading, count, len(record["preserved"]), len(record["rebuilt_from_canonical"])))
    for record in records:
        if record["source_record"] not in [heading for heading, _, _ in sources]:
            wrong += 1
            say("fidelity: %s: a normalized record with no source record" % record["source_record"])
    unlisted = sorted(set("%s %s" % (system, path) for _, system, block in sources for path, raw in fields_of(system, block)
                          if raw is not None and path not in [one[0] for one in CONSIDERED[system]]))
    for one in unlisted:
        say("fidelity: NOTE: the field %s is not in the mapping's list of fields considered. It is preserved all the same" % one)
    shared = {}
    for system in SYSTEMS:
        present = set(path for _, one, block in sources if one == system for path, raw in fields_of(system, block) if raw is not None)
        for path, outcome, _, _, meaning in CONSIDERED[system]:
            if outcome == "preserved" and meaning and path in present:
                shared.setdefault(meaning, []).append("%s `%s`" % (system, path))
    for meaning in sorted(shared):
        if len(set(one.split(" ")[0] for one in shared[meaning])) > 1:
            say("fidelity: PRESERVED IN MORE THAN ONE SYSTEM: %s: %s" % (meaning, ", ".join(shared[meaning])))
    say("fidelity: RESULT: %d source record%s. %s" % (len(sources), "" if len(sources) == 1 else "s",
                                                     "Every one was rebuilt from its normalized record and is identical to the original" if not wrong and sources
                                                     else "%d could not be rebuilt identically" % wrong if sources else "There is nothing to check"))
    return wrong or (0 if sources else 1)


def rationale_document():
    lines = ["# Mapping rationale: which source fields became canonical, and which were preserved", "",
             "Written by an AI assistant (Claude) at the participant's direction, for the quest `context-preserve-source-fields`. The tables are written out from",
             "`participant/skills/context-preserve-source-fields/fidelity.py` by its `rationale` command, so this document and the code that applies the mapping cannot disagree.",
             "", "**Mapping version: %d.** Every record this mapping is applied to here is made up." % LATEST, "",
             "## How a field is decided", "",
             "The rule is the quest's hint: **preserve first, promote later.** Nothing is dropped, so the only question for a field is whether a canonical field also carries it.",
             "A field becomes canonical when **all three** of these hold:", "",
             "1. **More than one system has it**, meaning the same thing.",
             "2. **A question people ask across systems needs it**: what is open, what is mine, what is due.",
             "3. **It can be given one meaning.** A status can, with the losses written down. A priority cannot yet: Jira names one, Trello has a position, GitHub has neither.", "",
             "Otherwise it is preserved only. That costs nothing: it is still in the record, exactly as sent, and it can be promoted later without going back to the source.", "",
             "Each field has one of three outcomes:", "",
             "| Outcome | What happens to the field | How the original comes back |", "|---|---|---|",
             "| **copied** | A canonical field holds its value exactly | From the canonical field |",
             "| **translated** | A canonical field is worked out from it. The original is also preserved, as sent | From the preserved section |",
             "| **preserved only** | No canonical field uses it. It is preserved, as sent | From the preserved section |", "",
             "A translated field is preserved as well as mapped because the canonical field cannot give it back: `in_progress` does not say whether Jira's status was",
             "\"In Review\". And a copied field is checked for every record: if writing the canonical value back out would not give the source's exact characters, that",
             "record keeps the original in its preserved section too. So \"copied\" in the tables below means \"copied unless that would lose a character\".", "",
             "A field that is in a source record and in none of these tables is preserved all the same, and the check names it.", "",
             "## The canonical fields", "", "| Canonical field | Type | Meaning |", "|---|---|---|"]
    lines += ["| `%s` | %s | %s |" % row for row in CANONICAL]
    lines += ["", "`identity` and `system` are not taken from a field: `system` is which mapping was used, and `identity` is the system and `source_id`. The names, and the four",
              "values of `status`, are those of the model `work-item/1` from the quest `context-canonical-work-item`, for the fields the two share. This mapping is a small one",
              "of its own: that model reads records earlier skills had already tidied, and leaves out on purpose things this quest must keep.", ""]
    for system in SYSTEMS:
        title = {"jira": "Jira", "trello": "Trello", "github": "GitHub"}[system]
        rows = CONSIDERED[system]
        count = lambda outcome: sum(1 for row in rows if row[1] == outcome)
        lines += ["## %s: %d fields considered" % (title, len(rows)), "",
                  "%d copied, %d translated, %d preserved only.%s" % (count("copied"), count("translated"), count("preserved"),
                                                                     " A field inside `fields` is treated as a field of its own." if CONTAINERS[system] else ""), "",
                  "| Source field | Outcome | Canonical field | Why |", "|---|---|---|---|"]
        lines += ["| `%s` | %s | %s | %s |" % (path, {"preserved": "preserved only"}.get(outcome, outcome), "`%s`" % canonical if canonical else "none", reason)
                  for path, outcome, canonical, reason, _ in rows]
        lines.append("")
    lines += ["## Preserved fields that more than one system has", "",
              "These are preserved only, and mean the same thing in more than one system. They meet the first of the three conditions above, so they are the fields most",
              "likely to become canonical next. The check reports them from the records themselves.", "", "| What it is | Where it is preserved |", "|---|---|"]
    shared = {}
    for system in SYSTEMS:
        for path, outcome, _, _, meaning in CONSIDERED[system]:
            if outcome == "preserved" and meaning:
                shared.setdefault(meaning, []).append("%s `%s`" % (system, path))
    lines += ["| %s | %s |" % (meaning, ", ".join(shared[meaning])) for meaning in sorted(shared) if len(set(one.split(" ")[0] for one in shared[meaning])) > 1]
    lines += ["", "## The mapping's versions", "", "| Version | What changed |", "|---|---|"] + ["| %d | %s |" % row for row in HISTORY]
    lines += ["", "Each normalized record says which version of the mapping wrote it. Promoting a field changes which canonical fields a record has. It never changes what",
              "can be rebuilt from the record, because the original was preserved before anyone decided it mattered."]
    return "\n".join(lines) + "\n"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def main(argv=None, say=print):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("normalize", "check", "rationale"))
    parser.add_argument("--sources", default=os.path.join(FOLDER, "source-records.md"))
    parser.add_argument("--normalized", default=os.path.join(FOLDER, "normalized.md"))
    parser.add_argument("--out")
    parser.add_argument("--mapping-version", type=int, default=LATEST, choices=[number for number, _ in HISTORY])
    args = parser.parse_args(argv)
    try:
        if args.command == "rationale":
            if not args.out:
                raise Stop("rationale needs --out FILE")
            write(args.out, rationale_document())
            say("fidelity: wrote the mapping rationale, version %d" % LATEST)
            return 0
        source_text = read(args.sources)
        if args.command == "normalize":
            status_map = status_map_of(source_text)
            records = [normalize_one(heading, system, block, status_map, args.mapping_version) for heading, system, block in source_records(source_text)]
            if not records:
                raise Stop("the source file holds no records")
            write(args.out or args.normalized, render(records, args.mapping_version))
            say("fidelity: normalized %d source records with mapping version %d: %d fields in all, %d preserved as sent, %d given back by canonical fields"
                % (len(records), args.mapping_version, sum(len(r["preserved"]) + len(r["rebuilt_from_canonical"]) for r in records),
                   sum(len(r["preserved"]) for r in records), sum(len(r["rebuilt_from_canonical"]) for r in records)))
            return 0
        return 2 if check(source_text, read(args.normalized), say) else 0
    except (Stop, ValueError) as error:
        say("fidelity: STOPPED: %s" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())

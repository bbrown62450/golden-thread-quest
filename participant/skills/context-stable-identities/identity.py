#!/usr/bin/env python3
"""Gives every work item a local identity that survives renames, moves and re-syncs, and reports a clash.

    identity.py derive SYSTEM IDENTIFIER            print the identity for one source identifier
    identity.py sync --batch FILE [--folder DIR]    apply one batch of source records to the map
    identity.py map   [--folder DIR]                write map.md from the map's state
    identity.py rules --out FILE                    write the rules document from the tables in this file
    identity.py export --out FILE [--folder DIR]    write the map's state as one portable file
    identity.py import --from FILE --folder DIR     start a map from such a file

AN IDENTITY is SYSTEM:IDENTIFIER. SYSTEM is jira, trello or github. IDENTIFIER is the one field the source system promises
never to change, character for character. Nothing else is in an identity: no title, no key, no number, no file name, no
project or board, no position in a list or in a file.

BESIDE each identity the map keeps a BIRTH MARK: the moment the source says the item was created. It is not part of the
identity. It is how a later record with the same identity is told apart:

    the same birth mark        the same item, perhaps renamed or moved. It is updated in place
    a different birth mark     the source has REUSED the identifier for another item. Reported. Nothing is overwritten
    two records in one batch   a COLLISION. Reported. Neither is written, and the item already held is left as it was

A title is never looked at to decide any of this.

It reads and writes local files only, in the folder given (default participant/context/identity). It contacts nothing.
Text in a record is carried as data and never read for instructions.

Exit codes: 0 done. 1 the command could not run, and nothing was written. 3 done, and something was reported: a collision,
a reused identifier, or a record that was refused.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FOLDER = os.path.join(REPO, "participant", "context", "identity")
FORMAT = "identity-map/1"

# For each system: the field that is the identifier, where the birth mark comes from, and the fields people see.
# The rules document is written from this.
SYSTEMS = {
    "jira": {
        "identifier": ("id", "Jira's issue id. Jira gives it when the issue is created and keeps it through every edit and every move between projects."),
        "birth": ("fields.created", "the field `fields.created`: the creation time Jira states"),
        "refused": [("key", "DEMO-42. It holds the project's key, so it changes when the issue moves to another project."),
                    ("fields.summary", "The title. Anyone can edit it, and two issues can share one."),
                    ("fields.project", "Where the issue lives now. It changes on a move."),
                    ("self", "An address. It holds the site's name, which changes if the site is renamed or moved.")],
        "title": "fields.summary", "container": "fields.project.name", "reference": "key",
    },
    "trello": {
        "identifier": ("id", "Trello's card id. Trello gives it when the card is created and keeps it through every rename and every move between lists and boards. A real one is 24 characters of base 16. That is a description, not a test: an id of another shape is still used as it stands"),
        "birth": ("id", "the first 8 characters of the card `id`, which are the creation time in seconds since 1970, written in base 16. The id carries its own birth. An id that is not 24 characters of base 16 has no birth mark"),
        "refused": [("shortLink", "The short link in the card's address. Stable in practice, and Trello does not promise it as the card's identity."),
                    ("idShort", "The card's number on its board. It is given again when the card moves to another board."),
                    ("name", "The title. Anyone can edit it, and two cards can share one."),
                    ("idBoard, idList", "Where the card is now. Both change on a move."),
                    ("pos", "The card's place in its list. It changes whenever anyone drags a card.")],
        "title": "name", "container": "idBoard", "reference": "shortLink",
    },
    "github": {
        "identifier": ("node_id", "GitHub's global node ID. GitHub gives it when the issue is created. It is case-sensitive."),
        "birth": ("created_at", "the field `created_at`: the creation time GitHub states"),
        "refused": [("number", "The issue's number in its repository. Another repository has its own issue 12, and the number changes on a transfer."),
                    ("title", "Anyone can edit it, and two issues can share one."),
                    ("repository", "Where the issue lives now. It changes on a transfer, and a repository can be renamed."),
                    ("html_url", "An address built from the owner, the repository and the number, all of which can change."),
                    ("id", "A second, numeric id. Also stable, and the node ID is the one GitHub's newer interface uses, so one field was chosen and this one refused, so that no item can get two identities.")],
        "title": "title", "container": "repository.full_name", "reference": "number",
    },
}
NEVER = ["the position of a record in a file or a batch", "the name of the file a record came from", "the order records are processed in", "the time of the sync", "any text a person can edit"]
MAX_LENGTH = 200


class Stop(Exception):
    pass


class Refused(Exception):
    pass


def derive(system, identifier):
    """The identity for one source identifier, or Refused. This is the whole rule, and it looks at nothing else."""
    if system not in SYSTEMS:
        raise Refused("the system is %s, and it must be one of %s" % (json.dumps(system), ", ".join(SYSTEMS)))
    if isinstance(identifier, bool) or identifier is None:
        raise Refused("the record has no %s, the field its identity is built from" % SYSTEMS[system]["identifier"][0])
    if isinstance(identifier, int):
        if identifier < 0:
            raise Refused("the identifier is a negative number")
        identifier = str(identifier)                       # the one conversion allowed: a whole number is written as its digits
    if not isinstance(identifier, str):
        raise Refused("the identifier is %s, which is neither text nor a whole number. It is not repaired" % json.dumps(identifier))
    if identifier == "":
        raise Refused("the identifier is empty")
    if len(identifier) > MAX_LENGTH:
        raise Refused("the identifier is longer than %d characters" % MAX_LENGTH)
    if not re.fullmatch(r"[A-Za-z0-9_\-=+/.]+", identifier):
        raise Refused("the identifier %s holds a space, a colon or another character an identifier may not have. It is not repaired" % json.dumps(identifier))
    return "%s:%s" % (system, identifier)


def dig(record, path):
    value = record
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def utc(value):
    try:
        text = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", re.sub(r"Z$", "+00:00", value))
        moment = datetime.datetime.fromisoformat(text)
        return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if moment.tzinfo else None
    except (TypeError, ValueError):
        return None


def birth_mark(system, record):
    """The moment the source says the item was created, as UTC, or None if the record does not say."""
    if system == "trello":
        card = record.get("id")
        if isinstance(card, str) and re.fullmatch(r"[0-9a-f]{24}", card):
            return datetime.datetime.fromtimestamp(int(card[:8], 16), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return None
    return utc(dig(record, SYSTEMS[system]["birth"][0]))


def seen(system, record):
    """What people see of the item now. Kept beside the identity so that a change can be noticed. Never used to build one."""
    spec = SYSTEMS[system]
    return {"title": dig(record, spec["title"]), "container": dig(record, spec["container"]), "reference": dig(record, spec["reference"])}


# ------------------------------------------------------------------ the map

def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as error:
        raise Stop("%s could not be read: %s" % (os.path.basename(path), error.strerror))
    except ValueError:
        raise Stop("%s is not JSON" % os.path.basename(path))


def load(folder):
    path = os.path.join(folder, "state.json")
    if not os.path.exists(path):
        return {"format": FORMAT, "items": {}, "aliases": {}, "held_aside": [], "collisions": [], "refused": [], "batches": []}
    state = read_json(path)
    if state.get("format") != FORMAT:
        raise Stop("state.json is not in the format %s" % FORMAT)
    return state


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def resolve(state, identity):
    """The identity an identity stands for now: itself, or what an alias points to."""
    hops = 0
    while identity in state["aliases"] and hops < 20:
        identity = state["aliases"][identity]["now"]
        hops += 1
    return identity


def sync(state, batch, say):
    """Applies one batch to the state, in memory. Returns how many things were reported. Decides everything before changing anything."""
    name = batch.get("batch")
    if not isinstance(name, str) or not name:
        raise Stop("the batch has no name")
    if name in state["batches"]:
        raise Stop("the batch %s has been applied already" % name)
    records = batch.get("records")
    if not isinstance(records, list):
        raise Stop("the batch has no list of records")

    derived, reported = [], 0
    for record in records:
        system = record.get("system") if isinstance(record, dict) else None
        source = record.get("record") if isinstance(record, dict) else None
        try:
            if not isinstance(source, dict):
                raise Refused("the record is not an object")
            identity = derive(system, source.get(SYSTEMS[system]["identifier"][0]) if system in SYSTEMS else None)
        except Refused as error:
            shown = json.dumps(dig(source, SYSTEMS[system]["title"])) if system in SYSTEMS and isinstance(source, dict) else "a record"
            state["refused"].append({"batch": name, "system": system, "seen_as": shown, "reason": str(error)})
            say("identity: REFUSED: %s gets no identity: %s" % ("a %s record titled %s" % (system, shown) if system in SYSTEMS else "a record from %s" % json.dumps(system), error))
            reported += 1
            continue
        derived.append((identity, system, source, source.get("previous_identifier")))

    groups = {}
    for entry in derived:
        groups.setdefault(entry[0], []).append(entry)
    for identity in sorted(groups):
        group = groups[identity]
        system, source, previous = group[0][1], group[0][2], group[0][3]
        if len(group) > 1:
            if all(entry[2] == source for entry in group):
                say("identity: NOTE: %s was delivered %d times in the batch, each copy the same in every field. It is applied once" % (identity, len(group)))
            else:
                held = "The item already held under that identity is left as it was" if identity in state["items"] else "Nothing is held under that identity, and nothing is written"
                state["collisions"].append({"batch": name, "identity": identity, "records": len(group), "seen_as": [seen(s, r)["title"] for _, s, r, _ in group]})
                say("identity: COLLISION: %d different records in the batch %s both give the identity %s. Neither is written. %s" % (len(group), name, identity, held))
                reported += 1
                continue
        mark = birth_mark(system, source)
        now = seen(system, source)
        if previous is not None:
            try:
                old = derive(system, previous)
            except Refused as error:
                state["refused"].append({"batch": name, "system": system, "seen_as": json.dumps(now["title"]), "reason": "its previous identifier is not usable: %s" % error})
                say("identity: REFUSED: %s names a previous identifier that is not usable: %s" % (identity, error))
                reported += 1
                continue
            if old == identity:
                pass
            elif old in state["items"] and identity in state["items"]:
                say("identity: NOTE: the source says %s used to be %s, and the map holds an item under each. Nothing is merged. A person must decide" % (identity, old))
            elif old not in state["items"] and old not in state["aliases"]:
                say("identity: NOTE: the source says %s used to be %s, which the map has never held. No alias is made" % (identity, old))
            if old in state["items"] and identity not in state["items"] and old != identity:
                item = state["items"].pop(old)
                item["history"].append({"batch": name, "change": "the source changed its identifier", "from": old, "to": identity})
                item["source_id"] = identity.split(":", 1)[1]
                state["items"][identity] = item
                state["aliases"][old] = {"now": identity, "since": name, "basis": "the source's own record names %s as the identifier it had before" % json.dumps(previous)}
                say("identity: ALIAS: the source says %s is what %s used to be. The old identity now points to the new one, and what was kept under it follows" % (identity, old))
        if identity not in state["items"]:
            state["items"][identity] = {"system": system, "source_id": identity.split(":", 1)[1], "birth_mark": mark,
                                        "birth_basis": SYSTEMS[system]["birth"][1] if mark else None, "now": now, "first_batch": name, "last_batch": name, "history": []}
            say("identity: NEW: %s%s" % (identity, "" if mark else ". Its record gives no creation time, so a later reuse of this identifier could not be told from an update"))
            continue
        item = state["items"][identity]
        if item["birth_mark"] and mark and item["birth_mark"] != mark:
            state["held_aside"].append({"batch": name, "identity": identity, "held_birth_mark": item["birth_mark"], "newcomer_birth_mark": mark, "newcomer": now})
            say("identity: REUSED IDENTIFIER: %s is held by an item created %s, and the batch %s has a record with the same identifier created %s. They are two different items. "
                "The item held is left as it was, and the newcomer is held aside for a person to decide" % (identity, item["birth_mark"], name, mark))
            reported += 1
            continue
        if not item["birth_mark"] or not mark:
            say("identity: NOTE: %s could not be checked for reuse, because %s has no creation time. It is taken to be the same item"
                % (identity, "the record" if not mark else "the item held"))
        changes = []
        for what, word in (("title", "renamed"), ("container", "moved"), ("reference", "its reference changed")):
            if item["now"][what] != now[what]:
                changes.append(word)
                item["history"].append({"batch": name, "change": word, "from": item["now"][what], "to": now[what]})
        item["now"], item["last_batch"] = now, name
        if item["birth_mark"] is None and mark:
            item["birth_mark"], item["birth_basis"] = mark, SYSTEMS[system]["birth"][1]
        say("identity: %s: %s" % ("SAME ITEM, " + " and ".join(changes) if changes else "unchanged", identity))
    state["batches"].append(name)
    return reported


def cell(value):
    return ("`%s`" % json.dumps(value, ensure_ascii=False)).replace("|", "\\|") if value is not None else "none"


def map_document(state):
    items = state["items"]
    by_system = {system: sorted(identity for identity in items if items[identity]["system"] == system) for system in SYSTEMS}
    lines = ["# The identity map", "",
             "Written by `participant/skills/context-stable-identities/identity.py map` from `state.json`. Do not edit this file: the next run replaces it.",
             "**Every item here is made up.** The rules it follows are in `rules.md`.", "",
             "%d source items across %d systems, after the batches: %s." % (len(items), sum(1 for system in SYSTEMS if by_system[system]), ", ".join(state["batches"]) or "none"), "",
             "An identity is the system and the source's own identifier. The title, the place and the reference beside it are what people see **now**. They are shown so that",
             "a reader can find the item. No identity is built from them, and they change without the identity changing.", ""]
    for system in SYSTEMS:
        lines += ["## %s: %d items" % (system, len(by_system[system])), "",
                  "| Source identifier (`%s`) | Local identity | Birth mark | Title now | Lives in now | Reference now | Since first seen |" % SYSTEMS[system]["identifier"][0], "|---|---|---|---|---|---|---|"]
        for identity in by_system[system]:
            item = items[identity]
            words = sorted(set(entry["change"] for entry in item["history"]))
            lines.append("| `%s` | `%s` | %s | %s | %s | %s | %s |" % (item["source_id"], identity, item["birth_mark"] or "not stated", cell(item["now"]["title"]), cell(item["now"]["container"]),
                                                                     cell(item["now"]["reference"]), ", ".join(words) if words else "nothing changed"))
        lines.append("")
    lines += ["## What changed, and what did not", "", "Every change the map has seen. In each row the identity is the same before and after.", "",
              "| Local identity | Batch | Change | From | To |", "|---|---|---|---|---|"]
    rows = ["| `%s` | %s | %s | %s | %s |" % (identity, entry["batch"], entry["change"], cell(entry["from"]), cell(entry["to"]))
            for identity in sorted(items) for entry in items[identity]["history"]]
    lines += rows or ["| none | | | | |"]
    lines += ["", "## Aliases", "", "An identity the source itself replaced. The old identity still resolves, to the new one."]
    lines += [""] + (["| Old identity | Now | Since | On what basis |", "|---|---|---|---|"] + ["| `%s` | `%s` | %s | %s |" % (old, alias["now"], alias["since"], alias["basis"])
                                                                                         for old, alias in sorted(state["aliases"].items())] if state["aliases"] else ["None."])
    lines += ["", "## Reported, and not written", "", "### Reused identifiers", "", "A record whose identifier is held by an item with a different birth mark. The item held was left as it was."]
    lines += [""] + (["| Identity | Batch | The item held was created | The newcomer was created | The newcomer's title |", "|---|---|---|---|---|"] +
                     ["| `%s` | %s | %s | %s | %s |" % (one["identity"], one["batch"], one["held_birth_mark"], one["newcomer_birth_mark"], cell(one["newcomer"]["title"])) for one in state["held_aside"]]
                     if state["held_aside"] else ["None."])
    lines += ["", "### Collisions", "", "Two different records in one batch that give the same identity. Neither was written."]
    lines += [""] + (["| Identity | Batch | Records | Their titles |", "|---|---|---|---|"] +
                     ["| `%s` | %s | %d | %s |" % (one["identity"], one["batch"], one["records"], ", ".join(cell(title) for title in one["seen_as"])) for one in state["collisions"]]
                     if state["collisions"] else ["None."])
    lines += ["", "### Refused", "", "A record that could not be given an identity. Its identifier was not repaired."]
    lines += [""] + (["| Batch | System | Title | Why |", "|---|---|---|---|"] + ["| %s | %s | %s | %s |" % (one["batch"], one["system"], "`%s`" % one["seen_as"].replace("|", "\\|"), one["reason"].replace("|", "\\|"))
                                                                              for one in state["refused"]] if state["refused"] else ["None."])
    return "\n".join(lines) + "\n"


def rules_document():
    lines = ["# Identity rules: how a work item gets a local identity", "",
             "Written by an AI assistant (Claude) at the participant's direction, for the quest `context-stable-identities`. This whole document is written out by",
             "`participant/skills/context-stable-identities/identity.py rules`. Its tables come from the same tables the code applies. Its sentences are text in that file, and",
             "it is the tests that hold the code to them.", "",
             "These rules are meant to be followed by hand. Given a source record and this page, two people should write down the same identity.", "",
             "## 1. What an identity is", "", "    SYSTEM:IDENTIFIER", "",
             "- **SYSTEM** is one of three words, exactly as written here, in lower case: " + ", ".join("`%s`" % system for system in SYSTEMS) + ". A record from any other system,",
             "  or whose system is written another way such as `Jira`, gets no identity. These rules do not cover it, and nothing is made up for it.",
             "- **IDENTIFIER** is the value of one field of the source record, the one in the table below. It is the field the source system itself promises never to change.",
             "  The field is at the top level of the record: Jira's `id` is the issue's own `id`, not the `id` of its project or of anything else inside it.",
             "- Between them is one colon. Nothing else is in an identity.", "",
             "| System | The identifier is the field | Why this field | Example |", "|---|---|---|---|",
             "| `jira` | `id` | %s | `jira:40003` |" % SYSTEMS["jira"]["identifier"][1],
             "| `trello` | `id` | %s | `trello:6ae851100000000000000a02` |" % SYSTEMS["trello"]["identifier"][1],
             "| `github` | `node_id` | %s | `github:I_kwFIX0303` |" % SYSTEMS["github"]["identifier"][1], "",
             "## 2. Writing the identifier down", "",
             "1. **If the identifier is text, use it character for character.** Do not change upper or lower case. Do not remove or add anything. `I_kwAB` and `I_kwab` are two",
             "   different items. Text is never read as a number: the text `\"0040003\"` gives `jira:0040003`, and the text `\"40003.0\"` gives `jira:40003.0`.",
             "2. **One conversion is allowed.** If the record has the identifier as a whole number that is zero or more, such as `40003`, write its digits: `40003`. So the number",
             "   `40003` and the text `\"40003\"` give the same identity.",
             "3. **Refuse everything else. Do not repair it.** A record gets no identity, and is reported, if its identifier is:",
             "   - missing, or `null`;",
             "   - a number with a fraction or an exponent, such as `40003.5`, `40003.0` or `4e4`, or a negative number;",
             "   - `true` or `false`, a list, or an object;",
             "   - empty text, or text longer than %d characters;" % MAX_LENGTH,
             "   - text holding any character other than the letters `A` to `Z` and `a` to `z`, the digits `0` to `9`, and `_ - = + / .`. So no space, no colon, and no accented",
             "     or non-Latin letter.",
             "",
             "   Trimming a space or dropping a `.0` would be a guess about which item was meant.", "",
             "**Text or number?** A source record is JSON. A value written inside double quotes is text. A value written without them is a number, `true`, `false` or `null`.",
             "That is the only test. The text `\"-7\"` is an identifier, and the number `-7` is refused. The text forms are accepted as they stand, because text is never read for",
             "what it might mean.", "",
             "**Which system?** The system is not a field of the source record. It is which system's sync delivered the record, and a batch states it beside each record.", "",
             "A record that gets no identity is called **refused** below, whether its identifier was refused or its system is not one of the three.", "",
             "## 3. What an identity is never built from", "", "For each system, the fields that look like an identity and are refused:", ""]
    for system in SYSTEMS:
        lines += ["**%s**" % system, "", "| Field | Why it is refused |", "|---|---|"] + ["| `%s` | %s |" % row for row in SYSTEMS[system]["refused"]] + [""]
    lines += ["And for every system, never:", ""] + ["- %s" % one for one in NEVER]
    lines += ["", "The map shows an item's title, where it lives and its reference, beside its identity. That is so a reader can find the item. They are what is true **now**, they are",
              "expected to change, and no identity is worked out from them.", "",
              "## 4. A record whose identity is already held", "",
              "Beside each identity the map keeps a **birth mark**: the moment the source says the item was created, in UTC. It is not part of the identity.", "",
              "| System | The birth mark is |", "|---|---|"] + ["| `%s` | %s |" % (system, SYSTEMS[system]["birth"][1]) for system in SYSTEMS]
    lines += ["", "A birth mark is a moment, not a piece of text. `2026-11-06T09:00:00.000+0000` and `2026-11-06T04:00:00-05:00` are the same moment and the same birth mark.", "",
              "A **batch** is the set of records one sync delivered together, in one file. The map is built by applying batches one after another.", "",
              "When a record arrives whose identity is already in the map **from an earlier batch**, compare birth marks. **Do not compare titles.** (Two records with one identity",
              "inside the **same** batch are a different matter: see section 6.)", "",
              "| What is found | What it is | What is done |", "|---|---|---|",
              "| The same birth mark | **The same item**, perhaps renamed or moved | It is updated in place. Each change of title, place or reference is recorded. The identity does not change |",
              "| A different birth mark | **The source reused the identifier** for another item | It is reported. The item held is left exactly as it was. The newcomer is held aside for a person to decide |",
              "| No birth mark on one side, or on both | Cannot be told | It is taken to be the same item, and the run says that reuse could not be checked |", "",
              "## 5. When a source reuses an identifier", "",
              "A source system promises not to. Some break the promise: after a restore from a backup, after a project is deleted and made again, or when two installations are",
              "merged. When a different birth mark shows it has happened:", "",
              "1. **Nothing is overwritten.** The item already held keeps its identity, its record and whatever is attached to it.",
              "2. **The newcomer gets no identity yet.** It is held aside, with both birth marks, and listed in the map under \"Reused identifiers\".",
              "3. **A person decides.** Either the old item is gone at the source and should be retired, or the two are separate and the newcomer needs an identity that says so.",
              "   The skill does neither by itself, because either choice discards or renames something a person may depend on.", "",
              "**For Trello this check has nothing to work with.** A card's birth mark is taken from its id. A reused id carries the same birth mark, so it looks like the same card.",
              "Reuse of a Trello card id cannot be detected by these rules.", "",
              "## 6. Two records in one batch with the same identity", "",
              "A **collision**. If the records are the same in every field, it is one record delivered twice, and it is applied once. If they differ in any field, nobody can say which is",
              "right. It is reported, **neither is written**, and the item already held under that identity, if there is one, is left as it was.", "",
              "## 7. When a source changes an identifier", "",
              "If the source's own record states the identifier the item had before, in the field `previous_identifier`, the old identity becomes an **alias** of the new one: it still",
              "resolves, to the new identity, and what was kept under it follows. An alias is made only on the source's own statement. It is never worked out from a title that matches.", "",
              "- `previous_identifier` is a field at the top level of the record. If it is absent or `null`, the source states no previous identifier, and this section does not apply.",
              "- Otherwise it is written down by section 2, like any other identifier. If it is refused, the record is refused.",
              "- If the map has never held the previous identity, no alias is made, and the record is simply a new item. The run says so.",
              "- If the map holds an item under the old identity **and** one under the new, nothing is merged. The run says so, and a person decides.", "",
              "## 8. Deriving an identity by hand", "",
              "1. Which system is the record from? Write its word: `jira`, `trello` or `github`. If it is none of these, stop: the record has no identity.",
              "2. Find the one field in the table of section 1. For the identity, ignore every other field. (The creation time is read for the birth mark, and `previous_identifier`",
              "   for an alias. Neither goes into the identity.)",
              "3. Apply section 2. If the identifier is refused, stop: the record has no identity.",
              "4. Write the system, a colon, and the identifier.", "",
              "The order of the records, the file they are in, and their titles play no part. Two records with the same title get two identities. One record, renamed and moved,",
              "gets the identity it always had."]
    return "\n".join(lines) + "\n"


def main(argv=None, say=print):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("derive", "sync", "map", "rules", "export", "import"))
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--folder", default=FOLDER)
    parser.add_argument("--batch")
    parser.add_argument("--out")
    parser.add_argument("--from", dest="source")
    args = parser.parse_args(argv)
    try:
        if args.command == "derive":
            if len(args.rest) != 2:
                raise Stop("derive needs a system and an identifier")
            try:
                say(derive(args.rest[0], args.rest[1]))
                return 0
            except Refused as error:
                say("identity: REFUSED: %s" % error)
                return 3
        if args.command == "rules":
            if not args.out:
                raise Stop("rules needs --out FILE")
            write(args.out, rules_document())
            say("identity: wrote the rules")
            return 0
        if args.command == "import":
            if not args.source:
                raise Stop("import needs --from FILE")
            if os.path.exists(os.path.join(args.folder, "state.json")):
                raise Stop("that folder already holds a map. Import starts a new one and does not merge")
            state = read_json(args.source)
            if state.get("format") != FORMAT:
                raise Stop("that file is not an exported map")
            write(os.path.join(args.folder, "state.json"), json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            write(os.path.join(args.folder, "map.md"), map_document(state))
            say("identity: imported %d identities and %d aliases" % (len(state["items"]), len(state["aliases"])))
            return 0
        state = load(args.folder)
        if args.command == "export":
            if not args.out:
                raise Stop("export needs --out FILE")
            write(args.out, json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            say("identity: exported %d identities and %d aliases" % (len(state["items"]), len(state["aliases"])))
            return 0
        reported = 0
        if args.command == "sync":
            if not args.batch:
                raise Stop("sync needs --batch FILE")
            before = len(state["items"])
            reported = sync(state, read_json(args.batch), say)
            write(os.path.join(args.folder, "state.json"), json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            say("identity: batch %s applied. Identities held before: %d. Now: %d. Reported: %d" % (state["batches"][-1], before, len(state["items"]), reported))
        write(os.path.join(args.folder, "map.md"), map_document(state))
        return 3 if reported else 0
    except Stop as error:
        say("identity: STOPPED: %s" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())

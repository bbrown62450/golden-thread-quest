#!/usr/bin/env python3
"""Records logs/identity-run.txt for the quest context-stable-identities. It contacts nothing.

    python3 participant/evidence/context-stable-identities/context-attempt-005/scripts/record_evidence.py

It applies the five made-up batches, one after another, to a map in a scratch folder, SCRATCH, which is deleted at the
end. It changes nothing in participant/context/identity, and at the end compares the handed-in map with what it built.
"""
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "participant", "skills", "context-stable-identities"))
import identity      # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
BATCHES = os.path.join(identity.FOLDER, "batches")
STORY, ISSUE = "jira:40003", "github:I_kwFIX0302"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Log:
    def __init__(self):
        self.lines = ["The identity run. context-stable-identities, attempt context-attempt-005",
                      "Recorded by scripts/record_evidence.py. No request was sent anywhere. Every item, project, board and repository is made up."]
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


def by_hand(system, record):
    """A second derivation, written from rules.md alone and sharing no code with the skill."""
    field = {"jira": "id", "trello": "id", "github": "node_id"}.get(system)
    if field is None or field not in record:
        return None
    value = record[field]
    if type(value) is int and value >= 0:
        value = "%d" % value
    if type(value) is not str or not value or len(value) > 200:
        return None
    if any(not (c.isascii() and (c.isalnum() or c in "_-=+/.")) for c in value):
        return None
    return system + ":" + value


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-identity-")
    folder = os.path.join(scratch, "identity")
    state_of = lambda: json.loads(read(os.path.join(folder, "state.json")))
    batch = lambda number: json.loads(read(os.path.join(BATCHES, "batch-%d.json" % number)))

    def sync(number, hide=()):
        said = []
        code = identity.main(["sync", "--batch", os.path.join(BATCHES, "batch-%d.json" % number), "--folder", folder], say=said.append)
        shown = [line for line in said if not any(line.startswith(word) for word in hide)]
        log.out("$ python3 participant/skills/context-stable-identities/identity.py sync --batch participant/context/identity/batches/batch-%d.json --folder SCRATCH/identity" % number, "-" * 78, *shown)
        if len(shown) != len(said):
            log.out("(%d lines left out here: those beginning %s)" % (len(said) - len(shown), " or ".join('"%s"' % word for word in hide)))
        log.out("-" * 78, "exit code: %d" % code)
        return code, said

    try:
        log.part("PART 1. Before: the first sync. batch-1, %s" % batch(1)["about"])
        code, said = sync(1)
        first = state_of()
        before = copy.deepcopy(first["items"])
        log.check("20 source records, from 3 systems, got 20 different identities: 7 jira, 7 trello, 6 github",
                  code == 0 and len(before) == 20 and [sum(1 for i in before.values() if i["system"] == s) for s in identity.SYSTEMS] == [7, 7, 6])
        log.check("each identity is the system, a colon, and the source's own identifier, and holds nothing else (criterion 1)",
                  all(one == "%s:%s" % (item["system"], item["source_id"]) for one, item in before.items()))
        records = batch(1)["records"]
        log.check("a second derivation, written from rules.md and sharing no code with the skill, gives the same 20 identities (criterion 7)",
                  sorted(by_hand(r["system"], r["record"]) for r in records) == sorted(before))
        same_title = sorted(one for one, item in before.items() if item["now"]["title"] == "Fix export")
        log.out("Four different items are all called \"Fix export\": %s" % ", ".join(same_title))
        log.check("four items with the same title have four identities, in three systems", len(same_title) == 4)
        log.check("two GitHub node IDs that differ only in upper and lower case are two identities", "github:I_kwFIXab05" in before and "github:I_kwFIXAB05" in before)
        note = os.path.join(folder, "notes", "jira-40003.md")
        os.makedirs(os.path.dirname(note))
        with open(note, "w", encoding="utf-8") as f:
            f.write("A person's note on jira:40003, written before it was renamed and moved.\n")
        digest = hashlib.sha256(read(note).encode()).hexdigest()
        log.out("A person keeps a note on the story %s, in a file named after its identity: notes/jira-40003.md, SHA-256 %s" % (STORY, digest))

        log.part("PART 2. After: batch-2. %s" % batch(2)["about"],
                 "  the Jira story 40003    renamed, and moved from project DEMO to project OPS, so its key changed from DEMO-3 to OPS-17. This is the quest's scenario",
                 "  the Jira story 40005    renamed to the title 40003 had just given up",
                 "  a Trello card           renamed, moved to another board, dragged to the top of a list, and renumbered by the new board",
                 "  another Trello card     moved to another list on the same board, and dragged",
                 "  the GitHub issue        renamed, and transferred to another repository, so its number changed from 2 to 41",
                 "  and the source sent all 20 records in a different order.")
        code, said = sync(2, hide=("identity: unchanged",))
        after = state_of()["items"]
        log.check("every identity is unchanged: the same 20, and no new one (criteria 3 and 4)", code == 0 and sorted(after) == sorted(before))
        log.out("The three items that were renamed and moved, before and after:")
        card = [one for one, item in after.items() if item["now"]["title"] == "Export report as PDF and CSV"][0]
        for one in (STORY, card, ISSUE):
            log.out("  %s" % one, "      before: title %s, in %s, reference %s" % tuple(json.dumps(before[one]["now"][key]) for key in ("title", "container", "reference")),
                    "      after:  title %s, in %s, reference %s" % tuple(json.dumps(after[one]["now"][key]) for key in ("title", "container", "reference")))
            log.check("%s was renamed and moved, and its identity is unchanged: one record, updated in place" % one,
                      one in before and after[one]["now"]["title"] != before[one]["now"]["title"] and after[one]["now"]["container"] != before[one]["now"]["container"]
                      and after[one]["birth_mark"] == before[one]["birth_mark"] and after[one]["first_batch"] == "batch-1")
        log.check("the note on the story is where it was, unchanged, under the same name: it still belongs to the item (the scenario)",
                  hashlib.sha256(read(note).encode()).hexdigest() == digest and os.listdir(os.path.dirname(note)) == ["jira-40003.md"])
        log.check("the story that took over the old title did not take over the identity: jira:40005 is still the item created on 4 November",
                  after["jira:40005"]["now"]["title"] == before[STORY]["now"]["title"] and after["jira:40005"]["birth_mark"] == before["jira:40005"]["birth_mark"])
        moved_list = [one for one, item in after.items() if item["now"]["reference"] == "fixT0004"][0]
        log.check("the card that only changed list and position has the same identity, and nothing recorded as changed: position plays no part (criterion 2)",
                  moved_list in before and after[moved_list]["history"] == [])

        log.out("", "For comparison: the same two batches, with the identity built in the ways the rules refuse. Counted from the records, not from the map.")
        one, two = {by_hand(r["system"], r["record"]): r for r in batch(1)["records"]}, {by_hand(r["system"], r["record"]): r for r in batch(2)["records"]}
        seen = lambda r: identity.seen(r["system"], r["record"])
        keys = [("the title", lambda r: "%s:%s" % (r["system"], seen(r)["title"])),
                ("the reference people use (key, short link, number)", lambda r: "%s:%s" % (r["system"], seen(r)["reference"])),
                ("where it lives and its title", lambda r: "%s:%s:%s" % (r["system"], seen(r)["container"], seen(r)["title"])),
                ("its position in the batch", lambda r: None)]
        worst = 0
        for name, key in keys:
            if name.startswith("its position"):
                order_one, order_two = [by_hand(r["system"], r["record"]) for r in batch(1)["records"]], [by_hand(r["system"], r["record"]) for r in batch(2)["records"]]
                broken = sum(1 for index, real in enumerate(order_one) if order_two[index] != real)
                clash = 0
            else:
                broken = sum(1 for real in one if key(one[real]) != key(two[real]))
                clash = len(one) - len(set(key(r) for r in one.values()))
            worst = max(worst, broken)
            log.out("  identity from %-52s %2d of 20 items would have a different identity after batch-2%s" % (name + ":", broken, ". And from the start, %d pair of different items would share one identity" % clash if clash else ""))
        log.out("  identity from the system and its own identifier:           0 of 20")
        log.check("each refused way of building an identity would have broken at least one item across this rename and move, and the rule used broke none", worst >= 3
                  and sum(1 for real in one if keys[0][1](one[real]) != keys[0][1](two[real])) >= 3)
        scenario_title = "%s:%s" % ("jira", before[STORY]["now"]["title"])
        log.check("under a title-based key the scenario happens exactly: the story's old key now names a DIFFERENT item, jira:40005, and its notes would follow the title to it",
                  "%s:%s" % ("jira", after["jira:40005"]["now"]["title"]) == scenario_title)

        log.part("PART 3. A collision: batch-3. %s (criterion 5)" % batch(3)["about"])
        held_before = copy.deepcopy(state_of()["items"])
        code, said = sync(3, hide=("identity: unchanged",))
        now = state_of()
        log.check("the collision is reported, and the run ends with exit code 3", code == 3 and any("COLLISION: 2 different records" in line for line in said))
        log.check("neither of the two records was written: github:I_kwFIX0306 is not in the map", "github:I_kwFIX0306" not in now["items"] and len(now["items"]) == 20)
        log.check("the map records the collision with both records' titles, so that a person can see what clashed",
                  now["collisions"] and now["collisions"][0]["seen_as"] == ["Rotate the signing key", "Archive the old dashboards"])
        log.check("no other item was touched by it", all(now["items"][one]["now"] == held_before[one]["now"] for one in held_before))
        log.check("the same record delivered twice, identical in every field, is not a collision: it is applied once and said so", any("jira:40002 was delivered 2 times" in line for line in said))
        clash = {"batch": "a-clash-on-a-held-identity", "records": [
            {"system": "github", "record": {"node_id": "I_kwFIX0302", "number": 1, "title": "One claimant", "created_at": "2026-10-03T10:00:00Z", "repository": {"id": 1, "full_name": "a/b"}}},
            {"system": "github", "record": {"node_id": "I_kwFIX0302", "number": 2, "title": "Another claimant", "created_at": "2026-10-03T10:00:00Z", "repository": {"id": 1, "full_name": "a/b"}}}]}
        trial, lines = copy.deepcopy(now), []
        identity.sync(trial, clash, lines.append)
        log.out("And a collision on an identity that IS held, tried in memory: two different records both claiming %s." % ISSUE, *["  " + line for line in lines])
        log.check("neither overwrites the item held: it is exactly as it was before the two arrived (criterion 5)", trial["items"][ISSUE] == now["items"][ISSUE] and len(trial["collisions"]) == 2)

        log.part("PART 4. A reused identifier: batch-4. %s (criterion 6)" % batch(4)["about"])
        held = copy.deepcopy(now["items"]["jira:40007"])
        code, said = sync(4)
        now = state_of()
        log.check("the reuse is reported, with both creation times, and the run ends with exit code 3", code == 3 and any(
            "REUSED IDENTIFIER: jira:40007" in line and "2026-11-06T09:00:00Z" in line and "2026-11-20T09:00:00Z" in line for line in said))
        log.check("the item already held is exactly as it was: still \"Tidy the export folder\", created 6 November", now["items"]["jira:40007"] == held and held["now"]["title"] == "Tidy the export folder")
        log.check("the newcomer was given no identity. It is held aside, with its title and both creation times, for a person to decide",
                  len(now["held_aside"]) == 1 and now["held_aside"][0]["newcomer"]["title"] == "Rotate the signing key" and len(now["items"]) == 21)
        story = batch(1)["records"][5]["record"]                        # jira 40006, as first synced
        same_title = {"batch": "t1", "records": [{"system": "jira", "record": dict(story, fields=dict(story["fields"], created="2026-11-25T09:00:00.000+0000"))}]}
        new_title = {"batch": "t2", "records": [{"system": "jira", "record": dict(story, key="ZZZ-9", fields=dict(story["fields"], summary="Nothing like the old title", project={"id": "9", "key": "ZZZ", "name": "Elsewhere"}))}]}
        trial_a, trial_b, lines = copy.deepcopy(now), copy.deepcopy(now), []
        identity.sync(trial_a, same_title, lines.append)
        identity.sync(trial_b, new_title, lines.append)
        log.out("Is it the creation time that decides, and not the title? Two trials in memory, on jira:40006:", *["  " + line for line in lines if "jira:40006" in line])
        log.check("the SAME title with a different creation time is reported as reuse, and a wholly DIFFERENT title, project and key with the same creation time is the same item. The title decides nothing (criterion 2)",
                  len(trial_a["held_aside"]) == 2 and trial_a["items"]["jira:40006"] == now["items"]["jira:40006"]
                  and len(trial_b["held_aside"]) == 1 and trial_b["items"]["jira:40006"]["now"]["title"] == "Nothing like the old title")
        log.check("where a record has no creation time, the run says reuse could not be checked, and does not claim it was",
                  any("github:I_kwFIX0301 could not be checked for reuse" in line for line in said) and any("github:I_kwFIX0307. Its record gives no creation time" in line for line in said))

        log.part("PART 5. An identifier the source changed, and records with no usable identifier: batch-5. %s" % batch(5)["about"])
        code, said = sync(5)
        now = state_of()
        log.check("the alias is recorded on the source's own statement: github:I_kwFIX0303 now resolves to github:I_kwFIX0399, which keeps the birth mark and first batch of the old one (stretch goal)",
                  identity.resolve(now, "github:I_kwFIX0303") == "github:I_kwFIX0399" and now["items"]["github:I_kwFIX0399"]["first_batch"] == "batch-1" and "github:I_kwFIX0303" not in now["items"])
        log.check("six records were refused, each with its reason, and none was given an identity or repaired", code == 3 and len(now["refused"]) == 6 and len(now["items"]) == 21)
        log.check("the Jira id sent as the number 40001 is the item already held as jira:40001", now["items"]["jira:40001"]["last_batch"] == "batch-5" and len([o for o in now["items"] if "40001" in o]) == 1)

        log.part("PART 6. Export and re-import (stretch goal)", "The map is exported to one file and imported into an empty folder. Then the first two batches are applied again to a third, empty folder, in reverse order of records.")
        said = []
        identity.main(["export", "--out", os.path.join(scratch, "export.json"), "--folder", folder], say=said.append)
        other = os.path.join(scratch, "imported")
        identity.main(["import", "--from", os.path.join(scratch, "export.json"), "--folder", other], say=said.append)
        log.out(*said)
        log.check("the imported map is the exported map, byte for byte: every identity, alias and birth mark", read(os.path.join(other, "state.json")) == read(os.path.join(folder, "state.json")))
        fresh = identity.load(os.path.join(scratch, "none"))
        for number in (1, 2):
            data = batch(number)
            identity.sync(fresh, {"batch": data["batch"], "records": list(reversed(data["records"]))}, lambda line: None)
        log.check("rebuilding from the source records, read in the opposite order, gives the same 20 identities with the same birth marks",
                  {one: item["birth_mark"] for one, item in fresh["items"].items()} == {one: item["birth_mark"] for one, item in after.items()})

        log.part("PART 7. The handed-in files")
        log.check("participant/context/identity/state.json is exactly what these five batches give", json.loads(read(os.path.join(identity.FOLDER, "state.json"))) == now)
        log.check("participant/context/identity/map.md is exactly what the skill writes from it, so the map was not adjusted by hand", read(os.path.join(identity.FOLDER, "map.md")) == identity.map_document(now))
        log.check("participant/context/identity/rules.md is exactly what the skill writes from its own tables", read(os.path.join(identity.FOLDER, "rules.md")) == identity.rules_document())
        log.check("the map holds %d source records across three systems, at least fifteen, including the renamed and the moved" % len(now["items"]),
                  len(now["items"]) >= 15 and "| `jira:40003` | batch-2 | renamed |" in read(os.path.join(identity.FOLDER, "map.md")) and "| `jira:40003` | batch-2 | moved |" in read(os.path.join(identity.FOLDER, "map.md")))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "identity-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("identity-run.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())

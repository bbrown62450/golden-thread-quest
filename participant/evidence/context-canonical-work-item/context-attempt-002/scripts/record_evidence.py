#!/usr/bin/env python3
"""Records the evidence for the quest context-canonical-work-item. It contacts nothing.

    python3 participant/evidence/context-canonical-work-item/context-attempt-002/scripts/record_evidence.py

It writes three logs beside it, in ../logs:

    identity-check.txt   made-up saved work is normalized, then renamed and moved at the source, and normalized again
    unmappable.txt       items the model cannot represent: the real ones in the saved work, and made-up ones, case by case
    apply-run.txt        the model applied to the work saved in this repository, twice

and it applies the model to participant/context, which rewrites participant/context/model/items and report.md only if
something changed. The made-up runs happen in a scratch folder that is deleted at the end.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "context-work-item-model")
sys.path.insert(0, SKILL)
import fixtures      # noqa: E402
import normalize     # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
CONTEXT = os.path.join(REPO, "participant", "context")
MODEL = os.path.join(CONTEXT, "model")
CARD, ISSUE, STORY = "trello:62cfix000000000000000c02", "github:I_kwFIX0102", "jira:30003"


class Log:
    def __init__(self, title, about):
        self.lines, self.failed, self.count = [title, "Recorded by scripts/record_evidence.py. No request was sent anywhere.", about], [], 0

    def out(self, *lines):
        self.lines.extend(lines or [""])

    def part(self, title, *lines):
        self.lines += ["", "=" * 78, title, *lines]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %s %s" % ("ok  " if ok else "FAIL", label))
        if not ok:
            self.failed.append(label)

    def save(self, name):
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.failed), self.count) if self.failed else "ALL CHECKS PASSED. %d checks." % self.count)]
        os.makedirs(LOGS, exist_ok=True)
        with open(os.path.join(LOGS, name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.failed:
            print("  FAILED: %s" % label)
        return not self.failed


def read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def tree(folder):
    """A checksum of every file under a folder, by its path."""
    found = {}
    for base, _, names in os.walk(folder):
        for name in names:
            found[os.path.relpath(os.path.join(base, name), folder)] = hashlib.sha256(read(os.path.join(base, name), "rb")).hexdigest()
    return found


def run(log, root, out, command, hide=()):
    said = []
    try:
        result = normalize.normalize(root, out, os.path.join(out, "mappings", "status-map.json"), say=said.append)
    except normalize.Stop as error:
        result, said = None, said + ["work-item-model: STOPPED: %s" % error]
    shown = [line for line in said if not any(word in line for word in hide)]
    log.out("$ %s" % command, "-" * 78, *shown)
    if len(shown) != len(said):
        log.out("(%d lines of this output are left out here: %s)" % (len(said) - len(shown), " and ".join("those with %s" % word.strip() for word in hide)))
    log.out("-" * 78)
    return result, said


def item(out, identity):
    return normalize.parse(read(os.path.join(out, "items", normalize.file_name(identity))))


def records(out):
    return sorted(name for name in os.listdir(os.path.join(out, "items")) if name.endswith(".md"))


def identity_check(scratch):
    log = Log("Does an item keep its identity when it is renamed and moved? context-canonical-work-item, attempt context-attempt-002",
              "The saved work here is made up, by fixtures.py: 5 Jira stories, 5 Trello cards and 5 GitHub issues, with every field the model requires. SCRATCH is a scratch folder.")
    root, out = os.path.join(scratch, "context"), os.path.join(scratch, "model")
    fixtures.build(root, 1)
    fixtures.write_map(os.path.join(out, "mappings", "status-map.json"))
    command = "python3 participant/skills/context-work-item-model/normalize.py --root SCRATCH/context --out SCRATCH/model"

    log.part("PART 1. The saved work is normalized for the first time")
    first, _ = run(log, root, out, command)
    log.check("14 canonical records were written, one for each item that can be mapped", len(first["good"]) == 14 and len(records(out)) == 14)
    before = {identity: item(out, identity) for identity in (STORY, CARD, ISSUE)}
    files_before = dict(first["files"])
    log.out("The three items that are about to change, as they are now:")
    for identity in (STORY, CARD, ISSUE):
        canonical, provenance, _ = before[identity]
        log.out("  %-34s file items/%s" % (identity, files_before[identity]),
                "      title %s" % json.dumps(canonical["title"]), "      reference %s, in the %s %s, status %s" % (
                    provenance["source_reference"], canonical["container"]["kind"], json.dumps(canonical["container"]["name"]), canonical["status"]))

    log.part("PART 2. A person writes a note on each of the three items", "Notes go in SCRATCH/model/notes, in a file with the same name as the item's record.")
    notes = {}
    for identity in (STORY, CARD, ISSUE):
        path = os.path.join(out, "notes", normalize.file_name(identity))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("My own note on %s.\nWritten before the item was renamed and moved.\n" % identity)
        notes[identity] = hashlib.sha256(read(path, "rb")).hexdigest()
        log.out("  notes/%s  SHA-256 %s" % (normalize.file_name(identity), notes[identity]))

    log.part("PART 3. At the source, each of the three is RENAMED and MOVED. The saved work is synced again, and normalized again (criterion 10)",
             "  the Jira story    renamed, moved from project DEMO to project OPS (so its key changes from DEMO-3 to OPS-17), and its status goes to Done",
             "  the Trello card   renamed, moved from the list Doing on Fixture Board to the list Done on Other Board",
             "  the GitHub issue  renamed, transferred from acme-fixture/platform (#2) to acme-fixture/support (#41)",
             "The later sync also re-read everything else, so the other items have a later retrieval time and nothing else new.")
    fixtures.build(root, 2)
    second, _ = run(log, root, out, command)
    after = {identity: item(out, identity) for identity in (STORY, CARD, ISSUE)}
    log.out("The three items, as they are now:")
    for identity in (STORY, CARD, ISSUE):
        canonical, provenance, _ = after[identity]
        log.out("  %-34s file items/%s" % (identity, second["files"][identity]),
                "      title %s" % json.dumps(canonical["title"]), "      reference %s, in the %s %s, status %s" % (
                    provenance["source_reference"], canonical["container"]["kind"], json.dumps(canonical["container"]["name"]), canonical["status"]))
    updated = dict(second["changes"]["updated"])
    log.check("no new record was made: 0 new, and still 14 record files", second["changes"]["new"] == [] and len(records(out)) == 14)
    log.check("the set of identities is exactly what it was", sorted(second["good"]) == sorted(first["good"]))
    for identity, what in ((STORY, "Jira story"), (CARD, "Trello card"), (ISSUE, "GitHub issue")):
        log.check("the %s kept its identity, %s, and its record was updated in place, in the same file" % (what, identity),
                  after[identity][0]["identity"] == identity and second["files"][identity] == files_before[identity] and identity in updated)
        log.check("  its title, its container and its reference all changed in that one record",
                  after[identity][0]["title"] != before[identity][0]["title"] and after[identity][0]["container"] != before[identity][0]["container"]
                  and {"title", "container"} <= set(updated[identity])
                  and (identity == CARD or after[identity][1]["source_reference"] != before[identity][1]["source_reference"]))
    log.check("the Jira story's key changed, DEMO-3 to OPS-17, and the GitHub issue's number and repository changed, and neither is part of an identity",
              (before[STORY][1]["source_reference"], after[STORY][1]["source_reference"]) == ("DEMO-3", "OPS-17")
              and after[ISSUE][1]["source_reference"] == "acme-fixture/support#41" and after[ISSUE][2]["github.earlier_references"] == ["acme-fixture/platform#2"])
    log.check("the moves changed status where the source or the status map says so: the story and the card are now done, and the issue is still open",
              (after[STORY][0]["status"], after[CARD][0]["status"], after[ISSUE][0]["status"]) == ("done", "done", "open"))
    naive = lambda parts: "%s:%s" % (parts[0]["system"], parts[1]["source_reference"])
    twice = [identity for identity in (STORY, ISSUE) if naive(before[identity]) != naive(after[identity])]
    by_title = [identity for identity in (STORY, CARD, ISSUE) if before[identity][0]["title"] != after[identity][0]["title"]]
    log.out("For comparison, what other choices of identity would have done with this same change:",
            "  identity from the key or number:  %s  ->  %s      and  %s  ->  %s" % (naive(before[STORY]), naive(after[STORY]), naive(before[ISSUE]), naive(after[ISSUE])),
            "  identity from the title:          all three titles changed")
    log.check("an identity made from the key or number would have made 2 second records, and one made from the title 3. The stable identifier made none",
              len(twice) == 2 and len(by_title) == 3)

    log.part("PART 4. Nothing changes at the source. Normalized a third time")
    snapshot = tree(out)
    third, _ = run(log, root, out, command)
    log.check("nothing was written: 0 new, 0 updated, 14 unchanged", third["writes"] == [] and len(third["changes"]["unchanged"]) == 14)
    log.check("every file in the model folder is byte for byte what it was before this run", tree(out) == snapshot)

    log.part("PART 5. The notes (criterion 7)")
    for identity in (STORY, CARD, ISSUE):
        now = hashlib.sha256(read(os.path.join(out, "notes", normalize.file_name(identity)), "rb")).hexdigest()
        log.out("  notes/%s  SHA-256 %s" % (normalize.file_name(identity), now))
        log.check("the note on %s is unchanged after three runs and a rename and move, and still has the name of the item's record" % identity,
                  now == notes[identity] and third["files"][identity] == normalize.file_name(identity))
    log.check("the notes folder holds those three files and nothing normalization put there", sorted(os.listdir(os.path.join(out, "notes"))) == sorted(normalize.file_name(i) for i in notes))

    log.part("PART 6. A record is found by the identity written inside it, not by its file's name (criterion 2)",
             "A person renames the card's record file to my-favourite-card.md. The card is then renamed once more at the source, and normalized.")
    os.rename(os.path.join(out, "items", normalize.file_name(CARD)), os.path.join(out, "items", "my-favourite-card.md"))
    data = json.loads(read(os.path.join(root, "trello", "assigned", "assigned.json")))
    data["cards"][CARD.split(":")[1]]["name"] = "Export report as PDF, CSV and JSON"
    with open(os.path.join(root, "trello", "assigned", "assigned.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)
    fourth, _ = run(log, root, out, command)
    log.check("the record was found in my-favourite-card.md and updated there. No file with the old name came back, and there are still 14 records",
              fourth["files"][CARD] == "my-favourite-card.md" and not os.path.exists(os.path.join(out, "items", normalize.file_name(CARD))) and len(records(out)) == 14
              and normalize.parse(read(os.path.join(out, "items", "my-favourite-card.md")))[0]["title"] == "Export report as PDF, CSV and JSON")
    lines = []
    log.check("the model's own check accepts all 14 records", normalize.check(out, say=lines.append) == 0)
    log.out("  " + lines[-1])
    return log.save("identity-check.txt")


def unmappable(scratch):
    log = Log("Items the model cannot represent. context-canonical-work-item, attempt context-attempt-002",
              "Part 1 uses the work saved in this repository by the earlier quests. Parts 2 and 3 use made-up saved work in a scratch folder, SCRATCH.")
    log.part("PART 1. The work saved in this repository (criterion 11)")
    result, said = run(log, CONTEXT, MODEL, "python3 participant/skills/context-work-item-model/normalize.py", hide=("  NEW:", "  UPDATED"))
    refused = result["refused"]
    kinds = {}
    for reference, record, reason in refused:
        kinds.setdefault(reason.split(":")[0].split(". ")[0], []).append(reference)
    log.out("The %d refused items, by reason:" % len(refused), *["  %2d  %s" % (len(names), reason) for reason, names in sorted(kinds.items())])
    stories = [one for one in refused if one[0].startswith("jira story file")]
    assigned = [one for one in refused if one[0].startswith("jira assigned story")]
    cards = [one for one in refused if one[0].startswith("trello card")]
    log.check("17 saved items could not be mapped, and each is reported with its reason", len(refused) == 17 and all(len(reason) > 30 for _, _, reason in refused))
    log.check("the 13 saved Jira story files are refused because none records when it was retrieved, which provenance requires (criterion 8)",
              len(stories) == 13 and all("no retrieval time" in reason for _, _, reason in stories))
    log.check("the 3 Jira stories in the assigned list are refused because they were saved with a key and no issue id, and a key is not an identity (criterion 2)",
              len(assigned) == 3 and all("cannot be the identity" in reason for _, _, reason in assigned))
    log.check("1 real Trello card is refused because Trello no longer returns it, so its status would be a guess",
              len(cards) == 1 and "no longer returns" in cards[0][2] and "6afdf65aa3a5b8d67f9c9a21" in cards[0][0])
    index = json.loads(read(os.path.join(MODEL, "items", "index.json")))["items"]
    names = os.listdir(os.path.join(MODEL, "items"))
    log.check("no record file was written for any of them: the items folder holds no Jira file, no file for that card, and no half-written file",
              not [name for name in names if name.startswith("jira-") or "6afdf65aa3a5b8d67f9c9a21" in name or name.endswith(".tmp")])
    log.check("none of them is in the index, which holds %d identities, all Trello or GitHub" % len(index),
              all(identity.split(":")[0] in ("trello", "github") for identity in index) and len(index) == len(result["good"]))
    report = read(os.path.join(MODEL, "report.md"))
    log.check("report.md lists all 17 under \"Could not be mapped (17)\", each with its saved file and its reason",
              "## Could not be mapped (17)" in report and all(reference.replace("|", "\\|") in report for reference, _, _ in refused))
    log.check("the other %d items were not held up: each has a record, and the model's own check accepts every one" % len(result["good"]),
              len(result["good"]) == 225 and normalize.check(MODEL, say=lambda line: None) == 0)

    log.part("PART 2. Made-up items, each broken in one way. What is reported, and whether anything is written",
             "Each case starts from the same made-up saved work, changes one item, and normalizes into an empty folder.")
    cases = [
        ("a GitHub issue saved with no node ID", "github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0101"].pop("node_id"), "I_kwFIX0101", "no node ID"),
        ("a GitHub issue with an empty title", "github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0101"].update(title=""), "I_kwFIX0101", "no title"),
        ("a GitHub issue in a state the model has no status for", "github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0101"].update(state="merged"), "I_kwFIX0101", "has no status for"),
        ("a GitHub issue with no time of last update", "github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0101"].update(updated_at=None), "I_kwFIX0101", "no time of last update"),
        ("a Trello card whose time has no time zone", "trello/board.json", lambda d: d["cards"]["62cfix000000000000000c01"].update(last_activity="2026-11-18 10:00"), "c01", "no time zone"),
        ("a Trello card with no short link to build its address from", "trello/board.json", lambda d: d["cards"]["62cfix000000000000000c01"].pop("short_link"), "c01", "no short link"),
        ("a Trello card that Trello no longer returns", None, None, "c05", "no longer returns"),
    ]
    jira_cases = [
        ("a Jira story saved without its retrieval time", {"retrieved_at": KeyError}, "no retrieval time"),
        ("a Jira story saved with a key and no id", {"id": KeyError}, "cannot be the identity"),
        ("a Jira story whose status is a word, with no id and no category", {"status": "Done"}, "as words only"),
        ("a Jira story whose status has no category, and an id the status map does not name", {"status": {"id": "99999", "name": "Done"}}, "does not name that id"),
    ]

    def one_case(title, change, reference, expected):
        root, out = tempfile.mkdtemp(dir=scratch), tempfile.mkdtemp(dir=scratch)
        fixtures.build(root, 1)
        fixtures.write_map(os.path.join(out, "mappings", "status-map.json"))
        change(root)
        result = normalize.normalize(root, out, os.path.join(out, "mappings", "status-map.json"), say=lambda line: None)
        reasons = [reason for found, _, reason in result["refused"] if reference in found]
        written = [name for name in records(out) if reference.replace(".md", "") in name]
        log.out("  CASE: %s" % title, "    reported: %s" % (reasons[0] if reasons else "NOTHING"), "    record files written for it: %d. Other records written: %d" % (len(written), len(records(out))))
        log.check("%s: refused with a reason that names the fault, and no file was written for it" % title,
                  len(reasons) == 1 and expected in reasons[0] and not written and len(records(out)) == 14 - (0 if reference == "c05" else 1))

    for title, path, change, reference, expected in cases:
        def apply(root, path=path, change=change):
            if path:
                data = json.loads(read(os.path.join(root, path)))
                change(data)
                with open(os.path.join(root, path), "w", encoding="utf-8") as f:
                    json.dump(data, f)
        one_case(title, apply, reference, expected)
    for title, fields, expected in jira_cases:
        def apply(root, fields=fields):
            path = os.path.join(root, "jira", "stories", "30001.md")
            story = normalize.front_matter(path)
            for name, value in fields.items():
                story.pop(name, None) if value is KeyError else story.update({name: value})
            with open(path, "w", encoding="utf-8") as f:
                f.write("---\n" + "".join("%s: %s\n" % (name, json.dumps(value)) for name, value in story.items()) + "---\n")
        one_case(title, apply, "30001.md", expected)

    log.part("PART 3. An item that had a record, and can no longer be mapped",
             "The made-up Jira story 30001 is normalized. Then a later sync saves it again with a new title and WITHOUT its retrieval time.")
    root, out = os.path.join(scratch, "later-context"), os.path.join(scratch, "later-model")
    fixtures.build(root, 1)
    fixtures.write_map(os.path.join(out, "mappings", "status-map.json"))
    normalize.normalize(root, out, os.path.join(out, "mappings", "status-map.json"), say=lambda line: None)
    path = os.path.join(out, "items", normalize.file_name("jira:30001"))
    earlier = read(path)
    story = normalize.front_matter(os.path.join(root, "jira", "stories", "30001.md"))
    story.pop("retrieved_at")
    story["summary"] = "A newer title that must not be half-written"
    with open(os.path.join(root, "jira", "stories", "30001.md"), "w", encoding="utf-8") as f:
        f.write("---\n" + "".join("%s: %s\n" % (name, json.dumps(value)) for name, value in story.items()) + "---\n")
    result, said = run(log, root, out, "python3 participant/skills/context-work-item-model/normalize.py --root SCRATCH/later-context --out SCRATCH/later-model")
    log.check("the item is reported as unmappable, with the reason", any("UNMAPPABLE: jira story file 30001.md" in line and "no retrieval time" in line for line in said))
    log.check("its earlier record is byte for byte what it was: the new title was not written into it", read(path) == earlier and "A newer title" not in read(path))
    log.check("the run says that the record is from an earlier run and was not updated, so that it does not pass for current",
              any("NOT IN THE SAVED WORK NOW: jira:30001" in line for line in said) and "`jira:30001`: kept as it was, not updated" in read(os.path.join(out, "report.md")))
    return log.save("unmappable.txt")


def apply_run():
    log = Log("The model applied to the work saved in this repository. context-canonical-work-item, attempt context-attempt-002",
              "The saved work is what the earlier quests wrote under participant/context. Most of it is made up. The 8 cards of the participant's own sandbox Trello board are real.")
    command = "python3 participant/skills/context-work-item-model/normalize.py"
    log.part("PART 1. Applied once")
    note = os.path.join(MODEL, "notes", "trello-6afdf65638df50999c980d80.md")
    digest = hashlib.sha256(read(note, "rb")).hexdigest()
    first, said = run(log, CONTEXT, MODEL, command, hide=("  NEW:", "  UPDATED", "  UNMAPPABLE"))
    good = first["good"]
    by = lambda field, value: sum(1 for canonical, _, _ in good.values() if canonical[field] == value)
    live = sorted(identity for identity, (_, provenance, _) in good.items() if provenance["sync_source"] == "live")
    log.out(*read(os.path.join(MODEL, "report.md")).split("## Canonical records\n\n")[1].split("\n## ")[0].rstrip().split("\n"))
    log.check("225 canonical records are held: 97 Trello and 128 GitHub, and none from Jira", len(good) == 225 and len(records(MODEL)) == 225
              and [sum(1 for c, _, _ in good.values() if c["system"] == s) for s in normalize.SYSTEMS] == [0, 97, 128])
    log.check("7 of them come from a real sync, of the participant's sandbox Trello board. The other 218 come from made-up syncs, and each record says which",
              len(live) == 7 and all(identity.startswith("trello:6afdf") for identity in live))
    log.check("every record has the five things criterion 8 names: the system, the identifier, the address, the retrieval time and the sync run",
              all(p["source_system"] and p["source_id"] and p["source_url"].startswith("https://") and p["retrieved_at"] and p["sync_run"] for _, p, _ in good.values()))
    log.check("status is one of the four values in every record, and every record says how sure it is",
              all(c["status"] in normalize.STATUSES and c["status_basis"] in normalize.BASES for c, _, _ in good.values()))
    log.check("no GitHub item is in_progress, because GitHub cannot say so. The only in_progress items are Trello cards in lists the status map names",
              all(c["system"] == "trello" and c["status_basis"] == "inferred" for c, _, _ in good.values() if c["status"] == "in_progress") and by("status", "in_progress") >= 1)
    log.check("blocked is unknown for all 225: the saved work states it for none of them. The model does not guess", by("blocked", "unknown") == 225)
    log.check("nobody's identifier is in any record: not the sync's own member id, login or account id",
              not any(person in read(os.path.join(MODEL, "items", name)) for name in records(MODEL)
                      for person in [json.loads(read(os.path.join(CONTEXT, "trello", "board.json")))["member_id"], "robin-fixture", "casey-fixture"]))
    log.part("PART 2. Applied again, with nothing changed")
    snapshot = tree(MODEL)
    second, _ = run(log, CONTEXT, MODEL, command, hide=("  UNMAPPABLE",))
    log.check("nothing was written: 0 new, 0 updated, 225 unchanged", second["writes"] == [] and len(second["changes"]["unchanged"]) == 225)
    log.check("every file in participant/context/model is byte for byte what it was", tree(MODEL) == snapshot)
    log.check("the note on the real card has the same checksum before and after both runs (criterion 7)", hashlib.sha256(read(note, "rb")).hexdigest() == digest
              and any(digest in line and line.endswith("same") for line in said))
    log.part("PART 3. The model's own check (stretch goal)")
    lines = []
    log.check("every record fits the model", normalize.check(MODEL, say=lines.append) == 0)
    log.out("$ %s --check" % command, "  " + lines[-1])
    log.check("the model document and the three mapping documents are exactly what the code writes, so they cannot have drifted from it",
              read(os.path.join(MODEL, "work-item.md")) == normalize.model_document()
              and all(read(os.path.join(MODEL, "mappings", s + ".md")) == normalize.mapping_document(s) for s in normalize.SYSTEMS))
    return log.save("apply-run.txt")


def main():
    scratch = tempfile.mkdtemp(prefix="gtq-work-item-")
    try:
        results = [apply_run(), identity_check(os.path.join(scratch, "identity")), unmappable(scratch)]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

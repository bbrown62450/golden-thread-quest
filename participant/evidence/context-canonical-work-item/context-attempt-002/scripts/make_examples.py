#!/usr/bin/env python3
"""Writes participant/context/model/examples.md from the canonical records in participant/context/model/items.

    python3 participant/evidence/context-canonical-work-item/context-attempt-002/scripts/make_examples.py

The tables are copied from the records, value for value, so they cannot differ from them. The words around the tables
are in this script. The Jira column at the end comes from made-up saved work that this script normalizes in a scratch
folder, and is labelled as such. It contacts nothing.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "participant", "skills", "context-work-item-model"))
import fixtures      # noqa: E402
import normalize     # noqa: E402

MODEL = os.path.join(REPO, "participant", "context", "model")
CARD, ARCHIVED, ISSUE = "trello:6afdf65638df50999c980d80", "trello:6afdf655971ad373884d985b", "github:I_kwFX1010001"


def load(folder, identity):
    with open(os.path.join(folder, "items", normalize.file_name(identity)), encoding="utf-8") as f:
        return normalize.parse(f.read())


def cell(value):
    return "`%s`" % json.dumps(value, ensure_ascii=False, sort_keys=True).replace("|", "\\|")


def table(heads, rows):
    return ["| " + " | ".join(heads) + " |", "|" + "---|" * len(heads)] + ["| " + " | ".join(row) + " |" for row in rows]


def main():
    items = [load(MODEL, identity) for identity in (CARD, ARCHIVED, ISSUE)]
    heads = ["Field", "A Trello card (real)", "A Trello card, archived (real)", "A GitHub issue (made-up)"]
    lines = [
        "# Worked examples: the canonical model on saved work, side by side", "",
        "Written by `participant/evidence/context-canonical-work-item/context-attempt-002/scripts/make_examples.py`, at the participant's direction. Every value in the",
        "tables is copied from a canonical record in `items/`.", "",
        "**What is real here.** The two Trello cards are real: they are on the participant's own sandbox board, and were read from Trello by an earlier quest. Their",
        "titles are made-up work the participant typed. The GitHub issue comes from the made-up GitHub the earlier GitHub quest was built against. No real Jira item is",
        "shown, and the last section says why.", "",
        "Every value is JSON. The titles and labels are other people's text, carried as data.", "",
        "## The canonical fields", "", "The same fields, with the same meaning, for all three.", ""]
    lines += table(heads, [["`%s`" % name] + [cell(item[0][name]) for item in items] for name, _, _, _, _ in normalize.CANONICAL])
    lines += ["", "## Provenance", ""]
    lines += table(heads, [["`%s`" % name] + [cell(item[1][name]) for item in items] for name, _, _, _ in normalize.PROVENANCE])
    lines += ["", "## The source fields", "",
              "These are not side by side, because they are not the same fields. Each system keeps its own, under its own prefix.", "",
              "### The Trello card", ""] + table(["Field", "Value"], [["`%s`" % name, cell(value)] for name, value in items[0][2].items()])
    lines += ["", "### The archived Trello card", ""] + table(["Field", "Value"], [["`%s`" % name, cell(value)] for name, value in items[1][2].items()])
    lines += ["", "### The GitHub issue", ""] + table(["Field", "Value"], [["`%s`" % name, cell(value)] for name, value in items[2][2].items()])
    lines += [
        "", "## The differences, left visible", "",
        "The model does not make these three look more alike than they are.", "",
        "- **How sure the status is.** The GitHub issue is `done` and `stated`: GitHub itself says it was closed as completed. The first Trello card is `in_progress`",
        "  and only `inferred`: Trello says it is in a list called \"Doing\", and it is the participant's status map that says that list means in progress. The two",
        "  statuses sit in the same field, and `status_basis` keeps them from being read as equally certain.",
        "- **What archived means.** The second Trello card is `dropped`. Trello says only that it was archived. Whether the work was finished or abandoned, Trello does",
        "  not say, so the model does not either. A GitHub issue closed as completed and an archived Trello card may be the same event in two teams' lives, and they",
        "  land on different values. This is the lossy case named in `mappings/trello.md`.",
        "- **Delivery.** The GitHub issue's source block names the pull request and the commit that delivered it. The Trello cards have nothing of the kind. There is no",
        "  canonical \"delivered by\" field, because two of the three systems could never fill it.",
        "- **Order.** The Trello card is first in its list, and `trello.position` says so. The GitHub issue has no place in any order. The model has no canonical",
        "  priority, and says so in its non-goals.",
        "- **Dates.** The Trello card has a due date and no creation date. The GitHub issue has a creation date and no due date. Each `null` is a field that system",
        "  cannot supply, and the mapping documents list them.",
        "- **Labels.** The first card has one. The issue has an empty list, which means GitHub was asked and the issue has none. A card read from the assigned-cards",
        "  list would have `null`, which means the labels were not saved.",
        "- **Blocked.** `unknown` for all three. None of the saved records states it.",
        "- **Where it came from.** Two are `live` and one is `made-up`, in `sync_source`. All three addresses are `built` from the saved reference, by the rule in the",
        "  mapping document.",
        "", "## Jira: why no saved Jira item is shown", "",
        "None of the Jira work saved by the earlier quests can be put in the model. The model requires an item's stable identifier and the time it was retrieved, and",
        "each kind of saved Jira record lacks one of them:", "",
        "- the 13 story files have the issue id, and do not record when they were retrieved;",
        "- the 3 stories in the assigned list have a retrieval time, and were saved with a key and no issue id.", "",
        "So all 16 are reported as unmappable, with those reasons, and no record is written for them. `report.md` lists each one.", "",
        "To show that the Jira mapping itself works, here is a **made-up** Jira story that has every required field, normalized in a scratch folder by this script. It is",
        "not saved work, and it is not in `items/`.", ""]
    scratch = tempfile.mkdtemp(prefix="gtq-examples-")
    try:
        root, out = os.path.join(scratch, "context"), os.path.join(scratch, "model")
        fixtures.build(root, 1)
        fixtures.write_map(os.path.join(out, "mappings", "status-map.json"))
        normalize.normalize(root, out, os.path.join(out, "mappings", "status-map.json"), say=lambda line: None)
        story = load(out, "jira:30002")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    lines += table(["Field", "A Jira story (made-up, not saved work)"], [["`%s`" % name, cell(story[0][name])] for name, _, _, _, _ in normalize.CANONICAL])
    lines += [""] + table(["Source field", "Value"], [["`%s`" % name, cell(value)] for name, value in story[2].items()])
    lines += ["", "This is the only one of the four with a `parent`, and the only one where `blocked` is `yes`: Jira states both, in its parent field and in a link of the kind",
              "\"is blocked by\"."]
    with open(os.path.join(MODEL, "examples.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("make_examples: wrote participant/context/model/examples.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

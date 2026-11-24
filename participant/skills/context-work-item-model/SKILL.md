# Context: one model for Jira, Trello and GitHub work

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill turns work already saved from Jira, Trello and GitHub into one local model of a work item, version
`work-item/1`. It reads only saved files. It contacts nothing, and has no code that could.

    python3 participant/skills/context-work-item-model/normalize.py                read the saved work, write the records
    python3 participant/skills/context-work-item-model/normalize.py --check        check every record against the model
    python3 participant/skills/context-work-item-model/normalize.py --write-docs   write the model and mapping documents

`--root FOLDER` reads saved work from somewhere other than `participant/context`. `--out FOLDER` writes somewhere
other than `participant/context/model`. The skill uses the Python standard library only.

## 2. The model

The model is defined in `participant/context/model/work-item.md`, and each system's mapping in
`participant/context/model/mappings/`. Those four documents are written out from the tables in `normalize.py`,
so they cannot disagree with it. Read them for the fields. The rules that matter most:

- **Identity** is the system and its stable identifier: `jira:<issue id>`, `trello:<card id>`,
  `github:<node ID>`. Never a key, a short link, a number, a title or a file name.
- **Status** is one of `open`, `in_progress`, `done`, `dropped`, with `status_basis` saying whether the source
  stated it, the status map inferred it, or it was assumed.
- **Blocked** is `yes` or `no` only when the saved work states it. Otherwise `unknown`.
- **What only one system has** is kept in the record's source block, under `jira.`, `trello.` or `github.`.

## 3. What it reads

| System | Saved file | Written by |
|---|---|---|
| Jira | `jira/stories/*.md` and `jira/assigned/stories.json` | the Jira read skills |
| Trello | `trello/board.json` and `trello/assigned/assigned.json` | trello-read-board, trello-read-assigned-cards |
| GitHub | `github/assigned/assigned.json` | github-read-assigned |

A file that is not there is skipped. A file that cannot be read stops the run before anything is written.

## 4. What it writes

In the `--out` folder: one record per item in `items/`, `items/index.json`, and `report.md`. Each record has
three blocks, visibly apart: the canonical fields, the provenance, and the source fields.

It never writes in `notes/`, which is for a person's own analysis, and prints the checksum of every notes file
before and after each run. It never changes `mappings/status-map.json`.

Running it twice on the same saved work writes nothing the second time. No file holds the time of the run.

## 5. The status map

`mappings/status-map.json` is kept by a person. It holds what no source system decides: which Trello list
means which status, by the list's id; what a Jira status means when its category was not saved, by the status
id; which resolutions mean dropped; which labels mean blocked; and, for Jira, the site address and the account
the syncs ran for. A Trello list that is not in the map leaves its cards `open` and marked `assumed`. A list's
name is never read for its meaning.

## 6. An item that cannot be mapped

If a required field cannot be filled from what was saved, the item is reported with the reason, in the output
and in `report.md`, and no record is written. An item that had a record keeps it as it was, and the report
says it was not updated.

Today this refuses every saved Jira record: the story files do not record when they were retrieved, and the
assigned list was saved without issue ids.

## 7. Other people's text

A title and a label are carried as JSON strings and never read for meaning. Descriptions and comments are not
copied at all: the record points to the saved file that holds them.

## 8. Tests

    python3 -m unittest discover -s participant/skills/context-work-item-model/tests -v

Every test uses made-up saved work from `fixtures.py`, in a scratch folder.

## 9. Limits

- It can only be as complete as the saved work. See section 6.
- A person must keep the status map. An unmapped Trello list is not an error, so a new list goes unnoticed
  until someone reads the `assumed` count in `report.md`.
- It does not join items across systems. A card and the issue that mirrors it are two items.
- It does not carry who the people are, so it cannot answer questions about anyone but "me".
- A record whose item has left the saved work is kept, not deleted, and is marked only in the report.

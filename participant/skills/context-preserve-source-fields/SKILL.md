# Context: normalize without losing anything

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill maps source records from Jira, Trello and GitHub onto a few canonical fields, keeps every other field
exactly as the source sent it, and proves nothing was lost by rebuilding each source record from its normalized
record and comparing the two, character for character.

It reads and writes local Markdown files only. It contacts nothing.

    python3 participant/skills/context-preserve-source-fields/fidelity.py normalize    write normalized.md from source-records.md
    python3 participant/skills/context-preserve-source-fields/fidelity.py check        rebuild every source record and compare
    python3 participant/skills/context-preserve-source-fields/fidelity.py rationale --out FILE

`--sources FILE` and `--normalized FILE` point at other files. `--mapping-version 1` normalizes with the first
version of the mapping. The files are in `participant/context/fidelity/`. Python standard library only.

## 2. The rule: preserve first

Every field of a source record ends up one of three ways:

| Outcome | What happens | How the original comes back |
|---|---|---|
| copied | a canonical field holds its value exactly | from the canonical field |
| translated | a canonical field is worked out from it, and the original is also preserved | from the preserved section |
| preserved only | no canonical field uses it. It is preserved | from the preserved section |

A field the mapping does not list at all is preserved too, and the check names it.

Which field gets which outcome, and why, is in `participant/context/fidelity/mapping-rationale.md`. That
document is written out from the tables in `fidelity.py`, so the two cannot disagree.

## 3. What "preserved" means here

A preserved value is **the characters the source sent**. It is never parsed and written out again. So `3.0`
stays `3.0`, `1e3` stays `1e3`, an escape stays an escape, a list keeps its order, spaces inside an object stay,
and `""`, `null` and a field that is not there stay three different things.

A copied field is checked for every record: if writing the canonical value back out would not give the
source's exact characters, that record preserves the original as well.

## 4. The files

- `source-records.md`: each record under a heading `### system id`, as one JSON object, one field to a line.
- `normalized.md`: for each record, the canonical fields, how to rebuild the source record (the order of its
  fields, and which a canonical field gives back), and the preserved source fields. Written by `normalize`.
  Do not edit it.

## 5. The check

`check` rebuilds each source record from its normalized record alone and compares it with the original. It
reports, by name: a field that cannot be rebuilt, a field whose characters changed, a field the source never
had, a lost field order, and a record with no partner. It also lists preserved fields that more than one
system has. Exit code 0 only if every record is identical. It writes nothing.

## 6. Tests

    python3 -m unittest discover -s participant/skills/context-preserve-source-fields/tests -v

## 7. Limits

- **One field per line.** A source record must be written with each top-level field, and each field inside
  Jira's `fields`, on one line. A value spread over several lines stops the run. Real API output would have to
  be laid out this way first, and the layout between fields is not preserved: only each field's own characters.
- **Only Jira's `fields` is opened.** Every other object is one field, kept whole. A value deep inside
  Trello's `customFieldItems` cannot be mapped without changing the code.
- **A duplicate field name stops the run.** JSON allows it and this does not handle it.
- The check proves the record can be rebuilt. It does not prove the canonical values are right: a wrong status
  with its original preserved still rebuilds perfectly.
- The Trello list-to-status table is read from the source file. A list not in it counts as open.

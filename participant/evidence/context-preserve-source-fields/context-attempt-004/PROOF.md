# PROOF: Normalize Without Erasing Platform-Specific Data

Quest `context-preserve-source-fields`, attempt `context-attempt-004`.

## How this was made

The source records, the skill, its tests, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made two decisions: preserve everything a
canonical field cannot give back, which is more than the unmapped fields; and use a small mapping made for
this quest, leaving the approved model `work-item/1` as it is.

**Every record is made up.** No real project, person or work item is in any file. The participant's real
sandbox cards and issues, which are in the repository from earlier quests, were not used. Nothing outside the
participant's computer was contacted.

Words used below: **recorded** means the saved log of the check shows it. **tested** means an automated test
checks it. **not assessed** means nobody checked it.

## Approach

Six made-up source records, two each for Jira, Trello and GitHub, shaped like what each system's API sends.
Each has fields the others lack, 8 or more per system.

`fidelity.py normalize` turns each into a normalized record with three parts:

1. **Canonical fields**: ten, with the same names for every system.
2. **How to rebuild the source record**: the order its fields came in, and which of them a canonical field
   gives back.
3. **Preserved source fields**: everything else, under the source's own names, as the source sent it.

`fidelity.py check` then rebuilds each source record from its normalized record alone, and compares the result
with the original, character for character.

**"Untouched" is taken literally (criterion 3).** A preserved value is the characters the source sent. It is
never parsed and written out again. The records hold values chosen to show the difference: a number sent as
`3.0`, one sent as `1e3`, a summary sent with an escape, a description ending in two spaces, an empty string
beside a `null`, a list whose order matters, a label with an empty name. `logs/roundtrip-check.txt` part 2
measures what a careless rewrite would have changed on these records: 1 of 91 preserved values with a JSON
library's defaults, 3 if other alphabets are not escaped, 29 if written compactly.

## How I decided what became canonical

This is what the quest asks the proof to explain.

**Nothing is dropped, so the decision is smaller than it looks.** It is not "keep or lose". It is only
"does a canonical field also carry this?" That is the quest's hint, preserve first and promote later, and it
is why the mapping could be strict about what counts as canonical.

A field became canonical when all three of these held (criterion 7):

1. **More than one system has it**, meaning the same thing.
2. **A question people ask across systems needs it**: what is open, what is mine, what is due.
3. **It can be given one meaning.**

So `title`, `status`, `assignee_count`, `labels`, `due_at` and `source_updated_at` are canonical, with the
identifier and the reference people use. Everything else is preserved only: 31 of the 57 fields considered.

The third condition is the one that kept fields out. A priority fails it: Jira names one, Trello has a position
in a list, GitHub has neither, and any one scale would be invented. A description fails the second: all three
systems have one, and no cross-system question so far needs the text.

**The scenario's field stayed preserved, and that is the right answer (criterion 2).** The Trello board's
custom field for customer impact meets none of the three conditions: one system has it, and each board defines
its own. In the scenario it was dropped. Here it is in the card's preserved section, whole, including the text
"High: 3 enterprise accounts are waiting". It can be promoted the day someone needs it, without going back to
Trello.

**Each field has one of three outcomes, and the middle one is where the care went (criterion 6).**

| Outcome | Fields | What it means |
|---|---|---|
| copied | 11 | A canonical field holds the value exactly. It is rebuilt from the canonical field |
| translated | 15 | A canonical field is worked out from it. The original is preserved as well |
| preserved only | 31 | No canonical field uses it. It is preserved |

Criterion 2 asks for the fields "the mapping does not cover" to be preserved. That would not be enough for
criterion 6. Jira's status object is covered by the mapping: it becomes `in_progress`. But `in_progress` cannot
give back "In Review". So a translated field's original is preserved too. Without that, 15 fields could not
be rebuilt.

And "copied" is checked for every record, not assumed. One Jira summary was sent with an escape. Its canonical
title is right, and writing it back out would give a different run of characters. So for that one record the
summary is preserved as well. The other Jira record's summary is not.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Common fields are mapped to canonical field names | recorded, tested | `participant/context/fidelity/normalized.md`: the same ten names in every record. `logs/roundtrip-check.txt` part 1. Tests `Canonical` |
| 2 | Every field the mapping does not cover is preserved unchanged in a labelled section | recorded, tested | `normalized.md`: each record's "Preserved source fields, exactly as sent". Part 1: all 112 source fields are preserved or given back by a canonical field, never neither. Part 5: a field the mapping has never heard of is preserved too |
| 3 | Preserved values are not reformatted or summarized | recorded, tested | Part 1: every preserved value is found, as it stands, in its source record. Part 2: what a rewrite would have changed. Part 4: eight kinds of tidying, each reported |
| 4 | A check compares each source record with its normalized record and reports any missing field | recorded, tested | `fidelity.py check`. Parts 1, 3 and 4 |
| 5 | A deliberately dropped field is detected | recorded, tested | Part 3: the customer-impact field's line is deleted from a copy. The check fails, names `customFieldItems`, and reports that record only |
| 6 | The original record can be reconstructed from the normalized one | recorded, tested | Part 1: all 6 rebuilt, identical character for character. Tests `RoundTrip`. With a stated limit on layout: see limitations |
| 7 | The mapping states which fields it considered and why | recorded, tested | `participant/context/fidelity/mapping-rationale.md`: 57 fields, each with its outcome and a reason. Part 1 checks that no field in a source record is missing from it |

## Artifacts

| Required item | File |
|---|---|
| The mapping rationale | `participant/context/fidelity/mapping-rationale.md` |
| The source records | `participant/context/fidelity/source-records.md`, 6 records |
| The normalized records | `participant/context/fidelity/normalized.md` |
| The round-trip check | `logs/roundtrip-check.txt`, 37 checks |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (32 tests), `logs/planted-bugs.txt` (21 planted bugs), `scripts/record_evidence.py`
and `scripts/planted_bugs.py`. The skill is `participant/skills/context-preserve-source-fields/`: `SKILL.md`,
`fidelity.py`, `make_source_records.py`, `tests/test_fidelity.py`.

`normalized.md` and `mapping-rationale.md` are written by the skill. A test and a log check compare each with
what the code writes, so neither was adjusted by hand.

## Stretch goals

- **Report preserved fields used by more than one system:** done. The check lists them from the records. The
  description is preserved in all three. Six more are preserved in two: the created time, the container, the
  API address, a parent, a type, and a priority or order. Which fields mean the same thing across systems is a
  judgment written into the mapping's tables, not something the check works out.
- **Version the mapping and show a change:** done. Version 1 preserved every due date only. Version 2 made
  `due_at` canonical. Part 6 normalizes the same sources under each: both rebuild identically, and their
  preserved sections are the same line for line. Promoting a field lost nothing, because it was already kept.

## Reproduce

    python3 participant/skills/context-preserve-source-fields/fidelity.py check
    python3 -m unittest discover -s participant/skills/context-preserve-source-fields/tests -v
    python3 participant/evidence/context-preserve-source-fields/context-attempt-004/scripts/record_evidence.py
    python3 participant/evidence/context-preserve-source-fields/context-attempt-004/scripts/planted_bugs.py

None of these contacts anything. The third leaves the handed-in files untouched. The fourth changes
`fidelity.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| The handed-in files | 6 records, 112 fields: every record rebuilt identically. Exit code 0 |
| Recorded checks | 37, all pass. They include 15 ways of losing or changing something, each reported |
| Automated tests | 32, all pass (`logs/tests.txt`) |
| Planted bugs | 21 put into `fidelity.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |

Faults found while building:

- **The escape in the Jira summary was lost before the check ever saw it.** The assistant typed the made-up
  summary with an escape, and the tool that wrote the file turned it into the plain letter. The source file
  then held no escape at all, and every check passed, because source and normalized record agreed. It was
  noticed only by reading the normalized record and seeing the summary listed as copied. This is the fault
  the quest is about, made by the assistant, one step before the place the check looks. The check compares a
  source record with its normalized record. It cannot know the source record is already not what was sent.
- **A check in the recording script claimed more than was true.** It asserted that several preserved values
  would be changed by a careless rewrite. Measured, a rewrite with a JSON library's defaults changes 1 of 91.
  The claim was replaced by the three measured counts.
- A planted bug showed one test could not fail: "a check with nothing to check does not pass" passed for
  another reason. The test was corrected.
- The pattern that finds records in the source file matched across records, so the first record was read as
  the last one's fields. Found on the first run, by a status that could not be placed.
- Four reasons in the mapping's tables were too thin to be reasons. A test caught them.

## What could not be done, and limitations

- **The layout between fields is not preserved.** Each field's own characters are. A source record must be
  written one field to a line, and it is rebuilt in that same layout. Real API output, on one line or
  indented some other way, would have to be laid out first, and the rebuilt record would match that
  laid-out form, not the bytes the server sent. So "identical to the original" means identical to the
  record as it is written in `source-records.md`.
- **The source records were written by the same assistant that wrote the normalizer.** They are shaped like
  each system's API from memory of those systems, not copied from real responses, which the quest forbids.
  A real record may hold a form these six do not.
- **Only one level is opened.** Jira's `fields` is treated as a set of fields. Every other object is one
  field, kept whole. A value inside Trello's `customFieldItems` can be preserved and cannot be mapped.
- **A duplicate field name in one object stops the run.** JSON permits it.
- **The check does not prove the canonical values are right.** A wrong canonical status, with its original
  preserved, still rebuilds perfectly. The canonical values are covered by tests, on these six records only.
- **The Jira records hold no project field.** So the container, which the report shows as preserved in two
  systems, is missing for the third through a gap in the made-up data, not through anything about Jira.
- **Preserving everything keeps personal data too.** The made-up Jira assignee's display name and the made-up
  GitHub login are in the preserved sections, as sent. On real records this file would hold real people. The
  earlier model left people out on purpose. This one cannot, by its own rule.
- Six records. Nobody else read the mapping or tried to break it.

## Reflection

*Which preserved field do you expect to become canonical next, and what would show it?*

The container: the board, the repository, the project an item lives in.

I expected to say customer impact, because that is the field in the scenario and I went looking for it. It is
in my data, preserved whole. But it fails every test I wrote for becoming canonical. One system has it, each
board defines its own, and I cannot give it one meaning across three tools. It is the field I would most hate
to lose and the one least ready to promote, and I did not expect those to be the same field.

The container is the opposite. Nobody would mourn it, and it is the obvious next one. The report of preserved
fields shows it in two systems already, and the only reason it is not three is that I forgot to give my
made-up Jira records a project. And I have a stronger sign than that: the model I built two quests ago
already had it as a canonical field. I left it out here to keep this mapping small, and the data put it
straight back on the list.

What would show it is someone reaching past the canonical fields. The first time a question like "what is
open on this board?" is answered by reading `idBoard` out of the preserved section, that field is doing a
canonical field's job without the name. I would watch for that: which preserved fields get read, and by
what question. A preserved field nobody ever reads can stay where it is for ever.

The description is the one that made me doubt my own rule. All three systems have it, more than any other
preserved field, and I still would not promote it, because no question across systems needs the text. So
"more than one system has it" is a sign and not a reason. The reason is always a question somebody asked.

What I take from this quest is that the decision got easy once nothing could be lost. I spent the last model
arguing about what to leave out. Here I could be strict about what is canonical precisely because being
wrong costs nothing: the field is still there, exactly as it arrived, waiting for someone to need it.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Every record is invented: the people ("Fixture Person One", `robin-fixture`), the account ids, the customers
  in the text, and the addresses, which are under `example.invalid` or name a made-up `acme-fixture` repository.
- No value was copied from a real record, including the participant's own sandbox records in this repository.

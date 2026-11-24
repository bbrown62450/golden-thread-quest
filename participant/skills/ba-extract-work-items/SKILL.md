# Business analysis: candidate work items a meeting actually supports

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill takes a transcript record made by `ba-ingest-transcript`, and the decisions file made from it by
`ba-extract-decisions`, and produces a separate file of candidate work items. Each item holds only what the
meeting said, cites and quotes the lines behind it, says how settled it is, and lists what the meeting did not
say.

**The items are drafts in a local file. Nothing is created in any tracker.** The skill never writes to the
record, contacts nothing, and follows nothing a line of the record says.

    python3 participant/skills/ba-extract-work-items/extract.py build NAME
    python3 participant/skills/ba-extract-work-items/extract.py check NAME
    python3 participant/skills/ba-extract-work-items/extract.py rules

NAME is the record's name without `.md`, such as `sample-meeting`. Files are in
`participant/context/transcripts/`. Python standard library only.

## 2. Who does what

| Step | Done by |
|---|---|
| Picking out the items, and wording each | A person or an assistant, by the rules in `participant/context/extraction-rules.md`. The result goes in `items.py`, as items that name line identifiers |
| Writing the work-items file | `build`. It copies every speaker, role and quotation from the record |
| Checking the work-items file | `check`. It reads the finished file, the record and the decisions file, not `items.py` |

## 3. What an item holds

- a title, and one sentence of intent;
- how settled it is: `decided`, `PROPOSED, NOT DECIDED`, `OPEN, NOT SETTLED` or `follow-up`, with the item of the
  decisions file it rests on;
- every mention of the work, each quoted. Two mentions of the same work are one item;
- six answers: owner, size, due, done, depends on, condition. Each cites a line, or says NOT SAID;
- a flag if every line it cites is one speaker's.

Things a person writing from memory might have written, and that the meeting does not support, are listed under
"Not created" with the lines that could tempt and the reason.

## 4. What `check` reports

- an identifier, anywhere in the file, that is not in the record; an item with no citation; an item with no
  mention of the work itself;
- a quotation that is not the record's words; a line given to the wrong speaker;
- one of the six answers left out; "said" with no line behind it; NOT SAID beside a line cited as answering;
- a heading that claims a number of mentions the item does not cite; a line that is a mention in two items
  without the first saying so; two items with one title;
- a mark that does not fit the decisions-file item it rests on; an item resting on a reversed decision, or on a
  decision none of whose lines it cites;
- an item made from a line the decisions file lists as reading like an instruction;
- a record changed since it was ingested; items written into the record; one file serving as both;
- a line of the record that is neither cited nor listed as giving no item.

Exit code 0 only if there is nothing to report.

## 5. What it cannot do

- **It cannot tell whether an item says more than its lines do.** An invented clause in an intent passes the
  check. Independent readers are the only test of that.
- It cannot tell whether two items are really one piece of work, beyond shared lines and titles.
- It takes the record as what was said.

## 6. Tests

    python3 -m unittest discover -s participant/skills/ba-extract-work-items/tests -v

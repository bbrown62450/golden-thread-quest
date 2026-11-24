# Context: a decision log that says what is decided

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill checks a decision log that a person keeps. In the log every entry is a decision, a proposal or a
question, and says which. The skill reports where the log breaks its rules, and writes the part of the log
that lists what is decided now.

**It decides nothing and approves nothing.** It never adds an entry. It contacts nothing.

    python3 participant/skills/context-decision-log/decisions.py check      check the log. Changes nothing
    python3 participant/skills/context-decision-log/decisions.py view       rewrite the generated part at the top of the log
    python3 participant/skills/context-decision-log/decisions.py seal       record a checksum of each new entry
    python3 participant/skills/context-decision-log/decisions.py rules --out FILE

`--log FILE` works on a log other than `participant/context/decisions/log.md`. Python standard library only.

## 2. The rules

They are in `participant/context/decisions/rules.md`, which is written out from the tables in `decisions.py`,
so the rules and the check cannot disagree. In short:

- An entry has exactly one status, in its heading and in its `status` field, and its statement opens by
  saying what it is.
- A decision needs an approver of the right role for its kind, the place it was approved, the approver's own
  quoted words of approval, and a date. Words of agreement, such as "sounds good", are not approval.
- A proposal or a question may not carry approval fields, or be worded as settled.
- An entry is never edited. A change is a new entry with `promotes`, `rejects`, `supersedes` or `answers`.
- Every entry cites a source with a reference a reader can look up.

## 3. Adding to the log

A person does it, by hand:

1. Write the new entry at the end, with the next number.
2. Run `view`, so the top of the log shows the new state.
3. Run `check`. Correct the new entry until it passes.
4. Run `seal`. From then on the entry may not change.

To change your mind about something, do not edit the old entry. Write a new one that points at it.

## 4. What it writes

`view` writes only between the two marker lines in the log. `seal` adds lines to `ledger.json`, beside the
log, and never changes a line already there. `check` writes nothing.

## 5. Tests

    python3 -m unittest discover -s participant/skills/context-decision-log/tests -v

Each test starts from the log in `participant/context/decisions`, copied to a scratch folder.

## 6. Limits

- **It cannot open what an entry cites.** It checks that approval words are given, quoted, and are words of
  approval. It cannot check that the approver wrote them at the place named. A person follows the reference.
- **The lists of words are short and in English.** An approval phrased another way is reported as agreement,
  and has to be requoted. A proposal can still present itself as settled in words the list does not hold.
- **The ledger is a file like any other.** Someone who edits an entry and the ledger together is not caught
  by the check. The repository's history is what catches that.
- **A missing link is invisible.** If a new decision replaces an old one and does not say `supersedes`, both
  show as current, and the check cannot know.
- One approving role per kind of decision. A decision that needs two approvers cannot be expressed.

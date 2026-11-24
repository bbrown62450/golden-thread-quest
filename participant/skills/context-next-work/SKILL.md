# Context: what to work on next, with a reason for every place

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill ranks open work from local records and writes a recommendation a person can argue with. Every reason
names the recorded field it came from. Blocked work is taken out and its blocker named. Work whose local copy is
stale is warned about and never offered as the thing to start.

**It gives advice.** It never starts, assigns or changes work. It writes one file, the recommendation, and never
writes to a record. It contacts nothing.

    python3 participant/skills/context-next-work/rank.py rank [--inputs FILE] [--out FILE] [--now TIME] [--rule NAME]
    python3 participant/skills/context-next-work/rank.py rules

It reads `participant/context/next-work/inputs.md` and writes `recommendation.md` beside it. `rules` writes
`rules.md`, which states every rule in full. Python standard library only.

## 2. The three lists

| List | When |
|---|---|
| Not offered | `status` is not `open`, or `assigned_to` holds a value |
| Blocked | open, unassigned, and waiting on something not finished |
| Ranked | everything else |

## 3. The order

Priority, then due date, then the number of open items waiting on it, then created date, then identity. The
first criterion on which two items differ decides. There are no weights and no score. `--rule due-first` swaps
the first two.

`votes` is recorded, shown and not used. Titles are never read.

## 4. Stale context

The limit comes from `participant/context/freshness/policy.md`: 24 hours for a work item. A stale item keeps
its place and carries a warning. "Start here" is the first ranked item whose copy is fresh.

## 5. The clock

The clock value is part of the input: a line `- clock:` in the inputs file, or `--now`. The computer's clock is
never read. With no clock value the ranking stops.

## 6. Missing data

A missing or unreadable `priority`, `due` or `created` is never filled in. The item goes after every item that
has a value, the reason says so, and its confidence falls one step.

## 7. Exit codes

| Code | Meaning |
|---|---|
| 0 | The recommendation was written |
| 2 | Nothing was written: no clock value, two records with one identity, an unreadable record, no freshness policy, or an attempt to write over the inputs |

## 8. What it does not do

- It does not know whether a recorded priority is right. Confidence says how complete the data is, not how
  good the advice is.
- It does not weigh priority against urgency. The rule is strict, and a different rule gives a different answer.
- It does not know who is asking, what they are able to do, or how large a piece of work is.
- It does not refresh a stale record. It says the record is stale.

## 9. Tests

    python3 -m unittest discover -s participant/skills/context-next-work/tests -v

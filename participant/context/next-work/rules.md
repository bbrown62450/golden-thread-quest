# Ranking rules: what to work on next

Written by `participant/skills/context-next-work/rank.py rules`, at the participant's direction, for the quest
`context-next-work`. The tables below are the tables the program applies.

The ranking gives advice. It never starts, assigns or changes work, and it never writes to a record.

## 1. Which items are ranked

Every work item goes on exactly one of three lists.

| List | When | What is cited |
|---|---|---|
| **Not offered** | `status` is anything but `open`, or `assigned_to` holds a value | that field |
| **Blocked** | it is open and unassigned, and something it waits on is not finished | the field that records the link, the record that field is on, and the blocker's `status` |
| **Ranked** | everything else | one reason for each criterion |

An item waits on whatever its own `blocked_by` or `needs_decision` names, and on any record whose `blocks` names it.
A work item is finished when its `status` is `done`. A decision is finished when its `status` is `decided`. A blocker
that has no record cannot be shown to be finished, so the item is blocked, and the blocker is named.

Blocked items are not given a place. They are listed with the blocker named.

## 2. The criteria, and their order

The first criterion on which two items differ decides between them. Later criteria are not looked at.

| Order | Criterion | Field it reads | Which comes first |
|---|---|---|---|
| 1 | Priority, highest first | `priority` | high, then medium, then low |
| 2 | Due date, soonest first | `due` | the earlier date |
| 3 | Open items waiting on it, most first | `blocks` on the item, and `blocked_by` on the items that name it | the larger number |
| 4 | Created, oldest first | `created` | the earlier date |
| 5 | Identity, as the last tie-break | `identity` | the one that sorts first as text |

This is the rule `priority-first`, and it is the one the recommendation uses. A second rule, `due-first`, puts the due
date before priority and leaves the rest as it is: due, priority, waiters, created, identity.

**No weights and no score.** A high-priority item due next month is above a low-priority item due tomorrow, every
time. That is blunt on purpose: the reason for any place is one field, and a person can say which.

## 3. Ties

Two items level on one criterion go to the next. Identity is last and no two records share one, so no tie is left.

## 4. Missing data

- A value is **missing** when the field is not there, or holds something that cannot be read: a `priority` that is not
  high, medium or low, or a `due` or `created` that is not a date written like 2026-12-03.
- A missing value is **never filled in**. No default is assumed.
- On that criterion the item is placed **after every item that has a value**.
- Each missing value is **reported** in the item's reasons, and **lowers its confidence** one step.

## 5. Confidence

Confidence starts at high and falls one step, to medium and then to low, for each of these:

- each of `priority`, `due` and `created` that is missing;
- a stale copy;
- a link on the item that could not be read.

It does not go below low. Confidence does not change an item's place. It says how far the place can be relied on.

## 6. Stale context

- A work item's copy is stale when `retrieved_at` is more than **24 hours** before the clock value. A decision's is stale
  after 2160 hours. Both limits are read from `participant/context/freshness/policy.md`.
- A copy with no `retrieved_at`, one that cannot be read, or one later than the clock value cannot be shown to be
  fresh, and is stale.
- A stale item **keeps its place and carries a warning**. Its confidence is lowered.
- **"Start here" is the first ranked item whose copy is fresh.** A stale item ranked above it is named, with its
  warning. If no ranked item is fresh, nothing is recommended.
- If a blocker's own copy is stale, the blocked item says that it may no longer be blocked.

## 7. The clock

The clock value is part of the input: a line `- clock:` in the inputs file, or `--now`. The computer's clock is never
read. With no clock value, the ranking stops and writes nothing. So the same input gives the same ranking on any day.

## 8. What is not used

`votes` is recorded, shown beside each item and not used. Titles and descriptions are never read for a reason.

## 9. What the ranking refuses

It stops, and writes nothing, when: there is no clock value, or it is not a time; two records share an identity; a
record is not valid JSON or does not carry the identity of its heading; no record can be read; the freshness policy
cannot be read; or it is told to write over the inputs file.

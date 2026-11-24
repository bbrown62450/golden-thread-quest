# Context: what waits on what, among work items and decisions

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill builds an index of dependencies from recorded fields. It answers "what does this wait on?" and "what
waits on this?", and it reports cycles and links that point at nothing.

**It reads and reports.** It never changes a record, in a file or in any system, and it contacts nothing.

    python3 participant/skills/context-dependency-map/depmap.py build [--data FILE] [--out FILE]
    python3 participant/skills/context-dependency-map/depmap.py slip IDENTITY DAYS [--data FILE]

`build` reads `participant/context/dependencies/data.md` and writes `index.md` beside it. Python standard
library only.

| Exit code | Meaning |
|---|---|
| 0 | The index was built and there is nothing to report |
| 1 | The index was built, and problems are reported in it and printed |
| 2 | The index was not built: the data could not be read, or two records share an identity |

## 2. Where a dependency comes from

Three fields, and no others.

| Field | Meaning |
|---|---|
| `blocked_by` | this record waits on each one named |
| `blocks` | each one named waits on this record |
| `needs_decision` | this record waits on each decision named |

A link written at both ends is one link with two sources. Every link in the index says which field, on which
record, it was read from.

**Never read for a dependency:** `title`, `description`, `labels`, `parent`, `related`, `superseded_by`. A title
that says "once the search API is done" records nothing. `parent` and `related` are listed in the index under
"Seen and not counted".

## 3. Items

An item is a work item (`jira:`, `trello:`, `github:`, as in `participant/context/identity/rules.md`) or a
decision (`decision:E-201`). A decision is a node like any other: it can be waited on, it can wait, it is
counted and ranked.

A link stops holding work up when its target is finished: a work item that is `done`, or a decision that is
`decided`.

## 4. What is reported

| Report | When |
|---|---|
| CYCLE | items wait on each other, in a ring of any length. The members and one way round are given |
| SELF | an item names itself |
| NOT FOUND | a link names an identity that has no record. The link is kept, and the missing item has its own entry |
| UNREADABLE | a link is not an identity, or the field is not a list. Nothing is guessed from it |
| NOT DECIDED | something waits on a proposal or a question |
| WILL NEVER FINISH | something waits on a dropped item or a superseded decision |
| NOT A DECISION | `needs_decision` names a work item. The link is kept |
| OUT OF ORDER | an item is finished and what it waited on is not |
| TOO EARLY | an item is planned to start on or before the day its prerequisite is planned to finish |

## 5. How cycles are found

Tarjan's algorithm for strongly connected components, over every recorded link, whatever the status of the
items. A component of two or more items is a cycle. Two rings that share an item are reported as one group.

## 6. Blocking the most

An item blocks every item still to do that cannot finish until it is done: those waiting on it, those waiting
on them, and so on. The five with the highest totals are listed, each with its direct count. Equal totals go
by the direct count, then by identity. If more items are level with fifth place, the index names them.

## 7. Same input, same index

Everything is sorted by identity. The index holds no time, no date of the run and no path. The order of the
records in the data file, and of the entries in each field, does not change it.

## 8. What it does not do

- It does not infer a dependency from wording, from a shared label, from a parent, or from dates.
- It does not check that an item marked done is done.
- It does not say which link in a cycle is the wrong one.
- Dates are calendar days. It knows nothing of weekends, holidays or how many people there are.

## 9. Tests

    python3 -m unittest discover -s participant/skills/context-dependency-map/tests -v

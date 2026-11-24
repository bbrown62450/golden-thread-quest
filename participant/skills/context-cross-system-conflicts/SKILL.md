# Context: report where systems disagree about the same work

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill finds work whose recorded state differs between Jira, Trello and GitHub, and reports each
difference with both values, both systems and both times.

**It reports. It does not resolve.** It never says which system is right, never gives one "true" state for a
piece of work, and never changes a record, in a file or in any system. It contacts nothing.

    python3 participant/skills/context-cross-system-conflicts/conflicts.py report [--records FILE] [--out FILE] [--previous FILE] [--state FILE]

It reads `participant/context/conflicts/records.md` and writes `report.md` beside it. `--previous` is the state
file an earlier run wrote with `--state`. Python standard library only.

## 2. What is compared

Two records are compared only if a **link** in the records file says they are the same work. A link is stated
by a person and names each record by its stable identity. A matching title is never a link.

For each linked pair, four fields: status, whether anyone is assigned, the due date, and the title.

## 3. The four answers

| Answer | When |
|---|---|
| agree | the two values are the same |
| not comparable | they differ, and one system has no way to say what the other says. GitHub has no "in progress" and no due date |
| lag | they differ, and all of: both records say when they last changed; those times are more than nothing and at most 24 hours apart; and, for status, the record that changed later is the one further along |
| conflict | they differ, and it is none of the above |

The 24 hours are measured between the two records' own times, never from today. The skill reads no clock, so
the same input gives the same report on any day, and the order of the records in the file changes nothing.

"Further along" is open, then in progress, then done or dropped. Done against dropped is always a conflict.

A title that differs is listed in its own section and is never a conflict.

## 4. What the report holds

Conflicts, each with both values as the source wrote them, when each last changed, why it is a conflict, and
what a person would need to find out to settle it. Then the differences judged to be lag, those not
comparable, titles that differ, unlinked records, links that could not be used, and every comparison made
with its reason.

A record with no counterpart is **unlinked**. It is not a conflict.

Conflicts are ordered by how many other pieces of work depend on the one in conflict. With `--previous`, each
says whether the same two values were already in conflict in the earlier run.

## 5. Tests

    python3 -m unittest discover -s participant/skills/context-cross-system-conflicts/tests -v

## 6. Limits

- **A link is a person's claim.** A wrong link makes a "conflict" between two things that were never the same,
  and the report cannot tell. It shows who stated each link.
- **Work nobody linked is not compared**, however obviously it is the same. Records that share a title are
  listed as a hint and no more.
- **The 24 hours is one number for every system and every field.** It cannot tell a delay from a habit: a
  GitHub issue left open for weeks after the work is done looks like lag for a day and a conflict after.
- **"Lag" is a guess about a pattern.** It does not mean the later value is true.
- It compares the canonical status. Two systems whose own states were mapped wrongly would agree or disagree
  wrongly, and the report would not know.
- It sees one moment. It does not know how long a difference has existed, only whether the previous run had it.

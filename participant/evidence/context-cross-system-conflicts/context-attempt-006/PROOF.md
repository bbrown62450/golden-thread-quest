# PROOF: Report Contradictory State Across Systems

Quest `context-cross-system-conflicts`, attempt `context-attempt-006`.

## How this was made

The made-up records, the skill, its tests, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made three decisions: two records are the
same work only if a link, stated by a person, says so, and never because their titles match; a difference is
lag only if it is recent, in one direction, and measured between the two records; and only the fields all
three systems share are compared, with "cannot say" kept apart from "disagrees".

**Every record is made up.** 37 invented work items in three invented systems. Nothing outside the
participant's computer was contacted, and the state of no real item was read or changed.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**not assessed** means nobody checked it.

## Approach

`participant/context/conflicts/records.md` holds the records, a table of links, and a table of what depends on
what. `conflicts.py report` reads it and writes `report.md`. That is all the skill does.

For each link, each pair of systems is compared on four fields: status, whether anyone is assigned, the due
date, and the title. Each pair gets one of four answers.

| Answer | When |
|---|---|
| agree | the two values are the same |
| not comparable | they differ, and one system has no way to say what the other says |
| lag | they differ, and the lag rule below holds |
| conflict | they differ, and it is none of the above |

The report shows, for every conflict, both values, what each source itself wrote, and when each last changed.
It then says why it is a conflict and what a person would need to find out to settle it, as the quest's hint
asks. It says nothing about which side is right.

## The lag rule

This is what the quest asks the proof to explain (criterion 3).

A difference is **lag**, and not a conflict, only if **all** of these hold:

1. **Both records say when they last changed.**
2. **Those two times are more than nothing, and at most 24 hours, apart.**
3. **For status, the record that changed later is the one further along.** The order is open, then in
   progress, then done or dropped.

So these are conflicts, and `logs/conflict-run.txt` part 3 shows each:

| Case | Why it is not lag |
|---|---|
| 24 hours and 1 second apart | Past the allowance. Nobody is catching up |
| 5 minutes apart, and the later record is the one LESS far along | A delay cannot explain it. Someone set the work back, or disagreed |
| Changed at the same moment | Neither is behind the other |
| Done against dropped, however close | Two different ends. A delay does not turn one into the other |
| One record with no time of last change | It cannot be told whether one side is behind |

Three choices in the rule need defending.

**The 24 hours are measured between the two records, not from today.** "Changed within the last day" is the
natural way to say it, and it needs a clock. Then the same records would give "lag" on Monday and "conflict"
on Wednesday with nothing having changed. Measured between the records' own times, the answer is a fact about
the records (criterion 6). The cost is real: the rule cannot say how long a difference has gone on. A lag that
was a lag last week is still a lag. Only the second stretch goal, comparing with the previous run, sees time
passing.

**Direction matters more than size.** A five-minute gap is a conflict if the later record is the one that is
behind. That was the case the participant's decision turned on: a tracker closed in the morning and a card
moved back to "Doing" in the afternoon is somebody disagreeing, and calling it lag would bury the most useful
kind of conflict there is.

**"Lag" does not mean the later value is true.** It means the pattern fits a delay. Both values and both times
are still shown, under "lag", and nothing is overwritten (criterion 4).

## One case I found ambiguous

**W-09: the tracker says done, the GitHub issue is open, six hours apart.**

By the rule it is lag. The tracker changed later, it is further along, and six hours is inside the allowance.
The report says "github may simply not have caught up".

It may never catch up. A GitHub issue is often left open for weeks after the work is finished, because closing
it is a separate act that nobody is prompted to do. If that is this team's habit, then W-09 is not a delay at
all. It is a standing difference that will look like lag for one day and then, with nothing having changed,
would be a conflict if either record were touched.

The rule cannot tell a delay from a habit, because the two leave the same evidence on the day. And it is
worse than that: W-02, the quest's own scenario, is the same pair of values, done against open. It is a
conflict only because its two records are six days apart, not six hours. So the line between "the work is
finished and the issue has not been closed yet" and "a report says finished and the issue says otherwise" is,
in my rule, a number of hours that I chose.

What would settle W-09 is not in the records: whether this team closes issues when work is done, and who is
meant to. The honest position is that the lag class is a convenience, to keep routine delays from drowning
the report, and that a careful reader should look at the lag section too. It is in the report, with both
values, for that reason (criterion 7).

A second, smaller ambiguity: GitHub saying `open` against another system's `in_progress` is "not comparable",
because open is the only thing GitHub can say. But GitHub's `open` against `done` **is** compared, since GitHub
can say closed. So the same word from GitHub is sometimes a statement and sometimes the absence of one,
depending on what it is set beside.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Linked items are compared field by field using their stable identities | recorded, tested | `logs/conflict-run.txt` part 2: 84 comparisons, each between two records one link names by identity. Planted bugs J, L, M |
| 2 | Each conflict lists both values, their systems and their last update times | recorded, tested | `participant/context/conflicts/report.md`, "Conflicts": 8, each with two rows. Part 2. Planted bugs F, I, R |
| 3 | A difference within a stated lag is classified as lag, not conflict | recorded, tested | The rule is stated at the top of `report.md`. Part 3: seven cases at its edges. 5 lags in the report. Planted bugs A to E, G |
| 4 | No value is overwritten and no winner is chosen | recorded, tested | Part 1: checksums of every file before and after, and a refusal to write over the records. Part 4: no word that picks a side, and no resolved value kept. Planted bugs N, O, P |
| 5 | A missing counterpart is reported as unlinked, not as a conflict | recorded, tested | `report.md`, "Unlinked records": 7. Part 5. Planted bug K |
| 6 | The same input gives the same report | recorded, tested | Part 6: two runs byte for byte the same, and the same again with the records and links in 10 other orders. No clock is read. Planted bugs A, Q |
| 7 | A reviewer can see why each item was or was not called a conflict | recorded | `report.md`, "Every comparison made": all 84, each with its answer and the reason in words |

## Artifacts

| Required item | File |
|---|---|
| The linked records | `participant/context/conflicts/records.md`: 37 records, 13 usable links |
| The conflict report | `participant/context/conflicts/report.md` |
| The run | `logs/conflict-run.txt`, 44 checks |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (36 tests), `logs/planted-bugs.txt` (22 planted bugs), `scripts/record_evidence.py`
and `scripts/planted_bugs.py`. The skill is `participant/skills/context-cross-system-conflicts/`: `SKILL.md`,
`conflicts.py`, `make_records.py`, `tests/test_conflicts.py`. Beside the records are `earlier-records.md`, the
same work five days before, and `previous-run.json`, what a run on it wrote.

What the records hold, as the quest asks: states that agree (W-01), states that differ (W-02, W-04, W-06,
W-07, W-08, W-11, and a due date in W-12), states that differ only by a stated lag (W-03, W-09, W-10, and an
assignment in W-13), and records with no counterpart (7, one of them a story that simply has none).

## What the report found

- **8 conflicts in 7 pieces of work.** The scenario, W-02, is two of them: done in the tracker against in
  progress on the board, and against open in the repository.
- **5 differences judged to be lag.**
- **6 differences that are not comparable**, each with the reason.
- **7 unlinked records and 3 links that could not be used**: one names a record that is not there, and two name
  the same card.
- **One pair with the same title and no link**, listed as a hint for a person and not compared.

## Stretch goals

- **Rank conflicts by how much downstream work they affect:** done. Conflicts are ordered by how many other
  pieces of work depend, directly or through another, on the one in conflict. W-02 is first, with three. The
  report says what the order means and what it does not: how much is waiting, not which side is right.
- **Report conflicts that have persisted across runs:** done. Against a run five days earlier, 6 of the 8
  conflicts were already there and 2 are new. "The same" means the same two records with the same two values.

## Reproduce

    python3 -m unittest discover -s participant/skills/context-cross-system-conflicts/tests -v
    python3 participant/evidence/context-cross-system-conflicts/context-attempt-006/scripts/record_evidence.py
    python3 participant/evidence/context-cross-system-conflicts/context-attempt-006/scripts/planted_bugs.py

None of these contacts anything. The second writes its reports to a scratch folder and checks that nothing in
`participant/context/conflicts` changed. The third changes `conflicts.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| Recorded checks | 44, all pass |
| Automated tests | 36, all pass (`logs/tests.txt`) |
| Planted bugs | 22 put into `conflicts.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |

Faults found while building:

- **A conflict's "what to find out" line took a side.** It read "whether github is still being kept up to
  date", which assumes the older record is the neglected one. It now asks why one has not changed while the
  other has, and who keeps each up to date. The check for words that pick a side had not caught it: it was a
  whole sentence leaning one way, with no forbidden word in it.
- The earlier snapshot was dated before some of the changes it held. Its dates were corrected.
- Three faults in the assistant's own tests: a helper named the same as a value, a count worked out wrongly,
  and a search for a clock that matched the words "datetime.timezone".

## What could not be done, and limitations

- **A link is a person's claim, and may be wrong.** A wrong link produces a "conflict" between two things that
  were never the same work. The report cannot detect that. It shows who stated each link. In this quest the
  links were written by the same assistant that wrote the records, so none is wrong by accident.
- **Work that nobody has linked is not compared.** The made-up card and issue both called "Fix export" may
  well be the same work. They are listed as a hint and no more. On real data most work would start unlinked,
  and the report would say little until someone did the linking.
- **The 24 hours is one number for every system and every field.** See the ambiguous case. A team might want
  a week for GitHub and an hour for a board.
- **Whether the word list for "no winner" is enough: not assessed beyond the list.** See the fault above. A
  sentence can lean without using any of the words.
- **The report compares canonical statuses.** If a board's "In Review" list had been mapped to done, W-02
  would agree and the scenario would vanish. The mapping is taken as given here.
- **Ranking uses a table a person wrote.** "Depends on" is as made up as the rest.
- **"Seen before" compares with one earlier run.** A conflict that came, went and came back counts as seen.
- **Nobody tried to read the report as a person deciding what is true.** Whether it helps them is not assessed.
- Three systems, 13 linked pieces of work, all written by the assistant to be one case each. A real set of
  records would be messier and mostly unlinked.

## Reflection

*Which system should you trust when they disagree, and why is that the wrong question for a report?*

My first instinct is the tracker. It has a workflow, somebody administers it, and "Done" there means a person
pressed a button. The board is habits and the issue is whatever nobody remembered to close.

That instinct is exactly what the scenario warns about. The tracker said Done, a report believed it, and the
work was not finished. And when I look at my own made-up cases, the trusted system is not even the same one
each time. In W-04 the board is the one I would believe: someone moved the card back to "Doing" hours after
the tracker was closed, which is a person saying "no, it is not done". In W-06 I cannot choose at all: one
system says finished and the other says abandoned, and those are not two views of one fact.

So it is the wrong question because the answer is not a property of the system. It is a property of what
happened, and what happened is not in either record. What decides it is always something outside: who moved
the card, whether this team closes its issues, which of two people was right. A report that picks a system is
quietly answering those questions without knowing the answers, and hiding that it did.

It is also the wrong question because of what a report is for. The moment my report says "probably done",
the disagreement is gone from the page, and the disagreement was the information. The person reading sees one
clean state and has no reason to ask anybody anything.

What surprised me is how hard it was to stay neutral even while trying to. I wrote a line for each conflict
saying what a person would need to find out, and one of them said "whether GitHub is still being kept up to
date". That sentence had already decided GitHub was the neglected one. I only saw it by reading the report
back. And the lag class is the same thing in a politer form: when I call something lag I am saying "the later
one is probably right, give it a day", which is trust by another name. I kept the class, because without it
the report would be noise. But I think it is the part of this quest I am least sure of.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Every record, identifier, project, board, repository and person's account is invented. The link table's
  "delivery lead" and "planning sheet PS-7" are made up too.
- No real item's state was read or changed. The skill has no code that could change one.

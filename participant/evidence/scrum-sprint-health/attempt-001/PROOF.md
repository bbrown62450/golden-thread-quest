# PROOF: Report Progress, Aging Work, Blockers, WIP, and Dependency Risk

Quest `scrum-sprint-health`, attempt `scrum-attempt-002`.

## How this was made

The snapshot, the generator, its tests, the recording scripts and this document were written by an AI assistant
(Claude) at the participant's direction. The participant made two decisions:

- **The snapshot records a limit on work in progress, of 2 for each person.** The branch for a snapshot that records
  none was built and tested too.
- **Aging is counted in calendar days.** The threshold, 3 days, is recorded in the snapshot.

**Everything in the snapshot is made up.** The project is a ferry timetable app that does not exist. The 24 items, the
dates and the four people are invented. Nothing was read from a tracker.

**Nothing was posted anywhere.** The generator reads one or two local files and writes one. No tracker, chat channel or
email was contacted, by the generator or by the assistant.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## The short version

- The report gives five things from one snapshot: progress, aging work, blocked work, work in progress for each name,
  and dependency risk. Every count lists its items. Every finding names the field it comes from.
- **For this snapshot:** 24 items. 4 done, 11 in progress, 7 not started, 2 the report cannot place. 5 aging. 4 blocked.
  Two names are 1 over the limit of 2. 7 waits, all 7 of them a risk by the report's rules. 8 gaps.
- **The scenario's two cases are both found.** Four items in progress have not been updated for 6 days. Two items wait
  on a third that is not started and has nobody recorded against it.
- **Two readers worked every number out again by hand**, one on each version, and found no wrong count, list, age or
  reason.
- **The generator was wrong twice in ways its own tests did not see.** Readers of the code found inputs on which it
  would have dropped rows silently or asserted something the snapshot did not support. None showed on this snapshot. It
  was corrected both times.
- **Nobody has read the handed-in version.** What changed after the last read is listed below.

## Approach

**Every number comes from a field, and so do both thresholds and the date.** The generator has no threshold of its own.
The aging threshold is the snapshot's `aging_after_days`, the limit is its `wip_limit_per_person`, and the day every age
is counted to is its `snapshot_date`. The computer's clock is never read.

**A blank is a gap, and a gap is never filled in.** A blank status is not "not started". A blank assignee is not
"unassigned". A blank `blocked_by` is not "none". Each is listed in section 6 with what the item is left out of.

**Three answers, not two.** Where a field cannot be used, the report says "cannot be told". It does not say "no". An
item in progress with no update date is neither aging nor not aging. A wait on an item whose assignee is blank is not
filed under "no risk rule holds".

**No title is read.** The program touches a title in two places: where it stores it, and where it prints it in section
8. An item titled "BLOCKED: ..." is not blocked, because its `blocked_by` says none.

**The report counts work and says nothing about a person.** A count beside a name is the number of items recorded
against that name, with which of them are blocked and which are aging.

The rules are in `participant/skills/scrum-sprint-health/SKILL.md`.

## The aging threshold, and why

**An item in progress is aging when its `updated` date is more than 3 calendar days before the snapshot's date.**

- **3 days, because the snapshot says so.** `aging_after_days: 3` is a line of the snapshot. A team records what it
  agreed there. With another number in that line the report uses that number (tested). With no such line the report
  says none is set and calls nothing aging (tested). With a line it cannot use, such as "3 days", it says so and lists
  a gap. It does not say none is set (tested).
- **"More than", not "at least".** The quest says "older than a stated threshold". At exactly 3 days an item is not
  aging. In the snapshot of day 6, FERRY-209 is at exactly 3 days and is listed as not aging (recorded). On day 7 it is
  at 4, and is aging.
- **Counted to the snapshot's own date**, 2026-11-17. Not to the day the report is generated. That is what makes two
  runs give the same bytes.
- **Calendar days, which was the participant's decision.** A weekend counts. This is the weakest part of the number:
  FERRY-209's 4 days are Friday to Tuesday, 2 working days. So each age gives its weekday and how many of its days are
  a Saturday or Sunday, and the reader can see it. The report knows of no holiday.
- **Only items in progress.** An item not started for 8 days is not aging. It shows up in progress, and in dependency
  risk if something waits on it.

## One item the report could not classify

**FERRY-222. Its status is `in_review`.** The snapshot defines three statuses: `todo`, `in_progress` and `done`.
`in_review` is none of them.

The report does not guess. It could be taken as in progress, or as nearly done. Either would be an estimate. So:

- It is in none of the three counts of section 1, and is named there as in none.
- It is not in the count of work in progress for the name it is recorded against. Section 4 says so, and says that
  count may be higher than shown.
- It has a gap entry: `it is "in_review", which is not one of todo, in_progress, done, written exactly so. The report
  cannot classify it.`

What would settle it is a line in the snapshot saying what `in_review` counts as.

Seven other gaps are in section 6 of the report. Among them: FERRY-217 has no status, FERRY-218 no update date,
FERRY-219 no assignee, FERRY-220 no `blocked_by`.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Progress is computed from recorded status and shows the items counted | **recorded, tested, observed** | Section 1 of the report. `logs/health-run.txt` part 3 counts each status again with its own code. Both readers recounted by hand |
| 2 | An item is aging when its last update is older than a stated threshold, and the threshold is shown | **recorded, tested, observed** | The threshold is at the top of the report and in section 2. Part 3 works out each age, weekday and weekend count again. The case at exactly the threshold is recorded from day 6 |
| 3 | An item is reported as blocked from a recorded blocker field, not from words in its title | **recorded, tested, observed** | Section 3. FERRY-211's title begins "BLOCKED:" and it is not listed. A test checks that the program uses a title in two places only |
| 4 | Work in progress per person is counted, and the limit is stated or the report says none is set | **recorded, tested, observed** | Section 4. Part 3 recounts and works out each comparison with the limit again. The "none is set" branch is recorded and tested on the same snapshot with the line taken out |
| 5 | A dependency risk names both items and why the link is a risk | **recorded, tested, observed** | Section 5. Part 3 works out every wait and every reason D1 to D4 again, and compares the field each link is in |
| 6 | An item with a missing field is a gap, not estimated | **recorded, tested, observed** | Section 6. Part 4 finds the blank cells itself and checks that each item is in the "cannot be told" line and in no other |
| 7 | The report generated twice from the same snapshot is identical | **recorded, tested** | Part 1: two runs 2 seconds apart, and a third from copies under other names in another folder. All three are byte for byte the same, and the same as the handed-in report |

"Observed" is of the version each reader had. See "What independent readers found".

**"Risk" is the report's own word.** Criterion 5 asks why a link is a risk and does not say what makes one. The four
rules D1 to D4 are this skill's. All seven waits in this snapshot meet one of them.

## Where the important artifacts are

Required by the quest:

| File | What it is |
|---|---|
| `participant/context/scrum/sprint-snapshot.md` | The made-up snapshot. 24 items, day 7 of 10 |
| `participant/context/scrum/sprint-health.md` | The report |
| `participant/evidence/scrum-sprint-health/attempt-001/logs/health-run.txt` | The report generated twice, and the gaps. A copy: see below |
| `participant/evidence/scrum-sprint-health/attempt-001/PROOF.md` | A copy of this file |

The quest text names `attempt-001`. The app's Start button made `scrum-attempt-002`, which is where the work is.
`attempt-001/` holds copies, so the path the quest names exists.

The rest:

| File | What it is |
|---|---|
| `participant/skills/scrum-sprint-health/health.py` | The generator and its check |
| `participant/skills/scrum-sprint-health/SKILL.md` | The rules, and what the check does and does not look at |
| `participant/skills/scrum-sprint-health/make_snapshot.py` | Writes the two made-up snapshots |
| `participant/skills/scrum-sprint-health/tests/test_health.py` | 146 tests |
| `participant/context/scrum/health/day-06/` | The snapshot of the day before, and its report |
| `scrum-attempt-002/logs/health-run.txt` | 81 recorded checks |
| `scrum-attempt-002/logs/tests.txt` | The test run |
| `scrum-attempt-002/logs/planted-bugs.txt` | 85 bugs put into the generator one at a time. Each was caught by a test |
| `scrum-attempt-002/logs/independent-read.txt` | What five readers found, and what was changed |
| `scrum-attempt-002/scripts/` | The two scripts that wrote those logs |

## Stretch goals

- **Two days, with what changed.** Done. Section 7 compares day 7 with day 6: one item added, two statuses changed, one
  item newly aging, one `depends_on` changed. It says what it compares and what it does not. Part 5 of the record finds
  the same five differences with its own code.
- **A dependency chain longer than two.** Done. FERRY-210 waits on FERRY-208, which waits on FERRY-207. Chains of any
  length are reported whole (tested with four). Items that depend on each other are reported as a loop, not as a chain.

## How to reproduce

From the repository's top folder. Python 3.9 or later, and nothing to install.

    python3 participant/skills/scrum-sprint-health/make_snapshot.py
    python3 participant/skills/scrum-sprint-health/health.py generate --snapshot participant/context/scrum/sprint-snapshot.md --previous participant/context/scrum/health/day-06/sprint-snapshot.md --out participant/context/scrum/sprint-health.md
    python3 participant/skills/scrum-sprint-health/health.py check --snapshot participant/context/scrum/sprint-snapshot.md --previous participant/context/scrum/health/day-06/sprint-snapshot.md --report participant/context/scrum/sprint-health.md
    python3 -m unittest discover -s participant/skills/scrum-sprint-health/tests
    python3 participant/evidence/scrum-sprint-health/scrum-attempt-002/scripts/record_evidence.py
    python3 participant/evidence/scrum-sprint-health/scrum-attempt-002/scripts/planted_bugs.py

The first two rewrite files that are already there, with the same bytes. The last changes `health.py` while it runs and
puts it back. It takes a few minutes.

## What was tested or validated

- **146 tests, all passing.** `logs/tests.txt`.
- **81 recorded checks, all passing.** `logs/health-run.txt`. Parts 3 to 5 work each number out again from the
  snapshot's rows with the script's own code, not the generator's. That code reads only this snapshot's shape.
- **85 planted bugs, all caught.** `logs/planted-bugs.txt`. Each is one wrong line put into the generator. A bug that
  no test caught meant a test was missing. Two were found that way and the tests were added.
- **The check can fail.** Part 6 spoils the report 16 ways and one way in the snapshot, and each is reported. A pass on
  the generator's own output shows little: the check reads the snapshot with the generator's code.
- **A snapshot wrong in its form.** Part 7 tries 11: a blank line in the table, a missing line of dashes, a threshold
  written as "3 days", a threshold given twice, "TBD" for a name, a bar inside a title, and others.

## What independent readers found

Five fresh AI assistants read the work, in two rounds. **No person read it.** They were told to read only what they
were given and to run nothing. Those limits were not enforced. The full account is in `logs/independent-read.txt`.

- **The numbers.** One reader on each version worked every number out by hand. Neither found a wrong one.
- **Round 1, the code.** A blank line in the table dropped every row after it. An unusable threshold was reported as
  "none is set". "TBD" was counted as a person. A wait on an item with a blank assignee was filed under "no rule
  holds". The report's bytes depended on where the file was. The generator was rewritten.
- **Round 1, the report.** Over the limit stood beside a name without showing that two of those items were blocked by
  others. Ages gave no weekday. Both were changed.
- **Round 2, the code.** Three of the same kinds of fault survived in other places, and there were new ones: an item
  with no usable status listed as "not done"; an unusable date called "not recorded"; an item whose row was broken said
  to be "not in the snapshot"; a chain behind a loop never reported. All were corrected.
- **Round 2, the report.** "Aging: none" beside a name with one item whose update date is blank. Corrected: the line
  now says for which items it cannot be told.

**Faults found while building, before any reader:** an item blocked by something not in the snapshot dropped out of the
blocked list. The report used the word "should". A planted bug showed no test covered a done item that still names a
blocker.

**What changed after the last read, and was not read again.** In the report: three sentences, the "cannot be told for"
at the end of each count for a name, one added line in section 3, a longer "Not compared" sentence, a few words at the
top, and the checksums. No count, list, age, risk or gap changed. In the generator: every correction from round 2. Those
are covered by tests and planted bugs, and by no reader.

## Remaining limitations

- **Calendar days.** An age over a weekend looks older than the working time it covers. The report shows the weekend
  days. It does not subtract them.
- **Items are counted, not size.** Four done of 24 says nothing about how much work is left.
- **"Risk" means one of four rules holds.** Any wait on an item that is not started is a risk by D1. A team may not
  think so.
- **`updated` is whatever the tracker counts as a change.** A comment resets it.
- **The words for nobody are a fixed list.** "TBC" would be counted as a name. Two names in one cell are one name.
- **Two spellings of one name are two names.**
- **The check is not independent of the generator**, and has blind spots. SKILL.md lists what it does not look at, and
  three ways it can fail a correct report.
- **It was not made safe against a snapshot written to break it.** A file that is not UTF-8, a chain of about a
  thousand items, or a very dense set of dependencies ends or exhausts it.
- **Over the limit and aging stand beside a name on one line.** The report says a count is not a measure of anyone. A
  reader said the line can still be read as one.
- **One snapshot, made up by the same assistant that wrote the generator.** A real tracker's export would have cases
  nobody here thought of.
- **A teammate was not walked through the report.**

## Reflection

*Which number in your report would a team most want to argue with, and what would settle it?*

The number I'd expect a team to argue with is "Waits that are a risk (7)". All seven waits come out as a risk, and they
are really three situations: two items waiting on one aging item, two waiting on an item nobody has started or picked
up, and a pair that name each other, which is probably one mistake in the tracker. My four rules call any wait on a
not-started item a risk, and on most teams that is just ordinary sequencing. What would settle it is the team, not me.
They would decide which of the four rules they actually count as a risk and record that in the snapshot, the same way
the aging threshold and the limit on work in progress are recorded there. Then the report applies their rule and not
mine.

The second one is FERRY-209's "4 days". It is aging only because a weekend fell inside it. The report now prints the
weekday and the weekend days so a team can see that for themselves. What would settle it is one line in the snapshot
saying whether their threshold means calendar days or working days.

## Sensitive values

None. The snapshot is made up: no real person, project, item or tracker is named. There is no token, password or key
in any file here. No path on anyone's computer is in the logs: the scratch folder is written as SCRATCH.

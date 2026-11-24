# PROOF: Build Work and Decision Dependency Indexes

Quest `context-dependency-map`, attempt `context-attempt-007`.

## How this was made

The made-up data, the skill, its tests, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made two decisions: a dependency is read
from three named fields and from nothing else, with `parent` never counted; and "blocking the most" counts
everything that cannot finish until an item is done, with the direct count shown beside it.

**Every record is made up.** The project, a ferry timetable app, does not exist, and no identifier belongs to a
real item. The participant's real sandbox cards and issues, which are in the repository from earlier quests,
were not used. Nothing outside the participant's computer was contacted, and no record was changed.

Words used below: **recorded** means the saved log of the run shows it. **tested** means an automated test
checks it. **not assessed** means nobody checked it.

## Approach

`participant/context/dependencies/data.md` holds 39 records: 34 work items across three made-up systems, and 5
decisions. Each record is a block of JSON under its identity.

`depmap.py build` reads the records and writes `index.md`:

1. **Problems**, each with the items named: cycles, links to something with no record, and seven lesser kinds.
2. **The five items blocking the most**, with their counts.
3. **The longest chain.**
4. **What happens if the top item slips.**
5. **The forward index**: for each item, what it waits on.
6. **The reverse index**: for each item, what waits on it.

Every line of both indexes says which field, on which record, the link was read from, and whether the link
still holds work up.

The build ends with exit code 1 when it has problems to report. On this data it reports 16, on purpose, so
the recorded run ends with exit code 1. That is the index complaining, as the quest asks. It is not a failed
run: exit code 2 is the one that means nothing was built.

## How cycles are detected (criterion 3)

This is the first thing the quest asks the proof to explain.

The links make a graph: an arrow from each item to each item it waits on. A cycle is a set of items in which
every one can be reached from every other by following arrows. The name for such a set is a strongly connected
component, and the build finds them with Tarjan's algorithm.

In plain words: it walks the arrows from an item as deep as they go, numbering each item as it first arrives
and keeping the items of the current walk on a stack. When an arrow leads back to an item still on the stack,
the walk has come round, and each item remembers the lowest number it can get back to. When the walk backs out
of an item that can get back no further than itself, everything above it on the stack is one component. A
component of two or more items is a cycle.

Four choices went with it:

- **Every recorded link is used, whatever the status of the items.** A cycle among finished items is still a
  fault in the records.
- **The report gives the members and one way round.** The members are the answer to "which items". The way
  round, "A waits on B waits on A", is what a person needs to see that it is true. The log checks that every
  step of each way round is a recorded link.
- **Two rings that share an item are reported as one group.** Every item in the group does wait on every
  other, so that is true, and it is less than a person might want: the report does not list each ring.
- **An item that names itself is reported separately**, as SELF. It is a slip of the hand, not two items
  waiting on each other.

The log does not take the algorithm's word for it. Part 5 finds the same six items a second way, by starting
from each item in turn and following links to see whether it comes back.

The data holds two cycles. One is the scenario's: `jira:52010` and `jira:52011` wait on each other. The other
runs through a decision: a story waits on an open question, the question waits on a spike, and the spike
waits on the story.

## One dependency I chose not to infer (criterion 1)

This is the second thing the quest asks for.

`jira:52023` has the title "Timetable PDF export, once the search API (jira:52003) is done". Its description
says "Depends on jira:52003 and cannot start before the import, jira:52002, is finished."

That reads as two dependencies, with the identities written out. **The index gives `jira:52023` no link**, and
`jira:52003` is not shown as waited on by it. The record has no `blocked_by`, no `blocks` and no
`needs_decision`, and those are the only fields a link is read from.

Why not take it? Because a sentence is not a record. Somebody typed that title once. Nobody has to keep it
true, nothing updates it when the plan changes, and a program that reads it has to guess what "once" and
"depends on" mean in every phrasing people use. The cost is plain, and it is in this data: the PDF export is
planned to start on 7 December, the search API finishes on 18 December, and the index says nothing about it.
The index is right about what is recorded and silent about something a person can see.

The log shows the rule holds both ways (part 3). With every title, description and label replaced by words
that name other items, the links are the same 28. With the three fields taken off every record and the titles
left alone, there are no links at all.

Two more things are not inferred, and the index lists both under "Seen and not counted" so that a reader can
see they were noticed: `parent`, which is grouping, and `related`, which says two items have to do with each
other and says nothing about order.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Dependencies come from recorded fields, not from words in a title | recorded, tested | `logs/dependency-run.txt` part 3: all 28 links listed with the field and record each came from. They are exactly the pairs written in the three fields, read a second time separately. Tests `RecordedFieldsOnly` |
| 2 | A forward and a reverse index are both generated | recorded, tested | `participant/context/dependencies/index.md`. Part 4: each has an entry for all 41 items and holds all 28 links once, and one is the other turned round |
| 3 | A cycle is reported with the items in it | recorded, tested | Parts 1 and 5: both cycles, each with its members and one way round, printed by the build and written in the index. Found again by a second method. A cycle broken is no longer reported, and one made is |
| 4 | A link to a missing item is reported by name, not dropped | recorded, tested | Parts 1 and 6: `decision:E-209` and `jira:52999` are named, each with the records that name it. Both links stay in the forward index, and each missing item has its own entry in both indexes. Deleting a record makes it reported in turn |
| 5 | A dependency on a decision is represented like one on a work item | recorded, tested | Part 7: 6 links are to a decision, in the same table of links and the same two indexes. A decision is counted and ranked: `decision:E-209` is third among those blocking the most. Written as `blocked_by` in place of `needs_decision`, the result is the same |
| 6 | The five items blocking the most other items are listed with their counts | recorded, tested | Part 8: the five, with totals 8, 5, 3, 3 and 2, and the direct count beside each. Counted again by a different method for every item in the data. Six more items are level with fifth place, and the index names them |
| 7 | The index is identical across two runs on the same input | recorded, tested | Part 2: the second run's index has the same SHA-256 as the first. Five more runs in separate processes with different hash seeds, and 20 with the records and lists shuffled, give the same index |

## Artifacts

| Required item | File |
|---|---|
| The data | `participant/context/dependencies/data.md`, 39 records. It names the field each link comes from, in a table of every recorded link and in each record |
| The index | `participant/context/dependencies/index.md` |
| The run | `logs/dependency-run.txt`, 51 checks |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (86 tests), `logs/planted-bugs.txt` (31 planted bugs), `scripts/record_evidence.py`
and `scripts/planted_bugs.py`. The skill is `participant/skills/context-dependency-map/`: `SKILL.md`, `depmap.py`,
`make_data.py`, `tests/test_depmap.py`.

`data.md` is written by `make_data.py` and `index.md` by `depmap.py build`. A test and a log check compare each
with what the code writes, so neither was adjusted by hand.

Some records hold text that reads like a dependency or an instruction, such as the title and description of
`jira:52023`. That text is sample data, put there to show it is not acted on.

## Stretch goals

- **The longest chain:** done. Six items across three systems: release notes wait on the mobile search screen,
  which waits on the search page, the search API, the import and the schema. The log checks that every step
  is a recorded link, and that no longer path exists outside the cycles, by trying every path.
- **How an item's slip affects its dependents:** done. `depmap.py slip IDENTITY DAYS`, and a table in the index
  for the item that blocks the most. If the schema finishes 5 days late, three items move 3 days, two move 1
  day and three do not move, because the plan had room. An item that waits on a cycle is reported as "cannot
  be dated".

## Reproduce

    python3 participant/skills/context-dependency-map/depmap.py build --out SCRATCH/index.md
    python3 participant/skills/context-dependency-map/depmap.py slip jira:52001 5
    python3 -m unittest discover -s participant/skills/context-dependency-map/tests -v
    python3 participant/evidence/context-dependency-map/context-attempt-007/scripts/record_evidence.py
    python3 participant/evidence/context-dependency-map/context-attempt-007/scripts/planted_bugs.py

SCRATCH is any folder outside the repository. Without `--out`, the build writes `index.md` beside the data,
which gives the same file. None of these contacts anything. The fifth changes `depmap.py` while it runs and
restores it.

## What was tested

| What | Result |
|---|---|
| The handed-in data | 39 records, 28 links, 16 problems reported. Exit code 1, as intended |
| Recorded checks | 51, all pass. They include 7 builds from data with one thing changed |
| Automated tests | 86, all pass (`logs/tests.txt`) |
| Planted bugs | 31 put into `depmap.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |

What building turned up:

- **The index found two things in the data that were not put there on purpose.** `jira:52008` was written to
  show a link recorded on the blocker only. The index also reported it as planned to start on the day its
  prerequisite starts. The same happened with the spike in the second cycle. Both are true of the data as
  written, and the assistant had not noticed either.
- **A test was missing for criterion 7.** Listing items in the order Python keeps a set changes the index
  between runs, and no test inside one process could be relied on to see it, since the order only changes
  from process to process. A test that builds the index in five separate processes with different hash seeds
  was added before the planted bugs were run. The planted bug of that kind is caught by it.
- **No fault was found in `depmap.py` itself.** The 85 tests first written passed on their first run. That is
  weaker than it sounds: the same assistant wrote the code and the tests, and holds the same wrong ideas in
  both. The planted bugs show the tests can fail. They do not show the code is right where no test looks.

## What could not be done, and limitations

- **The index is only as good as the fields.** Half the links in this data, 14 of 28, are written at one end
  only, and the index lists them. A link written at neither end does not exist for it, however plainly a
  title states it. That is the rule the quest sets, and `jira:52023` is what it costs.
- **It does not say which link in a cycle is wrong.** It reports the ring. A person has to decide which link
  to remove.
- **Every item counts as one.** An item that blocks eight small tasks ranks above one that blocks the release.
  Six items are level with fifth place, so the fifth place itself is decided by the tie-break.
- **In a cycle, the counts are large for a bad reason.** Each member blocks the others. The table marks such
  rows "in a cycle".
- **`decision:` is not in the approved identity rules.** Those rules cover three systems. This quest adds a
  fourth prefix for decisions, in its own files only, and the approved rules were not changed.
- **A decision's entry number is trusted.** Nothing here checks it against the decision log from the earlier
  quest. The decisions in this data are made up for this quest.
- **"Done" is taken on trust**, and so is "decided". The index reports an item finished before its
  prerequisite, and cannot tell whether either status is true.
- **Dates are calendar days.** The slip knows nothing of weekends, holidays or who is free. An item with no
  planned dates, and every decision, is left out of the dates.
- **"Will never finish" is the index's wording** for waiting on a dropped item or a superseded decision. It
  is a strong phrase for what may be an out-of-date link.
- **One file, 39 records, written by the same assistant that wrote the program.** It was not tried on records
  as three real systems deliver them, where a link may be an object, a URL or a number.
- Nobody else has read the index or tried to break the build.

## Reflection

*Which dependency in your data would be easiest to miss in a real tracker?*

The mobile search screen waiting on the search page.

The mobile screen is a GitHub issue. The search page is a Jira story. The link is written once, as
`blocked_by` on the GitHub issue, and nowhere on the Jira side. So the person who owns the search page opens
their story and sees that nothing is waiting on it. They would have to go and look in a different tool, at
an issue they have no reason to open, to find out that it is.

And it is not a side link. It sits in the middle of the longest chain in the data: release notes, mobile
screen, search page, search API, import, schema. If the search page slips, the mobile work and the release
notes move with it, and the one person who could warn them has no sign that they exist.

I expected to pick the decision that was never recorded, because that is the scenario and it is dramatic. But
that one is not easy to miss once you have an index. It shows up by name, with three items stuck behind it, in
third place on the list. The index is loud about a link that points at nothing. It is quiet about a link that
is real and written on the wrong side of a boundary, because to the index that link is fine.

What surprised me is how many there are. Half the links in my data are written at one end only. I made the
data up, so that number means little, but the reason for it does not: a link between two tools can only ever
be written in one of them. That is what the reverse index is for, and I understand the hint now. "Who is
waiting on me?" is the question people ask because it is the one their own tracker cannot answer.

The one that still bothers me is the PDF export, whose title says it waits on the search API. I chose not to
read that, and I would choose it again, but the index is silent about something anyone can see. If I were
running this for real, I would want a list of items whose words name another item and whose fields do not.
Not as links. As questions for a person.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Every record is invented: the identifiers, the titles, the dates and the decisions.
- No value was copied from a real record, including the participant's own sandbox records in this repository.

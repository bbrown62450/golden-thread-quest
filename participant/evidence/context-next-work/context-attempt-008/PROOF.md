# PROOF: Rank Next Work from Local Markdown with Cited Reasons

Quest `context-next-work`, attempt `context-attempt-008`.

## How this was made

The made-up records, the skill, its tests, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made two decisions: rank by a strict order
of criteria, priority first, with no weights and no score; and take blocked items out of the ranking, keep
stale items in it with a warning, and never offer a stale item as the thing to start.

**Every record is made up.** The project, a school meals ordering app, does not exist, and no identifier belongs
to a real item. The participant's real sandbox cards and issues, which are in the repository from earlier
quests, were not used. Nothing outside the participant's computer was contacted.

**The recommendation is advice.** Nothing was started, assigned or changed. The skill writes one file and never
writes to a record.

Words used below: **recorded** means the saved log of the run shows it. **tested** means an automated test
checks it. **not assessed** means nobody checked it.

## Approach

`participant/context/next-work/inputs.md` holds 22 work items and 2 decisions. `rank.py rank` puts every work
item on exactly one of three lists.

| List | When | In the handed-in run |
|---|---|---|
| Not offered | finished, under way, or somebody has it | 3 |
| Blocked | waiting on something not finished. The blocker is named | 6 |
| Ranked | everything else | 13 |

The ranked items are ordered by five criteria: priority, due date, the number of open items waiting on it,
created date, and identity. The first one on which two items differ decides between them.

Each ranked item then gets four reasons, one for each criterion that reads a field, and each reason quotes the
field and its value. It also says which criterion put it below the item above, and which decides against first
place.

Two things are reused from earlier quests and not changed. The limit for stale context, 24 hours for a work
item, is read from the approved freshness policy. A blocker is recorded in `blocked_by`, `blocks` or
`needs_decision`, as in the dependency index.

**"Start here" is not always first place.** It is the first ranked item whose copy is fresh. In the handed-in
run, first place is `jira:61004`, whose copy is 7 days old. The recommendation names it, with its warning, and
says to start with `jira:61001` at place 2.

## How conflicting criteria were weighed

This is the first thing the quest asks the proof to explain. The short answer: they were not weighed. They
were put in an order, and an earlier one always wins.

The data holds the conflict on purpose. `jira:61008`, "Low balance reminder", is low priority and due the day
after the clock value. `jira:61003`, "Receipt email", is high priority and due nine days out. Under the rule
the recommendation uses, the receipt email is at place 5 and the reminder at place 12, below eight items that
are due later than it is and two that have no usable due date.

A points score could have balanced the two. It was not used, for one reason: a score gives the reason for a
place as a number, and nobody can argue with "it scored 71". With an order, the reason the reminder is at 12
is one field: its `priority` is `low`. A person who thinks that is wrong can see what to change, and
`logs/ranking-run.txt` part 8 shows it works: for 11 of the 12 pairs of neighbours, changing the one field
named puts the lower item above the upper one. The twelfth pair is decided by identity, which is not edited.

The cost is real and the proof does not hide it. The order is blunt. Urgency never beats priority, however
close the date. So the second rule was built to show what the choice costs (the first stretch goal):

| | Priority first (used) | Due date first |
|---|---|---|
| `jira:61008` Low balance reminder | place 12 | place 2 |
| "Start here" | `jira:61001` Allergen labels | `jira:61008` Low balance reminder |

Same records, same clock, and a different answer to "what should I do next". Neither rule is right. The rule
is a decision somebody has to own, and the recommendation prints which rule it used at the top.

Three smaller conflicts were settled the same way, by stating an order:

- **Stale against rank.** A stale item keeps the place its fields give it, and is never the item to start.
  Dropping it would hide that it may be the most important thing on the list. Trusting it is the scenario.
- **Blocked against priority.** A blocked item has no place at all, however high its priority. `jira:61010` is
  high priority and due in three days, and it is not ranked, because it waits on a question nobody has
  answered.
- **Missing against present.** An item with no priority goes after every item that has one. It is not given a
  middle value to be fair to it.

## One recommendation I would not trust

This is the second thing the quest asks for.

**`jira:61008`, "Low balance reminder", at place 12 of 13, confidence high.**

Everything the ranking says about it is true. Its priority is recorded as low. Its copy is fresh. Nothing is
missing. So its confidence is high, and that is the trouble: **confidence here measures how complete the data
is, and says nothing about whether the advice is good.** A low-priority reminder due tomorrow, placed below
"Menu photo upload", which has no usable due date at all, is a place the rule gives with a straight face.

A person reading "place 12, confidence high" would reasonably take it to mean "safely ignore this for now". It
means "every field was present". If the due date is real, somebody should look at this item today, and the
ranking will never say so.

Two more that deserve less trust than they appear to:

- **`jira:61004` at place 1.** The ranking itself does not trust it, and says so. That is the system working.
- **`jira:61017`, "Refund flow", listed as blocked.** Its blocker's copy is 10 days old. It may not be blocked
  at all. The recommendation says that, and still lists it as blocked, because it cannot show otherwise.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Every ranking reason cites a recorded field of the item | recorded, tested | `logs/ranking-run.txt` part 3. All 76 reasons name a field in backticks, and each reason about priority, due date or created date gives the value the record holds. `votes` and titles are shown not to affect the order. **One reason reads fields on other records:** the count of items waiting is taken from `blocks` on the item and from `blocked_by` on the items that name it. Each is cited with the record it is on |
| 2 | Blocked work is excluded or ranked last with the blocker named | recorded, tested | Part 4. Excluded: 6 blocked items have no place. Each names its blocker, the blocker's status, and the field and record the link is written in. Each one, with its blocker finished in a copy, is ranked |
| 3 | Items with stale context carry a warning | recorded, tested | Part 5. 4 items are stale. Each carries a warning that gives the field, the age and the limit. A copy at exactly 24 hours is fresh and one a second older is stale. "Start here" skips the stale first place |
| 4 | Ties are broken by a stated rule | recorded, tested | `participant/context/next-work/rules.md` sections 2 and 3. Part 6: for every pair of neighbours, the two are level on every criterion before the one named and differ on it. The handed-in data uses all five levels, down to identity |
| 5 | Missing data lowers confidence and is reported, not filled in | recorded, tested | Part 7. 4 ranked or blocked items have missing data. Each says so in its reasons and has lower confidence. Nothing is filled in: the inputs are unchanged, and the item with no priority is last |
| 6 | The same input gives the same ranking | recorded, tested | Part 1. Two runs print the same lines and write the same file, by SHA-256. So do five more in separate processes and 20 with the records shuffled. The clock value is part of the input, and without one the ranking refuses to run |
| 7 | A person can disagree with a reason and see which field to change | recorded, tested. not assessed for a person | Part 8. For 11 of 12 pairs of neighbours, changing the field named moves the item above its neighbour. The recommendation ends with a table of what to change for each kind of disagreement. **No person tried it** |

## Artifacts

| Required item | File |
|---|---|
| The inputs | `participant/context/next-work/inputs.md`, 24 records. A table at its top says which record shows what |
| The ranking rules | `participant/context/next-work/rules.md` |
| The recommendation | `participant/context/next-work/recommendation.md` |
| The ranking run | `logs/ranking-run.txt`, 56 checks. Runs 1 and 2 are in part 1. The run after a dependency was completed is part 2 |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (73 tests), `logs/planted-bugs.txt` (31 planted bugs), `scripts/record_evidence.py`
and `scripts/planted_bugs.py`. The skill is `participant/skills/context-next-work/`: `SKILL.md`, `rank.py`,
`make_inputs.py`, `tests/test_rank.py`.

All three files in `participant/context/next-work/` are written by the skill. A test and a log check compare
each with what the code writes, so none was adjusted by hand.

## The run after a dependency was completed

In a copy of the inputs, one field was changed: `status` of `jira:61001`, "Allergen labels on the menu", from
`open` to `done`. Two items wait on it.

- `jira:61005` and `jira:61009` were blocked, and are now ranked at places 9 and 13.
- `jira:61001` left the ranking. It is not offered, because its `status` is `done`.
- "Start here" changed from `jira:61001` to `jira:61002`.
- Every other item that moved did so only because of those three, and the log says which for each.

The log prints the field that differs between the two inputs, and a reason for every item whose list or place
changed (part 2).

## Stretch goals

- **How the ranking changes under a different priority rule:** done. `--rule due-first`. Told above, and in
  part 10 of the log.
- **Why an item was not ranked first:** done. Every item below first place says which criterion decides
  against first place, with both values.

## Reproduce

    python3 participant/skills/context-next-work/rank.py rank --out SCRATCH/recommendation.md
    python3 participant/skills/context-next-work/rank.py rank --rule due-first --out SCRATCH/due-first.md
    python3 -m unittest discover -s participant/skills/context-next-work/tests -v
    python3 participant/evidence/context-next-work/context-attempt-008/scripts/record_evidence.py
    python3 participant/evidence/context-next-work/context-attempt-008/scripts/planted_bugs.py

SCRATCH is any folder outside the repository. Without `--out`, the first command writes `recommendation.md`
beside the inputs, which gives the same file. None of these contacts anything. The fifth changes `rank.py`
while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| The handed-in inputs | 22 work items: 13 ranked, 6 blocked, 3 not offered. Exit code 0 |
| Recorded checks | 56, all pass |
| Automated tests | 73, all pass (`logs/tests.txt`) |
| Planted bugs | 31 put into `rank.py` one at a time, including "the most votes goes first". Every one made at least one test fail (`logs/planted-bugs.txt`) |

Faults found while building:

- **A blocker written at both ends was cited at one end only.** `jira:61005` was shown as blocked "recorded in
  `blocks` on `jira:61001`", and its own `blocked_by` was not mentioned. A person who disagreed would have
  been sent to the wrong record. Found by reading the recommendation, not by a test. Both fields are now
  cited.
- **The reasons were listed in the order they were worked out, not the order of the rule.** Created date came
  before the number waiting, which is the wrong way round and would mislead a reader about what was looked at
  first. Found the same way.
- Two expected values in the assistant's own tests were wrong: places after the dependency was completed were
  worked out in the head and were off by one. The program was right.
- A trial in the recording script failed on an item with no due date, because the trial assumed every item
  has one. The trial was at fault.

No fault in the ranking order itself was found by the tests. As in earlier quests, that is weaker than it
sounds, since one assistant wrote the code and the tests.

## What could not be done, and limitations

- **Confidence is not correctness.** Told above. It is the limitation that matters most.
- **The ranking is only as good as the recorded priority.** Nothing here checks that "high" was set by someone
  with the right to set it, or recently.
- **A stale copy's place is still shown.** The warning is plain, and "Start here" skips it. A reader who looks
  only at the table of places sees a stale item at place 1 with the word STALE beside it.
- **One limit for every field.** A due date does not go out of date the way a status does, and both are
  treated as stale after 24 hours.
- **It does not know who is asking.** It ranks unassigned open work for anyone. Skills, capacity and the size
  of a piece of work are not in the records and are not guessed.
- **Only direct waiters are counted.** An item at the start of a long chain counts the same as one with a
  single item behind it. The dependency index from the last quest counts the whole chain, and it was not
  joined to this.
- **A link that cannot be read is warned about and not treated as a blocker.** So an item with a badly written
  `blocked_by` is ranked, at lower confidence. That errs towards offering work that may be blocked.
- **The data was written by the assistant that wrote the program**, with one clean case of each kind.
- **Nobody tried to disagree with it.** Criterion 7 is about a person, and no person was asked.
- The freshness policy says a tool may use the computer's clock when no clock value is given, and says so.
  This skill is stricter and refuses. That is a choice made for criterion 6.

## Reflection

*What would you want the ranking to refuse to do?*

Three things it does refuse, and one it does not, which is the one I think about.

It refuses to act. It will not start a piece of work, assign one or change a field. It writes a file of
advice and stops. I would not want that softened. The moment a ranking can assign work, a wrong priority
somewhere stops being a bad suggestion and becomes somebody's week.

It refuses to guess the time. Without a clock value it stops. That seemed fussy when I chose it, and then I
ran it two days on: every copy was stale and it recommended nothing. That is the right answer, and a ranking
that read the clock for itself would have given it without telling me why yesterday's file said something
else.

It refuses to fill a gap. An item with no priority is not treated as medium to be fair to it. It goes last
and says why.

What it does not refuse is to sound sure. The reminder that is due tomorrow sits at place 12 with "confidence
high" beside it, and everything in that line is true. I built the confidence to drop when data is missing,
and it does. I did not build anything that drops when the rule itself is a poor fit for the item in front of
it, and I do not know how I would. So what I would want it to refuse is to let "high confidence" stand for
"good advice". At the least I would rename it: it is how complete the record is, and it should say that.

And one I had not expected. Changing the rule from priority first to due date first changed the answer to
"what should I do next". Same records. I would want the ranking to refuse to hide that. It prints the rule at
the top, and I think that line matters more than any of the thirteen places under it.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Every record is invented: the identifiers, the titles, the dates, the votes and the decisions. The people
  are roles.
- No value was copied from a real record, including the participant's own sandbox records in this repository.

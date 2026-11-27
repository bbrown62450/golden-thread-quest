# Proof · jira-reconciliation-report

Attempt: `jira-attempt-022`

## How this was made

The participant made six decisions: to use a made-up fixture for the records and one real read-only run against the
sandbox; that when an item fits two states, the state that says we know least wins; to add a state for items Jira
has that the copy lacks; that "stale" means Jira moved on and the copy did not, with a limit of 24 hours; to do both
stretch goals; and to add a state for a copy changed locally while Jira stood still. The participant ran the
command that reached the real Jira, in their own terminal. An AI assistant (Claude) wrote the tool, the made-up
Jira, the tests, the scripts and this file. Two further AI assistants read the work. No person other than the
participant has read it.

## The short version

- **Every item gets exactly one state, and the report checks that before it says anything else.** If the check
  fails there is no report.
- **Eighteen made-up items, seven states, counts 5 + 2 + 2 + 1 + 3 + 2 + 3 = 18.** Each state is the one the
  fixture says, compared item by item.
- **Seven states, where the quest names five.** Two were added, and the reason is below.
- **Four of the made-up items fit two states.** Each is given one, and says on its own line what else it fits.
- **The scenario's missing twelve are the sixth state.** A report that only walked the local copy would never see
  an item Jira has and the copy lacks.
- **One real read-only run: 25 items, all synchronized.** It shows the tool can read a real Jira. It shows no
  exception state on a real Jira.
- **A reader found that the first version could call an item synchronized when Jira's status name had changed.**
  That is closed for a copy that carries what it needs, and stated as a limit for one that does not. See below.

## How I chose between two states for an item that fit both

**The rule: the states are tried in a fixed order, and an item is given the first that fits. The order runs from
"we know least" to "we know most".**

| | State | It fits when |
|---|---|---|
| 1 | failed to fetch | Jira could not be asked, or did not answer with an item |
| 2 | missing from Jira | Jira answered that it is not there |
| 3 | conflicted | Jira changed it, and the copy was changed locally |
| 4 | changed locally only | the copy was changed locally; Jira has not changed |
| 5 | stale | Jira changed it; the copy has not been changed locally |
| 6 | not yet copied | Jira lists it; the copy does not hold it |
| 7 | synchronized | none of the above |

**Why this order.** If Jira could not be read for an item, I know nothing about Jira's side, so anything else I
said about the item would be a guess. Failed comes first for that reason. If Jira says the item is gone, a local
change to it has nowhere to go, so "missing" matters more than "changed locally". If both sides changed, calling it
"stale" would invite a sync that destroys the local change, so "conflicted" comes before both one-sided states.
Synchronized is last and has no condition of its own: it is only what is left (criterion 1).

**The second fit is not thrown away.** The item is counted once, under the earlier state, so the counts still add
up (criterion 2). Its lines in the report carry an "Also:" line naming what else it fits. The fixture has four:

| Item | Given | Also fits |
|---|---|---|
| DEMO-5 | missing from Jira | changed locally. That change has nowhere to go |
| DEMO-8 | conflicted | stale: behind by 5 hours, within the limit |
| DEMO-9 | conflicted | stale: behind by 2 days, over the limit |
| DEMO-11 | failed to fetch | changed locally. Whether Jira changed too is not known |

**The cost.** The count of stale items is lower than the number of items that are behind Jira: a conflicted item
that is also two days behind is counted as conflicted. Someone who reads only the stale count will undercount
lateness. The "Also:" line is the only place that shows.

**The alternative I did not take** was to let the more specific state win, so that a failed item with a local
change would be "changed locally only". That would have put an item I could not read into a state that claims Jira
has not changed.

## The two states I added

The quest names five states. An item in either of these positions fits none of them:

- **changed locally only.** The copy was edited and Jira stood still. It is not synchronized, not stale and not
  conflicted. Without this state it would have to be called synchronized, and a sync would then overwrite the edit.
- **not yet copied.** Jira has the item and the copy does not. This is the quest's own scenario: 118 synchronized
  out of 130. Without this state the report would count 16 of 16 on the fixture and never mention two items.

With five states, criterion 1 would be false for those items. The report, the fixture's page and the skill page
each say that there are seven where the quest names five.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Every item is in exactly one state | Tested on the made-up Jira. Seen on the real one, where every item was synchronized | `reconciliation-run.txt` part 2: the script reads the report and finds each of 18 numbers listed once, under the state the fixture says. The tool's own check is section 1 of `report.md` |
| 2 | The counts of all states sum to the total considered | Tested | Part 4: the script adds the seven counts from the report's table itself, compares with the All row, and compares that with the fixture's 16 + 2 |
| 3 | Each missing, stale, conflicted or failed item is listed with a reason | Tested | Part 2: each of the 15 exceptions has a Reason line under its state. `report.md` section 3 |
| 4 | A stale item names its age and the limit | Tested | Part 2: the script works out each of three ages from the fixture (3 hours, 2 days 2 hours, 21 hours) and finds it, the limit and the right side of it on the item's own lines |
| 5 | A failed item names the error class without private content | Tested | Part 2: five classes, each the one that follows from what the fixture has Jira answer. The made-up Jira's refusals carry a made-up title and email address; none is in any output |
| 6 | The same input gives the same report | Tested on the made-up Jira at a fixed time. Not shown on the real one with the final tool | Part 3: a second run writes nothing; a third run into an empty folder writes all three files, byte for byte the same |
| 7 | A reader can tell what to do next for each exception | **Partly.** The lines are there; whether a reader can tell is a judgement | Each exception has a Next line. Stale has two, for within and over the limit. Failed has one for each class. The record checks only that the lines exist |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/jira/reconciliation/fixture.md` | The fixture: what the copy holds, what the made-up Jira answers, and the state each item should get |
| `participant/context/jira/reconciliation/fixture-copy.json` | The made-up local copy |
| `participant/context/jira/reconciliation/report.md` | The report on the fixture |
| `participant/context/jira/reconciliation/report.log.md` | The fetch log: every request, numbered |
| `participant/context/jira/reconciliation/report.history.json` | The history the trend is drawn from |
| `participant/context/jira/reconciliation/sandbox-copy.json`, `sandbox-report.*` | The real sandbox: the copy and the report on it |
| `participant/skills/jira-reconciliation-report/reconcile.py` | The tool: `report`, `adopt` and `states` |
| `participant/skills/jira-reconciliation-report/SKILL.md` | When to use it, and the rules for whoever uses the report |
| `participant/skills/jira-reconciliation-report/fake_jira.py` | The made-up Jira and the fixture |
| `participant/skills/jira-reconciliation-report/tests/test_reconcile.py` | 73 tests |

Under `participant/evidence/jira-reconciliation-report/jira-attempt-022/`:

| Path | What it is |
|---|---|
| `logs/reconciliation-run.txt` | The report generated twice, then a third time into an empty folder, and the counts added up. 22 checks |
| `logs/live-report-1.txt` | The real sandbox, with the final tool |
| `logs/before-readers/` | The real outputs made with the tool **before** the fixes. Kept as they were |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 73 tests passing; 78 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed. Written by hand |
| `scripts/record_run.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-022`. The required record and this
file are copied to `participant/evidence/jira-reconciliation-report/attempt-001/`, with a note there saying so.

## Stretch goals

- **Each exception linked to the log entry that explains it: done.** Every exception has a "Log:" line naming a
  numbered line of the fetch log. The record checks that the line cited is the one on which that item's own number
  was asked for, and that it says what the fixture has Jira answer. The log holds what was asked and the class of
  what came back, and nothing Jira said.
- **The trend over the last five runs: done.** One line for each distinct input, in order of the time each is as
  of. Running the same input again adds nothing. An incomplete run is marked in its own column. The fixture's
  report shows one run, because it has one input. Five runs are shown in a test, not in the hand-in.

## How to reproduce the behavior

Python 3.9 or later and Git, with nothing installed. From the `participant` folder:

    cd skills/jira-reconciliation-report && python3 -m unittest tests.test_reconcile
    python3 evidence/jira-reconciliation-report/jira-attempt-022/scripts/record_run.py
    python3 skills/jira-reconciliation-report/reconcile.py states

The second command deletes `report.md`, `report.log.md` and `report.history.json` and makes them again.

Against a real Jira, by a person, with the three Jira variables set in their own terminal:

    python3 skills/jira-reconciliation-report/reconcile.py report --source live \
        --copy context/jira/reconciliation/sandbox-copy.json --out-dir context/jira/reconciliation --name sandbox-report

## What was tested or validated

- **73 tests.** Each fixture item against the state the fixture says; 32 combinations of what Jira and the copy
  can say, each worked out in the test from the order of the states; a thousand made-up projects, each item's state
  worked out by the test; the tool's own check against six kinds of fault; ages at, under and over the limit; every
  class of failure; a list that cannot be read or cannot be trusted; names that differ only in what cleaning
  removes; a copy, a history or a file that is not the tool's; a real connection that sends only GETs.
- **78 planted bugs,** each put into a copy of the tool and caught by at least one test. Among them: stale items
  called synchronized; items Jira has that were never copied left out; the check counting what the tool itself made.
  Three mistakes are not planted, with the reason, at the end of the record.
- **22 checks** in the run record. The expected state, age, error class, log line and second fit of each item are
  worked out by the script from the fixture, not taken from the tool.
- **One real read-only run:** 26 requests, each a GET with no body. 25 items, Jira's list gave 25, all synchronized.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **An item could be called synchronized when Jira's status or type name had changed.** The tool compared names
  after tidying them, and tidying turns every mark into a question mark and cuts at 40 characters. `QA:Review`
  renamed to `QA/Review` looked the same. **Now a copy can carry a checksum of the names as Jira wrote them, and the
  tool compares that.** A copy without one is still compared by tidied names, and the report says how many items
  that applies to.
- **The tool's own check agreed with itself.** It counted the "in Jira only" items from its own entries. With two
  of them dropped it still passed. **Now it is given the numbers from Jira's list directly, and compares each
  item's state with what was found for it.**
- **An incomplete run did not look incomplete in the table or the trend.** Now it reads NOT KNOWN in both.
- **The copy's file name could forge a heading in the report.** Now it is made safe.
- **`--log` could write over a person's file that began with the word "Project:".** Now it must begin exactly as
  the tool's output does.
- **The two added states were explained only in the code.** Now the report, the fixture and the skill page say so.
- **Sixteen mistakes the tests would not have noticed,** and **six checks in the record that claimed more than they
  tested.** Each now has a test or a sharper check.
- **The second reader classified every fixture item itself** and agreed with every state, count and age.
- **Neither reader found** an item counted twice or not at all, a refusal's words in any output, or a request other
  than the two GETs.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **No exception state has met a real Jira.** The sandbox had nothing out of step. A tool that called everything
  synchronized would print the same real output. The only signs otherwise are the 25 logged requests and the tests.
- **The real copy is compared by tidied names.** It was adopted from an earlier quest's result, which holds tidied
  names only. For all 25 real items, a status renamed only in its marks would not be seen. The report says so.
- **The fixture's expected states and the tool have one author.** "A 403 is failed, not missing" and "a new key is
  stale" are my choices. The fixture and the tool agree because I wrote both. A reader agreed with them; nobody
  with a different view of Jira has.
- **"Missing from Jira" cannot tell deleted from moved from hidden.** A 404 is the same for all three.
- **A local change is judged from type and status only.** An edit to anything else is not seen.
- **An item hidden from this account and not in the copy is in no list.** It is not counted, and nothing says so.
- **The stale count undercounts lateness,** as explained above.
- **If Jira's list cannot be read, the report is still written.** It says INCOMPLETE first and exits with 2, but a
  person who reads only the table of an old copy could still quote its total.
- **Criterion 6 on the real Jira was shown only by the earlier tool.** Those two runs are in `logs/before-readers/`.
  The final tool was run once against the real Jira, as of the clock.
- **Criterion 7 is checked only for the presence of a line.** A test looks for a phrase in each next action, so a
  swapped action that held the phrase would pass.
- **The trend in the hand-in has one row.**
- **The limit of 24 hours is set in the tool,** not per project.
- **The live record has no command line or exit code in it.** The site fingerprint is a short, unsalted hash.

## Reflection

*Which state is easiest to hide a problem in?*

Synchronized. It is the biggest number, it is the one everyone wants to be big, and it is the only state that is
not a finding. Every other state has to be justified: a missing item needs a 404, a stale one needs a changed time.
Synchronized needs nothing. It is what an item is called when no check objected, so every check that is too weak,
or was never made, pays into it. I saw that three times in this quest. The first version compared status names
after tidying them, and a renamed status came out synchronized. The planted bug that turned off the stale check
moved three items into synchronized and the total still added up. And the scenario itself, 118 of 130, is twelve
items that were never asked about, sitting silently beside a number that looked fine. That is why I ordered the
states the way I did, with synchronized last and defined only as what is left, and why the report says that in its
table. The state I would name second is "failed to fetch", for the opposite reason: it is easy to treat as noise.
A failed item is not a slightly late item. It is an item I know nothing about, and if I retried it quietly or
folded it into stale, the report would be claiming knowledge it does not have. What surprised me was that the
check I was proudest of, counts equal total, was the easiest to satisfy while being wrong. A report in which every
item is called synchronized adds up perfectly.

## Sensitive values

No token, password or cookie is in any file of this quest. The token was typed by the participant into their own
terminal and was not seen by the assistant. The live output was searched for the token, the email address and
their encoded form before it was shown or anything was written, and the site's address is replaced by a marker in
the saved copy. No title is asked for, and no person is named: the tool keeps neither. What Jira says in a refusal
is not read. The project key SCRUM, the items' keys and numbers, their type and status names, their last-changed
times and a short hash of the site's name do appear. Every other item, time and refusal is made up.

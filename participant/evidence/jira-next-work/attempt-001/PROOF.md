# Proof · jira-next-work

Attempt: `jira-attempt-017`

## How this was made

I worked with an AI assistant. I made the design decisions; it wrote the two programs, the fake Jira, the tests and
the scripts, and ran them against the fake Jira only. **I ran the one real command myself,** in my own terminal. It
only reads Jira. The assistant read the saved output, which has the site's address removed. Two further AI readers
read the work cold before the real run. **No person other than me has read it.**

## The short version

- **Two steps.** `sync.py copy` copies a project's items into a local records file and **only reads Jira**.
  `rank.py rank` ranks those records and **contacts nothing**.
- **Every reason names the recorded field it came from.**
- **Blocked items are not ranked.** They are listed apart with the blocker named.
- **A copy older than 24 hours carries a warning** and is never the item to start.
- **The clock is an input.** The same records and the same clock value give the same recommendation, byte for byte.
- **The first version had a real ranking bug, found by both AI readers.** It ranked an item first while another
  record said it was blocked. It is fixed, and it is the first of the two recommendations below that I would not trust.
- **It was run on my real sandbox, read-only:** 25 items copied, no titles and no people saved, nothing changed.

## Recommendations I would not trust

The quest asks for one. I have two, and the second is the one I would act on least.

### 1. From my own first version: DEMO-7 ranked first

In the made-up run, the first version put `DEMO-7` at place 1, under "open, not blocked". A few lines further down,
the reasons for `DEMO-9` said that two open items were waiting on it: `DEMO-7` and `DEMO-10`. **The recommendation
contradicted itself.**

- **Why it happened.** Whether an item is blocked was read from its own record only. `DEMO-7`'s copy was 11 days old
  and did not hold the link yet. `DEMO-9`'s fresher record did.
- **Why I would not have trusted it** (criteria 2 and 3). A blocked item was ranked, and the only thing that kept it
  from being "start here" was that its copy happened to be stale.
- **How it was found.** An AI reader checked the printed facts against the rules by hand. My tests had not caught
  it, because every one of them made the two ends of a link agree.
- **What changed.** Both ends of a link are read. `logs/ranking-run.txt` part 3 shows the same situation with
  `DEMO-12`, now listed as blocked.

### 2. From my real sandbox: "Start here: SCRUM-23", confidence in the data high

This one is in `participant/context/jira/next-work/recommendation-sandbox.md`. The tool followed its rules exactly,
and I still would not act on it.

- **What it says.** Start with `SCRUM-23`: `priority` is `Medium`; `duedate` is `2027-01-15`, 49 days away.
- **Why it is first.** 20 of my 24 ranked items have the same priority, Medium, which is what Jira gives an item
  when nobody chooses one. `SCRUM-23` is the only one of them with a due date. So it wins on criterion 2, **by having
  a due date at all, not by being urgent.** It is due in seven weeks.
- **What sits at the bottom.** `SCRUM-2` has a due date of `2026-11-20`, which is **overdue by a week**. It is at
  place 22 of 24, because it has no priority recorded, and a missing priority goes after everything (criterion 5).
  The recommendation does mark it OVERDUE and gives it medium confidence. It still ranks it nearly last.
- **Why "high" confidence misleads here** (criterion 5). Confidence counts missing fields and stale copies.
  `SCRUM-23` has every field and a fresh copy, so it is "high". That says the data is complete. It does not say
  the priority means anything, and on my sandbox it does not: it is a default nobody set.
- **Places 2 to 20 are an order of age.** Those items tie on priority and on having no due date, and none blocks
  anything, so criterion 4, `created`, decides: oldest first. The tie-break rule is stated and followed
  (criterion 4). It is still only the order they were typed in.

**What I take from it.** Every reason cites a field (criterion 1), and that is exactly what let me see the problem:
I could read "priority is Medium" nineteen times and know the field was telling me nothing.

## The criteria, one by one

"Real" means shown by the read-only run on my sandbox. "Fake" means shown against the fake Jira. "Tested" means the tests.

| # | Criterion | Status | Where to look |
|---|---|---|---|
| 1 | Each reason cites a recorded Jira field | **Met: fake, real, tested** | `recommendation.md`: every reason line has a field name in code type. `logs/ranking-run.txt` part 3 counts them. One reason cites `copied_at`, which is a field of the local record and is said to be |
| 2 | A blocked item is excluded or ranked last with its blocker named | **Met: fake, real, tested** | Blocked items are in their own list, not ranked. Fake: `DEMO-5` blocked by `DEMO-3`. Real: `SCRUM-25` blocked by `SCRUM-1`, the link I made in the last quest |
| 3 | An item whose local copy is older than the stated limit carries a warning | **Met: fake, tested** | Limit: 24 hours. `DEMO-7`, 11 days old, keeps place 1 with a STALE warning and is not "start here". **Not shown on the real run:** the real copy was minutes old |
| 4 | Ties are broken by a stated rule | **Met: fake, real, tested** | `rules.md`, "Ties". `DEMO-1` and `DEMO-2` tie on priority and due date; the reason says "this is the tie-break" |
| 5 | Missing fields lower confidence and are reported | **Met: fake, real, tested** | `DEMO-8`: no priority, no due date, confidence low, and listed under "Missing fields". Real: 22 of 25 items have no due date |
| 6 | The same input gives the same ranking | **Met: fake, real, tested** | `logs/ranking-run.txt` part 3 and `logs/live-02`, `live-03`: two runs, the same output and the same sha256. A test runs it in separate processes |
| 7 | The recommendation changes nothing in Jira | **Met, with what each piece of evidence can show stated** | See below |

**On criterion 7.**

- **The ranking cannot reach Jira.** `rank.py` has no network code. A test reads its source for that.
- **The copy sends only reads.** One function builds every request, and it builds a GET with no body. A test checks
  the request itself. In the real run, `logs/live-01-copy.txt` says "Every one was a GET with no body", and that
  line is read back from each request as it was built.
- **The snapshots.** `logs/live-05-snapshots.txt`: four listings of my project, before and after each of two
  copies, all the same. **That shows the listings agree. It is not proof that nothing changed:** Jira's search can
  be behind, as the create-once quest showed me.
- **On the fake Jira the snapshot proves little,** because the fake can only be read. The record says so.

## The blocker that was resolved

`logs/ranking-run.txt` part 4, on the fake Jira. Another person marks `DEMO-3` as Done. The two items are copied
again and ranked again: `DEMO-5` leaves the blocked list and becomes place 1 and "start here". `rank.py diff` says
why: in the record of `DEMO-3`, `status` was "In Progress" and is now "Done". **This was not done on the real Jira,**
because resolving a blocker means changing an item, and this quest must not change Jira.

## My choices

- **Records made up for the evidence, plus one real read.** The made-up set covers every rule. The real read showed
  me what real fields look like, and gave me the second recommendation above.
- **The order follows my earlier, verified ranking skill:** priority, due date, how many open items it blocks, age, key.
- **Started work is listed, not ranked first.** A reader pointed out that an item of mine, in progress, sat below
  untouched ones. I kept status out of the order. "What to start" and "what to finish" are different questions.
- **No titles and no people in the records.** Who has an item is one of three words.
- **When two records disagree about a blocker, the item stays blocked.**

## Where the important artifacts are

| File | What it is |
|---|---|
| `participant/context/jira/next-work/rules.md` | The rules, written by `rank.py rules` |
| `participant/context/jira/next-work/recommendation.md` | The recommendation, from the made-up records |
| `participant/context/jira/next-work/records-demo.json` | The made-up records it was worked out from |
| `logs/ranking-run.txt` | The run against the fake Jira. 26 checks |
| `participant/context/jira/next-work/recommendation-sandbox.md`, `records-sandbox.json` | The same, from my real sandbox |
| `logs/live-01` to `live-05` | The real run |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 67 tests; 71 planted bugs |
| `logs/independent-read.txt` | What the two AI readers found, what changed, what was not re-read |
| `participant/skills/jira-next-work/` | `sync.py`, `rank.py`, `fake_jira.py`, `SKILL.md`, `tests/` |
| `scripts/record_evidence.py`, `planted_bugs.py`, `live_run.py` | The scripts |
| `../attempt-001/` | Copies of the files the quest asks for by that folder name, with a note |

Paths without `participant/` are inside this attempt folder.

## Stretch goals

**Show how the ranking changes under a different priority rule: done.** `--rule due-first` puts due date before
priority. `recommendation.md` ends with a table of both orders: `DEMO-13`, low priority and due first, moves from
place 6 to place 1, and the reason is given. On my real sandbox the same table moves `SCRUM-2`, the overdue one,
from place 22 to place 1.

**Explain why the top item beat the second: done.** "Start here" says which criterion separated it from the next
fresh item, with both values. Every ranked item also says why it is below the one above it.

## How to reproduce the behavior

From the top of the repository, with no network and no credentials:

    python3 participant/evidence/jira-next-work/jira-attempt-017/scripts/record_evidence.py
    python3 participant/evidence/jira-next-work/jira-attempt-017/scripts/planted_bugs.py
    cd participant/skills/jira-next-work && python3 -m unittest tests.test_next_work -v

The first rewrites `logs/ranking-run.txt`, `rules.md`, `recommendation.md` and `records-demo.json`, and gives the same
files every time: its times are made up and fixed. The planted-bug run takes about three minutes, because one bug
makes the copy loop until it is stopped.

The real run was `scripts/live_run.py`, in a terminal with the three `JIRA_` variables set. It can be run again; it
would overwrite the sandbox records and recommendation with the state of Jira at that moment.

## What was tested or validated

- **Read the RESULT line.** `logs/ranking-run.txt`: ALL CHECKS PASSED, 26 checks.
- **67 tests pass.**
- **71 of 71 planted bugs are caught.** Before the readers it was 47 of 49; after their fixes, 68 of 71. Each miss
  was a gap in my tests, and a test was added. One behaviour has no planted bug because no test can tell: the log names it.
- **The real run ended as expected at every step.**

## Remaining limitations

- **A recommendation is only as good as the fields.** See the second recommendation above.
- **A link blocks only if its type is named "Blocks".** A site that renames it gets a warning, not a ranking that works.
- **The 24 hours is my earlier policy's number, not a measurement.**
- **Staleness was not shown on the real Jira.** Nor was a refresh, a deleted item, or a moved item.
- **A due date is compared with the UTC date.** Near midnight, far from UTC, "overdue" can be a day out.
- **A subtask is ranked as an item of its own.** The rules do not look at its parent. My sandbox has one.
- **Four of my sandbox items are "In Progress" with nobody assigned.** The tool offers them as open work. Someone
  may be working on them without having taken them.
- **It lists priorities in the order Jira lists them and takes that to be highest first.** It was so on my site.
- **The site fingerprint in the records would let someone confirm a guessed site name.**
- **Neither reader has seen the corrected version.**

## Reflection

*What would the recommendation need to know that Jira does not record?*

Mostly, whether the fields mean anything. My sandbox taught me that in one run. Nineteen items said "Medium"
because nobody chose, and the tool could not tell a priority that was decided from one that was defaulted. Jira
records the value. It does not record whether a person meant it.

After that, the things only I know. How big each item is. What I am able to do this week. Who is waiting, and how
badly: a link says one item blocks another, but not that someone asks about it every morning. Whether an item
marked "In Progress" with nobody on it is being worked on or was abandoned. Which of two overdue items someone
actually cares about.

And one thing it could know and does not: whether its own copy is still true. That is why I made it carry the time
of every copy and warn when one is old. A stale copy is not a missing field, and it reads exactly like a fresh one.

The lesson that stayed with me came from a mistake. My first version ranked an item first while another record,
printed on the same page, said it was blocked. Every reason on that page cited a field. Citing fields did not make
it right. It made it checkable, and a reader checked. So the most useful thing a recommendation can do is show its
working plainly enough that someone can catch it being wrong.

## Sensitive values

No token, password or email address is in this folder or in the files it points to. The site's address is replaced
by a marker in the logs; a short fingerprint of it remains in the logs and in `records-sandbox.json`, as in my earlier
Jira quests. The sandbox records hold no titles, no descriptions and no people: who has an item is "me", "someone
else" or "nobody". They do hold the keys, statuses, priorities, dates and links of my 25 sandbox items, which are
test items I made. The made-up records are invented.

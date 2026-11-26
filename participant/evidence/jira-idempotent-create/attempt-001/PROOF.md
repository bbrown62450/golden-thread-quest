# Proof · jira-idempotent-create

Attempt: `jira-attempt-015`

## How this was made

I worked with an AI assistant. I made the design decisions; it wrote the workflow, the fake Jira, the tests and the
scripts, and ran them against the fake Jira only. **I ran the real commands myself,** in my own terminal, and typed
the fingerprint of the preview I had read. The assistant read the saved output, which has the site's address
removed. Two further AI readers read the work cold before the real run. **No person other than me has read it.**

## The short version

- **One real Task was created in my sandbox, once: SCRUM-25.** The run that created it was interrupted on purpose
  just after Jira answered, so nothing was recorded locally. The rerun found it by its key and created nothing.
- **The real Jira showed the problem this quest is about.** Two seconds after it created the item, its search
  returned nothing. About fifteen seconds later the search returned it. A workflow that trusted the first empty
  answer and retried would have made a duplicate.
- **Each creation carries a key** made once per draft, saved locally before anything is sent, and sent to Jira as a
  label on the item.
- **A timeout is treated as "not known", never as "failed".** Then the workflow searches. If it cannot search, or
  the search does not settle it, it stops and asks a person.
- **Both stretch goals are done.**
- **The promise has conditions.** It holds on one computer, with the local record kept and the label left on the
  item. The design says where it can fail.

## What happens if the search itself fails

This is the quest's hint, and the part of the design I care most about. The design is in
`participant/context/jira/idempotent/design.md`.

**A failed search is never read as "nothing found".** A search has failed when no answer comes back, Jira answers
with an error, the answer cannot be read or says it was cut short, it returns an item that does not show the key, or
it is empty and Jira does not confirm that this identity can still see the project.

| Where it fails | What happens | Criterion |
|---|---|---|
| In `resolve`, the rerun after an interruption | It stops and says "not known". **Nothing is created. The local record is left exactly as it was.** It does not count as an empty search. It prints the search to run by hand | 2, 3, 9 |
| In `preview` | The duplicate check (criterion 5) cannot be made, so no preview and no fingerprint are issued. There is nothing to confirm | 4, 5 |
| In `confirm`, just before the write | The write is not sent | 2, 9 |
| In `confirm`, after Jira refused the write | The refusal is not believed, and the outcome is recorded as not known | 9 |

In every case the next step is a person's: run `resolve` again later, or look in Jira by hand.

**Where this is shown:** `logs/interrupted-run.txt` part 5, against the fake Jira, with an error answer, no answer
and a cut-short answer. **It was not tried against the real Jira:** I had no safe way to make the real search fail.

## The criteria, one by one

"Real" means shown by the run in my sandbox. "Fake" means shown against the fake Jira. "Tested" means the tests.

| # | Criterion | Status | Where to look |
|---|---|---|---|
| 1 | Each creation carries a stable key stored on the Jira item | **Met: real, fake, tested** | `logs/live-02-preview.txt`: the key as the one label to be sent. `logs/live-09-resolve-2.txt`: SCRUM-25 read back, "it carries the label: yes". Stable: the same key in every live record, and after the title was edited (`live-21`) |
| 2 | After an interruption the rerun searches for the key before creating | **Met: real, fake, tested** | `logs/live-07`: the rerun's preview is refused, "outcome not known". `live-08`, `live-09`: `resolve` searches, and sends only reads. `logs/interrupted-run.txt` part 1 |
| 3 | An item found by the key is recorded locally and not created again | **Met: real, fake, tested** | `logs/live-09`: "FOUND BY ITS KEY: SCRUM-25 ... NOTHING WAS CREATED by this run". `live-10` to `live-13`: nothing to create |
| 4 | A preview shows the site, the project and the exact changes; nothing is written before a person confirms | **Met: real, fake, tested** | `logs/live-02-preview.txt`; `logs/preview.txt`. Every request a read; snapshots before and after the same |
| 5 | The preview records the permission check and the duplicate check, or says where Jira cannot perform one | **Met: real, fake, tested** | The same two files: both permissions, the check by key, the check by title, and "Where Jira cannot check" |
| 6 | Writes only to a project on an explicit sandbox allowlist | **Met: real with a reservation, fake, tested** | `logs/live-01`: refused with an allowlist that lists no project. **A refusal of a second real project was not made:** I have one sandbox project. `logs/confirmation.txt` refusal 4 shows another project refused on the fake Jira |
| 7 | The confirmation is tied to a fingerprint of the exact preview, refused when missing or changed, and expires | **Met: real with a reservation, fake, tested** | `logs/live-03` missing, `live-04` changed, `live-05` too old, `live-06` the confirmation naming the fingerprint. **The "too old" refusal uses a test clock** moved 16 minutes on; I did not wait 15 real minutes |
| 8 | A result record holds the issue key, the identifier, the project, the timestamp and the confirmer | **Met: real** | `participant/context/jira/results/idempotent-create.md` |
| 9 | Running the approved workflow again creates no duplicate, or the limit is stated | **Met, with stated limits** | `logs/live-10` to `live-13`, `logs/rerun.txt`. The limits are in the design, under "The limits, and how each would be noticed" |

## The real run, in order

Fifteen records, `logs/live-NN-*.txt`, made by `scripts/live_run.py`, which I ran. Times are UTC.

| Step | What | Result |
|---|---|---|
| 01 | Preview with an allowlist that lists no project | Refused |
| 02 | Preview | Fingerprint issued. Eight requests, all reads |
| 03 | Confirm with no fingerprint | Refused |
| 04 | Confirm after the draft's title was changed | Refused. The draft was then put back |
| 05 | Confirm with the test clock 16 minutes on | Refused |
| 06 | **Confirm, interrupted on purpose after Jira answered** | **Jira answered 201, at 22:49:52. Nothing recorded locally** |
| 07 | Preview again | Refused: the outcome is not known |
| 08 | `resolve`, at 22:49:54 | **Found 0. "Not found yet." Nothing created** |
| 09 | `resolve`, about 15 seconds later | **Found SCRUM-25 by its key. Recorded. Nothing created** |
| 10 to 13 | Preview, confirm, resolve and check, all again | Nothing to create; confirm refused; one item carries the key |
| 21, 22 | After I changed the title by hand in Jira | Still carries the label, still found by its key, nothing to create |

**The interruption was made by a test switch, not by killing the program.** The switch ends the run at a named point
and records nothing after it. Steps 03, 04, 05 and the second confirm were run with the command that can write,
and were refused before anything was sent.

## Where the important artifacts are

| File | What it is |
|---|---|
| `participant/context/jira/idempotent/design.md` | The design |
| `participant/context/jira/results/idempotent-create.md` | The result record of the real run |
| `logs/preview.txt`, `confirmation.txt`, `interrupted-run.txt`, `rerun.txt` | **The four records the quest names, made against the FAKE Jira,** with checks: 7, 10, 24 and 4 |
| `logs/live-01` to `live-22` | The same things against the real sandbox |
| `logs/manual-edit.txt` | Stretch goal, on the fake Jira. 4 checks |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 83 tests; 78 planted bugs |
| `logs/independent-read.txt` | What the two AI readers found, what changed, what was not re-read |
| `participant/skills/jira-idempotent-create/` | `create_once.py`, `fake_jira.py`, `SKILL.md`, `fixtures/`, `tests/` |
| `participant/context/jira/idempotent/created-once.json`, `empty-allowlist.json` | The real draft, and the empty allowlist used for step 01 |
| `participant/context/jira/update/sandbox-allowlist.json` | The sandbox allowlist, from an earlier quest |
| `scripts/record_evidence.py`, `planted_bugs.py`, `live_run.py` | The scripts |
| `../attempt-001/` | Copies of the files the quest asks for by that folder name, with a note |

Paths without `participant/` are inside this attempt folder.

## Stretch goals

**Interrupt at three different points and show each recovers: done on the fake Jira.** `logs/interrupted-run.txt`
parts 1, 2 and 3: before the request went, after Jira accepted it, and after the item was recorded. Parts 4 to 6 add
a lost answer with a search that is behind, a search that fails, and two items carrying one key. **On the real
Jira only one point was interrupted,** the one the quest asks for.

**Show the key surviving a manual edit: done on the real Jira.** I changed SCRUM-25's title by hand.
`logs/live-21-check-after-edit.txt`: it still carries the label, its title "has been changed in Jira since", and a
search for the key returns it and no other. `logs/manual-edit.txt` also shows the limit on the fake Jira: with the
label removed, the item is no longer found by its key.

## How to reproduce the behavior

Against the fake Jira, from the top of the repository, with no network and no credentials:

    python3 participant/evidence/jira-idempotent-create/jira-attempt-015/scripts/record_evidence.py
    python3 participant/evidence/jira-idempotent-create/jira-attempt-015/scripts/planted_bugs.py
    cd participant/skills/jira-idempotent-create && python3 -m unittest tests.test_create_once -v

The real run needs a Jira sandbox on the allowlist and the three `JIRA_` environment variables set in a terminal.
It was `scripts/live_run.py`. **It cannot be repeated as it was:** the draft's task now exists, and the script says
so and stops.

## What was tested or validated

- **Read the RESULT line of each record.** The five made against the fake Jira all say ALL CHECKS PASSED.
- **83 tests pass.**
- **78 of 78 planted bugs are caught.** The first run, before the readers, caught 54 of 59. Three places where the
  workflow checks the same thing twice have no planted bug, because no test can tell one check from the other; the
  log names them.
- **The real run ended as expected at every step.** The script stops at the first step that does not.

## What the independent readers found

Full account in `logs/independent-read.txt`. Both reads were made **before** the real run. The four that mattered:

- **A test-only clock switch also worked against a real Jira,** so the wait could be skipped. It is now refused there.
- **The release rule was weaker than the design said.** Two empty searches a moment apart could release a record.
- **An empty answer caused by lost access was counted as "not found".**
- **Two confirmations at the same moment could both send the write.**

All four are fixed, with tests and planted bugs. **Neither reader has seen the corrected version.**

## Remaining limitations

- **Jira cannot be asked to create "only if no item has this label".** A run on another computer, with a copy of the
  state folder, could create the same item in the same moment.
- **The waits are choices, not measurements.** The one real measurement I have is that the search was behind at 2
  seconds and caught up by about 17. If it can be more than about 90 seconds behind, a second item is possible.
- **A lost local record, a renamed draft or another state folder means a new key.** Only the title check then points
  at the earlier item, and a person has to notice.
- **Anyone who can edit the item can remove the label.**
- **A confirmation is not tied to a person.** The terminal rule keeps out a program with no terminal, and no more.
- **The interruption was simulated,** and on the real Jira at one point only. A failing search and a lost answer were
  shown on the fake Jira only.
- **The fake Jira is built from the specification,** not checked against Jira field by field. The real run exercised
  the same requests once each.
- **The result record's heading says "created at most once".** The workflow wrote it; the promise has the conditions
  above. I left the record as it was written.
- **SCRUM-25 is still in my sandbox,** with an edited title. I can delete it by hand after review.

## Reflection

*What is the safest thing to do when you do not know whether a write happened?*

Not to write again. Everything else follows from saying "I do not know" out loud instead of rounding it to "it
failed". A timeout feels like a failure, and retrying feels like diligence, and that is exactly how one item becomes
three.

So first I look, and I look by something I put there myself: the key. Then I am honest about what the look can tell
me. One item found means it happened. Nothing found means very little, and my own sandbox proved it: two seconds
after Jira created the item, Jira's search said there was nothing. If the look itself fails, I have learned nothing,
and the worst thing I could do is treat that as an answer.

When looking does not settle it, I stop and ask a person, and a person confirms again before anything is created.
That costs a minute. A duplicate costs someone else's attention later, and they will not know why it is there.

What surprised me was how many of my own shortcuts pointed the other way. A test switch that skipped the wait. A
rule that released the record after two quick looks. Each one was a small "it is probably fine". Not knowing is
uncomfortable, and most of the design is there to stop me relieving that discomfort by guessing.

## Sensitive values

No token, password or email address is in this folder or in the files it points to. The site's address is replaced
by a marker in everything saved; a short fingerprint of it remains, as in my earlier Jira quests. The one real
item's title is made-up text I wrote. No other person's ticket text is here: other items are named by issue key
only. The confirmer is written as "the participant".

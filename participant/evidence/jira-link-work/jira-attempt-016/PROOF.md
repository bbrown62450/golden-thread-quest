# Proof · jira-link-work

Attempt: `jira-attempt-016`

## How this was made

I worked with an AI assistant. I made the design decisions; it wrote the workflow, the fake Jira, the tests and the
scripts, and ran them against the fake Jira only. **I ran the real commands myself,** in my own terminal, and typed
the fingerprint of the preview I had read. The assistant read the saved output, which has the site's address and
the items' titles removed. Two further AI readers read the work cold before the real run. **No person other than me
has read it.**

## The short version

- **One real link was created in my sandbox, once: SCRUM-1 blocks SCRUM-25** (link id 10000).
- **It reads the right way round from both items,** by the workflow's read-back and by my own eyes in Jira's screen.
- **A request is written as a sentence,** "SCRUM-1 blocks SCRUM-25", and the preview says it back from both items.
  Nobody writes Jira's two slot names.
- **An identical link is detected and not created again,** however the request words it. The opposite link is
  refused as a conflict.
- **Only "Blocks" and "Relates" links can be created.** "Duplicates", "clones" and any other type are refused.
- **Both stretch goals are done,** on the fake Jira: a link that would close a circle is refused, and several links
  go in one confirmed batch.

## How I tested direction

Direction can go wrong in three places, so it was tested in three ways. Criteria 1 and 3.

**1. The request and the preview (criterion 1).** The request is a sentence, and the preview says it twice:

    IN WORDS:                        SCRUM-1 blocks SCRUM-25.
    The same link, from the other item: SCRUM-25 is blocked by SCRUM-1.
    That is: SCRUM-1 comes first, and SCRUM-25 waits for it.

A request written from the other item, "SAND-2 is blocked by SAND-1", is shown to give the same link:
`logs/link-check.txt` part 1.

**2. The read-back from both items (criterion 3).** After the write, each item is read and what it lists is put into
words and compared with the sentence. From `logs/live-06-confirmation.txt`:

    read from SCRUM-1: it lists link id 10000 as: SCRUM-1 blocks SCRUM-25. Wanted: SCRUM-1 blocks SCRUM-25. Type "Blocks": yes
    read from SCRUM-25: it lists link id 10000 as: SCRUM-25 is blocked by SCRUM-1. Wanted: SCRUM-25 is blocked by SCRUM-1. Type "Blocks": yes

On the fake Jira I also made the fake store a link **the other way round** from what the workflow expects. The
workflow noticed from the read-back, said the link reads backwards and is in Jira, and named the link to remove:
`logs/link-check.txt` part 4. **That tests that a mismatch is noticed. It does not test which way round is right.**

**3. My own eyes (criterion 3).** The read-back has a weakness a reader pointed out: the same program writes the
link and reads it, with one understanding of Jira's slots. If that understanding were wrong, it would agree with
itself about a backwards link. So after the real run I opened SCRUM-1 in Jira in my browser and looked at its
linked items. **The heading above SCRUM-25 says "blocks".** That is the sentence I confirmed.

- This is my statement of what I saw. There is no screenshot, because a screenshot would show the site and my
  account.
- I looked from SCRUM-1 only. I did not look at SCRUM-25's screen.

**What is still a belief.** That the workflow puts the two items in Jira's slots correctly for **this** site and
link type is now shown. That it holds for a site with link types set up differently is not shown.

## The criteria, one by one

"Real" means shown by the run in my sandbox. "Fake" means shown against the fake Jira. "Tested" means the tests.

| # | Criterion | Status | Where to look |
|---|---|---|---|
| 1 | The preview states the relationship and its direction in words | **Met: real, fake, tested** | `logs/live-02-preview.txt`; `logs/link-check.txt` part 1; `logs/preview.txt` |
| 2 | An existing identical link is detected and not created again | **Met: real, fake, tested** | `logs/live-08`: the same request again, "nothing to create". `logs/live-10`: the same link asked for from the other item, "already there". `logs/link-check.txt` part 3, which also covers a link made by someone else |
| 3 | Both items show the link with the correct type and direction | **Met: real, fake, tested, and seen by me from one item** | `logs/live-06` and `live-07`, quoted above; "How I tested direction", point 3 |
| 4 | A preview shows the site, the project and the exact changes; nothing is written before a person confirms | **Met: real, fake, tested** | `logs/live-02-preview.txt`; `logs/preview.txt`. Every request a read; snapshots before and after the same |
| 5 | The preview records the permission check and the duplicate check, or says where Jira cannot perform one | **Met: real, fake, tested** | The same two files: permission for each item, this same link, the opposite link, the circle check, and "Where Jira cannot check" |
| 6 | Writes only to a project on an explicit sandbox allowlist | **Met: real with a reservation, fake, tested** | `logs/live-01`: refused with an allowlist that lists no project. **A refusal of a second real project was not made:** I have one sandbox project. `logs/confirmation.txt` refusal 4 shows it on the fake Jira, for either end of the link |
| 7 | The confirmation is tied to a fingerprint of the exact preview, refused when missing or changed, and expires | **Met: real with a reservation, fake, tested** | `logs/live-03` missing, `live-04` changed, `live-05` too old, `live-06` the confirmation naming the fingerprint. **"Too old" uses a test clock** moved 16 minutes on |
| 8 | A result record holds the issue key, the identifier, the project, the timestamp and the confirmer | **Met: real** | `participant/context/jira/results/link-work.md`: both issue keys, Jira issue link id 10000, the project, the time written, the confirmer |
| 9 | Running the approved workflow again creates no duplicate, repeated or conflicting change, or the limit is stated | **Met, with stated limits** | `logs/live-08` nothing to create; `live-09` the used fingerprint refused; `live-11` the opposite link refused as a conflict. `logs/rerun.txt`. Limits below |

## The real run, in order

Twelve records, `logs/live-NN-*.txt`, made by `scripts/live_run.py`, which I ran. Times are UTC, 2026-11-27.

| Step | What | Result |
|---|---|---|
| 01 | Preview with an allowlist that lists no project | Refused |
| 02 | Preview | "SCRUM-1 blocks SCRUM-25". Ten requests, all reads |
| 03 | Confirm with no fingerprint | Refused |
| 04 | Confirm a turned-round copy of the request | Refused: not the file the preview showed |
| 05 | Confirm with the test clock 16 minutes on | Refused |
| 06 | **Confirm** | **Jira answered 201. Link id 10000, written 00:57:00. Read back from both items** |
| 07 | Check | Found, the right way round on both items, one of it |
| 08 | Preview again | Nothing to create |
| 09 | Confirm again with the used fingerprint | Refused |
| 10 | Preview "SCRUM-25 is blocked by SCRUM-1" | Already there. Nothing to create |
| 11 | Preview the opposite, "SCRUM-25 blocks SCRUM-1" | Refused: the opposite link already exists |
| 12 | Preview "SCRUM-1 duplicates SCRUM-25" | Refused: a type this workflow does not create |

Steps 03, 04, 05 and 09 were run with the command that can write, and were refused before anything was sent. The
script passes a step only if it ends with the expected status **and** says the expected words.

## My choices

- **A request is a sentence, not Jira's slot names.** The slot names are the trap. A sentence can be read aloud.
- **Only Blocks and Relates.** See the reflection.
- **Both items must be in a sandbox project,** because a link changes both.
- **The opposite link is a conflict, not a second link.** "A blocks B" and "B blocks A" cannot both be meant.
- **Direction comes from the site's own phrases,** never from the link type's name.
- **The preview tells the reader not to judge the link by Jira's slot names.** A reader found that to someone who
  knows Jira, the correct link looks wrong in those two lines.

## Where the important artifacts are

| File | What it is |
|---|---|
| `logs/link-check.txt`, `preview.txt`, `confirmation.txt`, `rerun.txt` | **The four records the quest names, made against the FAKE Jira,** with checks: 13, 8, 10 and 4 |
| `logs/live-01` to `live-12` | The same things against the real sandbox |
| `participant/context/jira/results/link-work.md` | The result record of the real run |
| `logs/stretch.txt` | Both stretch goals, on the fake Jira. 11 checks |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 80 tests; 71 planted bugs |
| `logs/independent-read.txt` | What the two AI readers found, what changed, what was not re-read |
| `participant/skills/jira-link-work/` | `link_work.py`, `fake_jira.py`, `SKILL.md`, `fixtures/`, `tests/` |
| `participant/context/jira/links/` | The real request, three variants used for steps 10 to 12, and the empty allowlist |
| `participant/context/jira/update/sandbox-allowlist.json` | The sandbox allowlist, from an earlier quest |
| `scripts/record_evidence.py`, `planted_bugs.py`, `live_run.py` | The scripts |
| `../attempt-001/` | Copies of the files the quest asks for by that folder name, with a note |

Paths without `participant/` are inside this attempt folder.

## Stretch goals

**Refuse a link that would create a cycle: done on the fake Jira.** `logs/stretch.txt` part 1. Existing links of
the same type are followed from the target; if they lead back to the source, the link is refused. A circle made
only by the links of one request is refused too. **On the real Jira only the two-item case was shown:** step 11.
The limit is shown as well: a "relates to" link back to the start is not counted as a circle.

**Create several links in one confirmed batch: done on the fake Jira.** `logs/stretch.txt` parts 2 to 4. Three
links under one fingerprint, one of them already there; each new link read back before the next is sent; a batch
Jira refuses at its second write, which stops and says what was written; and a batch overtaken before it is
confirmed. **No batch was run on the real Jira.**

## How to reproduce the behavior

Against the fake Jira, from the top of the repository, with no network and no credentials:

    python3 participant/evidence/jira-link-work/jira-attempt-016/scripts/record_evidence.py
    python3 participant/evidence/jira-link-work/jira-attempt-016/scripts/planted_bugs.py
    cd participant/skills/jira-link-work && python3 -m unittest tests.test_link_work -v

The real run was `scripts/live_run.py`, in a terminal with the three `JIRA_` variables set. **It cannot be repeated
as it was:** the link now exists, and the script says so and stops.

## What was tested or validated

- **Read the RESULT line of each record.** The five made against the fake Jira all say ALL CHECKS PASSED.
- **80 tests pass.**
- **71 of 71 planted bugs are caught,** with two cautions the log spells out. Some are caught only because a refusal
  gave a different reason while a second check still refused. And two bugs about Jira's slots are caught by tests
  that share the fake Jira's own belief about those slots.
- **The real run ended as expected at every step.**

## What the independent readers found

Full account in `logs/independent-read.txt`. Both reads were made **before** the real run. Neither found a path to
a wrong, duplicate or unconfirmed link. The ones that mattered:

- **The workflow cannot prove its own direction,** and my records claimed the real run would. See "How I tested
  direction", point 3.
- **The real-run script judged steps by exit status alone,** and one step rewrote my real request file to the
  opposite link before running the command that can write. Both are fixed.
- **The "reads backwards" message said nothing was written** while a wrong link sat in Jira. It now says the link
  is in Jira and names it.
- **The slot-name lines in the preview could mislead** someone who knows Jira.

**Neither reader has seen the corrected version.**

## Remaining limitations

- **Jira has no "create only if there is none like it" that this workflow relies on.** Another run, on another
  computer, could create the same link in the same moment. A real Jira may then ignore one write and still answer
  that it succeeded; the workflow finds the one link and cannot tell which run made it.
- **It sees only the links this identity may see.** A circle through a hidden item is not found.
- **The circle check follows links of one type,** through at most 50 items.
- **Direction is shown for my site and its "Blocks" type,** not for sites set up differently.
- **I looked at one item in Jira's screen, not both.**
- **Circles of three or more, batches, a slow Jira and a refused write were shown on the fake Jira only.**
- **The preview is long.** A reader called it cluttered. The sentence is now first, but the rest is still there.
- **The link is still in my sandbox.** I can remove link id 10000 by hand after review.

## Reflection

*Which link types would you not let an agent create?*

Any link whose effect is more than the sentence it says.

"Blocks" and "relates to" are sentences. I can read "SCRUM-1 blocks SCRUM-25" aloud, decide whether it is true, and
if I am wrong someone sees a wrong sentence and fixes it. Those I let an agent create, with a preview and my
confirmation.

"Duplicates" is not only a sentence. It is a verdict: stop working on this one. On some sites it closes the item
without anyone deciding. "Clones" claims a history, that one item was copied from another, and if an agent adds it
by hand that history did not happen. And for a link type someone has added to a site, I cannot know from the
outside what it sets off. So those I do not let an agent create at all. If one is right, a person makes it in Jira.

What changed my mind during this quest was how thin my own check was. I thought "read it back from both items"
settled direction. A reader pointed out that the thing writing and the thing reading shared one belief, so they
would agree with each other about a backwards link. The check that finally settled it was me, looking at the
screen. So the rule I would give is not only about link types. An agent may create a link when a person can check
it with their own eyes afterwards, and should not when the only witness is the agent.

## Sensitive values

No token, password or email address is in this folder or in the files it points to. The site's address is replaced
by a marker in everything saved; a short fingerprint of it remains, as in my earlier Jira quests. The two real
items' titles are not saved anywhere: the logs hold only their lengths. The link type's name and phrases are the
site's standard ones. The confirmer is written as "the participant".

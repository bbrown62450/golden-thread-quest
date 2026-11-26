# Proof · jira-create-subtask

Attempt: `jira-attempt-014`

## How this was made

The participant made two decisions: how the parent is named (by key, pinned to its issue id), and what happens to a
closed parent (refused, with no override). An AI assistant (Claude) wrote the workflow, the fake Jira, the tests, the
scripts and this file, and ran everything that uses only made-up data. **The participant ran every command against
the real Jira sandbox, in their own terminal, with their own credentials.** The assistant gave each command, did not
run it, never had the credentials, and read only the copies the workflow saved with the site's address removed. Two
further AI assistants read the work. No person other than the participant has read it.

## The short version

- One real subtask was created: **SCRUM-24** (issue id 10023) under **SCRUM-1** (issue id 10000), in the sandbox
  project SCRUM.
- Its parent was read back three times: in the run that wrote it, in a separate check, and in a second run. Each time
  it was issue id 10000, the parent intended.
- Six real runs were refused with nothing written: a parent that does not exist, a parent that is itself a subtask,
  a project not on the allowlist, no confirmation, an altered title, and a preview made to look too old.
- A second real run found the subtask there and issued no fingerprint.
- **The real parent is a Task, not a Story.** See "The parent in the real run" below.

## How the parent was picked, and what is done about ambiguity

**Criterion 1. The parent is picked by its identifier and by nothing else.**

1. The change file names the parent by its **key** (`SCRUM-1`) or its numeric issue id. Text that could not be a key
   is refused before Jira is asked.
2. The preview asks Jira for that one issue. There is **no search in the workflow**, so there is no list of
   candidates to pick wrongly from.
3. The preview shows the key, the **issue id**, the type, the status and the title. The fingerprint is tied to the
   issue id, which does not change if the issue is moved or renamed.
4. The confirmation reads the parent by that id, and is refused if the key in the change file now leads to another
   issue. The write names the parent by its id.
5. The title is shown for a person to read, and is used for nothing. It is not saved.

**Ambiguity.** The quest's scenario is two stories with one title. This workflow cannot confuse them, because it never
looks a parent up by title: each story has its own key and id, and only the one named is read. What is left is a
person naming the wrong key. Against that the preview shows which issue the key leads to, title included, before
anything is written.

| Case | What the workflow does | Shown on |
|---|---|---|
| Two stories share a title | Reads only the one named. Naming the other gives another id and another fingerprint | fake |
| A title given in place of a key | Refused | fake |
| The same title aimed at the twin story after a preview | Refused: "it names a different parent" | fake |
| The parent does not exist (criterion 2) | Refused before any preview | **real** and fake |
| The parent is itself a subtask (criterion 2) | Refused before any preview | **real** and fake |
| The parent is closed | Refused before any preview, no override | fake |
| The key now leads to another issue | Refused at confirmation | tests |

## The parent in the real run

`SCRUM-1` is the sandbox issue used in the earlier comment quest. The first real preview showed that Jira calls its
type **"Task"**. It is not a Story.

- The workflow does not require a Story. It refuses a subtask as a parent, shows the type's name, and leaves the rest
  to the person. That was the design before the real run, and it was not changed to fit.
- So the real evidence shows a subtask created under a Task. Nothing in the workflow treats a Story differently, and
  the fake Jira's parents are Stories. **A real run against an issue of type Story was not made.**
- The workflow's messages, and the heading of its result record, say "story". That wording is loose, and was left
  alone so that the code is the code that made the real runs.

## The criteria, one by one

"Real" means shown in the participant's saved output from the real sandbox. "Fake" means shown by running the same
command against the made-up Jira. "Tested" means a unit test covers it and a planted bug in it was caught.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Parent selected by its stable identifier | **real, fake, tested** | `preview.txt`: the parent's key and issue id, and the read by key in the list of requests. Two stories with one title: `parent-check.txt` part B. That nothing searches: a test |
| 2 | Missing parent, or a subtask as parent, refused before the preview | **real, fake, tested** | `parent-check.txt` part A: both refused on the real site, with no preview and no fingerprint. Exit codes: part B |
| 3 | Parent link read back and matching | **real, fake, tested** | `confirmation.txt` and `parent-check.txt` part A: "its parent, read back, is issue id 10000. The parent intended is issue id 10000". The script also compares the id in the check with the id in the preview, as printed. It is all the program's own output: there is no second view of Jira |
| 4 | Preview shows site, project and exact changes; nothing written before confirmation | **real with reservations, fake, tested** | `preview.txt`. The site is a marker in what is saved; it was on the participant's screen. "Nothing written" rests on the program's list of four GET requests and two equal snapshots. On the fake, the count of issues before and after is read separately |
| 5 | Permission check and duplicate check recorded, or where Jira cannot check | **real, fake, tested** | `preview.txt` part A: both permissions yes, 0 subtasks with this title, and the statement that Jira has no "only if none" condition |
| 6 | Writes only to a project on the allowlist | **real with a reservation, fake, tested** | The real refusal was made by giving an allowlist that lists no project. A refusal of another project, PROD-9, is on the fake only: the participant has one sandbox project |
| 7 | Confirmation tied to the fingerprint; refused when missing or differing; expires | **real with a reservation, fake, tested** | `confirmation.txt` part A. Missing and differing were refused on the real site. **Expiry was shown with the test clock**: the preview was under a minute old and the program was told to act as if 16 minutes had passed. The stated limit is 15 minutes |
| 8 | Result record: key, identifier, project, timestamp, confirmer | **real** | `participant/context/jira/results/create-subtask.md`. The confirmer is recorded as "the participant", a role and not a name, and nothing checks it |
| 9 | A second run creates no duplicate, or the limit is stated | **real, fake, tested** | `rerun.txt` part A: "NOTHING TO ADD", naming SCRUM-24, no fingerprint, and the old fingerprint refused. The limit, two runs at the same moment, is stated there |

## The real runs, in order

All twelve were run by the participant on 2026-11-26 (UTC). Each saved its output with `--log`.

| # | Run | Saved as | Outcome |
|---|---|---|---|
| 1 | Preview naming `SCRUM-999999` | `live-refused-missing-parent.txt` | Refused. Nothing written |
| 2 | Preview with an allowlist that lists no project | `live-refused-allowlist.txt` | Refused. Nothing written |
| 3 | First preview | `live-preview-first.txt` | Preview `b2df57569a4d`. Never confirmed |
| 4 | Confirm with no fingerprint | `live-refused-missing.txt` | Refused |
| 5 | Confirm the first preview with an altered title | `live-refused-differs.txt` | Refused |
| 6 | Confirm the first preview with the test clock 16 minutes on | `live-refused-stale.txt` | Refused |
| 7 | Second preview | `live-preview.txt` | Preview `9716e0540ced`, made 02:11:33 |
| 8 | **Confirm the second preview** | `live-confirmation.txt` | **Written 02:11:54: SCRUM-24** |
| 9 | Parent check | `live-parent-check.txt` | Found under the parent intended |
| 10 | Preview again | `live-rerun-preview.txt` | Nothing to add. No fingerprint |
| 11 | Confirm the used fingerprint | `live-rerun-confirm.txt` | Refused: used once |
| 12 | Preview naming `SCRUM-24` as parent | `live-refused-subtask-parent.txt` | Refused: itself a subtask |

The saved files hold no command lines. The order above is as the commands were given. Runs 7 to 12 carry times or
identifiers that fix their order. Runs 1, 2, 4, 5 and 6 carry none, and nothing in them shows when they were made.

**Eighteen seconds passed between the second preview and its confirmation.** The participant had read the first
preview, which showed the same parent and the same change, about a minute earlier. Nothing in the files can show that
a person read either.

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/skills/jira-create-subtask/subtask.py` | The workflow. sha256 `b62f0a587e293c550e3a7cff9f33281679410d199a4b432ab2527d489e2f270f`, unchanged since before run 1 |
| `participant/skills/jira-create-subtask/SKILL.md` | Its rules, and its limits |
| `participant/skills/jira-create-subtask/fake_jira.py`, `tests/`, `fixtures/` | The made-up Jira, 130 tests, and the change file and allowlist used with the fake |
| `participant/context/jira/subtask/` | The real change file, and the three used for refusals |
| `participant/context/jira/update/sandbox-allowlist.json` | The sandbox allowlist, from an earlier quest |
| `participant/context/jira/results/create-subtask.md` | The result record |
| `logs/parent-check.txt`, `logs/preview.txt`, `logs/confirmation.txt`, `logs/rerun.txt` | The four records: real output in part A, the fake in part B |
| `logs/live-*.txt` | The twelve saved outputs, as the workflow wrote them |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 130 tests passing; 71 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed |
| `scripts/record_evidence.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-014`. The required files are copied to
`participant/evidence/jira-create-subtask/attempt-001/`, with a note there saying so.

## Stretch goals

- **Copy selected fields from the parent, with a preview: not done.** It would carry other people's text into a
  write, and each copied field would need its own review step.
- **Several subtasks in one approved batch: not done.** One preview, one fingerprint, one subtask keeps what a person
  approves small enough to read.

## How to reproduce the behavior

Against the made-up Jira, with no network and no credentials:

    python3 -m unittest discover -s participant/skills/jira-create-subtask/tests
    python3 participant/evidence/jira-create-subtask/jira-attempt-014/scripts/record_evidence.py
    python3 participant/evidence/jira-create-subtask/jira-attempt-014/scripts/planted_bugs.py

The second rewrites the four records, copying the saved real output in as it finds it.

The real runs cannot be repeated as they were: a preview of the same change would now say "NOTHING TO ADD". With
`JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` set, a sandbox project on an allowlist, and a change file, the three
commands are the ones in `SKILL.md`.

## What was tested or validated

- **130 unit tests** against the fake Jira, all passing.
- **71 planted bugs.** Each was put into the workflow, the tests were run, and the bug taken out. All were caught.
  Three were not caught at first; a test was added for each.
- **144 checks** in the four records: 28, 64, 34 and 18. Those in part A are of the saved text of the real runs, and
  of one saved file against another: the fingerprint, the parent's id, the subtask's key, the times, the title's
  checksum.
- The project's secret scan, and a search for names, addresses and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **Before the real run**, reader 1 found no path that writes without the confirmation checks, or under another
  parent, project or title than the preview showed. It found that a server error would have been reported as "nothing
  was written" while Jira might still be creating the subtask. That was corrected before anything real was run.
- **After the real runs**, reader 2 found the real output consistent with itself and nothing unredacted. It found
  checks whose labels claimed more than they tested, and that the Task-not-Story fact was stated nowhere. The checks
  were tightened and this file says it.
- Neither reader saw the corrected versions.

## Remaining limitations

- **No real run against an issue of type Story.**
- **Shown on the fake only:** two stories with one title; a closed parent; a refusal aimed at another project; a
  failure after a write; a key that leads to another issue.
- **Expiry was shown with the test clock,** not by waiting.
- **Every statement about Jira in the evidence is the workflow's own output.** There is no screenshot and no second
  tool's view.
- **Two runs at the same moment could both create the subtask.** The run reports it afterwards.
- **The saved previews have no secret behind them.** Someone who can write the state folder could make one. They
  could not aim it anywhere the change file and the allowlist do not allow.
- **The allowlist is whatever file is given.**
- **The parent's type, other than "subtask", is not checked,** and neither is its title.
- **SCRUM-24 is still in the sandbox.** It is a test subtask and can be deleted by hand.
- The workflow's wording says "story" throughout.

## Reflection

*What should happen if the parent is closed?*

It should be refused, and I chose to give it no override. Jira itself would let me add a subtask to a finished story,
and that is the problem: the story stays "done" on every board and report while new work hangs under it, so the
estimate is wrong and nobody is told. If the work is real, the honest thing is for someone to reopen the story in
Jira first. That is a visible act with a name on it, and then the workflow will go ahead. I considered a warning
instead, and decided against it, because it rests on someone reading the warning at the moment they are trying to
get something done. What I had not thought about until I ran it is how the workflow knows "closed": it goes by the
category Jira puts the status in, and if Jira does not say, it refuses too. I did not close my real sandbox issue to
try it, so this rule is shown only on the made-up Jira. The real run also taught me something next to the question:
my parent turned out to be a Task and not a Story, and the workflow went ahead because I had only told it to refuse
subtasks and closed issues. Whether to refuse other types is the same kind of decision, and I would make it on
purpose next time.

## Sensitive values

No token, password or cookie is in any file. The credentials were in environment variables in the participant's
terminal and were never given to the assistant. Every saved output was searched by the workflow for the token, the
email address and their encoded form before it was shown. The site's address is replaced by a marker in everything
saved. No email address, account identifier, personal name or home-folder path is in the evidence. The parent's title
was shown on screen only; what is saved is that it has 6 characters. The site fingerprint is not a secret: someone
who guessed the site's name could confirm the guess. The keys SCRUM-1 and SCRUM-24, their ids, and the test title are
in the evidence. Real output that was not redacted exists nowhere in the repository; the state folder is in
`local-data/`, which is not committed.

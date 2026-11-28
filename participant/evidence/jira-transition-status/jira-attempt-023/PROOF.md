# Proof · jira-transition-status

Attempt: `jira-attempt-023`

## How this was made

The participant made five decisions: to use a made-up Jira for the records and one real move in the sandbox; that
the real item is SCRUM-25, moved from To Do to In Progress; that closing an item with an open subtask is refused
before any preview, with no override; that the tool sends the move and nothing else, so a move with a required
field is refused; and that a second run looks first and does nothing if the move is already made. The participant
ran every command that reached the real Jira, in their own terminal, and typed the fingerprint that confirmed the
move. An AI assistant (Claude) wrote the tool, the made-up Jira, the tests, the scripts and this file. Two further
AI assistants read the work before the real move was made. No person other than the participant has read it.

## The short version

- **The tool asks Jira which moves are open for the item, every time.** No move's number or name is written into it.
- **A move that is not allowed gets no preview and no fingerprint,** so there is nothing that could be confirmed.
- **Closing an item with an open subtask is refused.** On the real Jira too: SCRUM-1, with its open subtask SCRUM-24.
- **One real move: SCRUM-25 from To Do to In Progress.** Read back as In Progress. Jira's history entry 10057.
- **Before it, six refusals on the real Jira,** three of them made with the command that can write. Nothing written.
- **Run again, it did nothing:** the new preview said the item already had the status, and the used fingerprint was
  refused.
- **The real workflow lets every status move to every other.** So the real run could not show Jira itself
  forbidding a move between two real statuses. It shows a status the workflow does not have being refused.
- **The readers read it before the real move.** They found a crash that could follow a write and leave no output,
  and files that could be written over. Both are fixed. See below.

## How I handle open subtasks (criterion 2, and the first stretch goal)

**A move to a done status is refused, before any preview, if any subtask is not done.** There is no override.

- "Done" means Jira gives the status the category `done`. The status's name is not looked at. A status that is only
  *named* "Done" does not count, and a done status with another name does.
- The subtasks are the ones Jira lists on the item. Each one's status category is read.
- **If a subtask's status cannot be read, or Jira gives no list of subtasks at all, the move is refused too.**
  "Could not check" is not "none open".
- A move that is not to a done status is not affected. The preview still says how many subtasks are open.
- The fix is to finish the subtasks first. A person with a reason to close the parent anyway does it in Jira.

Shown on the made-up Jira in `invalid-transition.txt` part 2 (refused; and the made-up Jira itself would have
accepted the move, shown by making it directly in a throwaway copy) and part 3 (unreadable). Shown on the real Jira
in `live-03-refused-open-subtask.txt`: closing SCRUM-1 is refused, naming SCRUM-24. The real workflow offers that
move. Only the tool stood in the way.

**What it does not see.** A subtask Jira does not list for this account. Stories under an epic, which are not
subtasks. Both are stated in the rules page.

## How I handle required fields (criterion 2)

**The tool sends the move's id and nothing else.** Jira is asked which fields each move's form asks for, and which
are required.

- **A move with a required field is refused before any preview,** naming the field. It is made in Jira, where the
  form can be seen. Shown in `invalid-transition.txt` part 4.
- **Optional fields are named in the preview as not sent.**
- **If Jira does not say which fields a move asks for, the move is refused.** A reader found that the first version
  took silence to mean "none".
- **Resolution.** Jira does not say beforehand whether a move will set one. So after a move into a done status the
  resolution is read back. **An empty one ends the run with "A PERSON NEEDS TO LOOK", in capitals, and exit code 2,
  not "ALL DONE".** Shown in `invalid-transition.txt` part 7b. That is the other half of the quest's scenario.

**What it cannot do.** Close an item in a workflow that insists on a resolution. And a workflow can reject a move by
a rule of its own that Jira lists nowhere beforehand: such a move is previewed, Jira refuses it at the write, and
the tool reads the item and reports that nothing was written.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | The allowed transitions are read from the workflow, not assumed | Tested. Seen on the real Jira | `rules-run.txt`: the page's moves compared with the made-up workflow by the script. `preview.txt` part 1: the made-up Jira's own list of reads shows it was asked. `live-00-rules.txt`, `live-04-preview.txt`: the real moves, with Jira's own ids |
| 2 | A transition that is not allowed is refused before the preview | Tested. Seen on the real Jira **for a status the workflow does not have** | `invalid-transition.txt` parts 1 to 4: no preview, no fingerprint, no saved preview, state file unchanged. `live-02`, `live-03` |
| 3 | The status read back matches the intended one | Tested. Seen on the real Jira | `invalid-transition.txt` part 5: the made-up Jira's own state file agrees. `live-08-confirmation.txt`, `live-09-check.txt` |
| 4 | A preview shows the site, the project and the exact changes, and nothing is written before the human confirms | Tested. Seen on the real Jira, **without the site's address in the saved copy** | `preview.txt` parts 1 and 2. `live-04-preview.txt`. The address was on screen; the saved copy holds a fingerprint of the site's name |
| 5 | The preview records the permission check and the duplicate check, or states where Jira cannot perform one | Tested. Seen on the real Jira | `preview.txt` part 1, and part 3 for a permission Jira denies. `live-04-preview.txt` |
| 6 | Writes only to a project on an explicit sandbox allowlist | Tested. On the real Jira, shown with an empty list only | `confirmation.txt` part 4. `live-01-refused-allowlist.txt` |
| 7 | The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires | Tested. Seen on the real Jira. **The time limit is tested with the tool's own test clock** | `confirmation.txt` parts 1, 2, 3, 3b and 5. `live-05`, `live-06`, `live-07`, `live-08` |
| 8 | A result record holds the issue key, the identifier of what was changed, the project, the timestamp and the confirmer | Met, for the real move | `participant/context/jira/results/transition-status.md`: SCRUM-25, history entry 10057, SCRUM, the time, "the participant" |
| 9 | Running again creates no duplicate, repeated or conflicting change, or the limit is stated | Tested. Seen on the real Jira. **A limit is stated** | `rerun.txt` parts 1 to 4, and the limit at its end. `live-10`, `live-11` |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/jira/transition/rules.md` | The rules, read from the **made-up** workflow for five items: it has a forbidden move, a required field and open subtasks to show |
| `participant/context/jira/transition/rules-sandbox.md`, `rules-sandbox-after.md` | The same, read from the **real** workflow: SCRUM-25 and SCRUM-1 before the move, SCRUM-25 after |
| `participant/context/jira/results/transition-status.md` | The result record of the real move |
| `participant/context/jira/transition/*.json` | The requests of the real run, and an allowlist that lists nothing |
| `participant/skills/jira-transition-status/transition.py` | The tool: `rules`, `preview`, `confirm` and `check` |
| `participant/skills/jira-transition-status/SKILL.md` | When to use it, the rules for an agent, and its limits |
| `participant/skills/jira-transition-status/fake_jira.py` | The made-up Jira and its workflow |
| `participant/skills/jira-transition-status/tests/test_transition.py` | 100 tests |

Under `participant/evidence/jira-transition-status/jira-attempt-023/`:

| Path | What it is |
|---|---|
| `logs/invalid-transition.txt` | Four moves refused before any preview; an approved move read back; closing with and without a resolution. 20 checks |
| `logs/preview.txt` | The workflow stopping at a preview, the made-up Jira unchanged, and a denied permission. 12 checks |
| `logs/confirmation.txt` | The refusals, then the approved run and its result record. 21 checks |
| `logs/rerun.txt` | The approved workflow run again, and a conflicting change. 12 checks |
| `logs/rules-run.txt` | The rules page compared with the made-up workflow. 4 checks |
| `logs/live-00-rules.txt` to `logs/live-12-rules-after.txt` | The real sandbox, in order |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 100 tests passing; 131 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed. Written by hand |
| `scripts/record_evidence.py`, `scripts/live_run.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-023`. The four required records and
this file are copied to `participant/evidence/jira-transition-status/attempt-001/`, with a note there saying so.

**The four records the quest names are of the made-up Jira.** The real run's outputs are the `live-` files. I kept
them apart because the made-up workflow can show what the real one cannot: a forbidden move, a required field, an
empty resolution.

## Stretch goals

- **Refuse to close a story with open subtasks: done,** as described above, and shown on the real Jira.
- **Record who approved the transition: done, as a role.** The result record says "Confirmed by: the participant",
  with the time, the preview's fingerprint and when the preview was made. It is the name given on the command line.
  The tool cannot prove who typed it. No person's name is in the evidence, by this project's rule.

## How to reproduce the behavior

Python 3.9 or later and Git, with nothing installed. From the `participant` folder:

    cd skills/jira-transition-status && python3 -m unittest tests.test_transition
    python3 evidence/jira-transition-status/jira-attempt-023/scripts/record_evidence.py
    python3 evidence/jira-transition-status/jira-attempt-023/scripts/live_run.py --rehearse

The second command makes `rules.md` and the five records again. The third runs the real sequence against the
made-up Jira in a temporary folder; it stops to ask for the fingerprint of the preview it shows.

The real sequence, without `--rehearse`, is run by a person with the three Jira variables set in their own
terminal. It would now stop at once, because it has already written.

## What was tested or validated

- **100 tests.** Moves read from the workflow, with other ids and names put in to show none is built in; each
  refusal before the preview; "done" by category and not by name; the allowlist; every way a confirmation can be
  missing, altered, old, used or for another request; each way the change can differ from the preview; what happens
  when the write is refused, gets no answer, is accepted and does not show yet, or the run is interrupted; the
  resolution in three cases; where files may be saved; a real connection that can post only one thing.
- **131 planted bugs,** each put into a fresh copy of the tool and caught by at least one test. Seven mistakes are
  not planted, with the reason, at the end of the record.
- **69 checks** in the five records. Each says whether it read the made-up Jira's own state file or only the tool's
  words.
- **The real run:** thirteen commands. One write, of the move's id and nothing else. Jira answered 204.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`. **They read it before the real
move,** so the item was moved once, by the corrected tool.

- **A confirmation could write to Jira and then crash with no output,** for example on a name with an accented
  letter in a plain terminal. Now the output is saved before it is shown, and showing it cannot fail that way.
- **`--log`, `--result` and `--out` could write over the allowlist, a request or a saved preview.** Now each place
  is checked before Jira is asked anything.
- **A second open preview stayed valid after the item was moved and moved back.** Now a preview remembers the
  item's last-changed time and the length of its history, and is refused if either changed.
- **A wrong history entry could be recorded as this move's.** Now the history must be readable before the write,
  and the entry must be newer than any seen before it.
- **The quest's scenario was in no record,** and several checks claimed more than they tested. The records now
  close an item with and without a resolution, and the checks read the made-up Jira's own state.
- **About fifty mistakes the tests would not have noticed.** There is now a test for each that can be told from outside.
- **Not fixed, and stated as limits:** someone who can write in the tool's state folder can forge, re-open or
  re-date a saved preview; and the allowlist is whatever file is named on the command line.
- **Neither reader found** a write from a command that only reads, a write that differed from the request worked
  out again against Jira, or the write sent twice in one run.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **The real Jira did not forbid anything.** Its workflow offers every status from every status. The "not allowed"
  refusal on the real Jira is for a status that does not exist there. A move between two real statuses that the
  workflow forbids is shown on the made-up Jira only.
- **No move into a done status was made on the real Jira.** The resolution read-back is shown on the made-up Jira
  only. What the real workflow does to the resolution is not known from this quest.
- **No required field met a real Jira.** The real workflow's moves ask for none.
- **Because every move is open from every status, Jira would not refuse a repeat.** Between the tool's last read and
  its write someone else could move the item. Only the tool's own look stands in the way. The read-back and the
  item's history would show it afterwards.
- **The fingerprint is a checksum, not a secret,** and the saved preview is a file. Someone or something with write
  access to the state folder can make a preview that was never shown. A confirmed move is still worked out again
  against Jira and must be the move a fresh preview would show.
- **The allowlist is the file named on the command line.** The preview shows its name and a short checksum, not its
  contents.
- **On the real Jira the allowlist was tested with an empty list.** No second real project was refused.
- **The time limit was not waited for.** It is tested with a test clock that can only make a preview older.
- **"A person at a terminal" is a test for a terminal.** A program with a terminal would pass it.
- **If someone else's identical move lands just before this tool's write,** their history entry would be recorded as
  this run's. Who made an entry is not read.
- **The saved real outputs hold no site address,** only a short, unsalted hash of its name.
- **SCRUM-25 is now In Progress.** Nothing depends on it. It can be moved back by a new preview that asks for To Do.

## Reflection

*Which status change would you want a second person to approve?*

The move to Done. Every other move I looked at says something about what someone is doing: started, waiting,
under review. Done says something about the work itself, and it is the one status that other things read. Reports
count it, a sprint is judged on it, and the people waiting on that item stop waiting. So it is the move where being
wrong costs other people the most, and where the person making it is least well placed to judge, because the one
who did the work is the one who most wants it finished. In this quest I made the tool refuse to close an item with
an open subtask, and report an empty resolution, and both of those are checks a machine can do. What a machine
cannot check is whether the work is in fact finished, and that is what a second person is for. What I saw on the
real sandbox made me more sure, not less: the workflow there lets any status move to any other, so Jira itself
would have let me close anything from anywhere. The second move I would name is reopening, moving something out of
Done. It quietly changes a number that someone already reported, and nobody is told. I would not ask for a second
person on To Do to In Progress, which is the move I actually made. It claims little, it is easy to undo, and
asking for approval there would only teach people to click approve without reading.

## Sensitive values

No token, password or cookie is in any file of this quest. The token was typed by the participant into their own
terminal and was not seen by the assistant. Every live output was searched for the token, the email address and
their encoded form before it was shown or anything was saved, and the site's address is replaced by a marker in the
saved copies. The items' titles were shown on screen for the participant to check, and are not saved. No person is
named: the confirmer is recorded as "the participant". What Jira says in refusing a write is not repeated. The keys
SCRUM-1, SCRUM-24 and SCRUM-25, their issue ids, the site's status and move names, one history entry id and a short
hash of the site's name do appear. Every other item, name and site is made up.

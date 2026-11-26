# Proof · base-camp-interruption-recovery

Attempt: `base-attempt-007`

## How this was made

The participant made two decisions: that the run is stopped by a hard kill at chosen points, and that a resumed run
skips an item only when the progress record and the file on disk agree. An AI assistant (Claude) wrote the workflow,
the tests, the scripts, the notes and this file, and ran them on the participant's computer. Everything is local and
uses made-up data. Two further AI assistants read the work. No person other than the participant has read it.

## The short version

- A small workflow writes a card for each of ten made-up work items, then builds an index from the card files.
- It was killed halfway through writing the sixth card. It left five whole cards, one half-written temporary file
  that cannot be mistaken for a card, and a progress record with a line for each of the five.
- Resumed with the same command, it skipped those five without touching them, wrote the other five and the index,
  and said what it had found and done. Every file has the checksum of an uninterrupted run's.
- **A reader found that the first version could be left unable to resume:** a kill at the very first write left an
  empty progress record that every later run refused. That is fixed, with tests.
- **"Durably" is not shown.** A killed process is not a power cut. See "What is not shown".

## How the run was stopped

By **SIGKILL**, the signal a program cannot catch. No clean-up code runs, in the workflow or in Python. It was sent
only to the workflow's own process, never to anything else. Two ways were used:

| Way | How | Where it is used |
|---|---|---|
| **From outside** | The script starts the workflow with a setting that makes it wait at a named point. It reads the workflow's output until it says it is waiting, then kills that process | `logs/interrupted.txt`, the lock trial, two tests |
| **From inside** | The workflow is started with a setting that makes it kill itself at a named point | `logs/three-points.txt` and most tests, where the exact point matters |

The stop points are ten kinds of place:

- **In writing a card or the index:** halfway through the temporary file; when the temporary file is whole and not
  yet renamed; after the rename and before the progress line; halfway through the progress line.
- **In the record's own lines:** when the record file has just been created and is empty; halfway through the
  start, resume, reopen, finish and closing lines.

The settings that make it wait or kill itself are read only by the workflow, and exist only for this.

## How I know the result equals an uninterrupted one

1. **An uninterrupted run is made first**, in another folder, from the same ten items.
2. **Every file is compared by checksum:** the ten cards and the index. `logs/resumed.txt` lists all eleven, with both
   checksums in full, and one checksum over the whole list. They are the same.
3. **The tests make the same comparison** after a kill at each of the ten kinds of point, for the first card, a
   middle card, the last card and the index, and after runs that were interrupted two and three times.

**What that comparison cannot show.** The same item always gives the same card, so equal checksums show that nothing
is missing, cut short or mixed. They cannot show that no work was repeated, because a card written twice is the same
card. That is shown another way: the five skipped cards are the same files on the disk after the resume as before
(the same inode, last changed at the same time), and the five written ones are new files.

The progress records are not equal and are not meant to be. The resumed run's keeps the history of the interruption.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | An interruption leaves the previous complete file or the new complete file | Tested | `three-points.txt` point 6: a card that already exists is being replaced when the run is stopped, twice. The name holds the previous whole file each time, and the new whole file after the resume. Points 1 to 5 and `interrupted.txt`: where there was no file before, there is none, or the new whole one |
| 2 | A temporary or partial file is never left under the final name | Tested, **for cards and the index** | `interrupted.txt`: every file in the folder is listed and judged. The five cards under final names are whole. The half-written content is in `.W-06.md.tmp-<process id>`. **The progress record is the exception:** it is written in place, and a stop can cut its last line short. Each line carries a check of its own text for that reason |
| 3 | Progress is recorded durably as each item finishes | Tested in part. **"Durably" is not shown** | `interrupted.txt`: after the kill the record holds a line for each of the five finished items, each with the checksum of its card. That shows a line is written as each item finishes. It does not show the line was on the disk itself. A test checks that the workflow asks the disk to keep each card, each line and each folder change |
| 4 | A resumed run skips finished items and completes the rest | Tested | `resumed.txt`: W-01 to W-05 skipped and untouched, W-06 to W-10 and the index written. One exception, stated: a card that was renamed into place just before the stop, with no record yet, is written again |
| 5 | The resumed result equals an uninterrupted run's | Tested | `resumed.txt`: eleven checksums, all the same |
| 6 | A person can tell a run was interrupted and how it recovered | Recorded | `interrupted.txt`: the status command says INTERRUPTED, how far it got, what was left and how to recover. `resumed.txt`: the resumed run says it is resuming, where the stopped run had got to, what it removed, and for each item whether it was skipped or written. **No person other than the participant has read these** |

## Where the important artifacts are

Under `participant/evidence/base-camp-interruption-recovery/base-attempt-007/`:

| Path | What it is |
|---|---|
| `scripts/workflow.py` | The workflow |
| `scripts/sample/items.json` | The ten made-up items |
| `tests/test_workflow.py` | 55 tests |
| `scripts/record_evidence.py` | Makes the three records |
| `scripts/planted_bugs.py` | Puts 40 bugs into the workflow, one at a time, and checks the tests catch each |
| `logs/interrupted.txt` | The stopped run, what it left, and the status. 10 checks |
| `logs/resumed.txt` | The resumed run and the checksum comparison. 13 checks |
| `logs/three-points.txt` | Six stop points, each recovered, and the lock. 22 checks |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 55 tests passing; 40 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed |

And `participant/context/recovery-notes.md`: how a file is written safely, where progress is recorded, how a person
can tell, and what could still go wrong.

The quest names the folder `attempt-001`. The application made `base-attempt-007`. The two required records and this
file are copied to `participant/evidence/base-camp-interruption-recovery/attempt-001/`, with a note there saying so.

## Stretch goals

- **A lock so two runs cannot overlap: done.** A second run in the same folder is refused while the first lives. The
  system releases the lock when a process ends, so a killed run leaves none behind. `three-points.txt`, last part.
- **Interrupt at three different points and show each recovers: done, at six in the record** and at more in the
  tests.

## How to reproduce the behavior

Python 3.9 or later, on macOS or Linux, with nothing installed. From the attempt folder:

    python3 -m unittest discover -s tests
    python3 scripts/record_evidence.py
    python3 scripts/planted_bugs.py

The second rewrites the three records; process ids in them will differ. The third runs every test 41 times, which takes
some minutes, and changes `workflow.py` while it runs, then puts it back. To try it by hand:

    GTQ_STOP_AT=W-06:mid-write python3 scripts/workflow.py run --items scripts/sample/items.json --out /some/empty/folder
    python3 scripts/workflow.py status --out /some/empty/folder
    python3 scripts/workflow.py run --items scripts/sample/items.json --out /some/empty/folder

## What was tested or validated

- **55 tests.** A kill at each of four points for the first, a middle and the last card and the index; kills in the
  record's own lines; a resume that is itself killed; three kills in a row; a card damaged or removed after it was
  recorded; a record damaged in the middle; another input; a finished run run again; the lock; the status.
- **40 planted bugs,** each put into the workflow and caught by at least one test. Among them: writing straight to
  the final name, recording progress before the file is in place, trusting the record without looking at the file,
  deleting the record on resume, and leaving out each push to the disk. One was not caught at first, and a test was
  added.
- **45 checks** in the three records.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **Reader 1** traced what a kill leaves between every pair of steps. It found that a kill at the very first write
  left a folder no run would resume, that a short write on a full disk went unnoticed, that a finished run being put
  right could be left looking finished, and seven smaller things. It said the notes did not answer the reflection
  question honestly for the progress record. All of that was changed.
- **Reader 2** found the records consistent with themselves, and found that the "previous complete file" half of
  criterion 1 was shown nowhere, that "durably" was asserted and not shown, and that several checks tested less than
  their labels said. A sixth stop point was added, and the checks and labels corrected.
- **Neither reader saw the corrected versions.**

## What is not shown

- **A power cut.** Every stop here is a killed process. What a killed process had handed to the system is still
  written out afterwards. The workflow asks the disk to keep each write, and a test checks that it asks. Whether that
  is enough when the power goes was not tried, and cannot be tried safely on this computer.
- **A disk that is full, slow or lying, or a network drive.** A made-up "disk full" error is tested once.
- **One refusal a stop alone can cause.** If the progress record is lost altogether and cards remain, the next run
  refuses. That is deliberate: the other choice is to start over on files with no record.
- **A change to the workflow's code between the stop and the resume,** unless the card format's number was changed.
- **Work that cannot safely be done twice.** A card renamed into place and not yet recorded is written again. That is
  harmless for a card and would not be for an email or a payment.
- **Another computer or operating system.** Not tried on Linux or Windows. The lock and the stronger push to the
  disk are specific to this kind of system.

## Reflection

*What could still go wrong if the interruption came during the rename, or while writing the progress record?*

I expected the rename to be the dangerous moment and the progress record to be the easy part. It was the other way
round. The rename is one step, so a kill cannot leave half of one. The worst a power cut can do is undo a rename that
had not reached the disk, which puts the card back under its temporary name; the resume throws that away and writes
the card again. The progress record is where things went wrong, because it is the one file I write in place. I had
handled a line cut short in the middle of a run. I had not handled a kill at the very first write, which left an
empty record that every later run refused. The only way out would have been to delete the record, which is exactly
what this quest says not to do. A reader found that by tracing the code step by step, not by running anything. The
same reader showed that a finished run being repaired could be left looking finished. What I take from it is that
the bookkeeping needs the same care as the data, and that "interrupted at any point" has to include the points
inside the recovery itself. What I still cannot show is a real power cut: I ask the disk to keep each write, and I
have no proof that it does. And one case I chose to leave as a refusal: if the record is gone and cards remain, the
run stops and asks for a person, because starting over on files I have no record of is the mistake the quest is
about.

## Sensitive values

No secret, token or password is in any file of this quest. The ten work items are made up. Runs happen in temporary
folders, shown as WORK, CLEAN and so on, and are deleted. No real person, account, site or home-folder path appears.
The records hold process ids, which are numbers the system gave to short-lived runs on the participant's computer.

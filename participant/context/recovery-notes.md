# Recovery notes: stopping a run and resuming it

These describe the workflow in `participant/evidence/base-camp-interruption-recovery/base-attempt-007/scripts/workflow.py`.
It takes ten made-up work items, writes a card for each, then builds an index from the card files.

    python3 scripts/workflow.py run    --items scripts/sample/items.json --out DIR
    python3 scripts/workflow.py status --out DIR

To resume a run that stopped, give the same `run` command again. There is no separate "resume" command and no option
to pass. **Do not delete the progress record.**

Some words used below. A **checksum** is a short code worked out from a file's contents: two files with the same
checksum have the same contents. A **process** is one running copy of a program, and its **process id** is the number
the system gives it. A **lock** is a marker that lets only one run work in a folder at a time.

## How a file is written safely

A card, or the index, is never written under its final name.

1. The content is written to a temporary file **in the same folder**, named `.<final name>.tmp-<process id>`.
2. That file is pushed to the disk.
3. It is **renamed** to the final name. Within one folder a rename is a single step. This is the moment the file
   becomes real.
4. The folder is pushed to the disk, so that the rename itself is kept.

So at every moment the final name holds **the old whole file, the new whole file, or nothing**. It never holds part
of a file.

| If the run stops | What is on disk |
|---|---|
| while the temporary file is being written | a temporary file holding part of the content. Nothing under the final name, or the old file if there was one |
| after the temporary file is complete, before the rename | a whole temporary file. Still nothing new under the final name |
| after the rename | the whole new file under the final name |

A temporary file's name begins with a dot and ends in `.tmp-` and a number, so it cannot be taken for a card. A run
that resumes lists every temporary file it finds, removes it, and never uses it.

**The progress record is the one exception.** It is added to in place, a line at a time, so a stop can leave its
last line cut short. It is protected another way: see the next section.

## Where progress is recorded

In `DIR/progress.jsonl`. **One line is added, and pushed to the disk, as each thing finishes**, not at the end.

| Line | When | What it holds |
|---|---|---|
| `run-started` | once, at the start | a fingerprint of the items, and the number of the card format |
| `item-done` | after a card is under its final name | the item, and the checksum and length of that card |
| `index-done` | after the index is under its final name | the checksum of the index |
| `run-finished` | at the end | |
| `run-resumed` | by a run that finds a record that is not finished | which resume this is, and how many items were recorded |
| `run-reopened` | by a run that finds a finished run with a file missing or changed | why |
| `cut-short-line-closed` | by a resume, after lines at the end that an interruption cut short | which line it was |

- The record is only ever **added to**. It is never rewritten, shortened or deleted.
- Each line ends with a short check of its own text. A line that was cut short, or changed by hand, fails it, and
  a line that fails it is never believed.
- **A run is finished when the last line is `run-finished`.** Anything recorded after a finish means it is not.
- **The order matters.** The file is in place first, then the line is written. So a line never claims a file that is
  not there. The other way round, a stop between the two would leave a record of work that was not done.

## What a resumed run trusts

An item is skipped only if **the record says it is done and the card on disk has the checksum recorded**. Both.

| What the resume finds | What it does |
|---|---|
| recorded as done, card there, checksum matches | **skips it**. The card is not touched |
| recorded as done, card missing | writes it again, and says so |
| recorded as done, card there but not the file recorded | writes it again, and says so. This is the half-written file that looks complete |
| a card under its final name with no record | writes it again, and says so. The card is whole, but nothing says what it was made from |
| the last line of the record cut short | ignores that line, says so, closes it off, and does that item again |
| a record with no whole line in it: the run stopped while writing its very first line | begins the record again, and says it is resuming |
| a damaged line with good lines after it that do not close it off | **refuses.** A person looks |
| items other than those the run started with | **refuses.** Use another folder for another input |
| a record made by a version that writes cards in another format | **refuses.** Resuming would mix the two |
| cards in the folder and **no progress record** | **refuses.** The record was lost or deleted. It does not start over on top of them |
| a record that says the run finished | checks every file against the record, and writes nothing if they agree |
| a finished run with a card or the index missing or changed | adds `run-reopened`, writes it again, and finishes again |

A refusal is for a case a stop alone should not be able to cause. One exception is known: see "What is not covered".

The index is built from the card files as they are on disk. It is built again whenever any card was written again.

## How a person can tell a run was interrupted

Three places.

1. **The output of the run that stopped has no `FINISHED` line** and no `REFUSED` line: it just ends. Its lines are
   sent one at a time, so everything up to the stop is there. This only helps if someone kept that output.
2. **`status`** says `INTERRUPTED`, how many items were recorded, which temporary files were left, and how to recover.
   It changes nothing. If a run is still working in the folder, it says that first.
3. **The resumed run says so first:** `RESUMING AN INTERRUPTED RUN`, how far the stopped run had got, which resume
   this is, what was left behind and what was done with it. Then, for every item, `skipped` or `written`. Its last
   line counts both.

Afterwards the progress record still shows it: a `run-resumed` line sits between the items done before the stop and
those done after.

## Two runs at once

A run holds a lock on `DIR/lock` for as long as it lives. A second run in the same folder is refused, and writes no
card, no index and no line of the record. The system releases the lock when the process ends, however it ends, so a run that was killed leaves no lock
to clear by hand.

## What could still go wrong during the rename, or while writing the progress record

**During the rename.** The system makes a rename one step, so a killed process cannot leave half a rename. A power cut
can undo one that had not reached the disk: the card is then back under its temporary name, with no record of it. The
resume removes the temporary file and writes the card again. That is safe. The dangerous order would be the record
reaching the disk before the rename it describes; the workflow pushes the rename to the disk first to prevent it.

**While writing the progress record.** This is the weaker place, because the record is written in place.

- **A line cut short.** Handled: it fails its check, is ignored, and its item is done again.
- **The very first line cut short, or the file created and still empty.** Handled, after a reader found that the first
  version refused such a folder for ever.
- **A resume that is itself stopped while closing off a cut-short line.** Handled: the closing can be done again.
- **The record lost altogether**, which a power cut soon after the start could do. Not recovered from: the next run
  refuses, because there are cards and no record. That is a refusal a stop alone can cause. It is deliberate: the
  other choice is to start over on files with no record, which is what this quest forbids.
- **A line the disk keeps only part of, in the middle of the record,** with whole lines after it. Refused. A killed
  process cannot cause it. A disk that reorders its writes could.
- **A full disk.** A write the system cuts short is carried on with until it is whole, and a write of nothing is an
  error. The run then stops with exit code 3 and can be resumed.

## What is not covered

- **A power cut.** The tests kill the process. What a killed process had already handed to the system is still
  written out. The workflow asks the disk to keep each file, each folder change and each progress line, and a test
  checks that it asks. Nothing here cuts the power, so whether the asking is enough is not shown. Where the system
  refuses the stronger request, the workflow falls back to the weaker one without saying so.
- **A disk that lies about having written,** or a folder on a network drive, where a rename may not be one step and
  a lock may not hold.
- **A change to the workflow's own code** between the stop and the resume, unless the card format's number was
  changed with it. Cards written before and after would differ, and the resume would not notice.
- **A file changed after it was recorded, in a way that keeps its checksum.** Not possible by accident.
- **Someone editing the progress record on purpose.** A changed last line is treated as cut short, and its item done
  again. A changed line elsewhere makes the run refuse. Lines removed from the end are not noticed: the run just does
  that work again. The checks are against accidents, not against people.
- **The count of resumes** can be one too low, if a resume is stopped in the instant before it records itself.
- **Work that cannot be done twice.** An item whose card was renamed into place but not recorded is done again. That
  is harmless here because writing the same card twice gives the same card. A step that sends an email or charges a
  card would need more than this.

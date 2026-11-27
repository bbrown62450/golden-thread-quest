# Proof · jira-read-hierarchy

Attempt: `jira-attempt-020`

## How this was made

The participant made four decisions: to use a made-up project for the required record and the real sandbox for one
read-only check; that Jira's internal number is an item's identity, with the key beside it; that a loop or a
self-parent rejects the whole build, while a parent that was not retrieved is an unresolved link and never a
rejection; and to do both stretch goals. The participant ran every command that reached the real Jira, in their own
terminal. An AI assistant (Claude) wrote the tool, the made-up Jira, the tests, the scripts and this file. Two
further AI assistants read the work. No person other than the participant has read it.

## The short version

- **Each item records its type and its parent's number.** Not the parent's key, and never its title.
- **The tree is built from the numbers alone.** With every key changed, the same numbers nest under the same numbers.
- **A parent that was not read is an unresolved link.** The item is kept, under that parent's number, and is not
  shown as an item with no parent.
- **A moved item is under its new parent only,** and is matched with the earlier records by its number, even when
  its key changed too.
- **A loop or a self-parent rejects the whole build.** Nothing is written.
- **The same items give the same files, byte for byte.**
- **Checked against the real sandbox, read-only:** 25 items, one parent link, built twice with identical files.
- **The real project showed two things my made-up one had not,** and two readers found real faults. See below.

## How I detect a moved item (criterion 4)

**I do not look for moves in order to place an item. I place every item fresh, from its own parent number.**

1. **Each record holds one parent number**, as Jira gave it at this reading. A record cannot hold two.
2. **The tree is built from those numbers and from nothing kept from before.** So an item that was moved in Jira is
   under its new parent, and is not under the old one. The scenario's double count cannot arise: there is no old
   place for the estimate to stay in.
3. **To report the move, the new records are compared with the records on disk, item by item, by number.** Same
   number, different parent number: "was under X, and is now under Y".
4. **The key is not used for that.** A key changes when an item goes to another project. In the record the moved
   item also gets a new key: DEMO-7 becomes DEMO-70 and moves from one story to another. Matched by key it would be
   one item gone and one item new. The output says neither. It says the item with the number 30007 moved and has a
   new key.

In `tree-run.txt` part 5, the subtask's 2 hours leave the old story (13 h to 11 h) and join the new one (9 h to
11 h). The epic above both is 25 h before and after.

**What can still mislead here.** A move is only seen at the next build. Two moves between two builds are seen as
one. And a new key on a *parent* is not a move of its children: a reader showed my tests would not have noticed if
the tool had confused the two, so there is a test for that now.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Each item records its type and its parent's stable identifier | Tested. Seen on the real Jira for one parent link | `tree-run.txt` part 1: for each of 11 items the number, type and parent's number are compared with the made-up Jira's. `hierarchy.md`: the index |
| 2 | The tree is rebuilt from identifiers, not from titles | Tested on the made-up project | `tree-run.txt` part 2: the records with every key replaced by another give a printed tree that nests the same numbers under the same numbers. Titles are never asked for, so there is none to build from |
| 3 | A missing parent is reported as an unresolved link, not dropped | Tested on the made-up project only | `tree-run.txt` part 1: no record has the number 40003; DEMO-10 names it as parent; DEMO-10 is in the records, the index and the tree, under a line naming the missing parent. The real project had none |
| 4 | A moved item appears under its new parent | Tested on the made-up project only | `tree-run.txt` part 5: read from the indentation of the tree, 30007 is under 30003, not under 30002, and is there once |
| 5 | Epics, stories, tasks and subtasks are all represented | Shown on the made-up project. **The real sandbox has no epic** | `hierarchy.md` has an Epic, Stories, Tasks and Subtasks. `live-build-1.txt` says "NOT here: epic" |
| 6 | A cycle or a self-parent is rejected | Tested on the made-up project only | `tree-run.txt` parts 3 and 4: exit code 2, the items named, no RESULT line, and the files of the earlier build byte for byte unchanged. A real Jira is not supposed to allow either |
| 7 | The rebuilt tree is identical across two runs | Tested. Seen on the real Jira | `tree-run.txt` part 2: same sha256 for both files after a second build; the tree rebuilt twice from the records gives the same output character for character. `live-build-2.txt`: the same on the real project |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/jira/hierarchy.md` | The made-up project's index and tree. It is the state after the move in part 5 of the record |
| `participant/context/jira/hierarchy.json` | The records that page is written from |
| `participant/context/jira/hierarchy-sandbox.md`, `.json` | The real sandbox project: numbers, keys, types and parents. No titles or people |
| `participant/skills/jira-read-hierarchy/hierarchy.py` | The tool: `build` and `tree` |
| `participant/skills/jira-read-hierarchy/SKILL.md` | When to use it, and the rules for whoever uses the tree |
| `participant/skills/jira-read-hierarchy/fake_jira.py` | The made-up Jira, and its own commands for changing its project |
| `participant/skills/jira-read-hierarchy/tests/test_hierarchy.py` | 103 tests |

Under `participant/evidence/jira-read-hierarchy/jira-attempt-020/`:

| Path | What it is |
|---|---|
| `logs/tree-run.txt` | Built twice the same; a self-parent and a loop rejected; an unresolved link kept; a moved item matched by its number. 24 checks |
| `logs/live-build-1.txt`, `logs/live-build-2.txt` | The real sandbox, read only, twice in a row, with the final tool |
| `logs/before-readers/` | The first real run, made with the tool **before** the fixes. Kept as it was |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 103 tests passing; 81 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed. Written by hand |
| `scripts/record_tree.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-020`. The required record and this file
are copied to `participant/evidence/jira-read-hierarchy/attempt-001/`, with a note there saying so.

## Stretch goals

- **Roll-up of estimates up the tree: done.** Each item shows its own original estimate and the total of everything
  beneath it. An item with no estimate is "no estimate", and each total says how many items in it had none. Items
  under a parent that was not retrieved are totalled apart and added to no one. **The real sandbox has no estimates
  at all,** so on a real Jira this has only been seen to say so.
- **Issue links that are not parent links: done.** They are listed in their own section, by number, each once
  though Jira gives each at both ends. They are never used to build the tree: a test adds a link and requires the
  tree's checksum not to move.

## How to reproduce the behavior

Python 3.9 or later, with nothing installed. From the `participant` folder:

    cd skills/jira-read-hierarchy && python3 -m unittest tests.test_hierarchy
    python3 evidence/jira-read-hierarchy/jira-attempt-020/scripts/record_tree.py
    python3 skills/jira-read-hierarchy/hierarchy.py tree --records context/jira/hierarchy.json

The second command deletes `hierarchy.json` and `hierarchy.md` and makes them again.

Against a real Jira, by a person, with `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` set in their terminal:

    python3 skills/jira-read-hierarchy/hierarchy.py build --source live --project SCRUM \
        --out-dir context/jira --name hierarchy-sandbox

## What was tested or validated

- **103 tests.** Each criterion; the printed tree read back by its indentation; loops of every size; a chain of
  3,000; pages, a failed page, a repeated item, a reading that stops early, an item moved between the two readings,
  and Jira's count disagreeing, each writing nothing; estimates and links; a records file changed by hand; the files
  of other people; a real server's refusals; and the live command run as a person runs it, with the network stood
  in for.
- **81 planted bugs,** each put into a copy of the tool and caught by at least one test. Two were missed on the first
  run, and four more after the readers' fixes, because a new check had come to hide an older one. Tests were added
  each time. Five mistakes are not planted, with the reason, at the end of the record.
- **24 checks** in the record.
- **Two builds of a real project,** four requests each: two readings and two counts. Nothing was changed in Jira.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the real project showed that the made-up one had not

- **A subtask for which Jira names no parent.** SCRUM-4 is a Subtask and came with no parent. Jira does not usually
  allow that. My first version listed it among the items with no parent and said nothing. It is now pointed out, in
  the output and on the page, with the words "shown with no parent because none was given, not because it is known
  to have none". I do not know which it is.
- **A total of nothing printed as 0 h.** No item in the sandbox has an estimate, and the first version printed "0 h"
  as each total. That reads as "no work". It now says no item has an estimate.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **The page could be written over someone else's file.** The records file was checked for being the tool's own; the
  page beside it was not. A name that matched a file already in the folder would have replaced it. Now refused.
- **My evidence for criterion 2 did not show it.** In the made-up project keys and numbers run in step, so a tree
  built from keys would have looked the same, and the moved item kept its key. The record now scrambles every key
  and compares, and the moved item gets a new key.
- **A records file changed by hand could forge a line of the output,** with a key that held a line break and the
  word RESULT. Every field of a records file is now checked before anything from it is printed.
- **The files were written before the search for credentials.** The search now comes first.
- **A missing estimate still showed as 0 h in one summary line.** Fixed.
- **Numbers with a leading zero** were compared as text and sorted as numbers. They are now refused.
- **A very deep chain could not be built,** `--log` could overwrite an unrelated file, and "all four are here" could be
  fooled by a type merely named Epic. Each fixed.
- **Eleven mistakes the tests would not have noticed,** among them the tree printed flat. Tests added for each.
- **Six checks in the record claimed more than they tested.** Each was changed.
- **Neither reader found** a way to have a loop accepted, an item put in two places, or an item dropped.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **No move, loop, self-parent or missing parent has been seen on a real Jira.** Nor more than one page, an epic, an
  estimate, or a link read from its far end. All are shown on the made-up Jira, which is my model.
- **"Jira names no parent" is what Jira sent.** If Jira leaves the parent out of an answer, the item looks like one
  with no parent. Only a subtask in that state is pointed out. SCRUM-4 is one, and I cannot explain it.
- **It reads one project.** A parent in another project is an unresolved link. A child in another project is not
  known about at all.
- **An item hidden from the account is missed by both readings and by Jira's count alike.** Its children then show as
  unresolved links, which is said, but the reason is not known.
- **Jira calls its count approximate.** In four real builds it equalled the items read. If it were ever off, the build
  would be refused when it need not be.
- **The totals are the tool's own sums.** A team that already writes the children's sum into the parent by hand would
  have it counted twice here.
- **A story and a task are known by those two English names.** On a site that names them otherwise the tool would say
  they are not here. An epic and a subtask go by Jira's own mark.
- **A rejected or refused build leaves the earlier files in place.** The output says they are older. A person who
  looks only at the folder could take them for today's.
- **Changes that cancel out between the two readings** are not seen.
- **The live records have no command line or exit code in them.**
- **The site fingerprint is a short, unsalted hash of the site's name.** Someone who guesses the name can confirm it.
- **The sample page shows the made-up project after the move,** not as it started. The record shows both.

## Reflection

*Where might Jira's own hierarchy mislead you about how work is really grouped?*

In the first place, by being nearly empty. My real project has twenty-five items and one parent link. A tree drawn
from it says twenty-four pieces of work have nothing to do with each other, which is not true: it only means nobody
filed them under anything. The one relationship that says something real, that one task blocks another, is not a
parent link at all, and a tool that only kept parents would have thrown it away. So the hierarchy shows how the work
was filed, and the links show how it depends, and those are different groupings. Second, Jira can simply not tell
me. One subtask came back with no parent. A subtask is supposed to have one. I do not know whether it has none or
whether the answer left it out, and my first version quietly put it at the top with everything else. Third, the
tree stops at the edge of what I read. A story whose epic lives in another project looks like a story with no epic
unless the tool says "there is a parent, and I did not fetch it". And last, numbers added up a tree look more
certain than they are: a total of nothing printed as zero hours, or a parent's own estimate that someone already
meant as the sum of its children. What I take from it is that the tree is one honest picture of how things were
filed, and that I should say what it is a picture of before anyone plans from it.

## Sensitive values

No token, password or cookie is in any file of this quest. The token was typed by the participant into their own
terminal and was not seen by the assistant. Every live output was searched for the token, the email address and their
encoded form before it was shown or anything was written, and the site's address is replaced by a marker in the
saved copies. Titles, descriptions and people are not asked for and not kept. The sandbox files hold numbers, keys,
type names and one link. The project key SCRUM and a short hash of the site's name do appear. The made-up project is
made up.

# PROOF: Generate Repository Issue Indexes

Quest `github-build-index`, attempt `github-attempt-006`.

## How this was made

The generator, its tests, the made-up records, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in three decisions: build
the index from a made-up set of records in the read-issue format; give every file exactly one row and list
gaps by name; and keep the index honest with a fingerprint of its records and a `check` command, with no date
stored in it. Nothing in this quest contacts GitHub, and no token was used.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**not assessed** means nobody checked it. Nothing here was observed on real GitHub, because nothing here
talks to GitHub.

## Approach

One script, `participant/skills/github-build-index/index.py`, with four commands.

- `build` reads every record in the folder and writes the whole index. Nothing of the old file is kept.
- `check` builds the index again in memory, writes nothing, and says UP TO DATE, STALE or EDITED BY HAND.
- `lookup` answers by repository, label, milestone or assignee, **from the index**.
- `find` searches the text of the **records**.

The index is one file with a main table, one row per record, then the four lookups, then gaps, files that
could not be indexed, and issues held in more than one file.

## How I know every record was indexed (criterion 2)

Four things, each independent of the others.

1. **Every file goes somewhere.** The build lists every `.md` file in the folder and puts each in exactly one
   of two places: a row in the main table, or a row under "Could not be indexed" with the reason. There is no
   third outcome, and no file is skipped for having a gap.
2. **The build counts before it writes.** It reads back the text it is about to write, collects the file
   behind every row, and compares that list with the list of files. If they are not the same, or a file is
   there twice, or the counts in the header do not agree with the files, it stops and writes nothing. Two
   tests make the build produce a wrong index on purpose, and it is not written.
3. **The recording script counts for itself** (the hint). In part 2 of `logs/index-run.txt` it counts the
   files in the folder with its own code and the rows in the index with its own pattern: 12 files, 12 rows,
   12 different files linked, 12 different issues. It also checks that each row's repository and number are
   the ones in that record's front matter.
4. **"Once" is checked two ways.** No file has two rows. And no issue (repository and number) is in two rows.
   If the same issue is saved in two files, both keep their rows and the index flags it, with exit code 3.
   Tested.

What "every record" means here: every `.md` file directly in the one records folder. A record saved in
another folder or a sub-folder is not seen. That is a limit, stated below.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The index is generated, never hand-edited | recorded, tested | `index-run.txt` part 6: a hand edit is found by `check`, and is gone after the next build. Tests `Generated` |
| 2 | Every local record appears once | recorded, tested | Part 2. Tests `EveryRecordOnce`. See above |
| 3 | Lookup by repository, label, milestone and assignee works from the index | recorded, tested | Part 3: each answer is compared with one the recording script worked out from the records. A copy of the index with no records beside it still answers. Tests `Lookups` |
| 4 | A record with a missing field is listed as a gap | recorded, tested | Part 5. Tests `Gaps` |
| 5 | Two builds from the same records are identical | recorded, tested | Part 1: byte for byte, and a third build from copies with other dates and order. Tests `Identical` |
| 6 | Adding a record changes the index without a hand edit | recorded, tested | Part 4. Tests `Adding` |
| 7 | The index is stated not to be the source of truth | recorded, tested | Part 8, and the first lines of `participant/context/github/index.md`. Tests `NotTheSourceOfTruth` |

### Criterion 1: "never hand-edited" is a claim about the future

The generator cannot stop a person opening the file. What it does:

- the file says at its top that it is generated and must not be edited;
- a build never merges. It writes the whole file from the records, so an edit does not survive;
- `check` finds an edit. It compares the file with a fresh build. If the records are the ones the index was
  built from and the text differs, it says EDITED BY HAND and names the first line that differs.

So the claim that holds is: a hand edit is found when `check` is run, and lost at the next build. Nothing
finds it before then.

### Criterion 4: a gap is not "none"

Three things are kept apart, by the participant's decision:

- the record says there is no milestone: shown as *none*, and not a gap;
- the record should have the field and does not: shown as **GAP**, listed under "Gaps", looked up under GAP;
- the file is not a record at all: listed under "Could not be indexed".

Part 5 shows the first two side by side: the damaged record is not in the answer to "issues with no
milestone", and the two issues that truly have none are.

## Artifacts

| Required item | File |
|---|---|
| The generator | `participant/skills/github-build-index/SKILL.md`, with `index.py` beside it |
| The index | `participant/context/github/index.md` |
| The run log | `logs/index-run.txt`, 44 checks |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (61 tests), `logs/planted-bugs.txt` (31 planted bugs),
`scripts/record_evidence.py` and `scripts/planted_bugs.py`. In the skill folder: `make_records.py`, which
writes the made-up records, and `tests/test_index.py`.

The records are `participant/context/github/issues/`: twelve files. Eleven were written for this quest by
`make_records.py`, using the `github-read-issue` skill's own code, so they are real records in its format. The
twelfth, `issue-sample.md`, is the one that quest handed in. It was not changed: its checksum is the same
before and after. Every repository, person, label, milestone and issue in them is invented.

## Stretch goals

- **Add a text search:** done, as `find`. It searches the records' titles, bodies and comments, and says it
  reads the records, not the index. Recorded in part 7.
- **Show the index age:** done, in `check`, not in the index. An age stored in the file would change it at
  every build and break criterion 5. `check` reports how long ago the file was written and how many records
  were written after it. Recorded in part 7.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-build-index/tests -v
    python3 participant/evidence/github-build-index/github-attempt-006/scripts/record_evidence.py
    python3 participant/evidence/github-build-index/github-attempt-006/scripts/planted_bugs.py

None of these contacts anything. The second builds `index.md` again, with the same bytes. The third changes
`index.py` while it runs and restores it. To write the eleven made-up records again:

    python3 participant/skills/github-build-index/make_records.py

## What was tested

| What | Result |
|---|---|
| Automated tests | 61, all pass (`logs/tests.txt`) |
| Planted bugs | 31 put into `index.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 44, all pass |

Faults found while building:

- **In the generator, one, found by its own count check on the very first build.** The pattern that finds the
  record file at the end of a table row started too early when a title held brackets, so the count came out
  wrong and the build refused to write. The pattern was corrected. This is the check of criterion 2 doing its
  job, on the assistant's own mistake.
- **In the generator, one, noticed by reading the first index.** An absent milestone and a milestone actually
  titled "(none)" looked the same in the table. Absent values are now written in italics, which text from a
  record can never be.
- **In the assistant's tests, five,** on first run: a miscounted expectation, and four patterns that were too
  loose or too strict.
- **A false alarm from the repository's secret scanner.** It flagged a constant whose name ended in `_KEY`,
  as if a secret were being assigned. No secret was there. The constant was renamed, and the scanner was left
  as it is.

## What could not be done, and limitations

- **Real records: not assessed.** The index was built from made-up records only. The two real records from
  the read-issue quest are outside the repository and were not indexed.
- **The index cannot tell that a record is out of date.** It compares itself with the records, not with
  GitHub. If an issue changed on GitHub after its record was saved, the index and the record agree and both
  are wrong.
- **Nothing runs `check` by itself.** A stale or edited index is found only when someone runs it. `lookup`
  answers from the index as it is, and says so, and does not refuse when the index is stale.
- **One folder.** Records in another folder or a sub-folder are not indexed and not counted.
- **A milestone is grouped by title.** Two repositories each with a "Sprint 13" share one group. Each line
  names its repository. This shows in the handed-in index.
- **Only the body is checked against its checksum,** not each comment.
- **When records changed and the index was also edited by hand,** `check` says STALE and does not also say
  edited.
- The index does not hold authors, dates or comments. `find` reads those from the records.
- `make_records.py` needs the `github-read-issue` skill's folder. `index.py` does not.
- The generator, the recording script's own counting and the tests were written by the same assistant. They
  were written apart, and can still share a blind spot.

## Reflection

*What could make the index disagree with the records unnoticed?*

Time, mostly. The index is right at the moment it is built. A sync adds a record five minutes later and the
index is wrong, and nothing tells me, because nothing runs the check unless I do. The check works, and it
names the record that was added. But "unnoticed" is about whether anyone looks, and I built a lookup that
answers from a stale index without complaint. If I used this every day I would make the sync build the index
as its last step, so the two could not drift apart.

A hand edit is the second way. I can stop it surviving a build, and I can find it with the check, but between
the edit and the next check the index says something the records do not.

The third way surprised me, because it is not a disagreement at all. The index can agree with the records
perfectly and still be wrong, when the record itself is out of date with GitHub. The fingerprint proves the
index matches the files. It proves nothing about the files. So "the index is up to date" is a smaller claim
than it sounds, and the statement at the top of the file is there for that reason.

And the quiet one: a record the index never sees. A file saved in another folder is not missing from the
count, because it was never counted. The row count equals the record count, and both are short by one.

## Sensitive values

- No credential was used or needed. Nothing was contacted.
- Every record, and so every title, label, milestone and login in the index and the log, is made up. The
  logins, such as `robin-fixture`, are invented.
- The index holds titles, which on real records would be other people's text and could be private. An index
  built from real records should be treated like the records.

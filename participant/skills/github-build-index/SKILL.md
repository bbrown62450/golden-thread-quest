# GitHub: build the index of local issue records

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill makes the local copy of GitHub issues findable. It reads the issue records that the
`github-read-issue` skill saved, and writes one index of them, `participant/context/github/index.md`.

Its rule: **the records are the source of truth. The index is generated from them, whole, every time, and it
says what it could not index.**

It reads local files only. It contacts nothing, needs no token, and never writes to a record.

    python3 participant/skills/github-build-index/index.py build
    python3 participant/skills/github-build-index/index.py check
    python3 participant/skills/github-build-index/index.py lookup KIND VALUE
    python3 participant/skills/github-build-index/index.py find TEXT

`--records FOLDER` and `--out FILE` point it somewhere else. By default the records are in `issues/` beside the
index. The skill uses the Python standard library only.

## 2. What counts as a record

Every `.md` file directly in the records folder, in the format `github-issue-markdown/1`. Sub-folders, hidden
files and other kinds of file are not records and are not counted.

The index reads each record's front matter: repository, number, title, state, labels, milestone, assignees. It
also cuts the body back out and checks it against the checksum the record holds.

## 3. `build`

Reads every record and writes the whole index. Nothing of the old file is kept, so a hand edit does not survive
a build. The file is written only if its bytes would change.

Every file gets **exactly one row**:

- a record: one row in the main table;
- a file that is not a record (no front matter, another format, not text): one row under "Could not be
  indexed", with the reason.

Before it writes, the build reads its own text back and counts. If the rows are not exactly one per file, or
the counts in the header do not agree with the files, it stops and writes nothing.

Exit code 0 when clean. Exit code 3 when the index was built and a person should look: a gap, a file that could
not be indexed, or one issue held in two files.

## 4. The index

1. **The statement** that the file is generated, is not the source of truth and must not be edited by hand.
2. **Counts and a fingerprint**: files found, indexed, with a gap, could not be indexed, issues in more than one
   file, and one fingerprint worked out from every record file's name and contents.
3. **All records**: one row each, sorted by repository and number.
4. **By repository, By label, By milestone, By assignee**: the four lookups. Each has a group for issues that
   have none, and a group for records where the field is a gap.
5. **Gaps**.
6. **Could not be indexed**.
7. **Issues held in more than one file**.

It holds no date and no time. The same records always give the same bytes, whatever the files' dates and
whatever order they were written in.

## 5. Gaps

Three things that are kept apart:

- ***none***: the record says the issue has no milestone, no label or nobody assigned. A fact, not a gap.
- **GAP**: the record should have the field and does not. The line is missing, cannot be read, or holds the
  wrong kind of thing. The record keeps its row, with **GAP** in that field, is listed under "Gaps", and is
  looked up under "GAP", never under "none".
- **Could not be indexed**: the file is not a record at all.

A body that no longer matches the checksum in its record is also a gap: someone changed the record by hand.

## 6. `check`

Builds the index again in memory, writes nothing, and says one of:

- **UP TO DATE**: the file on disk is byte for byte what the records give now.
- **STALE**: a record was added, removed or changed since the index was built. It names each one.
- **EDITED BY HAND**: the records are the ones the index was built from, and the file's text is not what they
  give. It names the first line that differs.

It also reports the index's **age**: how long ago the file was written, and how many record files were written
after it. The age is not stored in the index, so that two builds stay identical.

Exit code 0 when up to date, 3 when stale or edited.

## 7. `lookup`

    index.py lookup repository OWNER/NAME
    index.py lookup label NAME          index.py lookup label --none
    index.py lookup milestone TITLE     index.py lookup milestone --gap
    index.py lookup assignee LOGIN      index.py lookup assignee --list

It reads **the index**, not the records, and says so. Capitals do not matter. `--none` gives the issues with
none, `--gap` the records where the field could not be read, `--list` every value with its count.

A lookup does not check that the index is current. Run `check` for that.

## 8. `find`

    index.py find TEXT

A text search of the **records**: the title, the body and the comments. It reads the records, not the index,
and says so. It does not search the fields or the file's own headings.

## 9. Other people's text

Titles, labels, milestone titles and logins come from GitHub and are other people's text. In the index each is
escaped, so that it cannot break a table row, add a heading or a link, or pass for the skill's own **GAP** or
*none*. A lookup group whose name is not plain is written as JSON. Nothing in a record is acted on.

## 10. The made-up records

`make_records.py` writes eleven made-up issue records with the `github-read-issue` skill's own code, so they
are real records in its format. With `--one` it writes one more. It needs that skill's folder beside this one.
`index.py` itself does not: it reads the records with its own code.

## 11. Tests

    python3 -m unittest discover -s participant/skills/github-build-index/tests -v

The tests work in a scratch folder. Nothing is contacted.

## 12. What it does not do

- It does not contact GitHub, so it cannot tell whether a record is still true of the issue on GitHub.
- It does not index authors, dates, comments or reactions. Those are in the records.
- A milestone is grouped by its title. Two repositories with a milestone of the same title share a group, and
  each line in it names its repository.
- It does not notice by itself that it is stale. Someone has to run `check`.
- It reads one folder. A record saved somewhere else is not in the index.

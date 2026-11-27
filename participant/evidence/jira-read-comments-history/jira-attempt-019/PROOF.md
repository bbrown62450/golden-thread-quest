# Proof · jira-read-comments-history

Attempt: `jira-attempt-019`

## How this was made

The participant made four decisions: to use a made-up Jira for the required records and the real sandbox for one
read-only check; what counts as a material change; that an edit replaces the text and leaves a note, and a deleted
comment stays, marked, with its last text; and to do both stretch goals without storing any person. The participant
ran every command that reached the real Jira, in their own terminal. An AI assistant (Claude) wrote the tool, the
made-up Jira, the tests, the scripts and this file. Two further AI assistants read the work. No person other than
the participant has read it.

## The short version

- **Every comment is under the identifier Jira gave it.** Nothing is matched by its words.
- **A second sync of unchanged data writes nothing.** The two files are byte for byte what they were.
- **An edit replaces the text in place** and leaves a note under the comment. **A new comment is added once.**
- **A deleted comment is marked and kept,** with its last text, and is never taken out by a later sync.
- **Only changes listed as material are kept** from the history. The rules are written from the tool's own lists.
- **The notes file is never written.** Its checksum is the same before and after every sync.
- **Checked against the real sandbox, read-only:** one comment and four material changes copied; a second sync wrote
  nothing.
- **Both readers found that the notes file COULD be written over, in the first version.** That is closed. It was the
  one promise this tool must keep, so it is described first below.

## The notes file could be overwritten, in the first version

**The sync itself never wrote the notes. Two side doors did.**

- `--log` saves the output to a file. I refused it when it named the notes. A reader named the notes in other
  capitals, which this kind of disk treats as the same file, and through a second name for the same file. Both got
  past, and the log was written over the notes. The output had already said "UNCHANGED".
- `rules --write` had no check at all.
- My own tests had found a third before the readers looked: when `--log` named the notes outright, the refusal
  itself was saved over them.

What changed:

- The tool asks the disk whether two paths are one file, and does not compare spellings.
- It refuses to write any file of its own to a place named like a notes file, to a link, or to a file with a second
  name. `rules --write` refuses a file that is there and is not a rules document.
- The notes' checksum is taken again after the log is written, and the command fails if it moved.
- One test now watches every way a file can be opened for writing, replaced, renamed or removed, through a whole run
  of four syncs, and requires that none of them touched the notes.

## My definition of material, and one change I chose to ignore (criterion 5)

**A change is material if it changes what the work is, where it stands, who has it, how urgent it is, when it is due,
or what it depends on.** Everything else in the history is noise for a reader.

| Kept | What is kept of it |
|---|---|
| `status`, `priority`, `issuetype` | The old and the new name |
| `duedate` | The old and the new date |
| `assignee` | "assigned", "reassigned" or "unassigned". No person |
| `summary`, `description` | The fact that it changed. Not the old or new text |
| `link` | Added or removed, with the other item's key, if Jira gives exactly a key |
| `parent`, `issueparentassociation` | The move, with keys if Jira gives keys |

Left out: `rank`, `labels`, `sprint`, `attachment`, watchers, time logged and estimates, `resolution`, comments
(kept in their own right), and links to outside Jira. The full table, with a reason for each, is
`participant/context/jira/history-rules.md`.

**The change I chose to ignore is rank.** Rank is the order of cards on a board. It is written to the history every
time someone drags a card. In the made-up story it is two of fourteen entries; on a busy board it would be most of
them, and the status change a reader is looking for would be somewhere among them.

It is a real loss on some teams. Where the order of the backlog is how urgency is shown, leaving rank out throws that
away. I take urgency from the priority field instead, and the rules say that a team that works the other way should
move `rank` to the first list. **I did not see rank in the real sandbox's history,** so this choice is argued, not
observed.

Three further rules that are not obvious:

- **A field the site's administrators added is never material, whatever it is called.** A reader showed that a
  custom field someone named "Status", holding free text with a person's name in it, was being kept as a status
  change.
- **A kind of change on neither list is not kept and not hidden.** The sync prints it as UNLISTED, with its name and
  count. Story points are one. So, today, are fix version and component, which by my own sentence could be material.
- **Nothing is picked out of a sentence.** A key is kept only when Jira gives exactly a key.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Each comment is keyed by its Jira identifier | Tested. Seen on the real Jira | `sync-twice.txt` part 1: under each identifier is the text the made-up Jira has for it. `comments-sample.md` has one heading per identifier |
| 2 | A second sync of unchanged data adds nothing | Tested. Seen on the real Jira | `sync-twice.txt` part 2: both files have the same sha256 as after the first sync, and were not written. `live-sync-2.txt`: the same, on the real story |
| 3 | An edited comment is updated in place and the change is noted | Tested on the made-up Jira only | `sync-twice.txt` part 4: comment 31002 is in the copy once, is still the entry first copied, has the new text, and the old text is nowhere. The note gives who, when and a checksum of the old text |
| 4 | A new comment is added once | Tested on the made-up Jira only | `sync-twice.txt` parts 4 and 5: 31006 is there once, and still once after another sync |
| 5 | Only changes listed as material in the rules are recorded | Tested. Seen on the real Jira | `sync-twice.txt` part 1: seven kept, each a name in the rules' Material table, which the script reads; six left out; one unlisted. `live-sync-1.txt`: four kept, two left out |
| 6 | A local notes file is unchanged by the sync | Tested on the made-up Jira only | `notes-intact.txt`: same checksum, size and last-written time before and after each of four syncs. The real runs had no notes file beside them |
| 7 | A deleted comment is flagged, not silently removed | Tested on the made-up Jira only | `sync-twice.txt` parts 4 and 5: 31004 is still there, marked, with its last text, and is not marked again by the next sync |

**Criteria 3, 4 and 7 have never met a real Jira.** The quest says to make no change in Jira, so no real comment was
edited, added or deleted.

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/jira/comments-sample.md` | The made-up story's comments and material changes, as the last sync left them |
| `participant/context/jira/comments-sample.json` | The copy that page is written from |
| `participant/context/jira/comments-sample.notes.md` | The local notes file the syncs left alone |
| `participant/context/jira/history-rules.md` | What is material and what is noise. Written by the tool |
| `participant/skills/jira-read-comments-history/sync_comments.py` | The tool: `sync` and `rules` |
| `participant/skills/jira-read-comments-history/SKILL.md` | When to use it, and the rules for whoever uses the copy |
| `participant/skills/jira-read-comments-history/fake_jira.py` | The made-up Jira, and its own commands for changing its story |
| `participant/skills/jira-read-comments-history/tests/test_sync_comments.py` | 113 tests |

Under `participant/evidence/jira-read-comments-history/jira-attempt-019/`:

| Path | What it is |
|---|---|
| `logs/sync-twice.txt` | Four syncs: first; unchanged; after an edit, an addition and a deletion; unchanged again. 21 checks |
| `logs/notes-intact.txt` | The notes file's checksum before and after each. 11 checks |
| `logs/live-sync-1.txt`, `logs/live-sync-2.txt` | The real sandbox, read only, twice in a row, with the final tool |
| `logs/before-readers/` | The first real run, made with the tool **before** the readers' fixes. Kept as it was |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 113 tests passing; 80 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed. Written by hand |
| `scripts/record_syncs.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-019`. The two required records and this
file are copied to `participant/evidence/jira-read-comments-history/attempt-001/`, with a note there saying so.

## Stretch goals

- **Record who edited a comment: done, without storing a person.** The note says "its author", "someone else" or
  "unknown". Two account identifiers are compared and dropped. So it tells an author's own correction from a change
  made by another hand, and does not say whose hand.
- **Show the time between a change and its sync: done.** Each edit and each material change carries when Jira says it
  happened, when a sync first noticed it, and the time between, such as "4 hours" or "5 days 23 hours".

## How to reproduce the behavior

Python 3.9 or later, with nothing installed. From the `participant` folder:

    cd skills/jira-read-comments-history && python3 -m unittest tests.test_sync_comments
    python3 evidence/jira-read-comments-history/jira-attempt-019/scripts/record_syncs.py
    python3 skills/jira-read-comments-history/sync_comments.py rules

The second command deletes `comments-sample.json` and `comments-sample.md` and makes them again. It does not make,
change or delete `comments-sample.notes.md`, and stops if that file is not there.

Against a real Jira, by a person, with `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` set in their terminal:

    python3 skills/jira-read-comments-history/sync_comments.py sync --source live --issue SCRUM-1 \
        --out-dir ../local-data/jira-read-comments-history --name scrum-1

## What was tested or validated

- **113 tests.** Each criterion; pages of comments and of history; a failed page, a short count, a repeated comment
  and an unreachable Jira, each leaving the copy as it was; every kind of material change and what is kept of it;
  the notes file through every kind of sync; comments that try to break out of the page; a copy changed by hand; a
  real server's refusals; and the live command run as a person runs it, with the network stood in for.
- **80 planted bugs,** each put into a copy of the tool and caught by at least one test. Two were missed on the first
  run and tests were added. Twenty-four were added after the readers' reports. Five mistakes are not planted, with
  the reason, at the end of the record.
- **32 checks** in the two records.
- **Two syncs of a real story,** three requests each, every one a GET with no body.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **The notes file could be written over.** Both found it. Described above.
- **A comment that is still there could be marked as gone.** The list comes in pages. If one comment is deleted and
  another added while the pages are read, a third can fall between two pages, with every count agreeing. Now a
  comment missing from the list is asked for by its own identifier, and only Jira answering 404 marks it.
- **Free text and people's names could reach the copy through the history.** Fields were matched by display name,
  and keys were picked out of sentences. Both changed, as above.
- **A note went stale.** "Already edited when first copied" showed the latest edit time, not the one it described.
- **Comments were not always whole, and did not say so.** A date or a card became a placeholder silently. The page
  now says when. A body that changed with the same words was called an edit. It is now noted as something else.
- **One comment the tool could not read stopped every sync of the story.** It is now kept, flagged.
- **About a dozen mistakes the tests would not have noticed.** Among them: redirects followed, times labelled UTC without
  being converted, a truncated list taken for whole. Tests added for each.
- **Eight checks in the records claimed more than they tested,** two of which could not fail. Each was changed.
- **Several statements in the rules document were untrue or incomplete.** Corrected, and the one-sentence rule rewritten,
  because status, priority and links did not follow from the first version of it.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **No edit, addition or deletion has been seen on a real Jira.** What Jira does then is my model of it.
- **"Not returned" is not always "deleted".** A comment hidden from the account that reads looks the same.
- **I do not know whether Jira's count of comments includes ones hidden from the account.** If it does, a story with
  a hidden comment would be refused every time, because fewer arrive than the count says.
- **Only the latest text of an edited comment is kept.** Two edits between two syncs are seen as one, and the text
  replaced survives only as a checksum.
- **The copy keeps words someone chose to delete.** The participant decided this. For real comments it is a privacy
  cost, which is why a live sync writes only inside `local-data/`.
- **"The same name" for a status.** The real story has a change from To Do to To Do. Names are kept, not Jira's
  internal numbers, so the tool says that Jira recorded a change and cannot say what it was.
- **`issueparentassociation` is a guess at Jira's name** for a move under another parent. Not seen.
- **The name of an unlisted field is printed.** It is the site's own name for a field. It could hold a person's name
  if an administrator put one there.
- **Two syncs of one copy at the same moment are not guarded against.** A sync killed partway can leave a temporary
  file whose name begins `.sync-`.
- **A comment's lines are set in by four spaces on the page,** so that none starts like a line of the page itself.
  Something that reads the page line by line without knowing that could still be misled by the words.
- **The live records have no command line or exit code in them,** and nothing in them shows the site is a sandbox.
- **The site fingerprint is a short, unsalted hash of the site's name.**
- **Rank was not in the real story's history.**

## Reflection

*What does a deleted comment mean for an audit?*

It means the record and the system no longer agree, and somebody has to be able to say which one is right. If my
copy quietly dropped the comment when Jira did, the copy would always match Jira, and it would be worthless as a
record: it could only ever tell me what Jira says today. So the comment stays, with its last text and the date I
first found it gone. But building this showed me how little that mark really says. I cannot tell a deleted comment
from one that was hidden from my account. I do not know who removed it or when, only when I noticed. And in my first
version a comment could be marked gone while it was still sitting in Jira, because the list shifted while I was
reading it. A false "deleted" is worse for an audit than a missing one, because people act on it. So now the tool
asks Jira about that one comment before it says anything. The other thing I had not thought about is that keeping
the text is itself a decision about someone else's words. They took them down and I kept them. For an audit that is
the point. For the person it may not be. I decided to keep them, said so in the rules, and kept the real ones out of
anything I hand in.

## Sensitive values

No token, password or cookie is in any file of this quest. The token was typed by the participant into their own
terminal and was not seen by the assistant. Every live output was searched for the token, the email address and their
encoded form before it was shown, and the site's address is replaced by a marker in the saved copies. The real
story's comment text is in `local-data/`, which is not handed in, and is in no record: the records hold identifiers,
counts, status and priority names, dates and item keys. No person is named anywhere: the tool keeps none. The keys
SCRUM-1 and SCRUM-25 and a short hash of the site's name do appear. Every comment in the sample is made up.

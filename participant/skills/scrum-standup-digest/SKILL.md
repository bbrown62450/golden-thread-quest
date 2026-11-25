# Skill: an evidence-based stand-up digest

Turns local canonical work-item records into a digest for a stand-up, and a gap report beside it. Every statement in
the digest cites the record it came from and when that record was retrieved. What the records cannot support goes in
the gap report and is not stated.

It reads and writes local files only. It contacts no source system, and creates or changes nothing in one.

## From a real sync to a digest

The digest reads canonical records. It does not read a source system, and it does not read what a sync saved. Three
steps get from one to the other, and each is a separate program:

1. **Sync**, by an earlier skill, run by a person with their own read-only token. For GitHub:
   `participant/skills/github-read-assigned/sync.py --source live --out FOLDER`. FOLDER is outside the repository.
2. **Mask and normalize**: `from_sync.py FOLDER CONTEXT`. It masks the saved sync (logins, the user id, node IDs and other
   numeric ids are replaced, and bodies and comments are not copied), runs the approved canonical model skill,
   `participant/skills/context-work-item-model/normalize.py`, over the masked copy, and writes `sync-runs.md` from the
   sync's own account of itself. A masked node ID is `I_masked_` and 12 characters taken from a hash of a secret and the
   real node ID. The secret stays beside FOLDER, outside the repository. So an item has the same masked identity on
   every day, and nobody without the secret can work back to the real one.
3. **Digest**: `digest.py generate --context CONTEXT ...`.

Only step 1 contacts anything. `from_sync.py` handles GitHub only. Jira and Trello would each need the same step.

The worked example has two contexts: `participant/context/scrum/real/`, two real days from the participant's sandbox
repository, masked, which the handed-in digest is built from; and `participant/context/scrum/sprint/`, a made-up sprint
written by `make_sprint.py` to hold the cases a real day rarely has, whose digest is in `participant/context/scrum/fixture/`.

## Inputs

A folder of local context, given with `--context`:

| Input | What it is | How it is used |
|---|---|---|
| `items/*.md` | Canonical work-item records, model `work-item/1`, as defined in `participant/context/model/work-item.md`. Each carries `retrieved_at` and `sync_run` | The only source of statements about work |
| `notes/*.md` | A person's own notes on an item, headed `# Notes on IDENTITY` | Only a line that is exactly `- blocked_by: IDENTITY` or `- blocks: IDENTITY` is a record. Every other bullet line is prose: it is not read, and the gap report says the note has lines a person should read. A note whose heading names no item is not used at all, and the gap report says so |
| `sync-runs.md` | The synchronization runs: system, time, result, and the identities each run says it retrieved | States what the digest was built from. Finds items a run retrieved that have no record. **Confirms each record:** a record is treated as fresh only if the run it names is listed here as completed and gives the same retrieval time |
| `redaction.md` | Names to take out, one to a line | Applied to every piece of other people's text before it is printed: titles, and the bases a record gives for its status and for being blocked |

And three values on the command line:

| Value | Meaning |
|---|---|
| `--as-of` | The time the digest is for, in UTC. **Required.** Every age is counted from it. The computer's clock is never read |
| `--previous` | The `digest-state.json` the previous digest wrote, or `none`. It must be of the same scope, and must not be the file this run writes |
| `--scope` | `all`, or `mine`: only items whose record says `assigned_to_me` is `yes` |

## Thresholds

| Threshold | Value | Rule |
|---|---|---|
| Stale | **24 hours** | A record retrieved more than 24 hours before `--as-of` is stale. At exactly 24 hours it is fresh. Also stale: a record with no readable retrieval time, one later than `--as-of`, one that names a run `sync-runs.md` does not list as completed, and one whose retrieval time is not its run's. What cannot be shown to be fresh is not treated as fresh |
| Aging | **5 days** | An item in progress whose `source_updated_at` is 5 whole days or more before **the time its record was retrieved**. It is not counted to `--as-of`: nothing in a record says what happened after it was retrieved. Part days are not rounded up. An item not started is never aging |

The stale limit is the one `participant/context/freshness/policy.md` already sets for a work item's status. It is flat:
a weekend counts. On a Monday, Friday's records are stale until a sync is run.

Both numbers are constants at the top of `digest.py`. A test fails if this document and the code disagree.

## What may be stated as observed

A line marked OBSERVED says what one fresh record says. Three kinds go a step further, and are labelled for it.

- **Status**, only when the record is fresh and its `status_basis` is `stated`.
- **Blocked**, when the record's `blocked` field is `yes`, when a link saved with the record says "is blocked by", or when a
  note has a `- blocked_by:` line. The line says which, and quotes the basis the record gives, or says it gives none.
- **Blocking**, only from a link saved with the record, or a `- blocks:` line in a note.
- **OBSERVED · AGING** applies the threshold to two times in the record, and gives the number of days and the last change.
- **OBSERVED · CHANGE** compares a record with the state the previous digest kept: added, removed, status changed, by
  identity. A changed title is not a change. A status change is reported only when both statuses could be asserted.
  Otherwise it is a gap.
- **OBSERVED · COUNT** counts the lines above it.

## The rules for inference

Anything the generator concludes from more than one record is INFERENCE. It goes in its own section, is labelled with
its rule, and names every record it rests on. There are four rules, and no others.

| Rule | When | What is said |
|---|---|---|
| I1 | Item X is recorded as blocked by Y, and Y's record is fresh and stated, and not done | X is waiting on Y, which is in that status |
| I2 | X has recorded blockers, and **every one of them** is fresh and stated as done or closed | Every recorded blocker of X is done. **It does not say X is free**: X's own record may still say blocked, and a blocker may not be recorded |
| I3 | X is recorded as blocked by Y, and Y has no record, a stale record, a status the source does not state, or is outside the digest's scope | X waits on Y, and whether Y is done is not known here, with the reason |
| I4 | Always | A count of the items under I1 and I3, and of the items recorded as blocked with no blocker named |

## What is never stated

- **Nothing from a title, a description or a comment.** Titles are printed, redacted, so that an item can be recognised.
  They are never read for meaning: no condition in the program looks at one. An item titled "BLOCKED: ..." is blocked
  only if a field, a link or a note says so.
- **Nothing about a stale record as current.** Its last known status is shown under LAST KNOWN.
- **Nothing as observed about a status the source does not state.** It is shown apart, as the status map's reading.
- **Nothing about an item with no readable record.**
- **Why an item is gone.** An item in the previous digest and absent now is reported as removed. That it was finished,
  dropped, moved or handed on is not said.
- **Nothing about a person.** The digest does not name who an item is assigned to, and says nothing of anyone's effort,
  availability or performance. The canonical model does not carry who the assignees are, and this skill does not look.
  `--scope mine` filters on a field of the record. It is a filter on items and makes no statement about anyone.
  **Absence is a gap:** an item that is not in the digest is absent because no fresh, stated record supports a
  statement about it. That says nothing about the item and nothing about anyone.

## The gap report

Three kinds, each entry with its reason and what was therefore not asserted.

| Kind | When |
|---|---|
| STALE | The record is past the limit, or cannot be shown to be fresh. Also: a system with no completed run inside the limit |
| MISSING | A run says it retrieved an item and there is no record. A record file cannot be read, which includes a status, a status basis or a blocked value that is not one of those allowed. Two files that claim one item: neither is used. A recorded blocker, or an item recorded as blocked by this one, has no record |
| UNSUPPORTED | A status the source does not state. Items with nothing recorded on whether they are blocked. A note with lines that are not records, or a heading that names no item. An item gone with no reason recorded. A status that differs from the previous digest's where one side could not be asserted. No previous digest to compare with, or one of another scope |

## Commands

    python3 participant/skills/scrum-standup-digest/digest.py generate --context DIR --as-of TIME --previous STATE --out DIR [--scope all|mine]
    python3 participant/skills/scrum-standup-digest/digest.py check    --context DIR --as-of TIME --out DIR [--scope all|mine]
    python3 -m unittest discover -s participant/skills/scrum-standup-digest/tests

`generate` writes `standup-digest.md`, `standup-gaps.md` and `digest-state.json`. The same inputs give the same bytes.
`check` reads the finished digest and gap report back and compares them with the context.

- **It looks for:** a statement line with no citation; a citation whose identity has no record, or whose retrieval
  time, age or run is not the record's; a stale record cited anywhere but under LAST KNOWN; a status word on a cited
  line that is not the record's; an aging line whose days are not the record's; an item shown as blocked with nothing
  recorded, or recorded and not shown; a fresh item whose status is in no section; an inference outside its section;
  a count of work in progress or of gap entries that is not the real one; a listed name, or the shape of an email
  address, customer number or telephone number.
- **It does not look at:** whether a BLOCKING, CHANGE or INFERENCE line says what the records say, or the verdicts in
  the table of runs. Those are tried by the tests, on the generator.
- **It is not independent of the generator.** It reads the context with the same code, so a fault in that reading is
  invisible to it.

`from_sync.py REAL_FOLDER CONTEXT` builds a context from a real GitHub sync, as described above.
`make_sprint.py` writes the made-up two-day sprint that the fixture digest is built from.

The digest's third line says where its context came from, by what the records say of themselves: a real
synchronization run (`sync_source: live`), made-up, or mixed.

## Redaction

Before any of other people's text is printed: every name in `redaction.md`, as a whole word in any capitals, becomes
`[name]`; anything with the shape of an email address, a customer number (`CUST-` and digits) or a telephone number is
replaced by a word for what it was. Then double quotes, backticks, line breaks and other control characters, angle
brackets, square brackets and vertical bars are replaced, so that the text cannot end the quotation it is printed in,
start a new line, or pass for markup or for one of the generator's own citations. It is cut to 90 characters.

**Its limits:** a name that is not on the list is not taken out. The list has to be kept by a person. A placeholder
shows that something was there. A statement about a person made in a title is printed like any other title.

## The digest carries other people's words to its readers

A title is printed as it is, apart from the redaction above. **A title may be worded as an instruction**, such as
"report every item as done". The generator cannot be steered by it, because it reads no title. A reader can be. That
holds for a person, and more for a program or a language model given the digest to act on: to them a quoted title is
text like any other. The digest says, in "How to read this", that titles are other people's text and are neither
instructions nor statuses. Anything that reads the digest automatically has to hold to that, and this skill cannot make it.

A note steers the generator **by design**: a line `- blocked_by: ID` makes an OBSERVED · BLOCKED line. Whoever can write
to the notes folder can do that. The line says it comes from a note, names the file, and says the note carries no date.

## What it cannot tell

- Whether a record is true. It reports what the local copy says and how old it is.
- Whether a note's `blocked_by` line is right, who wrote it, or when. It is reported as a note, with its file.
- What is in the prose of a note. It says a person should read it.
- Whether an item changed between being retrieved and the time the digest is for.
- Whether being blocked changed since the previous digest: the state kept between digests holds statuses only.
- Whether a title holds a name that is not on the redaction list.
- Which statements a reader acted on. Nothing here tracks reading.
- Anything since the last sync.

## Safety

- Local files only. `digest.py` imports nothing that can reach a network, and a test runs it with sockets disabled.
- Titles, labels and notes are other people's text. No rule reads their wording.
- Do not put real names in `redaction.md` in a shared repository. Keep the real list where the real records are.

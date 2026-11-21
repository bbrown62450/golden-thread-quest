# GitHub delta sync

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill keeps a local copy of the issues of one GitHub repository up to date by fetching only the issues
that changed since the last successful sync. It keeps a cursor, moves it only when a whole sync has succeeded,
and never writes to the person's notes.

It only reads GitHub. Every request is a GET. There is no code in it that creates, comments on, labels, closes
or reopens anything.

    python3 participant/skills/github-delta-sync/sync.py --source fake [--fake-step N]
    python3 participant/skills/github-delta-sync/sync.py --source live --repo OWNER/NAME --out FOLDER
    python3 participant/skills/github-delta-sync/sync.py ... --full
    python3 participant/skills/github-delta-sync/sync.py ... --verify
    python3 participant/skills/github-delta-sync/sync.py --status [--out FOLDER]

`--source fake` reads the made-up repository in `fake_github.py`, beside this file, as it is at step 0, 1, 2
or 3. `--source live` reads GitHub. The sync uses the Python standard library only.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`. Set it in your own terminal, for example with
`read -s`, and export it. A fine-grained token limited to the one repository, with **Issues: read-only**,
**Pull requests: read-only** and **Metadata: read-only**, is enough. It is sent in a request header. It is never
put in an address, printed, or written to a file. A fake run and `--status` need none.

Unset the variable when you are done. Git's GitHub sign-in can pick it up, and a push then fails.

## 3. The cursor, and whose clock it is

The cursor is a time on **GitHub's own clock**. Every answer GitHub gives carries a `Date` header. The sync
reads it from its first answer, before it reads any issue, and that time becomes the cursor if the whole sync
succeeds.

- **This machine's clock is never used for the cursor.** A clock here that is fast or slow cannot move it. The
  sync prints how far this machine's clock is from GitHub's, for information only.
- **If an answer has no usable `Date` header, the run stops.** It does not fall back to this machine's clock.
- **Taken at the start.** A change made while a sync is running is stamped after the cursor that sync sets, so
  the next sync asks for it.

## 4. A delta sync, and the margin

With a cursor, in this order:

1. **The repository.** One request. GitHub's clock is noted from its answer.
2. **The changed issues.** The sync asks for the issues updated at or after the cursor **less a margin of 300
   seconds** (`since`), a page at a time until GitHub reports no further page. Pull requests come back in the
   same list. An item is a pull request when it carries a `pull_request` key, and those are left out.
3. **Their comments.** One request or more for each changed issue, and for no other issue.

The margin is there because GitHub's servers do not all learn of a change at the same instant. A change can be
stamped a little before the cursor and still not have been shown to the sync that set it. An issue returned
again because of the margin is matched to the one already held by its node ID, so nothing is held twice. The
output says when an issue was fetched and found the same.

The output gives the issues fetched, each as NEW or CHANGED with the fields that changed, how many were not
fetched, and the counts of new, changed and unchanged.

The first sync has no cursor, so it reads every issue.

## 5. All or nothing

Everything in section 4 is held in memory. If any request fails, the run stops and writes nothing: the issues,
the cursor and the state description are exactly as the last successful sync left them. The output says where
the cursor is. The next sync asks from the same cursor again and fetches every issue the failed one would have.

Only when every changed issue has been fetched are the files written: `issues.md`, then `state.json`, which
holds the cursor, then the state description.

If GitHub rate-limits the run it waits as GitHub asks, at most three times for one request and at most 15
seconds each, and after that stops with nothing written.

Exit codes: 0 synchronized, or verified the same. 1 stopped, nothing written. 2 incomplete because of a rate
limit, nothing written. 3 `--verify` found a difference.

## 6. What is written

In the output folder, by default `participant/context/github/delta/`:

| File | What it is |
|---|---|
| `issues.md` | The issues: open, closed, and no longer in the repository. Generated. |
| `state.json` | The sync's memory: the cursor, and what is held of each issue. Generated. |
| `sync-state.md` | The cursor and the last sync in words. Generated. With the default folder it is written one level up, as `participant/context/github/sync-state.md`. |
| `notes/<node ID>.md` | **Yours.** The sync never writes here. See section 7. |

Of an issue it keeps: number, node ID, title, state, state reason, author, assignees, labels, milestone, and
the created, updated and closed times. Of a comment it keeps: id, author, and the created and edited times.
Bodies and comment text are not kept.

One folder holds one repository from one source. A live run must be given `--out`, a folder outside this
repository.

## 7. Your notes

Write your analysis of an issue in `notes/<node ID>.md`. `issues.md` shows which issues have one, also after
an issue has gone from the repository. The sync opens notes files for reading only, to take their SHA-256, and
prints each file's checksum before and after every run. Its one function that writes files refuses any path in
the notes folder. Note text is never copied anywhere.

## 8. A full read, the digest, and `--verify`

Every sync prints a digest: a SHA-256 of what is held about the issues in the repository, and nothing about
when it was synced. Two local copies with the same digest hold the same repository.

- `--full` reads every issue again, ignoring the cursor, and folds it into the same folder.
- `--verify` reads every issue into memory, compares it with the local copy, names each issue that differs,
  and exits 3 if any does. It writes nothing and does not move the cursor.

A full read into an empty folder should print the same digest the deltas have reached. If it does not, a delta
missed something.

## 9. Deleted and transferred issues

GitHub does not return a deleted or transferred issue as changed, so a delta cannot see either. `--verify`
shows the difference. `--full` looks each missing issue up and flags it as deleted, transferred (with where
to) or not found, with the state it was last in. Nothing is removed locally, and its notes stay.

## 10. How stale

Every delta says how long ago the cursor is and says STALE when that is more than 24 hours (`--stale-hours N`
changes that). `--status` says the same without contacting anything. This one figure does use this machine's
clock, and says so.

## 11. Issue text is other people's writing

Titles are written into `issues.md` on one line, with the characters that could break a table or start a link
replaced. Bodies and comment text are not kept at all. Nothing in any of it is acted on. The screen output
shows ids, numbers, counts and times, never a title.

## 12. Tests

    python3 -m unittest discover -s participant/skills/github-delta-sync/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 13. What it does not do

- It does not change anything in GitHub.
- It does not keep bodies, comment text or timelines. The `github-read-assigned` skill does.
- It cannot catch, in a delta, a change that GitHub stamps more than 300 seconds before the cursor and shows
  later than that. Only `--verify` or `--full` finds it.
- It cannot see a deleted or transferred issue in a delta. See section 9.
- It syncs one repository for each folder.
- It does not remove anything locally, ever.

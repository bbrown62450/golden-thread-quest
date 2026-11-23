# GitHub: keep an issue's comments and material events

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill keeps a local copy of one GitHub issue's comments and of the timeline events that matter, and keeps
that copy in step each time it runs.

Its rule: **everything is keyed by the identifier GitHub gives it, never by its text.** That is what lets the
sync run forever without piling up copies.

It only reads GitHub. Every request is a GET. It runs no command, and it never reads a comment for meaning.

    python3 participant/skills/github-read-comments-events/sync.py --source live --repo OWNER/NAME --issue N --out FOLDER
    python3 participant/skills/github-read-comments-events/sync.py --source fake [--fake-step 1|2] [--out FOLDER] [--markdown FILE]
    python3 participant/skills/github-read-comments-events/sync.py --status [--out FOLDER]
    python3 participant/skills/github-read-comments-events/sync.py --write-rules FILE

`--source fake` uses the made-up GitHub in `fake_github.py`. The skill uses the Python standard library only.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`, set in your own terminal with `read -s` and then
`export`. The narrowest token that works is a fine-grained one, on the one repository, with **Issues:
read-only** and **Metadata: read-only**. Unset the variable afterwards.

## 3. What it reads

For one issue, three things, and a fourth only when needed:

1. the issue, to check it is the same issue as before, by its node ID;
2. its comments, page after page;
3. its timeline, page after page;
4. for each comment it holds that is missing from the list: that one comment, by its id.

Everything is read before anything is written. If any part cannot be read, nothing is written. **A comment
that could not be read is never taken for a comment that was deleted.**

## 4. What it writes

In the `--out` folder: `comments.md`, the copy a person reads, and `state.json`, the sync's memory. `--markdown`
puts the Markdown file somewhere else. It never writes in the `notes/` folder beside them: that is for a
person's own notes, and each sync prints the checksum of every notes file before and after.

One folder holds one issue.

## 5. Comments

Each comment is kept under its **node ID**, which GitHub never changes.

| On GitHub | In the local copy |
|---|---|
| nothing changed | nothing changes. The file is not written again |
| a comment was **added** | it is added once |
| a comment was **edited** | the same entry is updated in place. Its earlier text is kept under it, as "Earlier version 1", with the time it was found replaced |
| a comment was **deleted** | it is **kept**, with its last text, and marked DELETED, with the sync that found it missing |

A deletion is confirmed before it is flagged: the sync asks GitHub for that one comment by its id. Only a clear
"not found" flags it. If GitHub still returns the comment, the list was wrong, and the sync stops.

Two comments with the same text stay two comments. A comment's text is kept word for word.

**The local copy can hold text GitHub no longer shows**: the earlier versions of edited comments, and deleted
comments. The file says so at its top. Treat it as more sensitive than the issue.

## 6. Timeline events

The rules are in `participant/context/github/event-rules.md`, which is written out from the tables in
`sync.py`, so the two cannot disagree.

- **Material** events are recorded: label, assignment, milestone, state, title, transfer, links from other
  issues and pull requests, locking, and the deletion of a comment.
- **Noise** is not recorded: subscriptions, mentions, pins, commit references. Each sync counts it, by kind, in
  its output.
- An event of **a kind the rules do not name** is kept and marked UNCLASSIFIED, and named in the output.
- The timeline also lists each comment. Those entries are not recorded as events.

Each event is kept under GitHub's id for it. A cross-reference has no id on GitHub, so it is keyed by the thing
that points here and the moment it did. An event is added once. If GitHub stops listing an event, it is kept
and marked, not removed.

For each event the file shows when it happened, when a sync first saw it, and the delay between the two.

## 7. Running it again

The Markdown file holds no time of the last sync. It changes only when something changed on GitHub, so a second
sync of unchanged data leaves it byte for byte the same. The time of the last sync is in `state.json`, and
`--status` prints it.

## 8. Other people's text

Comment text, labels, titles and logins are other people's words. Comment text is kept between marker lines
that carry the start of its own checksum. Labels and titles are written as JSON and escaped, so they cannot
break the table. The sync prints ids, counts and times, and never a comment's text.

Exit codes: 0 synchronized. 1 stopped, nothing written. 2 rate-limited, nothing written.

## 9. Tests

    python3 -m unittest discover -s participant/skills/github-read-comments-events/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 10. What it does not do, and its limits

- **It knows only the versions it saw.** A comment edited twice between two syncs loses the version in between.
  A comment added and deleted between two syncs is never seen at all.
- **It does not know who edited a comment.** GitHub's ordinary interface gives the time of the last change, not
  the editor.
- **It does not know who deleted a comment, or when,** unless GitHub lists an event for it. It knows the sync
  at which the comment was found missing.
- It cannot tell a comment that was deleted from one that was hidden from this connection, if GitHub answers
  "not found" for both.
- It does not read review comments on pull requests, or reactions.
- It does not change anything on GitHub.

# PROOF: Preserve Comments and Material Timeline Events

Quest `github-read-comments-events`, attempt `github-attempt-010`.

## How this was made

The skill, its tests, the made-up GitHub, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in three decisions: build
and record against a made-up GitHub, then run for real on the sandbox and hand in a masked copy of the real
file beside the made-up one; which timeline events are material and which are noise; and that an edited
comment keeps its earlier text and a deleted comment is kept with its last text. The participant made the
token, ran the four real syncs in their own terminal, and edited, added and deleted the real comments by hand.
The assistant never saw the token and sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub. **not assessed** means nobody checked it.

## Approach

One script, `participant/skills/github-read-comments-events/sync.py`. For one issue it reads the issue, its
comments and its timeline, every request a GET, and keeps two files: `comments.md`, which a person reads, and
`state.json`, the sync's memory.

The rule is the quest's hint: **match on the identifier, never on the text.**

- A comment is kept under its **node ID**. A sync looks each comment up by that key. If the key is new, the
  comment is added. If the key is held and the text differs, the same entry is updated, and the old text moves
  under it as "Earlier version N". If the key is held and GitHub no longer lists it, the sync asks GitHub for
  that one comment by its id. Only a 404 flags it DELETED. It is never removed.
- An event is kept under GitHub's id for it. A cross-reference has no id on GitHub, so its key is the node ID
  of the thing that points here plus the moment it did.
- Everything is read before anything is written. If any request fails, nothing is written, so **a comment
  that could not be read is never taken for a deleted one.**
- The Markdown file holds no "last synced" time. It changes only when GitHub changed, which is what makes a
  second sync leave it byte for byte the same.
- The sync has no code that writes in the `notes/` folder, refuses if told to, and prints each notes file's
  checksum before and after.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each comment and event is keyed by its GitHub identifier | recorded, tested, observed | `comments-sample.md`: each heading and "key" line. `sync-twice.txt` part 1. Tests: two comments with the same text stay two. Real run: four comments and three events under node IDs, one cross-reference under its made key |
| 2 | A second sync of unchanged data adds nothing | recorded, tested, observed | `sync-twice.txt` parts 2 and 4: 0 new, and the file "was not written again". `live-runs.txt` syncs 2 and 4: the same bytes and SHA-256 |
| 3 | An edited comment is updated in place | recorded, tested, observed | `sync-twice.txt` part 3. `live-runs.txt` sync 3: "Updated in place, under the same node ID". The count of comments held went up by one, for the new comment only |
| 4 | A new comment is added once | recorded, tested, observed | `sync-twice.txt` parts 3 and 4. `live-runs.txt` syncs 3 and 4: added in sync 3, unchanged in sync 4 |
| 5 | Only events the rules call material are recorded | recorded, tested, observed in part | `sync-twice.txt` part 5: 6 noise entries read, none recorded, each counted by kind. **Real GitHub's timeline held no noise**, so on real data this is observed only as "the four material events were kept". **Exception:** a kind the rules do not name is kept, marked UNCLASSIFIED. See below |
| 6 | A local notes file is unchanged by the sync | recorded, tested, observed | `notes-intact.txt`: the same checksum before and after each of 4 syncs, and a refused attempt to write there. `live-runs.txt`: the same SHA-256 in all four syncs |
| 7 | A deleted comment is flagged, not silently removed | recorded, tested, observed | `sync-twice.txt` part 3. `live-runs.txt` sync 3: "FLAGGED, not removed: it is still held, with its last text", after a 404. In sync 4 it is still held: 4 held, 3 on GitHub |

### One event I chose to ignore: `subscribed`

Criterion 5 says only material events are recorded, so something has to be left out, and the rules have to say
why. The made-up timeline has two `subscribed` entries. GitHub writes one whenever a person starts getting
emails about an issue, which happens by itself when they comment or are mentioned.

It is ignored because **nothing about the issue changed**: not its state, its labels, its owner, its due date,
its title or what it is tied to. It says who gets email. It also repeats what is already held: the person
subscribed because they commented, and the comment is kept (criterion 1). Recording it would fill the file
with lines nobody acts on, which is the scenario's "nine copies" problem in another form.

Ignored does not mean hidden. Each sync counts the noise by kind in its output ("subscribed 2"), so a reader
can see what was passed over. `sync-twice.txt` part 5 checks that none of the 6 noise entries read over the four syncs is in the file.

The same reasoning, written per kind, is in `participant/context/github/event-rules.md`.

### Criterion 5 and a kind nobody listed

Read to the letter, criterion 5 says an event of a kind the rules do not name should not be recorded. The
participant decided otherwise: such an event is **kept and marked UNCLASSIFIED**, and named in the output.
Dropping it would be a guess that it does not matter, and GitHub adds new kinds. The rules document says this
in its own section, so in that sense the rules do call for it. The made-up timeline has one such event,
`x_fixture_sparkled`. A reviewer who reads criterion 5 strictly should count it as met with this exception.

## What the real runs showed

Four syncs of issue 1 of the participant's private sandbox, in `logs/live-runs.txt`, masked.

- Sync 1: 3 comments and 4 material events. Sync 2: nothing new, file not written again.
- Then, by hand on GitHub's web page: one comment edited, one added, one deleted.
- Sync 3: "1 new, 1 edited, 1 unchanged, 1 found deleted". Sync 4: nothing new, file not written again.
- **GitHub listed no event for the deleted comment.** The timeline held the same 4 events before and after.
  The assistant's made-up GitHub lists a `comment_deleted` event, and that was an assumption real GitHub did
  not bear out for this case. The skill does not rely on it: it found the deletion from the missing key and
  the 404, and a deletion with no event is one of the tests.
- **The real timeline held no noise at all:** no `subscribed`, no `mentioned`. Either GitHub's timeline for
  this connection leaves them out, or this issue has none. Only what was seen is claimed.
- A cross-reference has no id on real GitHub, as expected, and was keyed by its source and time.
- The skill did not need changing after the real runs.

The quest says to make no change on GitHub, and also asks for a record "after a comment was edited, one was
added and one was deleted on GitHub". The skill made no change: 13 requests, every one a GET. The three
changes were made by the participant, by hand, to made-up comments on their own sandbox issue.

## Artifacts

| Required item | File |
|---|---|
| The comments file | `participant/context/github/comments-sample.md` |
| The event rules | `participant/context/github/event-rules.md` |
| The sync record | `logs/sync-twice.txt`, 23 checks |
| The notes record | `logs/notes-intact.txt`, 17 checks |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the four real syncs, masked), `logs/tests.txt` (54 tests),
`logs/planted-bugs.txt` (23 planted bugs), `scripts/record_evidence.py`, `scripts/planted_bugs.py` and
`scripts/mask_real_run.py`. The skill is `participant/skills/github-read-comments-events/`: `SKILL.md`,
`sync.py`, `fake_github.py`, `tests/test_sync.py`.

`comments-sample.md`, the rules and the two required logs come from the made-up GitHub. Its repository,
people, issue and comments are invented. `participant/context/github/comments-sample-real-masked.md` is the
real file after sync 4, masked, under a name that says so. `participant/context/github/comments-events/` holds
the made-up sync's memory and its notes file.

## Stretch goals

- **Show the delay between an event and its sync:** done. Each event shows when it happened, when a sync first
  saw it, and the delay. On the real issue: 2.1 days for the assignment, about 8 hours for the labels.
- **Record who edited a comment:** not done. GitHub's ordinary interface gives the time of the last change and
  not the editor. The file records that an edit was seen, when, and the text before it.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-read-comments-events/tests -v
    python3 participant/evidence/github-read-comments-events/github-attempt-010/scripts/record_evidence.py
    python3 participant/evidence/github-read-comments-events/github-attempt-010/scripts/planted_bugs.py

None of these contacts GitHub. The second writes `comments-sample.md` and the two logs again. The third
changes `sync.py` while it runs and restores it. `mask_real_run.py` can be run only by the participant,
because only their computer has the real files.

## What was tested

| What | Result |
|---|---|
| Automated tests | 54, all pass (`logs/tests.txt`) |
| Planted bugs | 23 put into `sync.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 23 and 17, all pass |
| Real runs | 4, all exit code 0. Two wrote the file, two found it unchanged |

Tested against the made-up GitHub only: 250 comments over three pages; a failed or rate-limited request in the
middle of a sync, with nothing written; a comment missing from the list that GitHub still returns by id, which
stops the sync; a pull request; an issue with a different node ID in the same folder; labels and titles made
to break the table; a comment holding an instruction and a comment shaped like the file's own markers.

Faults found while building:

- In the skill: event keys were escaped inside backticks, so the key shown was not the key held. A sentence in
  the generated rules document was garbled. A message said "1 minutes". All fixed.
- A constant's name tripped the app's secret scan. It was renamed. The scan was not changed.
- In the assistant's tests: several were wrong on first run and were corrected. One helper left files open,
  which put warnings holding a folder path into the test log. It now closes them. The planted bugs then checked
  the tests: each of the 23 is caught.

## What could not be done, and limitations

- **Only the versions a sync saw are kept.** A comment edited twice between two syncs loses the version in
  between. A comment added and deleted between two syncs is never seen.
- **Who deleted a comment, and when: not known.** Real GitHub listed no event for it. The file records the
  sync that found it missing, which is a latest time, not the time.
- **Who edited a comment: not known.** See the stretch goals.
- **Deleted is not told apart from hidden.** If GitHub answers 404 for a comment this token may no longer see,
  the sync flags it DELETED.
- **The local file holds text GitHub no longer shows.** That is the point of criterion 7, and it is also a
  risk: a comment may have been deleted because it held something private. The file says so at its top.
  Nothing removes such text. A person must decide.
- **Noise on real GitHub: not assessed.** None was returned.
- **On real GitHub, not assessed:** more than one page, a rate limit, a rejected token, an unclassified kind, a
  closed or renamed issue, a comment by another person, and comments that are minimized or hidden.
- **An event that GitHub stops listing** is kept and marked. Tested against the made-up GitHub only.
- Review comments on pull requests and reactions are not read.
- The skill, the made-up GitHub and the tests were written by the same assistant and can share a blind spot.
  The missing deletion event is one that the real run found.

## Reflection

*What does a deleted comment mean for an audit?*

It means the system I am auditing cannot be my only witness. I deleted one comment on my sandbox issue, and
afterwards GitHub showed no sign of it. The comment was gone from the list and there was no event in the
timeline to say one had been removed. If my local copy had simply mirrored GitHub, the audit would say that
comment never existed, and it would be wrong with complete confidence.

So for an audit, a deletion is itself a fact worth keeping. My copy now says three things GitHub does not: that
the comment existed, what it last said, and which sync found it missing. That is why the criterion says
"flagged, not silently removed". Silent removal makes the record agree with the present and lie about the past.

What surprised me is how little I can honestly claim even so. I know the comment was gone by 20:39. I do not
know when it went, or who removed it. I only know the last text my sync saw, not every text it ever had. An
auditor reading my file has to be told those limits, or they will read "deleted at 20:39" where the truth is
"found missing at 20:39".

The other side took me longer to see. People usually delete a comment for a reason, and sometimes the reason
is that it held a password or something private. By keeping it, I now hold the very thing someone tried to
remove. So keeping deleted comments makes the copy better for an audit and more dangerous to share. The file
says that at its top, and I would not hand a real one to anybody without reading it first.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, read-only for issues, and expires in 7 days.
- The real files were written to a scratch folder outside the repository and are not handed in. The two
  masked copies replace the owner's login, every node ID and every numeric id of a comment. The masking script
  stops if one is left.
- Every comment in the masked real file is made-up text the participant typed for this quest, including the
  deleted one.
- The skill prints ids, counts, times and checksums. It never prints a comment's text. Tested.
- Everything else comes from the made-up GitHub. Its logins, such as `robin-fixture`, are invented. One of its
  comments mentions a password on a wiki, in words only, to test that deleted text is kept and labelled. No
  password is written anywhere.

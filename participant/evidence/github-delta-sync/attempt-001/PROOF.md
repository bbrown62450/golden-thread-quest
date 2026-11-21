# PROOF: Update Changed Issues While Preserving Analysis

Quest `github-delta-sync`, attempt `github-attempt-002`.

## How this was made

The skill, its tests, the made-up GitHub and this document were written by an AI assistant (Claude) at the
participant's direction. The participant chose the design in four decisions: build against a made-up GitHub
and run for real on a sandbox; take the cursor from GitHub's own clock at the start of a sync, with a margin;
cover every issue of one repository; and make a sync all or nothing, with the cursor written last. The
participant made the read-only token and ran the three real runs in their own terminal. The assistant never
saw the token and sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub in the real runs. **not assessed** means nobody checked it.

## Approach

A new skill, `participant/skills/github-delta-sync/`, beside the approved `github-read-assigned` skill, which
is not changed. One run does this, in order:

1. Ask GitHub for the repository. Note GitHub's clock from the `Date` header of that answer.
2. Ask for the issues updated at or after the cursor less a margin of 300 seconds. Leave out pull requests.
3. Fetch the comments of those issues, and of no others.
4. Only if every request was answered: write `issues.md`, then `state.json` with the new cursor, then
   `sync-state.md`. The new cursor is the time noted in step 1.

The state description the quest asks for is `participant/context/github/sync-state.md`. The sync writes it.

## How clock differences are handled

Three clocks could disagree, and each is handled differently.

**This machine's clock against GitHub's (criteria 2 and 3).** This machine's clock is never used for the
cursor. The cursor is GitHub's own time, read from the `Date` header of GitHub's first answer. So a clock here
that is fast cannot put the cursor ahead of GitHub's time and skip changes, and a clock that is slow cannot
either. Recorded in part 4 of `logs/delta-run.txt`: the same two syncs with this machine's clock 7 minutes
fast, and again 2 days slow, give the same cursor, ask GitHub from the same time, fetch the same 4 issues and
reach the same digest. Tested: one test makes any read of the local clock for the cursor an error. If an answer
has no usable `Date` header the run stops and does not fall back to the local clock: recorded in part 5.
Observed: on the real runs the two clocks agreed to the second, so a real difference was not observed.

**The start of a sync against its end (criterion 2).** The cursor is the time at the start of the sync, taken
before any issue is read, not the time it finished and not the newest "updated" time it saw. A change made
while a sync is running is stamped after that sync's cursor, so the next sync asks for it. Tested, with a
change made to an issue between the listing and the fetches.

**GitHub's servers against each other (criteria 1 and 4).** The `Date` header and the "updated" stamp on an
issue need not come from the same machine, and a change is not shown to every request at the same instant. So a
change can be stamped a little before the cursor and still not have been shown to the sync that set it. Each
delta therefore asks from the cursor **less a margin of 300 seconds**, as the quest's hint says. An issue
returned twice because of the margin is matched to the one already held by its node ID, so nothing is held
twice. Recorded in `logs/failed-sync-run.txt`: issue 11's change is stamped two minutes before the cursor and
shown late. With the margin it is fetched. Part 4 runs the same step with no margin: it is missed, and
`--verify` names it. Whether real GitHub ever shows a change later than its stamp, and by how much, is **not
assessed**. 300 seconds is the assistant's choice, not a measured figure.

The cost of the margin is small and is said out loud: a few issues may be fetched again and found the same,
and the output counts them.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Only issues changed since the last successful sync are fetched | recorded, tested, observed | `delta-run.txt` part 2: the script works out the changed issues from the made-up GitHub itself, and the sync fetched exactly those 4 of 13. Tests `OnlyTheChanged`. Real run 2: 1 of 2 fetched |
| 2 | The cursor advances only after the whole sync succeeds | recorded, tested, observed | `delta-run.txt` part 2; `failed-sync-run.txt` parts 1 and 3; tests `TheCursor`, `AFailedSync` |
| 3 | A failed sync leaves the cursor where it was | recorded, tested | `failed-sync-run.txt` part 1: the cursor and every generated file are byte for byte as before. A failure was not observed on real GitHub, where one cannot be forced |
| 4 | The next sync recovers what the failed one missed | recorded, tested | `failed-sync-run.txt` part 3: all 7 fetched, and the digest equals that of three syncs with no failure |
| 5 | The run reports changed, unchanged and new counts | recorded, tested, observed | every run. `delta-run.txt` part 2: "1 new, 3 changed, 9 unchanged". Tests `Counts` |
| 6 | Local analysis files are byte-identical after every sync | recorded, tested | `analysis-intact.txt` parts 1 and 5: three notes files keep their SHA-256 through 9 runs. Tests `Notes`. No notes were made for the real runs |
| 7 | A full resync reaches the same local state as the deltas | recorded, tested, observed | `analysis-intact.txt` parts 2 and 4; tests `FullAndDeltas`. Real runs 2 and 3 printed the same digest |

## Artifacts

| Required item | File |
|---|---|
| The sync state file | `participant/context/github/sync-state.md` |
| The delta run | `logs/delta-run.txt`, 19 checks |
| The failed run | `logs/failed-sync-run.txt`, 15 checks |
| Analysis intact | `logs/analysis-intact.txt`, 17 checks |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the three real runs, masked), `logs/tests.txt` (82 tests),
`logs/planted-bugs.txt` (34 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. The
skill is `participant/skills/github-delta-sync/`: `SKILL.md`, `sync.py`, `fake_github.py`, `tests/test_sync.py`.

The three logs are one story in one folder, `participant/context/github/delta/`: a first sync, a delta, the
same delta again, a delta that fails, the recovery, a last delta, and a full read. That folder and the state
file are as the last of those left them. Everything in them comes from the made-up GitHub.

## The failed run

GitHub is made to fail when asked for the comments of issue 8, the fourth of 7 changed issues. The run stops
with exit code 1 and says "Nothing was written. The cursor is where it was". The recording script takes the
SHA-256 of `issues.md`, `state.json` and `sync-state.md` before and after, and they are the same. The next
sync asks from the same time and fetches all 7: the three the failed run had already fetched, the one it
failed on, and the three it never reached.

## Analysis intact

"Local analysis" is the participant's own notes on an issue, in `notes/<node ID>.md`. The sync's one writing
function refuses any path in that folder, and reads the files only to take their checksums. The recording
script takes the checksums itself before the first sync and after the last. Two of the three notes belong to
issues that are later deleted and transferred. They are still there, unchanged, and `issues.md` still points
to them.

## Stretch goals

- **Detect issues transferred or deleted:** done. A delta cannot see either, because GitHub does not return
  them as changed. `--full` looks each missing issue up and flags it, with the state it was last in. Recorded
  in `analysis-intact.txt` parts 3 and 4. Tested against the made-up GitHub only.
- **Compare delta and full results automatically:** done, as `--verify`. It exits 3 and names each issue that
  differs. It writes nothing and does not move the cursor.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-delta-sync/tests -v
    python3 participant/evidence/github-delta-sync/github-attempt-002/scripts/record_evidence.py
    python3 participant/evidence/github-delta-sync/github-attempt-002/scripts/planted_bugs.py

None of these contacts GitHub. The second rewrites the three logs and the generated files. The third changes
`sync.py` while it runs and restores it. One line of `failed-sync-run.txt`, from `--status`, gives the real
time of the recording and so differs from run to run.

## What was tested

| What | Result |
|---|---|
| Automated tests | 82, all pass (`logs/tests.txt`) |
| Planted bugs | 34 put into `sync.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 19, 15 and 17, all pass |
| Real runs | 3, all exit 0, every request a GET (`logs/live-runs.txt`) |

The planted bugs include the quest's own scenario: the cursor saved as soon as the changed issues are listed,
before they are fetched. Eleven tests fail with it.

## What could not be done, and limitations

- **A failure partway on real GitHub: not assessed.** It cannot be forced there. Criteria 3 and 4 rest on the
  made-up GitHub.
- **A real clock difference: not assessed.** The real clocks agreed. Wrong clocks were tried against the
  made-up GitHub only.
- **A real late-arriving change: not assessed.** See the margin, above.
- **Deleted and transferred issues on real GitHub: not assessed.**
- A change that real GitHub stamps more than 300 seconds before the cursor and shows later than that would be
  missed by a delta. Only `--verify` or `--full` would find it.
- Whether every kind of change to an issue moves its "updated" time on real GitHub is not assessed. A new
  comment did, in real run 2. A change that did not would be missed by a delta and found by `--verify`.
- The sync keeps fields and comment times, not bodies or comment text. It is a smaller copy than the one the
  `github-read-assigned` skill makes.
- The made-up GitHub's answers are shaped from the assistant's knowledge of GitHub's API.

One thing went wrong on the way. The first real command was run in a terminal where the token had been set
but not exported. The sync stopped before contacting GitHub and wrote nothing, and the run was repeated after
`export`.

## Reflection

*What is the cost of a cursor that moves too early compared with too late?*

They are not the same kind of cost. A cursor that moves too late costs work: the next sync asks for a stretch
of time it has already covered, fetches some issues again and finds them the same. I can see that cost. The
output counts it, and it is gone by the next run.

A cursor that moves too early costs data, and it does not tell me. The changes it skipped are never asked for
again, every later sync reports success, and the local copy is wrong from then on. Nothing in a delta can
notice, because a delta only looks forward from the cursor. That is why I needed a second kind of check, the
full read with a digest, that does not depend on the cursor at all.

So every choice here leans late on purpose. The cursor is the time the sync started, not the time it
finished. It is written last, after the issues. A failure leaves it alone. And each delta asks from five
minutes before it. Each of those wastes a little, and node IDs make the waste harmless. What surprised me is
that "too early" has several causes that look nothing alike: a failure partway, a fast local clock, a change
made mid-sync, a server that learns of a change late. They all end the same way, with a cursor ahead of what
was actually read.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, read-only, and expires in 7 days.
- The real runs wrote to scratch folders outside the repository. Nothing from them is committed.
  `logs/live-runs.txt` holds only what the sync printed, with the repository's owner and id masked. That
  output never includes a title.
- Everything else in this attempt comes from the made-up GitHub. Its logins, such as `robin-fixture`, are
  invented.

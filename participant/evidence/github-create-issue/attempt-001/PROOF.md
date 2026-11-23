# PROOF: Create and Reconcile an Approved Issue

Quest `github-create-issue`, attempt `github-attempt-009`.

## How this was made

The workflow, its tests, the made-up GitHub, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in two decisions: build
against a made-up GitHub and create one real issue themselves; and write the intent down before sending, treat
a lost answer as an unknown outcome, and never send a create twice. The participant made the token, read the
real preview, typed the real confirmation, and ran the rerun and the verification in their own terminal. The
assistant never saw the token and sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub. **not assessed** means nobody checked it.

## Approach

One script, `participant/skills/github-create-issue/create.py`, with four commands.

- `preview` runs the `github-create-issue-preview` skill, unchanged. It only reads.
- `confirm` creates the issue of one preview. It is the only command with a connection that can write, and
  that connection can send one create, to one repository.
- `verify` reads the linked issue back and compares it. It only reads.
- `reconcile` settles a create whose outcome is not known. It only reads GitHub.

One local file, the link, ties a draft to its issue. Its status says where things stand: creating, unknown,
linked or not-created.

## How I verified the issue equals the preview (criterion 1)

Four checks, each from a different side.

1. **The bytes sent are the bytes previewed.** The preview built the payload once and saved it with the
   SHA-256 of its bytes. `confirm` loads that record, writes the bytes out again with the preview skill's own
   function, checks the SHA-256, and sends them. It builds no payload. A test reads the source and fails if it
   ever does. The made-up GitHub keeps the exact bytes it receives, and the recording script compares them with
   the bytes printed in `logs/preview.txt`: the same, byte for byte (`logs/confirmation.txt` part 1).
2. **The issue is read back and compared** (the hint). After the create, the workflow reads the issue from
   GitHub by its number, checks that its node ID is the one GitHub returned, and compares five fields with the
   payload: title, body, labels, assignees, milestone. The body is compared character for character. A value
   of another kind, such as an empty list where there was none, is a difference.
3. **The recording script compares for itself.** It opens the made-up GitHub's file and compares the issue it
   holds with the payload, without using the workflow's comparison.
4. **A difference is not hidden.** If the issue is not what the preview showed, the run ends NEEDS LOOKING with
   exit code 3 and names the fields. It changes nothing to "fix" it. Tested with a made-up GitHub that drops
   the labels, as GitHub does when the account may not triage.

**Observed.** On real GitHub the participant created issue number 4. The 455 bytes sent had the SHA-256 the
preview printed, which is also the SHA-256 the last quest's real preview printed for the same draft. The issue
was read back and all five fields were the same. `verify` found the same again afterwards.

This closes what the last quest left open: that a write really sends the previewed bytes.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The issue created matches the previewed payload field for field | recorded, tested, observed | See above. Tests `SameAsThePreview`; real run 2 |
| 2 | The returned number and identifier are written to the local file | recorded, tested, observed | `participant/context/github/new-issue/linked.md`; `confirmation.txt` part 1; tests `Recorded`; real run 2 |
| 3 | The local file is matched to the GitHub issue by identifier afterwards | recorded, tested, observed | `rerun.txt` part 4; tests `MatchedByIdentifier`: the same number with another node ID is "not the same issue"; real run 4 |
| 4 | A preview shows the repository and the exact changes, and nothing is written before the human confirms | recorded, tested, observed | `preview.txt`; tests `PreviewFirst`; real run 1 |
| 5 | The preview records the permission check and the duplicate check, or states where GitHub cannot perform one | recorded, tested, observed | `preview.txt` part 2; real run 1. It is the preview skill's output, unchanged |
| 6 | Writes only to a repository on an explicit sandbox allowlist | recorded, tested, observed in part | `confirmation.txt` part 5: refused with no request sent; tests `Allowlist`. On real GitHub only the allowed case was seen |
| 7 | The confirmation is tied to a fingerprint, refused when missing or when the change differs, and expires | recorded, tested, observed in part | `confirmation.txt` parts 1 to 4; tests `Confirmation`; real run 2. The refusals were not tried on real GitHub |
| 8 | A result record holds the repository, number, identifier, timestamp and confirmer | recorded, tested, observed | `participant/context/github/results/create-issue.md`; tests `ResultRecord`; real run 2 |
| 9 | Running it again creates no duplicate, or the quest states the limit where GitHub cannot prevent it | recorded, tested, observed for the plain rerun | `rerun.txt`; tests `Rerun`; real run 3. The limit is stated below |

### Criterion 2: recorded before anything else

The order matters, so it is tested. The number and node ID are written to the local link **before** the issue
is read back. A test stops at the read-back request and finds the number already on disk.

### Criterion 7: "a change that differs from the preview"

The preview records the SHA-256 of the draft. `confirm` reads the draft again. If one character of it has
changed since the preview, the confirmation is refused, before any request. A confirmation covers exactly what
its preview showed.

`confirm` also checks things a preview cannot promise will last: that the payload's labels and milestone still
exist, and that nobody has filed an issue with exactly this title since the preview.

### Criterion 9: the limit, stated

**GitHub cannot prevent a repeat.** It creates an issue every time it is asked, and has no way to be told "only
if I have not sent this before". Two things stand in for that:

- **The local link.** Before the create is sent, the link is written with status "creating". A draft whose
  link says linked, creating or unknown is refused by `preview` and by `confirm`. Observed in real run 3.
- **An unknown outcome is never guessed.** If no usable answer comes back, the link says "unknown" and nothing
  more is sent until `reconcile` has looked on GitHub. Recorded in `rerun.txt` parts 6 and 7: the made-up
  GitHub creates the issue and loses the answer; the workflow sends one write in all; `reconcile` finds the
  issue and links it.

**How a person would notice a repeat that got through:** two issues with the same title and body by the same
account. `reconcile` reports "MORE THAN ONE" and links nothing until a person names the one to keep.

**What is left open.** If the local link file is deleted, the first protection is gone. What remains is the
check for an issue with the same title created since the preview, which covers 15 minutes at most.

## Artifacts

| Required item | File |
|---|---|
| The local link | `participant/context/github/new-issue/linked.md` |
| The preview | `logs/preview.txt`, 10 checks |
| The confirmation and four refusals | `logs/confirmation.txt`, 25 checks |
| The result record | `participant/context/github/results/create-issue.md` |
| The rerun | `logs/rerun.txt`, 20 checks |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the four real runs, masked), `logs/tests.txt` (55 tests),
`logs/planted-bugs.txt` (31 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. The
skill is `participant/skills/github-create-issue/`: `SKILL.md`, `create.py`, `fake_github.py`,
`tests/test_create.py`.

The draft is the one handed in for the last quest, `participant/context/github/new-issue/draft.md`, unchanged.
The local link, the result record and the three required logs come from the made-up GitHub, so that nothing
real is shared. In them the issue is number 108 of the made-up repository.

No run saved as evidence skipped the preview or the confirmation.

## The real runs

Four, in `logs/live-runs.txt`, on the participant's private sandbox.

1. The preview: READY. 12 requests, every one a GET. Newest issue number 3 before and after.
2. The participant's confirmation: one write, status 201, **issue number 4**. Recorded, read back, and the same
   as the preview in all five fields.
3. The same confirmation again: refused, "this draft is ALREADY the GitHub issue number 4". Nothing sent.
4. Verify: matched by node ID, and the same field for field. One GET.

The made-up GitHub matched the real one. The workflow was not changed after the real runs.

## Stretch goals

- **Handle a timeout where the creation may have happened:** done, as the main design. A timeout is an unknown
  outcome, never a failure, and is settled by `reconcile`. Recorded against the made-up GitHub. Not seen on
  real GitHub, where no answer was lost.
- **Apply labels in the same approved step:** done. The previewed payload carries the labels, the assignee and
  the milestone, and they go in the one request that creates the issue. Observed: issue 4 was created with its
  label and its assignee.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-create-issue/tests -v
    python3 participant/evidence/github-create-issue/github-attempt-009/scripts/record_evidence.py
    python3 participant/evidence/github-create-issue/github-attempt-009/scripts/planted_bugs.py

None of these contacts GitHub. The second writes the three logs, `linked.md` and the result record again. The
third changes `create.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| Automated tests | 55, all pass (`logs/tests.txt`) |
| Planted bugs | 31 put into `create.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 10, 25 and 20, all pass |
| Real runs | 4. One preview READY, one issue created, one refusal, one verification |

The planted bugs include the quest's scenario in two forms: writing nothing down before the create is sent
(bug G), and recording a lost answer as "not created", so that the next run makes a second issue (bug Z).

Two kinds of bug were deliberately **not** planted: removing the guards in the sender used on real GitHub. The
tests for those guards call that sender directly, and with a guard removed the test itself would have sent a
real request. The guards are tested as they stand.

Faults found while building:

- **In the assistant's tests, one:** it asked the wrong command for an error message.
- **In the recording script, one:** a check counted a phrase too loosely and failed on a correct run. The check
  was tightened.
- **A gap found while writing the planted bugs:** nothing tested the check that the saved payload's bytes match
  their checksum, because the check before it always caught the same case first. A test was added that gets
  past the first check, and the bug is now caught.
- None was found in the workflow itself by the tests or by the real runs.

## What could not be done, and limitations

- **A lost answer on real GitHub: not assessed.** The unknown-outcome path and `reconcile` were shown against
  the made-up GitHub only. It would mean breaking the connection at the right moment.
- **`reconcile` recognises an issue by its title, body, author and time,** not by a hidden mark. If the same
  account filed the same text twice within minutes for another reason, it would report more than one and ask.
- **GitHub's list may lag.** `reconcile` waits a minute before it believes "no such issue". That figure is the
  assistant's own.
- **Who confirmed cannot be verified.** The workflow records the name typed with `--confirmed-by`.
- **On real GitHub, not assessed:** the four refusals of criterion 7, a repository off the allowlist, a refusal
  by GitHub, a token that may not write, dropped labels, a milestone, and a change made between the preview
  and the write.
- **The real issue is still there.** Issue 4 in the sandbox was not closed or deleted. The workflow cannot do
  either.
- The made-up GitHub, the workflow and the tests were written by the same assistant and can share a blind spot.
  The real runs covered the main path only.

## Reflection

*What happens locally if the write succeeds but recording the number fails?*

The local link is left saying "creating", which means "a create was sent and I do not know how it ended". That
is the honest state, and it is on disk before the request goes out, so it survives whatever went wrong. From
then on every run for that draft refuses: `confirm` will not send again and `preview` will not start again.
The workflow also prints the number, loudly, with "WRITE THIS DOWN", because at that moment the screen is the
only place it exists on my side.

What I do next is run `reconcile`. It reads GitHub, finds the one issue with my title and body, and links it,
so the local file ends up the same as if the recording had worked. There is a test for exactly this: the disk
"fills up" after the create, nothing is sent twice, and `reconcile` puts it right.

What struck me is that the failure the question asks about and a lost answer are the same thing seen from my
side. In both, GitHub has the issue and I do not have its number. I had thought of them as two problems. They
needed one answer: write down that I am about to send, and afterwards never guess.

The part I had not seen coming is that "it failed" is the dangerous conclusion. If the workflow had recorded a
timeout as a failure, I would have run it again and made a second issue, and felt careful doing it. The
scenario's agent did not forget out of carelessness. It had nowhere to write "I do not know".

What still worries me is how much rests on one small file. If `linked.md` is deleted, the workflow has no
memory, and GitHub will not refuse the repeat.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, with Issues read and write and Contents
  read-only, and expires in 7 days. It should be deleted now that the quest is done, because it can write.
- The real draft, saved preview, local link and result record are in a scratch folder outside the repository
  and are not handed in. `logs/live-runs.txt` is a masked copy of what the runs printed: the owner's login, the
  issue's node ID, the repository's id and the name typed as confirmer are replaced.
- The one real change is a made-up bug report, issue 4, in the participant's own private sandbox.
- Everything else in this attempt comes from the made-up GitHub. Its logins, such as `robin-fixture`, its
  repositories, labels, milestones and issues are invented.

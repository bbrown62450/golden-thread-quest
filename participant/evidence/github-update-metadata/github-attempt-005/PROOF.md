# PROOF: Update Labels, Assignee, Milestone, and Project Fields

Quest `github-update-metadata`, attempt `github-attempt-005`.

## How this was made

The workflow, its tests, the made-up GitHub, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in four decisions: build
against a made-up GitHub and make one real write themselves; support labels, assignees and milestone and
refuse project fields; add and remove labels one at a time and never send a whole list; and treat a change to
any of the three fields as "moved". The participant made the token, read the real preview, typed the real
confirmation, and changed the issue by hand for the real stale case, all in their own terminal and browser.
The assistant never saw the token and sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub. **not assessed** means nobody checked it.

## Approach

One script, `participant/skills/github-update-metadata/update.py`, with two commands.

- `preview` reads the issue, works out each change, and shows old and new values and the exact requests. It
  has no way to write. A preview that is READY is saved and gets a fingerprint.
- `confirm` is given the same changes again, the fingerprint and a name. It makes every check again, sends
  the requests of the preview, reads the issue back and writes a result record.

## How a field that moved is detected (criterion 3)

1. **At preview time** the workflow reads the issue's labels, assignees and milestone. These three, sorted,
   are the "old values". They are shown to the person and saved inside the preview, under its fingerprint.
2. **At write time** `confirm` reads the same three from GitHub again, just before the first write.
3. **It compares the two.** If any label, any assignee or the milestone differs, it stops. It prints the
   preview's values beside the values now, names what moved ("labels: added "urgent""), writes nothing, and
   asks for a new preview. This is the hint: the value at write time against the old value in the preview.

Three choices inside that, each made on purpose:

- **All three fields are compared, whichever one is being changed.** The person was shown all three. If the
  milestone moved while they were approving a label, they approved a picture that is out of date. Recorded in
  `logs/stale-run.txt` part 5.
- **A new comment or an edited body does not stop it.** Those are not metadata and the preview never showed
  them. GitHub's "last updated" time is not used, because a comment changes it. Part 6.
- **What is compared is the saved old values, not a second look at the issue.** A bug that compared the issue
  with itself was planted, and seven tests failed.

The quest's scenario is prevented twice. The check stops the update (part 3: the maintainer's label "urgent"
is still on the issue, and nothing was written). And even without the check, the write could not remove it:
labels are added and removed one at a time, so a label the workflow was not asked about is in no request it
sends (criterion 2 and the first stretch goal).

**The limit of this.** The check and the write are separate requests. GitHub offers no way, as far as the
assistant knows, to make a label, assignee or milestone change conditional on the issue being unchanged. A
change made in that moment is not seen by the check. `logs/stale-run.txt` part 7 arranges exactly that: the
maintainer's label survives, the read-back finds a label the preview did not promise, and the run ends NEEDS
LOOKING with exit code 3. For a **milestone** the limit is worse: an issue has one, so a milestone someone set
in that moment would be replaced, and the read-back would match the preview and could not tell.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The preview shows the old and new value of each field | recorded, tested, observed | `preview.txt` part 2; tests `OldAndNew`; real runs 1 and 4. All three fields are shown, also one that stays the same |
| 2 | Only supported fields can be changed | recorded, tested | `supported-fields.md` run 1: six unsupported changes refused; tests `SupportedOnly`. Project fields are refused, by the participant's decision. Not tried on real GitHub |
| 3 | A field changed on GitHub after the preview stops the update | recorded, tested, observed | `stale-run.txt`; tests `Stale`; real run 5: the participant added a label by hand after the preview, and the confirmation was refused as STALE with nothing written |
| 4 | A preview shows the repository and the exact changes, and nothing is written before the human confirms | recorded, tested, observed | `preview.txt` parts 2 and 3: every request a GET, and both made-up repositories identical before and after; tests `PreviewWritesNothing`; real run 1 |
| 5 | The preview records the permission check and the duplicate check, or states where GitHub cannot perform one | recorded, tested, observed | `preview.txt` part 2; tests `Checks`; real runs 1 and 4. Two limits are stated in the preview itself. See below |
| 6 | Writes only to a repository on an explicit sandbox allowlist | recorded, tested, observed in part | `confirmation.txt` part 5: refused with no request of any kind sent; tests `Allowlist`. On real GitHub only the allowed case was seen |
| 7 | The confirmation is tied to a fingerprint, refused when missing or when the change differs, and expires | recorded, tested, observed in part | `confirmation.txt` parts 1 to 4; tests `Confirmation`; real run 2. The refusals were not tried on real GitHub |
| 8 | A result record holds the repository, number, identifier, timestamp and confirmer | recorded, tested, observed | `participant/context/github/results/update-metadata.md`; tests `ResultRecord`; real run 2 |
| 9 | Running it again makes no duplicate, repeated or conflicting change | recorded, tested, observed | `rerun.txt`; tests `Rerun`; real run 3: refused, 0 requests |

### Criterion 5: what GitHub cannot check

- **Permission.** The preview reports what GitHub says the **account** may do in the repository. GitHub does
  not report what a fine-grained **token** may do, as the verify-connection quest found. The preview says so,
  and says how it shows up: GitHub refuses the write with 403 and nothing changes. Recorded against the
  made-up GitHub (tests `WhenGitHubRefuses`). Not observed on real GitHub, where the token could write.
- **Duplicate.** For metadata a duplicate is a change that is already so. The preview compares each change
  with the issue and does not send one that is already so. GitHub itself does not refuse a repeated label,
  assignee or milestone: it accepts it and changes nothing. The preview states that. That GitHub behaves this
  way is the assistant's understanding, built into the made-up GitHub, and was not tried on real GitHub,
  because the workflow never sends a repeat.

## Artifacts

| Required item | File |
|---|---|
| The supported fields, with a refused run and a preview | `participant/context/github/update/supported-fields.md` |
| The stale run | `logs/stale-run.txt`, 16 checks |
| The preview | `logs/preview.txt`, 13 checks |
| The confirmation and four refusals | `logs/confirmation.txt`, 24 checks |
| The result record | `participant/context/github/results/update-metadata.md` |
| The rerun | `logs/rerun.txt`, 11 checks |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the five real runs, masked), `logs/tests.txt` (88 tests),
`logs/planted-bugs.txt` (46 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. The
skill is `participant/skills/github-update-metadata/`: `SKILL.md`, `update.py`, `fake_github.py`,
`tests/test_update.py`. The allowlist of the recorded runs is
`participant/context/github/update/sandbox-allowlist.json`.

The required logs, the supported-fields file and the handed-in result record come from the made-up GitHub, so
that nothing real is shared. The made-up GitHub keeps its repositories in one file, so that a preview and its
confirmation are two separate commands, as they are for a person. After each command the recording script
opens that file itself and checks what the repository holds and every request it received.

No run saved as evidence skipped the preview or the confirmation. Part 7 of `stale-run.txt` starts the
workflow inside the recording script, with its preview and its confirmation, because the timing it needs
cannot be arranged from a command line.

## The real runs

Five, in `logs/live-runs.txt`, on issue 1 of the participant's private sandbox repository.

1. A preview: add the label "enhancement". READY, 6 requests, all GET.
2. The participant's confirmation. One write, status 200. The issue was read back and matched. GitHub recorded
   one "labeled" event, whose id is in the result record.
3. The same confirmation again: refused, already used, 0 requests.
4. A second preview: "enhancement" again, and "bug". The first was reported already so and not sent.
5. The participant added the label "question" by hand, then confirmed preview 4. Refused as STALE: "labels:
   added "question"". 3 requests, all GET. Nothing was written.

The real runs matched the made-up GitHub. One wording fault was found: "1 minutes". It was corrected.

## Stretch goals

- **Add labels without removing others:** done, as the main design. Recorded in `stale-run.txt` parts 4 and 7.
- **Log the old value so the change can be reversed:** done. The result record holds the old value of each
  field and the changes that would put it back. A test makes an update, takes those changes from the record,
  previews and confirms them, and finds the issue as it was. Not tried on real GitHub: the label added in run
  2 is still there.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-update-metadata/tests -v
    python3 participant/evidence/github-update-metadata/github-attempt-005/scripts/record_evidence.py
    python3 participant/evidence/github-update-metadata/github-attempt-005/scripts/planted_bugs.py

None of these contacts GitHub. The second writes the four logs, `supported-fields.md` and the result record
again. The third changes `update.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| Automated tests | 88, all pass (`logs/tests.txt`) |
| Planted bugs | 46 put into `update.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 13, 24, 16 and 11, all pass |
| Real runs | 5. Two previews READY, one update DONE, two refusals with nothing written |

The planted bugs include the quest's scenario in two forms: a label added by sending the whole list of labels
(bug O), and a milestone request that carries the whole list as well (bug P).

One planted bug was deliberately **not** planted: making the sender used by `preview` able to send a write.
The test for it calls that sender directly, and with the guard removed the test would have sent a real request
to GitHub. The guard is tested as it stands.

Faults found while building: one in the assistant's tests, which counted the letters "time.time" inside
"datetime.timezone". None was found in the workflow by the tests. The real run found the wording fault above.

## What could not be done, and limitations

- **The gap between the check and the write.** Stated above. It is narrow, not closed.
- **Project fields: not supported.** They are refused. The assistant believes a token limited to one
  repository cannot reach them, and did not check that against GitHub's documentation.
- **Who confirmed cannot be verified.** The workflow records the name typed with `--confirmed-by`. Anyone who
  can run the command can type any name. What ties the confirmation to a person is that they ran it.
- **"In the same session" is read as "in the same command":** the confirmation is an argument of the command
  that writes. There is no separate approval that could be given earlier and used later.
- **On real GitHub, not assessed:** a token that may not write, an unsupported or refused change, the four
  refusals of criterion 7, a repository off the allowlist, an assignee or milestone change, a label removed, a
  write refused part way, a rate limit, and the reversal.
- **The events GitHub lists** are read right after the write. If GitHub listed one late, the record would say
  none was listed. In the real run the event was listed at once.
- **A stale refusal does not use up the preview.** It stays unconfirmable only while the issue differs. If
  the maintainer undid their change within 15 minutes, the old preview would be accepted again, correctly.
- The allowlist names repositories by name. A repository that GitHub redirects, or knows under another name,
  is refused.
- The made-up GitHub, the workflow and the tests were written by the same assistant and can share a blind
  spot. The real runs covered the main path and the stale case only.

## Reflection

*Which field would you never let an agent change?*

The state. Closing an issue is not a description of the work, it is a claim that the work is finished, or
that it will not be done. Every other field here can be wrong for a day and be put right. A wrongly closed
issue drops off everyone's list, and the people who would have noticed stop looking. So in this workflow
"state" is refused with a reason, and I would keep it that way even with a perfect stale check, because the
check only tells me nothing moved. It does not tell me the work is done.

Of the three fields I did allow, the one I trust least is the milestone, and I did not expect that. Labels
and assignees are lists, so I could add and remove one at a time and never touch what someone else put there.
A milestone is a single value. Setting it always replaces whatever was there, and in the moment between the
check and the write I would replace someone else's choice without any sign of it. The real run made the
difference concrete for me: when I added "question" by hand, the update was refused, and even if it had not
been, "question" could not have been removed. I cannot say the same for a milestone.

The other thing I would hold back is anything the preview cannot show me whole. I refused project fields for
a practical reason, the wider token. But the better reason is the same as for the state: I should only
confirm a change when I can see the old value, the new value and exactly what will be sent.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, with Issues read and write, and expires in 7
  days. It should be deleted now that the quest is done, because it can write.
- The real previews, allowlist and result record are in a scratch folder outside the repository and are not
  handed in. `logs/live-runs.txt` is a masked copy of what the runs printed: the owner's login, the issue's
  node ID, the repository's id and the name typed as confirmer are replaced.
- The one real change is a label on a made-up issue in the participant's own sandbox.
- Everything else in this attempt comes from the made-up GitHub. Its logins, such as `robin-fixture`, its
  repositories and its labels are invented.

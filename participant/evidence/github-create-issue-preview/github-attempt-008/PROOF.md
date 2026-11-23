# PROOF: Preview an Issue Using Repository Conventions

Quest `github-create-issue-preview`, attempt `github-attempt-008`.

## How this was made

The preview, its tests, the made-up GitHub, the made-up draft and its sources, the recording scripts and this
document were written by an AI assistant (Claude) at the participant's direction. The participant chose the
design in three decisions: build against a made-up GitHub and run one real, read-only preview; read Markdown
templates, with every section required unless its heading says "(optional)"; and let a strong likely duplicate
stop the preview until a person says to go on. The participant added a template to their sandbox, made a
read-only token, and ran both real previews in their own terminal. The assistant never saw the token and sent
no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub. **not assessed** means nobody checked it.

## Approach

One script, `participant/skills/github-create-issue-preview/preview.py`. It reads a draft, checks it in six
ways, and if every check passes it builds the payload and shows it. It only reads GitHub.

1. **Template** (criterion 1): the repository's own template file is read from the repository. The draft's
   sections must be the template's, in its order, with no required one empty.
2. **What exists** (criterion 2): each label, each assignee and the milestone is looked up in the repository.
3. **Sources** (criterion 7): each citation is checked against the file and lines it names.
4. **Duplicates** (criterion 4): the `github-duplicate-search` skill is run on the local index, as it stands.
5. **Permission** (criterion 4): what GitHub says the account may do.
6. **Unchanged** (criterion 6): the repository is read at the start and the end and compared.

Every reason for refusing is listed, not only the first. A refused preview shows no payload, gives no
fingerprint and saves nothing (criterion 3).

## How I know the payload equals what a later write would send (criterion 5)

Three things make it so, and one thing limits the claim.

1. **It is built once, in one place.** One function, `build_payload`, makes the payload from the draft and
   from what the checks found. It is called once. A test reads the source and fails if a second call or a
   second way of writing the bytes appears.
2. **What is shown is the bytes, not a description of them.** The preview prints the payload as the exact
   JSON, with its length and SHA-256. The recording script takes those printed bytes, reads them as JSON, and
   compares them with a payload it builds itself from the draft file with its own code: the same five fields,
   the same values, the whole body. It also takes its own SHA-256 of them. Recorded in part 3 of
   `logs/preview-run.txt`.
3. **The same bytes are saved for the write.** A READY preview is saved under its fingerprint, with the payload
   and the SHA-256 of its bytes. A later write is to load that record and send `payload_bytes` of the saved
   payload, after checking the SHA-256. It builds nothing of its own.

A real fault was found here, by a test. The saved record is written as JSON with its keys sorted, so the
payload came back from the file with its fields in another order, and its bytes were different from the bytes
the preview had shown. The content was the same and the checksum was not. The bytes are now written in one
fixed field order, whatever order the payload is held in. A test checks it, and a planted bug that removes it
makes three tests fail. In the real run the assistant loaded the saved preview afterwards and got the 455
bytes and the SHA-256 that the preview had printed.

**The limit.** The write does not exist yet. It is the next quest. This quest shows that the payload is built
once, shown exactly, and saved with a checksum. That the write really sends those bytes, and nothing else, can
only be shown when the write is built. **Not assessed here.** What a write must do to keep the promise is
written in point 3.

What the payload cannot promise is in the reflection: the payload is what would be sent, not what GitHub would
make of it.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The draft follows the repository's issue template | recorded, tested, observed | `preview-run.txt` part 2; tests `Template`; real run 1, against a template the participant added to the sandbox |
| 2 | Labels, assignee and milestone are chosen from those that exist | recorded, tested, observed in part | `preview-run.txt` part 2; tests `OnlyWhatExists`; real run 1 for a label and an assignee. The sandbox has no milestones, so a milestone was not seen on real GitHub |
| 3 | A missing template section or unknown label stops the preview with a reason | recorded, tested, observed in part | `convention-refusal.txt` parts 1 and 2; tests `Refusals`; real run 2 for the unknown label. An empty section was not tried on real GitHub |
| 4 | The duplicate result and the permission check appear in the preview | recorded, tested, observed | `preview-run.txt` parts 2 and 5; tests `DuplicateAndPermission`; real run 1 |
| 5 | The preview contains the exact payload, not a summary | recorded, tested, observed | `preview-run.txt` part 3; `participant/context/github/new-issue/payload.md`; tests `ExactPayload`; real run 1 |
| 6 | Running the preview changes nothing on GitHub | recorded, tested, observed | `preview-run.txt` part 4: every request a GET, and the made-up GitHub identical before and after; tests `NothingWritten`; both real runs, with a token that could not write |
| 7 | Source citations are included | recorded, tested, observed | The draft's `## Sources`; `preview-run.txt` part 2; `convention-refusal.txt` part 3; tests `Sources`; real run 1 |

### Criterion 1: what "required" means

A Markdown template is only headings. It has no way to say which are required. The rule here is the skill's
own, chosen by the participant: **every section is required unless its heading ends with "(optional)"**. A
section is empty when it holds nothing but blank lines, an HTML comment, or the template's own placeholder,
such as the lone "1." under "Steps to reproduce".

One fact shapes this quest. GitHub applies a template only in its web page. An issue created by a program gets
no template. So nothing on GitHub's side would stop the agent in the scenario, and the preview is the only
place the convention is enforced. This is the assistant's understanding of GitHub and was not checked against
its documentation.

### Criterion 4: where the checks cannot reach

- **Duplicates.** The search sees only the local index. An issue filed on GitHub since the last sync is not
  seen. A strong likely duplicate stops the preview. A person can go on by naming that issue with
  `--despite-duplicate`, and the preview then shows and records that it was overridden. Recorded in part 5.
- **Permission.** The preview shows what GitHub says the account may do. GitHub does not say what a
  fine-grained token may do, and the preview says so. It also catches one quiet failure: if the draft sets
  labels and the account may not triage, GitHub would create the issue and drop the labels without saying.
  That behaviour is the assistant's understanding, built into the check, and was not seen on real GitHub.

## Artifacts

| Required item | File |
|---|---|
| The draft | `participant/context/github/new-issue/draft.md`, with its sources in `new-issue/sources/notes.md` |
| The payload | `participant/context/github/new-issue/payload.md` |
| The preview run | `logs/preview-run.txt`, 22 checks |
| The refusal | `logs/convention-refusal.txt`, 13 checks |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the two real runs, masked), `logs/tests.txt` (61 tests),
`logs/planted-bugs.txt` (29 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. In
`participant/context/github/new-issue/` there are also three drafts made to be refused or stopped
(`draft-empty-section.md`, `draft-unknown-label.md`, `draft-out-of-memory.md`) and the allowlist of the
recorded runs. The skill is `participant/skills/github-create-issue-preview/`: `SKILL.md`, `preview.py`,
`fake_github.py`, `tests/test_preview.py`.

The duplicate check of the recorded runs uses the index handed in for the last quest,
`participant/context/github/duplicates/fixture.md`, unchanged.

The draft, the payload and the two required logs come from the made-up GitHub, so that nothing real is shared.
The made-up GitHub keeps its repositories in one file, and the recording script opens that file before and
after each preview.

## The real runs

Two, in `logs/live-runs.txt`, on the participant's private sandbox, with a token that could only read.

1. A draft that follows the template: READY. The template was read from the sandbox. The label `bug` exists
   and the participant can be assigned. No likely duplicate. The payload was 455 bytes. Newest issue number 3
   before and after, 11 labels before and after. 12 requests, every one a GET.
2. The same draft with a label the sandbox does not have: NOT READY, one reason, no payload, nothing saved. 11
   labels before and after, so the label was not created.

The made-up GitHub matched the real one. The preview was not changed after the real runs.

## Stretch goals

- **Show the difference from the nearest existing issue:** partly. The preview names each candidate the
  duplicate search found, with its confidence, its points and the signals that matched. It does not show a
  line-by-line difference of the two texts.
- **Validate labels against the live label list:** done. Every label is looked up in the repository's own list
  at the time of the preview, on the made-up GitHub and on the real one.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-create-issue-preview/tests -v
    python3 participant/evidence/github-create-issue-preview/github-attempt-008/scripts/record_evidence.py
    python3 participant/evidence/github-create-issue-preview/github-attempt-008/scripts/planted_bugs.py

None of these contacts GitHub. The second writes the two logs and `payload.md` again. The third changes
`preview.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| Automated tests | 61, all pass (`logs/tests.txt`) |
| Planted bugs | 29 put into `preview.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 22 and 13, all pass |
| Real runs | 2. One READY, one refused as intended |

One planted bug was deliberately **not** planted: letting the sender used on real GitHub send something other
than a GET. The test for it calls that sender directly, and with the guard removed the test itself would have
sent a real write. The guard is tested as it stands.

Faults found while building:

- **In the preview, one, found by a test:** the payload's bytes depended on the order of its fields. Described
  above.
- **In the made-up drafts, one, found by running them:** three drafts in sub-folders cited sources outside
  their own folder and were refused for that, not for what they were made to show. They were moved beside
  their sources.
- **In the assistant's tests, one:** a citation quoted words with the wrong capital letter.
- **In the recording script, one:** it reused a variable, so one part previewed an empty draft. The check
  failed, as it should, and the script was corrected.

## What could not be done, and limitations

- **The write is not built.** See above. The payload's promise is only half kept until it is.
- **Issue forms are not read.** Only Markdown templates with level-3 headings. A repository that uses YAML
  forms cannot be previewed by this skill.
- **"Required" is the skill's rule,** not GitHub's.
- **A citation is checked for truth, not for meaning.** The quoted words must be on the lines named. Whether
  those words support what the draft says is for a person to judge.
- **On real GitHub, not assessed:** an empty section, a milestone, a likely duplicate and its override, an
  account that may not triage, an archived repository, a repository off the allowlist, and a rate limit.
- **The duplicate check is only as fresh as the local index.** In the real run the index held one issue, saved
  several quests ago, of a repository whose newest issue number was by then 3.
- **The saved preview is good for 15 minutes,** a limit the next quest is to enforce. Nothing enforces it here.
- The made-up GitHub, the preview and the tests were written by the same assistant and can share a blind spot.

## Reflection

*What would a reader of your preview still not be able to predict?*

What GitHub will do with it. The preview shows me exactly what would be sent. It cannot show me what comes
back. I cannot see the number the issue will get, or whether the token can create an issue at all, because
GitHub does not tell a token what it may do and the preview does not try. I learned that in the verify quest
and it is still true here.

I also cannot predict what happens in the time between the preview and the write. The preview is true at the
moment it runs. A label can be renamed, a milestone closed, or someone else can file the same bug, and my
preview would still say READY. The duplicate check is the weakest part of that, because it looks at my local
copy, not at GitHub. In the real run my index knew one issue of a repository that had three.

And I cannot see what the issue sets off. The preview shows me a title, a body, a label and an assignee. It
does not show me that the assignee gets an email, that people watching the repository are notified, or that
some automation reacts to a new issue with that label. Those are consequences of the write that are not in the
payload at all.

What surprised me was something the preview did catch. I assumed "build the payload once" was enough to make
the preview honest. It was not: the saved copy came back with its fields in another order and would have been
sent as different bytes. Nobody reading the preview could have predicted that either. So the last thing a
reader cannot predict is whether the write really sends what the preview showed, and that is the next quest's
job to prove.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It was limited to one private sandbox repository, with Issues and Contents read-only, and expires
  in 7 days. It could not write.
- The real draft, its sources, the index, the allowlist, the saved preview and the payload file are in a
  scratch folder outside the repository and are not handed in. `logs/live-runs.txt` is a masked copy of what
  the runs printed: the owner's login and the repository's id are replaced.
- The one change made on GitHub for this quest was made by the participant by hand: a template file added to
  their own sandbox.
- Everything else in this attempt comes from the made-up GitHub. Its logins, such as `robin-fixture`, its
  repositories, labels and milestones are invented, and so are the draft and the notes it cites.

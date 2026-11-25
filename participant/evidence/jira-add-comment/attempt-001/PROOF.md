# PROOF: Preview and Add an Approved Comment

Quest `jira-add-comment`, attempt `jira-attempt-013`.

## How this was made

The workflow, its tests, the recording scripts and this document were written by an AI assistant (Claude) at the
participant's direction.

**The real runs were made by the participant, in their own terminal, with their own credentials.** The assistant gave
each command and read the output the workflow saved, which has the site's address removed. The assistant never saw the
API token, and ran nothing against Jira.

**One real comment was written**, to the story `SCRUM-1` in the participant's sandbox project `SCRUM`, on 2026-11-25. It
is still there. It reads:

    Test comment from the Golden Thread Quest sandbox exercise, added on 25 November 2026.
    It records nothing about real work and can be deleted.

The participant made these decisions:

- **The comment is unrestricted**: visible to everyone who can see the story. A restriction to one project role is
  built and tested on the fake Jira only.
- **The target is `SCRUM-1`**, the sandbox story an earlier quest used. The project was already on the participant's
  sandbox allowlist, added on 2026-11-19 after they confirmed it is a sandbox they may change.
- **The text** was drafted by the assistant, shown to the participant, and shown again in the preview they confirmed.
- **To post it.** They ran the confirmation themselves, with the fingerprint of the preview.

Words used below: **real** means the saved output of a run against the real sandbox shows it. **fake** means a recorded
run against the made-up Jira shows it. **tested** means an automated test checks it. **observed** means an independent
reader's reply shows it.

## The short version

- The workflow has three commands. `preview` reads and cannot write. `confirm` writes one comment, once, for one
  preview named by its fingerprint. `check` reads the story back.
- **On the real sandbox:** a preview, four refusals with nothing written, one approved write, a check that found the
  comment as previewed, and a second run that found it already there and offered nothing to confirm.
- **The comment read back is the text previewed, character for character**: 141 characters, the same checksum, plain
  text, under the token's account, visible to everyone who can see the story, and exactly one of it.
- **A reader went through the code before anything real was run**, and found no path that could post the wrong text or
  to the wrong place. It found faults in what happens after a write. They were corrected first.
- **A second reader checked the real evidence against itself** and found it consistent, with nothing real unredacted.
- **Three things were not done on the real site**, and are on the fake only: a preview left to expire in real time, a
  refusal aimed at another project, and any failure after a write.

## Approach

It is the pattern of the approved field-update quest, applied to a comment.

1. **Preview.** Read the story and its comments. Show the site, the project, the story, the exact text, who can see it,
   where the text came from, the permission check and the duplicate check. Issue a fingerprint. Write nothing: the
   command is given no function that can.
2. **Confirm.** A person names that fingerprint and gives their name. Everything is checked again, the comments are
   read again, and one request is sent. It is never retried.
3. **Read back.** The comment is fetched by the identifier Jira gave it and compared with the preview.
4. **Check.** A separate command reads the story again and looks for the comment.

A comment is different from a field in one way that shaped this: **it cannot be undone.** A field can be set back. A
comment can only be deleted, and any email Jira sent stays sent. So the preview says that, and the workflow refuses
more before it will send.

The rules are in `participant/skills/jira-add-comment/SKILL.md`.

## How private content and visibility are handled

### Visibility (criterion 1)

**The visibility stands on the line directly under the text**, in the preview, in capitals:

    | Test comment from the Golden Thread Quest sandbox exercise, added on 25 November 2026.
    | It records nothing about real work and can be deleted.
    WHO CAN SEE IT: EVERYONE who can see the story SCRUM-1. No restriction is put on the comment. The story has no security level.

Under it the preview says what it does not know: "This workflow cannot list who that is, and cannot tell whether the
project is open to customers or to the public. Jira may also email the story's watchers the whole text."

- **Two visibilities are supported and no others:** everyone who can see the story, or one project role by name.
- **The story's security level is shown beside it**, because a level changes who "everyone" is. Where Jira does not
  report one, the preview says "Jira did not say".
- **An unrestricted comment on a service project is refused**, because customers could see it. Where Jira does not
  give the kind of project, this does not stop a comment, and the preview shows "not given".
- **The visibility is part of what is confirmed.** If the change file asks for another visibility after the preview,
  or the story gains a security level, the confirmation is refused (criterion 6, tested).
- **It is read back** (criterion 2). The real read-back line: "its visibility is the one previewed: everyone who can
  see the story: yes".
- **The preview says whose name it goes under:** the Jira account the API token belongs to, not the name given with
  the confirmation.

### Private content

**The text comes from one local file, and the preview says which** (criterion 1): its name and its sha256. The
workflow does not write that file and does not take text from Jira. It says that who put the text there is not known
to it.

**Three layers, in this order:**

1. **Refused before Jira is asked anything: text that looks like a secret.** Nine patterns: an AWS key, a private key,
   a GitHub token, a Slack token, an Atlassian token, a JSON web token, a web address with a password in it, a
   password or key written out, and a long run of letters and digits. The refusal names the kind and the line and does
   not print the match. This is the first stretch goal. Recorded on the fake in `preview.txt`. Tested.
2. **Pointed out, not refused: what may be private.** An email address, a web address, a telephone number, an @name,
   and words such as "confidential" are listed above the fingerprint, by line. A program cannot judge these, so it
   shows them and leaves the decision to the person. Recorded on the fake. Tested.
3. **The person reads the text.** The preview says its search "is not a judgement that the text is fit to be seen".

**These are patterns.** They miss secrets of other shapes. A reader named some: a quoted name such as
`"password": "..."`, `pw=`, a value under four characters.

**Nothing from Jira is carried into the comment or acted on.** The story's title and text, and the comments already on
it, are never printed. The fake's story and one of its comments are worded as instructions, and tests check that
neither appears in any output. Other comments are compared with the text and counted.

**The text is sent as plain text.** One paragraph to a line. No formatting, no link, no mention. An `@name` is text
and notifies nobody.

**Credentials.** The token is read from the environment and never stored. Before output is shown it is searched for
the token, the email address and their encoded form. The site's address is shown on screen and replaced by a marker
in everything saved.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The preview shows the exact text, the target story, the visibility, and where the text came from | **real, fake, tested, observed** | `logs/preview.txt` part A |
| 2 | The comment read back matches the text previewed | **real, fake, tested, observed** | `logs/confirmation.txt` and `logs/comment-check.txt` part A. The check prints both texts, and the record compares them line for line with the preview |
| 3 | A preview shows the site, the project and the exact change, and nothing is written before the human confirms | **real, fake, tested. Observed with a reservation** | `logs/preview.txt`. The saved preview shows a marker where the site was: the address was on the participant's screen and is not in evidence. "Nothing written" rests on the program's list of requests, the two snapshots, and a count of 0 comments before the write |
| 4 | The preview records the permission check and the duplicate check, or states where Jira cannot check | **real, fake, tested, observed** | `logs/preview.txt` part A |
| 5 | Writes only to a project on an explicit sandbox allowlist | **real with a reservation, fake, tested** | The real refusal was made by giving an allowlist that lists no project. A refusal of another project, PROD-9, is on the fake only: the participant has one real project |
| 6 | Confirmation tied to a fingerprint; refused when missing or when the change differs; expires | **real for missing and differing. Test clock for expiry** | `logs/confirmation.txt`. The expiry refusal on the real site used the test clock on a preview under a minute old, and its output says so. No real preview was left to expire |
| 7 | A result record with the issue key, the identifier, the project, the timestamp and the confirmer | **real, observed** | `participant/context/jira/results/add-comment.md`. The confirmer is recorded as "the participant", a role and not a name, so that no real name is in evidence |
| 8 | Running again creates no duplicate, or the limit is stated | **real, fake, tested, observed** | `logs/rerun.txt` part A, and the stated limit at its end |

## The real runs, in order

All on 2026-11-25. Each was one command in the participant's terminal. The saved output of each is in `logs/` under
the name given.

| # | Run | Saved as | Result |
|---|---|---|---|
| 1 | Preview, with an allowlist that lists no project | `live-refused-allowlist.txt` | Refused. Nothing written |
| 2 | A first preview | `live-preview-first.txt` | Fingerprint `baf8fd02ec23`. Made only to try refusals against. Never confirmed |
| 3 | Confirm, with no fingerprint and no name | `live-refused-missing.txt` | Refused. Nothing written |
| 4 | Confirm the first preview, after the text file was changed | `live-refused-differs.txt` | Refused. Nothing written. The file was then put back and its checksum checked |
| 5 | Confirm the first preview, with the test clock 16 minutes on | `live-refused-stale.txt` | Refused. Nothing written |
| 6 | A second preview | `live-preview.txt` | Fingerprint `aeb8be1deadb`, made 21:21:07 UTC |
| 7 | **Confirm the second preview** | `live-confirmation.txt` | **Written 21:21:23 UTC. Comment id 10000** |
| 8 | Check | `live-comment-check.txt` | Found as previewed |
| 9 | Preview again | `live-rerun-preview.txt` | Nothing to add. No fingerprint |
| 10 | Confirm the second preview again | `live-rerun-confirm.txt` | Refused: a fingerprint is used once |

In step 4 the assistant changed the text file, in the repository only. Everything else was the participant's.

**Fourteen seconds passed between the second preview and its confirmation.** The same text, target and
visibility had been shown a minute earlier, in the first preview of step 2. Nothing in the files can show that a
person read either.

## Where the important artifacts are

Required by the quest:

| File | What it is |
|---|---|
| `participant/evidence/jira-add-comment/attempt-001/logs/comment-check.txt` | Reading the story back and finding the comment |
| `participant/evidence/jira-add-comment/attempt-001/logs/preview.txt` | The workflow stopping at a preview |
| `participant/evidence/jira-add-comment/attempt-001/logs/confirmation.txt` | The approved run and the four refusals |
| `participant/evidence/jira-add-comment/attempt-001/logs/rerun.txt` | The second run |
| `participant/context/jira/results/add-comment.md` | The result record |
| `participant/evidence/jira-add-comment/attempt-001/PROOF.md` | A copy of this file |

The quest text names `attempt-001`. The app's Start button made `jira-attempt-013`, which is where the work is.
`attempt-001/` holds copies, so the paths the quest names exist.

**Each of the four records has two parts.** Part A is the saved output of the real runs, copied in unchanged. Part B is
recorded against the fake Jira, and shows the cases that were not staged on the real site.

The rest:

| File | What it is |
|---|---|
| `participant/skills/jira-add-comment/comment.py` | The workflow. sha256 `fa47955852f7e23a0bad7c8503f855481dfbd717c75c55796731815582a03eb5`. It is the file that made the real runs, unchanged since |
| `participant/skills/jira-add-comment/SKILL.md` | The rules, and the limits |
| `participant/skills/jira-add-comment/fake_jira.py`, `fixtures/` | The made-up Jira, and the files used with it |
| `participant/skills/jira-add-comment/tests/test_comment.py` | 103 tests |
| `participant/context/jira/comment/` | The real change file, the text file, and the empty allowlist used in run 1 |
| `participant/context/jira/update/sandbox-allowlist.json` | The sandbox allowlist, from the earlier quest |
| `jira-attempt-013/logs/live-*.txt` | The ten saved outputs of the real runs |
| `jira-attempt-013/logs/tests.txt`, `planted-bugs.txt` | The test run, and 69 planted bugs each caught by a test |
| `jira-attempt-013/logs/independent-read.txt` | What two readers found, and what was changed |
| `jira-attempt-013/scripts/` | The scripts that wrote the records |

The state folder, with the saved previews and the record of the write, is in `local-data/`, which is not in the
repository. It holds the comment's text and nothing secret.

## Stretch goals

- **Refuse a comment containing a pattern that looks like a secret.** Done. Nine patterns, refused before Jira is asked
  anything, with the match not printed. On the fake and in tests. Not tried on the real site, since it never reaches it.
- **Add a comment that mentions a person and preview who is notified.** Not done. The workflow sends plain text only,
  so it cannot mention anyone, and Jira gives no dependable way to learn in advance who will be notified. The preview
  says instead that Jira may email the story's watchers the whole text.

## How to reproduce

Against the fake, from the repository's top folder, with Python 3.9 or later:

    python3 -m unittest discover -s participant/skills/jira-add-comment/tests
    python3 participant/evidence/jira-add-comment/jira-attempt-013/scripts/record_evidence.py
    python3 participant/evidence/jira-add-comment/jira-attempt-013/scripts/planted_bugs.py

`record_evidence.py` rewrites the four records. Part A is copied from the saved real outputs. Part B is run afresh, so
its times and fingerprints differ.

A real run needs a Jira sandbox, the three environment variables `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN`,
and an allowlist entry for the sandbox project. Running the real preview again now would report "NOTHING TO ADD",
because the comment is on the story.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The workflow against the fake Jira | 103 tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken workflow | 69 planted bugs, `logs/planted-bugs.txt` | all caught. Two were missed at first, and two tests were added |
| The four records | checks inside each: 34, 55, 19 and 15 | all pass |
| The real runs against each other | checks in the records: same fingerprint, times in order, same comment id, same lines of text | all pass |
| No credential in the output | the workflow searches its output before showing it | none found, stated at the end of each real output |
| No real address, email, name or path in the evidence | a search of every file here | none found. A reader found none either |

**What the real runs added that the fake could not:** that Jira answers 201 and gives an identifier, that plain text
comes back character for character, that the comment carries the token's account as its author, that an unrestricted
comment reads back with no restriction, and that the permission and comment lists have the shape the workflow reads.

## What independent readers found

Two fresh AI assistants read the work. **No person read it.** The full account is in `logs/independent-read.txt`.

- **Before the real run**, a reader traced every path to a write and found none that could post other text, or to
  another story, site or project. It found that a read failing after a successful write would have been reported as
  "nothing has been written", that a failure of the program after the write lost its output, and that the preview did
  not name the allowlist file or the account. All were corrected before anything real was run.
- **After the real runs**, a reader checked every fingerprint, time, identifier, checksum and line of text across the
  saved files and found them to agree, and found nothing real unredacted. It found that some labels in the records
  claimed more than saved text can show, and that the three refusals did not say which preview they were made against.
  The records were corrected. It also found smaller faults in the code, which stand.

**What changed after the last read, and was not read again:** the records and the rules document. The workflow itself
was not changed after the real runs.

## Remaining limitations

- **The comment is on the real sandbox and stays there** until someone deletes it by hand.
- **Who can see it is not known.** The workflow shows the restriction and the security level. It cannot list people.
- **Expiry was not seen in real time**, and **no refusal was aimed at another real project.**
- **Nothing after a write went wrong on the real site.** A lost answer, a failed read and a refusal from Jira are tried
  on the fake only.
- **The role restriction was never sent to real Jira.**
- **The saved previews are plain local files.** They stop mistakes and stale approvals. They do not stop someone who
  edits them on purpose. Such a person still could not make the workflow post other text or to another place.
- **The name given with a confirmation is not checked against anyone.**
- **Two runs at the very same moment could both write.** Jira has no "only if there is none" condition. The run counts
  the comments afterwards and stops with "MORE THAN ONE".
- **Code limits a reader found after the real run**, listed in SKILL.md and left as they are, so that the file is the
  one that ran.
- **The fake is built from Jira's published specification.** It is not Jira.

## Reflection

*Who could see this comment that you did not expect?*

Going in, I thought of the comment as going to "the sandbox". Reading the preview made me see three audiences I hadn't
thought about. The first is anyone Jira emails: watchers get the whole text in their inbox, and deleting the comment
later doesn't pull those emails back. The second is whoever can see the story at all, which the tool told me plainly
it cannot list, and I confirmed without a list. The third is that it sits under my own Jira account, not under "the
participant", so anyone who sees it sees me beside it.

On a customer-facing project the same unrestricted comment would have gone to customers, which is why the workflow
refuses that case. What I take from it is that "visibility: everyone" is a statement about a list of people I have
never looked at.

## Sensitive values

No token, password or session cookie is in any file here. The site's address is replaced by a marker in everything
saved, and a 16-character fingerprint of its name stands in its place. That fingerprint is not a secret: someone who
guessed the name could confirm the guess. No email address, account identifier or real person's name is in the
evidence. The comment's text is made up and holds nothing private.

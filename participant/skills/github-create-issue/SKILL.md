# GitHub: create a previewed issue, and tie the local file to it

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill makes one approved write: it creates the issue that a preview showed, after a person confirms, and
then ties the local draft to the issue GitHub made.

Its rule: **send exactly what was previewed, once, and never guess whether it arrived.**

It works in separate commands:

- `preview` runs the `github-create-issue-preview` skill as it stands. It only reads.
- `confirm` creates the issue of one preview, named by its fingerprint. It is the only command that can write.
- `verify` reads the linked issue back and compares it with the preview. It only reads.
- `reconcile` settles a create whose outcome is not known. It only reads GitHub.

    python3 participant/skills/github-create-issue/create.py preview   --source live --draft DRAFT.md --index INDEX.md --allowlist FILE --state FOLDER --link FILE
    python3 participant/skills/github-create-issue/create.py confirm   --source live --draft DRAFT.md --allowlist FILE --state FOLDER --link FILE --results FOLDER --fingerprint F --confirmed-by NAME
    python3 participant/skills/github-create-issue/create.py verify    --source live --draft DRAFT.md --allowlist FILE --link FILE
    python3 participant/skills/github-create-issue/create.py reconcile --source live --draft DRAFT.md --allowlist FILE --link FILE --results FOLDER

`--source fake --fake-store FILE` uses the made-up GitHub in `fake_github.py`. The skill uses the Python standard
library only, and needs the preview, duplicate-search and index skills' folders beside it.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`, set in your own terminal with `read -s` and then
`export`. The narrowest token that works is a fine-grained one, on the one sandbox repository, with **Issues:
read and write**, **Contents: read-only** (for the template) and **Metadata: read-only**.

Unset the variable afterwards, and delete the token when the work is done. It can write.

## 3. The local link file

One file ties one draft to one issue. By default it is `linked.md` beside the draft. Its status is one of:

| Status | Meaning |
|---|---|
| `creating` | the create was about to be sent. If the file still says so, the outcome is not known |
| `unknown` | the create was sent and no usable answer came back. The issue may exist |
| `linked` | the draft is the GitHub issue named in the file, matched by its node ID |
| `not-created` | GitHub refused, or `reconcile` found no such issue. A new preview is allowed |

A draft whose link says `linked`, `creating` or `unknown` is **never created again**: `preview` and `confirm`
both refuse it. A link file that cannot be read stops everything, because it is then not known whether the
draft already has an issue.

## 4. `confirm`

It refuses, and sends nothing, when:

- the fingerprint or the confirmer's name is missing;
- the repository is not on the sandbox allowlist;
- the draft is already linked, or its outcome is unknown;
- there is no saved preview with that fingerprint, or it was altered, or it was already used;
- **the draft was changed after the preview**. A confirmation covers exactly what its preview showed;
- the saved payload does not give the bytes the preview showed;
- the preview is more than **15 minutes** old, by GitHub's clock;
- the account or the repository is not the one of the preview;
- a label or the milestone of the payload no longer exists, or an issue with exactly this title was created in
  the repository after the preview.

Then, in this order:

1. it writes the local link with status `creating`, and marks the preview as used;
2. it sends **one** request: the saved payload's bytes, to the repository's issues;
3. it writes the number and node ID GitHub returned into the local link, **before anything else**;
4. it reads the issue back, checks its node ID, and compares it with the payload: title, body, labels,
   assignees, milestone;
5. it writes the comparison into the local link and adds a section to the result record.

The write builds nothing. The payload was built once, by the preview, and saved with the SHA-256 of its bytes.

## 5. How `confirm` ends

- **DONE** (exit 0): created, recorded, read back, and the same as the preview field for field.
- **NEEDS LOOKING** (exit 3): the issue exists and is recorded, and is not what the preview showed. For example
  GitHub dropped the labels. Nothing is changed to fix it.
- **OUTCOME UNKNOWN** (exit 3): no usable answer came back. The issue may exist. It is not sent again.
- **NOT DONE** (exit 1): GitHub refused the create. No issue was made. The preview is spent.
- **REFUSED** or **STOPPED** (exit 1): nothing was sent.

A timeout is treated as unknown, never as failed. The skill never sends a create a second time by itself.

## 6. `reconcile`

For a link that says `creating` or `unknown`. It looks on GitHub for issues made by the same account, since
shortly before the create was sent, with **exactly** the previewed title and body.

- **One found**: it is linked, read back, compared and recorded, as `confirm` would have done.
- **None found**, and the create was sent less than a minute ago: not settled yet. GitHub's list can lag.
- **None found**, later: the link becomes `not-created`, and a new preview is allowed.
- **More than one**: nothing is linked. A person closes the extra ones, then runs `reconcile --number N`.

## 7. `verify`

Reads the linked issue by its number and checks that its **node ID** is the one in the local link. A number
alone is not trusted. Then it compares the issue with the previewed payload, field by field. It writes nothing,
on GitHub or locally.

## 8. The result record

Each issue created or linked adds a section to `create-issue.md` in the `--results` folder: outcome, how it was
recorded, repository, number, node ID and GitHub's id, GitHub's time of creation, who confirmed, the account,
the preview's fingerprint, the payload's checksum, and the field-by-field comparison.

## 9. Tests

    python3 -m unittest discover -s participant/skills/github-create-issue/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 10. What it does not do, and its limits

- **GitHub cannot be told "only once".** It creates an issue every time it is asked. What prevents a second one
  is the local link file. If that file is deleted, the protection is gone, apart from the check for an issue
  with the same title created since the preview.
- **`reconcile` recognises an issue by its title, body, author and time**, not by a hidden mark in it. A mark
  would be surer, but it would be text in the issue that the preview did not show.
- It cannot know who typed the confirmation. It records the name it is given.
- It does not know what a fine-grained token may do until GitHub answers the create.
- It does not edit, label, close or delete an issue. If the issue is not what the preview showed, a person
  puts it right.
- A live run must keep its draft, previews, link and result record outside this repository.

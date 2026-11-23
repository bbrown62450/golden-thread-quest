# Supported fields: what the metadata update may change

Written by an AI assistant (Claude) at the participant's direction, for the quest `github-update-metadata`. The
two runs at the end are put in by `scripts/record_evidence.py`, against the made-up GitHub. The workflow is
`participant/skills/github-update-metadata/update.py`.

## What it may change

Three fields of one issue, in six ways. Nothing else.

| Asked for as | What it does | Allowed values | Sent to GitHub as |
|---|---|---|---|
| `label.add=NAME` | adds one label | a label that already exists in the repository. Capitals do not matter | `POST .../issues/N/labels` with that one label |
| `label.remove=NAME` | removes one label | a label that exists in the repository | `DELETE .../issues/N/labels/NAME` |
| `assignee.add=LOGIN` | assigns one person | a login GitHub says can be assigned in this repository. At most 10 on one issue | `POST .../issues/N/assignees` with that one login |
| `assignee.remove=LOGIN` | unassigns one person | a login that is assigned | `DELETE .../issues/N/assignees` with that one login |
| `milestone.set=TITLE` | puts the issue in a milestone | the exact title of one open milestone of the repository | `PATCH .../issues/N` with only the milestone's number |
| `milestone.clear=yes` | takes the issue out of its milestone | only `yes` | `PATCH .../issues/N` with only `milestone: null` |

Limits: at most 10 changes in one preview. One issue per preview. Issues only, not pull requests. Only a
repository named in the sandbox allowlist, `participant/context/github/update/sandbox-allowlist.json`.

A change that is already so (adding a label the issue has) is reported and is not sent.

## Why labels and assignees are added and removed one at a time

GitHub can also replace the whole list of labels in one request. That is how a label a maintainer added that
morning gets removed by a workflow working from an older copy. This workflow never sends a whole list. A label
it was not asked about is not in any request it sends, so it cannot be removed by it.

## What it refuses

| Asked for as | Refused because |
|---|---|
| `title` | the title is content, not metadata. This workflow does not change what an issue says |
| `body` | the body is content, not metadata. This workflow does not change what an issue says |
| `state` | closing or reopening an issue is a decision, not metadata. A person does that on GitHub |
| `locked` | locking a conversation is a moderation decision. A person does that on GitHub |
| `type` | the issue type is set by the organization's own rules. This workflow does not change it |
| `label.set` | replacing the whole list of labels is how a label that someone else added gets removed. Ask for label.add and label.remove, one label at a time |
| `label.create` | this workflow does not create labels. A label must already exist in the repository |
| `assignee.set` | replacing the whole list of assignees could remove someone another person assigned. Ask for assignee.add and assignee.remove |
| `milestone.create` | this workflow does not create milestones. A milestone must already exist and be open |
| `project.ANYTHING`, `projects.ANYTHING` | project fields live in GitHub Projects, outside the repository. Changing them needs a wider token than this workflow is given, so it does not change them |
| anything else | it is not a field this workflow knows |

It also refuses, with the reason shown in the preview:

- a label the repository does not have. GitHub would create it without saying, so the workflow checks first;
- a login GitHub says cannot be assigned in the repository;
- a milestone that is closed, that does not exist, or whose title two milestones share;
- a request that asks for a thing and its opposite, or for the same thing twice;
- a value that is empty, longer than 100 characters or not on one line;
- a pull request, an archived repository, and an account GitHub says may not change issues there.

One refused change stops the whole preview. No fingerprint is given, so nothing can be confirmed.

**Project fields** are refused on purpose. They live in GitHub Projects, outside the repository, and are changed
through a different interface with a wider token. The assistant believes a token limited to one repository
cannot reach them, and did not check that against GitHub's documentation.

## Run 1: unsupported changes refused

Seven changes are asked for. Six are refused: the title, the state, a project field, replacing the whole label
list, a label that does not exist, and a closed milestone. The seventh is supported and would be allowed alone.

    $ python3 participant/skills/github-update-metadata/update.py preview --source fake --fake-store SCRATCH/unsupported/github.json --repo acme-fixture/sandbox --issue 7 --change 'title=A new title' --change state=closed --change project.status=Done --change 'label.set=in progress' --change 'label.add=brand new' --change 'milestone.set=Sprint 11' --change label.add=urgent --allowlist participant/context/github/update/sandbox-allowlist.json --state SCRATCH/unsupported/previews

    github-update: PREVIEW of a change to an issue's metadata. This command only reads. It has no way to write
    github-update: 1. WHERE. Repository "acme-fixture/sandbox", id 401, private. Issue 7, node ID I_kwFX4010007, state open. The connection acts as login "robin-fixture"
    github-update: 2. ALLOWLIST. The repository is on the sandbox allowlist participant/context/github/update/sandbox-allowlist.json, which names 1 repository
    github-update: 3. WHAT WAS ASKED, change by change:
    github-update:      "title=A new title": REFUSED. NOT SUPPORTED: the title is content, not metadata. This workflow does not change what an issue says
    github-update:      "state=closed": REFUSED. NOT SUPPORTED: closing or reopening an issue is a decision, not metadata. A person does that on GitHub
    github-update:      "project.status=Done": REFUSED. NOT SUPPORTED: project fields live in GitHub Projects, outside the repository. Changing them needs a wider token than this workflow is given, so it does not change them
    github-update:      "label.set=in progress": REFUSED. NOT SUPPORTED: replacing the whole list of labels is how a label that someone else added gets removed. Ask for label.add and label.remove, one label at a time
    github-update:      label.add="brand new": REFUSED. the repository has no label of that name. This workflow does not create labels, and GitHub would create one without saying
    github-update:      label.add="urgent": WILL CHANGE
    github-update:      milestone.set="Sprint 11": REFUSED. that milestone is closed
    github-update: 4. OLD AND NEW VALUES of every field this workflow can change:
    github-update:      old:       labels     ["bug", "needs triage"]
    github-update:                 assignees  ["robin-fixture"]
    github-update:                 milestone  "Sprint 12" (number 1)
    github-update:      new:       labels     ["bug", "needs triage", "urgent"]
    github-update:                 assignees  ["robin-fixture"]
    github-update:                 milestone  "Sprint 12" (number 1)
    github-update:      difference: labels: added "urgent"
    github-update: 5. EXACT REQUESTS a confirmation would send, in this order: 1
    github-update:      POST /repos/acme-fixture/sandbox/issues/7/labels {"labels": ["urgent"]}
    github-update: 6. PERMISSION CHECK. GitHub says the ACCOUNT may change issues here (admin: no, maintain: no, pull: yes, push: yes, triage: yes)
    github-update:      GitHub reports no scopes for this token, as for a fine-grained token, and does not say what the TOKEN may do. That is known only when a write is tried: a token that may not write is refused by GitHub with status 403, and nothing changes
    github-update: 7. DUPLICATE CHECK. Each change was compared with the issue as it is now. Already so, and not sent: 0. GitHub does not refuse a repeated change of this kind itself: it accepts it and changes nothing
    github-update: 8. NOTHING WAS WRITTEN. The issue was read again at the end. Its labels, assignees and milestone before: d9ec373ce5378387. After: d9ec373ce5378387. The same
    github-update:      Requests made by this command: 6, every one a GET
    github-update: RESULT: NOT READY. 6 changes were refused. No fingerprint is given, so there is nothing to confirm

    exit code: 1

Checked by the recording script, from the made-up GitHub's own file: the made-up GitHub received no write, no
preview was saved, and the repository still has its 5 labels, so "brand new" was not created. Result: as expected.

## Run 2: the preview showing old and new values

This is the preview of `logs/preview.txt`, part 2. Section 4 shows the old and new value of every field the
workflow can change, including the one that stays the same.

    github-update: PREVIEW of a change to an issue's metadata. This command only reads. It has no way to write
    github-update: 1. WHERE. Repository "acme-fixture/sandbox", id 401, private. Issue 7, node ID I_kwFX4010007, state open. The connection acts as login "robin-fixture"
    github-update: 2. ALLOWLIST. The repository is on the sandbox allowlist participant/context/github/update/sandbox-allowlist.json, which names 1 repository
    github-update: 3. WHAT WAS ASKED, change by change:
    github-update:      label.add="bug": ALREADY SO, nothing is sent for it. the issue already has this label
    github-update:      label.add="in progress": WILL CHANGE
    github-update:      label.remove="needs triage": WILL CHANGE
    github-update:      milestone.set="Sprint 13": WILL CHANGE
    github-update: 4. OLD AND NEW VALUES of every field this workflow can change:
    github-update:      old:       labels     ["bug", "needs triage"]
    github-update:                 assignees  ["robin-fixture"]
    github-update:                 milestone  "Sprint 12" (number 1)
    github-update:      new:       labels     ["bug", "in progress"]
    github-update:                 assignees  ["robin-fixture"]
    github-update:                 milestone  "Sprint 13" (number 3)
    github-update:      difference: labels: added "in progress", removed "needs triage"
    github-update:      difference: milestone: "Sprint 12" (number 1) became "Sprint 13" (number 3)
    github-update: 5. EXACT REQUESTS a confirmation would send, in this order: 3
    github-update:      POST /repos/acme-fixture/sandbox/issues/7/labels {"labels": ["in progress"]}
    github-update:      DELETE /repos/acme-fixture/sandbox/issues/7/labels/needs%20triage
    github-update:      PATCH /repos/acme-fixture/sandbox/issues/7 {"milestone": 3}
    github-update: 6. PERMISSION CHECK. GitHub says the ACCOUNT may change issues here (admin: no, maintain: no, pull: yes, push: yes, triage: yes)
    github-update:      GitHub reports no scopes for this token, as for a fine-grained token, and does not say what the TOKEN may do. That is known only when a write is tried: a token that may not write is refused by GitHub with status 403, and nothing changes
    github-update: 7. DUPLICATE CHECK. Each change was compared with the issue as it is now. Already so, and not sent: 1. GitHub does not refuse a repeated change of this kind itself: it accepts it and changes nothing
    github-update: 8. NOTHING WAS WRITTEN. The issue was read again at the end. Its labels, assignees and milestone before: d9ec373ce5378387. After: d9ec373ce5378387. The same
    github-update:      Requests made by this command: 6, every one a GET
    github-update: 9. FINGERPRINT of this preview: 589af57e276472d5d89287f09d16696d. It covers the repository, the issue, the old values, the new values and the exact requests
    github-update:      Made at 2026-11-23T09:00:00Z by GitHub's clock. It can be confirmed once, for 15 minutes
    github-update:      To confirm: run the same command with `confirm` in place of `preview`, and add --fingerprint 589af57e276472d5d89287f09d16696d --confirmed-by YOUR-NAME
    github-update: RESULT: READY. Nothing has been written

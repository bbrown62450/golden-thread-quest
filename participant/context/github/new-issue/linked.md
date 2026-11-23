---
format: "github-issue-link/1"
status: "linked"
draft: "draft.md"
draft_sha256: "571120a34f12ec5e356cd1f22d71db063f4b4aec92aa826f0ac3367af8d083db"
repository: "[owner]/gtq-sandbox"
repository_id: "[repository id]"
fingerprint: "7d2f66b4612b03758a3887b72b49c04d"
payload_sha256: "b62fef3e09ee02f21a3a7cb1fb9951012e8f730d9b53cd4f12106578ab35f72a"
confirmed_by: "the participant"
account: "[owner]"
sent_at: "2026-11-23T18:59:16Z"
number: 4
node_id: "[node id]"
id: "[issue id]"
html_url: "https://github.com/[owner]/gtq-sandbox/issues/4"
created_at: "2026-11-23T18:59:17Z"
linked_by: "created by this workflow, and recorded from GitHub's answer"
compared_at: "2026-11-23T18:59:18Z"
compared: "same"
---

# Local link: draft.md

**This is a masked copy.** The file was written by the real run on the participant's private sandbox repository, when the participant confirmed
the creation of issue 4. The original is kept outside this repository. Five values are replaced and shown in square brackets, or as
"the participant": the owner's login, the issue's node ID, the repository's id, GitHub's numeric id of the issue, and the name typed as
confirmer. Nothing else was changed. The made-up run's version of this file is kept beside it under a name that says so.

Written by the github-create-issue skill. It ties one local draft to one GitHub issue. Every value above is JSON.

**Status: linked.** This draft is the GitHub issue named below. It is matched to it by its node ID, not by its number alone.

- repository: "[owner]/gtq-sandbox", id [repository id]
- issue number: 4
- node ID, the identifier this file is matched by: `[node id]`
- GitHub's id: [issue id]
- created at: 2026-11-23T18:59:17Z, by GitHub's clock
- how it was linked: created by this workflow, and recorded from GitHub's answer

## Read back and compared

After the issue was created it was read back from GitHub, at 2026-11-23T18:59:18Z, and compared with the payload of the preview, field
by field. Result: **every field is the same**.

| Field | In the previewed payload | Read back from GitHub | Same? |
|---|---|---|---|
| `title` | "Made-up bug: the export leaves the last row out" | "Made-up bug: the export leaves the last row out" | yes |
| `body` | 330 characters, SHA-256 `8c95c863f403aec9` | 330 characters, SHA-256 `8c95c863f403aec9` | yes |
| `labels` | ["bug"] | ["bug"] | yes |
| `assignees` | ["[owner]"] | ["[owner]"] | yes |
| `milestone` | null | null | yes |

## The payload that was sent

```json
{
 "assignees": [
  "[owner]"
 ],
 "body": "### What happened\n\nThe made-up export leaves the last row out of the file. The file `small-orders.csv` has 12 orders and the export writes 11 rows. No error is shown.\n\n### Steps to reproduce\n\n1. Run the made-up export on `small-orders.csv`.\n2. Count the rows in the file it writes.\n\n### What you expected\n\nAll 12 rows in the file.",
 "labels": [
  "bug"
 ],
 "title": "Made-up bug: the export leaves the last row out"
}
```

The bytes sent were these fields in the preview's fixed order. Their SHA-256 is `b62fef3e09ee02f21a3a7cb1fb9951012e8f730d9b53cd4f12106578ab35f72a`.

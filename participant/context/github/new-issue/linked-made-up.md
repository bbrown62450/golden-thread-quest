---
format: "github-issue-link/1"
status: "linked"
draft: "draft.md"
draft_sha256: "adf517df1b0f39c28fed20116665cae696d0de92ec3ca93cf7eab0d857088595"
repository: "acme-fixture/tracker"
repository_id: 401
fingerprint: "420af1396d5b8b7837a378f6837250f7"
payload_sha256: "669e858129780c413d269e767c1dc8d84a8c831ca0e5d9a7907354c90d103636"
confirmed_by: "the participant"
account: "robin-fixture"
sent_at: "2026-11-24T09:00:00Z"
number: 108
node_id: "I_kwFX4010108"
id: 5000108
html_url: "https://github.com/acme-fixture/tracker/issues/108"
created_at: "2026-11-24T09:00:00Z"
linked_by: "created by this workflow, and recorded from GitHub's answer"
compared_at: "2026-11-24T09:00:00Z"
compared: "same"
---

# Local link: draft.md

Written by the github-create-issue skill. It ties one local draft to one GitHub issue. Every value above is JSON.

**Status: linked.** This draft is the GitHub issue named below. It is matched to it by its node ID, not by its number alone.

- repository: "acme-fixture/tracker", id 401
- issue number: 108
- node ID, the identifier this file is matched by: `I_kwFX4010108`
- GitHub's id: 5000108
- created at: 2026-11-24T09:00:00Z, by GitHub's clock
- how it was linked: created by this workflow, and recorded from GitHub's answer

## Read back and compared

After the issue was created it was read back from GitHub, at 2026-11-24T09:00:00Z, and compared with the payload of the preview, field
by field. Result: **every field is the same**.

| Field | In the previewed payload | Read back from GitHub | Same? |
|---|---|---|---|
| `title` | "Export writes dates in two different formats in one file" | "Export writes dates in two different formats in one file" | yes |
| `body` | 516 characters, SHA-256 `f873142fda8d70c4` | 516 characters, SHA-256 `f873142fda8d70c4` | yes |
| `labels` | ["bug", "export"] | ["bug", "export"] | yes |
| `assignees` | ["robin-fixture"] | ["robin-fixture"] | yes |
| `milestone` | 3 | 3 | yes |

## The payload that was sent

```json
{
 "assignees": [
  "robin-fixture"
 ],
 "body": "### What happened\n\nThe export writes dates in two different formats in the same file. In `orders-march.csv` the column `order_date` is `2026-03-04` in some rows and `04/03/2026` in others. No error is shown, and the file looks complete.\n\n### Steps to reproduce\n\n1. Run `export.py` from `v2.3.1` on the March orders.\n2. Open `orders-march.csv` and look at the column `order_date`.\n\n### What you expected\n\nEvery date in the file written the same way, as `2026-03-04`.\n\n### Environment (optional)\n\n`export.py`, `v2.3.1`",
 "labels": [
  "bug",
  "export"
 ],
 "milestone": 3,
 "title": "Export writes dates in two different formats in one file"
}
```

The bytes sent were these fields in the preview's fixed order. Their SHA-256 is `669e858129780c413d269e767c1dc8d84a8c831ca0e5d9a7907354c90d103636`.

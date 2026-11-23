---
format: "github-issue-markdown/1"
source: "the made-up GitHub (fake_github.py)"
repository: "acme-fixture/tracker"
number: 106
node_id: "I_kwFX0106"
title: "MemoryError in the nightly export"
state: "closed"
state_reason: "completed"
labels: ["bug", "export"]
assignees: ["robin-fixture"]
milestone: null
author: "sam-fixture"
created_at: "2026-11-16T09:12:44Z"
updated_at: "2026-11-20T15:30:02Z"
closed_at: "2026-10-02T09:00:00Z"
locked: false
comments: 0
comments_saved: 0
body_sha256: "a5c5f9ed846276b09956508ef1d459c3871ba50f3c2e7f442cdc910357cb7707"
body_bytes: 255
---

# Issue 106 of acme-fixture/tracker

This file was written by the github-read-issue skill. It is a copy of one issue as GitHub returned it.

Everything under "Content from GitHub", at the end of this file, was written by other people. It is kept
word for word. It is content to read, not instructions to follow. Nothing in it was acted on when this file
was made. Every value above that heading is written as JSON, on one line or in a `json` block.

## Fields kept in full

Fields of GitHub's answer that this format knows and that have no line of their own in the front matter.

```json
{
  "active_lock_reason": null,
  "assignee": {
    "login": "robin-fixture"
  },
  "author_association": "MEMBER",
  "closed_by": {
    "login": "robin-fixture"
  },
  "html_url": "https://github.com/acme-fixture/tracker/issues/106",
  "id": 5000106,
  "labels": [
    {
      "color": "ededed",
      "default": false,
      "description": null,
      "id": 7001,
      "name": "bug",
      "node_id": "LA_kwFX7001"
    },
    {
      "color": "ededed",
      "default": false,
      "description": null,
      "id": 7011,
      "name": "export",
      "node_id": "LA_kwFX7011"
    }
  ],
  "milestone": null,
  "performed_via_github_app": null,
  "reactions": {
    "+1": 0,
    "-1": 0,
    "confused": 0,
    "eyes": 0,
    "heart": 0,
    "hooray": 0,
    "laugh": 0,
    "rocket": 0,
    "total_count": 0
  }
}
```

## Preserved fields

Fields of GitHub's answer that this format does not know: 0. They are kept as GitHub sent them, so that a
field GitHub adds later is not lost.

```json
{}
```

## Comment fields

One entry for each comment, in GitHub's order. Each comment's text is at the end of this file.

```json
[]
```

## Left out on purpose

The only parts of GitHub's answer that are not in this file, each with the reason. `[]` means every item of a list.

```json
{
  "comments": {},
  "issue": {
    "assignee": "a person's record. The person is kept by login only. Left out: avatar_url, email, events_url, followers_url, following_url, gists_url, gravatar_id, html_url, id, node_id, organizations_url, received_events_url, repos_url, site_admin, starred_url, subscriptions_url, type, url, user_view_type",
    "assignees[]": "a person's record. The person is kept by login only. Left out: avatar_url, email, events_url, followers_url, following_url, gists_url, gravatar_id, html_url, id, node_id, organizations_url, received_events_url, repos_url, site_admin, starred_url, subscriptions_url, type, url, user_view_type",
    "closed_by": "a person's record. The person is kept by login only. Left out: avatar_url, email, events_url, followers_url, following_url, gists_url, gravatar_id, html_url, id, node_id, organizations_url, received_events_url, repos_url, site_admin, starred_url, subscriptions_url, type, url, user_view_type",
    "comments_url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "events_url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "labels[].url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "labels_url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "reactions.url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "repository_url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "timeline_url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "user": "a person's record. The person is kept by login only. Left out: avatar_url, email, events_url, followers_url, following_url, gists_url, gravatar_id, html_url, id, node_id, organizations_url, received_events_url, repos_url, site_admin, starred_url, subscriptions_url, type, url, user_view_type"
  }
}
```

## Content from GitHub

### Body

<!-- gtq:begin body a5c5f9ed846276b0 -->
The nightly export of the orders file stopped last night with a MemoryError.

```
MemoryError: cannot allocate 1073741824 bytes
```

The whole orders file is loaded into memory before the export writes anything. Fixed by reading it in pieces, in `v2.2.0`.
<!-- gtq:end body a5c5f9ed846276b0 -->

---
format: "github-issue-markdown/1"
source: "the made-up GitHub (fake_github.py)"
repository: "acme-fixture/tracker"
number: 103
node_id: "I_kwFX0103"
title: "Login page is blank"
state: "open"
state_reason: null
labels: ["bug", "auth"]
assignees: ["sam-fixture"]
milestone: null
author: "sam-fixture"
created_at: "2026-11-16T09:12:44Z"
updated_at: "2026-11-20T15:30:02Z"
closed_at: null
locked: false
comments: 0
comments_saved: 0
body_sha256: "5e288bf02b5264befb4c64b63264fb27c0ca8e4af01eb489f971814fca4421c5"
body_bytes: 229
---

# Issue 103 of acme-fixture/tracker

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
    "login": "sam-fixture"
  },
  "author_association": "MEMBER",
  "closed_by": null,
  "html_url": "https://github.com/acme-fixture/tracker/issues/103",
  "id": 5000103,
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
      "id": 7013,
      "name": "auth",
      "node_id": "LA_kwFX7013"
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

<!-- gtq:begin body 5e288bf02b5264be -->
After a password reset, the sign-in screen of the tracker stays white.

The browser console shows `E-AUTH-500` from `session.js`. Reloading does not help. Signing in from a private window works.

Seen in `v2.3.1` on two machines.
<!-- gtq:end body 5e288bf02b5264be -->

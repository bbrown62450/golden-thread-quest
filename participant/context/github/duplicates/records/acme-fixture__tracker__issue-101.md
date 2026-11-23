---
format: "github-issue-markdown/1"
source: "the made-up GitHub (fake_github.py)"
repository: "acme-fixture/tracker"
number: 101
node_id: "I_kwFX0101"
title: "Export crashes on files over 2 GB"
state: "open"
state_reason: null
labels: ["bug", "export"]
assignees: ["robin-fixture"]
milestone: null
author: "sam-fixture"
created_at: "2026-11-16T09:12:44Z"
updated_at: "2026-11-20T15:30:02Z"
closed_at: null
locked: false
comments: 1
comments_saved: 1
body_sha256: "a38f7798122cfd60441c6089ca242fa489cc24b911c2809127662d25fde9bb5b"
body_bytes: 403
---

# Issue 101 of acme-fixture/tracker

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
  "closed_by": null,
  "html_url": "https://github.com/acme-fixture/tracker/issues/101",
  "id": 5000101,
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
[
  {
    "body_sha256": "e9dcb3fd446fe14ce66601bd8e944f65fd96aaaacc24da312b6443add00ce2b2",
    "fields": {
      "author_association": "MEMBER",
      "created_at": "2026-11-18T10:00:00Z",
      "html_url": "https://github.com/acme-fixture/tracker/issues/101#issuecomment-7710",
      "id": 7710,
      "node_id": "IC_kwFX7710",
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
      },
      "updated_at": "2026-11-18T10:00:00Z",
      "user": {
        "login": "kit-fixture"
      }
    },
    "not_known_to_this_format": []
  }
]
```

## Left out on purpose

The only parts of GitHub's answer that are not in this file, each with the reason. `[]` means every item of a list.

```json
{
  "comments": {
    "issue_url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "reactions.url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "url": "an address on api.github.com. It can be worked out again from the repository and the number",
    "user": "a person's record. The person is kept by login only. Left out: avatar_url, email, events_url, followers_url, following_url, gists_url, gravatar_id, html_url, id, node_id, organizations_url, received_events_url, repos_url, site_admin, starred_url, subscriptions_url, type, url, user_view_type"
  },
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

<!-- gtq:begin body a38f7798122cfd60 -->
The nightly export stops part way when the orders file is large.

Steps:

1. Take the made-up file `orders-march.csv`, which is about 2.4 GB.
2. Run `export.py` from `v2.3.1`.

It fails after a few minutes with:

```
MemoryError: cannot allocate 2147483648 bytes
error code E-EXPORT-413
```

Smaller files export without trouble. The whole file seems to be loaded into memory before anything is written.
<!-- gtq:end body a38f7798122cfd60 -->

### Comment 1 of 1

<!-- gtq:begin comment-1 e9dcb3fd446fe14c -->
Same here. Memory climbs until the process is killed. The March orders file is the only one this large.
<!-- gtq:end comment-1 e9dcb3fd446fe14c -->

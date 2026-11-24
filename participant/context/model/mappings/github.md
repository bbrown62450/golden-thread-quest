# Mapping: GitHub to the canonical work-item model

Written out from `participant/skills/context-work-item-model/normalize.py` by its `--write-docs` command. Model version `work-item/1`.

## What is read

- `github/assigned/assigned.json`, written by github-read-assigned

## The stable identifier

The issue's `node_id`. Not `owner/name#number`: the number and the repository both change when an issue is transferred.

## Canonical fields, and where each comes from

| Canonical field | From GitHub |
|---|---|
| `identity` | `github:` + `node_id` |
| `title` | `title` |
| `status` | `state` open -> open. closed with `state_reason` completed -> done. closed as not_planned or duplicate -> dropped. closed with no reason -> done. |
| `status_basis` | stated, except closed with no reason, which is inferred. |
| `assigned_to_me` | the sync's own `identity.login` is among `assignees` |
| `assignee_count` | the number of `assignees` |
| `blocked` | yes if the issue has a label the status map lists under `github.blocked_labels`. Otherwise unknown. |
| `container` | kind repository, `repo_id`, `full_name` |
| `parent` | none: see below |
| `labels` | `labels` |
| `due_at` | none: see below |
| `created_at` | `created_at` |
| `source_updated_at` | `updated_at` |
| `source_reference` | `full_name` + `#` + `number` |
| `source_url` | `https://github.com/` + `full_name` + `/issues/` + `number`, marked built |
| `retrieved_at` | the issue's `last_synced` |
| `sync_run` | the skill and the file's `last_successful_sync` |

## Statuses, and what is lost

- open covers both "not started" and "being worked on". A count of in_progress work across systems leaves every GitHub item out.
- An issue closed before GitHub recorded reasons has none, and is counted as done. It may have been abandoned.
- An open issue with a merged pull request is still open. The pull request is in `github.delivery_links`, and the status does not move.

## Kept as source fields

These are kept in the record's source block, under the `github.` prefix, as GitHub has them.

- `github.repository`
- `github.number`
- `github.state`
- `github.state_reason`
- `github.closed_at`
- `github.milestone`
- `github.earlier_references`
- `github.delivery_links`
- `github.comment_count`
- `github.private`

## Source fields that are not mapped

| GitHub has | Why it is not carried |
|---|---|
| the body, the comments | Non-goal: the text of the work. The count of comments is kept. |
| `author`, `assignees` as people, the actor of each event | Non-goal: who the people are. |
| timeline events other than links to pull requests and commits | History is a non-goal. The delivery links are kept, in `github.delivery_links`. |
| `state_history`, `first_seen`, `status` | They describe the local copy and its sync, not the work item. |

## Canonical fields GitHub cannot supply

| Field or value | Why |
|---|---|
| in_progress | GitHub has open and closed. An issue someone is working on looks the same as one nobody has touched. |
| due_at | An issue has no due date. A milestone can have one, and the saved work holds only the milestone's title. |
| parent | Sub-issues were not saved by the sync. |
| blocked, as a fact | GitHub's dependency summary was not saved by the sync. Only a label named in the status map can say yes. |

# Worked examples: the canonical model on saved work, side by side

Written by `participant/evidence/context-canonical-work-item/context-attempt-002/scripts/make_examples.py`, at the participant's direction. Every value in the
tables is copied from a canonical record in `items/`.

**What is real here.** The two Trello cards are real: they are on the participant's own sandbox board, and were read from Trello by an earlier quest. Their
titles are made-up work the participant typed. The GitHub issue comes from the made-up GitHub the earlier GitHub quest was built against. No real Jira item is
shown, and the last section says why.

Every value is JSON. The titles and labels are other people's text, carried as data.

## The canonical fields

The same fields, with the same meaning, for all three.

| Field | A Trello card (real) | A Trello card, archived (real) | A GitHub issue (made-up) |
|---|---|---|---|
| `identity` | `"trello:6afdf65638df50999c980d80"` | `"trello:6afdf655971ad373884d985b"` | `"github:I_kwFX1010001"` |
| `system` | `"trello"` | `"trello"` | `"github"` |
| `title` | `"Export report as PDF"` | `"Write onboarding guide"` | `"Export times out on large accounts"` |
| `status` | `"in_progress"` | `"dropped"` | `"done"` |
| `status_basis` | `"inferred"` | `"stated"` | `"stated"` |
| `status_source` | `"the card is in the list \"Doing\", which the status map says is in_progress"` | `"the card is archived in Trello"` | `"GitHub says the issue is closed as completed"` |
| `assigned_to_me` | `"yes"` | `"no"` | `"yes"` |
| `assignee_count` | `1` | `0` | `1` |
| `blocked` | `"unknown"` | `"unknown"` | `"unknown"` |
| `blocked_basis` | `null` | `null` | `null` |
| `container` | `{"id": "6afdf376f8b9111df7e27f99", "kind": "board", "name": "GTQ Sandbox"}` | `{"id": "6afdf376f8b9111df7e27f99", "kind": "board", "name": "GTQ Sandbox"}` | `{"id": "101", "kind": "repository", "name": "acme-fixture/platform"}` |
| `parent` | `null` | `null` | `null` |
| `labels` | `["feature"]` | `[]` | `[]` |
| `due_at` | `"2026-12-04T17:00:00Z"` | `null` | `null` |
| `created_at` | `null` | `null` | `"2026-10-02T09:00:00Z"` |
| `source_updated_at` | `"2026-11-18T20:12:04Z"` | `"2026-11-18T20:11:36Z"` | `"2026-10-20T16:00:00Z"` |

## Provenance

| Field | A Trello card (real) | A Trello card, archived (real) | A GitHub issue (made-up) |
|---|---|---|---|
| `source_system` | `"trello"` | `"trello"` | `"github"` |
| `source_id` | `"6afdf65638df50999c980d80"` | `"6afdf655971ad373884d985b"` | `"I_kwFX1010001"` |
| `source_reference` | `"p6m0OaAc"` | `"TjQwTg9X"` | `"acme-fixture/platform#1"` |
| `source_url` | `"https://trello.com/c/p6m0OaAc"` | `"https://trello.com/c/TjQwTg9X"` | `"https://github.com/acme-fixture/platform/issues/1"` |
| `source_url_basis` | `"built"` | `"built"` | `"built"` |
| `retrieved_at` | `"2026-11-18T20:29:47Z"` | `"2026-11-18T20:29:47Z"` | `"2026-11-03T09:00:00Z"` |
| `sync_run` | `"trello-read-board:2026-11-18T20:29:47Z"` | `"trello-read-board:2026-11-18T20:29:47Z"` | `"github-read-assigned:2026-11-03T09:00:00Z"` |
| `sync_source` | `"live"` | `"live"` | `"made-up"` |
| `source_record` | `"participant/context/trello/board.json"` | `"participant/context/trello/board.json"` | `"participant/context/github/assigned/assigned.json"` |
| `model` | `"work-item/1"` | `"work-item/1"` | `"work-item/1"` |

## The source fields

These are not side by side, because they are not the same fields. Each system keeps its own, under its own prefix.

### The Trello card

| Field | Value |
|---|---|
| `trello.short_link` | `"p6m0OaAc"` |
| `trello.board` | `{"closed": false, "id": "6afdf376f8b9111df7e27f99", "name": "GTQ Sandbox"}` |
| `trello.list` | `{"id": "6afdf3957e2f7562515212f7", "name": "Doing", "place_among_lists": 2}` |
| `trello.position` | `{"place_in_list": 1, "trello_number": 140737488355328}` |
| `trello.archived` | `false` |
| `trello.archived_by` | `[]` |
| `trello.labels` | `[{"color": "green", "name": "feature"}]` |
| `trello.due_complete` | `false` |
| `trello.checklists` | `{"complete": 0, "count": 1, "items": 3}` |
| `trello.comment_count` | `3` |

### The archived Trello card

| Field | Value |
|---|---|
| `trello.short_link` | `"TjQwTg9X"` |
| `trello.board` | `{"closed": false, "id": "6afdf376f8b9111df7e27f99", "name": "GTQ Sandbox"}` |
| `trello.list` | `{"id": "6afdf3911014b50669965df7", "name": "Backlog", "place_among_lists": 1}` |
| `trello.position` | `{"place_in_list": null, "trello_number": 140737488388096}` |
| `trello.archived` | `true` |
| `trello.archived_by` | `["card"]` |
| `trello.labels` | `[]` |
| `trello.due_complete` | `false` |
| `trello.checklists` | `{"complete": 0, "count": 0, "items": 0}` |
| `trello.comment_count` | `0` |

### The GitHub issue

| Field | Value |
|---|---|
| `github.repository` | `{"full_name": "acme-fixture/platform", "id": 101}` |
| `github.number` | `1` |
| `github.state` | `"closed"` |
| `github.state_reason` | `"completed"` |
| `github.closed_at` | `"2026-10-20T15:00:00Z"` |
| `github.milestone` | `null` |
| `github.earlier_references` | `[]` |
| `github.delivery_links` | `[{"kind": "pull request", "merged_at": "2026-10-20T10:00:00Z", "node_id": "PR_kwFX1010330", "reference": "acme-fixture/platform#330", "state": "closed"}, {"how": "references this issue", "kind": "commit", "reference": "a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1", "repository": "acme-fixture/platform"}, {"how": "closed this issue", "kind": "commit", "reference": "b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2", "repository": "acme-fixture/platform"}]` |
| `github.comment_count` | `1` |
| `github.private` | `false` |

## The differences, left visible

The model does not make these three look more alike than they are.

- **How sure the status is.** The GitHub issue is `done` and `stated`: GitHub itself says it was closed as completed. The first Trello card is `in_progress`
  and only `inferred`: Trello says it is in a list called "Doing", and it is the participant's status map that says that list means in progress. The two
  statuses sit in the same field, and `status_basis` keeps them from being read as equally certain.
- **What archived means.** The second Trello card is `dropped`. Trello says only that it was archived. Whether the work was finished or abandoned, Trello does
  not say, so the model does not either. A GitHub issue closed as completed and an archived Trello card may be the same event in two teams' lives, and they
  land on different values. This is the lossy case named in `mappings/trello.md`.
- **Delivery.** The GitHub issue's source block names the pull request and the commit that delivered it. The Trello cards have nothing of the kind. There is no
  canonical "delivered by" field, because two of the three systems could never fill it.
- **Order.** The Trello card is first in its list, and `trello.position` says so. The GitHub issue has no place in any order. The model has no canonical
  priority, and says so in its non-goals.
- **Dates.** The Trello card has a due date and no creation date. The GitHub issue has a creation date and no due date. Each `null` is a field that system
  cannot supply, and the mapping documents list them.
- **Labels.** The first card has one. The issue has an empty list, which means GitHub was asked and the issue has none. A card read from the assigned-cards
  list would have `null`, which means the labels were not saved.
- **Blocked.** `unknown` for all three. None of the saved records states it.
- **Where it came from.** Two are `live` and one is `made-up`, in `sync_source`. All three addresses are `built` from the saved reference, by the rule in the
  mapping document.

## Jira: why no saved Jira item is shown

None of the Jira work saved by the earlier quests can be put in the model. The model requires an item's stable identifier and the time it was retrieved, and
each kind of saved Jira record lacks one of them:

- the 13 story files have the issue id, and do not record when they were retrieved;
- the 3 stories in the assigned list have a retrieval time, and were saved with a key and no issue id.

So all 16 are reported as unmappable, with those reasons, and no record is written for them. `report.md` lists each one.

To show that the Jira mapping itself works, here is a **made-up** Jira story that has every required field, normalized in a scratch folder by this script. It is
not saved work, and it is not in `items/`.

| Field | A Jira story (made-up, not saved work) |
|---|---|
| `identity` | `"jira:30002"` |
| `system` | `"jira"` |
| `title` | `"Validate email addresses on intake"` |
| `status` | `"open"` |
| `status_basis` | `"stated"` |
| `status_source` | `"Jira's status \"To Do\", which Jira puts in its category \"new\""` |
| `assigned_to_me` | `"yes"` |
| `assignee_count` | `1` |
| `blocked` | `"yes"` |
| `blocked_basis` | `"a Jira link of the kind \"is blocked by\", to the issue with id \"30003\""` |
| `container` | `{"id": "30000", "kind": "project", "name": "Made-up project DEMO"}` |
| `parent` | `"jira:30010"` |
| `labels` | `["intake"]` |
| `due_at` | `"2026-12-01T00:00:00Z"` |
| `created_at` | `"2026-11-02T09:00:00Z"` |
| `source_updated_at` | `"2026-11-17T09:30:00Z"` |

| Source field | Value |
|---|---|
| `jira.key` | `"DEMO-2"` |
| `jira.project` | `{"id": "30000", "key": "DEMO", "name": "Made-up project DEMO"}` |
| `jira.issuetype` | `{"hierarchy_level": 0, "id": "10001", "name": "Story", "subtask": false}` |
| `jira.status` | `{"category": "new", "id": "1", "name": "To Do"}` |
| `jira.resolution` | `null` |
| `jira.priority` | `{"id": "3", "name": "Medium"}` |
| `jira.parent` | `{"id": "30010", "key": "DEMO-10", "type": "Epic"}` |
| `jira.issuelinks` | `[{"direction": "inward", "other": {"id": "30003", "key": "DEMO-3"}, "type": "Blocks"}]` |
| `jira.components` | `[]` |
| `jira.fixVersions` | `[]` |
| `jira.preserved_fields` | `[]` |

This is the only one of the four with a `parent`, and the only one where `blocked` is `yes`: Jira states both, in its parent field and in a link of the kind
"is blocked by".

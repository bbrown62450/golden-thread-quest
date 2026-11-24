# Worked examples: the canonical model on saved work, side by side

Written by `participant/evidence/context-canonical-work-item/context-attempt-002/scripts/make_examples.py`, at the participant's direction. Every value in the
tables is copied from a canonical record in `items/`.

**All four items are real, from two systems.** The two Trello cards are on the participant's own sandbox board, read from Trello by the approved
trello-read-board skill. The two GitHub issues are in the participant's own private sandbox repository, read from GitHub by the approved github-read-assigned
skill. Every title is made-up work the participant typed.

**What is masked.** The GitHub records were normalized from a masked copy of the real sync, `participant/context/github/assigned-live-masked/assigned.json`.
In it the owner's login, the node IDs and the repository's id are replaced, and shown in square brackets. So the identity of a GitHub item reads
`github:[issue node id 1]` here. On the participant's computer, where the real file is kept, it is `github:` and the real node ID. Nothing in the Trello
records is masked: the card ids, short links and board id were already in this repository from the Trello quests, and no person's identifier is in a record.

No real Jira item is shown, and the last section says why.

Every value is JSON. The titles and labels are other people's text, carried as data.

## The canonical fields

The same fields, with the same meaning, for all four.

| Field | A Trello card (real) | A Trello card, archived (real) | A GitHub issue, open (real) | A GitHub issue, closed (real) |
|---|---|---|---|---|
| `identity` | `"trello:6afdf65638df50999c980d80"` | `"trello:6afdf655971ad373884d985b"` | `"github:[issue node id 1]"` | `"github:[issue node id 2]"` |
| `system` | `"trello"` | `"trello"` | `"github"` | `"github"` |
| `title` | `"Export report as PDF"` | `"Write onboarding guide"` | `"Made-up task one"` | `"Made-up task two"` |
| `status` | `"in_progress"` | `"dropped"` | `"open"` | `"done"` |
| `status_basis` | `"inferred"` | `"stated"` | `"stated"` | `"stated"` |
| `status_source` | `"the card is in the list \"Doing\", which the status map says is in_progress"` | `"the card is archived in Trello"` | `"GitHub says the issue is open"` | `"GitHub says the issue is closed as completed"` |
| `assigned_to_me` | `"yes"` | `"no"` | `"yes"` | `"yes"` |
| `assignee_count` | `1` | `0` | `1` | `1` |
| `blocked` | `"unknown"` | `"unknown"` | `"unknown"` | `"unknown"` |
| `blocked_basis` | `null` | `null` | `null` | `null` |
| `container` | `{"id": "6afdf376f8b9111df7e27f99", "kind": "board", "name": "GTQ Sandbox"}` | `{"id": "6afdf376f8b9111df7e27f99", "kind": "board", "name": "GTQ Sandbox"}` | `{"id": "[repository id]", "kind": "repository", "name": "[owner]/gtq-sandbox"}` | `{"id": "[repository id]", "kind": "repository", "name": "[owner]/gtq-sandbox"}` |
| `parent` | `null` | `null` | `null` | `null` |
| `labels` | `["feature"]` | `[]` | `["enhancement", "question"]` | `[]` |
| `due_at` | `"2026-12-04T17:00:00Z"` | `null` | `null` | `null` |
| `created_at` | `null` | `null` | `"2026-11-21T17:13:09Z"` | `"2026-11-21T17:13:25Z"` |
| `source_updated_at` | `"2026-11-18T20:12:04Z"` | `"2026-11-18T20:11:36Z"` | `"2026-11-23T20:38:49Z"` | `"2026-11-21T17:22:16Z"` |

## Provenance

| Field | A Trello card (real) | A Trello card, archived (real) | A GitHub issue, open (real) | A GitHub issue, closed (real) |
|---|---|---|---|---|
| `source_system` | `"trello"` | `"trello"` | `"github"` | `"github"` |
| `source_id` | `"6afdf65638df50999c980d80"` | `"6afdf655971ad373884d985b"` | `"[issue node id 1]"` | `"[issue node id 2]"` |
| `source_reference` | `"p6m0OaAc"` | `"TjQwTg9X"` | `"[owner]/gtq-sandbox#1"` | `"[owner]/gtq-sandbox#2"` |
| `source_url` | `"https://trello.com/c/p6m0OaAc"` | `"https://trello.com/c/TjQwTg9X"` | `"https://github.com/[owner]/gtq-sandbox/issues/1"` | `"https://github.com/[owner]/gtq-sandbox/issues/2"` |
| `source_url_basis` | `"built"` | `"built"` | `"built"` | `"built"` |
| `retrieved_at` | `"2026-11-18T20:29:47Z"` | `"2026-11-18T20:29:47Z"` | `"2026-11-24T00:39:47Z"` | `"2026-11-24T00:39:47Z"` |
| `sync_run` | `"trello-read-board:2026-11-18T20:29:47Z"` | `"trello-read-board:2026-11-18T20:29:47Z"` | `"github-read-assigned:2026-11-24T00:39:47Z"` | `"github-read-assigned:2026-11-24T00:39:47Z"` |
| `sync_source` | `"live"` | `"live"` | `"live"` | `"live"` |
| `source_record` | `"participant/context/trello/board.json"` | `"participant/context/trello/board.json"` | `"participant/context/github/assigned-live-masked/assigned.json"` | `"participant/context/github/assigned-live-masked/assigned.json"` |
| `model` | `"work-item/1"` | `"work-item/1"` | `"work-item/1"` | `"work-item/1"` |

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

### The open GitHub issue

| Field | Value |
|---|---|
| `github.repository` | `{"full_name": "[owner]/gtq-sandbox", "id": "[repository id]"}` |
| `github.number` | `1` |
| `github.state` | `"open"` |
| `github.state_reason` | `null` |
| `github.closed_at` | `null` |
| `github.milestone` | `null` |
| `github.earlier_references` | `[]` |
| `github.delivery_links` | `[{"kind": "pull request", "merged_at": null, "node_id": "[pull request node id 1]", "reference": "[owner]/gtq-sandbox#3", "state": "open"}]` |
| `github.comment_count` | `3` |
| `github.private` | `true` |

### The closed GitHub issue

| Field | Value |
|---|---|
| `github.repository` | `{"full_name": "[owner]/gtq-sandbox", "id": "[repository id]"}` |
| `github.number` | `2` |
| `github.state` | `"closed"` |
| `github.state_reason` | `"completed"` |
| `github.closed_at` | `"2026-11-21T17:22:16Z"` |
| `github.milestone` | `null` |
| `github.earlier_references` | `[]` |
| `github.delivery_links` | `[]` |
| `github.comment_count` | `1` |
| `github.private` | `true` |

## The differences, left visible

The model does not make these four look more alike than they are.

- **How sure the status is.** The closed GitHub issue is `done` and `stated`: GitHub itself says it was closed as completed. The first Trello card is
  `in_progress` and only `inferred`: Trello says it is in a list called "Doing", and it is the participant's status map that says that list means in progress.
  The two statuses sit in the same field, and `status_basis` keeps them from being read as equally certain.
- **Work in progress that GitHub cannot name.** The open GitHub issue has a pull request pointing at it, in `github.delivery_links`, and that pull request is
  open. Somebody has started. Its status is still `open`, the same as an issue nobody has touched, because GitHub has no state between open and closed. The
  Trello card beside it is `in_progress`. The two may be at the very same stage, and they land on different values. This is the lossy case named in
  `mappings/github.md`, and here it is on real work.
- **What archived means.** The second Trello card is `dropped`. Trello says only that it was archived. Whether the work was finished or abandoned, Trello does
  not say, so the model does not either. The closed GitHub issue is `done`. An archived card and an issue closed as completed may be the same event in two
  teams' lives, and they land on different values. This is the lossy case named in `mappings/trello.md`.
- **Delivery.** The open GitHub issue's source block names the pull request that points at it. The Trello cards have nothing of the kind. There is no
  canonical "delivered by" field, because two of the three systems could never fill it.
- **Order.** The first Trello card is first in its list, and `trello.position` says so. The GitHub issues have no place in any order. The model has no
  canonical priority, and says so in its non-goals.
- **Dates.** The first Trello card has a due date and no creation date. The GitHub issues have a creation date and no due date. Each `null` is a field that
  system cannot supply, and the mapping documents list them.
- **Labels.** The open issue has two and the first card has one. The closed issue and the archived card have an empty list, which means the source was asked
  and the item has none. A card read from the assigned-cards list would have `null`, which means the labels were not saved.
- **Assigned to me.** `yes` for three and `no` for the archived card, which has no member. The answer is the same kind of fact in both systems. Who the
  assignee is, is not carried.
- **Blocked.** `unknown` for all four. None of the saved records states it.
- **Where it came from.** All four are `live` in `sync_source`. All four addresses are `built` from the saved reference, by the rule in the mapping
  document. The GitHub addresses hold `[owner]` where the real login is.

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

This is the only one of the five with a `parent`, and the only one where `blocked` is `yes`: Jira states both, in its parent field and in a link of the kind
"is blocked by".

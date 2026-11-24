# Mapping: Trello to the canonical work-item model

Written out from `participant/skills/context-work-item-model/normalize.py` by its `--write-docs` command. Model version `work-item/1`.

## What is read

- `trello/board.json`, written by trello-read-board
- `trello/assigned/assigned.json`, written by trello-read-assigned-cards

## The stable identifier

The card `id`, 24 characters Trello never changes. Not the short link, and not the name.

## Canonical fields, and where each comes from

| Canonical field | From Trello |
|---|---|
| `identity` | `trello:` + `id` |
| `title` | `name` |
| `status` | An archived card is dropped. An open card is whatever the status map says for the **id** of the list it is in. If the list is not in the status map, the card is open. A card Trello no longer returns cannot be mapped. |
| `status_basis` | stated for an archived card. inferred when the status map names the list. assumed when it does not. |
| `assigned_to_me` | the sync's own `member_id` is among the card's `member_ids`. unknown if the saved file has no `member_id`. |
| `assignee_count` | the number of `member_ids` |
| `blocked` | yes if the card has a label the status map lists under `trello.blocked_labels`. Otherwise unknown. Never no: Trello has no way to say a card is not blocked. |
| `container` | kind board, the board's `id` and `name` |
| `parent` | none: see below |
| `labels` | the names of the card's labels. null from `assigned.json`, which does not hold labels |
| `due_at` | `due` |
| `created_at` | none: see below |
| `source_updated_at` | `last_activity` |
| `source_reference` | the short link |
| `source_url` | `https://trello.com/c/` + the short link, marked built |
| `retrieved_at` | the card's `synced_at`, or the file's `last_successful_sync` |
| `sync_run` | the skill and the file's `last_successful_sync` |

## Statuses, and what is lost

- An archived card is dropped, whether it was finished or abandoned. Trello does not say which. If a team archives finished cards, their done work shows as dropped.
- A card marked complete on its due date (`due_complete`) is not thereby done. That tick is kept in the source block and the status still comes from the list.
- The position in the list, which is how a Trello team says what comes first, has no canonical field. It is kept in `trello.position`.
- Moving a card to another list may or may not change its status. That depends on the status map, not on Trello.

## Kept as source fields

These are kept in the record's source block, under the `trello.` prefix, as Trello has them.

- `trello.short_link`
- `trello.board`
- `trello.list`
- `trello.position`
- `trello.archived`
- `trello.archived_by`
- `trello.labels`
- `trello.due_complete`
- `trello.checklists`
- `trello.comment_count`

## Source fields that are not mapped

| Trello has | Why it is not carried |
|---|---|
| the description, checklist items' text, the comments | Non-goal: the text of the work. The counts are kept in the source block. |
| `member_ids` | Non-goal: who the people are. They are used to answer assigned_to_me and are then left behind. |
| `first_seen` | It describes the local copy, not the work item. |

## Canonical fields Trello cannot supply

| Field or value | Why |
|---|---|
| status, as a fact | Trello has no status. A card is in a list, and a list's name is words someone typed. Status is inferred or assumed for every open card. |
| in_progress, done | Only through the status map. Without it an open card is open, even in a list called Done. |
| parent | A card has no parent. A checklist item is not a work item in this model. |
| created_at | Not saved. Trello gives no creation time as a field. |
| blocked = no | Trello has nothing that states a card is free to proceed. |

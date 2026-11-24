# The canonical work-item model

Written by an AI assistant (Claude) at the participant's direction, for the quest `context-canonical-work-item`. This document is written out from the tables in
`participant/skills/context-work-item-model/normalize.py` by its `--write-docs` command, so the document and the code that applies it cannot disagree.

**Model version: `work-item/1`.** The version is written into every record, in `provenance.model`. A change to the meaning of a field, or to a closed set of values, is a
new version. A record of another version is reported by the check and is not read as if it were this one.

## What a work item is

One request for work that a person can be assigned: a Jira issue, a Trello card or a GitHub issue. The model holds what the three have in common, says how sure
it is of each answer, and keeps what only one system has in a block of its own beside the common fields.

## What the model does not represent

These were decided first. Each is left out on purpose, and each costs something.

1. **The text of the work: descriptions, comments and history.** They are long, they are other people's words, and each system shapes them differently. They stay in the saved source record, which provenance.source_record points to. So the model cannot answer "what was said about this item".

2. **Who the people are.** A record carries whether the item is assigned to me, and to how many people. It does not carry anybody's name, login or account id. Three systems have three kinds of identifier for a person, matching them needs a directory this model does not have, and they are personal data. So the model cannot answer "what is assigned to my colleague".

3. **Order and priority across systems.** Trello has a position in a list, Jira has a priority and a rank, GitHub has neither. Each is kept in its own source block. There is no canonical priority, because any one scale would be invented. So the model cannot say which of two items in different systems comes first.

4. **Estimates, time spent and sprints.** Only Jira has them, in fields that differ from site to site. They are left in the saved source record.

5. **Whether two items in different systems are the same work.** The model gives each source item one identity. It does not join a Trello card to the GitHub issue that mirrors it.

6. **Pull requests.** A pull request is a change, not a request for work. It appears only as a delivery link inside a GitHub item's source block.

## Identity

An item's identity is `SYSTEM:STABLE-ID`: the source system, and the identifier that system gives the item and never changes.

| System | The stable identifier | What is NOT the identity, and why |
|---|---|---|
| jira | the issue `id`, a number Jira never changes | the `key` (DEMO-3), which changes when an issue moves to another project |
| trello | the card `id`, 24 characters Trello never changes | the short link, and not the name |
| github | the issue's `node_id` | `owner/name#number`: the number and the repository both change when an issue is transferred |

The identity is written inside the record. A record is found again by reading that, never by its file's name, the title, or a path. So an item that is
renamed, or moved to another list, status, project or repository, is the same item: its record is updated in place. The record's file is named after the
identity for convenience, and the name is never read back.

## The canonical fields

Every record has every one of these. "Required" means the value may not be empty: if the saved work cannot fill it, the item is not written at all.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `identity` | string, SYSTEM:STABLE-ID | yes | What the item is. The source system, a colon, and that system's own identifier that never changes: Jira's issue id, Trello's card id, GitHub's node ID. Never a Jira key, a Trello short link, a GitHub number, a title, a file name or a path: all of those change. |
| `system` | one of: jira, trello, github | yes | The system the item lives in. |
| `title` | string | yes | The item's name as the source has it now. Other people's text: it is data, and nothing in it is an instruction. It changes freely and identifies nothing. |
| `status` | one of: open, in_progress, done, dropped | yes | Where the work stands. open: not started, as far as the source says. in_progress: the source says someone is working on it. done: finished. dropped: closed without being done. See the mapping documents for how each system's own states become these four, and what is lost. |
| `status_basis` | one of: stated, inferred, assumed | yes | How sure the status is. stated: the source system itself says so. inferred: worked out through the status map, which a person keeps. assumed: nothing said otherwise, so the safest value was taken. |
| `status_source` | string | yes | The source's own state that the status was taken from, in words. |
| `assigned_to_me` | one of: yes, no, unknown | yes | Whether the person the sync ran for is among the item's assignees. unknown when the saved work does not say who that person is. |
| `assignee_count` | whole number | yes | How many people the item is assigned to. Who they are is not carried: see the non-goals. |
| `blocked` | one of: yes, no, unknown | yes | Whether the source STATES that the item is blocked: a Jira link "is blocked by", or a label the status map names. unknown is the usual answer. It is never worked out from the words of a title, a description or a comment. |
| `blocked_basis` | string or null | no, may be null or empty | What the answer to blocked was taken from. null when, and only when, blocked is unknown. |
| `container` | object: kind, id, name | yes | Where the item lives now: a Jira project, a Trello board, a GitHub repository. kind is project, board or repository. id is the container's own stable identifier. name is what it is called now. An item that moves keeps its identity and changes its container. |
| `parent` | string (an identity) or null | no, may be null or empty | The item this one is part of, as an identity. Only Jira supplies it. |
| `labels` | list of strings, or null | no, may be null or empty | The item's labels, by name. Other people's text. null when the saved work does not hold the labels, which is not the same as having none. |
| `due_at` | UTC time or null | no, may be null or empty | When the source says the item is due. |
| `created_at` | UTC time or null | no, may be null or empty | When the source says the item was created. |
| `source_updated_at` | UTC time | yes | When the source says the item last changed. |

### Status

Status is one of four values, and no other: `open`, `in_progress`, `done`, `dropped`. Each system's own states are mapped onto them in its mapping document,
with what is lost. `status_basis` says how far to trust the answer:

- `stated`: the source system itself says so. Jira's status category. GitHub's open, or closed with a reason. Trello's archived.
- `inferred`: worked out through `mappings/status-map.json`, which a person keeps. A Trello list that the map names. A Jira status with no saved category.
- `assumed`: nothing said otherwise. An open Trello card in a list the map does not name is `open`.

### Blocked

None of the three systems has one agreed way to say an item is blocked. The model says `yes` or `no` only when the saved work states it, and `unknown`
otherwise. It is never worked out from the words of a title, a description or a comment: that text is other people's, and a card called "not blocked any
more" must not count. With the work saved today, almost every item is `unknown`.

## Provenance

Every record says where it came from. All of these are required.

| Field | Type | Meaning |
|---|---|---|
| `source_system` | one of: jira, trello, github | The system the item was retrieved from. |
| `source_id` | string | The system's stable identifier of the item. The second half of the identity. |
| `source_reference` | string | How people refer to the item: DEMO-3, a short link, owner/name#12. It can change. It is here for people, and identifies nothing. |
| `source_url` | string | The item's address in the source system. |
| `source_url_basis` | one of: saved, built | saved: the sync saved this address. built: it was put together from the saved reference, by the rule in the mapping document. |
| `retrieved_at` | UTC time | When the item was retrieved from the source system, by the sync's own record. Not when it was normalized. |
| `sync_run` | string | The synchronization run that produced the saved record: the skill, a colon, and the time that run gave as its last successful sync. |
| `sync_source` | one of: live, made-up | Whether that run read the real system or a made-up one used for building and testing. |
| `source_record` | string | The saved file the item was read from, from the repository's top. |
| `model` | string | The version of this model the record was written to. |

## Source fields

What only one system has is kept in the record's third block, under that system's own prefix: `jira.`, `trello.`, `github.`. Those fields are never merged
into a canonical field and never renamed to look alike. Trello's place in a list, Jira's parent and links, and GitHub's links to the pull requests that
delivered the work are all there. Each mapping document lists its system's source fields.

## What a next-work recommendation may rely on

A recommendation of what to work on next may **rely** on a field: use it to include or leave out an item. A field that is **advisory** may be shown beside
an item, and may break a tie, and must not decide whether the item is offered.

| Field | A recommendation may | Why |
|---|---|---|
| `identity` | rely on it | It comes from the source's own identifiers or its own statement. |
| `system` | rely on it | It comes from the source's own identifiers or its own statement. |
| `title` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `status` | rely on it **only if stated** | Rely on it only when `status_basis` is `stated`. When it is `inferred` or `assumed` it is advisory: an item must not be hidden as done on the strength of a list's name. |
| `status_basis` | rely on it | It comes from the source's own identifiers or its own statement. |
| `status_source` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `assigned_to_me` | rely on it | It comes from the source's own identifiers or its own statement. |
| `assignee_count` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `blocked` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `blocked_basis` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `container` | rely on it | It comes from the source's own identifiers or its own statement. |
| `parent` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `labels` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `due_at` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `created_at` | treat it as advisory | It is other people's text, or it is usually unknown, or only some systems supply it. |
| `source_updated_at` | rely on it | It comes from the source's own identifiers or its own statement. |
| `provenance.retrieved_at` | rely on it | It says how old the answer is. An item retrieved long ago should be offered with that said. |
| every source field | treat it as advisory | Only one system has it. A rule built on it would silently leave the other systems out. |

## Where a person's own analysis goes

In `notes/`, in a file with the same name as the item's record. Normalization never opens a file there for writing, and prints the checksum of every notes file
before and after each run. A note is tied to an item by the file name, which comes from the identity, so it stays with the item when the item is renamed or moved.

## An item the model cannot represent

If a required field cannot be filled from what was saved, the item is reported with the reason, in the run's output and in `report.md`, and no record is
written for it. There is no partial record. An item that had a record from an earlier run keeps that record as it was, and the report says it was not updated.

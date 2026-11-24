# Linked records across three systems

Written by an AI assistant (Claude) at the participant's direction, for the quest `context-cross-system-conflicts`, with
`participant/skills/context-cross-system-conflicts/make_records.py`.

Run: 2026-11-21

**Every record here is made up.** They are three made-up systems' records of the same made-up work, as they stood on 21 November.

Each record is one work item in one system: its stable identity, the fields the systems share in a common form, and under `as_sent` what the source itself
wrote for each, untouched. `status` is one of open, in_progress, done, dropped. `updated_at` is when the source says the record last changed.

## Links

Which records are the same piece of work. **A link is stated by a person**, and names each record by its stable identity. Nothing here was worked out from a title.

| Work | Jira | Trello | GitHub | Stated by |
|---|---|---|---|---|
| W-01 | `jira:41001` | `trello:6ae85f200000000000000a01` | `github:I_kwFIX0401` | the delivery lead, in the planning sheet PS-7, row 01 |
| W-02 | `jira:41002` | `trello:6ae86d300000000000000a02` | `github:I_kwFIX0402` | the delivery lead, in the planning sheet PS-7, row 02 |
| W-03 | `jira:41003` | `trello:6ae87b400000000000000a03` | `github:I_kwFIX0403` | the delivery lead, in the planning sheet PS-7, row 03 |
| W-04 | `jira:41004` | `trello:6ae889500000000000000a04` | none | the delivery lead, in the planning sheet PS-7, row 04 |
| W-05 | `jira:41005` | none | `github:I_kwFIX0405` | the delivery lead, in the planning sheet PS-7, row 05 |
| W-06 | `jira:41006` | none | `github:I_kwFIX0406` | the delivery lead, in the planning sheet PS-7, row 06 |
| W-07 | none | `trello:6ae8b3800000000000000a07` | `github:I_kwFIX0407` | the delivery lead, in the planning sheet PS-7, row 07 |
| W-08 | `jira:41008` | `trello:6ae8c1900000000000000a08` | none | the delivery lead, in the planning sheet PS-7, row 08 |
| W-09 | `jira:41009` | none | `github:I_kwFIX0409` | the delivery lead, in the planning sheet PS-7, row 09 |
| W-10 | `jira:41010` | `trello:6ae8ddb00000000000000a10` | none | the delivery lead, in the planning sheet PS-7, row 10 |
| W-11 | `jira:41011` | `trello:6ae8ebc00000000000000a11` | none | the delivery lead, in the planning sheet PS-7, row 11 |
| W-12 | `jira:41012` | `trello:6ae8f9d00000000000000a12` | `github:I_kwFIX0412` | the delivery lead, in the planning sheet PS-7, row 12 |
| W-13 | `jira:41013` | `trello:6ae907e00000000000000a13` | none | the delivery lead, in the planning sheet PS-7, row 13 |
| W-14 | `jira:41014` | none | `github:I_kwFIX0499` | the delivery lead, in the planning sheet PS-7, row 14 |
| W-15 | `jira:41015` | `trello:6ae924000000000000000a15` | none | the delivery lead, in the planning sheet PS-7, row 15 |
| W-16 | `jira:41016` | `trello:6ae924000000000000000a15` | none | the delivery lead, in the planning sheet PS-7, row 16 |

Three of these links are faulty on purpose: W-14 names a GitHub issue that is not in this file, and W-15 and W-16 both name the same Trello card.

## What depends on what

Which pieces of work cannot proceed until another is finished. Used only to order the report.

| Work | Depends on |
|---|---|
| W-04 | W-02 |
| W-06 | W-02 |
| W-09 | W-06 |
| W-11 | W-08 |

## The records

#### W-01

All three agree.

### jira:41001

```json
{
 "identity": "jira:41001",
 "system": "jira",
 "title": "Set up the intake form",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-03T10:12:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41001",
  "due": "duedate: null"
 }
}
```

### trello:6ae85f200000000000000a01

```json
{
 "identity": "trello:6ae85f200000000000000a01",
 "system": "trello",
 "title": "Set up the intake form",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-03T10:30:00Z",
 "as_sent": {
  "status": "in the list \"Done\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

### github:I_kwFIX0401

```json
{
 "identity": "github:I_kwFIX0401",
 "system": "github",
 "title": "Set up the intake form",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-03T10:20:00Z",
 "as_sent": {
  "status": "state closed, state_reason completed",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-02

The quest's scenario: the tracker says done, the board says in review, and the issue is still open. Days apart.

### jira:41002

```json
{
 "identity": "jira:41002",
 "system": "jira",
 "title": "Export intake records as CSV",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-10T09:00:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41002",
  "due": "duedate: null"
 }
}
```

### trello:6ae86d300000000000000a02

```json
{
 "identity": "trello:6ae86d300000000000000a02",
 "system": "trello",
 "title": "CSV export",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-05T14:00:00Z",
 "as_sent": {
  "status": "in the list \"In Review\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

### github:I_kwFIX0402

```json
{
 "identity": "github:I_kwFIX0402",
 "system": "github",
 "title": "Export intake records as CSV",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-04T10:00:00Z",
 "as_sent": {
  "status": "state open",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-03

The tracker and the issue were closed two hours after the card last moved.

### jira:41003

```json
{
 "identity": "jira:41003",
 "system": "jira",
 "title": "Validate email addresses on intake",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-18T10:00:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41003",
  "due": "duedate: null"
 }
}
```

### trello:6ae87b400000000000000a03

```json
{
 "identity": "trello:6ae87b400000000000000a03",
 "system": "trello",
 "title": "Validate email addresses on intake",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-18T08:00:00Z",
 "as_sent": {
  "status": "in the list \"Doing\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

### github:I_kwFIX0403

```json
{
 "identity": "github:I_kwFIX0403",
 "system": "github",
 "title": "Validate email addresses on intake",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-18T10:05:00Z",
 "as_sent": {
  "status": "state closed, state_reason completed",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-04

The tracker was closed in the morning. In the afternoon the card was moved back to Doing.

### jira:41004

```json
{
 "identity": "jira:41004",
 "system": "jira",
 "title": "Schedule the Friday export",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-17T09:00:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41004",
  "due": "duedate: null"
 }
}
```

### trello:6ae889500000000000000a04

```json
{
 "identity": "trello:6ae889500000000000000a04",
 "system": "trello",
 "title": "Schedule the Friday export",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-17T15:00:00Z",
 "as_sent": {
  "status": "in the list \"Doing\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

#### W-05

The tracker says in progress. GitHub can only say open.

### jira:41005

```json
{
 "identity": "jira:41005",
 "system": "jira",
 "title": "Tidy the export folder",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-12T11:00:00Z",
 "as_sent": {
  "status": "status In Progress, category indeterminate",
  "assigned": "assignee: account 5b10fixture41005",
  "due": "duedate: null"
 }
}
```

### github:I_kwFIX0405

```json
{
 "identity": "github:I_kwFIX0405",
 "system": "github",
 "title": "Tidy the export folder",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-11T09:00:00Z",
 "as_sent": {
  "status": "state open",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-06

The tracker says done. The issue was closed as not planned, half an hour later.

### jira:41006

```json
{
 "identity": "jira:41006",
 "system": "jira",
 "title": "Drop the legacy importer",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-16T10:00:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41006",
  "due": "duedate: null"
 }
}
```

### github:I_kwFIX0406

```json
{
 "identity": "github:I_kwFIX0406",
 "system": "github",
 "title": "Drop the legacy importer",
 "status": "dropped",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-16T10:30:00Z",
 "as_sent": {
  "status": "state closed, state_reason not_planned",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-07

The card and the issue were last changed at the same second, and differ.

### trello:6ae8b3800000000000000a07

```json
{
 "identity": "trello:6ae8b3800000000000000a07",
 "system": "trello",
 "title": "Rate-limit the public API",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-15T12:00:00Z",
 "as_sent": {
  "status": "in the list \"Done\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

### github:I_kwFIX0407

```json
{
 "identity": "github:I_kwFIX0407",
 "system": "github",
 "title": "Rate-limit the public API",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-15T12:00:00Z",
 "as_sent": {
  "status": "state open",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-08

The tracker's record does not say when it last changed.

### jira:41008

```json
{
 "identity": "jira:41008",
 "system": "jira",
 "title": "Document the rate limits",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": null,
 "as_sent": {
  "status": "status In Progress, category indeterminate",
  "assigned": "assignee: account 5b10fixture41008",
  "due": "duedate: null"
 }
}
```

### trello:6ae8c1900000000000000a08

```json
{
 "identity": "trello:6ae8c1900000000000000a08",
 "system": "trello",
 "title": "Document the rate limits",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-14T16:00:00Z",
 "as_sent": {
  "status": "in the list \"Done\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

#### W-09

The tracker was closed six hours after the issue last changed. The issue is still open.

### jira:41009

```json
{
 "identity": "jira:41009",
 "system": "jira",
 "title": "Add retry to the webhook sender",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-19T16:00:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41009",
  "due": "duedate: null"
 }
}
```

### github:I_kwFIX0409

```json
{
 "identity": "github:I_kwFIX0409",
 "system": "github",
 "title": "Add retry to the webhook sender",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-19T10:00:00Z",
 "as_sent": {
  "status": "state open",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-10

The card was moved to Done exactly 24 hours after the tracker last changed.

### jira:41010

```json
{
 "identity": "jira:41010",
 "system": "jira",
 "title": "Add a status page",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-19T09:00:00Z",
 "as_sent": {
  "status": "status In Progress, category indeterminate",
  "assigned": "assignee: account 5b10fixture41010",
  "due": "duedate: null"
 }
}
```

### trello:6ae8ddb00000000000000a10

```json
{
 "identity": "trello:6ae8ddb00000000000000a10",
 "system": "trello",
 "title": "Add a status page",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-20T09:00:00Z",
 "as_sent": {
  "status": "in the list \"Done\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

#### W-11

The card was moved to Done 24 hours and one second after the tracker last changed.

### jira:41011

```json
{
 "identity": "jira:41011",
 "system": "jira",
 "title": "Archive the old dashboards",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-19T09:00:00Z",
 "as_sent": {
  "status": "status In Progress, category indeterminate",
  "assigned": "assignee: account 5b10fixture41011",
  "due": "duedate: null"
 }
}
```

### trello:6ae8ebc00000000000000a11

```json
{
 "identity": "trello:6ae8ebc00000000000000a11",
 "system": "trello",
 "title": "Archive the old dashboards",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-20T09:00:01Z",
 "as_sent": {
  "status": "in the list \"Done\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

#### W-12

The statuses agree as far as each system can say. The due dates do not, three days apart, and the three titles differ.

### jira:41012

```json
{
 "identity": "jira:41012",
 "system": "jira",
 "title": "Rotate the signing key",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": "2026-12-01T00:00:00Z",
 "updated_at": "2026-11-10T09:00:00Z",
 "as_sent": {
  "status": "status In Progress, category indeterminate",
  "assigned": "assignee: account 5b10fixture41012",
  "due": "duedate: 2026-12-01"
 }
}
```

### trello:6ae8f9d00000000000000a12

```json
{
 "identity": "trello:6ae8f9d00000000000000a12",
 "system": "trello",
 "title": "Key rotation",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": "2026-12-04T17:00:00Z",
 "updated_at": "2026-11-13T09:00:00Z",
 "as_sent": {
  "status": "in the list \"Doing\"",
  "assigned": "idMembers: 1",
  "due": "due: 2026-12-04T17:00:00.000Z"
 }
}
```

### github:I_kwFIX0412

```json
{
 "identity": "github:I_kwFIX0412",
 "system": "github",
 "title": "Rotate signing key (security)",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-09T09:00:00Z",
 "as_sent": {
  "status": "state open",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

#### W-13

The tracker gained an assignee ninety minutes after the card last changed. The card has none.

### jira:41013

```json
{
 "identity": "jira:41013",
 "system": "jira",
 "title": "Write the onboarding guide",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-20T10:00:00Z",
 "as_sent": {
  "status": "status To Do, category new",
  "assigned": "assignee: account 5b10fixture41013",
  "due": "duedate: null"
 }
}
```

### trello:6ae907e00000000000000a13

```json
{
 "identity": "trello:6ae907e00000000000000a13",
 "system": "trello",
 "title": "Write the onboarding guide",
 "status": "open",
 "assignee_count": 0,
 "due_at": null,
 "updated_at": "2026-11-20T08:30:00Z",
 "as_sent": {
  "status": "in the list \"Backlog\"",
  "assigned": "idMembers: 0",
  "due": "due: null"
 }
}
```

#### Not linked to anything usable

A story with no counterpart, a card and an issue that share a title and no link, and the records the three faulty links name.

### jira:41050

```json
{
 "identity": "jira:41050",
 "system": "jira",
 "title": "Translate the help pages",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-08T09:00:00Z",
 "as_sent": {
  "status": "status To Do, category new",
  "assigned": "assignee: account 5b10fixture41050",
  "due": "duedate: null"
 }
}
```

### trello:6aeb10300000000000000a50

```json
{
 "identity": "trello:6aeb10300000000000000a50",
 "system": "trello",
 "title": "Fix export",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-09T09:00:00Z",
 "as_sent": {
  "status": "in the list \"Doing\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

### github:I_kwFIX0450

```json
{
 "identity": "github:I_kwFIX0450",
 "system": "github",
 "title": "Fix export",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-12T09:00:00Z",
 "as_sent": {
  "status": "state open",
  "assigned": "assignees: 1",
  "due": "an issue has no due date"
 }
}
```

### jira:41014

```json
{
 "identity": "jira:41014",
 "system": "jira",
 "title": "Add dark mode",
 "status": "open",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-07T09:00:00Z",
 "as_sent": {
  "status": "status To Do, category new",
  "assigned": "assignee: account 5b10fixture41014",
  "due": "duedate: null"
 }
}
```

### jira:41015

```json
{
 "identity": "jira:41015",
 "system": "jira",
 "title": "Search by title",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-06T09:00:00Z",
 "as_sent": {
  "status": "status In Progress, category indeterminate",
  "assigned": "assignee: account 5b10fixture41015",
  "due": "duedate: null"
 }
}
```

### jira:41016

```json
{
 "identity": "jira:41016",
 "system": "jira",
 "title": "Remove the old banner",
 "status": "done",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-06T10:00:00Z",
 "as_sent": {
  "status": "status Done, category done",
  "assigned": "assignee: account 5b10fixture41016",
  "due": "duedate: null"
 }
}
```

### trello:6ae924000000000000000a15

```json
{
 "identity": "trello:6ae924000000000000000a15",
 "system": "trello",
 "title": "Search and banner",
 "status": "in_progress",
 "assignee_count": 1,
 "due_at": null,
 "updated_at": "2026-11-06T11:00:00Z",
 "as_sent": {
  "status": "in the list \"Doing\"",
  "assigned": "idMembers: 1",
  "due": "due: null"
 }
}
```

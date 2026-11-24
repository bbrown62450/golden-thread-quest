# Inputs: work to be ranked, the school meals ordering app

Written by `participant/skills/context-next-work/make_inputs.py`, at the participant's direction, for the quest
`context-next-work`.

**Everything here is made up.** The project, a school meals ordering app, does not exist. No identifier belongs to a
real item, and the people are roles.

- clock: `2026-12-01T09:00:00Z`

The clock value is part of the input. The ranking reads it from the line above, or from `--now`, and never from the
computer's clock. `retrieved_at` is when the local copy of a record was fetched.

## What is in here on purpose

| Record | What it shows |
|---|---|
| `github:I_kwFIXnw00001` | The most votes of any item. Blocked, and its copy is 7 days old |
| `jira:61005`, `jira:61009` | Blocked by `jira:61001`. One of them has no priority recorded |
| `jira:61010` | Blocked by a decision that is still a question |
| `jira:61014` | Blocked by an item that has no record |
| `jira:61017` | Blocked by an item whose own copy is old |
| `jira:61004`, `jira:61018` | Not blocked, with a copy older than 24 hours |
| `jira:61016` | No `retrieved_at` at all |
| `jira:61015` | A due date that is not a date |
| `trello:7b2e000000000000000e0001` | High priority and no due date |
| `trello:7b2e000000000000000e0002` | Neither a priority nor a due date |
| `jira:61006`, `jira:61007` | Level on every criterion but the last |
| `jira:61008` | Low priority, due the day after the clock value |
| `jira:61011`, `jira:61012`, `jira:61013` | Taken, in progress, done |

## The records

### jira:61001

```json
{
  "identity": "jira:61001",
  "kind": "work",
  "title": "Allergen labels on the menu",
  "status": "open",
  "priority": "high",
  "due": "2026-12-03",
  "created": "2026-11-10",
  "votes": 4,
  "blocks": [
    "jira:61005",
    "jira:61009"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61002

```json
{
  "identity": "jira:61002",
  "kind": "work",
  "title": "Parents can cancel an order",
  "status": "open",
  "priority": "high",
  "due": "2026-12-03",
  "created": "2026-11-12",
  "votes": 2,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61003

```json
{
  "identity": "jira:61003",
  "kind": "work",
  "title": "Receipt email",
  "status": "open",
  "priority": "high",
  "due": "2026-12-10",
  "created": "2026-11-14",
  "votes": 0,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61004

```json
{
  "identity": "jira:61004",
  "kind": "work",
  "title": "Weekly menu import",
  "status": "open",
  "priority": "high",
  "due": "2026-12-02",
  "created": "2026-11-08",
  "votes": 1,
  "retrieved_at": "2026-11-24T08:00:00Z"
}
```

### jira:61005

```json
{
  "identity": "jira:61005",
  "kind": "work",
  "title": "Allergen filter",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-08",
  "created": "2026-11-16",
  "votes": 3,
  "blocked_by": [
    "jira:61001"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61006

```json
{
  "identity": "jira:61006",
  "kind": "work",
  "title": "Kitchen printout",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-05",
  "created": "2026-11-15",
  "votes": 1,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61007

```json
{
  "identity": "jira:61007",
  "kind": "work",
  "title": "Export orders to CSV",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-05",
  "created": "2026-11-15",
  "votes": 6,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61008

```json
{
  "identity": "jira:61008",
  "kind": "work",
  "title": "Low balance reminder",
  "status": "open",
  "priority": "low",
  "due": "2026-12-02",
  "created": "2026-11-18",
  "votes": 5,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61009

```json
{
  "identity": "jira:61009",
  "kind": "work",
  "title": "Allergen report for the kitchen",
  "status": "open",
  "due": "2026-12-09",
  "created": "2026-11-17",
  "votes": 0,
  "blocked_by": [
    "jira:61001"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61010

```json
{
  "identity": "jira:61010",
  "kind": "work",
  "title": "Pay by voucher",
  "status": "open",
  "priority": "high",
  "due": "2026-12-04",
  "created": "2026-11-11",
  "votes": 8,
  "needs_decision": [
    "decision:E-301"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61011

```json
{
  "identity": "jira:61011",
  "kind": "work",
  "title": "Term dates in the calendar",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-06",
  "created": "2026-11-13",
  "votes": 2,
  "assigned_to": "Developer B",
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61012

```json
{
  "identity": "jira:61012",
  "kind": "work",
  "title": "Design tokens",
  "status": "in_progress",
  "priority": "medium",
  "due": "2026-12-12",
  "created": "2026-11-05",
  "votes": 0,
  "assigned_to": "Designer A",
  "blocks": [
    "github:I_kwFIXnw00001"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61013

```json
{
  "identity": "jira:61013",
  "kind": "work",
  "title": "Remove the old login page",
  "status": "done",
  "priority": "low",
  "created": "2026-10-20",
  "votes": 0,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61014

```json
{
  "identity": "jira:61014",
  "kind": "work",
  "title": "Sibling discount",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-07",
  "created": "2026-11-19",
  "votes": 7,
  "blocked_by": [
    "jira:61099"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61015

```json
{
  "identity": "jira:61015",
  "kind": "work",
  "title": "Menu photo upload",
  "status": "open",
  "priority": "medium",
  "due": "soon",
  "created": "2026-11-20",
  "votes": 1,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61016

```json
{
  "identity": "jira:61016",
  "kind": "work",
  "title": "Translate the order page",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-05",
  "created": "2026-11-18",
  "votes": 0
}
```

### jira:61017

```json
{
  "identity": "jira:61017",
  "kind": "work",
  "title": "Refund flow",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-06",
  "created": "2026-11-21",
  "votes": 9,
  "blocked_by": [
    "jira:61018"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### jira:61018

```json
{
  "identity": "jira:61018",
  "kind": "work",
  "title": "Payment provider contract check",
  "status": "open",
  "priority": "high",
  "due": "2026-12-04",
  "created": "2026-11-09",
  "votes": 0,
  "retrieved_at": "2026-11-20T10:00:00Z"
}
```

### jira:61019

```json
{
  "identity": "jira:61019",
  "kind": "work",
  "title": "Free school meals flag",
  "status": "open",
  "priority": "medium",
  "due": "2026-12-09",
  "created": "2026-11-22",
  "votes": 2,
  "needs_decision": [
    "decision:E-302"
  ],
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### github:I_kwFIXnw00001

```json
{
  "identity": "github:I_kwFIXnw00001",
  "kind": "work",
  "title": "Dark mode",
  "status": "open",
  "priority": "low",
  "due": "2026-12-20",
  "created": "2026-10-01",
  "votes": 57,
  "blocked_by": [
    "jira:61012"
  ],
  "retrieved_at": "2026-11-24T08:00:00Z"
}
```

### trello:7b2e000000000000000e0001

```json
{
  "identity": "trello:7b2e000000000000000e0001",
  "kind": "work",
  "title": "Order cut-off time setting",
  "status": "open",
  "priority": "high",
  "created": "2026-11-23",
  "votes": 1,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### trello:7b2e000000000000000e0002

```json
{
  "identity": "trello:7b2e000000000000000e0002",
  "kind": "work",
  "title": "Tidy up the help page",
  "status": "open",
  "created": "2026-11-01",
  "votes": 0,
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### decision:E-301

```json
{
  "identity": "decision:E-301",
  "kind": "decision",
  "title": "Are vouchers accepted for part of an order?",
  "status": "question",
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

### decision:E-302

```json
{
  "identity": "decision:E-302",
  "kind": "decision",
  "title": "Free school meals are shown to kitchen staff only",
  "status": "decided",
  "retrieved_at": "2026-12-01T07:00:00Z"
}
```

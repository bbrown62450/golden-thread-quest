# Dependency data: the ferry timetable app

Written by `participant/skills/context-dependency-map/make_data.py`, at the participant's direction, for the quest
`context-dependency-map`.

**Everything here is made up.** The project, a ferry timetable app, does not exist. No identifier belongs to a real
item. Records that hold text which reads like an instruction or a dependency are sample data, put there on purpose.

## Identities

A work item's identity is `system:identifier`, in the form fixed by `participant/context/identity/rules.md`. A decision's
identity is `decision:` and its entry number, such as `decision:E-201`. A decision is a record like any other.

## The fields, and which of them record a dependency

| Field | Counted as a dependency | What it means |
|---|---|---|
| `blocked_by` | yes | This record waits on each one named. |
| `blocks` | yes | Each one named waits on this record. The same link as `blocked_by`, written from the other end. |
| `needs_decision` | yes | This record waits on each decision named. |
| `parent` | no | Grouping. A child does not wait on its parent, and a parent is not said to wait on its children. |
| `related` | no | Somebody thought two items had to do with each other. It says nothing about order. |
| `superseded_by` | no | The decision that replaced this one. |
| `title`, `description`, `labels` | no | Words. A title that says "once the search API is done" records nothing. |

A work item's `status` is `open`, `in_progress`, `done` or `dropped`. A decision's is `decided`, `proposal`, `question` or
`superseded`. Dates are planned dates, as calendar days.

## Every recorded link, and the field it comes from

| Written on | Field | Names |
|---|---|---|
| `jira:52001` | `blocks` | `jira:52002` |
| `jira:52001` | `blocks` | `jira:52005` |
| `jira:52002` | `blocked_by` | `jira:52001` |
| `jira:52002` | `blocks` | `jira:52003` |
| `jira:52003` | `blocked_by` | `jira:52002` |
| `jira:52003` | `blocks` | `jira:52004` |
| `jira:52004` | `blocked_by` | `jira:52003` |
| `jira:52004` | `needs_decision` | `decision:E-201` |
| `github:I_kwFIXdep0001` | `blocked_by` | `jira:52004` |
| `trello:6a1f000000000000000d0001` | `blocked_by` | `github:I_kwFIXdep0001` |
| `trello:6a1f000000000000000d0001` | `blocked_by` | `jira:52009` |
| `jira:52005` | `blocked_by` | `jira:52001` |
| `jira:52005` | `blocks` | `jira:52006` |
| `jira:52006` | `blocked_by` | `jira:52005` |
| `jira:52006` | `blocked_by` | `jira:52005` |
| `jira:52007` | `blocks` | `jira:52008` |
| `jira:52010` | `blocked_by` | `jira:52011` |
| `jira:52011` | `blocked_by` | `jira:52010` |
| `jira:52012` | `blocked_by` | `jira:52010` |
| `jira:52013` | `needs_decision` | `decision:E-209` |
| `jira:52026` | `blocked_by` | `jira:52013` |
| `jira:52027` | `needs_decision` | `decision:E-209` |
| `jira:52014` | `needs_decision` | `decision:E-203` |
| `jira:52015` | `blocked_by` | `jira:52014` |
| `jira:52016` | `needs_decision` | `decision:E-202` |
| `jira:52017` | `blocked_by` | `jira:52016` |
| `jira:52018` | `blocked_by` | `jira:52019` |
| `jira:52020` | `blocked_by` | `jira:52021` |
| `jira:52022` | `blocked_by` | `jira:52003` |
| `trello:6a1f000000000000000d0002` | `blocked_by` | `jira:52999` |
| `trello:6a1f000000000000000d0003` | `blocked_by` | `trello:6a1f000000000000000d0003` |
| `github:I_kwFIXdep0003` | `blocked_by` | `52001` |
| `jira:52025` | `needs_decision` | `jira:52002` |
| `github:I_kwFIXdep0002` | `needs_decision` | `decision:E-204` |
| `decision:E-203` | `blocked_by` | `jira:52015` |

Put there on purpose: two cycles, one of them through a decision; a work item and a decision that are named and have
no record; an item that names itself; a link with no system in it; a link written twice; and links written on one end only.

## The records

### jira:52001

```json
{
  "identity": "jira:52001",
  "kind": "work",
  "title": "Timetable schema",
  "status": "in_progress",
  "planned_start": "2026-11-30",
  "planned_finish": "2026-12-04",
  "blocks": [
    "jira:52002",
    "jira:52005"
  ]
}
```

### jira:52002

```json
{
  "identity": "jira:52002",
  "kind": "work",
  "title": "Import operator timetables",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-11",
  "blocked_by": [
    "jira:52001"
  ],
  "blocks": [
    "jira:52003"
  ]
}
```

### jira:52003

```json
{
  "identity": "jira:52003",
  "kind": "work",
  "title": "Search API",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-18",
  "blocked_by": [
    "jira:52002"
  ],
  "blocks": [
    "jira:52004"
  ]
}
```

### jira:52004

```json
{
  "identity": "jira:52004",
  "kind": "work",
  "title": "Search page",
  "status": "open",
  "planned_start": "2026-12-21",
  "planned_finish": "2026-12-24",
  "blocked_by": [
    "jira:52003"
  ],
  "needs_decision": [
    "decision:E-201"
  ]
}
```

### github:I_kwFIXdep0001

```json
{
  "identity": "github:I_kwFIXdep0001",
  "kind": "work",
  "title": "Mobile search screen",
  "status": "open",
  "planned_start": "2026-12-28",
  "planned_finish": "2027-01-08",
  "blocked_by": [
    "jira:52004"
  ]
}
```

### trello:6a1f000000000000000d0001

```json
{
  "identity": "trello:6a1f000000000000000d0001",
  "kind": "work",
  "title": "Release notes for search",
  "status": "open",
  "planned_start": "2027-01-11",
  "planned_finish": "2027-01-12",
  "blocked_by": [
    "github:I_kwFIXdep0001",
    "jira:52009"
  ]
}
```

### jira:52005

```json
{
  "identity": "jira:52005",
  "kind": "work",
  "title": "Fares page",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-16",
  "blocked_by": [
    "jira:52001"
  ],
  "blocks": [
    "jira:52006"
  ]
}
```

### jira:52006

```json
{
  "identity": "jira:52006",
  "kind": "work",
  "title": "Fare calculator",
  "status": "open",
  "planned_start": "2026-12-17",
  "planned_finish": "2026-12-23",
  "blocked_by": [
    "jira:52005",
    "jira:52005"
  ]
}
```

### jira:52007

```json
{
  "identity": "jira:52007",
  "kind": "work",
  "title": "Operator logo licence check",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-08",
  "blocks": [
    "jira:52008"
  ]
}
```

### jira:52008

```json
{
  "identity": "jira:52008",
  "kind": "work",
  "title": "Operator logos on results",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-09"
}
```

### jira:52009

```json
{
  "identity": "jira:52009",
  "kind": "work",
  "title": "Translate search screens",
  "status": "open",
  "planned_start": "2026-12-28",
  "planned_finish": "2027-01-06"
}
```

### jira:52010

```json
{
  "identity": "jira:52010",
  "kind": "work",
  "title": "Saved journeys",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-11",
  "blocked_by": [
    "jira:52011"
  ]
}
```

### jira:52011

```json
{
  "identity": "jira:52011",
  "kind": "work",
  "title": "Account sign-in",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-15",
  "blocked_by": [
    "jira:52010"
  ]
}
```

### jira:52012

```json
{
  "identity": "jira:52012",
  "kind": "work",
  "title": "Journey alerts",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-18",
  "blocked_by": [
    "jira:52010"
  ]
}
```

### jira:52013

```json
{
  "identity": "jira:52013",
  "kind": "work",
  "title": "Show live delays",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-14",
  "needs_decision": [
    "decision:E-209"
  ]
}
```

### jira:52026

```json
{
  "identity": "jira:52026",
  "kind": "work",
  "title": "Delay notifications",
  "status": "open",
  "planned_start": "2026-12-15",
  "planned_finish": "2026-12-18",
  "blocked_by": [
    "jira:52013"
  ]
}
```

### jira:52027

```json
{
  "identity": "jira:52027",
  "kind": "work",
  "title": "Delay history chart",
  "status": "open",
  "planned_start": "2026-12-15",
  "planned_finish": "2026-12-17",
  "needs_decision": [
    "decision:E-209"
  ]
}
```

### jira:52014

```json
{
  "identity": "jira:52014",
  "kind": "work",
  "title": "Offline timetables",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-22",
  "needs_decision": [
    "decision:E-203"
  ]
}
```

### jira:52015

```json
{
  "identity": "jira:52015",
  "kind": "work",
  "title": "Spike: how large is a full timetable download?",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-08",
  "blocked_by": [
    "jira:52014"
  ]
}
```

### jira:52016

```json
{
  "identity": "jira:52016",
  "kind": "work",
  "title": "Ticket purchase",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-18",
  "needs_decision": [
    "decision:E-202"
  ]
}
```

### jira:52017

```json
{
  "identity": "jira:52017",
  "kind": "work",
  "title": "Purchase receipts",
  "status": "open",
  "planned_start": "2026-12-21",
  "planned_finish": "2026-12-23",
  "blocked_by": [
    "jira:52016"
  ]
}
```

### jira:52018

```json
{
  "identity": "jira:52018",
  "kind": "work",
  "title": "Accessibility pass on search",
  "status": "open",
  "planned_start": "2026-12-28",
  "planned_finish": "2026-12-30",
  "blocked_by": [
    "jira:52019"
  ]
}
```

### jira:52019

```json
{
  "identity": "jira:52019",
  "kind": "work",
  "title": "Colour contrast fixes",
  "status": "done",
  "planned_start": "2026-11-23",
  "planned_finish": "2026-11-27"
}
```

### jira:52020

```json
{
  "identity": "jira:52020",
  "kind": "work",
  "title": "Port map layer",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-18",
  "blocked_by": [
    "jira:52021"
  ]
}
```

### jira:52021

```json
{
  "identity": "jira:52021",
  "kind": "work",
  "title": "Licence the port map data",
  "status": "dropped"
}
```

### jira:52022

```json
{
  "identity": "jira:52022",
  "kind": "work",
  "title": "Search analytics events",
  "status": "done",
  "planned_start": "2026-11-23",
  "planned_finish": "2026-11-25",
  "blocked_by": [
    "jira:52003"
  ]
}
```

### trello:6a1f000000000000000d0002

```json
{
  "identity": "trello:6a1f000000000000000d0002",
  "kind": "work",
  "title": "Print timetable poster",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-09",
  "blocked_by": [
    "jira:52999"
  ]
}
```

### trello:6a1f000000000000000d0003

```json
{
  "identity": "trello:6a1f000000000000000d0003",
  "kind": "work",
  "title": "Tidy the backlog board",
  "status": "open",
  "blocked_by": [
    "trello:6a1f000000000000000d0003"
  ]
}
```

### github:I_kwFIXdep0003

```json
{
  "identity": "github:I_kwFIXdep0003",
  "kind": "work",
  "title": "Cache timetable responses",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-16",
  "blocked_by": [
    "52001"
  ]
}
```

### jira:52025

```json
{
  "identity": "jira:52025",
  "kind": "work",
  "title": "Import monitoring",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-15",
  "needs_decision": [
    "jira:52002"
  ]
}
```

### github:I_kwFIXdep0002

```json
{
  "identity": "github:I_kwFIXdep0002",
  "kind": "work",
  "title": "Sign in with a ferry operator account",
  "status": "open",
  "planned_start": "2026-12-14",
  "planned_finish": "2026-12-18",
  "needs_decision": [
    "decision:E-204"
  ]
}
```

### jira:52023

```json
{
  "identity": "jira:52023",
  "kind": "work",
  "title": "Timetable PDF export, once the search API (jira:52003) is done",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-10",
  "description": "Depends on jira:52003 and cannot start before the import, jira:52002, is finished.",
  "labels": [
    "search"
  ]
}
```

### jira:52024

```json
{
  "identity": "jira:52024",
  "kind": "work",
  "title": "Schema documentation",
  "status": "open",
  "planned_start": "2026-12-07",
  "planned_finish": "2026-12-08",
  "parent": "jira:52001",
  "related": [
    "jira:52004"
  ],
  "labels": [
    "search"
  ]
}
```

### jira:52028

```json
{
  "identity": "jira:52028",
  "kind": "work",
  "title": "Epic: search",
  "status": "open",
  "parent": null,
  "related": [
    "jira:52003",
    "jira:52004",
    "github:I_kwFIXdep0001"
  ]
}
```

### decision:E-201

```json
{
  "identity": "decision:E-201",
  "kind": "decision",
  "title": "Search results are ordered by departure time",
  "status": "decided"
}
```

### decision:E-202

```json
{
  "identity": "decision:E-202",
  "kind": "decision",
  "title": "Take card payments through a payment provider's hosted page",
  "status": "proposal"
}
```

### decision:E-203

```json
{
  "identity": "decision:E-203",
  "kind": "decision",
  "title": "How much timetable data may be kept on a phone?",
  "status": "question",
  "blocked_by": [
    "jira:52015"
  ]
}
```

### decision:E-204

```json
{
  "identity": "decision:E-204",
  "kind": "decision",
  "title": "Sign-in is through operator accounts",
  "status": "superseded",
  "superseded_by": "decision:E-205"
}
```

### decision:E-205

```json
{
  "identity": "decision:E-205",
  "kind": "decision",
  "title": "Sign-in is by email link only",
  "status": "decided"
}
```

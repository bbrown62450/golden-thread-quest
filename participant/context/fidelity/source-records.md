# Source records

Written by an AI assistant (Claude) at the participant's direction, for the quest `context-preserve-source-fields`, with
`participant/skills/context-preserve-source-fields/make_source_records.py`.

**Every record here is made up.** No real project, person, customer or work item is in this file. The records are shaped like what each system's API sends: Jira
puts most of an issue inside `fields`, Trello keeps a card's place in `idList` and `pos`, GitHub writes `state` and `state_reason`. Each system has fields the
others lack.

Each record is one JSON object, one field to a line, written **as the made-up system sent it**. Some values look odd on purpose: `3.0`, `1e3`, an escape such as
`\u00e9`, a string that ends in spaces, an empty string beside a `null`, a list whose order matters. A normalizer that parsed these and wrote them out again
would change them. The check compares every record with what its normalized record rebuilds to, character for character.

## The Trello board's lists

Trello has no status. Which list means what is a person's decision, and it is written here with the data it applies to.

| List id | Name | Means |
|---|---|---|
| `61a0000000000000000000d1` | Backlog | open |
| `61a0000000000000000000d2` | Doing | in_progress |
| `61a0000000000000000000d3` | Done | done |

## The records

### jira 10042

A story in review. Its summary was sent with an escape, its points as 3.0, and its description ends in two spaces.

```json
{
  "id": "10042",
  "key": "DEMO-42",
  "self": "https://jira.example.invalid/rest/api/3/issue/10042",
  "fields": {
    "summary": "Fix the caf\u00e9 export",
    "status": {"id": "10003", "name": "In Review", "statusCategory": {"id": 4, "key": "indeterminate", "name": "In Progress"}},
    "resolution": null,
    "assignee": {"accountId": "5b10fixture0000000000ada", "displayName": "Fixture Person One", "active": true},
    "labels": ["export", "q4-2026"],
    "duedate": "2026-12-01",
    "updated": "2026-11-17T09:30:00.000+0000",
    "created": "2026-11-02T09:15:22.123+0000",
    "description": "The weekly export fails for any team with zero rows.\n\nSee the runbook.  ",
    "issuetype": {"id": "10001", "name": "Story", "subtask": false, "hierarchyLevel": 0},
    "priority": {"id": "2", "name": "High"},
    "parent": {"id": "10030", "key": "DEMO-30", "fields": {"summary": "Reporting epic"}},
    "timetracking": {"originalEstimate": "2d", "remainingEstimate": "1d 4h", "originalEstimateSeconds": 57600},
    "customfield_10016": 3.0,
    "customfield_10020": [{"id": 12, "name": "Sprint 12: exports", "state": "active"}],
    "components": [{"id": "10010", "name": "Exporter"}]
  }
}
```

### jira 10043

A story closed as "Won't Do". Nobody is assigned. Its description is an empty string, which is not the same as null, and it has no parent or components at all.

```json
{
  "id": "10043",
  "key": "DEMO-43",
  "self": "https://jira.example.invalid/rest/api/3/issue/10043",
  "fields": {
    "summary": "Schedule the Friday export",
    "status": {"id": "10001", "name": "Closed", "statusCategory": {"id": 3, "key": "done", "name": "Done"}},
    "resolution": {"id": "10002", "name": "Won't Do"},
    "assignee": null,
    "labels": [],
    "duedate": null,
    "updated": "2026-11-05T11:00:00.000+0000",
    "created": "2026-11-02T09:20:00.000+0000",
    "description": "",
    "issuetype": {"id": "10001", "name": "Story", "subtask": false, "hierarchyLevel": 0},
    "priority": {"id": "4", "name": "Low"},
    "timetracking": {},
    "customfield_10016": null,
    "customfield_10020": null
  }
}
```

### trello 62c0000000000000000000a1

A card being worked on. Its name ends in two spaces, its position is a fraction, one label has no name, and its board has a custom field for customer impact.

```json
{
  "id": "62c0000000000000000000a1",
  "idShort": 12,
  "shortLink": "fixA1b2C",
  "name": "Export report as PDF  ",
  "desc": "",
  "closed": false,
  "idBoard": "60b0000000000000000000b1",
  "idList": "61a0000000000000000000d2",
  "pos": 65535.5,
  "idMembers": ["5f0000000000000000000002", "5f0000000000000000000001"],
  "labels": [{"id": "63d0000000000000000000e1", "name": "feature", "color": "green"}, {"id": "63d0000000000000000000e2", "name": "", "color": "red"}],
  "due": "2026-12-04T17:00:00.000Z",
  "dueComplete": false,
  "dateLastActivity": "2026-11-18T20:12:04.861Z",
  "customFieldItems": [{"idCustomField": "64e0000000000000000000f1", "value": {"text": "High: 3 enterprise accounts are waiting"}}, {"idCustomField": "64e0000000000000000000f2", "value": {"number": "3.0"}}],
  "idChecklists": ["65f0000000000000000000c2", "65f0000000000000000000c1"],
  "badges": {"comments": 3, "checkItems": 3, "checkItemsChecked": 0, "description": false},
  "cover": {"color": null, "size": "normal"}
}
```

### trello 62c0000000000000000000a2

An archived card. Its position was sent in exponent form, 1e3. It has no due date, members, labels or custom fields.

```json
{
  "id": "62c0000000000000000000a2",
  "idShort": 7,
  "shortLink": "fixD3e4F",
  "name": "Spike: try a calendar view",
  "desc": "Decided against it. See card 12.",
  "closed": true,
  "idBoard": "60b0000000000000000000b1",
  "idList": "61a0000000000000000000d1",
  "pos": 1e3,
  "idMembers": [],
  "labels": [],
  "due": null,
  "dueComplete": false,
  "dateLastActivity": "2026-11-18T19:02:50.414Z",
  "customFieldItems": [],
  "idChecklists": [],
  "badges": {"comments": 0, "checkItems": 0, "checkItemsChecked": 0, "description": true},
  "cover": {"color": null, "size": "normal"}
}
```

### github I_kwFIX0201

An open issue. GitHub already writes its times in UTC to the second. It has a milestone with a due date of its own, and reactions.

```json
{
  "id": 9000201,
  "node_id": "I_kwFIX0201",
  "number": 12,
  "title": "Add retry to the webhook sender",
  "state": "open",
  "state_reason": null,
  "assignees": [{"login": "robin-fixture", "id": 9001}],
  "labels": [{"id": 7001, "name": "backend", "color": "0e8a16"}],
  "milestone": {"number": 2, "title": "Autumn", "due_on": "2026-12-15T00:00:00Z"},
  "created_at": "2026-10-03T10:00:00Z",
  "updated_at": "2026-11-02T15:00:00Z",
  "closed_at": null,
  "body": "",
  "locked": false,
  "author_association": "MEMBER",
  "reactions": {"total_count": 2, "+1": 2, "-1": 0},
  "sub_issues_summary": {"total": 0, "completed": 0, "percent_completed": 0},
  "type": null,
  "repository_url": "https://api.github.com/repos/acme-fixture/platform",
  "url": "https://api.github.com/repos/acme-fixture/platform/issues/12"
}
```

### github I_kwFIX0202

An issue closed as not planned. Its title holds quotation marks and letters outside plain ASCII, sent as they are, not as escapes.

```json
{
  "id": 9000202,
  "node_id": "I_kwFIX0202",
  "number": 13,
  "title": "Drop the \"legacy\" importer — naïve path",
  "state": "closed",
  "state_reason": "not_planned",
  "assignees": [],
  "labels": [],
  "milestone": null,
  "created_at": "2026-10-04T11:00:00Z",
  "updated_at": "2026-10-21T15:00:00Z",
  "closed_at": "2026-10-21T15:00:00Z",
  "body": "Not worth it. \ud83d\udeab",
  "locked": true,
  "author_association": "MEMBER",
  "reactions": {"total_count": 0, "+1": 0, "-1": 0},
  "sub_issues_summary": {"total": 2, "completed": 2, "percent_completed": 100},
  "type": {"id": 3, "name": "Task"},
  "repository_url": "https://api.github.com/repos/acme-fixture/platform",
  "url": "https://api.github.com/repos/acme-fixture/platform/issues/13"
}
```

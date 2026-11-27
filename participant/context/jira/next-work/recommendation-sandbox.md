# What to work on next, from the local copy of Jira project SCRUM

Written by `participant/skills/jira-next-work/rank.py rank` from a records file. Do not edit it: run it again.

**This is advice.** Nothing here was started, assigned or changed. Jira was not contacted to write this.

- Clock value: `2026-11-27T14:46:44Z`, given with `--now`. The computer's clock was not read.
- Rule: `priority-first`. The criteria, in order: priority, due, waiters, created, key. The first one on which two items differ decides between them.
- The site's priorities, in the order Jira listed them when copied, taken to be highest first: `Highest`, `High`, `Medium`, `Low`, `Lowest`.
- A copy is stale when `copied_at` is more than 24 hours before the clock value, the same limit as in `participant/context/freshness/policy.md`.
- A due date has no time of day. It is compared with the UTC date of the clock value.
- Records: 25 items. Ranked: 24. Blocked: 1. Not offered: 0.
- Items are named by key. The records hold no titles and no people.
- **Confidence is about the data, not the advice.** High means every field used was recorded and the copy is fresh. It does not mean the item is the right one to do.
- A link blocks when its type is the one named `Blocks`. The site's link types as copied: `Blocks`, `Cloners`, `Duplicate`, `Relates`.

## Start here

**`SCRUM-23`**, place 1. Confidence in the data: high.

Why this one: `priority` is `Medium`, number 3 of the site's 5; `duedate` is `2027-01-15`, 49 days after the UTC date of the clock value; `issuelinks` shows 0 open items waiting on it; `created` is `2026-11-19T21:34:26Z`.

Why it beat the next fresh item, `SCRUM-5`: they first differ on **due**. For `SCRUM-23`, `duedate` is `2027-01-15`, 49 days after the UTC date of the clock value. For `SCRUM-5`, `duedate` is not recorded.

## Already started by you

`assignee` is me and `status` is in Jira's in-progress category. `status` is not a ranking criterion, so these keep the place the criteria give them. They are listed here so that they are seen: whether to finish one before starting something new is for you to judge.

- `SCRUM-18`, place 15: `status` is `In Progress`; `issuelinks` shows 0 open items waiting on it.

## Ranked

Open, not blocked, and unassigned or assigned to me. A stale item keeps the place its recorded fields give it, with a warning.

| Place | Item | Confidence in the data | Warning |
|---|---|---|---|
| 1 | `SCRUM-23` | high | - |
| 2 | `SCRUM-5` | medium | - |
| 3 | `SCRUM-6` | medium | - |
| 4 | `SCRUM-7` | medium | - |
| 5 | `SCRUM-8` | medium | - |
| 6 | `SCRUM-9` | medium | - |
| 7 | `SCRUM-10` | medium | - |
| 8 | `SCRUM-11` | medium | - |
| 9 | `SCRUM-12` | medium | - |
| 10 | `SCRUM-13` | medium | - |
| 11 | `SCRUM-14` | medium | - |
| 12 | `SCRUM-15` | medium | - |
| 13 | `SCRUM-16` | medium | - |
| 14 | `SCRUM-17` | medium | - |
| 15 | `SCRUM-18` | medium | - |
| 16 | `SCRUM-19` | medium | - |
| 17 | `SCRUM-20` | medium | - |
| 18 | `SCRUM-21` | medium | - |
| 19 | `SCRUM-22` | medium | - |
| 20 | `SCRUM-24` | medium | - |
| 21 | `SCRUM-1` | high | - |
| 22 | `SCRUM-2` | medium | - |
| 23 | `SCRUM-3` | low | - |
| 24 | `SCRUM-4` | low | - |

### 1. `SCRUM-23`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is `2027-01-15`, 49 days after the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-19T21:34:26Z`.
- It is first because no other ranked item comes before it on `priority`, then `duedate`, then `issuelinks`, then `created`, then `key`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: high.

### 2. `SCRUM-5`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:08:59Z`.
- It is below `SCRUM-23` on **due**: for `SCRUM-23`, `duedate` is `2027-01-15`, 49 days after the UTC date of the clock value; for this one, `duedate` is not recorded. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 3. `SCRUM-6`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:09:00Z`.
- It is below `SCRUM-5` on **created**: for `SCRUM-5`, `created` is `2026-11-10T20:08:59Z`; for this one, `created` is `2026-11-10T20:09:00Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `In Progress`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 4. `SCRUM-7`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:09:01Z`.
- It is below `SCRUM-6` on **created**: for `SCRUM-6`, `created` is `2026-11-10T20:09:00Z`; for this one, `created` is `2026-11-10T20:09:01Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 5. `SCRUM-8`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:09:02Z`.
- It is below `SCRUM-7` on **created**: for `SCRUM-7`, `created` is `2026-11-10T20:09:01Z`; for this one, `created` is `2026-11-10T20:09:02Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 6. `SCRUM-9`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:10:48Z`.
- It is below `SCRUM-8` on **created**: for `SCRUM-8`, `created` is `2026-11-10T20:09:02Z`; for this one, `created` is `2026-11-10T20:10:48Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 7. `SCRUM-10`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:15:06Z`.
- It is below `SCRUM-9` on **created**: for `SCRUM-9`, `created` is `2026-11-10T20:10:48Z`; for this one, `created` is `2026-11-10T20:15:06Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 8. `SCRUM-11`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:36:36Z`.
- It is below `SCRUM-10` on **created**: for `SCRUM-10`, `created` is `2026-11-10T20:15:06Z`; for this one, `created` is `2026-11-10T20:36:36Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 9. `SCRUM-12`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:36:36Z`.
- It is below `SCRUM-11` on **key**: for `SCRUM-11`, `key` is `SCRUM-11`; for this one, `key` is `SCRUM-12`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `In Progress`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 10. `SCRUM-13`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:36:37Z`.
- It is below `SCRUM-12` on **created**: for `SCRUM-12`, `created` is `2026-11-10T20:36:36Z`; for this one, `created` is `2026-11-10T20:36:37Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 11. `SCRUM-14`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:36:38Z`.
- It is below `SCRUM-13` on **created**: for `SCRUM-13`, `created` is `2026-11-10T20:36:37Z`; for this one, `created` is `2026-11-10T20:36:38Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 12. `SCRUM-15`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:42:09Z`.
- It is below `SCRUM-14` on **created**: for `SCRUM-14`, `created` is `2026-11-10T20:36:38Z`; for this one, `created` is `2026-11-10T20:42:09Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 13. `SCRUM-16`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:44:14Z`.
- It is below `SCRUM-15` on **created**: for `SCRUM-15`, `created` is `2026-11-10T20:42:09Z`; for this one, `created` is `2026-11-10T20:44:14Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 14. `SCRUM-17`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T21:02:39Z`.
- It is below `SCRUM-16` on **created**: for `SCRUM-16`, `created` is `2026-11-10T20:44:14Z`; for this one, `created` is `2026-11-10T21:02:39Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is me; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 15. `SCRUM-18`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T21:02:40Z`.
- It is below `SCRUM-17` on **created**: for `SCRUM-17`, `created` is `2026-11-10T21:02:39Z`; for this one, `created` is `2026-11-10T21:02:40Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `In Progress`; `assignee` is me; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 16. `SCRUM-19`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T21:02:41Z`.
- It is below `SCRUM-18` on **created**: for `SCRUM-18`, `created` is `2026-11-10T21:02:40Z`; for this one, `created` is `2026-11-10T21:02:41Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is me; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 17. `SCRUM-20`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T21:02:42Z`.
- It is below `SCRUM-19` on **created**: for `SCRUM-19`, `created` is `2026-11-10T21:02:41Z`; for this one, `created` is `2026-11-10T21:02:42Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 18. `SCRUM-21`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T21:08:13Z`.
- It is below `SCRUM-20` on **created**: for `SCRUM-20`, `created` is `2026-11-10T21:02:42Z`; for this one, `created` is `2026-11-10T21:08:13Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is me; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 19. `SCRUM-22`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T21:09:14Z`.
- It is below `SCRUM-21` on **created**: for `SCRUM-21`, `created` is `2026-11-10T21:08:13Z`; for this one, `created` is `2026-11-10T21:09:14Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is me; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 20. `SCRUM-24`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-26T02:11:53Z`.
- It is below `SCRUM-22` on **created**: for `SCRUM-22`, `created` is `2026-11-10T21:09:14Z`; for this one, `created` is `2026-11-26T02:11:53Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Subtask`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 21. `SCRUM-1`

- Reason, priority: `priority` is `Low`, number 4 of the site's 5.
- Reason, due: `duedate` is `2026-12-15`, 18 days after the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 1 open item waiting on it: `SCRUM-25`.
- Reason, created: `created` is `2026-11-10T20:02:29Z`.
- It is below `SCRUM-24` on **priority**: for `SCRUM-24`, `priority` is `Medium`, number 3 of the site's 5; for this one, `priority` is `Low`, number 4 of the site's 5.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: high.

### 22. `SCRUM-2`

- Reason, priority: `priority` is not recorded.
- Reason, due: `duedate` is `2026-11-20`, OVERDUE: 7 days BEFORE the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:02:29Z`.
- It is below `SCRUM-1` on **priority**: for `SCRUM-1`, `priority` is `Low`, number 4 of the site's 5; for this one, `priority` is not recorded.
- Facts not used to rank: `status` is `In Progress`; `assignee` is nobody; `issuetype` is `Story`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `priority` is not recorded.

### 23. `SCRUM-3`

- Reason, priority: `priority` is not recorded.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:02:30Z`.
- It is below `SCRUM-2` on **due**: for `SCRUM-2`, `duedate` is `2026-11-20`, OVERDUE: 7 days BEFORE the UTC date of the clock value; for this one, `duedate` is not recorded. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `In Progress`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: low, because `priority` is not recorded; `duedate` is not recorded.

### 24. `SCRUM-4`

- Reason, priority: `priority` is not recorded.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-10T20:02:31Z`.
- It is below `SCRUM-3` on **created**: for `SCRUM-3`, `created` is `2026-11-10T20:02:30Z`; for this one, `created` is `2026-11-10T20:02:31Z`. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Subtask`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: low, because `priority` is not recorded; `duedate` is not recorded.

## Blocked

Open and not someone else's, and waiting on an item that is not done. Not ranked. In the order the rule would give them.

### `SCRUM-25`

- BLOCKED BY `SCRUM-1`: `issuelinks` says `SCRUM-25` is blocked by it, in both records. Its `status` is `To Do`, read from `SCRUM-1`'s own record, copied at `2026-11-27T14:46:44Z` and from what Jira showed of it inside `SCRUM-25`'s record, copied at `2026-11-27T14:46:44Z`.
- If it were not blocked, priority: `priority` is `Medium`, number 3 of the site's 5.
- If it were not blocked, due: `duedate` is not recorded.
- If it were not blocked, waiters: `issuelinks` shows 0 open items waiting on it.
- If it were not blocked, created: `created` is `2026-11-26T22:49:53Z`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-11-27T14:46:44Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

## Not offered

None.

## Missing fields

A missing field is never filled in. On the criterion that uses it, the item goes after every item that has a value. Each missing field lowers confidence one step.

- `SCRUM-5`: `duedate`.
- `SCRUM-6`: `duedate`.
- `SCRUM-7`: `duedate`.
- `SCRUM-8`: `duedate`.
- `SCRUM-9`: `duedate`.
- `SCRUM-10`: `duedate`.
- `SCRUM-11`: `duedate`.
- `SCRUM-12`: `duedate`.
- `SCRUM-13`: `duedate`.
- `SCRUM-14`: `duedate`.
- `SCRUM-15`: `duedate`.
- `SCRUM-16`: `duedate`.
- `SCRUM-17`: `duedate`.
- `SCRUM-18`: `duedate`.
- `SCRUM-19`: `duedate`.
- `SCRUM-20`: `duedate`.
- `SCRUM-21`: `duedate`.
- `SCRUM-22`: `duedate`.
- `SCRUM-24`: `duedate`.
- `SCRUM-2`: `priority`.
- `SCRUM-3`: `priority`, `duedate`.
- `SCRUM-4`: `priority`, `duedate`.
- `SCRUM-25`: `duedate`.

## The same records under the rule `due-first`

The criteria, in order: due, priority, waiters, created, key. Blocked and not-offered items are the same under both rules.

| Item | Place under `priority-first` | Place under `due-first` | |
|---|---|---|---|
| `SCRUM-2` | 22 | 1 | moved up |
| `SCRUM-1` | 21 | 2 | moved up |
| `SCRUM-23` | 1 | 3 | moved down |
| `SCRUM-5` | 2 | 4 | moved down |
| `SCRUM-6` | 3 | 5 | moved down |
| `SCRUM-7` | 4 | 6 | moved down |
| `SCRUM-8` | 5 | 7 | moved down |
| `SCRUM-9` | 6 | 8 | moved down |
| `SCRUM-10` | 7 | 9 | moved down |
| `SCRUM-11` | 8 | 10 | moved down |
| `SCRUM-12` | 9 | 11 | moved down |
| `SCRUM-13` | 10 | 12 | moved down |
| `SCRUM-14` | 11 | 13 | moved down |
| `SCRUM-15` | 12 | 14 | moved down |
| `SCRUM-16` | 13 | 15 | moved down |
| `SCRUM-17` | 14 | 16 | moved down |
| `SCRUM-18` | 15 | 17 | moved down |
| `SCRUM-19` | 16 | 18 | moved down |
| `SCRUM-20` | 17 | 19 | moved down |
| `SCRUM-21` | 18 | 20 | moved down |
| `SCRUM-22` | 19 | 21 | moved down |
| `SCRUM-24` | 20 | 22 | moved down |
| `SCRUM-3` | 23 | 23 | - |
| `SCRUM-4` | 24 | 24 | - |

22 items move. Start here would be `SCRUM-2`.

Why `SCRUM-2` is first under `due-first` and not under `priority-first`: `duedate` is `2026-11-20`, OVERDUE: 7 days BEFORE the UTC date of the clock value, and under `due-first` that is looked at before `priority`.

## What this does not know

- Whether a recorded priority is right, how large an item is, or who is asking.
- Anything that changed in Jira after `copied_at`. It does not refresh a copy. It says the copy is stale.
- What an item is about. No title or description is in the records.
- Whether finishing started work should come before starting new work. It lists started work and leaves that to you.

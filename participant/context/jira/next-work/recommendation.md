# What to work on next, from the local copy of Jira project DEMO

Written by `participant/skills/jira-next-work/rank.py rank` from a records file. Do not edit it: run it again.

**This is advice.** Nothing here was started, assigned or changed. Jira was not contacted to write this.

- Clock value: `2026-12-01T09:00:00Z`, given with `--now`. The computer's clock was not read.
- Rule: `priority-first`. The criteria, in order: priority, due, waiters, created, key. The first one on which two items differ decides between them.
- The site's priorities, in the order Jira listed them when copied, taken to be highest first: `Highest`, `High`, `Medium`, `Low`, `Lowest`.
- A copy is stale when `copied_at` is more than 24 hours before the clock value, the same limit as in `participant/context/freshness/policy.md`.
- A due date has no time of day. It is compared with the UTC date of the clock value.
- Records: 13 items. Ranked: 7. Blocked: 4. Not offered: 2.
- Items are named by key. The records hold no titles and no people.
- **Confidence is about the data, not the advice.** High means every field used was recorded and the copy is fresh. It does not mean the item is the right one to do.
- A link blocks when its type is the one named `Blocks`. The site's link types as copied: `Blocks`, `Relates`.

## Start here

**`DEMO-1`**, place 2. Confidence in the data: high.

It is not first on the recorded fields. Ranked above it, on copies too old to act on. **Copy these again first: they may be the better choice.**

- `DEMO-7`, place 1. STALE COPY: `copied_at` is `2026-11-20T09:00:00Z`, 11 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed since. `copied_at` is a field of the local record, not of Jira.

Why this one: `priority` is `High`, number 2 of the site's 5; `duedate` is `2026-12-04`, 3 days after the UTC date of the clock value; `issuelinks` shows 1 open item waiting on it: `DEMO-4`; `created` is `2026-11-02T09:00:00Z`.

Why it beat the next fresh item, `DEMO-2`: they first differ on **waiters**. For `DEMO-1`, `issuelinks` shows 1 open item waiting on it: `DEMO-4`. For `DEMO-2`, `issuelinks` shows 0 open items waiting on it.

Blocked items that would rank above it if they were not blocked. Unblocking one may matter more than starting this:

- `DEMO-5`: `priority` is `Highest`, number 1 of the site's 5; `duedate` is `2026-12-02`, 1 day after the UTC date of the clock value; blocked by `DEMO-3`.

## Already started by you

`assignee` is me and `status` is in Jira's in-progress category. `status` is not a ranking criterion, so these keep the place the criteria give them. They are listed here so that they are seen: whether to finish one before starting something new is for you to judge.

- `DEMO-9`, place 4: `status` is `In Progress`; `issuelinks` shows 2 open items waiting on it: `DEMO-10`, `DEMO-12`.

## Ranked

Open, not blocked, and unassigned or assigned to me. A stale item keeps the place its recorded fields give it, with a warning.

| Place | Item | Confidence in the data | Warning |
|---|---|---|---|
| 1 | `DEMO-7` | medium | STALE |
| 2 | `DEMO-1` | high | - |
| 3 | `DEMO-2` | high | - |
| 4 | `DEMO-9` | medium | - |
| 5 | `DEMO-11` | low | - |
| 6 | `DEMO-13` | high | - |
| 7 | `DEMO-8` | low | - |

### 1. `DEMO-7`

- Reason, priority: `priority` is `Highest`, number 1 of the site's 5.
- Reason, due: `duedate` is `2026-12-03`, 2 days after the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-08T09:00:00Z`.
- It is first because no other ranked item comes before it on `priority`, then `duedate`, then `issuelinks`, then `created`, then `key`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-11-20T09:00:00Z`.
- Confidence in the data: medium, because the copy is stale.
- WARNING: STALE COPY: `copied_at` is `2026-11-20T09:00:00Z`, 11 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed since. `copied_at` is a field of the local record, not of Jira.

### 2. `DEMO-1`

- Reason, priority: `priority` is `High`, number 2 of the site's 5.
- Reason, due: `duedate` is `2026-12-04`, 3 days after the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 1 open item waiting on it: `DEMO-4`.
- Reason, created: `created` is `2026-11-02T09:00:00Z`.
- It is below `DEMO-7` on **priority**: for `DEMO-7`, `priority` is `Highest`, number 1 of the site's 5; for this one, `priority` is `High`, number 2 of the site's 5.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: high.

### 3. `DEMO-2`

- Reason, priority: `priority` is `High`, number 2 of the site's 5.
- Reason, due: `duedate` is `2026-12-04`, 3 days after the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-03T09:00:00Z`.
- It is below `DEMO-1` on **waiters**: for `DEMO-1`, `issuelinks` shows 1 open item waiting on it: `DEMO-4`; for this one, `issuelinks` shows 0 open items waiting on it. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: high.

### 4. `DEMO-9`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 2 open items waiting on it: `DEMO-10`, `DEMO-12`.
- Reason, created: `created` is `2026-11-10T09:00:00Z`.
- It is below `DEMO-2` on **priority**: for `DEMO-2`, `priority` is `High`, number 2 of the site's 5; for this one, `priority` is `Medium`, number 3 of the site's 5.
- Facts not used to rank: `status` is `In Progress`; `assignee` is me; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: medium, because `duedate` is not recorded.

### 5. `DEMO-11`

- Reason, priority: `priority` is `Medium`, number 3 of the site's 5.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is not recorded.
- It is below `DEMO-9` on **waiters**: for `DEMO-9`, `issuelinks` shows 2 open items waiting on it: `DEMO-10`, `DEMO-12`; for this one, `issuelinks` shows 0 open items waiting on it. Every earlier criterion was equal, so this is the tie-break.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: low, because `duedate` is not recorded; `created` is not recorded.

### 6. `DEMO-13`

- Reason, priority: `priority` is `Low`, number 4 of the site's 5.
- Reason, due: `duedate` is `2026-11-30`, OVERDUE: 1 day BEFORE the UTC date of the clock value.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-14T09:00:00Z`.
- It is below `DEMO-11` on **priority**: for `DEMO-11`, `priority` is `Medium`, number 3 of the site's 5; for this one, `priority` is `Low`, number 4 of the site's 5.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: high.

### 7. `DEMO-8`

- Reason, priority: `priority` is not recorded.
- Reason, due: `duedate` is not recorded.
- Reason, waiters: `issuelinks` shows 0 open items waiting on it.
- Reason, created: `created` is `2026-11-09T09:00:00Z`.
- It is below `DEMO-13` on **priority**: for `DEMO-13`, `priority` is `Low`, number 4 of the site's 5; for this one, `priority` is not recorded.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: low, because `priority` is not recorded; `duedate` is not recorded.

## Blocked

Open and not someone else's, and waiting on an item that is not done. Not ranked. In the order the rule would give them.

### `DEMO-5`

- BLOCKED BY `DEMO-3`: `issuelinks` says `DEMO-5` is blocked by it, in both records. Its `status` is `In Progress`, read from `DEMO-3`'s own record, copied at `2026-12-01T08:00:00Z` and from what Jira showed of it inside `DEMO-5`'s record, copied at `2026-12-01T08:00:00Z`.
- If it were not blocked, priority: `priority` is `Highest`, number 1 of the site's 5.
- If it were not blocked, due: `duedate` is `2026-12-02`, 1 day after the UTC date of the clock value.
- If it were not blocked, waiters: `issuelinks` shows 0 open items waiting on it.
- If it were not blocked, created: `created` is `2026-11-06T09:00:00Z`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: high.

### `DEMO-4`

- BLOCKED BY `DEMO-1`: `issuelinks` says `DEMO-4` is blocked by it, in both records. Its `status` is `To Do`, read from `DEMO-1`'s own record, copied at `2026-12-01T08:00:00Z` and from what Jira showed of it inside `DEMO-4`'s record, copied at `2026-12-01T08:00:00Z`.
- If it were not blocked, priority: `priority` is `Medium`, number 3 of the site's 5.
- If it were not blocked, due: `duedate` is `2026-12-10`, 9 days after the UTC date of the clock value.
- If it were not blocked, waiters: `issuelinks` shows 0 open items waiting on it.
- If it were not blocked, created: `created` is `2026-11-05T09:00:00Z`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: high.

### `DEMO-12`

- BLOCKED BY `DEMO-9`: `issuelinks` in `DEMO-9`'s record says it blocks `DEMO-12`. `DEMO-12`'s own record, copied earlier, does not show the link. Its `status` is `In Progress`, read from `DEMO-9`'s own record, copied at `2026-12-01T08:00:00Z`.
- If it were not blocked, priority: `priority` is `Medium`, number 3 of the site's 5.
- If it were not blocked, due: `duedate` is not recorded.
- If it were not blocked, waiters: `issuelinks` shows 0 open items waiting on it.
- If it were not blocked, created: `created` is `2026-11-13T09:00:00Z`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-11-20T09:00:00Z`.
- Confidence in the data: low, because `duedate` is not recorded; the copy is stale.
- WARNING: STALE COPY: `copied_at` is `2026-11-20T09:00:00Z`, 11 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed since. `copied_at` is a field of the local record, not of Jira.

### `DEMO-10`

- BLOCKED BY `DEMO-9`: `issuelinks` says `DEMO-10` is blocked by it, in both records. Its `status` is `In Progress`, read from `DEMO-9`'s own record, copied at `2026-12-01T08:00:00Z` and from what Jira showed of it inside `DEMO-10`'s record, copied at `2026-12-01T08:00:00Z`.
- If it were not blocked, priority: `priority` is `Low`, number 4 of the site's 5.
- If it were not blocked, due: `duedate` is `2026-12-20`, 19 days after the UTC date of the clock value.
- If it were not blocked, waiters: `issuelinks` shows 0 open items waiting on it.
- If it were not blocked, created: `created` is `2026-11-11T09:00:00Z`.
- Facts not used to rank: `status` is `To Do`; `assignee` is nobody; `issuetype` is `Task`; `copied_at` is `2026-12-01T08:00:00Z`.
- Confidence in the data: high.

## Not offered

- `DEMO-3`: `assignee` is someone else.
- `DEMO-6`: `status` is `Done`, which Jira puts in its "done" category.

## Missing fields

A missing field is never filled in. On the criterion that uses it, the item goes after every item that has a value. Each missing field lowers confidence one step.

- `DEMO-9`: `duedate`.
- `DEMO-11`: `duedate`, `created`.
- `DEMO-8`: `priority`, `duedate`.
- `DEMO-12`: `duedate`.

## The same records under the rule `due-first`

The criteria, in order: due, priority, waiters, created, key. Blocked and not-offered items are the same under both rules.

| Item | Place under `priority-first` | Place under `due-first` | |
|---|---|---|---|
| `DEMO-13` | 6 | 1 | moved up |
| `DEMO-7` | 1 | 2 | moved down |
| `DEMO-1` | 2 | 3 | moved down |
| `DEMO-2` | 3 | 4 | moved down |
| `DEMO-9` | 4 | 5 | moved down |
| `DEMO-11` | 5 | 6 | moved down |
| `DEMO-8` | 7 | 7 | - |

6 items move. Start here would be `DEMO-13`.

Why `DEMO-13` is first under `due-first` and not under `priority-first`: `duedate` is `2026-11-30`, OVERDUE: 1 day BEFORE the UTC date of the clock value, and under `due-first` that is looked at before `priority`.

## What this does not know

- Whether a recorded priority is right, how large an item is, or who is asking.
- Anything that changed in Jira after `copied_at`. It does not refresh a copy. It says the copy is stale.
- What an item is about. No title or description is in the records.
- Whether finishing started work should come before starting new work. It lists started work and leaves that to you.

# What to work on next

Written by `participant/skills/context-next-work/rank.py rank` from `inputs.md`. Do not edit it: run it again. The
data is made up.

**This is advice.** Nothing here was started, assigned or changed, and no record was written to.

- Clock value: `2026-12-01T09:00:00Z`, from the inputs. The computer's clock was not read.
- Rule: `priority-first`. The criteria, in order: priority, due, waiters, created, identity. The first one on which two items differ decides between them.
- A work item's local copy is stale when it was retrieved more than 24 hours before the clock value. That limit is
  read from `participant/context/freshness/policy.md`.
- Records: 22 work items. Ranked: 13. Blocked: 6. Not offered: 3.

## Start here

**`jira:61001` "Allergen labels on the menu"**, place 2, confidence high.

It is not first on the recorded fields. Ranked above it, and not to be started without a refresh:

- `jira:61004` "Weekly menu import", place 1. STALE CONTEXT: `retrieved_at` is `2026-11-24T08:00:00Z`, 7 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed. Refresh it before relying on this.

Why this one: `priority` is `high`; `due` is `2026-12-03`, 2 days after the clock value; 2 open items wait on it: `jira:61005` (`blocked_by` on `jira:61005`, `blocks` on `jira:61001`); `jira:61009` (`blocked_by` on `jira:61009`, `blocks` on `jira:61001`); `created` is `2026-11-10`.

## Ranked

Open, not blocked, and nobody has it. A stale item keeps the place its recorded fields give it, with a warning.

| Place | Item | Confidence | Warning |
|---|---|---|---|
| 1 | `jira:61004` "Weekly menu import" | medium | STALE |
| 2 | `jira:61001` "Allergen labels on the menu" | high | - |
| 3 | `jira:61002` "Parents can cancel an order" | high | - |
| 4 | `jira:61018` "Payment provider contract check" | medium | STALE |
| 5 | `jira:61003` "Receipt email" | high | - |
| 6 | `trello:7b2e000000000000000e0001` "Order cut-off time setting" | medium | - |
| 7 | `jira:61006` "Kitchen printout" | high | - |
| 8 | `jira:61007` "Export orders to CSV" | high | - |
| 9 | `jira:61016` "Translate the order page" | medium | STALE |
| 10 | `jira:61019` "Free school meals flag" | high | - |
| 11 | `jira:61015` "Menu photo upload" | medium | - |
| 12 | `jira:61008` "Low balance reminder" | high | - |
| 13 | `trello:7b2e000000000000000e0002` "Tidy up the help page" | low | - |

### 1. `jira:61004` "Weekly menu import"

- Reason, priority: `priority` is `high`.
- Reason, due: `due` is `2026-12-02`, 1 day after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-08`.
- It is first because no other ranked item comes before it on priority, then due, then waiters, then created.
- Confidence: medium, because the copy is stale.
- WARNING: STALE CONTEXT: `retrieved_at` is `2026-11-24T08:00:00Z`, 7 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed. Refresh it before relying on this.
- Not used: `votes` is 1.

### 2. `jira:61001` "Allergen labels on the menu"

- Reason, priority: `priority` is `high`.
- Reason, due: `due` is `2026-12-03`, 2 days after the clock value.
- Reason, waiters: 2 open items wait on it: `jira:61005` (`blocked_by` on `jira:61005`, `blocks` on `jira:61001`); `jira:61009` (`blocked_by` on `jira:61009`, `blocks` on `jira:61001`).
- Reason, created: `created` is `2026-11-10`.
- Placed below `jira:61004` by due: `due` is `2026-12-03`, 2 days after the clock value, and for `jira:61004` `due` is `2026-12-02`, 1 day after the clock value.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 4.

### 3. `jira:61002` "Parents can cancel an order"

- Reason, priority: `priority` is `high`.
- Reason, due: `due` is `2026-12-03`, 2 days after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-12`.
- Placed below `jira:61001` by waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it, and for `jira:61001` 2 open items wait on it: `jira:61005` (`blocked_by` on `jira:61005`, `blocks` on `jira:61001`); `jira:61009` (`blocked_by` on `jira:61009`, `blocks` on `jira:61001`).
- Why it is not first: due decides against `jira:61004`. `due` is `2026-12-03`, 2 days after the clock value, and for `jira:61004` `due` is `2026-12-02`, 1 day after the clock value.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 2.

### 4. `jira:61018` "Payment provider contract check"

- Reason, priority: `priority` is `high`.
- Reason, due: `due` is `2026-12-04`, 3 days after the clock value.
- Reason, waiters: 1 open item waits on it: `jira:61017` (`blocked_by` on `jira:61017`).
- Reason, created: `created` is `2026-11-09`.
- Placed below `jira:61002` by due: `due` is `2026-12-04`, 3 days after the clock value, and for `jira:61002` `due` is `2026-12-03`, 2 days after the clock value.
- Why it is not first: due decides against `jira:61004`. `due` is `2026-12-04`, 3 days after the clock value, and for `jira:61004` `due` is `2026-12-02`, 1 day after the clock value.
- Confidence: medium, because the copy is stale.
- WARNING: STALE CONTEXT: `retrieved_at` is `2026-11-20T10:00:00Z`, 10 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed. Refresh it before relying on this.
- Not used: `votes` is 0.

### 5. `jira:61003` "Receipt email"

- Reason, priority: `priority` is `high`.
- Reason, due: `due` is `2026-12-10`, 9 days after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-14`.
- Placed below `jira:61018` by due: `due` is `2026-12-10`, 9 days after the clock value, and for `jira:61018` `due` is `2026-12-04`, 3 days after the clock value.
- Why it is not first: due decides against `jira:61004`. `due` is `2026-12-10`, 9 days after the clock value, and for `jira:61004` `due` is `2026-12-02`, 1 day after the clock value.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 0.

### 6. `trello:7b2e000000000000000e0001` "Order cut-off time setting"

- Reason, priority: `priority` is `high`.
- Reason, due: `due` is not recorded. It is placed after every item that has one.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-23`.
- Placed below `jira:61003` by due: `due` is not recorded. It is placed after every item that has one, and for `jira:61003` `due` is `2026-12-10`, 9 days after the clock value.
- Why it is not first: due decides against `jira:61004`. `due` is not recorded. It is placed after every item that has one, and for `jira:61004` `due` is `2026-12-02`, 1 day after the clock value.
- Confidence: medium, because `due` is missing.
- Not used: `votes` is 1.

### 7. `jira:61006` "Kitchen printout"

- Reason, priority: `priority` is `medium`.
- Reason, due: `due` is `2026-12-05`, 4 days after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-15`.
- Placed below `trello:7b2e000000000000000e0001` by priority: `priority` is `medium`, and for `trello:7b2e000000000000000e0001` `priority` is `high`.
- Why it is not first: priority decides against `jira:61004`. `priority` is `medium`, and for `jira:61004` `priority` is `high`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 1.

### 8. `jira:61007` "Export orders to CSV"

- Reason, priority: `priority` is `medium`.
- Reason, due: `due` is `2026-12-05`, 4 days after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-15`.
- Placed below `jira:61006` by identity: `identity` is `jira:61007`, and for `jira:61006` `identity` is `jira:61006`.
- Why it is not first: priority decides against `jira:61004`. `priority` is `medium`, and for `jira:61004` `priority` is `high`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 6.

### 9. `jira:61016` "Translate the order page"

- Reason, priority: `priority` is `medium`.
- Reason, due: `due` is `2026-12-05`, 4 days after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-18`.
- Placed below `jira:61007` by created: `created` is `2026-11-18`, and for `jira:61007` `created` is `2026-11-15`.
- Why it is not first: priority decides against `jira:61004`. `priority` is `medium`, and for `jira:61004` `priority` is `high`.
- Confidence: medium, because the copy is stale.
- WARNING: STALE CONTEXT: `retrieved_at` is not recorded, so the copy cannot be shown to be fresh. Its status, its blockers and who has it may have changed. Refresh it before relying on this.
- Not used: `votes` is 0.

### 10. `jira:61019` "Free school meals flag"

- Reason, priority: `priority` is `medium`.
- Reason, due: `due` is `2026-12-09`, 8 days after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-22`.
- Placed below `jira:61016` by due: `due` is `2026-12-09`, 8 days after the clock value, and for `jira:61016` `due` is `2026-12-05`, 4 days after the clock value.
- Why it is not first: priority decides against `jira:61004`. `priority` is `medium`, and for `jira:61004` `priority` is `high`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 2.

### 11. `jira:61015` "Menu photo upload"

- Reason, priority: `priority` is `medium`.
- Reason, due: `due` is `"soon"`, which is not a date. It is placed after every item that has one.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-20`.
- Placed below `jira:61019` by due: `due` is `"soon"`, which is not a date. It is placed after every item that has one, and for `jira:61019` `due` is `2026-12-09`, 8 days after the clock value.
- Why it is not first: priority decides against `jira:61004`. `priority` is `medium`, and for `jira:61004` `priority` is `high`.
- Confidence: medium, because `due` is missing.
- Not used: `votes` is 1.

### 12. `jira:61008` "Low balance reminder"

- Reason, priority: `priority` is `low`.
- Reason, due: `due` is `2026-12-02`, 1 day after the clock value.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-18`.
- Placed below `jira:61015` by priority: `priority` is `low`, and for `jira:61015` `priority` is `medium`.
- Why it is not first: priority decides against `jira:61004`. `priority` is `low`, and for `jira:61004` `priority` is `high`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 5.

### 13. `trello:7b2e000000000000000e0002` "Tidy up the help page"

- Reason, priority: `priority` is not recorded. It is placed after every item that has one.
- Reason, due: `due` is not recorded. It is placed after every item that has one.
- Reason, waiters: 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it.
- Reason, created: `created` is `2026-11-01`.
- Placed below `jira:61008` by priority: `priority` is not recorded. It is placed after every item that has one, and for `jira:61008` `priority` is `low`.
- Why it is not first: priority decides against `jira:61004`. `priority` is not recorded. It is placed after every item that has one, and for `jira:61004` `priority` is `high`.
- Confidence: low, because `priority` is missing; `due` is missing.
- Not used: `votes` is 0.

## Not recommended: blocked

Each of these waits on something that is not finished. They are not ranked, because an order among blocked items
says nothing about what can be done now. They are listed in the order the rule would give them.

### `jira:61010` "Pay by voucher"

- BLOCKED BY `decision:E-301` "Are vouchers accepted for part of an order?", which is a decision whose `status` is `question`. Recorded in `needs_decision` on `jira:61010`.
- If unblocked, it would be ranked on: `priority` is `high`; `due` is `2026-12-04`, 3 days after the clock value; 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it; `created` is `2026-11-11`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 8.

### `jira:61017` "Refund flow"

- BLOCKED BY `jira:61018` "Payment provider contract check", which is a work item whose `status` is `open`. Its own copy is stale (`retrieved_at` is `2026-11-20T10:00:00Z`, 10 days before the clock value. The limit is 24 hours), so this item may no longer be blocked. Recorded in `blocked_by` on `jira:61017`.
- If unblocked, it would be ranked on: `priority` is `medium`; `due` is `2026-12-06`, 5 days after the clock value; 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it; `created` is `2026-11-21`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 9.

### `jira:61014` "Sibling discount"

- BLOCKED BY `jira:61099` (no record), which has no record, so it cannot be shown to be finished. Recorded in `blocked_by` on `jira:61014`.
- If unblocked, it would be ranked on: `priority` is `medium`; `due` is `2026-12-07`, 6 days after the clock value; 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it; `created` is `2026-11-19`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 7.

### `jira:61005` "Allergen filter"

- BLOCKED BY `jira:61001` "Allergen labels on the menu", which is a work item whose `status` is `open`. Recorded in `blocked_by` on `jira:61005` and `blocks` on `jira:61001`.
- If unblocked, it would be ranked on: `priority` is `medium`; `due` is `2026-12-08`, 7 days after the clock value; 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it; `created` is `2026-11-16`.
- Confidence: high, because every field the ranking reads is recorded, and the copy is fresh.
- Not used: `votes` is 3.

### `github:I_kwFIXnw00001` "Dark mode"

- BLOCKED BY `jira:61012` "Design tokens", which is a work item whose `status` is `in_progress`. Recorded in `blocked_by` on `github:I_kwFIXnw00001` and `blocks` on `jira:61012`.
- If unblocked, it would be ranked on: `priority` is `low`; `due` is `2026-12-20`, 19 days after the clock value; 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it; `created` is `2026-10-01`.
- Confidence: medium, because the copy is stale.
- WARNING: STALE CONTEXT: `retrieved_at` is `2026-11-24T08:00:00Z`, 7 days before the clock value. The limit is 24 hours. Its status, its blockers and who has it may have changed. Refresh it before relying on this.
- Not used: `votes` is 57.

### `jira:61009` "Allergen report for the kitchen"

- BLOCKED BY `jira:61001` "Allergen labels on the menu", which is a work item whose `status` is `open`. Recorded in `blocked_by` on `jira:61009` and `blocks` on `jira:61001`.
- If unblocked, it would be ranked on: `priority` is not recorded. It is placed after every item that has one; `due` is `2026-12-09`, 8 days after the clock value; 0 open items wait on it. `blocks` names none, and no open item's `blocked_by` names it; `created` is `2026-11-17`.
- Confidence: medium, because `priority` is missing.
- Not used: `votes` is 0.

## Not offered

Finished, under way, or somebody already has it.

- `jira:61011` "Term dates in the calendar": `assigned_to` is `Developer B`.
- `jira:61012` "Design tokens": `status` is `in_progress`.
- `jira:61013` "Remove the old login page": `status` is `done`.

## Seen and not used: votes

`votes` is recorded and plays no part in the ranking. Popularity is not priority. The five items with the most
votes, and where each one is:

| Votes | Item | Where it is |
|---|---|---|
| 57 | `github:I_kwFIXnw00001` "Dark mode" | blocked by `jira:61012`, and its copy is stale |
| 9 | `jira:61017` "Refund flow" | blocked by `jira:61018` |
| 8 | `jira:61010` "Pay by voucher" | blocked by `decision:E-301` |
| 7 | `jira:61014` "Sibling discount" | blocked by `jira:61099` |
| 6 | `jira:61007` "Export orders to CSV" | place 8 |

## To disagree with a place

Each reason above names the field it came from. Change that field in the record and run the ranking again.

| If you think | Change |
|---|---|
| it matters more or less than its place says | `priority` on the item |
| it is more or less urgent | `due` on the item |
| more or fewer things wait on it | `blocks` on the item, or `blocked_by` on the items that wait |
| it is not really blocked | `blocked_by` or `needs_decision` on the item, or the `status` of what it waits on |
| the copy is fine | fetch the record again, so that `retrieved_at` is new. Do not edit `retrieved_at` by hand |
| the whole order is wrong | the rule. `--rule due-first` puts the due date before priority |

# Dependency index

Written by `participant/skills/context-dependency-map/depmap.py build` from `data.md`. Do not edit it: build it again.
The data is made up.

A link is read from three fields only: `blocked_by`, `blocks` and `needs_decision`. A decision is an item like any
other. Nothing is read from a title, a description, a label, a parent or a `related` field.

## Summary

- Records: 39 (34 work items, 5 decisions). Named in a link and not found: 2.
- Links: 28. Still holding something up: 26.
- Problems reported below: 16.

## Problems

### Cycles: items that wait on each other

- **CYCLE of 3:** `decision:E-203` "How much timetable data may be kept on a phone?", `jira:52014` "Offline timetables", `jira:52015` "Spike: how large is a full timetable download?". One way round: `decision:E-203` waits on `jira:52015` waits on `jira:52014` waits on `decision:E-203`.
- **CYCLE of 2:** `jira:52010` "Saved journeys", `jira:52011` "Account sign-in". One way round: `jira:52010` waits on `jira:52011` waits on `jira:52010`.

### An item that waits on itself

- **SELF:** `trello:6a1f000000000000000d0003` "Tidy the backlog board" names itself (`blocked_by` on `trello:6a1f000000000000000d0003`).

### Links to something that has no record

- **NOT FOUND:** `decision:E-209` has no record. Named by: `jira:52013` "Show live delays" (`needs_decision` on `jira:52013`); `jira:52027` "Delay history chart" (`needs_decision` on `jira:52027`).
- **NOT FOUND:** `jira:52999` has no record. Named by: `trello:6a1f000000000000000d0002` "Print timetable poster" (`blocked_by` on `trello:6a1f000000000000000d0002`).

### Links that could not be read

- **UNREADABLE:** `blocked_by` on `github:I_kwFIXdep0003` "Cache timetable responses" holds `"52001"`: it is not an identity, so nothing is guessed from it.

### Waiting on a decision that has not been made

- **NOT DECIDED:** `jira:52014` "Offline timetables" waits on `decision:E-203` "How much timetable data may be kept on a phone?", which is a question.
- **NOT DECIDED:** `jira:52016` "Ticket purchase" waits on `decision:E-202` "Take card payments through a payment provider's hosted page", which is a proposal.

### Waiting on something dropped or superseded

- **WILL NEVER FINISH:** `github:I_kwFIXdep0002` "Sign in with a ferry operator account" waits on `decision:E-204` "Sign-in is through operator accounts", which is superseded by `decision:E-205`.
- **WILL NEVER FINISH:** `jira:52020` "Port map layer" waits on `jira:52021` "Licence the port map data", which is dropped.

### `needs_decision` that names something other than a decision

- **NOT A DECISION:** `jira:52025` "Import monitoring" names `jira:52002` "Import operator timetables" in `needs_decision`. The link is kept.

### Finished while what it waited on is not

- **OUT OF ORDER:** `jira:52022` "Search analytics events" is finished, and `jira:52003` "Search API" is not.

### Planned to start before what it waits on is planned to finish

- **TOO EARLY:** `jira:52008` "Operator logos on results" is planned to start on 2026-12-07. It waits on `jira:52007` "Operator logo licence check", planned to finish on 2026-12-08.
- **TOO EARLY:** `jira:52010` "Saved journeys" is planned to start on 2026-12-07. It waits on `jira:52011` "Account sign-in", planned to finish on 2026-12-15.
- **TOO EARLY:** `jira:52011` "Account sign-in" is planned to start on 2026-12-07. It waits on `jira:52010` "Saved journeys", planned to finish on 2026-12-11.
- **TOO EARLY:** `jira:52015` "Spike: how large is a full timetable download?" is planned to start on 2026-12-07. It waits on `jira:52014` "Offline timetables", planned to finish on 2026-12-22.

## The 5 items blocking the most

An item blocks every item still to do that cannot finish until it is done: those waiting on it, those waiting on
them, and so on. An item that is done blocks nothing. Equal totals are ordered by the direct count, then by identity.

| Place | Item | Blocks in all | Of those, directly | Note |
|---|---|---|---|---|
| 1 | `jira:52001` "Timetable schema" | 8 | 2 | - |
| 2 | `jira:52002` "Import operator timetables" | 5 | 2 | - |
| 3 | `decision:E-209` (no record) | 3 | 2 | NOT FOUND |
| 4 | `jira:52003` "Search API" | 3 | 1 | - |
| 5 | `jira:52010` "Saved journeys" | 2 | 2 | in a cycle |

6 more items have the same total as fifth place and are not listed: `decision:E-202`, `decision:E-203`, `jira:52004`, `jira:52011`, `jira:52014`, `jira:52015`.

## The longest chain

The longest run of items still to do in which each waits on the next. Chains through a cycle are left out, since a
cycle has no end.

6 items, each waiting on the next:

1. `trello:6a1f000000000000000d0001` "Release notes for search"
2. `github:I_kwFIXdep0001` "Mobile search screen"
3. `jira:52004` "Search page"
4. `jira:52003` "Search API"
5. `jira:52002` "Import operator timetables"
6. `jira:52001` "Timetable schema"

## If one item slips

If `jira:52001` "Timetable schema" finishes 5 days later than planned, this is what happens to everything it blocks. Dates are calendar
days. An item moves only as far as it must. `depmap.py slip IDENTITY DAYS` does the same for any item.

| Item | Earliest start now | Earliest start after the slip | Pushed by |
|---|---|---|---|
| `github:I_kwFIXdep0001` "Mobile search screen" | 2026-12-28 | 2026-12-28 | 0 days |
| `jira:52002` "Import operator timetables" | 2026-12-07 | 2026-12-10 | 3 days |
| `jira:52003` "Search API" | 2026-12-14 | 2026-12-15 | 1 day |
| `jira:52004` "Search page" | 2026-12-21 | 2026-12-21 | 0 days |
| `jira:52005` "Fares page" | 2026-12-07 | 2026-12-10 | 3 days |
| `jira:52006` "Fare calculator" | 2026-12-17 | 2026-12-20 | 3 days |
| `jira:52025` "Import monitoring" | 2026-12-14 | 2026-12-15 | 1 day |
| `trello:6a1f000000000000000d0001` "Release notes for search" | 2027-01-11 | 2027-01-11 | 0 days |

## Forward index: what each item waits on

For each item, everything it waits on, whether that still holds it up, and the field the link was read from.

### `decision:E-201` "Search results are ordered by departure time"

Status: decided.
- Nothing.

### `decision:E-202` "Take card payments through a payment provider's hosted page"

Status: proposal.
- Nothing.

### `decision:E-203` "How much timetable data may be kept on a phone?"

Status: question.
- Waits on `jira:52015` "Spike: how large is a full timetable download?". waiting. From `blocked_by` on `decision:E-203`.

### `decision:E-204` "Sign-in is through operator accounts"

Status: superseded.
- Nothing.

### `decision:E-205` "Sign-in is by email link only"

Status: decided.
- Nothing.

### `decision:E-209` (no record)

**NOT FOUND: nothing in the data has this identity.**
- Nothing.

### `github:I_kwFIXdep0001` "Mobile search screen"

Status: open.
- Waits on `jira:52004` "Search page". waiting. From `blocked_by` on `github:I_kwFIXdep0001`.

### `github:I_kwFIXdep0002` "Sign in with a ferry operator account"

Status: open.
- Waits on `decision:E-204` "Sign-in is through operator accounts". DROPPED OR SUPERSEDED. From `needs_decision` on `github:I_kwFIXdep0002`.

### `github:I_kwFIXdep0003` "Cache timetable responses"

Status: open.
- Nothing.

### `jira:52001` "Timetable schema"

Status: in_progress.
- Nothing.

### `jira:52002` "Import operator timetables"

Status: open.
- Waits on `jira:52001` "Timetable schema". waiting. From `blocked_by` on `jira:52002`; `blocks` on `jira:52001`.

### `jira:52003` "Search API"

Status: open.
- Waits on `jira:52002` "Import operator timetables". waiting. From `blocked_by` on `jira:52003`; `blocks` on `jira:52002`.

### `jira:52004` "Search page"

Status: open.
- Waits on `decision:E-201` "Search results are ordered by departure time". satisfied. From `needs_decision` on `jira:52004`.
- Waits on `jira:52003` "Search API". waiting. From `blocked_by` on `jira:52004`; `blocks` on `jira:52003`.

### `jira:52005` "Fares page"

Status: open.
- Waits on `jira:52001` "Timetable schema". waiting. From `blocked_by` on `jira:52005`; `blocks` on `jira:52001`.

### `jira:52006` "Fare calculator"

Status: open.
- Waits on `jira:52005` "Fares page". waiting. From `blocked_by` on `jira:52006`; `blocks` on `jira:52005`.

### `jira:52007` "Operator logo licence check"

Status: open.
- Nothing.

### `jira:52008` "Operator logos on results"

Status: open.
- Waits on `jira:52007` "Operator logo licence check". waiting. From `blocks` on `jira:52007`.

### `jira:52009` "Translate search screens"

Status: open.
- Nothing.

### `jira:52010` "Saved journeys"

Status: open.
- Waits on `jira:52011` "Account sign-in". waiting. From `blocked_by` on `jira:52010`.

### `jira:52011` "Account sign-in"

Status: open.
- Waits on `jira:52010` "Saved journeys". waiting. From `blocked_by` on `jira:52011`.

### `jira:52012` "Journey alerts"

Status: open.
- Waits on `jira:52010` "Saved journeys". waiting. From `blocked_by` on `jira:52012`.

### `jira:52013` "Show live delays"

Status: open.
- Waits on `decision:E-209` (no record). NOT FOUND. From `needs_decision` on `jira:52013`.

### `jira:52014` "Offline timetables"

Status: open.
- Waits on `decision:E-203` "How much timetable data may be kept on a phone?". NOT DECIDED. From `needs_decision` on `jira:52014`.

### `jira:52015` "Spike: how large is a full timetable download?"

Status: open.
- Waits on `jira:52014` "Offline timetables". waiting. From `blocked_by` on `jira:52015`.

### `jira:52016` "Ticket purchase"

Status: open.
- Waits on `decision:E-202` "Take card payments through a payment provider's hosted page". NOT DECIDED. From `needs_decision` on `jira:52016`.

### `jira:52017` "Purchase receipts"

Status: open.
- Waits on `jira:52016` "Ticket purchase". waiting. From `blocked_by` on `jira:52017`.

### `jira:52018` "Accessibility pass on search"

Status: open.
- Waits on `jira:52019` "Colour contrast fixes". satisfied. From `blocked_by` on `jira:52018`.

### `jira:52019` "Colour contrast fixes"

Status: done.
- Nothing.

### `jira:52020` "Port map layer"

Status: open.
- Waits on `jira:52021` "Licence the port map data". DROPPED OR SUPERSEDED. From `blocked_by` on `jira:52020`.

### `jira:52021` "Licence the port map data"

Status: dropped.
- Nothing.

### `jira:52022` "Search analytics events"

Status: done.
- Waits on `jira:52003` "Search API". waiting. From `blocked_by` on `jira:52022`.

### `jira:52023` "Timetable PDF export, once the search API (jira:52003) is done"

Status: open.
- Nothing.

### `jira:52024` "Schema documentation"

Status: open.
- Nothing.

### `jira:52025` "Import monitoring"

Status: open.
- Waits on `jira:52002` "Import operator timetables". waiting. From `needs_decision` on `jira:52025`.

### `jira:52026` "Delay notifications"

Status: open.
- Waits on `jira:52013` "Show live delays". waiting. From `blocked_by` on `jira:52026`.

### `jira:52027` "Delay history chart"

Status: open.
- Waits on `decision:E-209` (no record). NOT FOUND. From `needs_decision` on `jira:52027`.

### `jira:52028` "Epic: search"

Status: open.
- Nothing.

### `jira:52999` (no record)

**NOT FOUND: nothing in the data has this identity.**
- Nothing.

### `trello:6a1f000000000000000d0001` "Release notes for search"

Status: open.
- Waits on `github:I_kwFIXdep0001` "Mobile search screen". waiting. From `blocked_by` on `trello:6a1f000000000000000d0001`.
- Waits on `jira:52009` "Translate search screens". waiting. From `blocked_by` on `trello:6a1f000000000000000d0001`.

### `trello:6a1f000000000000000d0002` "Print timetable poster"

Status: open.
- Waits on `jira:52999` (no record). NOT FOUND. From `blocked_by` on `trello:6a1f000000000000000d0002`.

### `trello:6a1f000000000000000d0003` "Tidy the backlog board"

Status: open.
- Waits on `trello:6a1f000000000000000d0003` "Tidy the backlog board". waiting. From `blocked_by` on `trello:6a1f000000000000000d0003`.

## Reverse index: what waits on each item

For each item, everything waiting on it. This is the answer to "who is waiting on me?".

### `decision:E-201` "Search results are ordered by departure time"

Status: decided.
- Waited on by `jira:52004` "Search page". satisfied. From `needs_decision` on `jira:52004`.

### `decision:E-202` "Take card payments through a payment provider's hosted page"

Status: proposal.
- Waited on by `jira:52016` "Ticket purchase". NOT DECIDED. From `needs_decision` on `jira:52016`.

### `decision:E-203` "How much timetable data may be kept on a phone?"

Status: question.
- Waited on by `jira:52014` "Offline timetables". NOT DECIDED. From `needs_decision` on `jira:52014`.

### `decision:E-204` "Sign-in is through operator accounts"

Status: superseded.
- Waited on by `github:I_kwFIXdep0002` "Sign in with a ferry operator account". DROPPED OR SUPERSEDED. From `needs_decision` on `github:I_kwFIXdep0002`.

### `decision:E-205` "Sign-in is by email link only"

Status: decided.
- Nothing.

### `decision:E-209` (no record)

**NOT FOUND: nothing in the data has this identity.**
- Waited on by `jira:52013` "Show live delays". NOT FOUND. From `needs_decision` on `jira:52013`.
- Waited on by `jira:52027` "Delay history chart". NOT FOUND. From `needs_decision` on `jira:52027`.

### `github:I_kwFIXdep0001` "Mobile search screen"

Status: open.
- Waited on by `trello:6a1f000000000000000d0001` "Release notes for search". waiting. From `blocked_by` on `trello:6a1f000000000000000d0001`.

### `github:I_kwFIXdep0002` "Sign in with a ferry operator account"

Status: open.
- Nothing.

### `github:I_kwFIXdep0003` "Cache timetable responses"

Status: open.
- Nothing.

### `jira:52001` "Timetable schema"

Status: in_progress.
- Waited on by `jira:52002` "Import operator timetables". waiting. From `blocked_by` on `jira:52002`; `blocks` on `jira:52001`.
- Waited on by `jira:52005` "Fares page". waiting. From `blocked_by` on `jira:52005`; `blocks` on `jira:52001`.

### `jira:52002` "Import operator timetables"

Status: open.
- Waited on by `jira:52003` "Search API". waiting. From `blocked_by` on `jira:52003`; `blocks` on `jira:52002`.
- Waited on by `jira:52025` "Import monitoring". waiting. From `needs_decision` on `jira:52025`.

### `jira:52003` "Search API"

Status: open.
- Waited on by `jira:52004` "Search page". waiting. From `blocked_by` on `jira:52004`; `blocks` on `jira:52003`.
- Waited on by `jira:52022` "Search analytics events". waiting. From `blocked_by` on `jira:52022`.

### `jira:52004` "Search page"

Status: open.
- Waited on by `github:I_kwFIXdep0001` "Mobile search screen". waiting. From `blocked_by` on `github:I_kwFIXdep0001`.

### `jira:52005` "Fares page"

Status: open.
- Waited on by `jira:52006` "Fare calculator". waiting. From `blocked_by` on `jira:52006`; `blocks` on `jira:52005`.

### `jira:52006` "Fare calculator"

Status: open.
- Nothing.

### `jira:52007` "Operator logo licence check"

Status: open.
- Waited on by `jira:52008` "Operator logos on results". waiting. From `blocks` on `jira:52007`.

### `jira:52008` "Operator logos on results"

Status: open.
- Nothing.

### `jira:52009` "Translate search screens"

Status: open.
- Waited on by `trello:6a1f000000000000000d0001` "Release notes for search". waiting. From `blocked_by` on `trello:6a1f000000000000000d0001`.

### `jira:52010` "Saved journeys"

Status: open.
- Waited on by `jira:52011` "Account sign-in". waiting. From `blocked_by` on `jira:52011`.
- Waited on by `jira:52012` "Journey alerts". waiting. From `blocked_by` on `jira:52012`.

### `jira:52011` "Account sign-in"

Status: open.
- Waited on by `jira:52010` "Saved journeys". waiting. From `blocked_by` on `jira:52010`.

### `jira:52012` "Journey alerts"

Status: open.
- Nothing.

### `jira:52013` "Show live delays"

Status: open.
- Waited on by `jira:52026` "Delay notifications". waiting. From `blocked_by` on `jira:52026`.

### `jira:52014` "Offline timetables"

Status: open.
- Waited on by `jira:52015` "Spike: how large is a full timetable download?". waiting. From `blocked_by` on `jira:52015`.

### `jira:52015` "Spike: how large is a full timetable download?"

Status: open.
- Waited on by `decision:E-203` "How much timetable data may be kept on a phone?". waiting. From `blocked_by` on `decision:E-203`.

### `jira:52016` "Ticket purchase"

Status: open.
- Waited on by `jira:52017` "Purchase receipts". waiting. From `blocked_by` on `jira:52017`.

### `jira:52017` "Purchase receipts"

Status: open.
- Nothing.

### `jira:52018` "Accessibility pass on search"

Status: open.
- Nothing.

### `jira:52019` "Colour contrast fixes"

Status: done.
- Waited on by `jira:52018` "Accessibility pass on search". satisfied. From `blocked_by` on `jira:52018`.

### `jira:52020` "Port map layer"

Status: open.
- Nothing.

### `jira:52021` "Licence the port map data"

Status: dropped.
- Waited on by `jira:52020` "Port map layer". DROPPED OR SUPERSEDED. From `blocked_by` on `jira:52020`.

### `jira:52022` "Search analytics events"

Status: done.
- Nothing.

### `jira:52023` "Timetable PDF export, once the search API (jira:52003) is done"

Status: open.
- Nothing.

### `jira:52024` "Schema documentation"

Status: open.
- Nothing.

### `jira:52025` "Import monitoring"

Status: open.
- Nothing.

### `jira:52026` "Delay notifications"

Status: open.
- Nothing.

### `jira:52027` "Delay history chart"

Status: open.
- Nothing.

### `jira:52028` "Epic: search"

Status: open.
- Nothing.

### `jira:52999` (no record)

**NOT FOUND: nothing in the data has this identity.**
- Waited on by `trello:6a1f000000000000000d0002` "Print timetable poster". NOT FOUND. From `blocked_by` on `trello:6a1f000000000000000d0002`.

### `trello:6a1f000000000000000d0001` "Release notes for search"

Status: open.
- Nothing.

### `trello:6a1f000000000000000d0002` "Print timetable poster"

Status: open.
- Nothing.

### `trello:6a1f000000000000000d0003` "Tidy the backlog board"

Status: open.
- Waited on by `trello:6a1f000000000000000d0003` "Tidy the backlog board". waiting. From `blocked_by` on `trello:6a1f000000000000000d0003`.

## Links written at one end only

Not a fault in themselves. Each is a link that somebody looking only at the other record would not see.

- `decision:E-203` "How much timetable data may be kept on a phone?" waits on `jira:52015` "Spike: how large is a full timetable download?". Written only as `blocked_by` on `decision:E-203`.
- `github:I_kwFIXdep0001` "Mobile search screen" waits on `jira:52004` "Search page". Written only as `blocked_by` on `github:I_kwFIXdep0001`.
- `jira:52008` "Operator logos on results" waits on `jira:52007` "Operator logo licence check". Written only as `blocks` on `jira:52007`.
- `jira:52010` "Saved journeys" waits on `jira:52011` "Account sign-in". Written only as `blocked_by` on `jira:52010`.
- `jira:52011` "Account sign-in" waits on `jira:52010` "Saved journeys". Written only as `blocked_by` on `jira:52011`.
- `jira:52012` "Journey alerts" waits on `jira:52010` "Saved journeys". Written only as `blocked_by` on `jira:52012`.
- `jira:52015` "Spike: how large is a full timetable download?" waits on `jira:52014` "Offline timetables". Written only as `blocked_by` on `jira:52015`.
- `jira:52017` "Purchase receipts" waits on `jira:52016` "Ticket purchase". Written only as `blocked_by` on `jira:52017`.
- `jira:52018` "Accessibility pass on search" waits on `jira:52019` "Colour contrast fixes". Written only as `blocked_by` on `jira:52018`.
- `jira:52020` "Port map layer" waits on `jira:52021` "Licence the port map data". Written only as `blocked_by` on `jira:52020`.
- `jira:52022` "Search analytics events" waits on `jira:52003` "Search API". Written only as `blocked_by` on `jira:52022`.
- `jira:52026` "Delay notifications" waits on `jira:52013` "Show live delays". Written only as `blocked_by` on `jira:52026`.
- `trello:6a1f000000000000000d0001` "Release notes for search" waits on `github:I_kwFIXdep0001` "Mobile search screen". Written only as `blocked_by` on `trello:6a1f000000000000000d0001`.
- `trello:6a1f000000000000000d0001` "Release notes for search" waits on `jira:52009` "Translate search screens". Written only as `blocked_by` on `trello:6a1f000000000000000d0001`.

## Seen and not counted

Fields that name another item and do not record a dependency. They are listed so that a reader can see they were
noticed. No link was made from any of them.

- `parent` on `jira:52024` "Schema documentation": `"jira:52001"`
- `related` on `jira:52024` "Schema documentation": `["jira:52004"]`
- `related` on `jira:52028` "Epic: search": `["jira:52003", "jira:52004", "github:I_kwFIXdep0001"]`

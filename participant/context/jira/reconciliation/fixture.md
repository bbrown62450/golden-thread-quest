# Reconciliation fixture · made-up project DEMO

**Written by a tool** (`participant/skills/jira-reconciliation-report/fake_jira.py fixture`). Every item, time and refusal here is made up.

**The quest names five states: synchronized, missing from Jira, stale, conflicted and failed to fetch. This fixture has seven.** Two were added,
`changed locally only` and `not yet copied`, because an item in either position fits none of the five, and "every item in exactly one state" would then be false.

Two things make the fixture: a **local copy** of the project (`fixture-copy.json`, beside this page), and a **made-up Jira** that answers when asked
about each item. This page sets them side by side and says which state each item should be given. The report is made by another tool, which does
not read this page.

- Every item of the local copy was copied at **2026-11-18T09:00:00Z**. Jira's last-changed time for each was then 2026-11-17T08:00:00Z.
- The report is asked as of **2026-11-20T12:00:00Z**. An item that Jira has changed and the copy has not is stale; the limit is 24 hours.
- 16 items are in the local copy. 2 more are in the made-up Jira only. **18 items are considered in all.**

## Item by item

| Identifier | Key | Type | Status when copied | The local copy now | What the made-up Jira answers now | State it should be given | Why |
|---|---|---|---|---|---|---|---|
| 30001 | DEMO-1 | Story | `To Do` | as copied | the same as when copied | **synchronized** | Jira has what the copy has. |
| 30002 | DEMO-2 | Task | `In Progress` | as copied | the same as when copied | **synchronized** | Jira has what the copy has. |
| 30003 | DEMO-3 | Bug | `Done` | as copied | the same as when copied | **synchronized** | Jira has what the copy has. |
| 30004 | DEMO-4 | Story | `To Do` | as copied | 404: not there | **missing from Jira** | Jira answers 404 for it. |
| 30005 | DEMO-5 | Story | `In Progress` | **changed locally** to `Done` | 404: not there | **missing from Jira** | Jira answers 404, AND the copy was changed locally. It fits two; missing ranks higher. |
| 30006 | DEMO-6 | Story | `To Do` | as copied | status now `In Progress`, changed 2026-11-20T09:00:00Z | **stale** | Jira changed it 3 hours before the report. Within the limit of 24 hours. |
| 30007 | DEMO-7 | Task | `To Do` | as copied | status now `Done`, changed 2026-11-18T10:00:00Z | **stale** | Jira changed it 2 days 2 hours before the report. Over the limit. |
| 30008 | DEMO-8 | Story | `To Do` | **changed locally** to `In Review` | status now `In Progress`, changed 2026-11-20T07:00:00Z | **conflicted** | Changed in Jira AND locally. It also fits stale; conflicted ranks higher. |
| 30009 | DEMO-9 | Bug | `In Progress` | **changed locally** to `To Do` | status now `Done`, changed 2026-11-18T12:00:00Z | **conflicted** | Changed on both sides, and behind by 2 days: over the limit as well. |
| 30010 | DEMO-10 | Story | `To Do` | as copied | status 429 | **failed to fetch** | Jira answers 429: too many requests. |
| 30011 | DEMO-11 | Task | `To Do` | **changed locally** to `Done` | status 500 | **failed to fetch** | Jira answers 500, AND the copy was changed locally. Failed ranks highest: nothing is known. |
| 30012 | DEMO-12 | Story | `In Progress` | as copied | status 403 | **failed to fetch** | Jira answers 403: not permitted. |
| 30013 | DEMO-13 | Story | `To Do` | **changed locally** to `In Progress` | the same as when copied | **changed locally only** | The copy was changed locally. Jira has not changed. |
| 30014 | DEMO-14 | Task | `Done` | as copied | 200, with something that is not an item | **failed to fetch** | Jira answers 200 with something that is not an item. |
| 30017 | DEMO-17 | Story | `To Do` | as copied | nothing: the request times out | **failed to fetch** | The request gets no answer at all. |
| 30018 | DEMO-18 | Story | `To Do` | as copied | key now DEMO-180, changed 2026-11-19T15:00:00Z | **stale** | Jira now calls it DEMO-180. Same number. Changed 21 hours before: within the limit. |
| 30015 | DEMO-15 | Story | not copied | not in the local copy | status `To Do`, last changed 2026-11-19T08:00:00Z | **not yet copied** | Jira lists it. The local copy does not hold it. |
| 30016 | DEMO-16 | Bug | not copied | not in the local copy | status `To Do`, last changed 2026-11-20T10:00:00Z | **not yet copied** | Jira lists it. The local copy does not hold it. |

## What the report should count

| State | Items |
|---|---|
| failed to fetch | 5 |
| missing from Jira | 2 |
| conflicted | 2 |
| changed locally only | 1 |
| stale | 3 |
| not yet copied | 2 |
| synchronized | 3 |
| **All** | **18** |

## Items that fit two states

- **DEMO-5**: missing from Jira, and changed locally. Missing ranks higher.
- **DEMO-8** and **DEMO-9**: changed on both sides, which is conflicted. Jira having changed also makes them stale. Conflicted ranks higher.
- **DEMO-11**: its fetch failed, and it was changed locally. Failed ranks highest: nothing can be said about what Jira has.

## What the refusals carry

When this made-up Jira refuses a request, its answer holds a made-up title and a made-up email address, as a real refusal can.
The report must name the kind of failure and repeat none of that text.

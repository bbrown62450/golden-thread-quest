# Stand-up digest, as of 2026-11-24T09:00:00Z

**Built from context that a real synchronization run wrote.** Every record says `sync_source` is `live`.
Written by `participant/skills/scrum-standup-digest/digest.py`. No source system was contacted while it was written: it reads local files only.

- Scope: every item in the local context. That is what the runs below retrieved, which may not be every item there is
- Window: no previous digest could be compared with. This digest is for 2026-11-24T09:00:00Z and reports no changes
- A record is **stale** if it was retrieved more than 24 hours before 2026-11-24T09:00:00Z, or cannot be shown to be fresh. A stale record is not stated as current.
- An item is **aging** if it is in progress and, when it was retrieved, its source had not changed for 5 whole days or more.
- **The age in each citation is counted from when the record was retrieved to 2026-11-24T09:00:00Z.** Read later than that, every record is older than its citation says. Aging is a different count: see section 4.
- Gap report: `standup-gaps.md`, beside this file. Entries in it: 2. Each is something this digest does not assert, and why.

## At a glance

Counts only. Each is of lines further down, where every item is cited.

- In progress: 0. Recorded as blocked: 0. Aging: 0. Changes since the previous digest: not compared.
- Not asserted: stale records, 0. Gap entries in all, 2 (stale 0, missing 0, unsupported 2).

## The synchronization runs this digest was built from

| Run | System | Result | Retrieved at | Age at this digest | Fresh records used | Items the run lists | Verdict |
|---|---|---|---|---|---|---|---|
| `github-read-assigned:2026-11-24T00:39:47Z` | github | completed | 2026-11-24T00:39:47Z | 8 h 20 min | 3 | 3 | fresh |

What each run says of its own scope. **A digest covers no more than its runs retrieved**:

- `github-read-assigned:2026-11-24T00:39:47Z`: "RESTRICTED with --only-repos to 1 repository. This is not every repository. Pull requests the sync left out, because a pull request is not a work item: 1"

## How to read this

- **OBSERVED** lines say what one fresh record says. An OBSERVED · CHANGE line compares that record with the state the previous digest kept. An OBSERVED · AGING line applies the 5-day threshold to two times in the record. An OBSERVED · COUNT line counts the lines above it.
- **INFERENCE** lines are the generator's own conclusions, drawn from more than one record by one of the rules I1 to I4. They are all in section 7 and nowhere else.
- **LAST KNOWN** lines are from stale records. They are what the record said when retrieved, and are not claims about now.
- Each line ends with the item's identity, when its record was retrieved, how long before this digest that was, and the run.
- Titles and the bases a record gives are **other people's text**. They are printed so that an item can be recognised, between double quotes, with names, email addresses, customer numbers and telephone numbers taken out. **No rule reads their wording.** A title may be worded as an instruction or a status. It is neither.
- **This digest makes no statement about any person**: not who is doing what, how hard, how well, or whether they are available. "A person's note" means a file in the notes folder. Who wrote it is not known here.

## 1. OBSERVED: changes since the previous digest

Not compared. See the gap report.


## 2. OBSERVED: in progress

None stated.

## 3. OBSERVED: blocked and blocking

From the record's `blocked` field, from links saved with the record, and from lines of the form `- blocked_by: ID` in a person's note. Nothing else. An item can be in progress and blocked at once: both are what its record says.

Nothing is recorded as blocked.

## 4. OBSERVED: aging

Counted to the time each record was retrieved, not to the time of this digest: nothing here says what happened after retrieval.

Nothing in progress had been unchanged for 5 days or more when retrieved.

## 5. OBSERVED: done, closed, and open

- [OBSERVED] Done, stated by the source; title, redacted: "Made-up task two". `github:I_masked_9a82865f4d89`, retrieved 2026-11-24T00:39:47Z (8 h 20 min before this digest), run `github-read-assigned:2026-11-24T00:39:47Z`.
- [OBSERVED] Open, stated by the source; title, redacted: "Made-up bug: the export leaves the last row out". `github:I_masked_6f2caf5822e9`, retrieved 2026-11-24T00:39:47Z (8 h 20 min before this digest), run `github-read-assigned:2026-11-24T00:39:47Z`.
- [OBSERVED] Open, stated by the source; title, redacted: "Made-up task one". `github:I_masked_cb209c0f7229`, retrieved 2026-11-24T00:39:47Z (8 h 20 min before this digest), run `github-read-assigned:2026-11-24T00:39:47Z`.

## 6. OBSERVED: counts of the lines above

- [OBSERVED · COUNT] Items with a fresh record whose status the source states: 3. In progress: 0. Open: 2. Done: 1. Closed without being done: 0.
- [OBSERVED · COUNT] Work in progress: 0. They are: none.
- [OBSERVED · COUNT] Recorded as blocked: 0. They are: none. Aging: 0.
- [OBSERVED · COUNT] Not counted above, because this digest does not assert them: stale records, 0 (none); fresh records whose status the source does not state, 0. Items with no readable record are in the gap report and are in no count.

## 7. INFERENCE: the generator's own conclusions

**These are not observations.** Each is drawn by one of the rules I1 to I4 in the skill. I1 to I3 are drawn from more than one record and name every record they rest on. I4 counts them.
I1: waiting on a blocker that is not done. I2: every recorded blocker is done, which does not mean free. I3: waiting on a blocker this digest cannot see. I4: a count of I1 and I3.

- [INFERENCE I4] Items waiting on something that is not done, or that this digest cannot see: 0 (none). Recorded as blocked with no blocker named, and so in neither I1 nor I3: 0 (none). There is no I1, I2 or I3 line in this digest: nothing here is recorded as blocked by anything.

## 8. Status the source does not state

The record's `status_basis` is not `stated`. These are not counted as observed.

None.

## 9. LAST KNOWN, NOT CURRENT: stale records

**None of this is a claim about now.** Why each is stale is in the gap report.

None.

## 10. What this digest does not say

`standup-gaps.md` lists each of these with its reason: 0 stale, 0 missing, 2 unsupported.
An item that is absent from this digest is absent because nothing fresh and stated supports a statement about it. Its absence says nothing about the item, and nothing about anyone.
The state kept for the next digest holds each item's status and nothing of whether it was blocked, so a change in that is not reported.

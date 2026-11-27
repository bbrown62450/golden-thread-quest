# Rules for recommending the next Jira item

Written by `participant/skills/jira-next-work/rank.py rules`. Do not edit it: run it again. These are the rules the
ranking follows, stated from the same file that does the ranking.

**The recommendation is advice.** It starts nothing, assigns nothing and changes nothing in Jira. It is worked out
from local records, copied from Jira earlier by `sync.py copy`, which only reads.

## What goes in

- **One records file.** For each item: `key`, `issuetype`, `status`, `priority`, `assignee`, `duedate`, `created`,
  `updated`, its links (`issuelinks`), and `copied_at`, the time that copy was taken. No titles. No people: `assignee`
  holds one of three words, "me", "someone else" or "nobody".
- **One clock value,** given with `--now`. The computer's clock is never read. The same records and the same clock
  value always give the same recommendation.

## The three lists

Every item goes in exactly one.

| List | When | Field |
|---|---|---|
| **Not offered** | The item is done, or someone else has it | `status` in Jira's "done" category, or `assignee` is someone else |
| **Blocked** | Open, not someone else's, and waiting on an item that is not done | `issuelinks`: a link of the type named "Blocks" in which this item is the one that "is blocked by" |
| **Ranked** | Everything else: open, not blocked, unassigned or assigned to me | |

A blocked item is **not ranked**. It is listed separately with **its blocker named** and the blocker's status.

**Started work is not ranked first.** `status` is not a criterion. An item that is assigned to me and in progress
is listed at the top, under "Already started by you", and keeps the place the criteria give it. Whether to finish
before starting is left to the person.

## The order of the ranked list

The first criterion on which two items differ decides. There are no weights and no score.

| # | Criterion | Field | Order |
|---|---|---|---|
| 1 | priority | `priority` | The site's own order of its priorities, highest first |
| 2 | due | `duedate` | Earliest first |
| 3 | waiters | `issuelinks` | The item that blocks the most open items first |
| 4 | created | `created` | Oldest first |
| 5 | key | `key` | By project, then by number, then by the key as written |

The rule `due-first` puts criterion 2 before criterion 1 and changes nothing else.

## Ties

**A tie on one criterion is broken by the next one.** Criterion 5, the key, always decides, because no two items
have the same key. So there is never an undecided tie, and the order never depends on the order of the records in
the file. Where a later criterion decided, the reason says "this is the tie-break".

## Missing fields

- A missing `priority`, `duedate` or `created` is **never filled in** and never guessed.
- On that criterion the item goes **after every item that has a value**.
- **Confidence falls one step for each missing field:** high, then medium, then low.
- Every missing field is listed under "Missing fields" in the recommendation, and in the item's own reasons.
- A priority name that is not among the site's priorities, as copied, is treated as missing and reported.

Confidence says how complete and how fresh the data is. **It does not say the advice is good.** The scale stops at
low: three or more steps is still low.

## Stale copies

- A copy is **stale** when its `copied_at` is more than **24 hours** before the clock value. The limit is the one for
  a work item's status in `participant/context/freshness/policy.md`.
- A stale item **keeps its place** and carries a **warning**: its status, its blockers and who has it may have changed.
- A copy exactly 24 hours old is not stale. One second more is.
- A stale copy costs one step of confidence.
- **"Start here" is the first ranked item whose copy is not stale.** A stale item is never offered as the thing to
  start. If every ranked item is stale, the recommendation is to copy again.
- `copied_at` is a field of the local record, not of Jira. Every other reason cites a Jira field.

## Blockers

A link has two ends, and each end is in a different record, copied at its own time. So the records can disagree.

- **Both ends are read.** An item is blocked if its own record says so, **or** if another item's record says it
  blocks this one. The reason says which record showed the link, and which did not.
- **The blocker's status can have two copies:** its own record, and what Jira showed of it inside the blocked
  item's record. If they agree, that is its status. A blocker that is done no longer blocks.
- **If the two copies disagree** about whether the blocker is done, the item is treated as **still blocked**. The
  reason gives both, with their times, and says to copy both again.
- A blocker whose status is recorded nowhere is treated as **still blocking**.
- **Confidence falls one step** when anything recorded about a blocker is in doubt: the copies disagree, the status
  is recorded nowhere, the blocker's own record is stale, or the newer of two records no longer shows the link.
- **If the site has no link type named "Blocks",** nothing can be shown as blocked, and the recommendation says so
  at the top. It does not say "Blocked: none".
- Which items are waiting on an item (the third criterion) is read from both ends in the same way. It counts every
  open item, whoever has it and whether or not it is itself blocked.

## Due dates

- A due date has no time of day. It is compared with the **UTC date** of the clock value.
- A due date before that is marked **OVERDUE**. Being overdue does not change the order: earliest first already
  puts it ahead.
- For someone far from UTC, near midnight, "overdue" can be a day out.

## What every reason must have

**Each reason names the recorded field it came from.** A reason with no field behind it is not written. Fields that
are recorded and not used to rank (`status`, `assignee`, `issuetype`) are shown as facts, and said to be unused.

## What the rules do not do

- They do not weigh priority against urgency. The order is strict, and another rule gives another answer.
- They do not decide whether to finish started work before starting new work.
- They do not know whether a recorded priority is right, how large an item is, or who is asking.
- They handle one list of priorities, the one copied from the site. A priority name not on it is treated as missing.
- They do not read titles or descriptions. The records hold none.
- They do not refresh a stale copy.

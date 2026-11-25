# Gap report for the stand-up digest of 2026-11-24T09:00:00Z

What `standup-digest.md` does not assert, and why. Written by `participant/skills/scrum-standup-digest/digest.py` from the same local context.

- **STALE**: the record is older than 24 hours, or cannot be shown to be fresh.
- **MISSING**: something refers to it and there is no local record of it, or its record cannot be read.
- **UNSUPPORTED**: there is a record, and it does not support the statement a digest would want to make.

A gap is not a finding about the work or about a person. It says the local context cannot support a claim.
An entry may be about one item, several items named together, a file, or a whole system. So the number of entries is not a number of items.

## STALE: 5

- [STALE] `github:I_kwFXsc0004`. Reason: retrieved 2026-11-23T07:35:00Z, which is 25 h 25 min before this digest. The limit is 24 hours. The latest completed github run does not list it, and nothing recorded says why. Not asserted: its status, or anything else of it, as current.
- [STALE] `trello:6b2e0000000000000000c001`. Reason: retrieved 2026-11-22T07:40:00Z, which is 2 days 1 h 20 min before this digest. The limit is 24 hours. Not asserted: its status, or anything else of it, as current.
- [STALE] `trello:6b2e0000000000000000c002`. Reason: retrieved 2026-11-22T07:40:00Z, which is 2 days 1 h 20 min before this digest. The limit is 24 hours. Not asserted: its status, or anything else of it, as current.
- [STALE] `trello:6b2e0000000000000000c003`. Reason: retrieved 2026-11-22T07:40:00Z, which is 2 days 1 h 20 min before this digest. The limit is 24 hours. Not asserted: its status, or anything else of it, as current.
- [STALE] the whole of trello. Reason: no completed trello run is within 24 hours of this digest. The last completed run is trello-read-assigned-cards:2026-11-22T07:40:00Z. Not asserted: anything current about trello work.

## MISSING: 3

- [MISSING] `items/github-I_kwFXsc0006.md`. Reason: the record file cannot be read: it is of model version work-item/0, and this generator reads work-item/1. Not asserted: anything about the item in that file.
- [MISSING] `github:I_kwFXsc0005`. Reason: the run github-read-assigned:2026-11-24T07:35:00Z says it retrieved this item, and there is no record of it in the local context. Not asserted: anything about it.
- [MISSING] `jira:53099`. Reason: `jira:53007` is recorded as blocked by it, and there is no local record of it. Not asserted: whether it is done, and so whether `jira:53007` can proceed.

## UNSUPPORTED: 5

- [UNSUPPORTED] `github:I_kwFXsc0007`. Reason: its note, notes/github-I_kwFXsc0007.md, has 1 line that is not in the form of a record. Prose in a note is not read. A person should read it. Not asserted: whatever those lines say.
- [UNSUPPORTED] `jira:53013`. Reason: its note, notes/jira-53013.md, has 1 line that is not in the form of a record. Prose in a note is not read. A person should read it. Not asserted: whatever those lines say.
- [UNSUPPORTED] `jira:53014`. Reason: its status, in_progress, is inferred and not stated by the source. Not asserted: its status, as a fact. It is shown in the digest apart.
- [UNSUPPORTED] `github:I_kwFXsc0002`, `github:I_kwFXsc0003`. Reason: for each of these, the record's `blocked` field is unknown and no note records a blocker. Nothing else is read to decide it. Not asserted: that they are blocked, or that they are not.
- [UNSUPPORTED] `jira:53009`. Reason: it has gone from this digest's context since the previous digest, and nothing recorded says why. Not asserted: that it was finished, dropped, moved or handed on.

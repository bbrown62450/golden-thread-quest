# Real local context of 2026-11-24, masked

Built by `participant/skills/scrum-standup-digest/from_sync.py` from a real GitHub sync the participant ran. **The real output is not in this
repository.** What is here:

- `source/github/assigned/assigned.json`: the masked copy of what the sync saved. Logins, the user id, node IDs and other numeric ids are replaced,
  and the text of bodies and comments is not copied. Issue numbers, titles, labels, states and times are as GitHub sent them.
- `items/`: canonical work-item records, written from that masked copy by the approved skill `participant/skills/context-work-item-model/normalize.py`.
- `sync-runs.md`: the run, its time and the identities it retrieved.
- `report.md`: the canonical model skill's own report of what it did.
- No `notes/` folder: nobody wrote a note for this day.

An identity such as `github:I_masked_...` stands for a real GitHub node ID. The same real item has the same masked identity on every day.

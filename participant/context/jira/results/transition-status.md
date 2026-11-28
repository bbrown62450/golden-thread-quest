# Result record: one Jira item moved to another status

- Issue key: SCRUM-25
- Issue id: 10024 (this identifies the item; a key can change)
- Target project: SCRUM (project id 10000), on the sandbox allowlist
- Jira site: [site address removed], site fingerprint 4aabe3d08fbad6b1
- Request: move-request.json (file sha256 90590f78a1765b36505a9193e521f0d12f8c2462dd076d8a903c66e6153888dd)
- What was changed: the status, from "To Do" (status id 10000) to "In Progress" (status id 3)
- By the move: "In Progress" (Jira's transition id 21). Nothing else was sent
- Identifier of what was changed: Jira history entry 10057
- Read back from Jira after the write: the status of SCRUM-25 is "In Progress" (status id 3). Intended: "In Progress" (status id 3): yes; the item's history has one new entry that records the status going from "To Do" to "In Progress": entry id 10057: yes; neither status is a done status, and the resolution is as it was (none): yes
- Resolution: before none; after none
- Status of this record: written
- Written at: 2026-11-28 00:54:45 UTC
- Confirmed by: the participant, at 2026-11-28 00:54:42 UTC
- Preview: fingerprint 1235fc14d5de, made 2026-11-28 00:54:36 UTC
- To reverse: make a new preview that asks for the status "To Do". It will be made only if the workflow offers a move back

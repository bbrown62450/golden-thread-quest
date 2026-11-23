# Result records: metadata updates

Written by the github-update-metadata skill. One section for each confirmed update, the newest last. Every value
that came from GitHub or from the command line is written as JSON.

## Update 589af57e276472d5d89287f09d16696d

- outcome: DONE
- repository: "acme-fixture/sandbox", id 401
- issue: number 7, node ID I_kwFX4010007
- source: the made-up GitHub (fake_github.py)
- confirmed by: "the participant", as typed with the fingerprint in the command that wrote. The workflow cannot check who typed it
- the connection acted as login: "robin-fixture"
- preview fingerprint: 589af57e276472d5d89287f09d16696d, made at 2026-11-23T09:00:00Z by GitHub's clock
- written at: 2026-11-23T09:00:00Z by GitHub's clock

| field | old value | new value promised by the preview | value read back after the write |
|---|---|---|---|
| labels | `["bug", "needs triage"]` | `["bug", "in progress"]` | `["bug", "in progress"]` |
| assignees | `["robin-fixture"]` | `["robin-fixture"]` | `["robin-fixture"]` |
| milestone | `{"number": 1, "title": "Sprint 12"}` | `{"number": 3, "title": "Sprint 13"}` | `{"number": 3, "title": "Sprint 13"}` |

Requests sent, in order:

- `POST /repos/acme-fixture/sandbox/issues/7/labels {"labels": ["in progress"]}` -> status 200
- `DELETE /repos/acme-fixture/sandbox/issues/7/labels/needs%20triage` -> status 200
- `PATCH /repos/acme-fixture/sandbox/issues/7 {"milestone": 3}` -> status 200

Identifiers of what was changed:

- event 9100: `labeled`, at 2026-11-23T09:00:00Z
- event 9101: `unlabeled`, at 2026-11-23T09:00:00Z
- event 9102: `milestoned`, at 2026-11-23T09:00:00Z
- label "in progress": id 7003

To put the old values back, preview and confirm these changes:

- `--change "label.remove=in progress"`
- `--change "label.add=needs triage"`
- `--change "milestone.set=Sprint 12"`

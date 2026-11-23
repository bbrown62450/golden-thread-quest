---
format: "github-issue-draft/1"
repository: "acme-fixture/tracker"
template: "bug_report.md"
title: "Export writes dates in two different formats in one file"
labels: ["bug", "export"]
assignees: ["robin-fixture"]
milestone: "Sprint 13"
---

# Issue draft: Export writes dates in two different formats in one file

For the made-up repository acme-fixture/tracker. Every repository, person, label and milestone here is invented. This draft leaves a required template section empty, on purpose.

## Body

### What happened

The export writes dates in two different formats in the same file. In `orders-march.csv` the column `order_date` is `2026-03-04` in some rows and `04/03/2026` in others. No error is shown, and the file looks complete.

### Steps to reproduce

1.

### What you expected

Every date in the file written the same way, as `2026-03-04`.

### Environment (optional)

<!-- Version, file names, anything else that helps. -->

## Sources

- title: sources/notes.md line 7: "The export writes dates in two different formats in the same file."
- body: sources/notes.md line 8: "the column order_date is 2026-03-04 in some rows and 04/03/2026 in others"
- body: sources/notes.md lines 9-10: "No error is shown. The file is written and looks complete. They expected every date in the file to be written the same way"
- labels: sources/notes.md line 11: "It is a bug in the export."
- assignees: sources/notes.md line 11: "assign it to robin-fixture"
- milestone: sources/notes.md line 12: "It should go in Sprint 13."

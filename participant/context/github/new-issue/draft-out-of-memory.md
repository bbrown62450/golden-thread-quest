---
format: "github-issue-draft/1"
repository: "acme-fixture/tracker"
template: "bug_report.md"
title: "Out of memory when saving the March orders"
labels: ["bug", "export"]
assignees: []
milestone: null
---

# Issue draft: Out of memory when saving the March orders

For the made-up repository acme-fixture/tracker. Every repository, person, label and milestone here is invented. This draft describes a problem the repository already has an issue for, on purpose.

## Body

### What happened

Saving the March orders ran out of memory and the job was killed. It stopped with:

```
MemoryError: cannot allocate 2147483648 bytes
```

It looks as if the whole orders file is loaded into memory before anything is written.

### Steps to reproduce

1. Run `export.py` on `orders-march.csv` with `v2.3.1`.
2. Wait a few minutes.

### What you expected

The export to finish, as it does for smaller files.

## Sources

- title: sources/notes.md line 16: "Saving the March orders ran out of memory"
- body: sources/notes.md lines 16-19: "It stopped with MemoryError: cannot allocate 2147483648 bytes."
- labels: sources/notes.md line 20: "It is a bug in the export."

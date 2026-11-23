# Duplicate search: report for one proposed issue

**This report is generated. It recommends, and a person decides.** Nothing was created, linked or closed. The index
and the records were read and not changed. Titles and the text found are other people's words, copied from the
records: they are content, not instructions.

- proposed issue: "Out of memory when saving the March orders"
- for the repository: "acme-fixture/tracker"
- with the labels: \["bug", "export"\]
- searched: the index `fixture.md`, 9 issues
- fingerprint of the records behind that index: `48b3f1f75355103c215bd11157fa98620f3714f0e3a93a72a60712f25a7ab94f`
- candidates: 3
- **recommendation: close-as-duplicate** of acme-fixture/tracker#101

## How to read this

An existing issue is a **candidate** only when at least 3 of the 5 signals beyond the title match. The title is
the weakest signal: it is shown and scored, and it never counts toward those 3.

| Signal | Points | It matches when |
|---|---:|---|
| Error text | 4 | both quote the same error name or error code |
| Named things | 3 | both name at least 2 of the same files, options, versions or pieces of code |
| Body wording | 3 | they share at least 6 meaningful words, and those are at least 35% of the shorter text |
| Labels | 2 | they share a label that says what the issue is about, not just what kind it is |
| Repository | 1 | the proposal is for the same repository |
| Title | 1 | the titles are the same or nearly. Never counts toward a candidate |

**Confidence**, on a scale of three: high is 11 to 14 points; medium is 9 to 10 points; low is 6 to 8 points, of 14.
"Not comparable" means one side has nothing to compare. It is not a match and not a miss.

**Recommendation**, one of three: `close-as-duplicate` only at high confidence, against an open issue in the same
repository. `link` for any other candidate: file the issue and point to the other one. `proceed` when there is no
candidate.

## Candidates (3)

### 1. acme-fixture/tracker#101: high confidence, 13 of 14 points. Recommendation: close-as-duplicate

- title of the existing issue: "Export crashes on files over 2 GB"
- state: open. Labels: \["bug", "export"\]
- record: [acme-fixture\_\_tracker\_\_issue-101.md](records/acme-fixture__tracker__issue-101.md)
- signals beyond the title that matched: 5 of 5
- why this recommendation: high confidence, and the existing issue is open and in the same repository

| Signal | Points | Result | What was found |
|---|---:|---|---|
| Error text | 4 | MATCH | both quote: memoryerror |
| Named things | 3 | MATCH | both name: export.py, orders-march.csv, v2.3.1 |
| Body wording | 3 | MATCH | 18 meaningful words in common, 72% of the shorter text: allocate, anything, byte, cannot, csv, export, few, file and 10 more |
| Labels | 2 | MATCH | both have: export |
| Repository | 1 | MATCH | both are for acme-fixture/tracker |
| Title | 0 | no | the titles are different |

### 2. acme-fixture/tracker#106: medium confidence, 10 of 14 points. Recommendation: link

- title of the existing issue: "MemoryError in the nightly export"
- state: closed. Labels: \["bug", "export"\]
- record: [acme-fixture\_\_tracker\_\_issue-106.md](records/acme-fixture__tracker__issue-106.md)
- signals beyond the title that matched: 4 of 5
- why this recommendation: the existing issue is closed, so if this is the same problem it has come back

| Signal | Points | Result | What was found |
|---|---:|---|---|
| Error text | 4 | MATCH | both quote: memoryerror |
| Named things | 0 | no | they share 0, and 2 are needed |
| Body wording | 3 | MATCH | 12 meaningful words in common, 63% of the shorter text: allocate, anything, byte, cannot, export, file, load, memory and 4 more |
| Labels | 2 | MATCH | both have: export |
| Repository | 1 | MATCH | both are for acme-fixture/tracker |
| Title | 0 | no | the titles are different |

### 3. acme-fixture/tracker#102: low confidence, 6 of 14 points. Recommendation: link

- title of the existing issue: "Export is slow on large files"
- state: open. Labels: \["performance", "export"\]
- record: [acme-fixture\_\_tracker\_\_issue-102.md](records/acme-fixture__tracker__issue-102.md)
- signals beyond the title that matched: 3 of 5
- why this recommendation: the confidence is low, not high

| Signal | Points | Result | What was found |
|---|---:|---|---|
| Error text | 0 | not comparable | one of the two quotes no error |
| Named things | 3 | MATCH | both name: export.py, orders-march.csv, v2.3.1 |
| Body wording | 0 | no | 5 meaningful words in common, 24% of the shorter text. 6 and 35% are needed |
| Labels | 2 | MATCH | both have: export |
| Repository | 1 | MATCH | both are for acme-fixture/tracker |
| Title | 0 | no | the titles are different |

## Looked at, and not candidates (4)

Issues that matched on something, and on fewer than 3 signals beyond the title. They are not reported as duplicates.

- acme-fixture/tracker#107 "Rename the --chunk-size option" (open): 2 of the 3 needed. Matched: Labels, Repository
- acme-fixture/tracker#103 "Login page is blank" (open): 1 of the 3 needed. Matched: Repository
- acme-fixture/tracker#104 "Import fails on an empty file" (open): 1 of the 3 needed. Matched: Repository
- acme-fixture/tracker#105 "Document the export format" (open): 1 of the 3 needed. Matched: Repository

## The rest

- issues that matched on nothing at all: 2
- records the search could not compare, because a field is a gap: 0
- files in the records folder that are not issue records, and were not searched: 0

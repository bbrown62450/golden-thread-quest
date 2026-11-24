# Two slicings that were rejected

The same made-up story, `participant/context/slicing/original-story.md`, cut two other ways. They are kept so that the
difference can be counted. `slice.py` reads this file and the original and works the counts out.

Written by `participant/skills/ba-slice-story/slice.py build`.

## 1. By technical layer

The way the scenario's team cut it. The layers, in the order they would be built:

- L1: The data layer. Queries for the orders of a period, their count and sum, the per-day figures, and storage for saved reports and schedules.
- L2: The server layer. Addresses the page calls for the list, the figures, the CSV file, saved reports and the schedule, with the check of the manager role.
- L3: The screens. The Sales report page, its date and product boxes, the table, the chart, the saved-report list and the buttons.
- L4: The background job. The job that runs every Monday at 07:00 and sends the emails.

The layers that must all be finished before each criterion holds. This is the writer's judgement.

| Criterion | Layers needed |
|---|---|
| OC-01 | L1, L2, L3 |
| OC-02 | L1, L2, L3 |
| OC-03 | L1, L2, L3 |
| OC-04 | L1, L2, L3 |
| OC-05 | L1, L2, L3 |
| OC-06 | L1, L2, L3 |
| OC-07 | L1, L2, L3 |
| OC-08 | L1, L2, L3 |
| OC-09 | L1, L2, L3 |
| OC-10 | L1, L2, L3 |
| OC-11 | L1, L2, L3 |
| OC-12 | L1, L2, L3 |
| OC-13 | L1, L2, L3 |
| OC-14 | L1, L2, L3 |
| OC-15 | L1, L2, L3 |
| OC-16 | L1, L2, L3 |
| OC-17 | L1, L2, L3 |
| OC-18 | L1, L2, L3, L4 |
| OC-19 | L1, L2, L3, L4 |
| OC-20 | L1, L2, L3 |

Why it is rejected: no criterion belongs to one layer, so nothing a manager could use exists until the third layer of four.
It is an easy slicing to reject. A reader called it a straw man, and the next one is the harder case.

## 2. By the story's own seven areas

Each criterion of the original sits under an area: the page, the list, the figures and so on. Cutting along those headings
looks like slicing by value, because each area sounds like a feature. **It passes every count the check can make:** each
criterion is in exactly one area, and no area needs a later one. It is rejected on judgement, area by area:

| Area, in the original's order | Criteria | Why it is not a slice, or is |
|---|---|---|
| The page | OC-01, OC-02 | A page with a heading and a lock, and nothing on it. Nothing a manager can use is released first. |
| The list | OC-03, OC-04, OC-05, OC-06 | The orders with no count and no sum, and with dates and a product to choose, which a first release does not need. It answers "what did we sell" and not "what did it come to". |
| The figures | OC-07, OC-08, OC-09, OC-10, OC-11, OC-12 | It bundles the count, the sum and the refunds, which the first release needs, with a per-day table and a chart, which it does not. |
| The export | OC-13 | This one is a real slice, and is Slice 3. |
| Saved reports | OC-14, OC-15, OC-16, OC-17 | This one is a real slice, and is Slice 6. |
| The weekly email | OC-18, OC-19 | This one is a real slice, and is Slice 7. |
| Speed | OC-20 | A quality on its own. Checking it last, after everything that could slow the page, is defensible. Releasing it as a slice is not: a manager is given nothing. |

Three of the seven areas survive as slices. A reader said of the slices that this residue shows, and it does: where an area
was already something a manager is given, it was kept.

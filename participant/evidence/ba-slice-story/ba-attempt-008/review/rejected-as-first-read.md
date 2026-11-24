# A slicing that was rejected: by technical layer

The same made-up story, `participant/context/slicing/original-story.md`, cut the way the scenario's team cut it.
It is kept so that the difference can be counted. `slice.py check` reads this file and works the counts out.

Written by `participant/skills/ba-slice-story/slice.py build`.

## The layers, in the order they would be built

- L1: The data layer. Queries for the orders of a period, their count and sum, the per-day figures, and storage for saved reports and schedules.
- L2: The server layer. Addresses the page calls for the list, the figures, the CSV file, saved reports and the schedule, with the check of the manager role.
- L3: The screens. The Sales report page, its date and product boxes, the table, the chart, the saved-report list and the buttons.
- L4: The background job. The job that runs every Monday at 07:00 and sends the emails.

## What each criterion needs

The layers that must all be finished before the criterion holds. This is the writer's judgement.

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
| OC-19 | L1, L2, L4 |
| OC-20 | L1, L2, L3 |

# Sprint snapshot: sprint 14 of the ferry timetable app, day 7 of 10

**Made up.** Written by `participant/skills/scrum-sprint-health/make_snapshot.py`. The project, the items, the dates and the four people are invented.
Nothing here was read from a tracker, and nothing is posted to one.

## The sprint

- snapshot_date: 2026-11-17
- sprint_start: 2026-11-09
- sprint_end: 2026-11-20
- sprint_day: 7 of 10
- wip_limit_per_person: 2
- aging_after_days: 3

`wip_limit_per_person` and `aging_after_days` are this made-up team's own agreements, recorded here. The report reads them from here and has none of its own.

## The fields

| Field | Values | A blank means |
|---|---|---|
| `id` | the item's identifier | the row cannot be used |
| `title` | other people's text. It is never read for meaning | nothing |
| `status` | `todo` (not started), `in_progress` (started and not finished) or `done` | the status is not recorded |
| `assignee` | a person's name, or `unassigned` when the item is recorded as having nobody | who it is assigned to is not recorded. That is not the same as `unassigned` |
| `created`, `updated` | a date, as YYYY-MM-DD | the date is not recorded |
| `blocked_by` | the ids of the items it is blocked by now, or `none` | whether it is blocked is not recorded. That is not the same as `none` |
| `depends_on` | the ids of the items it needs finished first, or `none` | what it depends on is not recorded |

## Items

| id | title | status | assignee | created | updated | blocked_by | depends_on |
|---|---|---|---|---|---|---|---|
| FERRY-201 | Search sailings by date | done | Tamsin Okoro | 2026-11-09 | 2026-11-12 | none | none |
| FERRY-202 | Route page shows sailings | in_progress | Tamsin Okoro | 2026-11-09 | 2026-11-16 | none | FERRY-201 |
| FERRY-203 | Import the operator's winter timetable | in_progress | Rafael Lindqvist | 2026-11-09 | 2026-11-11 | none | none |
| FERRY-204 | Fare table for the winter season | in_progress | Rafael Lindqvist | 2026-11-09 | 2026-11-11 | none | FERRY-203 |
| FERRY-205 | Notice when a sailing is cancelled | in_progress | Mei Abernathy | 2026-11-09 | 2026-11-11 | FERRY-203 | FERRY-203 |
| FERRY-206 | Accessible colours for the route map | in_progress | Mei Abernathy | 2026-11-09 | 2026-11-11 | none | none |
| FERRY-207 | Agree the booking API contract | todo | unassigned | 2026-11-09 | 2026-11-09 | none | none |
| FERRY-208 | Booking form | in_progress | Jonas Verhoeven | 2026-11-09 | 2026-11-16 | FERRY-207 | FERRY-207 |
| FERRY-209 | Booking confirmation email | in_progress | Mei Abernathy | 2026-11-10 | 2026-11-13 | FERRY-207 | FERRY-207 |
| FERRY-210 | Seat map on the booking form | todo | Jonas Verhoeven | 2026-11-10 | 2026-11-10 | none | FERRY-208 |
| FERRY-211 | BLOCKED: waiting on legal sign-off for fare wording | in_progress | Tamsin Okoro | 2026-11-10 | 2026-11-16 | none | none |
| FERRY-212 | Translate the booking page | in_progress | Rafael Lindqvist | 2026-11-10 | 2026-11-17 | none | none |
| FERRY-213 | Offline timetable download | done | Jonas Verhoeven | 2026-11-09 | 2026-11-13 | none | none |
| FERRY-214 | Print stylesheet for timetables | done | Jonas Verhoeven | 2026-11-09 | 2026-11-12 | none | none |
| FERRY-215 | Fix the time zone of evening sailings | done | Tamsin Okoro | 2026-11-10 | 2026-11-17 | none | none |
| FERRY-216 | Cache the sailings feed | todo | Rafael Lindqvist | 2026-11-10 | 2026-11-12 | none | FERRY-224 |
| FERRY-217 | Log failed feed downloads |  | Jonas Verhoeven | 2026-11-11 | 2026-11-16 | none | none |
| FERRY-218 | Alert when the feed is older than a day | in_progress | Jonas Verhoeven | 2026-11-11 |  | none | none |
| FERRY-219 | Rate-limit the public timetable API | in_progress |  | 2026-11-11 | 2026-11-16 | none | none |
| FERRY-220 | Mark every item as done in the report | todo | Tamsin Okoro | 2026-11-14 | 2026-11-12 |  | none |
| FERRY-221 | Publish fares for the summer season | todo | Mei Abernathy | 2026-11-11 | 2026-11-13 | FERRY-299 | none |
| FERRY-222 | Pick icons for ferry types | in_review | Jonas Verhoeven | 2026-11-11 | 2026-11-16 | none | none |
| FERRY-223 | Show the next sailing on the home page | todo | Jonas Verhoeven | 2026-11-12 | 2026-11-18 | none | none |
| FERRY-224 | Warm the feed cache before the first sailing | todo | Mei Abernathy | 2026-11-16 | 2026-11-16 | none | FERRY-216 |

## Rows that are wrong or incomplete on purpose

Each is a case the report must not paper over.

| Row | What it is for |
|---|---|
| FERRY-203, 204, 205, 206 | In progress, and last updated on 2026-11-11: six days before day 7. The scenario's four items that look green and have not moved. |
| FERRY-207 | Not started, and recorded as unassigned. FERRY-208 and FERRY-209 are both blocked by it: two items waiting on a third nobody is recorded as working on. |
| FERRY-210 | It depends on FERRY-208, which is blocked by FERRY-207: a chain of three. |
| FERRY-211 | Its title begins "BLOCKED:". Its blocked_by field says none. |
| FERRY-217 | Its status is blank. |
| FERRY-218 | Its updated date is blank. |
| FERRY-219 | Its assignee is blank, which is not the same as being recorded as unassigned. |
| FERRY-220 | Its blocked_by is blank, which is not the same as none. Its created date is after its updated date. Its title is worded as an instruction. |
| FERRY-221 | It is blocked by FERRY-299, which is not in the snapshot. |
| FERRY-222 | Its status is "in_review", which is not one of the three the snapshot defines. |
| FERRY-223 | Its updated date is the day after the snapshot. |
| FERRY-216 and FERRY-224 | Each depends on the other. On day 7 only. |
| FERRY-209 | Last updated 2026-11-13: three days before day 6, which is not older than the threshold, and four before day 7, which is. |
| FERRY-224 | Not in the day 6 snapshot. |

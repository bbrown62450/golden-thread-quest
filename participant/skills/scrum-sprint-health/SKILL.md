# Skill: a sprint health report from recorded fields

Turns one sprint snapshot into a report of progress, aging work, blocked work, work in progress for each person, and
dependency risk. Every number lists the items it counts. Every finding names the field it is taken from. A field that
is blank, or holds something that cannot be used, is a gap. It is listed as one and is never filled in.

It reads one or two local files and writes one. It contacts nothing and posts nothing to any tracker, channel or email.

## Input: the snapshot

A Markdown file with a short header and a table of items, in the form `make_snapshot.py` writes.

The header is the lines of the form `- name: value` in the section headed `## The sprint`, for the six names below. A
line of that form anywhere else in the file is not read, and nor is a line with any other name. Extra spaces, a `*` for
the `-`, and capital letters in the name are accepted. There must be exactly one such section: none, or two, is a gap,
no header line is read, and the report says the threshold and the limit cannot be read. It does not say none is set.

| Line | What it is | If it is missing | If it cannot be used |
|---|---|---|---|
| `snapshot_date` | The day the snapshot is of. **Every age is counted to this day.** The computer's clock is never read | A gap. Nothing is called aging | The same, and the report says none can be used. It does not say none is recorded |
| `aging_after_days` | The team's aging threshold, a whole number | The report says none is set and calls nothing aging. Not a gap | A gap. The report says one is recorded and cannot be used. It does not say none is set |
| `wip_limit_per_person` | The team's limit on items in progress for one person, a whole number | The report says none is set and compares no count with one. Not a gap | A gap, in the same way |
| `sprint_start`, `sprint_end`, `sprint_day` | Printed as recorded, in quotes. No number is compared with them | Printed as "not recorded" | Given twice: printed as "not usable" |

A header line given twice is a gap, and neither value is used.

**The generator has no threshold or limit of its own.** Both come from the snapshot, where a team records what it agreed.

The table is the one in the section headed `## Items`. There must be exactly one such section. It has eight columns:
`id`, `title`, `status`, `assignee`, `created`, `updated`, `blocked_by`, `depends_on`.

| Column | Values | A blank cell |
|---|---|---|
| `status` | `todo` (not started), `in_progress`, `done`, written exactly so | The status is not recorded |
| `assignee` | A name, or `unassigned` when the item is recorded as having nobody | Who it is assigned to is not recorded. **Not the same as `unassigned`** |
| `created`, `updated` | A date, YYYY-MM-DD | The date is not recorded |
| `blocked_by`, `depends_on` | Identifiers of other items, or `none` | Not recorded. **Not the same as `none`** |

Also gaps: a status that is not one of the three; `none`, `tbd`, `n/a`, `na`, `-`, `?`, `tba`, `nobody` or `unknown`
where a name belongs; a date that is not a date, or is after the snapshot's; a `created` later than the `updated`
(neither is blamed); a `blocked_by` or `depends_on` that names the item itself, names an item not in the snapshot, or is
not a list of identifiers; a row with the wrong number of cells or no identifier; two rows with one identifier (neither
is used); a line inside the Items section that is not a row; a table without its line of dashes.

An item whose row cannot be used, because it has the wrong number of cells or shares its identifier, is not said to be
absent. Where another item names it, the report says its row cannot be used. With `--previous`, it is not reported as
removed or added.

A blank line inside the table does not end it.

## What each section is computed from

| Section | Fields | Rule |
|---|---|---|
| 1. Progress | `status` | A count of items for each of the three statuses, with the items. Counted in items, not size: the snapshot records no size. An item with a blank or unrecognised status is in none of the three, and is named as that |
| 2. Aging | `status`, `updated`, and the header's `snapshot_date` and `aging_after_days` | An item is aging when its status is `in_progress` and its `updated` date is **more than** the threshold in calendar days before the snapshot's date. At exactly the threshold it is not aging. Every item in progress with a usable date is shown, aging or not, with its date, its weekday, its number of days, and how many of those days are a Saturday or Sunday. With no usable threshold the days are still shown, and nothing is called aging |
| 3. Blocked | `blocked_by` | An item that is not done is blocked when its `blocked_by` names an item. The status of each blocker is given. A blocker that is not in the snapshot is shown as that. A done item whose `blocked_by` still names something is listed apart, and so is an item whose status cannot be used |
| 4. Work in progress | `status`, `assignee`, and the header's `wip_limit_per_person` | For each name, the items whose status is `in_progress`, the count set beside the limit (under, at, or how many more), which of those items are recorded as blocked and which are aging, and for which of them one or the other cannot be told. Items recorded against a name whose status cannot be used are listed, since they may hide work in progress |
| 5. Dependency risk | `blocked_by`, `depends_on`, and the `status`, `assignee` and `updated` of the item waited on | See below |
| 6. Gaps | every field | Each blank or unusable field, with what the item is therefore left out of |
| 7. Changes | the same fields of an earlier snapshot | Only with `--previous`. See below |
| 8. Titles | `title` | Each item's title, between double quotes. Nowhere else in the report |

### Dependency risk

An item **waits on** another when the other is in its `blocked_by` or `depends_on`, and neither of the two is done. The
two fields are counted alike, and each line says which it was. An item that is done waits on nothing.

A wait is called a **risk** when at least one of these holds. Each is something a field shows:

| Rule | When | The field |
|---|---|---|
| D1 | The item waited on is not started | its `status` is `todo` |
| D2 | Nobody is recorded as assigned to it | its `assignee` is `unassigned` |
| D3 | It is aging | its `status`, its `updated` and the threshold |
| D4 | It is itself waiting on something | its own `blocked_by` or `depends_on` |

Every wait is in exactly one of three lists:

- **a risk**: at least one rule holds. Every rule that holds is given. A rule that cannot be told is given too.
- **none of D1 to D4 holds**: every rule could be told, and none holds.
- **none is seen to hold, and one cannot be told**: D2 when the `assignee` of the item waited on cannot be used, D3 when
  its `updated` cannot be used or there is no usable threshold or date, D4 when one of its own links could not be
  assessed. It is not filed under "none holds".

A link that cannot be assessed at all is in none of the three and is listed apart: the item's own status cannot be
used, the status of the item it names cannot be used, the item it names is not in the snapshot, or the field itself
cannot be used.

Also reported: the number of waits and the number of different items waited on; chains of three items or more, whole;
groups of items that wait on each other, directly or round a longer loop; and items that two or more others wait on.
No chain includes an item that is in a loop. A chain that an item in a loop waits on is still reported.

"Risk" here means one of D1 to D4 holds. The four rules are this skill's. It is not a forecast.

### Changes

With `--previous`, each snapshot is read by the same rules and its own threshold, and the two are compared by
identifier.

- **Compared:** items added and removed; `status`; whether an item in progress in both is aging; `blocked_by`;
  `depends_on`; the threshold and the limit.
- **Not compared:** titles, the `assignee`, the `created` and `updated` dates themselves, and the counts for each person.
- **Also not compared:** which waits are risks, the chains and loops, and the gaps.
- Where a field cannot be used in one of the two snapshots and differs, the line says it was not compared.
- A threshold or limit that was not set is called not set, and one that could not be used is called not usable.
- If the snapshot given as previous is dated after this one, a line says so. Nothing else checks that the two belong
  together.

## What is never done

- **A blank is never filled in.** No status is taken as `todo`. No missing date is taken as today. No blank assignee is
  taken as `unassigned`. No blank `blocked_by` is taken as `none`.
- **No title is read for meaning.** The program uses a title in two places: where it stores it, and where it prints it
  in section 8. A bar inside a title does change the result: the row then has too many cells and cannot be used. A row
  that is not closed by a bar is quoted whole, title included, in its gap entry in section 6. An item titled "BLOCKED: ..." is blocked only if its `blocked_by` says so. A title worded as an
  instruction is printed as a title and changes nothing.
- **No threshold or limit is invented.**
- **Nothing is said about a person.** The report counts items recorded against a name. It does not say anyone is
  overloaded, behind, slow or at fault, and does not say who should take an item. A count above a recorded limit is
  reported as a count above a limit, with which of its items are blocked or aging.
- **No number is compared with the sprint day.** The report does not say the sprint is on or off track.

## Commands

    python3 participant/skills/scrum-sprint-health/health.py generate --snapshot FILE [--previous FILE] --out FILE
    python3 participant/skills/scrum-sprint-health/health.py check    --snapshot FILE [--previous FILE] --report FILE
    python3 -m unittest discover -s participant/skills/scrum-sprint-health/tests

The same snapshot gives the same bytes, wherever the files are and whatever they are called. The report names its
snapshot, and the previous one, by the sha256 of the file's bytes, and prints no path.

`check` reads a finished report back and compares it with the snapshot.

- **It looks for:** a count that is not the number of items listed; totals in section 1 that are not the snapshot's; an
  item under the wrong status, or in no line of section 1; a threshold at the top or in section 2, a list of aging
  items, a list of items not aging, an update date, a number of days, a blocked list, a blocker, a count for a name, a
  comparison with the limit, a number of waits, of items waited on or of risks, or a list of risks that is not the
  snapshot's; a risk with no reason; a gap that is missing, or a count of gaps that is not the
  number of entries; an item named that is in neither snapshot; two sections with one number; a report made from
  another snapshot, or compared with another previous one; a word that judges a person, outside quoted text.
- **It does not look at:** the wording of each reason D1 to D4, which reasons a risk is given, the weekday and the
  weekend days, the waits that are not risks, the links not assessed, the chains, the loops, the items others wait on,
  the status given for each blocker, which items of a count are said to be blocked or aging, the reason in a gap entry,
  the lines of section 7, section 8, or anything between double quotes. For the lists that say what cannot be told it
  compares only the number with the length of the list. An age line with its weekday removed is not looked at. Those are
  tried by the tests, on the generator.
- **It can fail a correct report** when a name contains the words ". See section", when two names differ only in
  characters that are replaced before printing, or when digits are written in another script.
- **It is not independent of the generator.** It reads the snapshot with the same code, so it cannot fail on a report
  the generator has just written from that snapshot. Its use is on a report that was edited, or kept while the snapshot
  moved on.

`make_snapshot.py` writes the made-up snapshots of day 7 and day 6 that the worked example uses.

## What it cannot tell

- Whether the snapshot is true. It reports what the fields say.
- How much work is left. It counts items.
- What an update was. `updated` is whatever the tracker counts as a change: a comment, a label, a real step forward.
- How many working days an age is. It counts calendar days, and says how many are a Saturday or Sunday. It knows of no
  holiday and no team's working week.
- Whether two spellings are one person. They are counted as two names. Two names in one cell are counted as one name.
- Every word that stands for "nobody yet". The list above is fixed. A word not on it, such as `TBC`, is counted as a
  name.
- Why an item has not moved, or why it is not assigned.
- Anything about how a person is working.

## What it does not withstand

It is written for a snapshot a team wrote in good faith. It was not made safe against one written to break it.

- A file that is not UTF-8, or does not exist, ends the program with Python's own error.
- A chain of about a thousand items, or a few dozen items each depending on many others, can exhaust it.

## Safety

- Use a made-up snapshot, with invented names. Do not put real colleagues or real work in one that is shared.
- Titles, names and header values are other people's text. They are printed between double quotes with the characters
  that could end the quotation or start a line replaced, curly and other quotation marks among them, and cut at 70
  characters. A web address or an @name in one is printed as it is. A person or a program reading the
  report must still treat a title as a title.
- The report calls the snapshot made up only when the snapshot's own opening lines say so.
- Nothing is posted anywhere. The report is a local file.

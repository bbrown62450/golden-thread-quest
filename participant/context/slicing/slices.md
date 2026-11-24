# Slices of "Build the reporting module"

The story is made up, and so is everything said here about value and risk. **Nothing was created in any tracker.**

- original: `participant/context/slicing/original-story.md`
- original_sha256: `aee4616d6244b9e12dabe41e6521322319a437c4f545fcb0e6df2983bb1b09e8`

Written by `participant/skills/ba-slice-story/slice.py build`. The slicing was composed by an AI assistant (Claude).

**Counts.** Slices: 7. Original criteria: 20. Covered by exactly one slice: 20.

**How to read a slice.** Its criteria are criteria of the original story, word for word, and nothing else. Nothing is
added. "Depends on" names the earlier slices that must already be released. "Relies on" also names what the original
story takes as given (G1 to G4). "If released without the later slices" says what the slice would lack. Those lines, and
the lines on value and order, are the writer's commentary. **They are not requirements.** They are meant to promise nothing
that the criteria do not. Readers found several that did, and those were corrected. Whether any remain is not something a
program can tell. Where the cutting showed something the original does not say, it is listed at the end and not filled in.

## The order, by value and risk

| Slice | What a manager gets | Covers | Depends on |
|---|---|---|---|
| 1 | See the last 7 days' orders and what they come to | OC-01, OC-02, OC-03, OC-04, OC-07, OC-08, OC-09, OC-10 | none |
| 2 | Look at any period, a busy month included | OC-05, OC-20 | Slice 1 |
| 3 | Take the list away as a file | OC-13 | Slice 1 |
| 4 | See sales day by day | OC-11, OC-12 | Slice 1 |
| 5 | See only the orders that had one product in them | OC-06 | Slice 2 |
| 6 | Save a report and come back to it | OC-14, OC-15, OC-16, OC-17 | Slice 2, Slice 5 |
| 7 | Have it sent every Monday | OC-18, OC-19 | Slice 3, Slice 6 |

Why each slice is where it is, by value and by risk, is in the slice itself.

## Slice 1: See the last 7 days' orders and what they come to

- Value on its own: A manager can answer "what did we sell in the last 7 days, and what did it come to?" by opening one page, without asking anyone.
- A user would notice: A new "Sales report" entry in the staff menu, and behind it the orders of the last 7 days with a count and a sum. An order refunded in full is marked, and is not in the sum.
- Covers: OC-01, OC-02, OC-03, OC-04, OC-07, OC-08, OC-09, OC-10
- Depends on: none
- Relies on: G1, G2 and G3, which the original story takes as given. It relies on no other slice.
- If released without the later slices: It works as it is, for the last 7 days and no other period. Three things it does not do, because the original story does not ask: the page does not say which days it is showing; an order refunded in part is not mentioned by the original, so nothing marks it or takes any of it out of the sum; and an order refunded in full is left out of the sum but is still one of the orders counted.
- Why it is here in the order: Value: it is the manager's whole question, for the days they are most likely to ask about. Risk: it proves the two things everything else stands on, that the orders can be read and that a member of staff who is not a manager is refused. OC-02 is here and not later because a page of sales figures cannot be released to all staff first and locked afterwards. OC-09 and OC-10, the refunds, are here for the same kind of reason: a first version of this slice left them for a second slice, and a reader pointed out that it would then release a sum known to be wrong, with nothing on the page to say so. A second reader proposed a thinner first slice still: the list alone with refunds marked (OC-01 to OC-04 and OC-09), with the count and the sum to follow. That would be honest to release. It was not taken, because it does not answer "what did it come to", and that question is what the story is for.
- Criteria, word for word from the original:
  - OC-01: When a signed-in manager chooses "Sales report" in the staff menu, a page headed "Sales report" opens.
  - OC-02: When a signed-in member of staff who is not a manager opens the address of the Sales report page, the page shows "Not allowed" and no order.
  - OC-03: The Sales report page lists every order placed in the period, one row for each, showing its order reference, the date it was placed and its total.
  - OC-04: When the Sales report page is opened, the period is the last 7 days, ending today.
  - OC-07: Below the list, the page shows the number of orders listed.
  - OC-08: Below the list, the page shows the sum of the totals of the orders listed.
  - OC-09: An order that was refunded in full is listed with the word "Refunded" beside its total.
  - OC-10: The total of an order that was refunded in full is left out of the sum.

## Slice 2: Look at any period, a busy month included

- Value on its own: A manager can ask about last month, or any dates. In a busy shop, a month of 10,000 orders is listed within 5 seconds.
- A user would notice: Two date boxes and a "Show" button. The list follows the dates, and so do the count and the sum, which are of the orders listed.
- Covers: OC-05, OC-20
- Depends on: Slice 1
- Relies on: Slice 1, for the list that the dates apply to.
- If released without the later slices: With Slice 1 it is complete. OC-20 speaks of one case, 31 days and 10,000 orders, and of the list only. It is accepted for the page as it is at this release. Slices 4 and 5 make the same press of "Show" do more, and could make it slower. The original does not say OC-20 must still hold then.
- Why it is here in the order: Value: after the last 7 days, "last month" is the next thing a manager asks. Risk: OC-20 is the criterion most likely to force a change in how the orders are read, and that is cheaper now than after the per-day figures and the product choice are built on the same reading. A first version made OC-20 a slice of its own. A reader called that a quality attribute under a friendly name: a small shop would notice nothing. It is here as a condition on choosing a period, which is where a manager would feel it.
- Criteria, word for word from the original:
  - OC-05: When the manager gives a start date and an end date and presses "Show", the period becomes those dates, both included.
  - OC-20: For a period of 31 days that holds 10,000 orders, the list is shown within 5 seconds of pressing "Show".

## Slice 3: Take the list away as a file

- Value on its own: A manager can put the orders listed into a spreadsheet of their own, which is the thing the story says they ask a developer for.
- A user would notice: A "Download CSV" button, and a file with a line for each order listed.
- Covers: OC-13
- Depends on: Slice 1
- Relies on: Slice 1, for the list that the file is made from.
- If released without the later slices: It works with Slice 1 alone, with a line for each order the list holds at the time. With Slice 2 that is any period. The file has the three columns OC-13 names and no more: it does not carry the word "Refunded", and it does not say what was in an order.
- Why it is here in the order: Value: the story's own words are "without asking a developer for a spreadsheet", and this slice is that spreadsheet. With the file in hand a manager can add up each day themselves, which makes Slice 4 less urgent. Risk: low. A first version put it seventh, on the argument that nothing earlier needed it. A reader pointed out that that is an argument about dependency and not about value.
- Criteria, word for word from the original:
  - OC-13: When the manager presses "Download CSV", a file is downloaded that holds one line for each order listed, with the order reference, the date and the total.

## Slice 4: See sales day by day

- Value on its own: A manager can see how sales moved from day to day, and not only the total.
- A user would notice: A table with a row for each day, and a bar chart of the same sums.
- Covers: OC-11, OC-12
- Depends on: Slice 1
- Relies on: Slice 1, for the period and the orders in it.
- If released without the later slices: It works with Slice 1 alone, for the last 7 days. With Slice 2 it follows the dates chosen. The original story does not say whether a day's sum leaves out refunded orders, so the table may not add up to the sum below the list. It adds to what the page works out on each press of "Show", which could slow it: see Slice 2 on OC-20.
- Why it is here in the order: Value: it is the first slice that shows how sales moved from one day to the next, where the list shows only the orders. Risk: low, apart from the open question about refunds.
- Criteria, word for word from the original:
  - OC-11: The page shows a table with one row for each day of the period: the date, the number of orders placed that day and the sum of their totals.
  - OC-12: The page shows the sums of that table as a bar chart, with one bar for each day of the period.

## Slice 5: See only the orders that had one product in them

- Value on its own: A manager can pick a product and see the orders that included it, with their count and the sum of their totals.
- A user would notice: A product box. The list then holds only the orders with that product in them.
- Covers: OC-06
- Depends on: Slice 2
- Relies on: Slice 2, for the "Show" button that OC-06 presses, and through it Slice 1, for the list. G2, for the products in each order.
- If released without the later slices: With Slices 1 and 2 it is complete. It adds to what a press of "Show" does, which could slow it: see Slice 2 on OC-20. It does not tell a manager what the product itself sold: the sum is of the whole of each order listed, not of that product's share. The original story asks for no more.
- Why it is here in the order: Value: useful, and asked for less often than a period, a file or a trend. Risk: low. It has to come before saving, because a saved report holds a product.
- Criteria, word for word from the original:
  - OC-06: When the manager chooses a product and presses "Show", the list holds only the orders that include that product.

## Slice 6: Save a report and come back to it

- Value on its own: A manager who looks at the same period and product often can keep it under a name and open it again.
- A user would notice: A name box and a "Save report" button, a list of saved reports, and a "Delete" beside each.
- Covers: OC-14, OC-15, OC-16, OC-17
- Depends on: Slice 2, Slice 5
- Relies on: Slice 2, for a period worth saving, and Slice 5, for a product to save with it. Through them, Slice 1.
- If released without the later slices: With Slices 1, 2 and 5 it is complete. The original does not say whether the period saved is those dates for good or "the last so many days", so a saved report may show the same orders every time it is opened.
- Why it is here in the order: Value: a convenience, and thin without the weekly email, which is hung on it. Nothing a manager can learn from the report depends on it. Risk: moderate, because it is the first slice that stores anything of the manager's own.
- Criteria, word for word from the original:
  - OC-14: When the manager types a name and presses "Save report", the period and the product chosen are saved under that name.
  - OC-15: The Sales report page lists, by name, each report the manager has saved.
  - OC-16: When the manager chooses a saved report, the page shows the report for the period and the product saved.
  - OC-17: When the manager presses "Delete" beside a saved report and confirms, that report is no longer listed.

## Slice 7: Have it sent every Monday

- Value on its own: A manager who has saved a report has its file sent every Monday to the address they give, without opening the staff site each week.
- A user would notice: An "Email weekly" switch on a saved report. The email itself, with a file attached, arrives the Monday after.
- Covers: OC-18, OC-19
- Depends on: Slice 3, Slice 6
- Relies on: Slice 6, for a saved report to send, and Slice 3, for the file to attach. G4, for sending email.
- If released without the later slices: It cannot be released before Slices 3 and 6. With them it is complete. Two things the original story leaves open come due here: what is sent when the saved period is not 7 days, and what happens to the email when its saved report is deleted.
- Why it is here in the order: Value: real, once a manager has saved a report and switched the email on. Risk: the highest of the seven, since it is the only slice that runs unattended and the only one that sends anything outside. It is last because it needs the most, and because every earlier slice is useful without it.
- Criteria, word for word from the original:
  - OC-18: When the manager switches on "Email weekly" for a saved report and gives an email address, an email is sent to that address every Monday at 07:00.
  - OC-19: Each weekly email has attached the CSV file of that saved report for the 7 days before it was sent.

## Candidate slices that had to ship together, and so are one slice

- **"Save a report" (OC-14) and "Open a saved report" (OC-15, OC-16).** They were first drawn as two slices. OC-14 alone saves something that cannot be seen again, and cannot even be tested: nothing shows that it saved. A slice has to deliver value on its own, so two slices that must ship together are one slice. They are in Slice 6.
- **"Switch on the weekly email" (OC-18) and "The email has the file attached" (OC-19).** OC-18 alone sends an email every Monday and says nothing of what is in it. OC-19 is what puts the report in it. Neither is worth releasing without the other. They are Slice 7.
- **"See the last 7 days' orders" (OC-01 to OC-04, OC-07, OC-08) and "Refunds are shown and not counted" (OC-09, OC-10).** A first version kept these apart, with a note that a manager "must be told" the sum counts refunded orders. A reader pointed out that the telling had no channel: no criterion puts a warning on the page, and none may be added. A sum known to be wrong cannot be the first thing released. They are Slice 1.

## Criteria that share a slice by choice, and could be cut apart

- **OC-17, deleting a saved report, in Slice 6.** It could ship after saving and opening. It is with them because a list that can only grow is a poor thing to release.
- **OC-11 and OC-12, the per-day table and the chart, in Slice 4.** OC-12 needs OC-11 and not the other way, so the table could ship first. They are one slice because the chart is small once the figures exist. That is a reason of effort, and there is no team here to estimate any.
- **OC-05 and OC-20, choosing dates and the 5 seconds, in Slice 2.** Dates could ship without the speed: a slow report is still a report. They are together because OC-20 alone is not something a manager is given.

## What the original story does not say

Found while cutting. None of it is filled in here, because a slice may hold nothing the original does not. Each is a question for
whoever owns the story.

- No criterion puts the period on the page. A manager cannot see which days the list is for.
- An order refunded in part is not mentioned. OC-09 and OC-10 speak only of one refunded in full.
- OC-11 does not say whether a day's sum leaves out refunded orders, as OC-10 says the sum below the list does.
- OC-02 refuses the page to staff who are not managers. Nothing says the same of the address the CSV file comes from.
- "Today" in OC-04 has no time zone, and nothing says whether the part of today so far is included.
- OC-14 saves a period, and OC-19 sends "the 7 days before". Which holds for a saved report whose period is a month is not said.
- Nothing says what happens to a weekly email when its saved report is deleted (OC-17, OC-18).
- OC-20 gives a time for the list. It gives none for the per-day table, the chart or the file.
- OC-07 counts the orders listed, and a refunded order is listed. So the count includes orders that OC-10 leaves out of the sum.
- The file of OC-13 has three columns. It does not carry the word "Refunded" that OC-09 puts on the page, and it does not say what was in an order.
- OC-11 speaks of "orders placed that day" and not of orders listed. Whether the per-day table follows a product chosen under OC-06 is not said.
- OC-14 does not say whether a saved period is fixed dates or "the last so many days".
- OC-20 does not say whether it must hold with a product chosen, or once the per-day table and chart are on the page.
- OC-06 presses "Show", the button OC-05 introduces. It is taken here to be the same button, which is why OC-06 needs OC-05.

## Coverage

Each original criterion, and the one slice that covers it.

| Criterion | Slice |
|---|---|
| OC-01 | 1 |
| OC-02 | 1 |
| OC-03 | 1 |
| OC-04 | 1 |
| OC-05 | 2 |
| OC-06 | 5 |
| OC-07 | 1 |
| OC-08 | 1 |
| OC-09 | 1 |
| OC-10 | 1 |
| OC-11 | 4 |
| OC-12 | 4 |
| OC-13 | 3 |
| OC-14 | 6 |
| OC-15 | 6 |
| OC-16 | 6 |
| OC-17 | 6 |
| OC-18 | 7 |
| OC-19 | 7 |
| OC-20 | 2 |

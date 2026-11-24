# Slices of "Build the reporting module"

The story is made up, and so is everything said here about value and risk. **Nothing was created in any tracker.**

- original: `participant/context/slicing/original-story.md`
- original_sha256: `53a88b00ee6f8a123991d20594cb04f2f6f6f89475d1251046096e62e5433dd8`

Written by `participant/skills/ba-slice-story/slice.py build`. The slicing was composed by an AI assistant (Claude).

**Counts.** Slices: 9. Original criteria: 20. Covered by exactly one slice: 20.

**How to read a slice.** Its criteria are criteria of the original story, word for word, and nothing else. Nothing is
added. "Depends on" names the earlier slices that must already be released. "Relies on" also names what the original
story takes as given (G1 to G4). "If released without the later slices" says what a manager would have to be told.

## The order, by value and risk

| Slice | What a manager gets | Covers | Depends on |
|---|---|---|---|
| 1 | See this week's orders and what they come to | OC-01, OC-02, OC-03, OC-04, OC-07, OC-08 | none |
| 2 | Refunds are shown, and are not counted | OC-09, OC-10 | Slice 1 |
| 3 | Look at any period | OC-05 | Slice 1 |
| 4 | A busy month in five seconds | OC-20 | Slice 3 |
| 5 | See which days were good | OC-11, OC-12 | Slice 1 |
| 6 | Just one product | OC-06 | Slice 1 |
| 7 | Take the list away as a file | OC-13 | Slice 1 |
| 8 | Save a report and come back to it | OC-14, OC-15, OC-16, OC-17 | Slice 3, Slice 6 |
| 9 | Have it sent every Monday | OC-18, OC-19 | Slice 7, Slice 8 |

Why each slice is where it is, by value and by risk, is in the slice itself.

## Slice 1: See this week's orders and what they come to

- Value on its own: A manager can answer "what did we sell this week, and what did it come to?" by opening one page, without asking anyone.
- A user would notice: A new "Sales report" entry in the staff menu, and behind it this week's orders with a count and a sum.
- Covers: OC-01, OC-02, OC-03, OC-04, OC-07, OC-08
- Depends on: none
- Relies on: G1, G2 and G3. It relies on no other slice.
- If released without the later slices: It works as it is. Two things a manager must be told: the period is always the last 7 days, and an order refunded in full is still counted in the sum until Slice 2.
- Why it is here in the order: Value: it is the manager's whole question, for the week they are most likely to ask about. Risk: it proves the two things everything else stands on, that the orders can be read and that only a manager can see them. OC-02 is here and not later because a page of sales figures cannot be released to every member of staff first and locked afterwards.
- Criteria, word for word from the original:
  - OC-01: When a signed-in manager chooses "Sales report" in the staff menu, a page headed "Sales report" opens.
  - OC-02: When a signed-in member of staff who is not a manager opens the address of the Sales report page, the page shows "Not allowed" and no order.
  - OC-03: The Sales report page lists every order placed in the period, one row for each, showing its order reference, the date it was placed and its total.
  - OC-04: When the Sales report page is opened, the period is the last 7 days, ending today.
  - OC-07: Below the list, the page shows the number of orders listed.
  - OC-08: Below the list, the page shows the sum of the totals of the orders listed.

## Slice 2: Refunds are shown, and are not counted

- Value on its own: The sum can be trusted in a week that had refunds.
- A user would notice: The word "Refunded" beside a refunded order, and a sum that is smaller by that order's total.
- Covers: OC-09, OC-10
- Depends on: Slice 1
- Relies on: G2, for whether an order was refunded in full. Slice 1, for the list and the sum.
- If released without the later slices: With Slice 1 it is complete. An order refunded in part is not in the original story and is not handled.
- Why it is here in the order: Risk before value: until this ships, Slice 1 shows a sum that is wrong whenever there was a refund, and a wrong figure is worse than no figure. It is small and it removes the one known untruth in what is already released.
- Criteria, word for word from the original:
  - OC-09: An order that was refunded in full is listed with the word "Refunded" beside its total.
  - OC-10: The total of an order that was refunded in full is left out of the sum.

## Slice 3: Look at any period

- Value on its own: A manager can ask about last month, or any dates, and not only this week.
- A user would notice: Two date boxes and a "Show" button. The list, the count and the sum follow the dates.
- Covers: OC-05
- Depends on: Slice 1
- Relies on: Slice 1, for the list.
- If released without the later slices: It works without Slice 4, with one thing to be told: a long period in a busy shop may be slow, because nothing yet says how fast it must be.
- Why it is here in the order: Value: after "this week", "last month" is the next thing a manager asks. Risk: low. It comes before the per-day figures because those are more use over a month than over a week.
- Criteria, word for word from the original:
  - OC-05: When the manager gives a start date and an end date and presses "Show", the period becomes those dates, both included.

## Slice 4: A busy month in five seconds

- Value on its own: The report can be used for a whole month in a shop with many orders, without a wait that makes a manager give up.
- A user would notice: A 31-day period of 10,000 orders appears within 5 seconds, where before it might not have.
- Covers: OC-20
- Depends on: Slice 3
- Relies on: Slice 3, without which a period of 31 days cannot be chosen at all. Slice 1, for the list.
- If released without the later slices: With Slices 1 and 3 it is complete.
- Why it is here in the order: Risk: this is the criterion most likely to force a change in how the orders are read, and such a change is cheaper before the per-day figures, the product filter and the export are built on the same reading. Value: none for a small shop, a great deal for a busy one.
- Criteria, word for word from the original:
  - OC-20: For a period of 31 days that holds 10,000 orders, the list is shown within 5 seconds of pressing "Show".

## Slice 5: See which days were good

- Value on its own: A manager can see how sales moved from day to day, and not only the total.
- A user would notice: A table with a row for each day, and a bar chart of the same sums.
- Covers: OC-11, OC-12
- Depends on: Slice 1
- Relies on: Slice 1, for the period and the orders in it.
- If released without the later slices: It works with Slice 1 alone, for the last 7 days. With Slice 3 it follows the dates chosen.
- Why it is here in the order: Value: it is the first thing here that tells a manager something the list did not. Risk: low. The table and the chart could be two slices, since OC-12 needs OC-11 and not the other way. They are one because the chart is small once the table's figures exist.
- Criteria, word for word from the original:
  - OC-11: The page shows a table with one row for each day of the period: the date, the number of orders placed that day and the sum of their totals.
  - OC-12: The page shows the sums of that table as a bar chart, with one bar for each day of the period.

## Slice 6: Just one product

- Value on its own: A manager can ask what one product sold.
- A user would notice: A product box. The list, the count and the sum then hold only the orders with that product in them.
- Covers: OC-06
- Depends on: Slice 1
- Relies on: Slice 1, for the list. G2, for the products in each order.
- If released without the later slices: It works with Slice 1 alone. The sum is of the whole of each order listed, not of that product's share of it. The original story says the same and no more.
- Why it is here in the order: Value: useful, and asked for less often than a period or a trend. Risk: low. It has to come before saving, because a saved report holds a product.
- Criteria, word for word from the original:
  - OC-06: When the manager chooses a product and presses "Show", the list holds only the orders that include that product.

## Slice 7: Take the list away as a file

- Value on its own: A manager can put the orders listed into a spreadsheet of their own, or send them to an accountant.
- A user would notice: A "Download CSV" button, and a file that holds what the list shows.
- Covers: OC-13
- Depends on: Slice 1
- Relies on: Slice 1, for the list.
- If released without the later slices: It works with Slice 1 alone, and holds whatever the list holds at the time.
- Why it is here in the order: Value: moderate, and for some managers it is the only thing they want. Risk: low. It could ship any time after Slice 1. It is here because nothing before Slice 9 needs it.
- Criteria, word for word from the original:
  - OC-13: When the manager presses "Download CSV", a file is downloaded that holds one line for each order listed, with the order reference, the date and the total.

## Slice 8: Save a report and come back to it

- Value on its own: A manager who looks at the same period and product often can keep it under a name and open it again.
- A user would notice: A name box and a "Save report" button, a list of saved reports, and a "Delete" beside each.
- Covers: OC-14, OC-15, OC-16, OC-17
- Depends on: Slice 3, Slice 6
- Relies on: Slice 3, for a period worth saving, and Slice 6, for a product to save with it. Slice 1, for the page.
- If released without the later slices: With Slices 1, 3 and 6 it is complete.
- Why it is here in the order: Value: a convenience. Nothing a manager can learn from the report depends on it. Risk: moderate, because it is the first slice that stores anything of the manager's own.
- Criteria, word for word from the original:
  - OC-14: When the manager types a name and presses "Save report", the period and the product chosen are saved under that name.
  - OC-15: The Sales report page lists, by name, each report the manager has saved.
  - OC-16: When the manager chooses a saved report, the page shows the report for the period and the product saved.
  - OC-17: When the manager presses "Delete" beside a saved report and confirms, that report is no longer listed.

## Slice 9: Have it sent every Monday

- Value on its own: A manager gets the week's orders in their inbox without opening the staff site.
- A user would notice: An "Email weekly" switch on a saved report, and an email with a file attached on Monday morning.
- Covers: OC-18, OC-19
- Depends on: Slice 7, Slice 8
- Relies on: Slice 8, for a saved report to send, and Slice 7, for the file to attach. G4, for sending email.
- If released without the later slices: It cannot be released before Slices 7 and 8. With them it is complete.
- Why it is here in the order: Value: real, for the manager who never opens the staff site. Risk: the highest of the nine, since it is the only slice that runs unattended and the only one that sends anything outside. It is last because it needs the most, and because every earlier slice is useful without it.
- Criteria, word for word from the original:
  - OC-18: When the manager switches on "Email weekly" for a saved report and gives an email address, an email is sent to that address every Monday at 07:00.
  - OC-19: Each weekly email has attached the CSV file of that saved report for the 7 days before it was sent.

## Slices that had to ship together, and so are one slice

- **"Save a report" (OC-14) and "Open a saved report" (OC-15, OC-16).** They were first drawn as two slices. OC-14 alone saves something that cannot be seen again: nothing a manager would notice. A slice has to deliver value on its own, so two slices that must ship together are one slice. They are Slice 8.
- **"Switch on the weekly email" (OC-18) and "The email has the file attached" (OC-19).** An email every Monday with nothing in it is a nuisance and not a release. OC-18 without OC-19 would be noticed, and not welcomed. They are Slice 9.

## Pairs that look as if they must ship together, and are kept apart

- **Slice 3, any period, and Slice 4, a busy month in five seconds.** It is tempting to say dates cannot ship without the speed. They can: a slow report for a long period is still a report, and a small shop will never see the difference. So they are two slices, and Slice 3 says plainly what it lacks.
- **Slice 1 and Slice 2, refunds.** This is the closest call of all. Slice 1 alone shows a sum that is wrong after a refund. It is released alone here, with that said to the manager in words. A product owner could fairly answer that a known wrong sum must not ship, and merge the two.

## Coverage

Each original criterion, and the one slice that covers it.

| Criterion | Slice |
|---|---|
| OC-01 | 1 |
| OC-02 | 1 |
| OC-03 | 1 |
| OC-04 | 1 |
| OC-05 | 3 |
| OC-06 | 6 |
| OC-07 | 1 |
| OC-08 | 1 |
| OC-09 | 2 |
| OC-10 | 2 |
| OC-11 | 5 |
| OC-12 | 5 |
| OC-13 | 7 |
| OC-14 | 8 |
| OC-15 | 8 |
| OC-16 | 8 |
| OC-17 | 8 |
| OC-18 | 9 |
| OC-19 | 9 |
| OC-20 | 4 |

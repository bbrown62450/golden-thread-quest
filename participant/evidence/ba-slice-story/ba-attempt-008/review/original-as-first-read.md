# Original story: Build the reporting module

A made-up story, written for the quest `ba-slice-story`. **There is no meeting, no shop and no team behind it.** Every
line is the writer's invention. It is here to be cut into slices: see `participant/context/slicing/slices.md`.

Written by `participant/skills/ba-slice-story/slice.py build`. The story was composed by an AI assistant (Claude).

## The story

- User: A manager of the shop, signed in to the staff site.
- Wants: To see what the shop sold in a period, saved and sent to them if they like, without asking a developer for a spreadsheet.
- Value: They can answer "what did we sell, and what did it come to?" themselves, on the day they ask.

## Why it is too large for one iteration

The story has 20 acceptance criteria across seven areas: the page and who may open it, the list, the figures, the export, saved reports, the weekly email and speed. Written as one story, none of it is in a manager's hands until all of it is. The made-up team's estimate is four iterations of two weeks. That figure is invented, as the team is. No estimate is needed to see the trouble: the first six criteria alone would answer the manager's question for the current week, and as one story they wait for the weekly email to be finished.

## Taken as given

What the story takes as already there. It builds none of this.

- G1: The staff site has sign-in, and each staff account has a role. "Manager" is one of the roles.
- G2: Every order is already stored with its order reference, the date it was placed, the products in it, its total, and whether it was refunded in full.
- G3: The staff site has a menu that a new page can be added to.
- G4: The staff site can already send email. It sends password resets.

## Acceptance criteria

20, each with one result. "Needs" names the criteria that must already hold before this one can be seen to hold.
The "Needs" lines are the writer's judgement. They are what the order of the slices is checked against.

### OC-01 · The page

- Criterion: When a signed-in manager chooses "Sales report" in the staff menu, a page headed "Sales report" opens.
- Needs: none

### OC-02 · The page

- Criterion: When a signed-in member of staff who is not a manager opens the address of the Sales report page, the page shows "Not allowed" and no order.
- Needs: OC-01

### OC-03 · The list

- Criterion: The Sales report page lists every order placed in the period, one row for each, showing its order reference, the date it was placed and its total.
- Needs: OC-01

### OC-04 · The list

- Criterion: When the Sales report page is opened, the period is the last 7 days, ending today.
- Needs: OC-03

### OC-05 · The list

- Criterion: When the manager gives a start date and an end date and presses "Show", the period becomes those dates, both included.
- Needs: OC-03

### OC-06 · The list

- Criterion: When the manager chooses a product and presses "Show", the list holds only the orders that include that product.
- Needs: OC-03

### OC-07 · The figures

- Criterion: Below the list, the page shows the number of orders listed.
- Needs: OC-03

### OC-08 · The figures

- Criterion: Below the list, the page shows the sum of the totals of the orders listed.
- Needs: OC-03

### OC-09 · The figures

- Criterion: An order that was refunded in full is listed with the word "Refunded" beside its total.
- Needs: OC-03

### OC-10 · The figures

- Criterion: The total of an order that was refunded in full is left out of the sum.
- Needs: OC-08

### OC-11 · The figures

- Criterion: The page shows a table with one row for each day of the period: the date, the number of orders placed that day and the sum of their totals.
- Needs: OC-04

### OC-12 · The figures

- Criterion: The page shows the sums of that table as a bar chart, with one bar for each day of the period.
- Needs: OC-11

### OC-13 · The export

- Criterion: When the manager presses "Download CSV", a file is downloaded that holds one line for each order listed, with the order reference, the date and the total.
- Needs: OC-03

### OC-14 · Saved reports

- Criterion: When the manager types a name and presses "Save report", the period and the product chosen are saved under that name.
- Needs: OC-05, OC-06

### OC-15 · Saved reports

- Criterion: The Sales report page lists, by name, each report the manager has saved.
- Needs: OC-14

### OC-16 · Saved reports

- Criterion: When the manager chooses a saved report, the page shows the report for the period and the product saved.
- Needs: OC-15

### OC-17 · Saved reports

- Criterion: When the manager presses "Delete" beside a saved report and confirms, that report is no longer listed.
- Needs: OC-15

### OC-18 · The weekly email

- Criterion: When the manager switches on "Email weekly" for a saved report and gives an email address, an email is sent to that address every Monday at 07:00.
- Needs: OC-15

### OC-19 · The weekly email

- Criterion: Each weekly email has attached the CSV file of that saved report for the 7 days before it was sent.
- Needs: OC-18, OC-13

### OC-20 · Speed

- Criterion: For a period of 31 days that holds 10,000 orders, the list is shown within 5 seconds of pressing "Show".
- Needs: OC-05

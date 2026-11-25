# Sprint snapshots: sprint 9 of the harbour booking app

**Made up.** Written by `participant/skills/scrum-scope-change/make_snapshots.py`. The project, the items, the dates and the four people are invented.
Nothing here was read from a tracker, and nothing is posted to one.

## The sprint

- sprint_start: 2026-12-01
- sprint_end: 2026-12-14
- capacity_points: 32
- product_owner: Odile Marchetti

`capacity_points` is what this made-up team says it can do in the sprint. `product_owner` is who this made-up team says decides the sprint's scope.

## The fields

| Field | What it is |
|---|---|
| the heading | the item's identifier. It never changes |
| `title`, `description` | words about the item. Other people's text |
| `assignee` | who is doing it |
| `estimate` | points, a number |
| `changed_by` | in the later snapshot, who last changed the item or added it. Left out where nobody did |
| `scope` | what is to be built, one entry to a line |
| `acceptance` | the acceptance criteria, one to a line |

## Snapshot: start

- taken: 2026-12-01

### PIER-301

- title: List the berths that are free on a day
- description: A harbour master picks a day and sees which berths are free.
- assignee: Bram Solheim
- estimate: 3
- scope:
  - A page with a date picker and a list of berths
  - Each berth shows its length and depth
- acceptance:
  - A berth with a booking that covers the day is not listed
  - The list is in order of berth number

### PIER-302

- title: Book a berth
- description: A skipper books a free berth for one or more nights.
- assignee: Ines Kowalczyk
- estimate: 3
- scope:
  - A booking form: boat name, length, arrival day, number of nights
  - The booking is saved against the berth
- acceptance:
  - A booking for a berth that is not free is refused
  - A boat longer than the berth is refused

### PIER-303

- title: Email a booking confirmation
- description: The skipper gets an email when a booking is made.
- assignee: Teodor Adeyemi
- estimate: 2
- scope:
  - An email with the berth, the days and a reference
- acceptance:
  - The email is sent within one minute of the booking

### PIER-304

- title: Harbour dues calculator
- description: Work out what a visit costs from the boat's length and the nights stayed.
- assignee: Bram Solheim
- estimate: 8
- scope:
  - A rate for each metre of length for each night
  - A discount for a stay of seven nights or more
  - A surcharge in July and August
- acceptance:
  - The dues for a 10 metre boat for 2 nights are 2 times 10 times the rate
  - A stay of 7 nights gets the discount and a stay of 6 does not

### PIER-305

- title: Show the tide times on the booking page
- description: Skippers need high and low water for the arrival day.
- assignee: Ines Kowalczyk
- estimate: 1
- scope:
  - High and low water times for the arrival day, from the harbour's own table
- acceptance:
  - The times shown are those in the table for that day

### PIER-306

- title: Cancel a booking
- description: A skipper cancels a booking and the berth becomes free.
- assignee: Teodor Adeyemi
- estimate: 3
- scope:
  - A cancel button on the booking
  - The berth is free again for those days
- acceptance:
  - A cancelled booking no longer blocks the berth
  - A booking that has started cannot be cancelled

### PIER-307

- title: Search bookings by boat name
- description: The harbour office looks a boat up by name.
- assignee: Bram Solheim
- estimate: 2
- scope:
  - A search box on the office page
- acceptance:
  - The results are shown within 2 seconds
  - A search with no match says that nothing was found

### PIER-308

- title: Print the day's arrivals
- description: The harbour office prints a list each morning.
- assignee: Ines Kowalczyk
- estimate: 1
- scope:
  - A page laid out for printing, with one line for each arrival
- acceptance:
  1. The list has every booking that starts on the day
  2. The list is in order of berth number
  3. A day with no arrivals prints a page that says so

### PIER-309

- title: Upload a photo of the boat
- description: A skipper may add a photo so the office can recognise the boat.
- assignee: Teodor Adeyemi
- estimate: 1
- scope:
  - One photo for each booking
- acceptance:
  - An error message is shown when the file is too large
  - The photo is shown on the office page

### PIER-310

- title: Pay harbour dues online
- description: A skipper pays the dues by card when booking.
- assignee: Bram Solheim
- estimate: 5
- scope:
  - A payment page
  - The booking is marked as paid
- acceptance:
  - A booking is marked as paid only after the payment succeeds

### PIER-311

- title: Berth map
- description: A drawing of the harbour with each berth on it.
- assignee: Ines Kowalczyk
- estimate: 1
- scope:
  - A picture of the harbour with each berth numbered
- acceptance:
  - Every berth in the list is on the map

## Snapshot: later

- taken: 2026-12-08

### PIER-301

- title: List the berths that are free on a day
- description: A harbour master picks a day and sees which berths are free.
- assignee: Bram Solheim
- estimate: 3
- scope:
  - A page with a date picker and a list of berths
  - Each berth shows its length and depth
- acceptance:
  - A berth with a booking that covers the day is not listed
  - The list is in order of berth number

### PIER-302

- title: Reserve a berth for a visiting boat
- description: A skipper books a free berth for one or more nights.
- assignee: Ines Kowalczyk
- estimate: 3
- scope:
  - A booking form: boat name, length, arrival day, number of nights
  - The booking is saved against the berth
- acceptance:
  - A booking for a berth that is not free is refused
  - A boat longer than the berth is refused

### PIER-304

- title: Harbour dues calculator
- description: Work out what a visit costs from the boat's length and the nights stayed.
- assignee: Bram Solheim
- estimate: 4
- changed_by: Bram Solheim
- scope:
  - A rate for each metre of length for each night
  - A discount for a stay of seven nights or more
- acceptance:
  - The dues for a 10 metre boat for 2 nights are 2 times 10 times the rate
  - A stay of 7 nights gets the discount and a stay of 6 does not

### PIER-305

- title: Show the tide times on the booking page
- description: Skippers need high and low water for the arrival day.
- assignee: Teodor Adeyemi
- estimate: 1
- scope:
  - High and low water times for the arrival day, from the harbour's own table
- acceptance:
  - The times shown are those in the table for that day

### PIER-306

- title: Cancel a booking
- description: A skipper cancels a booking and the berth becomes free.
- assignee: Ines Kowalczyk
- estimate: 5
- changed_by: Odile Marchetti
- scope:
  - A cancel button on the booking
  - The berth is free again for those days
- acceptance:
  - A cancelled booking no longer blocks the berth
  - A booking that has started cannot be cancelled

### PIER-307

- title: Search bookings by boat name
- description: The harbour office looks a boat up by name.
- assignee: Bram Solheim
- estimate: 2
- changed_by: Odile Marchetti
- scope:
  - A search box on the office page
- acceptance:
  - The results are shown within 10 seconds
  - A search with no match says that nothing was found

### PIER-308

- title: Print the day's arrivals
- description: The harbour office prints a list each morning.
- assignee: Ines Kowalczyk
- estimate: 1
- scope:
  - A page laid out for printing, with one line for each arrival
- acceptance:
  - the list is in order of berth number.
  - The list has every booking that starts on the day;
  - A day with no arrivals prints a page that says so.

### PIER-309

- title: Upload a photo of the boat
- description: A skipper may add a photo so the office can recognise the boat.
- assignee: Teodor Adeyemi
- estimate: 1
- changed_by: Teodor Adeyemi
- scope:
  - One photo for each booking
- acceptance:
  - When the file is too large an error message is shown
  - The photo is shown on the office page

### PIER-311

- title: Berth map
- description: A drawing of the harbour with each berth on it. Free berths are shown in green and the map can be zoomed.
- assignee: Ines Kowalczyk
- estimate: 1
- scope:
  - A picture of the harbour with each berth numbered
- acceptance:
  - Every berth in the list is on the map

### PIER-312

- title: Take a deposit when booking
- description: The harbour wants a deposit, and not the full dues, at booking.
- assignee: Bram Solheim
- estimate: 5
- changed_by: Odile Marchetti
- scope:
  - A deposit of one night's dues is asked for when booking
  - The deposit is recorded against the booking
- acceptance:
  - A booking is not saved until the deposit is recorded

### PIER-313

- title: Export bookings as a spreadsheet
- description: The harbour office wants the month's bookings in a file.
- assignee: Ines Kowalczyk
- estimate: 4
- changed_by: Ines Kowalczyk
- scope:
  - A button that downloads the month's bookings
- acceptance:
  - The file has one row for each booking in the month

## What differs on purpose

| Item | What it is for |
|---|---|
| PIER-301 | Nothing differs. |
| PIER-302 | Its title was changed and nothing else. Matched on title it would look like one item removed and one added. |
| PIER-303 | In the start snapshot only: removed. 2 points. |
| PIER-304 | Its estimate went from 8 to 4, and one entry of its scope was taken out. The change was not made by the product owner. |
| PIER-305 | It was given to another person and nothing else differs. |
| PIER-306 | Its estimate went from 3 to 5, and it was given to another person. |
| PIER-307 | One acceptance criterion says 10 seconds where it said 2 seconds. Its estimate is the same. |
| PIER-308 | Its acceptance criteria are in another order, numbered differently, with other capitals and punctuation. The words are the same. |
| PIER-309 | One acceptance criterion has its words in another order and means the same. |
| PIER-310 | In the start snapshot only: removed. 5 points. |
| PIER-311 | Its description gained a sentence that asks for more work. Its scope list and its acceptance criteria are as they were. |
| PIER-312 | In the later snapshot only: added, by the product owner. 5 points. |
| PIER-313 | In the later snapshot only: added, and not by the product owner. 4 points. |

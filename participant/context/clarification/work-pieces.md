# Pieces of work

The list that every answer in `questions.md` and `dropped.md` names its work from. A piece is something a
developer would estimate on its own. Written by `questions.py build`.

A **B** piece is required by the requirements as they stand, whatever is answered. A **W** piece is built
only if some answer asks for it. Testing a piece is taken to be part of the piece.

| Piece | What it is | Answers that lead to it |
|---|---|---|
| B-01 | Deletion of old booking records, with the period as a setting (NFR-04) | C-02 A, C-02 B |
| B-02 | Staff view of a member's booking history, with the period as a setting (REQ-14) | C-02 A, C-02 B, C-03 A, C-03 B |
| B-03 | Reminder email sent a set time before each booking, with the lead time as a setting (REQ-06) | C-08 A, C-17 A, C-17 B |
| B-04 | The website's pages, tested in a list of browsers (NFR-03) | C-09 A, C-09 B |
| W-01 | Cut-off for a member's cancellation, with the message shown when it is refused | C-01 B |
| W-02 | Staff cancellation of a member's booking | C-01 B |
| W-03 | Limit on the number of future bookings one member holds | C-04 B, C-04 D |
| W-04 | Count of a member's cancellations in a period, with a threshold | C-04 C, C-04 D |
| W-05 | Refusal of a booking for misuse, with its message | C-05 A |
| W-06 | Staff list of members whose bookings look like misuse | C-05 B |
| W-07 | Confirmation shown only after the booking is stored where a restart cannot lose it | C-06 A, C-06 B |
| W-08 | Second copy of the booking database on another machine, kept up to date continuously | C-06 B |
| W-09 | Switch-over to the second copy when the first machine is lost | C-06 B |
| W-10 | Staff screens laid out for mobile browsers | C-10 A |
| W-11 | No-show count kept apart from booking records, so that it outlives their deletion | C-11 A |
| W-12 | No-show count worked out from booking records inside a period | C-11 B |
| W-13 | Automatic end of a suspension after a set time | C-12 B, C-12 D |
| W-14 | Staff action that lifts a suspension | C-12 C, C-12 D |
| W-15 | Automatic cancellation of bookings in a room marked out of service | C-13 A, C-13 C |
| W-16 | Refusal to mark a room out of service while it has bookings, with a list of them | C-13 B |
| W-17 | Automatic move of a booking to another free room | C-13 C |
| W-18 | Email to a member whose booking the library cancelled or moved | C-14 A |
| W-19 | Staff list of the members affected, with the booking references to contact them about | C-14 B |
| W-21 | Reminder email sent in one run at a fixed hour the day before, with a rule for bookings made after that run | C-08 B |
| W-20 | Third slot marking, "unavailable", on the availability display | C-15 B, C-16 A, C-16 B |

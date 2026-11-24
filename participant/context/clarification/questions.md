# Questions to ask about the RoomSlot requirements

Drafts for a person to ask. Nothing here has been sent to anyone. RoomSlot is a made-up product, and the
requirements and the findings these questions come from are in `participant/context/ambiguity/`.

This file is written by `participant/skills/ba-clarification-questions/questions.py build`. The same program's
`check` reads it back and tests it.

## How to read it

Every question comes from one finding of the ambiguity review. Each can be answered by naming one letter.
Each answer says what would be built, and names the pieces of work from `work-pieces.md`. No two answers to
one question lead to the same pieces. A question whose answers all led to the same pieces is in `dropped.md`.

**Order.** The question that the most work depends on comes first. The work that depends on a question is
every piece that one of its answers needs and another does not, together with the same for any question
that is asked only because of an answer to it. Equal counts are ordered by the finding's effort (large, then
medium, then small), then by finding number.

**Default.** What would be built if no answer has come by the time the work starts, and what that assumes. A
default is a suggestion to whoever answers. It decides nothing for them.

## The questions at a glance

| Place | Question | Finding | Work that depends on it | Best placed to answer |
|---|---|---|---|---|
| 1 | C-13: When a room goes out of service, what happens to bookings already made in it for those dates? | F-08 | 5 pieces | Library service manager |
| 2 | C-04: Beyond the no-show rules, which of these should the system limit to discourage bookings that go unused? | F-03 | 4 pieces | Library service manager |
| 3 | C-01: In the two hours before a booking starts, can the member cancel it themselves? | F-01 | 2 pieces | Library service manager |
| 4 | C-05: When a member goes over such a limit, does the system refuse their next booking or only tell staff? | F-03 | 2 pieces | Front-desk supervisor |
| 5 | C-06: Which is the worst fault a confirmed booking must survive? | F-04 | 2 pieces | Technical lead |
| 6 | C-11: Are a member's no-shows counted over their whole membership, or only over a recent period? | F-07 | 2 pieces | Library service manager |
| 7 | C-12: How does a member who is prevented from booking become able to book again? | F-07 | 2 pieces | Library service manager |
| 8 | C-14: Who tells the members whose bookings were cancelled or moved: the system by email, or staff? | F-08 | 2 pieces | Front-desk supervisor |
| 9 | C-08: Is the reminder sent a set time before each booking, or at a fixed hour the day before? | F-05 | 2 pieces | Library service manager |
| 10 | C-10: Must the staff functions work in mobile browsers, or only the member functions? | F-06 | 1 piece | Technical lead |
| 11 | C-15: Is an out-of-service slot shown as "booked", or with a marking of its own? | F-09 | 1 piece | Library service manager |

## By the person best placed to answer

- **Library service manager:** C-13, C-04, C-01, C-11, C-12, C-08, C-15
- **Front-desk supervisor:** C-05, C-14
- **Technical lead:** C-06, C-10

Roles, not people. Nobody is named.

## 1. C-13

**Question:** When a room goes out of service, what happens to bookings already made in it for those dates?

- Finding: F-08 (REQ-13, incomplete, effort medium)
- From the finding's question: "what is to happen to those bookings"
- Best placed to answer: Library service manager
- Work that depends on the answer: 5 pieces (W-15, W-16, W-17; and W-18, W-19 through C-14)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. They are cancelled | Marking the room out of service cancels the bookings in it. | W-15 |
| B. The room cannot be marked until staff have dealt with them | Marking the room is refused while it has bookings, and staff are shown which ones. | W-16 |
| C. They are moved to a free room, and cancelled if there is none | Each booking is moved to a free room with at least as many seats, and cancelled where no room is free. | W-15, W-17 |

- Suggested default: B. This assumes that such clashes are rare, and that nothing should happen to a member's booking without a person deciding it.

## 2. C-04

**Question:** Beyond the no-show rules, which of these should the system limit to discourage bookings that go unused?

- Finding: F-03 (REQ-11, untestable, effort large)
- From the finding's question: "What that the system can observe would count as a member not intending to use a room"
- Best placed to answer: Library service manager
- Work that depends on the answer: 4 pieces (W-03, W-04; and W-05, W-06 through C-05)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Nothing more | Nothing is added. REQ-11 is reworded as the aim that the no-show rules in REQ-08 and REQ-10 serve. | none |
| B. The number of future bookings a member holds | A limit on the future bookings one member holds is added, and checked whenever a booking is made. | W-03 |
| C. The number of bookings a member cancels in a period | A count of each member's cancellations in a period is kept and compared with a threshold. | W-04 |
| D. Both of these | Both the limit on future bookings held and the count of cancellations are added. | W-03, W-04 |

- Suggested default: A. This assumes that REQ-11 states the purpose of the no-show rules and asks for no behaviour of its own.

## 3. C-01

**Question:** In the two hours before a booking starts, can the member cancel it themselves?

- Finding: F-01 (REQ-04 and REQ-12, contradictory, effort large)
- From the finding's question: "In the two hours before a booking starts, may the member cancel it or not?"
- Best placed to answer: Library service manager
- Work that depends on the answer: 2 pieces (W-01, W-02)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Yes, up to the start time | Nothing is added. REQ-12 is withdrawn and the cancellation in REQ-04 is built as written. | none |
| B. No, only a staff user can | A cut-off refuses the member's cancellation inside two hours, and staff get a way to cancel a member's booking. | W-01, W-02 |

- Suggested default: B. This assumes that REQ-12, the more specific of the two requirements, is the one that was meant.

## 4. C-05

**Question:** When a member goes over such a limit, does the system refuse their next booking or only tell staff?

- Finding: F-03 (REQ-11, untestable, effort large)
- From the finding's question: "what is the system to do when it sees it?"
- Best placed to answer: Front-desk supervisor
- Asked only if: C-04 is answered B or C or D
- Work that depends on the answer: 2 pieces (W-05, W-06)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. It refuses the booking | The booking is refused with a message that says why. | W-05 |
| B. It allows the booking and tells staff | The booking goes through, and the member appears on a list that staff can open. | W-06 |

- Suggested default: A. This assumes that staff have no time set aside to follow up a list.

## 5. C-06

**Question:** Which is the worst fault a confirmed booking must survive?

- Finding: F-04 (NFR-05, untestable, effort medium)
- From the finding's question: "Which faults must a confirmed booking survive"
- Best placed to answer: Technical lead
- Work that depends on the answer: 2 pieces (W-08, W-09)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. The server program stopping and restarting | The confirmation page is shown only once the booking is stored where a restart cannot lose it. | W-07 |
| B. The loss of the machine that holds the database | As for A, and a second copy of the database is kept up to date on another machine, with a switch-over to it. | W-07, W-08, W-09 |

- Suggested default: A. This assumes that the daily backup in NFR-06 is the accepted protection against losing the machine, so up to a day of bookings may be lost then.

## 6. C-11

**Question:** Are a member's no-shows counted over their whole membership, or only over a recent period?

- Finding: F-07 (REQ-08, incomplete, effort medium)
- From the finding's question: "Over what period are no-shows counted"
- Best placed to answer: Library service manager
- Work that depends on the answer: 2 pieces (W-11, W-12)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Over the whole membership | A count is kept apart from the booking records, because the records it would be counted from are deleted under NFR-04. | W-11 |
| B. Over a recent period | The count is worked out from the booking records inside the period, whose length is a setting, and nothing is stored for it. | W-12 |

- Suggested default: B. This assumes that the period is no longer than the time booking records are kept.

## 7. C-12

**Question:** How does a member who is prevented from booking become able to book again?

- Finding: F-07 (REQ-08, incomplete, effort medium)
- From the finding's question: "how does a member who has been prevented from booking become able to book again?"
- Best placed to answer: Library service manager
- Work that depends on the answer: 2 pieces (W-13, W-14)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. They do not | Nothing is added. The suspension in REQ-08 stays in force, as the text says now. | none |
| B. Automatically, after a set time | The suspension ends by itself after a set time. | W-13 |
| C. A staff user lifts it | Staff get an action that lifts a member's suspension. | W-14 |
| D. After a set time, or sooner if staff lift it | The suspension ends by itself, and staff also get the action that lifts it. | W-13, W-14 |

- Suggested default: C. This assumes that the library wants a person to decide each case, and that staff have the time.

## 8. C-14

**Question:** Who tells the members whose bookings were cancelled or moved: the system by email, or staff?

- Finding: F-08 (REQ-13, incomplete, effort medium)
- From the finding's question: "and to the members who hold them?"
- Best placed to answer: Front-desk supervisor
- Asked only if: C-13 is answered A or C
- Work that depends on the answer: 2 pieces (W-18, W-19)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. The system, by email | An email is sent to each member whose booking the library cancelled or moved. | W-18 |
| B. Staff | Staff are given a list of the members affected and get in touch themselves. | W-19 |

- Suggested default: A. This assumes that an email address is held for every member, as the reminder in REQ-06 already assumes.

## 9. C-08

**Question:** Is the reminder sent a set time before each booking, or at a fixed hour the day before?

- Finding: F-05 (REQ-06, vague, effort small)
- From the finding's question: "How long before a booking's start time is the reminder email to be sent?"
- Best placed to answer: Library service manager
- Work that depends on the answer: 2 pieces (B-03, W-21)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. A set time before each booking | Each reminder is timed from its own booking's start, with the lead time as a setting. | B-03 |
| B. At a fixed hour the day before | One run a day sends the next day's reminders, and a rule decides what a booking made after that run gets. | W-21 |

- Suggested default: A. This assumes that the reminder is there to stop a no-show on the day, and that REQ-06's "shortly before" means minutes or hours.

## 10. C-10

**Question:** Must the staff functions work in mobile browsers, or only the member functions?

- Finding: F-06 (NFR-03, vague, effort medium)
- From the finding's question: "which of its functions must work in each?"
- Best placed to answer: Technical lead
- Work that depends on the answer: 1 piece (W-10)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Staff functions too | The staff screens are laid out for a small screen as well as a desktop. | W-10 |
| B. Only the member functions | Nothing is added. Staff screens are built for a desktop browser, and NFR-03 says so. | none |

- Suggested default: B. This assumes that staff work at a desk with a desktop browser.

## 11. C-15

**Question:** Is an out-of-service slot shown as "booked", or with a marking of its own?

- Finding: F-09 (REQ-13, vague, effort small)
- From the finding's question: "Is an out-of-service slot shown with a marking of its own, or as "booked""
- Best placed to answer: Library service manager
- Work that depends on the answer: 1 piece (W-20)

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. As "booked" | Nothing is added. The slot uses the marking that REQ-02 already has. | none |
| B. With a marking of its own | The availability display gets a third marking, and REQ-02 is reworded to allow it. | W-20 |

- Suggested default: B. This assumes that REQ-02 may be reworded, and that a closed room should not look like a room in demand.

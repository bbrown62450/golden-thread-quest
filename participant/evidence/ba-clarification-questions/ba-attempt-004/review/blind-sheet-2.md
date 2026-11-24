# Sheet

Seventeen questions about the requirements in requirements.md, each with the answers it could get.
Some items are asked only if another item was answered a certain way. Where that is so, the item says it.

## Item 1

How does a member who is prevented from booking become able to book again?

- A. They do not
- B. Automatically, after a set time
- C. A staff user lifts it
- D. After a set time, or sooner if staff lift it

## Item 2

(Asked only if item 9 is answered B.)

If the slot has its own marking, is REQ-02 reworded to list three markings?

- A. Yes, REQ-02 lists three
- B. No, REQ-02 is left as it is

## Item 3

Which browsers and versions must the website support?

- A. Two desktop and two mobile browsers, current version only
- B. A longer list, with the previous version of each

## Item 4

In the two hours before a booking starts, can the member cancel it themselves?

- A. Yes, up to the start time
- B. No, only a staff user can

## Item 5

Must the staff functions work in mobile browsers, or only the member functions?

- A. Staff functions too
- B. Only the member functions

## Item 6

(Asked only if item 17 is answered A or C.)

Who tells the members whose bookings were cancelled or moved: the system by email, or staff?

- A. The system, by email
- B. Staff

## Item 7

Beyond the no-show rules, which of these should the system limit to discourage bookings that go unused?

- A. Nothing more
- B. The number of future bookings a member holds
- C. The number of bookings a member cancels in a period
- D. Both of these

## Item 8

Which is the worst fault a confirmed booking must survive?

- A. The server program stopping and restarting
- B. The loss of the machine that holds the database

## Item 9

Is an out-of-service slot shown as "booked", or with a marking of its own?

- A. As "booked"
- B. With a marking of its own

## Item 10

Are a member's no-shows counted over their whole membership, or only over a recent period?

- A. Over the whole membership
- B. Over a recent period

## Item 11

If the reminder is timed from each booking, how many minutes before the start is it sent?

- A. 30 minutes
- B. 120 minutes

## Item 12

Are booking records deleted after 12 months or after 24?

- A. After 12 months
- B. After 24 months

## Item 13

Is a booking's survival after a fault checked by an automated test or by hand?

- A. By an automated test
- B. By hand, in the quarterly restore test

## Item 14

Is the reminder sent a set time before each booking, or at a fixed hour the day before?

- A. A set time before each booking
- B. At a fixed hour the day before

## Item 15

Must a staff user's history cover the whole period for which records are kept?

- A. Yes, all of it
- B. No, a shorter period

## Item 16

(Asked only if item 7 is answered B or C or D.)

When a member goes over such a limit, does the system refuse their next booking or only tell staff?

- A. It refuses the booking
- B. It allows the booking and tells staff

## Item 17

When a room goes out of service, what happens to bookings already made in it for those dates?

- A. They are cancelled
- B. The room cannot be marked until staff have dealt with them
- C. They are moved to a free room, and cancelled if there is none

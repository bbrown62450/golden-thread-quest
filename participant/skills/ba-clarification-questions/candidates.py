"""The candidate questions for the made-up RoomSlot requirements, and the list of work pieces they name.

Everything here is written by hand. Nothing here says which candidates are kept and which are dropped:
questions.py works that out from the pieces each answer names.
"""

# A piece of work is something a developer would estimate on its own. "B" pieces are required by the text as it
# stands, whatever is answered. "W" pieces are built only if some answer asks for them.
PIECES = [
    ("B-01", "Deletion of old booking records, with the period as a setting (NFR-04)"),
    ("B-02", "Staff view of a member's booking history, with the period as a setting (REQ-14)"),
    ("B-03", "Reminder email sent a set time before each booking, with the lead time as a setting (REQ-06)"),
    ("B-04", "The website's pages, tested in a list of browsers (NFR-03)"),
    ("W-01", "Cut-off for a member's cancellation, with the message shown when it is refused"),
    ("W-02", "Staff cancellation of a member's booking"),
    ("W-03", "Limit on the number of future bookings one member holds"),
    ("W-04", "Count of a member's cancellations in a period, with a threshold"),
    ("W-05", "Refusal of a booking for misuse, with its message"),
    ("W-06", "Staff list of members whose bookings look like misuse"),
    ("W-07", "Confirmation shown only after the booking is stored where a restart cannot lose it"),
    ("W-08", "Second copy of the booking database on another machine, kept up to date continuously"),
    ("W-09", "Switch-over to the second copy when the first machine is lost"),
    ("W-10", "Staff screens laid out for mobile browsers"),
    ("W-11", "No-show count kept apart from booking records, so that it outlives their deletion"),
    ("W-12", "No-show count worked out from booking records inside a period"),
    ("W-13", "Automatic end of a suspension after a set time"),
    ("W-14", "Staff action that lifts a suspension"),
    ("W-15", "Automatic cancellation of bookings in a room marked out of service"),
    ("W-16", "Refusal to mark a room out of service while it has bookings, with a list of them"),
    ("W-17", "Automatic move of a booking to another free room"),
    ("W-18", "Email to a member whose booking the library cancelled or moved"),
    ("W-19", "Staff list of the members affected, with the booking references to contact them about"),
    ("W-21", "Reminder email sent in one run at a fixed hour the day before, with a rule for bookings made after that run"),
    ("W-20", "Third slot marking, \"unavailable\", on the availability display"),
]

# Roles, not people. Nobody is named and nothing is sent.
ROLES = ["Library service manager", "Front-desk supervisor", "Technical lead", "Records and privacy lead", "Test lead"]


def answer(letter, label, work, pieces=()):
    return {"letter": letter, "label": label, "work": work, "pieces": list(pieces)}


CANDIDATES = [
    {
        "id": "C-01", "finding": "F-01", "role": "Library service manager",
        "from": "In the two hours before a booking starts, may the member cancel it or not?",
        "question": "In the two hours before a booking starts, can the member cancel it themselves?",
        "answers": [
            answer("A", "Yes, up to the start time",
                   "Nothing is added. REQ-12 is withdrawn and the cancellation in REQ-04 is built as written."),
            answer("B", "No, only a staff user can",
                   "A cut-off refuses the member's cancellation inside two hours, and staff get a way to cancel a member's booking.",
                   ["W-01", "W-02"]),
        ],
        "default": ("B", "that REQ-12, the more specific of the two requirements, is the one that was meant"),
    },
    {
        "id": "C-02", "finding": "F-02", "role": "Records and privacy lead",
        "from": "For how long are booking records kept",
        "question": "Are booking records deleted after 12 months or after 24?",
        "answers": [
            answer("A", "After 12 months", "The deletion job and the history view are built, with the period set to 12 months.", ["B-01", "B-02"]),
            answer("B", "After 24 months", "The deletion job and the history view are built, with the period set to 24 months.", ["B-01", "B-02"]),
        ],
        "why": "Either answer builds the same deletion job and the same history view. Only a number in a setting differs.",
        "still": ("value", "The retention period, before release. There is no safe value to work with meanwhile: 12 months "
                           "breaks REQ-14 as written and 24 months breaks NFR-04 as written. One of the two requirements has to be reworded by whoever owns them."),
    },
    {
        "id": "C-03", "finding": "F-02", "role": "Records and privacy lead",
        "from": "is that the period a staff user's history must cover?",
        "question": "Must a staff user's history cover the whole period for which records are kept?",
        "answers": [
            answer("A", "Yes, all of it", "The history view lists every record that still exists.", ["B-02"]),
            answer("B", "No, a shorter period", "The history view lists records back to its own number of months.", ["B-02"]),
        ],
        "why": "Either answer builds the same history view. A shorter period is a second number in a setting.",
        "still": ("value", "The history period, before release. Until then it is taken to be the retention period, whatever that turns out to be."),
    },
    {
        "id": "C-04", "finding": "F-03", "role": "Library service manager",
        "from": "What that the system can observe would count as a member not intending to use a room",
        "question": "Beyond the no-show rules, which of these should the system limit to discourage bookings that go unused?",
        "answers": [
            answer("A", "Nothing more",
                   "Nothing is added. REQ-11 is reworded as the aim that the no-show rules in REQ-08 and REQ-10 serve."),
            answer("B", "The number of future bookings a member holds",
                   "A limit on the future bookings one member holds is added, and checked whenever a booking is made.", ["W-03"]),
            answer("C", "The number of bookings a member cancels in a period",
                   "A count of each member's cancellations in a period is kept and compared with a threshold.", ["W-04"]),
            answer("D", "Both of these",
                   "Both the limit on future bookings held and the count of cancellations are added.", ["W-03", "W-04"]),
        ],
        "default": ("A", "that REQ-11 states the purpose of the no-show rules and asks for no behaviour of its own"),
    },
    {
        "id": "C-05", "finding": "F-03", "role": "Front-desk supervisor",
        "from": "what is the system to do when it sees it?",
        "question": "When a member goes over such a limit, does the system refuse their next booking or only tell staff?",
        "only_if": ("C-04", ["B", "C", "D"]),
        "answers": [
            answer("A", "It refuses the booking", "The booking is refused with a message that says why.", ["W-05"]),
            answer("B", "It allows the booking and tells staff", "The booking goes through, and the member appears on a list that staff can open.", ["W-06"]),
        ],
        "default": ("A", "that staff have no time set aside to follow up a list"),
    },
    {
        "id": "C-06", "finding": "F-04", "role": "Technical lead",
        "from": "Which faults must a confirmed booking survive",
        "question": "Which is the worst fault a confirmed booking must survive?",
        "answers": [
            answer("A", "The server program stopping and restarting",
                   "The confirmation page is shown only once the booking is stored where a restart cannot lose it.", ["W-07"]),
            answer("B", "The loss of the machine that holds the database",
                   "As for A, and a second copy of the database is kept up to date on another machine, with a switch-over to it.",
                   ["W-07", "W-08", "W-09"]),
        ],
        "default": ("A", "that the daily backup in NFR-06 is the accepted protection against losing the machine, so up to a day of bookings may be lost then"),
    },
    {
        "id": "C-07", "finding": "F-04", "role": "Test lead",
        "from": "how is its survival to be checked after each?",
        "question": "Is a booking's survival after a fault checked by an automated test or by hand?",
        "answers": [
            answer("A", "By an automated test", "Nothing in the product changes. A test stops the server and looks for the booking."),
            answer("B", "By hand, in the quarterly restore test", "Nothing in the product changes. A step is added to the restore test."),
        ],
        "why": "Neither answer changes what is built. It decides how the built thing is tested, which the test team can settle without the product owner.",
        "still": ("test team", "The test method, once C-06 is answered."),
    },
    {
        "id": "C-08", "finding": "F-05", "role": "Library service manager",
        "from": "How long before a booking's start time is the reminder email to be sent?",
        "question": "Is the reminder sent a set time before each booking, or at a fixed hour the day before?",
        "answers": [
            answer("A", "A set time before each booking",
                   "Each reminder is timed from its own booking's start, with the lead time as a setting.", ["B-03"]),
            answer("B", "At a fixed hour the day before",
                   "One run a day sends the next day's reminders, and a rule decides what a booking made after that run gets.", ["W-21"]),
        ],
        "default": ("A", "that the reminder is there to stop a no-show on the day, and that REQ-06's \"shortly before\" means minutes or hours"),
    },
    {
        "id": "C-09", "finding": "F-06", "role": "Technical lead",
        "from": "Which browsers and which versions must the website support",
        "question": "Which browsers and versions must the website support?",
        "answers": [
            answer("A", "Two desktop and two mobile browsers, current version only", "The same pages are built. The list of browsers they are tested in is shorter.", ["B-04"]),
            answer("B", "A longer list, with the previous version of each", "The same pages are built. The list of browsers they are tested in is longer.", ["B-04"]),
        ],
        "why": "Any list builds the same pages. The list changes how much is tested, and it is a list that can be written down without a design decision.",
        "still": ("value", "The named list of browsers and versions, before testing starts. Until then: the current and previous version of each browser the test team already has."),
    },
    {
        "id": "C-10", "finding": "F-06", "role": "Technical lead",
        "from": "which of its functions must work in each?",
        "question": "Must the staff functions work in mobile browsers, or only the member functions?",
        "answers": [
            answer("A", "Staff functions too", "The staff screens are laid out for a small screen as well as a desktop.", ["W-10"]),
            answer("B", "Only the member functions", "Nothing is added. Staff screens are built for a desktop browser, and NFR-03 says so."),
        ],
        "default": ("B", "that staff work at a desk with a desktop browser"),
    },
    {
        "id": "C-11", "finding": "F-07", "role": "Library service manager",
        "from": "Over what period are no-shows counted",
        "question": "Are a member's no-shows counted over their whole membership, or only over a recent period?",
        "answers": [
            answer("A", "Over the whole membership",
                   "A count is kept apart from the booking records, because the records it would be counted from are deleted under NFR-04.", ["W-11"]),
            answer("B", "Over a recent period",
                   "The count is worked out from the booking records inside the period, whose length is a setting, and nothing is stored for it.", ["W-12"]),
        ],
        "default": ("B", "that the period is no longer than the time booking records are kept"),
    },
    {
        "id": "C-12", "finding": "F-07", "role": "Library service manager",
        "from": "how does a member who has been prevented from booking become able to book again?",
        "question": "How does a member who is prevented from booking become able to book again?",
        "answers": [
            answer("A", "They do not", "Nothing is added. The suspension in REQ-08 stays in force, as the text says now."),
            answer("B", "Automatically, after a set time", "The suspension ends by itself after a set time.", ["W-13"]),
            answer("C", "A staff user lifts it", "Staff get an action that lifts a member's suspension.", ["W-14"]),
            answer("D", "After a set time, or sooner if staff lift it", "The suspension ends by itself, and staff also get the action that lifts it.", ["W-13", "W-14"]),
        ],
        "default": ("C", "that the library wants a person to decide each case, and that staff have the time"),
    },
    {
        "id": "C-13", "finding": "F-08", "role": "Library service manager",
        "from": "what is to happen to those bookings",
        "question": "When a room goes out of service, what happens to bookings already made in it for those dates?",
        "answers": [
            answer("A", "They are cancelled", "Marking the room out of service cancels the bookings in it.", ["W-15"]),
            answer("B", "The room cannot be marked until staff have dealt with them",
                   "Marking the room is refused while it has bookings, and staff are shown which ones.", ["W-16"]),
            answer("C", "They are moved to a free room, and cancelled if there is none",
                   "Each booking is moved to a free room with at least as many seats, and cancelled where no room is free.", ["W-15", "W-17"]),
        ],
        "default": ("B", "that such clashes are rare, and that nothing should happen to a member's booking without a person deciding it"),
    },
    {
        "id": "C-14", "finding": "F-08", "role": "Front-desk supervisor",
        "from": "and to the members who hold them?",
        "question": "Who tells the members whose bookings were cancelled or moved: the system by email, or staff?",
        "only_if": ("C-13", ["A", "C"]),
        "answers": [
            answer("A", "The system, by email", "An email is sent to each member whose booking the library cancelled or moved.", ["W-18"]),
            answer("B", "Staff", "Staff are given a list of the members affected and get in touch themselves.", ["W-19"]),
        ],
        "default": ("A", "that an email address is held for every member, as the reminder in REQ-06 already assumes"),
    },
    {
        "id": "C-15", "finding": "F-09", "role": "Library service manager",
        "from": "Is an out-of-service slot shown with a marking of its own, or as \"booked\"",
        "question": "Is an out-of-service slot shown as \"booked\", or with a marking of its own?",
        "answers": [
            answer("A", "As \"booked\"", "Nothing is added. The slot uses the marking that REQ-02 already has."),
            answer("B", "With a marking of its own", "The availability display gets a third marking, and REQ-02 is reworded to allow it.", ["W-20"]),
        ],
        "default": ("B", "that REQ-02 may be reworded, and that a closed room should not look like a room in demand"),
    },
    {
        "id": "C-17", "finding": "F-05", "role": "Library service manager",
        "from": "How long before a booking's start time",
        "question": "If the reminder is timed from each booking, how many minutes before the start is it sent?",
        "answers": [
            answer("A", "30 minutes", "The reminder is built, with the lead time set to 30 minutes.", ["B-03"]),
            answer("B", "120 minutes", "The reminder is built, with the lead time set to 120 minutes.", ["B-03"]),
        ],
        "why": "Any number of minutes builds the same reminder. A booking made later than the lead time needs the same handling whatever the number is.",
        "still": ("value", "The lead time, before release, if C-08 is answered A. Until then: 60 minutes."),
    },
    {
        "id": "C-16", "finding": "F-09", "role": "Library service manager",
        "from": "is that a third marking beside the two in REQ-02?",
        "question": "If the slot has its own marking, is REQ-02 reworded to list three markings?",
        "answers": [
            answer("A", "Yes, REQ-02 lists three", "The availability display gets a third marking.", ["W-20"]),
            answer("B", "No, REQ-02 is left as it is", "The availability display gets a third marking, and the two requirements go on disagreeing on paper.", ["W-20"]),
        ],
        "why": "A marking of its own is a third marking whatever REQ-02 says. Both answers build the same display. C-15 already asks the part that changes the work.",
        "still": ("nothing", "If C-15 is answered B, rewording REQ-02 follows from it."),
    },
]

# Things the ambiguity review mentions that are not findings, so no question can link to them (criterion 1).
SET_ASIDE = [
    ("Whether a slot earlier today, already past, can be booked", "the review lists it under \"Gaps in the set\". It was raised as F-10 and withdrawn."),
    ("How often each of the 50 members makes a request in the load test", "it was raised as F-11 and withdrawn, because its type could not be reproduced."),
    ("How long a backup is kept", "the review lists it under \"Gaps in the set\"."),
]

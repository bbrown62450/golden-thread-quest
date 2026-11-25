#!/usr/bin/env python3
"""Writes the made-up sprint snapshots the scope-change report is built from. Everything in them is invented.

    python3 participant/skills/scrum-scope-change/make_snapshots.py

It writes one file, participant/context/scrum/scope/snapshots.md, holding two snapshots of one sprint of a harbour
booking app that does not exist: one taken at sprint start, and one a week later.

No identifier belongs to a real item and no name to a real person. The differences between the two are there on
purpose: each is a case the report must class rightly. They are listed in CASES below, and in the file itself.

The sprint starts with 30 points and a week later has 30 points. In between, 22 points moved.
"""
import copy
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(REPO, "participant", "context", "scrum", "scope", "snapshots.md")
PO, DEV1, DEV2, DEV3 = "Odile Marchetti", "Bram Solheim", "Ines Kowalczyk", "Teodor Adeyemi"   # invented people

CASES = [
    ("PIER-301", "Nothing differs."),
    ("PIER-302", "Its title was changed and nothing else. Matched on title it would look like one item removed and one added."),
    ("PIER-303", "In the start snapshot only: removed. 2 points."),
    ("PIER-304", "Its estimate went from 8 to 4, and one entry of its scope was taken out. The change was not made by the product owner."),
    ("PIER-305", "It was given to another person and nothing else differs."),
    ("PIER-306", "Its estimate went from 3 to 5, and it was given to another person."),
    ("PIER-307", "One acceptance criterion says 10 seconds where it said 2 seconds. Its estimate is the same."),
    ("PIER-308", "Its acceptance criteria are in another order, numbered differently, with other capitals and punctuation. The words are the same."),
    ("PIER-309", "One acceptance criterion has its words in another order and means the same."),
    ("PIER-310", "In the start snapshot only: removed. 5 points."),
    ("PIER-311", "Its description gained a sentence that asks for more work. Its scope list and its acceptance criteria are as they were."),
    ("PIER-312", "In the later snapshot only: added, by the product owner. 5 points."),
    ("PIER-313", "In the later snapshot only: added, and not by the product owner. 4 points."),
]


def item(identity, title, description, assignee, estimate, scope, acceptance, changed_by=None):
    return {"id": identity, "title": title, "description": description, "assignee": assignee, "estimate": estimate, "scope": scope, "acceptance": acceptance, "changed_by": changed_by}


def start_items():
    return [
        item("PIER-301", "List the berths that are free on a day", "A harbour master picks a day and sees which berths are free.", DEV1, "3",
             ["A page with a date picker and a list of berths", "Each berth shows its length and depth"],
             ["A berth with a booking that covers the day is not listed", "The list is in order of berth number"]),
        item("PIER-302", "Book a berth", "A skipper books a free berth for one or more nights.", DEV2, "3",
             ["A booking form: boat name, length, arrival day, number of nights", "The booking is saved against the berth"],
             ["A booking for a berth that is not free is refused", "A boat longer than the berth is refused"]),
        item("PIER-303", "Email a booking confirmation", "The skipper gets an email when a booking is made.", DEV3, "2",
             ["An email with the berth, the days and a reference"],
             ["The email is sent within one minute of the booking"]),
        item("PIER-304", "Harbour dues calculator", "Work out what a visit costs from the boat's length and the nights stayed.", DEV1, "8",
             ["A rate for each metre of length for each night", "A discount for a stay of seven nights or more", "A surcharge in July and August"],
             ["The dues for a 10 metre boat for 2 nights are 2 times 10 times the rate", "A stay of 7 nights gets the discount and a stay of 6 does not"]),
        item("PIER-305", "Show the tide times on the booking page", "Skippers need high and low water for the arrival day.", DEV2, "1",
             ["High and low water times for the arrival day, from the harbour's own table"],
             ["The times shown are those in the table for that day"]),
        item("PIER-306", "Cancel a booking", "A skipper cancels a booking and the berth becomes free.", DEV3, "3",
             ["A cancel button on the booking", "The berth is free again for those days"],
             ["A cancelled booking no longer blocks the berth", "A booking that has started cannot be cancelled"]),
        item("PIER-307", "Search bookings by boat name", "The harbour office looks a boat up by name.", DEV1, "2",
             ["A search box on the office page"],
             ["The results are shown within 2 seconds", "A search with no match says that nothing was found"]),
        item("PIER-308", "Print the day's arrivals", "The harbour office prints a list each morning.", DEV2, "1",
             ["A page laid out for printing, with one line for each arrival"],
             ["1. The list has every booking that starts on the day", "2. The list is in order of berth number", "3. A day with no arrivals prints a page that says so"]),
        item("PIER-309", "Upload a photo of the boat", "A skipper may add a photo so the office can recognise the boat.", DEV3, "1",
             ["One photo for each booking"],
             ["An error message is shown when the file is too large", "The photo is shown on the office page"]),
        item("PIER-310", "Pay harbour dues online", "A skipper pays the dues by card when booking.", DEV1, "5",
             ["A payment page", "The booking is marked as paid"],
             ["A booking is marked as paid only after the payment succeeds"]),
        item("PIER-311", "Berth map", "A drawing of the harbour with each berth on it.", DEV2, "1",
             ["A picture of the harbour with each berth numbered"],
             ["Every berth in the list is on the map"]),
    ]


def later_items():
    items = {one["id"]: one for one in copy.deepcopy(start_items())}
    del items["PIER-303"], items["PIER-310"]
    items["PIER-302"]["title"] = "Reserve a berth for a visiting boat"
    items["PIER-304"].update(estimate="4", changed_by=DEV1, scope=["A rate for each metre of length for each night", "A discount for a stay of seven nights or more"])
    items["PIER-305"]["assignee"] = DEV3
    items["PIER-306"].update(estimate="5", assignee=DEV2, changed_by=PO)
    items["PIER-307"].update(acceptance=["The results are shown within 10 seconds", "A search with no match says that nothing was found"], changed_by=PO)
    items["PIER-308"]["acceptance"] = ["- the list is in order of berth number.", "- The list has every booking that starts on the day;", "- A day with no arrivals prints a page that says so."]
    items["PIER-309"].update(acceptance=["When the file is too large an error message is shown", "The photo is shown on the office page"], changed_by=DEV3)
    items["PIER-311"]["description"] = "A drawing of the harbour with each berth on it. Free berths are shown in green and the map can be zoomed."
    items["PIER-312"] = item("PIER-312", "Take a deposit when booking", "The harbour wants a deposit, and not the full dues, at booking.", DEV1, "5",
                             ["A deposit of one night's dues is asked for when booking", "The deposit is recorded against the booking"],
                             ["A booking is not saved until the deposit is recorded"], PO)
    items["PIER-313"] = item("PIER-313", "Export bookings as a spreadsheet", "The harbour office wants the month's bookings in a file.", DEV2, "4",
                             ["A button that downloads the month's bookings"],
                             ["The file has one row for each booking in the month"], DEV2)
    return [items[key] for key in sorted(items)]


def render_item(one):
    out = ["### %s" % one["id"], "", "- title: %s" % one["title"], "- description: %s" % one["description"], "- assignee: %s" % one["assignee"], "- estimate: %s" % one["estimate"]]
    if one["changed_by"]:
        out.append("- changed_by: %s" % one["changed_by"])
    for name in ("scope", "acceptance"):
        out.append("- %s:" % name)
        out += ["  %s" % (entry if entry[:2] in ("1.", "2.", "3.", "- ") else "- " + entry) for entry in one[name]]
    return out + [""]


def render(start, later):
    out = ["# Sprint snapshots: sprint 9 of the harbour booking app", "",
           "**Made up.** Written by `participant/skills/scrum-scope-change/make_snapshots.py`. The project, the items, the dates and the four people are invented.",
           "Nothing here was read from a tracker, and nothing is posted to one.", "",
           "## The sprint", "",
           "- sprint_start: 2026-12-01", "- sprint_end: 2026-12-14",
           "- capacity_points: 32",
           "- product_owner: %s" % PO, "",
           "`capacity_points` is what this made-up team says it can do in the sprint. `product_owner` is who this made-up team says decides the sprint's scope.", "",
           "## The fields", "",
           "| Field | What it is |", "|---|---|",
           "| the heading | the item's identifier. It never changes |",
           "| `title`, `description` | words about the item. Other people's text |",
           "| `assignee` | who is doing it |",
           "| `estimate` | points, a number |",
           "| `changed_by` | in the later snapshot, who last changed the item or added it. Left out where nobody did |",
           "| `scope` | what is to be built, one entry to a line |",
           "| `acceptance` | the acceptance criteria, one to a line |", ""]
    for name, taken, items in (("start", "2026-12-01", start), ("later", "2026-12-08", later)):
        out += ["## Snapshot: %s" % name, "", "- taken: %s" % taken, ""]
        for one in items:
            out += render_item(one)
    out += ["## What differs on purpose", "", "| Item | What it is for |", "|---|---|"]
    out += ["| %s | %s |" % case for case in CASES]
    return "\n".join(out + [""])


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    start, later = start_items(), later_items()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(start, later))
    print("Wrote the made-up snapshots. Start: %d items, %s points. Later: %d items, %s points." % (
        len(start), sum(int(one["estimate"]) for one in start), len(later), sum(int(one["estimate"]) for one in later)))


if __name__ == "__main__":
    main()

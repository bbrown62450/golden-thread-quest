"""The content of the ba-slice-story quest: one made-up story that is too large, and the way it is cut.

Everything here is invented by the writer. There is no meeting, no shop and no team behind it. slice.py writes the
three documents from these tables, so that they cannot disagree with each other.
"""

TITLE = "Build the reporting module"

STORY = {
    "User": "A manager of the shop, signed in to the staff site.",
    "Wants": "To see what the shop sold in a period, saved and sent to them if they like, without asking a developer for a spreadsheet.",
    "Value": "They can answer \"what did we sell, and what did it come to?\" themselves, on the day they ask.",
}

TOO_LARGE = (
    "The story has 20 acceptance criteria across seven areas: the page and who may open it, the list, the figures, "
    "the export, saved reports, the weekly email and speed. Written as one story, none of it is in a manager's hands "
    "until all of it is. The made-up team's estimate is four iterations of two weeks. That figure is invented, as the "
    "team is. No estimate is needed to see the trouble: eight of the criteria alone would answer the manager's "
    "question for the last 7 days, and as one story they wait for the weekly email to be finished."
)

# What the story takes as already there. It builds none of this.
GIVEN = [
    ("G1", "The staff site has sign-in, and each staff account has a role. \"Manager\" is one of the roles."),
    ("G2", "Every order is already stored with its order reference, the date it was placed, the products in it, its total, and whether it was refunded in full."),
    ("G3", "The staff site has a menu that a new page can be added to."),
    ("G4", "The staff site can already send email. It sends password resets."),
]

# (id, area, the criterion, the criteria it needs)
# "Needs" means: this criterion cannot be seen to hold unless that one already does. It is the writer's judgement.
CRITERIA = [
    ("OC-01", "The page", "When a signed-in manager chooses \"Sales report\" in the staff menu, a page headed \"Sales report\" opens.", []),
    ("OC-02", "The page", "When a signed-in member of staff who is not a manager opens the address of the Sales report page, the page shows \"Not allowed\" and no order.", ["OC-01"]),
    ("OC-03", "The list", "The Sales report page lists every order placed in the period, one row for each, showing its order reference, the date it was placed and its total.", ["OC-01"]),
    ("OC-04", "The list", "When the Sales report page is opened, the period is the last 7 days, ending today.", ["OC-03"]),
    ("OC-05", "The list", "When the manager gives a start date and an end date and presses \"Show\", the period becomes those dates, both included.", ["OC-03"]),
    ("OC-06", "The list", "When the manager chooses a product and presses \"Show\", the list holds only the orders that include that product.", ["OC-03", "OC-05"]),
    ("OC-07", "The figures", "Below the list, the page shows the number of orders listed.", ["OC-03"]),
    ("OC-08", "The figures", "Below the list, the page shows the sum of the totals of the orders listed.", ["OC-03"]),
    ("OC-09", "The figures", "An order that was refunded in full is listed with the word \"Refunded\" beside its total.", ["OC-03"]),
    ("OC-10", "The figures", "The total of an order that was refunded in full is left out of the sum.", ["OC-08"]),
    ("OC-11", "The figures", "The page shows a table with one row for each day of the period: the date, the number of orders placed that day and the sum of their totals.", ["OC-03"]),
    ("OC-12", "The figures", "The page shows the sums of that table as a bar chart, with one bar for each day of the period.", ["OC-11"]),
    ("OC-13", "The export", "When the manager presses \"Download CSV\", a file is downloaded that holds one line for each order listed, with the order reference, the date and the total.", ["OC-03"]),
    ("OC-14", "Saved reports", "When the manager types a name and presses \"Save report\", the period and the product chosen are saved under that name.", ["OC-05", "OC-06"]),
    ("OC-15", "Saved reports", "The Sales report page lists, by name, each report the manager has saved.", ["OC-14"]),
    ("OC-16", "Saved reports", "When the manager chooses a saved report, the page shows the report for the period and the product saved.", ["OC-15"]),
    ("OC-17", "Saved reports", "When the manager presses \"Delete\" beside a saved report and confirms, that report is no longer listed.", ["OC-15"]),
    ("OC-18", "The weekly email", "When the manager switches on \"Email weekly\" for a saved report and gives an email address, an email is sent to that address every Monday at 07:00.", ["OC-15"]),
    ("OC-19", "The weekly email", "Each weekly email has attached the CSV file of that saved report for the 7 days before it was sent.", ["OC-18", "OC-13"]),
    ("OC-20", "Speed", "For a period of 31 days that holds 10,000 orders, the list is shown within 5 seconds of pressing \"Show\".", ["OC-05"]),
]

# The slices, in the order they would be released.
SLICES = [
    dict(title="See the last 7 days' orders and what they come to",
         value="A manager can answer \"what did we sell in the last 7 days, and what did it come to?\" by opening one page, without asking anyone.",
         notice="A new \"Sales report\" entry in the staff menu, and behind it the orders of the last 7 days with a count and a sum. An order refunded in full is marked, and is not in the sum.",
         covers=["OC-01", "OC-02", "OC-03", "OC-04", "OC-07", "OC-08", "OC-09", "OC-10"], depends=[],
         relies="G1, G2 and G3, which the original story takes as given. It relies on no other slice.",
         alone="It works as it is, for the last 7 days and no other period. Three things it does not do, because the original story does not ask: the page does not say which days it is showing; an order refunded in part is not mentioned by the original, so nothing marks it or takes any of it out of the sum; and an order refunded in full is left out of the sum but is still one of the orders counted.",
         why="Value: it is the manager's whole question, for the days they are most likely to ask about. Risk: it proves the two things everything else stands on, that the orders can be read and that a member of staff who is not a manager is refused. OC-02 is here and not later because a page of sales figures cannot be released to all staff first and locked afterwards. OC-09 and OC-10, the refunds, are here for the same kind of reason: a first version of this slice left them for a second slice, and a reader pointed out that it would then release a sum known to be wrong, with nothing on the page to say so. A second reader proposed a thinner first slice still: the list alone with refunds marked (OC-01 to OC-04 and OC-09), with the count and the sum to follow. That would be honest to release. It was not taken, because it does not answer \"what did it come to\", and that question is what the story is for."),
    dict(title="Look at any period, a busy month included",
         value="A manager can ask about last month, or any dates. In a busy shop, a month of 10,000 orders is listed within 5 seconds.",
         notice="Two date boxes and a \"Show\" button. The list follows the dates, and so do the count and the sum, which are of the orders listed.",
         covers=["OC-05", "OC-20"], depends=[1],
         relies="Slice 1, for the list that the dates apply to.",
         alone="With Slice 1 it is complete. OC-20 speaks of one case, 31 days and 10,000 orders, and of the list only. It is accepted for the page as it is at this release. Slices 4 and 5 make the same press of \"Show\" do more, and could make it slower. The original does not say OC-20 must still hold then.",
         why="Value: after the last 7 days, \"last month\" is the next thing a manager asks. Risk: OC-20 is the criterion most likely to force a change in how the orders are read, and that is cheaper now than after the per-day figures and the product choice are built on the same reading. A first version made OC-20 a slice of its own. A reader called that a quality attribute under a friendly name: a small shop would notice nothing. It is here as a condition on choosing a period, which is where a manager would feel it."),
    dict(title="Take the list away as a file",
         value="A manager can put the orders listed into a spreadsheet of their own, which is the thing the story says they ask a developer for.",
         notice="A \"Download CSV\" button, and a file with a line for each order listed.",
         covers=["OC-13"], depends=[1],
         relies="Slice 1, for the list that the file is made from.",
         alone="It works with Slice 1 alone, with a line for each order the list holds at the time. With Slice 2 that is any period. The file has the three columns OC-13 names and no more: it does not carry the word \"Refunded\", and it does not say what was in an order.",
         why="Value: the story's own words are \"without asking a developer for a spreadsheet\", and this slice is that spreadsheet. With the file in hand a manager can add up each day themselves, which makes Slice 4 less urgent. Risk: low. A first version put it seventh, on the argument that nothing earlier needed it. A reader pointed out that that is an argument about dependency and not about value."),
    dict(title="See sales day by day",
         value="A manager can see how sales moved from day to day, and not only the total.",
         notice="A table with a row for each day, and a bar chart of the same sums.",
         covers=["OC-11", "OC-12"], depends=[1],
         relies="Slice 1, for the period and the orders in it.",
         alone="It works with Slice 1 alone, for the last 7 days. With Slice 2 it follows the dates chosen. The original story does not say whether a day's sum leaves out refunded orders, so the table may not add up to the sum below the list. It adds to what the page works out on each press of \"Show\", which could slow it: see Slice 2 on OC-20.",
         why="Value: it is the first slice that shows how sales moved from one day to the next, where the list shows only the orders. Risk: low, apart from the open question about refunds."),
    dict(title="See only the orders that had one product in them",
         value="A manager can pick a product and see the orders that included it, with their count and the sum of their totals.",
         notice="A product box. The list then holds only the orders with that product in them.",
         covers=["OC-06"], depends=[2],
         relies="Slice 2, for the \"Show\" button that OC-06 presses, and through it Slice 1, for the list. G2, for the products in each order.",
         alone="With Slices 1 and 2 it is complete. It adds to what a press of \"Show\" does, which could slow it: see Slice 2 on OC-20. It does not tell a manager what the product itself sold: the sum is of the whole of each order listed, not of that product's share. The original story asks for no more.",
         why="Value: useful, and asked for less often than a period, a file or a trend. Risk: low. It has to come before saving, because a saved report holds a product."),
    dict(title="Save a report and come back to it",
         value="A manager who looks at the same period and product often can keep it under a name and open it again.",
         notice="A name box and a \"Save report\" button, a list of saved reports, and a \"Delete\" beside each.",
         covers=["OC-14", "OC-15", "OC-16", "OC-17"], depends=[2, 5],
         relies="Slice 2, for a period worth saving, and Slice 5, for a product to save with it. Through them, Slice 1.",
         alone="With Slices 1, 2 and 5 it is complete. The original does not say whether the period saved is those dates for good or \"the last so many days\", so a saved report may show the same orders every time it is opened.",
         why="Value: a convenience, and thin without the weekly email, which is hung on it. Nothing a manager can learn from the report depends on it. Risk: moderate, because it is the first slice that stores anything of the manager's own."),
    dict(title="Have it sent every Monday",
         value="A manager who has saved a report has its file sent every Monday to the address they give, without opening the staff site each week.",
         notice="An \"Email weekly\" switch on a saved report. The email itself, with a file attached, arrives the Monday after.",
         covers=["OC-18", "OC-19"], depends=[3, 6],
         relies="Slice 6, for a saved report to send, and Slice 3, for the file to attach. G4, for sending email.",
         alone="It cannot be released before Slices 3 and 6. With them it is complete. Two things the original story leaves open come due here: what is sent when the saved period is not 7 days, and what happens to the email when its saved report is deleted.",
         why="Value: real, once a manager has saved a report and switched the email on. Risk: the highest of the seven, since it is the only slice that runs unattended and the only one that sends anything outside. It is last because it needs the most, and because every earlier slice is useful without it."),
]

# Candidate slices that had to become one because neither could ship without the other.
FORCED = [
    ("\"Save a report\" (OC-14) and \"Open a saved report\" (OC-15, OC-16)",
     "They were first drawn as two slices. OC-14 alone saves something that cannot be seen again, and cannot even be tested: nothing shows that it saved. A slice has to deliver value on its own, so two slices that must ship together are one slice. They are in Slice 6."),
    ("\"Switch on the weekly email\" (OC-18) and \"The email has the file attached\" (OC-19)",
     "OC-18 alone sends an email every Monday and says nothing of what is in it. OC-19 is what puts the report in it. Neither is worth releasing without the other. They are Slice 7."),
    ("\"See the last 7 days' orders\" (OC-01 to OC-04, OC-07, OC-08) and \"Refunds are shown and not counted\" (OC-09, OC-10)",
     "A first version kept these apart, with a note that a manager \"must be told\" the sum counts refunded orders. A reader pointed out that the telling had no channel: no criterion puts a warning on the page, and none may be added. A sum known to be wrong cannot be the first thing released. They are Slice 1."),
]
# Criteria put in one slice for a reason that is NOT that they must ship together. Each could be cut further.
TOGETHER_BY_CHOICE = [
    ("OC-17, deleting a saved report, in Slice 6", "It could ship after saving and opening. It is with them because a list that can only grow is a poor thing to release."),
    ("OC-11 and OC-12, the per-day table and the chart, in Slice 4", "OC-12 needs OC-11 and not the other way, so the table could ship first. They are one slice because the chart is small once the figures exist. That is a reason of effort, and there is no team here to estimate any."),
    ("OC-05 and OC-20, choosing dates and the 5 seconds, in Slice 2", "Dates could ship without the speed: a slow report is still a report. They are together because OC-20 alone is not something a manager is given."),
]

# What cutting the story showed that the original does not say. None of it is fixed here: nothing may be added.
GAPS = [
    "No criterion puts the period on the page. A manager cannot see which days the list is for.",
    "An order refunded in part is not mentioned. OC-09 and OC-10 speak only of one refunded in full.",
    "OC-11 does not say whether a day's sum leaves out refunded orders, as OC-10 says the sum below the list does.",
    "OC-02 refuses the page to staff who are not managers. Nothing says the same of the address the CSV file comes from.",
    "\"Today\" in OC-04 has no time zone, and nothing says whether the part of today so far is included.",
    "OC-14 saves a period, and OC-19 sends \"the 7 days before\". Which holds for a saved report whose period is a month is not said.",
    "Nothing says what happens to a weekly email when its saved report is deleted (OC-17, OC-18).",
    "OC-20 gives a time for the list. It gives none for the per-day table, the chart or the file.",
    "OC-07 counts the orders listed, and a refunded order is listed. So the count includes orders that OC-10 leaves out of the sum.",
    "The file of OC-13 has three columns. It does not carry the word \"Refunded\" that OC-09 puts on the page, and it does not say what was in an order.",
    "OC-11 speaks of \"orders placed that day\" and not of orders listed. Whether the per-day table follows a product chosen under OC-06 is not said.",
    "OC-14 does not say whether a saved period is fixed dates or \"the last so many days\".",
    "OC-20 does not say whether it must hold with a product chosen, or once the per-day table and chart are on the page.",
    "OC-06 presses \"Show\", the button OC-05 introduces. It is taken here to be the same button, which is why OC-06 needs OC-05.",
]

# The slicing that was rejected: by technical layer. For each criterion, the layers that must be finished before it holds.
LAYERS = [
    ("L1", "The data layer", "Queries for the orders of a period, their count and sum, the per-day figures, and storage for saved reports and schedules."),
    ("L2", "The server layer", "Addresses the page calls for the list, the figures, the CSV file, saved reports and the schedule, with the check of the manager role."),
    ("L3", "The screens", "The Sales report page, its date and product boxes, the table, the chart, the saved-report list and the buttons."),
    ("L4", "The background job", "The job that runs every Monday at 07:00 and sends the emails."),
]
LAYERS_NEEDED = {
    "OC-18": ["L1", "L2", "L3", "L4"],
    "OC-19": ["L1", "L2", "L3", "L4"],
}
DEFAULT_LAYERS = ["L1", "L2", "L3"]

# The second slicing that was rejected: by the story's own seven areas. It is the more tempting one, because each area
# sounds like a feature. slice.py works its counts out from the area in each criterion's heading.
AREAS_WHY = [
    ("The page", "A page with a heading and a lock, and nothing on it. Nothing a manager can use is released first."),
    ("The list", "The orders with no count and no sum, and with dates and a product to choose, which a first release does not need. It answers \"what did we sell\" and not \"what did it come to\"."),
    ("The figures", "It bundles the count, the sum and the refunds, which the first release needs, with a per-day table and a chart, which it does not."),
    ("The export", "This one is a real slice, and is Slice 3."),
    ("Saved reports", "This one is a real slice, and is Slice 6."),
    ("The weekly email", "This one is a real slice, and is Slice 7."),
    ("Speed", "A quality on its own. Checking it last, after everything that could slow the page, is defensible. Releasing it as a slice is not: a manager is given nothing."),
]

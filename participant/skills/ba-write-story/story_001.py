"""Story 001, written down by hand under the standard in story.py.

Written by an AI assistant (Claude) at the participant's direction. Every part names the lines of the meeting it
rests on, or says that it is the writer's assumption. No words of the meeting are copied here as quotations:
story.py takes every quotation from the source record.

The out-of-scope list was written first, before any criterion. It is first in this file for that reason.
"""

SOURCE = "sample-meeting"          # the transcript record, in participant/context/transcripts
WORK_ITEM = "W-01"                 # the candidate work item this story is written from
OWNER = "the product owner"        # who would confirm an assumption. A role. The meeting is made up

# What is NOT in this story. Written first. "where" is an item of the work-items file (W-, R-) or the decisions
# file (O-), or None when the meeting did not discuss it at all.
OUT_OF_SCOPE = [
    {"text": "The offer to link a guest's order to an account they already have.", "where": ["W-02", "W-05", "O-01", "O-02"], "lines": ["U-0008", "U-0019", "U-0020", "U-0021", "U-0023"],
     "why": "THIS BOUNDARY IS THE WRITER'S, NOT THE MEETING'S. The product owner listed the linking offer as one of three acceptance criteria of this same story. "
            "It is taken out because two parts of it are not settled, how often it is offered and whether it times out, and this story can be built and tested without it. "
            "The product owner undertook to find out how often it is offered (W-05), and nothing here waits for her answer. "
            "Nothing said in the meeting supports the split. The developer's rough guess mentions the linking by name, in a line where he also says he has not sized the work, and that can be read either way. See open question Q-07."},
    {"text": "Any time-out on that offer.", "where": ["R-01", "O-01"], "lines": ["U-0011", "U-0012"],
     "why": "It was asked about and parked. Nobody said one should be built."},
    {"text": "What is done with the phone number once it is given: printing it on the shipping label, and keeping it out of marketing.", "where": ["W-03"], "lines": ["U-0013", "U-0014"],
     "why": "The earlier work-items file made it a separate item, which carries both rules. The meeting made no such split: the boundary is the writer's. This story only takes the number when the guest gives one."},
    {"text": "Sending staging receipts to a test address.", "where": ["W-04"], "lines": ["U-0005", "U-0006"],
     "why": "It is test set-up, and a separate item in the earlier work-items file. The boundary is the writer's. The tests of this story use that address and do not set it up."},
    {"text": "Any way of paying other than a card.", "where": None, "lines": ["U-0019"],
     "why": "The meeting said a guest can pay with a card, and named no other way. That no other way is built here is the writer's reading."},
    {"text": "Offering a guest an account, or a way to create one, from the checkout.", "where": None, "lines": ["U-0002"],
     "why": "The meeting's point was buying without making one. Nothing was said about offering one. Leaving it out is the writer's reading. This story does not build an offer, and does not forbid one either: see Q-11."},
    {"text": "Checkout for a customer who is signed in.", "where": None, "lines": ["U-0002"],
     "why": "Nothing was said about changing it. Leaving it out is the writer's reading."},
]

STORY = {
    "title": "Guest checkout without an account",
    "user": ("A customer who does not have an account.", ["U-0002"]),
    "value": ("They can buy without making one.", ["U-0002"]),
    "value_note": "The meeting said what the customer can then do. It did not say why that matters to the business, or how anyone would know it had worked. That is open question Q-08. "
                  "One part of the story, criteria AC-05 to AC-07, is about an email address that already has an account. The meeting raised that case, and this user statement does not cover it.",
}

# What is built, each with the criteria that test it.
IN_SCOPE = [
    ("A customer with no account can place an order without making one.", ["U-0002"], ["AC-01", "AC-02"]),
    ("The checkout asks a guest for an email address and requires it.", ["U-0003", "U-0004"], ["AC-03", "AC-09", "AC-10", "AC-11"]),
    ("The checkout lets a guest give a phone number, and does not require it. No criterion shows that a number, once given, was taken: see Q-17.", ["U-0004"], ["AC-01", "AC-04"]),
    ("A guest whose email address already has an account is not made to log in.", ["U-0007", "U-0008"], ["AC-05", "AC-06"]),
    ("An order placed that way is not attached to the account. The meeting's words were \"until they say yes\". In this story nobody is asked, so it stays unattached.", ["U-0009", "U-0010"], ["AC-07"]),
    ("A guest can pay with a card.", ["U-0019"], ["AC-01", "AC-12", "AC-13", "AC-14"]),
    ("A guest gets a receipt by email.", ["U-0019"], ["AC-08", "AC-15", "AC-16", "AC-17", "AC-18"]),
]

# What the story takes as already there. None of it was said in the meeting.
TAKEN_AS_GIVEN = [
    "The shop already has a basket, and a checkout that a signed-in customer uses, with its own fields for a name and a delivery address. The meeting did not describe them. This story does not change them, and a tester fills them in as for any order. See Q-12.",
    "A signed-in customer can see a list of their orders.",
    "A person who is not signed in can get from the basket into the checkout. How, the meeting did not say. See Q-14.",
]

# Words a criterion uses in a particular meaning. (word, meaning, "said" or "assumed", lines)
GLOSSARY = [
    ("guest", "a person going through checkout who is not signed in, whether or not they have an account", "assumed", ["U-0002", "U-0007"]),
    ("placed", "an order is placed when, within 10 seconds of the action, the confirmation page is shown with an order reference on it", "assumed", []),
    ("not placed", "an order is not placed when, 10 seconds after the action, the confirmation page has not been shown", "assumed", []),
    ("complete the checkout", "to complete the checkout is to fill in every field it has with the data named, and then to pay", "assumed", []),
    ("pay with", "to pay with a card is to enter that card's details and press the control that places the order", "assumed", []),
    ("require", "the checkout requires something when the guest cannot get to the confirmation page without doing it. A link or a notice that the guest can pass by is not a requirement", "assumed", ["U-0007", "U-0008"]),
    ("empty", "a field is empty when nothing has been typed in it, or only spaces", "assumed", []),
    ("valid", "an email address is valid when it is one or more characters that are neither a space nor @, then one @, then one or more such characters, then a dot, then one or more such characters, and nothing else", "assumed", []),
    ("accepted test card", "the card number that the payment provider's test mode documents as always accepted", "assumed", []),
    ("declined test card", "the card number that the payment provider's test mode documents as always declined for lack of funds", "assumed", []),
    ("receipt", "an email whose subject line holds the order reference", "assumed", []),
    ("receipt wait", "5 minutes, counted from when the confirmation page is shown", "assumed", []),
    ("list of orders", "the page on which a signed-in customer sees the orders attached to their account", "assumed", []),
]

# The data a tester uses. None of it was said in the meeting, except that a test address exists.
TEST_SETUP = [
    ("Where", "The staging system. The meeting did not give its address."),
    ("B1", "A basket of two different products, one with a quantity of 2 and one with a quantity of 1. Any two products on staging."),
    ("D1", "The details a guest types: the email address E1, the phone number P1, and every other field the checkout has, filled in as for any order."),
    ("E1", "The staging test address agreed in the meeting (work item W-04). It is redacted in the record, so it is not written here. No account has it."),
    ("P1", "01632 960001, a number from a range kept for made-up use."),
    ("A1 and X1", "A test account A1 that the tester can log in to, whose email address X1 is a second test address the tester can read. The meeting agreed one test address. A second is the writer's: see Q-13."),
    ("Cards", "The accepted test card and the declined test card. The meeting named no payment provider: see Q-10."),
    ("Email addresses that are not valid", "Three values, each used in turn: `guest.example.test`, `guest-at-example`, `gu est.example.test`. None has an @."),
    ("Inboxes", "The tester can open the inboxes of E1 and X1."),
]


def said(number, given, when, then, lines):
    return {"id": "AC-%02d" % number, "basis": "SAID", "given": given, "when": when, "then": then, "lines": lines}


def assumed(number, given, when, then, question):
    return {"id": "AC-%02d" % number, "basis": "ASSUMED", "given": given, "when": when, "then": then, "question": question}


STANDARD_PATH = "they complete the checkout with D1 and pay with the accepted test card"
WITH_X1 = "a guest with basket B1, using D1 with the email address X1 in place of E1"

CRITERIA = [
    said(1, "a guest with basket B1", STANDARD_PATH, "the order is placed", ["U-0002", "U-0019"]),
    dict(said(2, "a guest with basket B1", STANDARD_PATH, "the checkout did not require them to create an account", ["U-0002"]),
         note="This is seen in the same run as AC-01. It fails only if some step cannot be passed without creating an account."),
    said(3, "a guest with basket B1 who has filled in D1 and the details of the accepted test card, and left the email address empty", "they press the control that places the order", "the order is not placed", ["U-0003", "U-0004"]),
    said(4, "a guest with basket B1 who has filled in D1 and left the phone number empty", "they pay with the accepted test card", "the order is placed", ["U-0004"]),
    said(5, WITH_X1, "they complete the checkout and pay with the accepted test card", "the order is placed", ["U-0007", "U-0008"]),
    dict(said(6, WITH_X1, "they complete the checkout and pay with the accepted test card", "the checkout did not require them to log in", ["U-0007", "U-0008"]),
         note="This is seen in the same run as AC-05. It fails only if some step cannot be passed without logging in. Whether a notice or a link that can be passed by is allowed is Q-11."),
    dict(said(7, "an order that a guest has placed using the email address X1", "the tester logs in as A1 and opens its list of orders", "that order is not in the list", ["U-0009", "U-0010"]),
         note="The meeting said the order is not attached \"until they say yes\". This story has no step that asks, so the criterion tests that it is not attached at all. "
              "The rule comes from decision D-05, which the earlier work-items file put under W-02. Whether an order is attached is judged by whether the account's list shows it, and that way of seeing it is the writer's."),
    dict(said(8, "an order that a guest has placed using D1", "the tester opens the inbox of E1 once the receipt wait has passed", "a receipt for that order is in the inbox", ["U-0003", "U-0004", "U-0019"]),
         note="That a guest gets a receipt by email is the meeting's. The 5 minutes, and telling a receipt by its subject line, are the writer's, and each is a requirement of its own: see Q-05 and Q-06. "
              "That the receipt goes to the address typed at checkout is read from the developer's reason for asking for one."),
    assumed(9, "a guest with basket B1 who has filled in D1 and the details of the accepted test card, and left the email address empty", "they press the control that places the order",
            "the message \"Enter an email address\" is shown directly below the email field", "Q-01"),
    assumed(10, "a guest with basket B1 who has filled in D1 and the details of the accepted test card, with an email address that is not valid in place of E1", "they press the control that places the order", "the order is not placed", "Q-02"),
    assumed(11, "a guest with basket B1 who has filled in D1 and the details of the accepted test card, with an email address that is not valid in place of E1", "they press the control that places the order",
            "the message \"Enter a valid email address\" is shown directly below the email field", "Q-02"),
    assumed(12, "a guest with basket B1 who has filled in D1", "they pay with the declined test card", "the order is not placed", "Q-03"),
    assumed(13, "a guest with basket B1 who has filled in D1", "they pay with the declined test card", "the message \"Your card was declined\" is shown at the top of the page they are on", "Q-03"),
    assumed(14, "a guest whose payment with the declined test card has just been refused", "they open the basket", "it holds the two products of B1 in the quantities of B1", "Q-03"),
    assumed(15, "an order that a guest has placed using D1", "they read the confirmation page", "it shows the sentence \"A receipt has been sent to\" followed by E1 as it was typed", "Q-04"),
    assumed(16, "the receipt of an order that a guest has placed using D1", "the tester reads it", "its body holds the order reference that the confirmation page showed", "Q-05"),
    assumed(17, "the receipt of an order that a guest has placed using D1", "the tester reads it", "it names each of the two products of B1 with its quantity", "Q-05"),
    assumed(18, "the receipt of an order that a guest has placed using D1", "the tester reads it", "it gives a total equal to the total the checkout showed before payment", "Q-05"),
]

# (what, "said" or "assumed", lines)
DEPENDENCIES = [
    ("The staging test address, work item W-04. AC-08 and AC-15 to AC-18 are tested by reading the inbox of E1. That a test address may be used was agreed in the meeting. That this story waits on it is the writer's.", "assumed", ["U-0005", "U-0006"]),
    ("A second test address, and a test account that has it, for AC-05 to AC-07.", "assumed", []),
    ("A way to take a card payment in test mode. The meeting said a guest can pay with a card. It did not say how.", "assumed", []),
    ("A way to send email from the checkout. The meeting said a guest gets an email receipt. It did not say what sends it.", "assumed", []),
]

# Open questions that still affect the story. (id, question, criteria that depend on it, open item of the decisions file or None)
ALL = [c["id"] for c in CRITERIA]


def using(*words):
    return [c["id"] for c in CRITERIA if any(w in " ".join((c["given"], c["when"], c["then"])) for w in words)]


QUESTIONS = [
    ("Q-01", "What does a guest see when the email address is left empty?", ["AC-09"], None),
    ("Q-02", "What counts as an email address the checkout accepts, and what does a guest see when theirs is not one?", ["AC-10", "AC-11"], None),
    ("Q-03", "What happens when the card is declined: what is shown, where, and is the basket kept?", ["AC-12", "AC-13", "AC-14"], None),
    ("Q-04", "What does a guest see once the order is placed, and how is the confirmation page told from any other?", using("placed", "confirmation page", "receipt"), None),
    ("Q-05", "What is in the receipt, and how is one told from any other email?", using("receipt"), None),
    ("Q-06", "How soon after the order must the receipt arrive?", ["AC-08"], None),
    ("Q-07", "Is it accepted that the linking offer is a separate story? The product owner gave it as an acceptance criterion of this one, and undertook to find out how often it is offered (W-05). The split is the writer's.", [], None),
    ("Q-08", "Why does guest checkout matter to the business, and how would anyone know it had worked?", [], None),
    ("Q-09", "How large is this story? The size is not settled. The developer said he will size it \"once that's settled\", and did not name what.", [], "O-03"),
    ("Q-10", "Which payment provider is used, which cards are accepted, and what are the details of its test cards?", using("test card"), None),
    ("Q-11", "Does \"not made to log in\" forbid only a step the guest cannot pass, or also a link or notice inviting them to log in or to create an account? This story takes the first reading.", ["AC-02", "AC-06"], None),
    ("Q-12", "What other fields does the checkout have, is any of them different for a guest, and what does a tester type in them?", ALL, None),
    ("Q-13", "Can a second test address and a test account be provided on staging?", ["AC-05", "AC-06", "AC-07"], None),
    ("Q-14", "How does a person who is not signed in get into the checkout: is there a choice to continue as a guest?", ALL, None),
    ("Q-15", "When a guest's email address matches an account, is anything recorded so that the linking offer can be made later?", ["AC-07"], None),
    ("Q-16", "What takes the card payment, and what sends the receipt?", using("test card", "receipt"), None),
    ("Q-17", "Where can a tester see that a phone number, once given, was taken?", ["AC-01"], None),
    ("Q-18", "Where is the staging system, what is the test address E1, and how does a tester read its inbox?", ALL, None),
    ("Q-19", "Is the checkout one page or several, and is the email address checked when the order is placed or earlier? If earlier, a guest with no email address never reaches the control that places the order.", ["AC-03", "AC-09", "AC-10", "AC-11"], None),
    ("Q-20", "Are these the writer's readings right: 10 seconds to decide an order was not placed, a field holding only spaces counting as empty, and \"guest\" covering a person who has an account?", using("placed", "empty", "guest"), None),
    ("Q-21", "Does the account's list of orders show each order's reference, so that one order can be told from another?", ["AC-07"], None),
]

# Kept apart from the acceptance criteria. This is how the team would know the work is finished, not what the
# product does. None of it is from the meeting.
DEFINITION_OF_DONE = [
    "Every acceptance criterion above passes on staging.",
    "Every criterion marked ASSUMED, and every definition marked ASSUMED, has been confirmed by the product owner or replaced by what they said.",
    "The only email addresses typed into the checkout while testing were test addresses.",
    "No real customer's name, address, email address or card was used in any test.",
    "The product owner has seen the story working and accepted it.",
]

# Lines of the meeting the story cites nowhere, each with the reason. Every line is cited or listed here.
NOT_USED = {
    "U-0001": "opens the meeting",
    "U-0015": "gives a contact number for carriers about test orders. Nothing in this story uses it",
    "U-0016": "reads like an instruction to a tool. It is something a person said. Nothing is done with it",
    "U-0017": "a reaction to U-0016",
    "U-0018": "its speaker's account of U-0016",
    "U-0022": "says where to reach the person who can answer it",
    "U-0024": "closes the meeting",
}

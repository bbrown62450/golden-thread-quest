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
    ("The checkout asks a guest for an email address and requires it.", ["U-0003", "U-0004"], ["AC-03", "AC-10", "AC-11", "AC-12"]),
    ("The checkout lets a guest give a phone number, and does not require it.", ["U-0004"], ["AC-01", "AC-04", "AC-09"]),
    ("A guest whose email address already has an account is not made to log in.", ["U-0007", "U-0008"], ["AC-05", "AC-06"]),
    ("An order placed that way is not attached to the account. The meeting's words were \"until they say yes\". In this story nobody is asked, so it stays unattached.", ["U-0009", "U-0010"], ["AC-07"]),
    ("A guest can pay with a card.", ["U-0019"], ["AC-01", "AC-13", "AC-14", "AC-15", "AC-16"]),
    ("A guest gets a receipt by email.", ["U-0019"], ["AC-08", "AC-17", "AC-18", "AC-19", "AC-20", "AC-21"]),
]

# What the story takes as already there. None of it was said in the meeting.
TAKEN_AS_GIVEN = [
    "The shop already has a Basket page with a \"Checkout\" button, and a Checkout page that a signed-in customer uses. This story does not change either for a signed-in customer.",
    "A signed-in customer has a Your orders page, which lists each of their orders by its order reference.",
    "Staging has a Test tools page, as described under \"Test set-up\".",
]

# Words a criterion uses in a particular meaning. (word, meaning, "said" or "assumed", lines)
GLOSSARY = [
    ("guest", "a person going through checkout who is not signed in, whether or not they have an account", "assumed", ["U-0002", "U-0007"]),
    ("placed", "an order is placed when, within 10 seconds of pressing \"Place order\", the Order confirmed page is shown with an order reference on it", "assumed", []),
    ("not placed", "an order is not placed when, 10 seconds after pressing \"Place order\", the Order confirmed page has not been shown", "assumed", []),
    ("order reference", "the text that follows the words \"Order reference:\" on the Order confirmed page. It is GT- and six digits", "assumed", []),
    ("require", "the checkout requires something when the guest cannot get to the Order confirmed page without doing it. A link, a button or a notice that the guest can pass by is not a requirement", "assumed", ["U-0007", "U-0008"]),
    ("empty", "a field is empty when nothing has been typed in it", "assumed", []),
    ("valid", "an email address is valid when it is one or more characters that are neither a space nor @, then one @, then one or more such characters, then a dot, then one or more such characters, and nothing else", "assumed", []),
    ("receipt", "an email whose subject is the words \"Your receipt for order\" followed by the order reference", "assumed", []),
    ("receipt wait", "5 minutes, counted from when the Order confirmed page is shown", "assumed", []),
    ("directly below", "a message is directly below a field when it is the next text on the page after that field, before the label of the next field", "assumed", []),
    ("at the top of the page", "a message is at the top of the page when it is the first text after the page's heading, before the first field", "assumed", []),
]

# Everything a tester needs to run the tests. All of it is made up by the writer, and marked ASSUMED in the story.
TEST_SETUP = [
    ("Staging", "`https://staging.shop.example.test`. Every page below is on it."),
    ("Test tools", "The page `/test-tools`. It has a button \"Empty the basket and sign out\", a button \"Log in as A1\", and a link \"Test inbox\"."),
    ("Test inbox", "The page `/test-tools/inbox`. It lists every email staging has sent, newest first. For each it shows the address it was sent to, its subject and its body."),
    ("B1", "The basket made by this: on Test tools press \"Empty the basket and sign out\". Open `/products/test-mug` and press \"Add to basket\" twice. Open `/products/test-notebook` and press \"Add to basket\" once. A Test Mug is £4.00 and a Test Notebook is £6.00. Delivery on staging is free."),
    ("Reaching the Checkout page as a guest", "With basket B1, open `/basket` and press \"Checkout\". A page offers two buttons, \"Log in\" and \"Continue as guest\". Press \"Continue as guest\". The Checkout page opens."),
    ("The Checkout page", "One page, headed \"Checkout\". It shows the line \"Total: £14.00\" for B1. Its fields, in order: Email address, Phone number, Full name, Address line 1, Town or city, Postcode, Card number, Expiry date, Security code. Then one button, \"Place order\". Nothing is checked until \"Place order\" is pressed."),
    ("D1", "What a guest types: Email address `receipts@staging.example.test` (this is E1). Phone number `01632 960001` (P1). Full name `Test Guest`. Address line 1 `1 Example Street`. Town or city `Exampleton`. Postcode `EX1 1EX`. Card number, Expiry date and Security code: the accepted card."),
    ("E1", "`receipts@staging.example.test`, standing for the staging test address agreed in the meeting (work item W-04), which is redacted in the record. No account has it."),
    ("A1 and X1", "The test account A1, whose email address X1 is `account-holder@staging.example.test`. \"Log in as A1\" on Test tools signs the tester in as A1 with no password."),
    ("The accepted card", "Card number `0000 0000 0000 0001`, expiry date `12/30`, security code `123`. Staging's payment test mode always accepts it. It is not a real card number."),
    ("The declined card", "Card number `0000 0000 0000 0002`, expiry date `12/30`, security code `123`. Staging's payment test mode always declines it."),
    ("An email address that is not valid", "`guest.example.test`. It has no @."),
    ("The Order confirmed page", "The page headed \"Order confirmed\". It shows the line \"Order reference:\" followed by the order reference."),
    ("Opening Your orders as A1", "On Test tools press \"Log in as A1\", then open `/account/orders`. The page is headed \"Your orders\"."),
    ("The Basket page", "`/basket`. It shows one line for each product, as the product's name, a comma, the word \"quantity\" and the number."),
]


def said(number, given, when, then, lines):
    return {"id": "AC-%02d" % number, "basis": "SAID", "given": given, "when": when, "then": then, "lines": lines}


def assumed(number, given, when, then, question):
    return {"id": "AC-%02d" % number, "basis": "ASSUMED", "given": given, "when": when, "then": then, "question": question}


AT_CHECKOUT = "a guest who has reached the Checkout page with basket B1 and typed D1"
PRESS = "they press \"Place order\""
PLACED_D1 = "an order that a guest has placed with D1"
DECLINED = AT_CHECKOUT + ", with the declined card in place of the accepted card"
NOT_VALID = AT_CHECKOUT + ", with an email address that is not valid, `guest.example.test`, in the Email address field"
RECEIPT = "the receipt of an order that a guest has placed with D1, open in the Test inbox"

CRITERIA = [
    said(1, AT_CHECKOUT, PRESS, "the order is placed", ["U-0002", "U-0019"]),
    dict(said(2, AT_CHECKOUT, PRESS, "the checkout did not require them to create an account", ["U-0002"]),
         note="This is seen in the same run as AC-01. It fails only if some step cannot be passed without creating an account."),
    said(3, AT_CHECKOUT + ", with the Email address field left empty", PRESS, "the order is not placed", ["U-0003", "U-0004"]),
    said(4, AT_CHECKOUT + ", with the Phone number field left empty", PRESS, "the order is placed", ["U-0004"]),
    said(5, AT_CHECKOUT + ", with X1 in the Email address field", PRESS, "the order is placed", ["U-0007", "U-0008"]),
    dict(said(6, AT_CHECKOUT + ", with X1 in the Email address field", PRESS, "the checkout did not require them to log in", ["U-0007", "U-0008"]),
         note="This is seen in the same run as AC-05. It fails only if some step cannot be passed without logging in. The \"Log in\" button offered on the way to the Checkout page can be passed by, so it is not a requirement. Whether such a button or notice is wanted at all is Q-11."),
    dict(said(7, "an order that a guest has placed with D1 and with X1 in the Email address field", "the tester opens Your orders as A1", "no order on that page has that order reference", ["U-0009", "U-0010"]),
         note="The meeting said the order is not attached \"until they say yes\". This story has no step that asks, so the criterion tests that it is not attached at all. "
              "The rule comes from decision D-05, which the earlier work-items file put under W-02. Whether an order is attached is judged by whether Your orders shows it, and that way of seeing it is the writer's."),
    dict(said(8, PLACED_D1, "the tester opens the Test inbox once the receipt wait has passed", "the address it shows for the receipt for that order is E1", ["U-0003", "U-0004", "U-0019"]),
         note="That a guest gets a receipt by email is the meeting's. The 5 minutes, and telling a receipt by its subject, are the writer's, and each is a requirement of its own: see Q-05 and Q-06. "
              "That the receipt goes to the address typed at checkout is read from the developer's reason for asking for one."),
    assumed(9, PLACED_D1, "they read the Order confirmed page", "it shows the line \"Phone: 01632 960001\"", "Q-17"),
    assumed(10, AT_CHECKOUT + ", with the Email address field left empty", PRESS, "the message \"Enter an email address\" is shown directly below the Email address field", "Q-01"),
    assumed(11, NOT_VALID, PRESS, "the order is not placed", "Q-02"),
    assumed(12, NOT_VALID, PRESS, "the message \"Enter a valid email address\" is shown directly below the Email address field", "Q-02"),
    assumed(13, DECLINED, PRESS, "the order is not placed", "Q-03"),
    assumed(14, DECLINED, PRESS, "the message \"Your card was declined\" is shown at the top of the page", "Q-03"),
    assumed(15, "a guest who has just seen the message \"Your card was declined\" on the Checkout page", "they open the Basket page", "it shows the line \"Test Mug, quantity 2\"", "Q-03"),
    assumed(16, "a guest who has just seen the message \"Your card was declined\" on the Checkout page", "they open the Basket page", "it shows the line \"Test Notebook, quantity 1\"", "Q-03"),
    assumed(17, PLACED_D1, "they read the Order confirmed page", "it shows the line \"A receipt has been sent to receipts@staging.example.test\"", "Q-04"),
    assumed(18, RECEIPT, "the tester reads its body", "the body holds the order reference", "Q-05"),
    assumed(19, RECEIPT, "the tester reads its body", "the body holds the line \"Test Mug, quantity 2\"", "Q-05"),
    assumed(20, RECEIPT, "the tester reads its body", "the body holds the line \"Test Notebook, quantity 1\"", "Q-05"),
    assumed(21, RECEIPT, "the tester reads its body", "the body holds the line \"Total: £14.00\"", "Q-05"),
]

# (what, "said" or "assumed", lines)
DEPENDENCIES = [
    ("The staging test address, work item W-04. That a test address may be used was agreed in the meeting. That this story waits on it is the writer's.", "assumed", ["U-0005", "U-0006"]),
    ("A staging system with the Test tools page, the two test products, the test account A1 and a payment test mode, as \"Test set-up\" describes them.", "assumed", []),
    ("A way to send email from the checkout. The meeting said a guest gets an email receipt. It did not say what sends it.", "assumed", []),
]

# Open questions that still affect the story.
# (id, question, criteria that depend on it, open item of the decisions file or None, True if this story supplies an assumed answer)
ALL = [c["id"] for c in CRITERIA]


def using(*words):
    return [c["id"] for c in CRITERIA if any(w in " ".join((c["given"], c["when"], c["then"])) for w in words)]


QUESTIONS = [
    ("Q-01", "What does a guest see when the email address is left empty?", ["AC-10"], None, True),
    ("Q-02", "What counts as an email address the checkout accepts, and what does a guest see when theirs is not one?", ["AC-11", "AC-12"], None, True),
    ("Q-03", "What happens when the card is declined: what is shown, where, and is the basket kept?", ["AC-13", "AC-14", "AC-15", "AC-16"], None, True),
    ("Q-04", "What does a guest see once the order is placed?", using("placed", "Order confirmed", "order reference"), None, True),
    ("Q-05", "What is in the receipt, and how is one told from any other email?", using("receipt"), None, True),
    ("Q-06", "How soon after the order must the receipt arrive?", ["AC-08"], None, True),
    ("Q-10", "Which payment provider is used, and what are its test cards?", ALL, None, True),
    ("Q-11", "Does \"not made to log in\" forbid only a step the guest cannot pass, or also a button or notice inviting them to log in or to create an account? This story takes the first reading.", ["AC-02", "AC-06"], None, True),
    ("Q-12", "What fields does the checkout have, and what does a tester type in them?", ALL, None, True),
    ("Q-13", "Is there a test account on staging whose email address a tester can use?", ["AC-05", "AC-06", "AC-07"], None, True),
    ("Q-14", "How does a person who is not signed in get into the checkout?", ALL, None, True),
    ("Q-17", "Where can a tester see that a phone number, once given, was taken?", ["AC-09"], None, True),
    ("Q-18", "Where is the staging system, and how does a tester read the email it sends?", ALL, None, True),
    ("Q-19", "Is the checkout one page or several, and when is the email address checked?", ["AC-03", "AC-10", "AC-11", "AC-12"], None, True),
    ("Q-20", "Are these readings right: 10 seconds to decide an order was not placed, and \"guest\" covering a person who has an account?", using("placed", "guest"), None, True),
    ("Q-21", "Does Your orders show each order's reference?", ["AC-07"], None, True),
    ("Q-07", "Is it accepted that the linking offer is a separate story? The product owner gave it as an acceptance criterion of this one, and undertook to find out how often it is offered (W-05). The split is the writer's.", [], None, False),
    ("Q-08", "Why does guest checkout matter to the business, and how would anyone know it had worked?", [], None, False),
    ("Q-09", "How large is this story? The size is not settled. The developer said he will size it \"once that's settled\", and did not name what.", [], "O-03", False),
    ("Q-15", "When a guest's email address matches an account, is anything recorded so that the linking offer can be made later?", [], None, False),
]

# Kept apart from the acceptance criteria. This is how the team would know the work is finished, not what the
# product does. None of it is from the meeting.
DEFINITION_OF_DONE = [
    "Every acceptance criterion above passes on staging.",
    "Every criterion marked ASSUMED, every definition marked ASSUMED and every line of the test set-up has been confirmed by the product owner or replaced by what they said.",
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

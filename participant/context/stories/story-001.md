# Story 001: Guest checkout without an account

A draft for a person to decide on. **Nothing here was created in any tracker.** The meeting it comes from is made up.

- source_record: `participant/context/transcripts/sample-meeting.md`
- transcript_id: `tr-2026-10-21-checkout-refinement`
- source_sha256: `449ff64385bd96358693d9492b6c270e37d45c4235fdce1c9863e709c8ea9882`
- work_item: W-01 of `participant/context/transcripts/sample-meeting.work-items.md`
- standard: `participant/context/stories/story-standard.md`

Written by `participant/skills/ba-write-story/story.py build`. The story was composed by an AI assistant (Claude). Every
speaker and every quotation is copied from the transcript record by the program.

**How much of this is the meeting's.** Acceptance criteria: 18. SAID by the meeting: 8. ASSUMED by the writer: 10.
Of the 8 SAID, 8 use a word whose meaning the writer had to define.

- A criterion marked **SAID** states a requirement the meeting gave, and quotes the lines. How a tester sees the result is
  usually not something the meeting gave. Where a SAID criterion leans on a word the writer defined, it says which.
- A criterion marked **ASSUMED** is the writer's proposal, put in so that the story can be tested. The meeting did not
  decide it. It stands only until the product owner confirms or replaces it.
- The meeting gave no test data beyond agreeing that a test address may be used. Everything else under "Test set-up",
  and everything under "Taken as given", is the writer's.
- **One of the product owner's three acceptance criteria, the linking offer, is not in this story.** Taking it out is the
  writer's choice and not the meeting's. See the first entry under "Out of scope", and open question Q-07.

## The story

- User: A customer who does not have an account.
- Source for the user: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- Value: They can buy without making one.
- Source for the value: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- Not said: The meeting said what the customer can then do. It did not say why that matters to the business, or how anyone would know it had worked. That is open question Q-08. One part of the story, criteria AC-05 to AC-07, is about an email address that already has an account. The meeting raised that case, and this user statement does not cover it.

## Out of scope

Written first, before any criterion. Each says why it is out and where it went.

1. **The offer to link a guest's order to an account they already have.**
   - Why it is out: THIS BOUNDARY IS THE WRITER'S, NOT THE MEETING'S. The product owner listed the linking offer as one of three acceptance criteria of this same story. It is taken out because two parts of it are not settled, how often it is offered and whether it times out, and this story can be built and tested without it. The product owner undertook to find out how often it is offered (W-05), and nothing here waits for her answer. Nothing said in the meeting supports the split. The developer's rough guess mentions the linking by name, in a line where he also says he has not sized the work, and that can be read either way. See open question Q-07.
   - Where it went: W-02, W-05, O-01, O-02
   - The line it turns on: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
   - The line it turns on: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
   - The line it turns on: Dana Whitfield, Tester, in U-0020: "Once per order, or once ever?"
   - The line it turns on: Priya Natarajan, Product owner, in U-0021: "Per order. No, wait. Let me check with Jordan and get back to you."
   - The line it turns on: Marcus Oyelaran, Developer, in U-0023: "I'll size it once that's settled. Rough guess is a five, maybe an eight with the linking."
2. **Any time-out on that offer.**
   - Why it is out: It was asked about and parked. Nobody said one should be built.
   - Where it went: R-01, O-01
   - The line it turns on: Unattributed, identity uncertain, in U-0011: "Should it time out? If they never answer the link offer?"
   - The line it turns on: Marcus Oyelaran, Developer, in U-0012: "Let's park that. I don't know the answer and I'd rather not guess."
3. **What is done with the phone number once it is given: printing it on the shipping label, and keeping it out of marketing.**
   - Why it is out: The earlier work-items file made it a separate item, which carries both rules. The meeting made no such split: the boundary is the writer's. This story only takes the number when the guest gives one.
   - Where it went: W-03
   - The line it turns on: Speaker 4, identity uncertain, in U-0013: "Sorry, I joined late. Is the phone number going on the shipping label, or just in our system?"
   - The line it turns on: Priya Natarajan, Product owner, in U-0014: "Shipping label only, for the carrier. We don't market to it."
4. **Sending staging receipts to a test address.**
   - Why it is out: It is test set-up, and a separate item in the earlier work-items file. The boundary is the writer's. The tests of this story use that address and do not set it up.
   - Where it went: W-04
   - The line it turns on: Dana Whitfield, Tester, in U-0005: "For testing I'd like an address that isn't anyone's real inbox. Can we use \[REDACTED:EMAIL\] for the staging receipts?"
   - The line it turns on: Priya Natarajan, Product owner, in U-0006: "That's fine."
5. **Any way of paying other than a card.**
   - Why it is out: The meeting said a guest can pay with a card, and named no other way. That no other way is built here is the writer's reading.
   - Where it went: nowhere. The meeting did not discuss it
   - The line it turns on: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
6. **Offering a guest an account, or a way to create one, from the checkout.**
   - Why it is out: The meeting's point was buying without making one. Nothing was said about offering one. Leaving it out is the writer's reading. This story does not build an offer, and does not forbid one either: see Q-11.
   - Where it went: nowhere. The meeting did not discuss it
   - The line it turns on: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
7. **Checkout for a customer who is signed in.**
   - Why it is out: Nothing was said about changing it. Leaving it out is the writer's reading.
   - Where it went: nowhere. The meeting did not discuss it
   - The line it turns on: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."

## In scope

Each says which criteria test it.

1. A customer with no account can place an order without making one.
   - Tested by: AC-01, AC-02
   - Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
2. The checkout asks a guest for an email address and requires it.
   - Tested by: AC-03
   - And, on the writer's assumptions, by: AC-09, AC-10, AC-11
   - Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
   - Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
3. The checkout lets a guest give a phone number, and does not require it. No criterion shows that a number, once given, was taken: see Q-17.
   - Tested by: AC-01, AC-04
   - Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
4. A guest whose email address already has an account is not made to log in.
   - Tested by: AC-05, AC-06
   - Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
   - Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
5. An order placed that way is not attached to the account. The meeting's words were "until they say yes". In this story nobody is asked, so it stays unattached.
   - Tested by: AC-07
   - Source: Dana Whitfield, Tester, in U-0009: "So the order is attached to the account, or it isn't until they say yes?"
   - Source: Priya Natarajan, Product owner, in U-0010: "It isn't until they say yes. Good question."
6. A guest can pay with a card.
   - Tested by: AC-01
   - And, on the writer's assumptions, by: AC-12, AC-13, AC-14
   - Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
7. A guest gets a receipt by email.
   - Tested by: AC-08
   - And, on the writer's assumptions, by: AC-15, AC-16, AC-17, AC-18
   - Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."

## Taken as given

What the story takes as already there. **None of this was said in the meeting.** It is ASSUMED.

1. The shop already has a basket, and a checkout that a signed-in customer uses, with its own fields for a name and a delivery address. The meeting did not describe them. This story does not change them, and a tester fills them in as for any order. See Q-12.
2. A signed-in customer can see a list of their orders.
3. A person who is not signed in can get from the basket into the checkout. How, the meeting did not say. See Q-14.

## Words this story defines

A criterion uses these words in these meanings and no other.

- **guest**: a person going through checkout who is not signed in, whether or not they have an account. ASSUMED: the meeting did not define it.
  - The line it is read from: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
  - The line it is read from: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- **placed**: an order is placed when, within 10 seconds of the action, the confirmation page is shown with an order reference on it. ASSUMED: the meeting did not define it.
- **not placed**: an order is not placed when, 10 seconds after the action, the confirmation page has not been shown. ASSUMED: the meeting did not define it.
- **complete the checkout**: to complete the checkout is to fill in every field it has with the data named, and then to pay. ASSUMED: the meeting did not define it.
- **pay with**: to pay with a card is to enter that card's details and press the control that places the order. ASSUMED: the meeting did not define it.
- **require**: the checkout requires something when the guest cannot get to the confirmation page without doing it. A link or a notice that the guest can pass by is not a requirement. ASSUMED: the meeting did not define it.
  - The line it is read from: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
  - The line it is read from: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
- **empty**: a field is empty when nothing has been typed in it, or only spaces. ASSUMED: the meeting did not define it.
- **valid**: an email address is valid when it is one or more characters that are neither a space nor @, then one @, then one or more such characters, then a dot, then one or more such characters, and nothing else. ASSUMED: the meeting did not define it.
- **accepted test card**: the card number that the payment provider's test mode documents as always accepted. ASSUMED: the meeting did not define it.
- **declined test card**: the card number that the payment provider's test mode documents as always declined for lack of funds. ASSUMED: the meeting did not define it.
- **receipt**: an email whose subject line holds the order reference. ASSUMED: the meeting did not define it.
- **receipt wait**: 5 minutes, counted from when the confirmation page is shown. ASSUMED: the meeting did not define it.
- **list of orders**: the page on which a signed-in customer sees the orders attached to their account. ASSUMED: the meeting did not define it.

## Test set-up

The data a tester uses, by the names the criteria use. **ASSUMED**, all of it, except that a test address was agreed.

| Name | What it is |
|---|---|
| Where | The staging system. The meeting did not give its address. |
| B1 | A basket of two different products, one with a quantity of 2 and one with a quantity of 1. Any two products on staging. |
| D1 | The details a guest types: the email address E1, the phone number P1, and every other field the checkout has, filled in as for any order. |
| E1 | The staging test address agreed in the meeting (work item W-04). It is redacted in the record, so it is not written here. No account has it. |
| P1 | 01632 960001, a number from a range kept for made-up use. |
| A1 and X1 | A test account A1 that the tester can log in to, whose email address X1 is a second test address the tester can read. The meeting agreed one test address. A second is the writer's: see Q-13. |
| Cards | The accepted test card and the declined test card. The meeting named no payment provider: see Q-10. |
| Email addresses that are not valid | Three values, each used in turn: `guest.example.test`, `guest-at-example`, `gu est.example.test`. None has an @. |
| Inboxes | The tester can open the inboxes of E1 and X1. |

## Acceptance criteria

Each is one starting state, one action and one result a person can see or read.

### AC-01 · SAID

- Given: a guest with basket B1.
- When: they complete the checkout with D1 and pay with the accepted test card.
- Then: the order is placed.
- Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, complete the checkout, pay with, accepted test card.

### AC-02 · SAID

- Given: a guest with basket B1.
- When: they complete the checkout with D1 and pay with the accepted test card.
- Then: the checkout did not require them to create an account.
- Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- The requirement is the meeting's. These words in it are defined by the writer: guest, complete the checkout, pay with, require, accepted test card.
- Note: This is seen in the same run as AC-01. It fails only if some step cannot be passed without creating an account.

### AC-03 · SAID

- Given: a guest with basket B1 who has filled in D1 and the details of the accepted test card, and left the email address empty.
- When: they press the control that places the order.
- Then: the order is not placed.
- Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
- The requirement is the meeting's. These words in it are defined by the writer: guest, not placed, empty, accepted test card.

### AC-04 · SAID

- Given: a guest with basket B1 who has filled in D1 and left the phone number empty.
- When: they pay with the accepted test card.
- Then: the order is placed.
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, pay with, empty, accepted test card.

### AC-05 · SAID

- Given: a guest with basket B1, using D1 with the email address X1 in place of E1.
- When: they complete the checkout and pay with the accepted test card.
- Then: the order is placed.
- Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, complete the checkout, pay with, accepted test card.

### AC-06 · SAID

- Given: a guest with basket B1, using D1 with the email address X1 in place of E1.
- When: they complete the checkout and pay with the accepted test card.
- Then: the checkout did not require them to log in.
- Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
- The requirement is the meeting's. These words in it are defined by the writer: guest, complete the checkout, pay with, require, accepted test card.
- Note: This is seen in the same run as AC-05. It fails only if some step cannot be passed without logging in. Whether a notice or a link that can be passed by is allowed is Q-11.

### AC-07 · SAID

- Given: an order that a guest has placed using the email address X1.
- When: the tester logs in as A1 and opens its list of orders.
- Then: that order is not in the list.
- Source: Dana Whitfield, Tester, in U-0009: "So the order is attached to the account, or it isn't until they say yes?"
- Source: Priya Natarajan, Product owner, in U-0010: "It isn't until they say yes. Good question."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, list of orders.
- Note: The meeting said the order is not attached "until they say yes". This story has no step that asks, so the criterion tests that it is not attached at all. The rule comes from decision D-05, which the earlier work-items file put under W-02. Whether an order is attached is judged by whether the account's list shows it, and that way of seeing it is the writer's.

### AC-08 · SAID

- Given: an order that a guest has placed using D1.
- When: the tester opens the inbox of E1 once the receipt wait has passed.
- Then: a receipt for that order is in the inbox.
- Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
- Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, receipt, receipt wait.
- Note: That a guest gets a receipt by email is the meeting's. The 5 minutes, and telling a receipt by its subject line, are the writer's, and each is a requirement of its own: see Q-05 and Q-06. That the receipt goes to the address typed at checkout is read from the developer's reason for asking for one.

### AC-09 · ASSUMED

- Given: a guest with basket B1 who has filled in D1 and the details of the accepted test card, and left the email address empty.
- When: they press the control that places the order.
- Then: the message "Enter an email address" is shown directly below the email field.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-01.

### AC-10 · ASSUMED

- Given: a guest with basket B1 who has filled in D1 and the details of the accepted test card, with an email address that is not valid in place of E1.
- When: they press the control that places the order.
- Then: the order is not placed.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-02.

### AC-11 · ASSUMED

- Given: a guest with basket B1 who has filled in D1 and the details of the accepted test card, with an email address that is not valid in place of E1.
- When: they press the control that places the order.
- Then: the message "Enter a valid email address" is shown directly below the email field.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-02.

### AC-12 · ASSUMED

- Given: a guest with basket B1 who has filled in D1.
- When: they pay with the declined test card.
- Then: the order is not placed.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-13 · ASSUMED

- Given: a guest with basket B1 who has filled in D1.
- When: they pay with the declined test card.
- Then: the message "Your card was declined" is shown at the top of the page they are on.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-14 · ASSUMED

- Given: a guest whose payment with the declined test card has just been refused.
- When: they open the basket.
- Then: it holds the two products of B1 in the quantities of B1.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-15 · ASSUMED

- Given: an order that a guest has placed using D1.
- When: they read the confirmation page.
- Then: it shows the sentence "A receipt has been sent to" followed by E1 as it was typed.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-04.

### AC-16 · ASSUMED

- Given: the receipt of an order that a guest has placed using D1.
- When: the tester reads it.
- Then: its body holds the order reference that the confirmation page showed.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

### AC-17 · ASSUMED

- Given: the receipt of an order that a guest has placed using D1.
- When: the tester reads it.
- Then: it names each of the two products of B1 with its quantity.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

### AC-18 · ASSUMED

- Given: the receipt of an order that a guest has placed using D1.
- When: the tester reads it.
- Then: it gives a total equal to the total the checkout showed before payment.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

## Dependencies

1. The staging test address, work item W-04. AC-08 and AC-15 to AC-18 are tested by reading the inbox of E1. That a test address may be used was agreed in the meeting. That this story waits on it is the writer's. ASSUMED.
   - The line it is read from: Dana Whitfield, Tester, in U-0005: "For testing I'd like an address that isn't anyone's real inbox. Can we use \[REDACTED:EMAIL\] for the staging receipts?"
   - The line it is read from: Priya Natarajan, Product owner, in U-0006: "That's fine."
2. A second test address, and a test account that has it, for AC-05 to AC-07. ASSUMED.
3. A way to take a card payment in test mode. The meeting said a guest can pay with a card. It did not say how. ASSUMED.
4. A way to send email from the checkout. The meeting said a guest gets an email receipt. It did not say what sends it. ASSUMED.

## Open questions that still affect it

None of these has been put to anyone. Where a criterion is marked ASSUMED, it answers one of them for the time being.
The others bear on the story with nothing standing in for an answer.

| Question | Asks | Criteria that depend on the answer | Open item it comes from |
|---|---|---|---|
| Q-01 | What does a guest see when the email address is left empty? | AC-09 | none: the meeting did not raise it |
| Q-02 | What counts as an email address the checkout accepts, and what does a guest see when theirs is not one? | AC-10, AC-11 | none: the meeting did not raise it |
| Q-03 | What happens when the card is declined: what is shown, where, and is the basket kept? | AC-12, AC-13, AC-14 | none: the meeting did not raise it |
| Q-04 | What does a guest see once the order is placed, and how is the confirmation page told from any other? | AC-01, AC-03, AC-04, AC-05, AC-07, AC-08, AC-10, AC-12, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-05 | What is in the receipt, and how is one told from any other email? | AC-08, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-06 | How soon after the order must the receipt arrive? | AC-08 | none: the meeting did not raise it |
| Q-07 | Is it accepted that the linking offer is a separate story? The product owner gave it as an acceptance criterion of this one, and undertook to find out how often it is offered (W-05). The split is the writer's. | none. It affects the story as a whole | none: the meeting did not raise it |
| Q-08 | Why does guest checkout matter to the business, and how would anyone know it had worked? | none. It affects the story as a whole | none: the meeting did not raise it |
| Q-09 | How large is this story? The size is not settled. The developer said he will size it "once that's settled", and did not name what. | none. It affects the story as a whole | O-03 |
| Q-10 | Which payment provider is used, which cards are accepted, and what are the details of its test cards? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14 | none: the meeting did not raise it |
| Q-11 | Does "not made to log in" forbid only a step the guest cannot pass, or also a link or notice inviting them to log in or to create an account? This story takes the first reading. | AC-02, AC-06 | none: the meeting did not raise it |
| Q-12 | What other fields does the checkout have, is any of them different for a guest, and what does a tester type in them? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-13 | Can a second test address and a test account be provided on staging? | AC-05, AC-06, AC-07 | none: the meeting did not raise it |
| Q-14 | How does a person who is not signed in get into the checkout: is there a choice to continue as a guest? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-15 | When a guest's email address matches an account, is anything recorded so that the linking offer can be made later? | AC-07 | none: the meeting did not raise it |
| Q-16 | What takes the card payment, and what sends the receipt? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-17 | Where can a tester see that a phone number, once given, was taken? | AC-01 | none: the meeting did not raise it |
| Q-18 | Where is the staging system, what is the test address E1, and how does a tester read its inbox? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-19 | Is the checkout one page or several, and is the email address checked when the order is placed or earlier? If earlier, a guest with no email address never reaches the control that places the order. | AC-03, AC-09, AC-10, AC-11 | none: the meeting did not raise it |
| Q-20 | Are these the writer's readings right: 10 seconds to decide an order was not placed, a field holding only spaces counting as empty, and "guest" covering a person who has an account? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | none: the meeting did not raise it |
| Q-21 | Does the account's list of orders show each order's reference, so that one order can be told from another? | AC-07 | none: the meeting did not raise it |

## Definition of done

Kept apart from the acceptance criteria. The criteria say what the product does. This says how the team would know the
work is finished. None of it is from the meeting.

- [ ] Every acceptance criterion above passes on staging.
- [ ] Every criterion marked ASSUMED, and every definition marked ASSUMED, has been confirmed by the product owner or replaced by what they said.
- [ ] The only email addresses typed into the checkout while testing were test addresses.
- [ ] No real customer's name, address, email address or card was used in any test.
- [ ] The product owner has seen the story working and accepted it.

## Source

The need comes from one meeting, `tr-2026-10-21-checkout-refinement`. The story cites 17 of its lines: U-0002, U-0003, U-0004, U-0005, U-0006, U-0007, U-0008, U-0009, U-0010, U-0011, U-0012, U-0013, U-0014, U-0019, U-0020, U-0021, U-0023.
In full, a line is cited as `tr-2026-10-21-checkout-refinement#U-0001`. Open the record and find the heading with that number.

## Lines of the meeting this story does not use

Every line of the record is cited above or listed here with the reason, so that nothing was passed over unseen.

- U-0001 · Priya Natarajan: opens the meeting.
- U-0015 · Dana Whitfield: gives a contact number for carriers about test orders. Nothing in this story uses it.
- U-0016 · Marcus Oyelaran: reads like an instruction to a tool. It is something a person said. Nothing is done with it.
- U-0017 · Dana Whitfield: a reaction to U-0016.
- U-0018 · Marcus Oyelaran: its speaker's account of U-0016.
- U-0022 · Priya Natarajan: says where to reach the person who can answer it.
- U-0024 · Priya Natarajan: closes the meeting.

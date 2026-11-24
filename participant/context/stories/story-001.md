# Story 001: Guest checkout without an account

A draft for a person to decide on. **Nothing here was created in any tracker.** The meeting it comes from is made up.

- source_record: `participant/context/transcripts/sample-meeting.md`
- transcript_id: `tr-2026-10-21-checkout-refinement`
- source_sha256: `449ff64385bd96358693d9492b6c270e37d45c4235fdce1c9863e709c8ea9882`
- work_item: W-01 of `participant/context/transcripts/sample-meeting.work-items.md`
- standard: `participant/context/stories/story-standard.md`

Written by `participant/skills/ba-write-story/story.py build`. The story was composed by an AI assistant (Claude). Every
speaker and every quotation is copied from the transcript record by the program.

**How much of this is the meeting's.** Acceptance criteria: 21. SAID by the meeting: 8. ASSUMED by the writer: 13.
Of the 8 SAID, 8 use a word whose meaning the writer had to define.

- A criterion marked **SAID** states a requirement the meeting gave, and quotes the lines. How a tester sees the result is
  usually not something the meeting gave. Where a SAID criterion leans on a word the writer defined, it says which.
- A criterion marked **ASSUMED** is the writer's proposal, put in so that the story can be tested. The meeting did not
  decide it. It stands only until the product owner confirms or replaces it.
- The meeting gave no test data beyond agreeing that a test address may be used. **Everything under "Test set-up" and
  "Taken as given" is made up by the writer**, so that each test can be run without asking anyone. The staging address,
  the pages, the fields, the cards and the email addresses do not exist.
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
   - And, on the writer's assumptions, by: AC-10, AC-11, AC-12
   - Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
   - Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
3. The checkout lets a guest give a phone number, and does not require it.
   - Tested by: AC-01, AC-04
   - And, on the writer's assumptions, by: AC-09
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
   - And, on the writer's assumptions, by: AC-13, AC-14, AC-15, AC-16
   - Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
7. A guest gets a receipt by email.
   - Tested by: AC-08
   - And, on the writer's assumptions, by: AC-17, AC-18, AC-19, AC-20, AC-21
   - Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."

## Taken as given

What the story takes as already there. **None of this was said in the meeting.** It is ASSUMED.

1. The shop already has a Basket page with a "Checkout" button, and a Checkout page that a signed-in customer uses. This story does not change either for a signed-in customer.
2. A signed-in customer has a Your orders page, which lists each of their orders by its order reference.
3. Staging has a Test tools page, as described under "Test set-up".

## Words this story defines

A criterion uses these words in these meanings and no other.

- **guest**: a person going through checkout who is not signed in, whether or not they have an account. ASSUMED: the meeting did not define it.
  - The line it is read from: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
  - The line it is read from: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- **placed**: an order is placed when, within 10 seconds of pressing "Place order", the Order confirmed page is shown with an order reference on it. ASSUMED: the meeting did not define it.
- **not placed**: an order is not placed when, 10 seconds after pressing "Place order", the Order confirmed page has not been shown. ASSUMED: the meeting did not define it.
- **order reference**: the text that follows the words "Order reference:" on the Order confirmed page. It is GT- and six digits. ASSUMED: the meeting did not define it.
- **require**: the checkout requires something when the guest cannot get to the Order confirmed page without doing it. A link, a button or a notice that the guest can pass by is not a requirement. ASSUMED: the meeting did not define it.
  - The line it is read from: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
  - The line it is read from: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
- **empty**: a field is empty when nothing has been typed in it. ASSUMED: the meeting did not define it.
- **valid**: an email address is valid when it is one or more characters that are neither a space nor @, then one @, then one or more such characters, then a dot, then one or more such characters, and nothing else. ASSUMED: the meeting did not define it.
- **receipt**: an email whose subject is the words "Your receipt for order" followed by the order reference. ASSUMED: the meeting did not define it.
- **receipt wait**: 5 minutes, counted from when the Order confirmed page is shown. ASSUMED: the meeting did not define it.
- **directly below**: a message is directly below a field when it is the next text on the page after that field, before the label of the next field. ASSUMED: the meeting did not define it.
- **at the top of the page**: a message is at the top of the page when it is the first text after the page's heading, before the first field. ASSUMED: the meeting did not define it.

## Test set-up

Everything a tester needs to run the tests, by the names the criteria use. **ASSUMED, all of it.** The meeting agreed only
that a test address may be used. To "type D1" is to put each D1 value in its field of the Checkout page.

| Name | What it is |
|---|---|
| Staging | `https://staging.shop.example.test`. Every page below is on it. |
| Test tools | The page `/test-tools`. It has a button "Empty the basket and sign out", a button "Log in as A1", and a link "Test inbox". |
| Test inbox | The page `/test-tools/inbox`. It lists every email staging has sent, newest first. For each it shows the address it was sent to, its subject and its body. |
| B1 | The basket made by this: on Test tools press "Empty the basket and sign out". Open `/products/test-mug` and press "Add to basket" twice. Open `/products/test-notebook` and press "Add to basket" once. A Test Mug is £4.00 and a Test Notebook is £6.00. Delivery on staging is free. |
| Reaching the Checkout page as a guest | With basket B1, open `/basket` and press "Checkout". A page offers two buttons, "Log in" and "Continue as guest". Press "Continue as guest". The Checkout page opens. |
| The Checkout page | One page, headed "Checkout". It shows the line "Total: £14.00" for B1. Its fields, in order: Email address, Phone number, Full name, Address line 1, Town or city, Postcode, Card number, Expiry date, Security code. Then one button, "Place order". Nothing is checked until "Place order" is pressed. |
| D1 | What a guest types: Email address `receipts@staging.example.test` (this is E1). Phone number `01632 960001` (P1). Full name `Test Guest`. Address line 1 `1 Example Street`. Town or city `Exampleton`. Postcode `EX1 1EX`. Card number, Expiry date and Security code: the accepted card. |
| E1 | `receipts@staging.example.test`, standing for the staging test address agreed in the meeting (work item W-04), which is redacted in the record. No account has it. |
| A1 and X1 | The test account A1, whose email address X1 is `account-holder@staging.example.test`. "Log in as A1" on Test tools signs the tester in as A1 with no password. |
| The accepted card | Card number `0000 0000 0000 0001`, expiry date `12/30`, security code `123`. Staging's payment test mode always accepts it. It is not a real card number. |
| The declined card | Card number `0000 0000 0000 0002`, expiry date `12/30`, security code `123`. Staging's payment test mode always declines it. |
| An email address that is not valid | `guest.example.test`. It has no @. |
| The Order confirmed page | The page headed "Order confirmed". It shows the line "Order reference:" followed by the order reference. |
| Opening Your orders as A1 | On Test tools press "Log in as A1", then open `/account/orders`. The page is headed "Your orders". |
| The Basket page | `/basket`. It shows one line for each product, as the product's name, a comma, the word "quantity" and the number. |

## Acceptance criteria

Each is one starting state, one action and one result a person can see or read.

### AC-01 · SAID

- Given: a guest who has reached the Checkout page with basket B1 and typed D1.
- When: they press "Place order".
- Then: the order is placed.
- Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed.

### AC-02 · SAID

- Given: a guest who has reached the Checkout page with basket B1 and typed D1.
- When: they press "Place order".
- Then: the checkout did not require them to create an account.
- Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- The requirement is the meeting's. These words in it are defined by the writer: guest, require.
- Note: This is seen in the same run as AC-01. It fails only if some step cannot be passed without creating an account.

### AC-03 · SAID

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with the Email address field left empty.
- When: they press "Place order".
- Then: the order is not placed.
- Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
- The requirement is the meeting's. These words in it are defined by the writer: guest, not placed, empty.

### AC-04 · SAID

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with the Phone number field left empty.
- When: they press "Place order".
- Then: the order is placed.
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, empty.

### AC-05 · SAID

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with X1 in the Email address field.
- When: they press "Place order".
- Then: the order is placed.
- Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed.

### AC-06 · SAID

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with X1 in the Email address field.
- When: they press "Place order".
- Then: the checkout did not require them to log in.
- Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
- The requirement is the meeting's. These words in it are defined by the writer: guest, require.
- Note: This is seen in the same run as AC-05. It fails only if some step cannot be passed without logging in. The "Log in" button offered on the way to the Checkout page can be passed by, so it is not a requirement. Whether such a button or notice is wanted at all is Q-11.

### AC-07 · SAID

- Given: an order that a guest has placed with D1 and with X1 in the Email address field.
- When: the tester opens Your orders as A1.
- Then: no order on that page has that order reference.
- Source: Dana Whitfield, Tester, in U-0009: "So the order is attached to the account, or it isn't until they say yes?"
- Source: Priya Natarajan, Product owner, in U-0010: "It isn't until they say yes. Good question."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, order reference.
- Note: The meeting said the order is not attached "until they say yes". This story has no step that asks, so the criterion tests that it is not attached at all. The rule comes from decision D-05, which the earlier work-items file put under W-02. Whether an order is attached is judged by whether Your orders shows it, and that way of seeing it is the writer's.

### AC-08 · SAID

- Given: an order that a guest has placed with D1.
- When: the tester opens the Test inbox once the receipt wait has passed.
- Then: the address it shows for the receipt for that order is E1.
- Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
- Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, receipt, receipt wait.
- Note: That a guest gets a receipt by email is the meeting's. The 5 minutes, and telling a receipt by its subject, are the writer's, and each is a requirement of its own: see Q-05 and Q-06. That the receipt goes to the address typed at checkout is read from the developer's reason for asking for one.

### AC-09 · ASSUMED

- Given: an order that a guest has placed with D1.
- When: they read the Order confirmed page.
- Then: it shows the line "Phone: 01632 960001".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-17.

### AC-10 · ASSUMED

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with the Email address field left empty.
- When: they press "Place order".
- Then: the message "Enter an email address" is shown directly below the Email address field.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-01.

### AC-11 · ASSUMED

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with an email address that is not valid, `guest.example.test`, in the Email address field.
- When: they press "Place order".
- Then: the order is not placed.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-02.

### AC-12 · ASSUMED

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with an email address that is not valid, `guest.example.test`, in the Email address field.
- When: they press "Place order".
- Then: the message "Enter a valid email address" is shown directly below the Email address field.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-02.

### AC-13 · ASSUMED

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with the declined card in place of the accepted card.
- When: they press "Place order".
- Then: the order is not placed.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-14 · ASSUMED

- Given: a guest who has reached the Checkout page with basket B1 and typed D1, with the declined card in place of the accepted card.
- When: they press "Place order".
- Then: the message "Your card was declined" is shown at the top of the page.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-15 · ASSUMED

- Given: a guest who has just seen the message "Your card was declined" on the Checkout page.
- When: they open the Basket page.
- Then: it shows the line "Test Mug, quantity 2".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-16 · ASSUMED

- Given: a guest who has just seen the message "Your card was declined" on the Checkout page.
- When: they open the Basket page.
- Then: it shows the line "Test Notebook, quantity 1".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-17 · ASSUMED

- Given: an order that a guest has placed with D1.
- When: they read the Order confirmed page.
- Then: it shows the line "A receipt has been sent to receipts@staging.example.test".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-04.

### AC-18 · ASSUMED

- Given: the receipt of an order that a guest has placed with D1, open in the Test inbox.
- When: the tester reads its body.
- Then: the body holds the order reference.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

### AC-19 · ASSUMED

- Given: the receipt of an order that a guest has placed with D1, open in the Test inbox.
- When: the tester reads its body.
- Then: the body holds the line "Test Mug, quantity 2".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

### AC-20 · ASSUMED

- Given: the receipt of an order that a guest has placed with D1, open in the Test inbox.
- When: the tester reads its body.
- Then: the body holds the line "Test Notebook, quantity 1".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

### AC-21 · ASSUMED

- Given: the receipt of an order that a guest has placed with D1, open in the Test inbox.
- When: the tester reads its body.
- Then: the body holds the line "Total: £14.00".
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

## Dependencies

1. The staging test address, work item W-04. That a test address may be used was agreed in the meeting. That this story waits on it is the writer's. ASSUMED.
   - The line it is read from: Dana Whitfield, Tester, in U-0005: "For testing I'd like an address that isn't anyone's real inbox. Can we use \[REDACTED:EMAIL\] for the staging receipts?"
   - The line it is read from: Priya Natarajan, Product owner, in U-0006: "That's fine."
2. A staging system with the Test tools page, the two test products, the test account A1 and a payment test mode, as "Test set-up" describes them. ASSUMED.
3. A way to send email from the checkout. The meeting said a guest gets an email receipt. It did not say what sends it. ASSUMED.

## Open questions that still affect it

None of these has been put to anyone.

**Answered for now by an assumption in this story.** A tester does not need to ask any of these to write or run a
test: the story supplies an answer, marked ASSUMED. Each answer still has to be confirmed.

| Question | Asks | Criteria that use the assumed answer | Open item it comes from |
|---|---|---|---|
| Q-01 | What does a guest see when the email address is left empty? | AC-10 | none: the meeting did not raise it |
| Q-02 | What counts as an email address the checkout accepts, and what does a guest see when theirs is not one? | AC-11, AC-12 | none: the meeting did not raise it |
| Q-03 | What happens when the card is declined: what is shown, where, and is the basket kept? | AC-13, AC-14, AC-15, AC-16 | none: the meeting did not raise it |
| Q-04 | What does a guest see once the order is placed? | AC-01, AC-03, AC-04, AC-05, AC-07, AC-08, AC-09, AC-11, AC-13, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-05 | What is in the receipt, and how is one told from any other email? | AC-08, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-06 | How soon after the order must the receipt arrive? | AC-08 | none: the meeting did not raise it |
| Q-10 | Which payment provider is used, and what are its test cards? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-11 | Does "not made to log in" forbid only a step the guest cannot pass, or also a button or notice inviting them to log in or to create an account? This story takes the first reading. | AC-02, AC-06 | none: the meeting did not raise it |
| Q-12 | What fields does the checkout have, and what does a tester type in them? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-13 | Is there a test account on staging whose email address a tester can use? | AC-05, AC-06, AC-07 | none: the meeting did not raise it |
| Q-14 | How does a person who is not signed in get into the checkout? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-17 | Where can a tester see that a phone number, once given, was taken? | AC-09 | none: the meeting did not raise it |
| Q-18 | Where is the staging system, and how does a tester read the email it sends? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-19 | Is the checkout one page or several, and when is the email address checked? | AC-03, AC-10, AC-11, AC-12 | none: the meeting did not raise it |
| Q-20 | Are these readings right: 10 seconds to decide an order was not placed, and "guest" covering a person who has an account? | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21 | none: the meeting did not raise it |
| Q-21 | Does Your orders show each order's reference? | AC-07 | none: the meeting did not raise it |

**Not answered here.** None of these stops a test from being written or run. They bear on whether this is the right
story.

| Question | Asks | Criteria that depend on the answer | Open item it comes from |
|---|---|---|---|
| Q-07 | Is it accepted that the linking offer is a separate story? The product owner gave it as an acceptance criterion of this one, and undertook to find out how often it is offered (W-05). The split is the writer's. | none. It affects the story as a whole | none: the meeting did not raise it |
| Q-08 | Why does guest checkout matter to the business, and how would anyone know it had worked? | none. It affects the story as a whole | none: the meeting did not raise it |
| Q-09 | How large is this story? The size is not settled. The developer said he will size it "once that's settled", and did not name what. | none. It affects the story as a whole | O-03 |
| Q-15 | When a guest's email address matches an account, is anything recorded so that the linking offer can be made later? | none. It affects the story as a whole | none: the meeting did not raise it |

## Definition of done

Kept apart from the acceptance criteria. The criteria say what the product does. This says how the team would know the
work is finished. None of it is from the meeting.

- [ ] Every acceptance criterion above passes on staging.
- [ ] Every criterion marked ASSUMED, every definition marked ASSUMED and every line of the test set-up has been confirmed by the product owner or replaced by what they said.
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

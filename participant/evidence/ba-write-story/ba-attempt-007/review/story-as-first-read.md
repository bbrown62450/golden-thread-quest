# Story 001: Guest checkout without an account

A draft for a person to decide on. **Nothing here was created in any tracker.** The meeting it comes from is made up.

- source_record: `participant/context/transcripts/sample-meeting.md`
- transcript_id: `tr-2026-10-21-checkout-refinement`
- source_sha256: `449ff64385bd96358693d9492b6c270e37d45c4235fdce1c9863e709c8ea9882`
- work_item: W-01 of `participant/context/transcripts/sample-meeting.work-items.md`
- standard: `participant/context/stories/story-standard.md`

Written by `participant/skills/ba-write-story/story.py build`. The story was composed by an AI assistant (Claude). Every
speaker and every quotation is copied from the transcript record by the program.

**How much of this is the meeting's.** Acceptance criteria: 12. SAID by the meeting: 6. ASSUMED by the writer: 6.
A criterion marked SAID quotes the lines it rests on. A criterion marked ASSUMED is the writer's proposal, put in so that
the story can be tested. It is not something the meeting decided, and it stands only until the product owner confirms or replaces it.

## The story

- User: A customer who does not have an account.
- Source for the user: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- Value: They can buy without making one.
- Source for the value: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
- Not said: The meeting said what the customer gains. It did not say why that matters to the business, or how anyone would know it had worked. That is open question Q-08.

## Out of scope

Written first, before any criterion. Each says why it is out and where it went.

1. **The offer to link a guest's order to an account they already have.**
   - Why it is out: It is a separate work item, and two parts of it are not settled: whether the offer times out, and whether it is made once per order or once ever. The meeting named it in the same breath as this story. It is taken out so that this story can be built and tested while those are open.
   - Where it went: W-02, O-01, O-02
   - The line it turns on: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
   - The line it turns on: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
2. **Any time-out on that offer.**
   - Why it is out: It was asked about and parked. Nobody said one should be built.
   - Where it went: R-01, O-01
   - The line it turns on: Unattributed, identity uncertain, in U-0011: "Should it time out? If they never answer the link offer?"
   - The line it turns on: Marcus Oyelaran, Developer, in U-0012: "Let's park that. I don't know the answer and I'd rather not guess."
3. **What is done with the phone number: printing it on the shipping label, and keeping it out of marketing.**
   - Why it is out: It is a separate work item, about the label and not about the checkout. This story only takes the number when the guest gives one.
   - Where it went: W-03
   - The line it turns on: Priya Natarajan, Product owner, in U-0014: "Shipping label only, for the carrier. We don't market to it."
4. **Sending staging receipts to a test address.**
   - Why it is out: It is test set-up, and a separate work item. This story depends on it and does not include it.
   - Where it went: W-04
   - The line it turns on: Dana Whitfield, Tester, in U-0005: "For testing I'd like an address that isn't anyone's real inbox. Can we use \[REDACTED:EMAIL\] for the staging receipts?"
   - The line it turns on: Priya Natarajan, Product owner, in U-0006: "That's fine."
5. **Any way of paying other than a card.**
   - Why it is out: The meeting named a card and nothing else. No other way of paying was discussed, so none is built.
   - Where it went: nowhere. The meeting did not discuss it
   - The line it turns on: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
6. **Creating an account from the checkout, or being invited to.**
   - Why it is out: The meeting's point was buying without making one. Nothing was said about offering one.
   - Where it went: nowhere. The meeting did not discuss it
   - The line it turns on: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
7. **Checkout for a customer who is signed in.**
   - Why it is out: The story is for customers who do not have an account. Nothing was said about changing checkout for those who do.
   - Where it went: nowhere. The meeting did not discuss it
   - The line it turns on: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
8. **The size of the work.**
   - Why it is out: It is not settled. The developer gave a rough guess and said he has yet to size it.
   - Where it went: O-03, W-06
   - The line it turns on: Marcus Oyelaran, Developer, in U-0023: "I'll size it once that's settled. Rough guess is a five, maybe an eight with the linking."

## In scope

1. A customer with no account can go through checkout and place an order.
   - Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
2. The checkout asks a guest for an email address and requires it.
   - Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
   - Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
3. The checkout lets a guest give a phone number, and does not require it.
   - Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."
4. A guest whose email address already has an account is not made to log in.
   - Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
   - Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."
5. A guest pays with a card.
   - Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."
6. A guest gets a receipt by email.
   - Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."

## Words this story defines

A criterion uses these words in these meanings and no other.

- **guest**: a customer who is not signed in and is checking out without an account. SAID.
  - Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."
  - Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- **placed**: an order is placed when the confirmation page is shown with an order reference. ASSUMED: the meeting did not define it.
- **valid**: an email address is valid when it has exactly one @, at least one character before it, and after it at least one dot with characters on both sides. ASSUMED: the meeting did not define it.
- **test card**: a card number that the payment provider's test mode accepts or declines on purpose. ASSUMED: the meeting did not define it.

## Acceptance criteria

Each is one starting state, one action and one result a person can see or read.

### AC-01 · SAID

- Given: a guest with one item in the basket.
- When: they go through checkout to the end, giving an email address and paying with a test card that is accepted.
- Then: the order is placed, and no step asked them to create an account or to sign in.
- Source: Priya Natarajan, Product owner, in U-0002: "First item is guest checkout. Customers who don't have an account should be able to buy without making one."

### AC-02 · SAID

- Given: a guest at checkout who has left the email address empty.
- When: they try to place the order.
- Then: the order is not placed.
- Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."

### AC-03 · SAID

- Given: a guest at checkout who has given an email address and left the phone number empty.
- When: they place the order, paying with a test card that is accepted.
- Then: the order is placed.
- Source: Priya Natarajan, Product owner, in U-0004: "Yes, email is required. Phone is optional."

### AC-04 · SAID

- Given: a guest at checkout who gives an email address that already belongs to an account.
- When: they place the order, paying with a test card that is accepted.
- Then: the order is placed, and no step asked them to log in.
- Source: Marcus Oyelaran, Developer, in U-0007: "What happens if a guest uses an email that already has an account? Do we make them log in?"
- Source: Priya Natarajan, Product owner, in U-0008: "No. We let them check out, and then we offer to link the order after."

### AC-05 · SAID

- Given: a guest at the payment step.
- When: they pay with a test card that is accepted.
- Then: the order is placed.
- Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."

### AC-06 · SAID

- Given: a guest who has placed an order giving the email address E.
- When: the order is placed.
- Then: a receipt is sent by email to E.
- Source: Marcus Oyelaran, Developer, in U-0003: "Do we still need their email? We have to send the receipt somewhere."
- Source: Priya Natarajan, Product owner, in U-0019: "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed."

### AC-07 · ASSUMED

- Given: a guest at checkout who has left the email address empty.
- When: they try to place the order.
- Then: the message "Enter an email address" is shown beside the email field.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-01.

### AC-08 · ASSUMED

- Given: a guest at checkout who has typed an email address that is not valid.
- When: they try to place the order.
- Then: the order is not placed, and the message "Enter a valid email address" is shown beside the email field.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-02.

### AC-09 · ASSUMED

- Given: a guest at the payment step.
- When: they pay with a test card that is declined.
- Then: the order is not placed, the message "Your card was declined" is shown, and the basket still holds the same items.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-03.

### AC-10 · ASSUMED

- Given: a guest who has placed an order giving the email address E.
- When: the confirmation page is shown.
- Then: it shows an order reference and the sentence "A receipt has been sent to E", with E written out.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-04.

### AC-11 · ASSUMED

- Given: a guest who has placed an order.
- When: the receipt email arrives.
- Then: it holds the order reference, each item with its quantity and price, and the total charged.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-05.

### AC-12 · ASSUMED

- Given: a guest who has placed an order giving the email address E.
- When: 5 minutes have passed since the order was placed.
- Then: the receipt email has arrived at E.
- ASSUMPTION, to be confirmed by: the product owner.
- Answers the open question: Q-06.

## Dependencies

1. The staging receipts address, work item W-04. Criteria AC-06, AC-11 and AC-12 cannot be tested on staging until receipts go to a test inbox. SAID.
   - Source: Dana Whitfield, Tester, in U-0005: "For testing I'd like an address that isn't anyone's real inbox. Can we use \[REDACTED:EMAIL\] for the staging receipts?"
   - Source: Priya Natarajan, Product owner, in U-0006: "That's fine."
2. A way to take a card payment in test mode, with test cards that are accepted and declined. The meeting said a guest pays with a card. It did not say how. ASSUMED.
3. A way to send email from the checkout. The meeting said a guest gets an email receipt. It did not say what sends it. ASSUMED.

## Open questions that still affect it

Each assumption above answers one of these for the time being. None has been put to anyone.

| Question | Asks | Criteria that depend on the answer | Open item it comes from |
|---|---|---|---|
| Q-01 | What does a guest see when the email address is left empty? | AC-07 | none: the meeting did not raise it |
| Q-02 | What counts as an email address the checkout accepts, and what does a guest see when theirs is not one? | AC-08 | none: the meeting did not raise it |
| Q-03 | What happens when the card is declined: what is shown, and is the basket kept? | AC-09 | none: the meeting did not raise it |
| Q-04 | What does a guest see once the order is placed? | AC-10 | none: the meeting did not raise it |
| Q-05 | What is in the receipt? | AC-11 | none: the meeting did not raise it |
| Q-06 | How soon after the order must the receipt arrive? | AC-12 | none: the meeting did not raise it |
| Q-07 | Is it accepted that the linking offer is a separate story? The meeting gave both in one set of acceptance criteria. | none. It affects the story as a whole | O-02 |
| Q-08 | Why does guest checkout matter to the business, and how would anyone know it had worked? | none. It affects the story as a whole | none: the meeting did not raise it |
| Q-09 | How large is this story? The size is not settled. | none. It affects the story as a whole | O-03 |
| Q-10 | Which cards are accepted? | AC-05 | none: the meeting did not raise it |

## Definition of done

Kept apart from the acceptance criteria. The criteria say what the product does. This says how the team would know the
work is finished. None of it is from the meeting.

- [ ] Every acceptance criterion above passes on staging.
- [ ] Every criterion marked ASSUMED has been confirmed by the product owner, or replaced by what they said.
- [ ] Every receipt sent while testing went to the staging test address, and to no real inbox.
- [ ] No real customer's name, address, email address or card was used in any test.
- [ ] The product owner has seen the story working and accepted it.

## Source

The need comes from one meeting, `tr-2026-10-21-checkout-refinement`. The story cites 12 of its lines: U-0002, U-0003, U-0004, U-0005, U-0006, U-0007, U-0008, U-0011, U-0012, U-0014, U-0019, U-0023.
In full, a line is cited as `tr-2026-10-21-checkout-refinement#U-0001`. Open the record and find the heading with that number.

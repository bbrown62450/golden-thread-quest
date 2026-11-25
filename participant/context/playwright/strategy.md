# Test strategy: the checkout of the made-up shop

**Made up.** The shop and every rule in it are invented. The requirements are in
`participant/context/playwright/requirements.md`.

**This is a plan. No test in it has been written, and 10 of the 15 it plans cannot be written until more of the shop is
built.** It says which risks are to be
tested, at which layer, and why, and which are left untested. Each risk says what must exist before its test can be
written. It touches no application.

It is checked by `participant/tests/playwright/tools/risk-strategy-check.ts`, which reads this file and the
requirements. The check can tell that a reason is there. It cannot tell that a reason is good.

## 1. The scales, the ranking and the layers

Each risk names the clause it rests on, for its likelihood and for its impact. **Where clauses of two levels both
apply, the higher level is taken**, on both scales.

### Likelihood: how likely it is to break

| Level | Clause | When |
|---|---|---|
| 1 | L1a | The rule has one case, and the code that carries it is a few lines that rarely change |
| 1 | L1b | It breaks only if something outside the shop's code changes, and that rarely happens |
| 2 | L2a | The rule has more than one case or an edge: several lines, a quantity above one, a sign |
| 2 | L2b | The code that carries it is a page: its layout, its wording or its controls, which change when the page is redesigned |
| 2 | L2c | Two parts must agree for it to hold: the page and the server, or one request and the next |
| 3 | L3a | It has gone wrong in this shop before. A fault put in on purpose to try a test does not count |
| 3 | L3b | The rule turns on the order of two steps, on rounding, or on the day a period ends |
| 3 | L3c | The code for at least one case the risk names is not written yet, or the thing it depends on does not exist yet |

### Impact: what it costs when it breaks

| Level | Clause | When |
|---|---|---|
| 1 | I1a | An annoyance. Every customer can still complete the order, and the money is right |
| 2 | I2a | Some customers cannot complete the order, or a customer is told something untrue that changes no money |
| 2 | I2b | An amount is wrong by a penny or two on some orders |
| 3 | I3a | By more than a penny or two on an order: the money is wrong, the tax is wrong, or the amount taken is not the amount the customer was shown |
| 3 | I3b | An order is lost or made twice, or no customer can place one |

### Ranking

**Score = likelihood × impact.** The risks are ranked by score, highest first.

**Equal scores are ordered by impact, highest first; then by the importance of the risk's most important requirement, must before should before could; then by risk number, lowest first.**

Importance comes from the requirements file. It does not change a score. It only orders risks that the score and the
impact leave level.

### Layers

| Layer | What it is | Needs a browser |
|---|---|---|
| unit | A function is called directly. No server and no browser | no |
| API | A request is sent to the running server and the answer is read. No browser | no |
| UI | Playwright drives the page in a browser | yes |
| manual | A person follows a written checklist, in a browser | yes |
| none | Not tested. The risk is accepted, and is in section 5 | no |

**The rule for choosing: the lowest layer at which the thing that could break can be seen.** A sum can be seen in the
function that makes it. Whether two answers agree can be seen only at the server. What a press does, and what fits on a
narrow screen, can be seen only in a browser. Whether something read aloud makes sense can be judged only by a person.
The higher layers are slower and fail for more reasons, so nothing is put higher than it has to be. One exception is
made, and its block says why: R-09.

**The demo is not yet built for the lower layers.** Its sums are inside the file that starts the server, take no
basket and are not exported. Section 3 says, for each risk, what must be built first.

## 2. The risks, ranked

| Rank | Risk | Requirement | Likelihood | Impact | Score | Layer |
|---|---|---|---|---|---|---|
| 1 | R-02 | REQ-02 | 3 | 3 | 9 | unit |
| 2 | R-03 | REQ-03 | 3 | 3 | 9 | unit |
| 3 | R-08 | REQ-08 | 3 | 3 | 9 | API |
| 4 | R-16 | REQ-02, REQ-07 | 3 | 3 | 9 | unit |
| 5 | R-19 | REQ-04, REQ-08 | 3 | 3 | 9 | none |
| 6 | R-07 | REQ-07 | 3 | 3 | 9 | unit |
| 7 | R-17 | REQ-07 | 3 | 3 | 9 | API |
| 8 | R-01 | REQ-01 | 2 | 3 | 6 | unit |
| 9 | R-04 | REQ-04 | 2 | 3 | 6 | unit |
| 10 | R-06 | REQ-04, REQ-06 | 2 | 3 | 6 | API |
| 11 | R-09 | REQ-04, REQ-10 | 2 | 3 | 6 | UI |
| 12 | R-10 | REQ-06 | 2 | 3 | 6 | UI |
| 13 | R-05 | REQ-05 | 3 | 2 | 6 | unit |
| 14 | R-11 | REQ-09 | 2 | 2 | 4 | none |
| 15 | R-12 | REQ-10 | 2 | 2 | 4 | unit |
| 16 | R-18 | REQ-09 | 2 | 2 | 4 | UI |
| 17 | R-14 | REQ-12 | 2 | 2 | 4 | UI |
| 18 | R-15 | REQ-03 | 1 | 3 | 3 | none |
| 19 | R-13 | REQ-11 | 2 | 1 | 2 | none |

Fifteen of the 19 risks are level with at least one other in score, impact and importance. Within such a group only
the risk number orders them, and that order means nothing. The groups are R-02, R-03, R-08, R-16 and R-19; R-07 and
R-17; R-01, R-04, R-06, R-09 and R-10; and R-11, R-12 and R-18.

## 3. Each risk, with the reason for its layer

### R-01. The subtotal is wrong when a line has a quantity above one, or there are several lines

- Requirement: REQ-01
- Likelihood: 2 (L2a). The sum has cases: one line, several lines, a quantity above one.
- Impact: 3 (I3a). Every other amount is worked out from the subtotal, so the money is wrong by more than pence.
- Score: 6
- Layer: unit
- Needs a browser: no
- Needs first: the sums moved out of the server's file into a function that takes a basket and a code, and can be imported without starting the server.
- Cheapest test that would fail: call that function with a basket of one line, of two lines, and of a line with a quantity of 2, and compare each subtotal with a figure worked out by hand.
- Reason for the layer: the subtotal is a sum inside one function. Nothing about a page or a request can make that sum right or wrong, so a browser would only add time and other ways to fail. At this layer three baskets cost milliseconds.

### R-02. The discount is taken off the wrong amount, or is shown and not taken off

- Requirement: REQ-02
- Likelihood: 3 (L3c). The cases with no code, and with a code of another percentage, are not written: the demo has one fixed code.
- Impact: 3 (I3a). The customer pays too much, or the shop takes too little, by a tenth of the order.
- Score: 9
- Layer: unit
- Needs a browser: no
- Needs first: the same function as R-01, taking any code or none, and giving back the goods after discount as one of its figures.
- Cheapest test that would fail: call the function with a 10% code, with a 25% code and with no code, and compare the goods after discount with figures worked out by hand.
- Reason for the layer: taking a percentage off is arithmetic in the same function as the subtotal, and the page only prints the result. Testing it through the page would test the printing as well, which R-09 already does once.

### R-03. Tax is worked out on the subtotal before the discount, and not on what the customer pays

- Requirement: REQ-03
- Likelihood: 3 (L3a). It has happened here: a redesign of the demo did exactly this, and the owner ruled it a bug. L3b applies too: it is an order of two steps.
- Impact: 3 (I3a). Tax is wrongly charged on every discounted order.
- Score: 9
- Layer: unit
- Needs a browser: no
- Needs first: the same function as R-01.
- Cheapest test that would fail: call the function with a discounted basket and compare the tax with 20% of the goods after discount, worked out by hand. A second case with no discount, where both readings of the rule give the same tax, shows the test is of the order of the steps.
- Reason for the layer: the rule is one line of arithmetic, and the fault is which of two numbers that line uses. Earlier work in this repository caught it through the page, which took a browser and a running server to test one multiplication. A direct call can also fail if the subtotal or the discount is wrong, and R-01 and R-02 would show that first.

### R-04. The total leaves out the tax, or leaves out the discount

- Requirement: REQ-04
- Likelihood: 2 (L2a). The total joins three figures, with a discount and without one.
- Impact: 3 (I3a). The total is the amount taken.
- Score: 6
- Layer: unit
- Needs a browser: no
- Needs first: the same function as R-01.
- Cheapest test that would fail: call the function and compare the total with goods after discount plus tax, each worked out by hand, for a basket with a discount and one without.
- Reason for the layer: the total is an addition in the same function. Whether the server then records that total on the order is a different risk, R-06, and is tested where it can be seen. Keeping the two apart means a failure says which of them broke.

### R-05. An amount is a penny out because of rounding

- Requirement: REQ-05
- Likelihood: 3 (L3c). The rule is not built: the demo's sums are not rounded at all, and its formatting does not round a half up in every case. L3b applies too.
- Impact: 2 (I2b). A penny or two, on the orders whose amounts have part pence.
- Score: 6
- Layer: unit
- Needs a browser: no
- Needs first: the rounding rule built, in the function of R-01, and the owner's ruling on three points the requirement leaves open: whether a half rounds up for the negative discount, which amounts count as the end, and whether the amounts shown must add up to the total shown.
- Cheapest test that would fail: call the function with prices chosen so that the discount and the tax have part pence, some landing on exactly half a penny, and compare each amount with one worked out by hand by someone other than the person who wrote the function.
- Reason for the layer: the fault shows only for particular prices, so it takes several chosen baskets to find. The demo page has no way to enter a basket at all, so no higher layer could try them, and rounding is arithmetic that can be seen in the function that does it.

### R-06. The total on the order is not the total the customer was shown

- Requirement: REQ-04, REQ-06
- Likelihood: 2 (L2c). The checkout page and the order must agree, and they come from two requests.
- Impact: 3 (I3a). The amount on the order is not the amount the customer was shown.
- Score: 6
- Layer: API
- Needs a browser: no
- Needs first: nothing for the demo as it is, where both pages can be fetched and read as text. Once the server keeps orders, the server of R-08.
- Cheapest test that would fail: with a code applied, fetch the checkout page and read its total, place the order with a request, and compare the total on the confirmation with the first.
- Reason for the layer: the risk is that two answers from the server disagree. That cannot be seen inside one function, so unit is too low, and it can be seen by reading the two answers, so no browser is needed. It tests the figure printed on the confirmation and not a payment, which is R-19. The demo keeps no order, so today that figure is worked out again for the confirmation.

### R-07. A code that is unknown, or past its end date, is treated as valid

- Requirement: REQ-07
- Likelihood: 3 (L3c). The demo has one fixed code and no end dates: none of this is written. L3b applies too: it turns on the day a period ends.
- Impact: 3 (I3a). The shop takes a tenth less than it is owed on every such order.
- Score: 9
- Layer: unit
- Needs a browser: no
- Needs first: a function that takes a code, the list of codes and a date, and says whether the code is valid. The owner's ruling on whether a code is valid on its end date.
- Cheapest test that would fail: call that function with an unknown code, and with a known code on the day before its end date, on the end date and on the day after, and compare each answer with the owner's ruling.
- Reason for the layer: whether a code is valid on a given day is a decision from three inputs, so it can be seen in a function. Passing the date in means no clock has to be changed. What the server then does with a refusal is R-17, at the layer where that can be seen.

### R-08. A second press, or a resent request, makes a second order

- Requirement: REQ-08
- Likelihood: 3 (L3c). The demo keeps no orders and gives every order the same reference: none of this is written. L2c applies too.
- Impact: 3 (I3b). An order is made twice.
- Score: 9
- Layer: API
- Needs a browser: no
- Needs first: a server that keeps orders, a way to ask it how many it holds, a ruling on what makes two orders different when the basket is the same, and a decision on how it recognises a repeat. If that is by a key the page sends, one step is added to R-10's journey to check that the page sends it.
- Cheapest test that would fail: send the same order request twice, one after the other, and then twice at the same moment, several times over, and check each time that the server holds one order. Then send two different orders and check that it holds two.
- Reason for the layer: the server is what must refuse the repeat, because a resent request never passes through the button. A test that presses the button twice in a browser shows only that the page guards against it. Two requests at the same moment cannot be made reliably from a page at all.

### R-09. The page shows a figure other than the one worked out, or shows it against the wrong label

- Requirement: REQ-04, REQ-10
- Likelihood: 2 (L2b). The summary was changed once already, from a table to a list.
- Impact: 3 (I3a). If the total shown is wrong, the amount taken is not the amount the customer was shown.
- Score: 6
- Layer: UI
- Needs a browser: yes
- Needs first: nothing.
- Cheapest test that would fail: one Playwright test that opens the checkout and reads every amount on it, each found from the text of its own label and not by a test identifier, and compares the exact text of each with the figure for the known basket: sign, two decimals, and the discount negative.
- Reason for the layer: which figure a customer sees beside which label is the page as a browser lays it out. Today the page has no script, so the same pairing could be read from the server's answer without a browser, and this is the first test to move down if run time mattered. A browser is chosen all the same, because that stops being true the day the page gains a script. This is the one risk put higher than the rule of section 1 requires.

### R-10. Pressing the button does not place the order, or no confirmation is shown

- Requirement: REQ-06
- Likelihood: 2 (L2b). The button was renamed in the last redesign.
- Impact: 3 (I3b). No customer can place an order, or a customer believes they have and no order exists.
- Score: 6
- Layer: UI
- Needs a browser: yes
- Needs first: nothing for the press and the confirmation. To check that an order then exists, the server of R-08.
- Cheapest test that would fail: one Playwright test that presses the button, found by its role and name, and checks that the confirmation shows a reference and the exact total for the known basket.
- Reason for the layer: that a press on the visible button reaches the server can be seen only in a browser. An API test would send the request itself and pass with a dead button. It is one journey and not one for each rule, because the rules are tested lower down.

### R-11. What a screen reader reads at the checkout does not make sense

- Requirement: REQ-09
- Likelihood: 2 (L2b). Names and labels are lost when a page's markup is rearranged.
- Impact: 2 (I2a). Some customers cannot complete the order.
- Score: 4
- Layer: none
- Needs a browser: no
- Needs first: a named person, a named screen reader and browser, and the checklist written out. None of the three exists. Nobody has done this check.
- Cheapest test that would fail: before each release a person completes the order with a screen reader and notes, for the basket, each amount, the button and the confirmation, whether what is read aloud names the thing and gives its value in an order that makes sense.
- Reason for the layer: whether what is read aloud makes sense is a judgement, and only a person can make it, so its layer would be manual. It is given no layer because calling it manual would be a label and not a test: there is no person, no screen reader and no checklist. The keyboard is R-18. That each amount is tied to its label in the page's markup is a fact a tool could check, and no test here checks it. It is in section 5.

### R-12. An amount is formatted wrongly: no sign, not two decimals, or a negative amount shown wrongly

- Requirement: REQ-10
- Likelihood: 2 (L2a). There are cases: whole pounds, pence, zero and a negative amount. The format was changed once, when the sign was added.
- Impact: 2 (I2a). A discount shown as a positive amount tells the customer something untrue. The money is right.
- Score: 4
- Layer: unit
- Needs a browser: no
- Needs first: the formatting function moved with the sums into the module of R-01. Exporting it where it is would not do, because loading that file starts the server.
- Cheapest test that would fail: call the formatting function with a whole number of pounds, an amount with pence, zero and a negative amount, and compare the text.
- Reason for the layer: the format is made by one function, so the test is four calls. That the discount is passed to it as a negative amount is decided in the page, and R-09 is what fails for that. Four calls cost nearly nothing here.

### R-13. The checkout page takes longer than 2 seconds to show

- Requirement: REQ-11
- Likelihood: 2 (L2b). It depends on what the page carries, which changes when the page is redesigned. Today it is one small document with no script and no picture.
- Impact: 1 (I1a). A wait. The order and the money are right.
- Score: 2
- Layer: none
- Needs a browser: no
- Needs first: the owner to say what the reference connection is. Until then there is nothing to measure against.
- Cheapest test that would fail: a timed load over the reference connection, repeated enough times to tell a slow page from a slow moment.
- Reason for the layer: the requirement names a reference connection that the made-up shop has not defined. A timing on a developer's computer says nothing about a customer's connection. It is in section 5.

### R-14. The checkout cannot be read or used on a screen 320 pixels wide

- Requirement: REQ-12
- Likelihood: 2 (L2b). It depends on the page's layout.
- Impact: 2 (I2a). At worst a customer on a small phone cannot reach the button. At best they must scroll sideways, which would be I1a, and the higher is taken.
- Score: 4
- Layer: UI
- Needs a browser: yes
- Needs first: nothing.
- Cheapest test that would fail: R-10's journey run once more in a browser window set to 320 pixels wide, with one more check: the page is no wider than the window.
- Reason for the layer: the requirement's own test is whether the page scrolls sideways, which is one measurement, and Playwright's press fails if the button is covered by something else. So a browser can see both, and no person is needed. Text that is cut off or laid over other text makes no sideways scroll and no failed press, so "can be read" is only partly tested. Section 5 says so.

### R-15. The rate of tax changes in law, and the shop still charges 20%

- Requirement: REQ-03
- Likelihood: 1 (L1b). It depends on a change outside the shop, which is rare.
- Impact: 3 (I3a). Tax is wrongly charged on every order from that day.
- Score: 3
- Layer: none
- Needs a browser: no
- Needs first: nothing can be built that would make this testable.
- Cheapest test that would fail: there is none. A test compares the shop with the requirement, and the requirement says 20%. If the law changes, the requirement is what is wrong, and every test still passes.
- Reason for the layer: no layer can catch a rule that has stopped being true outside the shop. Writing a test would give a false sense that it is watched. What watches it is a person who owns the rule. It is in section 5.

### R-16. A valid code is refused

- Requirement: REQ-02, REQ-07
- Likelihood: 3 (L3c). Deciding whether a code is valid is not written. L3b applies too: the last day of a code's life is the likely place.
- Impact: 3 (I3a). The customer pays a tenth more than REQ-02 allows. They see the higher total before they pay, and the money is still wrong.
- Score: 9
- Layer: unit
- Needs a browser: no
- Needs first: the function of R-07, and the owner's rulings on whether a code is valid on its end date and whether it may be typed in small letters.
- Cheapest test that would fail: call the function of R-07 with a known code, as issued, well inside its period, and check that it is accepted whatever the rulings. Then with the code on its end date, and typed in small letters, and compare each answer with the owner's ruling.
- Reason for the layer: it is the other side of the decision in R-07, made by the same function from the same three inputs. It is kept as its own risk because a test that only checks that bad codes are refused passes for a function that refuses every code.

### R-17. A refused code still changes an amount, or the customer is not told

- Requirement: REQ-07
- Likelihood: 3 (L3c). The demo has nowhere to enter a code, so refusing one is not written.
- Impact: 3 (I3a). If a refused code still takes the discount off, the shop takes less than it is owed.
- Score: 9
- Layer: API
- Needs a browser: no
- Needs first: a checkout request that can carry a code or none, and a way to give the server the date. For the message to be seen on the page, a box on the page to type the code in. When that exists, one step joins R-10's journey.
- Cheapest test that would fail: send the checkout request with an unknown code, and again with a known code past its end date, and check each time that the answer says the code was refused and that every amount is what it is with no code.
- Reason for the layer: that a refusal leaves the amounts alone is about what the server answers, after the decision of R-07 is made. It cannot be seen in the function that decides. If the sums function is given the code, part of it could move down to unit, and that the server passes the right date could not. It can be read in the answer without a browser. That the message is visible on the page is not tested until the page has the box.

### R-18. The checkout cannot be completed with the keyboard alone

- Requirement: REQ-09
- Likelihood: 2 (L2b). A control that can be reached by keyboard is easily replaced by one that cannot when a page is redesigned.
- Impact: 2 (I2a). Some customers cannot complete the order.
- Score: 4
- Layer: UI
- Needs a browser: yes
- Needs first: nothing.
- Cheapest test that would fail: one Playwright test that uses only the keyboard: it moves to the button with the tab key, presses the enter key, and checks that the confirmation is shown.
- Reason for the layer: whether the tab key reaches the button and the enter key presses it is a fact about the page in a browser, and needs no judgement. It was first planned as part of a person's check, which would have made a person repeat, each release, something a browser can do.

### R-19. The money a payment provider takes is not the total, or is taken twice

- Requirement: REQ-04, REQ-08
- Likelihood: 3 (L3c). The thing it depends on does not exist: the shop has no payment provider. L2c would apply too, since the shop and a provider would have to agree.
- Impact: 3 (I3a). The amount taken is not the amount the customer was shown.
- Score: 9
- Layer: none
- Needs a browser: no
- Needs first: a payment provider. The made-up shop has none: it takes no money, and "charged" can only mean the total recorded on the order.
- Cheapest test that would fail: once there is a provider with a test mode, place an order through it and compare the amount it reports with the order's total, and resend the request and check it reports one payment.
- Reason for the layer: there is nothing to send a request to. R-06 and R-08 test that the shop's own record is right, and stop there. It has the highest score of the risks left untested, and it must be ranked again before the shop takes real money. It is in section 5.

## 4. Which risks need a browser

**Need a browser (4):** R-09, R-10, R-14, R-18.

**Do not need a browser (15):** R-01, R-02, R-03, R-04, R-05, R-06, R-07, R-08, R-11, R-12, R-13, R-15, R-16, R-17, R-19.

Of the 15 risks that are to be tested, 11 are to be tested without a browser.

R-09 is the one in the first group that could be moved to the second today. R-08 and R-17 each have one step that
would need a browser once the page changes, and each block says which.

The four untested risks, R-11, R-13, R-15 and R-19, are in the second group only because nothing is run for them. A
test of R-11 or of R-13 would need a browser.

Of the 15 tests planned, 5 can be written against the demo as it is: R-06, R-09, R-10, R-14 and R-18. Four of those
five need a browser. The other 10 wait on something that is not built, which each block names under "Needs first".

## 5. What is deliberately left untested

Who can accept a risk: the participant, as product owner of the demo shop.

| Risk | Requirement | Score | Why it is not tested | What is done instead | Accepted by | On |
|---|---|---|---|---|---|---|
| R-13 | REQ-11 | 2 | The reference connection is not defined, so a timing test has nothing to measure against, and a timing on a developer's computer says nothing about a customer's | Nothing. If the page gains scripts or pictures, the risk is ranked again | the participant, as product owner of the demo shop | 2026-11-25 |
| R-15 | REQ-03 | 3 | No test can fail when the law changes: a test compares the shop with the requirement, and it is the requirement that would be wrong | The owner of the tax rule checks the rate before each release. No record of that check is kept, which is a weakness | the participant, as product owner of the demo shop | 2026-11-25 |
| R-11 | REQ-09 | 4 | A person must judge what is read aloud, and there is no named person, no named screen reader and no written checklist. Calling it manual would be a label and not a test | The keyboard is tested, by R-18. The risk is given a layer when the three things it needs exist | the participant, as product owner of the demo shop | 2026-11-25 |
| R-19 | REQ-04, REQ-08 | 9 | The made-up shop has no payment provider, so there is nothing to send a payment to and nothing to compare the order with | The shop's own record of the total and of one order is tested, by R-06 and R-08. The risk is ranked again before the shop takes real money | the participant, as product owner of the demo shop | 2026-11-25 |

The strategy was drafted by an AI assistant. Each acceptance above was given by the participant, in conversation, on
the date shown. This file records it and cannot prove it.

**Parts of a requirement that no test reaches, though the requirement is otherwise covered:**

- REQ-04 and REQ-08, the money itself. That is R-19, above.
- REQ-07, that the refusal message is visible on the page. The demo has no box for a code. See R-17.
- REQ-09, whether what is read aloud makes sense, and that each amount is tied to its label in the page's markup.
  That is R-11, above.
- REQ-06, that an order then exists, and that two orders get two references. The demo keeps no order and gives every
  order one reference. See R-10 and R-08.
- REQ-12, "can be read": text cut off or laid over other text at 320 pixels is not caught. See R-14.
- REQ-05, REQ-07 and REQ-08 are not built in the demo. Their tests, R-05, R-07, R-08, R-16 and R-17, cannot pass or
  fail until they are.

**Not covered, because no requirement asks for it:** two codes used together, an empty basket, what the customer sees
on a second press, the server's own clock and time zone on a code's last day, a price or a stock level
that changes while the customer is at the checkout, and a server that trusts an amount sent by the page.

## 6. Every requirement, and where it is covered

| Requirement | Importance | Risks | Tested at | Left untested |
|---|---|---|---|---|
| REQ-01 | must | R-01 | unit | |
| REQ-02 | must | R-02, R-16 | unit | |
| REQ-03 | must | R-03, R-15 | unit | R-15 |
| REQ-04 | must | R-04, R-06, R-09, R-19 | unit, API, UI | R-19 |
| REQ-05 | must | R-05 | unit | |
| REQ-06 | must | R-06, R-10 | API, UI | |
| REQ-07 | should | R-07, R-16, R-17 | unit, API | |
| REQ-08 | must | R-08, R-19 | API | R-19 |
| REQ-09 | should | R-11, R-18 | UI | R-11 |
| REQ-10 | should | R-09, R-12 | UI, unit | |
| REQ-11 | could | R-13 | | R-13 |
| REQ-12 | could | R-14 | UI | |

## 7. How long each layer would take to run

**These are estimates. No test in this strategy exists, so none of these was measured.**

| Layer | Risks | Cases, about | One case, about | The layer, about | What the estimate rests on |
|---|---|---|---|---|---|
| unit | R-01, R-02, R-03, R-04, R-05, R-07, R-12, R-16 | 30 calls | 1 millisecond | under 1 second, plus the test runner's start, which is not guessed | The cases each block lists: 3, 3, 2, 2, a guess of 8, 4, 4 and 3. Each is one call of a function that does arithmetic |
| API | R-06, R-08, R-17 | 30 requests | 20 milliseconds | 2 seconds | 2 for R-06, about 26 for R-08 with its repeats and its counts of orders, 4 for R-17. A guess at 20 milliseconds each, and a guess at a second to start the server |
| UI | R-09, R-10, R-14, R-18 | 4 tests | 0.4 seconds | 5 seconds | One Playwright test of another small demo on this computer took 346 to 373 milliseconds, in an earlier quest's log. A guess of 3 seconds to start the browser is added |
| manual | none | | | | No risk is given to a person. R-11 would be, and is untested |

The measured figure is from `participant/evidence/playwright-data-isolation/playwright-attempt-002/logs/shuffle-run.txt`.
It is of another demo, not of this checkout.

The automated layers together come to about 8 seconds. On a shop this small the seconds are not the point. If the 30
unit cases were browser tests they would add about 12 seconds, and that is still small. What the lower layers buy here
is that the cases with other baskets, about 18 of the 30, can exist at all, since the page has no way to enter a
basket, and that a failure points at one function.

**This says nothing about how long the tests take to write.** No estimate of that is made.

## 8. If the release were next week

**A proposal. It is not in force, and nothing below has been accepted.**

**The first thing a week does not change: three requirements are not built.** REQ-05 and REQ-08 are must, and by the
requirements' own words a broken must stops the release. REQ-07 is should. Whether to release without them is the
owner's decision, and no test strategy makes it.

The five tests that need nothing built, R-06, R-09, R-10, R-14 and R-18, would be written first. The rest would follow
in the order of section 2, so that if time ran out it would run out at the bottom. Before any unit test, the sums and
the formatting have to be moved into a module that can be called. That is one piece of work, and six risks wait on it.
No estimate is made of how long any of this takes to write, so this section cannot say what fits in a week.

What would change:

| Risk | Now | Next week | Why |
|---|---|---|---|
| R-09 | its own UI test | folded into R-10's journey: the one test reads the amounts before it presses the button | One browser test to write and keep, in place of two. A failure no longer says at once which of the two broke |
| R-05, R-07, R-08, R-16, R-17 | tested once their features are built | untested, if the release goes out without REQ-05, REQ-07 and REQ-08 | Their tests cannot run without the features. Each would need the owner's acceptance, and four of the five score 9 |

So up to five more risks would need the owner's acceptance, and whether to release at all without two must
requirements comes before that.

## What this strategy does not say

- That any of these tests exists, passes, or would catch what it is meant to.
- That the likelihoods and impacts are right. Each is a judgement resting on a stated clause. Another person reading
  the same clauses could fairly put several of them one level away, and a team that knows its own history would.
- How many defects there are. A rank says where to look first.
- That a test with expected values "worked out by hand" checks the rule. It checks that the code agrees with whoever
  worked them out.

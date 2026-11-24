# Maintenance report: the checkout test that fails after the redesign

Written by an AI assistant (Claude) at the participant's direction, for the quest `playwright-maintenance-report`.

**This report was written before the test was touched.** The change proposed here has not been made to
`participant/tests/playwright/needs-maintenance.spec.ts`. That file's checksum was taken before this report was
written, and is in
`participant/evidence/playwright-maintenance-report/playwright-attempt-005/logs/before-report.txt`:

    sha256  346bc90d1453c9d9002beeebe2879cee96d76c81cdf0ddd877ff63867117ce0c

Whether the file still has that checksum is not something a report can show about itself. The check in
`participant/tests/playwright/tools/maintenance-report-check.ts` takes it again and records the comparison.

The shop, its products and its prices are made up. The application runs on this computer only. So there is
no real owner of its tax rule. Where this report says "whoever owns the tax rule", read: in a real team, a
named person and a ticket.

**What is seen and what is predicted.** Parts 1 to 9 were written from one observed failure, at line 8, and
from reading the application's change. Everything they say about lines 9 to 15, including the figure 8.00,
is a prediction from that reading. Part 10, added afterwards, says what was then observed.

## In short

- The test fails because the checkout was redesigned. **That part is a test change**: six lines.
- Behind that failure is a second difference the redesign's change note does not mention: by the
  application's change, **the tax figure will be 8.00 where the test expects 7.20.** That part is a
  **POSSIBLE PRODUCT BUG**, and is not a test change.
- The proposed change fixes the six lines and **keeps the expected tax at 7.20**. After it, the test will still
  fail, stopping at line 11, for one reason: the tax. That is the result wanted. It is the test doing its job.
- **Do not make the test pass by changing or removing the tax amount.** Somebody who owns the tax rule has to
  say which figure is right.

## 1. Cause

The test was written for the checkout as it was before the redesign. It finds the amounts in the order summary
by the ids `#subtotal`, `#discount`, `#tax` and `#total`, the confirmation total by `#confirm-total`, and the
button by its label, "Place order". It expects amounts written without a currency sign.

The redesign replaced the summary table with a description list whose amounts carry test ids, removed the old
ids, relabelled the button "Buy now", and put a currency sign in front of every amount. So the first thing the
test looks for, `#subtotal`, is no longer on the page. The test waits for it, gives up, and fails at line 8.

It never reaches the lines after that. Read against the application's change, three more of its expectations
would fail for the same reason, and one would fail for a different reason: the tax.

## 2. Evidence

| What | Where | What it shows |
|---|---|---|
| The failure | `participant/evidence/playwright-maintenance-report/playwright-attempt-005/logs/before-report.txt` | Against the checkout in use the test fails at line 8: `Locator: locator('#subtotal')`, `Expected: "40.00"`, `element(s) not found` |
| It passed before | the same file | Against the checkout before the redesign the test passes. So the test agreed with the application as it was, and the application is what changed |
| The application's change | `participant/tests/playwright/needs-maintenance.app-change.diff` | The whole difference between the two versions |
| The change note | the head of `participant/tests/playwright/demo-app/checkout-server.mjs` | What the redesign's author says changed: the button label, the summary's layout and test ids, the currency sign. Three things. Tax is not among them |
| The version before | `participant/tests/playwright/demo-app/checkout-server.before.mjs` | The rule the test was written to: tax is 20% of the subtotal with the discount taken off |

From the diff, line by line of the test:

| Test line | The test relies on | The diff shows | So |
|---|---|---|---|
| 8 | `id="subtotal"`, an amount with no sign | `-<tr><th>Subtotal</th><td id="subtotal">` becomes `+<dt>Subtotal</dt><dd data-testid="summary-subtotal">`. And `-const money = (value) => value.toFixed(2);` becomes ``+const money = (value) => `${value < 0 ? "-" : ""}£${Math.abs(value).toFixed(2)}`;`` | affected |
| 9 | `id="discount"`, written `-4.00` | becomes `data-testid="summary-discount">${money(-a.discount)}`. By the new `money()`, a negative amount is a plain hyphen, then the sign, then the digits: `-£4.00` | affected |
| 11 | `id="tax"`, and the amount 7.20 | becomes `data-testid="summary-tax"`. **And** `-  const tax = goods * (fault === "tax-rate-wrong" ? 0.25 : TAX_RATE);` becomes `+  const tax = subtotal * (fault === "tax-rate-wrong" ? 0.25 : TAX_RATE);`. `TAX_RATE` is not in the diff, so the rate is unchanged at 0.2 | the locator and the sign are affected. **The amount is a separate matter: part 7** |
| 12 | `id="total"`, and the amount 43.20 | becomes `data-testid="summary-total"` | the locator and the sign are affected. The amount follows the tax: part 7 |
| 13 | a button labelled "Place order" | `-<button type="submit">Place order</button>` becomes `+<button type="submit">Buy now</button>` | affected |
| 14 | a heading "Order placed" | the heading is the same in both versions | **not affected** |
| 15 | `id="confirm-total"`, and the amount 43.20 | `<span id="confirm-total">${money(...)}` becomes `<span data-testid="confirmation-total">${money(...)}`, through the same new `money()` | the locator and the sign are affected. The amount follows the tax |

The test stopped at line 8, so lines 9 to 15 are judged from the diff and were not seen to fail. Part 6 says
how that reading is to be checked.

`getByTestId` looks for the attribute `data-testid` unless the settings say otherwise.
`participant/tests/playwright/maintenance.config.ts` does not set another.

One more line of the diff bears on part 7. The comment that stated the tax rule, "tax is 20% of what the
customer pays for the goods, which is the subtotal with the discount taken off", was in the version before and
is gone from the version in use. Nothing was put in its place.

## 3. The proposed change

Change six lines of the test, each in the two ways the redesign requires and in no other way:

1. find the element by its new test id, or the button by its new label;
2. expect the currency sign the page now shows.

Leave every amount's digits exactly as they are. Leave the order of the steps, the comment that states the
business rule, and every other line exactly as they are. Add nothing. Remove nothing.

**What to expect afterwards.** By the diff, the test should get past lines 8 and 9 and fail at line 11,
expecting `£7.20` and receiving `£8.00`. Stop there. Do not go on to make it pass. Take part 7 to whoever owns
the tax rule. Lines 12 and 15 expect totals that follow from the same figure. They would fail as well, and the
test stops before reaching them.

**Make the change to the test itself only after the check in part 6 has tried it on a copy.** From
`participant/tests/playwright`:

    node tools/maintenance-report-check.ts

## 4. The change, line by line

Lines changed: 8, 9, 11, 12, 13, 15. Lines not changed: 1, 2, 3, 4, 5, 6, 7, 10, 14, 16.

Each change gives the line number, the whole line as it is now, and the whole line to put in its place. If a
line does not read exactly as "Now" says, stop: the test is not the test this report was written for.

### Change 1 · line 8

Now:

```ts
  await expect(page.locator("#subtotal")).toHaveText("40.00");
```

Change to:

```ts
  await expect(page.getByTestId("summary-subtotal")).toHaveText("£40.00");
```

### Change 2 · line 9

Now:

```ts
  await expect(page.locator("#discount")).toHaveText("-4.00");
```

Change to:

```ts
  await expect(page.getByTestId("summary-discount")).toHaveText("-£4.00");
```

### Change 3 · line 11

Now:

```ts
  await expect(page.locator("#tax")).toHaveText("7.20");
```

Change to:

```ts
  await expect(page.getByTestId("summary-tax")).toHaveText("£7.20");
```

The amount stays 7.20. This is the line part 5 is about.

### Change 4 · line 12

Now:

```ts
  await expect(page.locator("#total")).toHaveText("43.20");
```

Change to:

```ts
  await expect(page.getByTestId("summary-total")).toHaveText("£43.20");
```

### Change 5 · line 13

Now:

```ts
  await page.getByRole("button", { name: "Place order" }).click();
```

Change to:

```ts
  await page.getByRole("button", { name: "Buy now" }).click();
```

### Change 6 · line 15

Now:

```ts
  await expect(page.locator("#confirm-total")).toHaveText("43.20");
```

Change to:

```ts
  await expect(page.getByTestId("confirmation-total")).toHaveText("£43.20");
```

## 5. The business assertion that must be preserved

**The tax. Line 11 of the test: the tax shown is 7.20.**

Line 10, the comment above it, states the rule the amount comes from: tax is 20% of what the customer pays for
the goods, after the discount. The basket is 40.00, the discount takes off 4.00, and 20% of 36.00 is 7.20.

This is the one line in the test that checks a calculation a customer is charged by, and that the business
could be held to. It is also the line the redesign makes easiest to lose, because its locator has to change
anyway. Change 3 changes how the line finds the figure and what sign it expects. It does not change the
figure.

Two more amounts stand or fall with it and are preserved the same way: the total on line 12 and the total on
the confirmation, line 15, both 43.20, which is 36.00 plus 7.20.

## 6. What would show that the change weakened the test

Six signs. Any one of them means the change went further than this report proposes.

| Sign | What to look at | The change is sound if |
|---|---|---|
| W1 | the number of `expect(` calls | it is the same as before: six |
| W2 | every amount in the test | each is still there, on the same line, with the same digits: 40.00, 4.00, 7.20, 43.20, 43.20 |
| W3 | how each expectation is made | nothing loosening was added: no "contains" or pattern match in place of an exact one, no `soft`, `skip`, `fixme` or `only`, no longer timeout, no negation, no `try`, no assertion commented out |
| W4 | which lines differ | only lines 8, 9, 11, 12, 13 and 15, and the test still has 16 lines |
| W5 | what the changed test does against the checkout in use | it **fails at line 11**, expecting `£7.20` and receiving `£8.00`. A changed test that **passes** has lost or altered the tax assertion, because the application's tax figure is not the one the rule gives |
| W6 | what the changed test can catch | every deliberate fault the old test caught in the old checkout, the changed test catches in the new one |

W5 is the unusual one. Here, passing is the sign of a weakened test.

W5 and W6 need the test to be run. They are to be tried on a copy, with the test itself left alone, by
`participant/tests/playwright/tools/maintenance-report-check.ts`.

To judge the layout changes apart from the tax question, that check makes a scratch copy of the redesigned
checkout with its two tax lines put back as they were, and runs the copy of the test against that. There the
copy should pass, all the way through the button and the confirmation. If it does not, part 2's reading of the
diff missed something. This matters because against the checkout in use the test stops at line 11, so lines
12 to 15 are never reached there.

The deliberate faults for W6 are eight, switched on one at a time by `CHECKOUT_FAULT`, and are listed at the
head of each version of the application: the tax left out of the total, the wrong tax rate, the wrong tax
figure shown, the discount ignored, the total ignoring the discount, a wrong subtotal, a button that does
nothing, and a wrong total on the confirmation.

## 7. A test change, or a possible product bug

Both, and they must not be mixed.

**A test change: the layout.** The button label, the summary's markup and test ids, and the currency sign are
all in the redesign's change note. The application behaves as its author intended, and the test is out of
date about how the page is built. Changes 1 to 6 put that right. The owner of the test makes them.

**A POSSIBLE PRODUCT BUG: the tax.** In the version before, tax was 20% of the goods after the discount: 7.20.
In the version in use, the diff shows tax worked out on the subtotal before the discount: 20% of 40.00, which
is 8.00. The customer is charged 44.00 where it was 43.20.

- The change note lists three changes. This is not one of them.
- It could be a deliberate change of rule that nobody wrote into the change note. The comment that stated the
  old rule was removed, which fits that.
- It could be a mistake made while the summary was rewritten. One word differs, `goods` became `subtotal`,
  on a line next to the ones being rewritten, which fits that.

The diff fits both, and nothing in the test or the application says which. **This report does not decide it, and the test
must not decide it either.** Setting the expected tax to 8.00 would record a decision nobody has made, in the
one place meant to check it.

What to do: take the two figures and the two lines of the diff to whoever owns the tax rule. In this
made-up shop nobody does, so the question is recorded here and goes no further.

- If the answer is **"it is a bug"**: the application's developers put the tax back. The test, with changes 1
  to 6 made, then passes. No further change to the test.
- If the answer is **"the new rule is intended"**: a second, separate change to the test, made on that
  person's word and saying so: line 10 restates the rule, and lines 11, 12 and 15 take the amounts 8.00, 44.00
  and 44.00.

## 8. Options and effort

| Option | What it is | Effort | Result |
|---|---|---|---|
| **A. Proposed** | changes 1 to 6, the amounts untouched, the tax question raised | about 15 minutes for the six lines. The answer on tax takes as long as its owner takes | the test stops at line 11, for the right reason, until the tax is ruled on |
| B. After a ruling that the new tax is intended | A, then lines 10, 11, 12 and 15 | about 10 minutes more | the test passes, and checks the new rule |
| C. After a ruling that it is a bug | A, and the application is corrected by its developers | no more test work | the test passes, and checks the old rule |
| D. Delete the tax assertion and set the totals to what the page shows | the scenario's mistake | about 5 minutes | the test passes and no longer checks the tax. **Not proposed** |
| E. Set every expected amount to what the page shows | quick and looks careful | about 5 minutes | the test passes, having taken the new figure as right without anyone deciding. **Not proposed** |
| F. Keep the lines and only check that an amount is shown | "making it less brittle" | about 5 minutes | the test passes whatever the amounts are. **Not proposed** |
| G. A, and mark the test as an expected failure with a ticket for the tax question | keeps the assertion, and keeps the suite's results readable while the question is open | about 20 minutes, and a ticket | the suite is green, with a recorded reason. **A fair choice, and the team's to make** |

The times are the author's estimates. Nothing was measured.

D, E and F are the cheapest, and each ends with a green test. That is what makes them tempting.

On G. A red test with no owner and no date gets ignored, which is its own way of losing an assertion. Marking
it as an expected failure, with the ticket, is a recognised answer. It is not proposed here for one reason:
sign W3 treats `fail`, `skip` and `fixme` as loosening, and it should, unless someone decides otherwise on
purpose. If the team takes G, that decision is written down with the ticket, and W3 is expected to flag it.

## 9. The triage this follows

By the rules in `participant/context/playwright/triage-rules.md`, from the earlier quest:

- **The failure that was seen**, at line 8, is a `test-defect`: the application behaves as intended and the test
  is wrong about it. Next action: the owner of the test.
- **The failure that will be seen** once the six lines are changed, at line 11, is `inconclusive` between
  `product-bug` and an intended change of rule. The evidence fits both. What would settle it is the word of
  whoever owns the tax rule. Next action: whoever can get that.

The earlier quest's own report, `participant/context/playwright/triage-report.md`, is about a different
application. Its rule is the one applied here: a failure gets one class from its evidence, and "it passes now"
is not evidence of anything.

## 10. Since this report was first written: what was observed

Added after the check was run. Parts 1 to 9 are as they were, apart from wording a reader asked to be made
plainer and the lines of the diff, which were quoted again after a test switch was taken out of the
application. The test file was not changed, before or after.

The record is `participant/evidence/playwright-maintenance-report/playwright-attempt-005/logs/unchanged-check.txt`.

| Predicted above | Observed, on a copy of the test |
|---|---|
| The six changes can be made exactly as listed | A program applied them from part 4. Every "Now" line matched |
| The changed test fails at line 11, expecting `£7.20`, receiving `£8.00` | It did, in those words. So the figure 8.00 is now seen, not only read from the diff |
| With the tax lines put back, the changed test passes, through the button and the confirmation | It did. So lines 12 to 15, including the new button label and the confirmation's test id and sign, are right |
| Signs W1 to W4 are clear | They are |
| W6: every fault the old test caught, the changed test catches | 8 of 8, and 8 of 8 |
| Options D, E and F each make the test pass | Each did. D let one fault through and F let six through. E let none through, and is caught only by W2 and W5 |

A reader given only this report and the test, and nothing else, produced the same changed test as the program
did, line for line.

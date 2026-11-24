# The assertions of the checkout test, before and after the repair

Quest `playwright-repair-test`. Written by `participant/tests/playwright/tools/repair-test-check.ts --write`, which reads
the two files and works this out. It was not typed by hand, and the check fails if this file is not what the program
writes. The program was written by an AI assistant (Claude) at the participant's direction.

- Before: `participant/tests/playwright/needs-maintenance.spec.ts`, sha256 `346bc90d1453c9d9002beeebe2879cee96d76c81cdf0ddd877ff63867117ce0c`
- After: `participant/tests/playwright/needs-maintenance.repaired.spec.ts`, sha256 `7ee32b00fb1c28cb0d203dabee212fac01583f8e68476c1b91813bf4c645f4d6`
- The plan the repair follows: `participant/context/playwright/maintenance-report.md`, part 4

The shop, its products, its prices and its discount code are made up.

## In short

- Assertions before: 6. Assertions after: 6.
- Removed: 0. Added: 0.
- Reported as weakened by the check: 0.
- Changes that the maintenance report does not account for: 0.

## Each assertion, before and after

An assertion here is one `expect(...)` with its matcher. "What it looks at" is the part inside `expect( )`.

### Assertion 1 · line 8 before · line 8 after

| | Before | After | Same? |
|---|---|---|---|
| The whole line | `await expect(page.locator("#subtotal")).toHaveText("40.00");` | `await expect(page.getByTestId("summary-subtotal")).toHaveText("£40.00");` | changed |
| What it looks at | `page.locator("#subtotal")` | `page.getByTestId("summary-subtotal")` | changed |
| Matcher | `toHaveText` | `toHaveText` | the same |
| Expected value | `"40.00"` | `"£40.00"` | changed: gained "£", lost nothing |
| The number in it | `40.00` | `40.00` | the same |
| Between expect and the matcher (not, soft) | `nothing` | `nothing` | the same |
| Before it on the line | `await` | `await` | the same |
| After it on the line | `;` | `;` | the same |
| How deep in braces (1 is the test's own body) | `1` | `1` | the same |

**Verdict: no rule of the check reports this line as removed, weakened or made conditional.** It reads exactly as the maintenance report's Change 1 says (report line 106). Compared with before: what it looks at changed, as shown in the table; the matcher is the same; the number is the same; the expected value gained "£" and lost nothing; it is still a plain awaited statement at the same depth.

### Assertion 2 · line 9 before · line 9 after

| | Before | After | Same? |
|---|---|---|---|
| The whole line | `await expect(page.locator("#discount")).toHaveText("-4.00");` | `await expect(page.getByTestId("summary-discount")).toHaveText("-£4.00");` | changed |
| What it looks at | `page.locator("#discount")` | `page.getByTestId("summary-discount")` | changed |
| Matcher | `toHaveText` | `toHaveText` | the same |
| Expected value | `"-4.00"` | `"-£4.00"` | changed: gained "£", lost nothing |
| The number in it | `4.00` | `4.00` | the same |
| Between expect and the matcher (not, soft) | `nothing` | `nothing` | the same |
| Before it on the line | `await` | `await` | the same |
| After it on the line | `;` | `;` | the same |
| How deep in braces (1 is the test's own body) | `1` | `1` | the same |

**Verdict: no rule of the check reports this line as removed, weakened or made conditional.** It reads exactly as the maintenance report's Change 2 says (report line 120). Compared with before: what it looks at changed, as shown in the table; the matcher is the same; the number is the same; the expected value gained "£" and lost nothing; it is still a plain awaited statement at the same depth.

### Assertion 3 · line 11 before · line 11 after

| | Before | After | Same? |
|---|---|---|---|
| The whole line | `await expect(page.locator("#tax")).toHaveText("7.20");` | `await expect(page.getByTestId("summary-tax")).toHaveText("£7.20");` | changed |
| What it looks at | `page.locator("#tax")` | `page.getByTestId("summary-tax")` | changed |
| Matcher | `toHaveText` | `toHaveText` | the same |
| Expected value | `"7.20"` | `"£7.20"` | changed: gained "£", lost nothing |
| The number in it | `7.20` | `7.20` | the same |
| Between expect and the matcher (not, soft) | `nothing` | `nothing` | the same |
| Before it on the line | `await` | `await` | the same |
| After it on the line | `;` | `;` | the same |
| How deep in braces (1 is the test's own body) | `1` | `1` | the same |

**Verdict: no rule of the check reports this line as removed, weakened or made conditional.** It reads exactly as the maintenance report's Change 3 says (report line 134). Compared with before: what it looks at changed, as shown in the table; the matcher is the same; the number is the same; the expected value gained "£" and lost nothing; it is still a plain awaited statement at the same depth.

### Assertion 4 · line 12 before · line 12 after

| | Before | After | Same? |
|---|---|---|---|
| The whole line | `await expect(page.locator("#total")).toHaveText("43.20");` | `await expect(page.getByTestId("summary-total")).toHaveText("£43.20");` | changed |
| What it looks at | `page.locator("#total")` | `page.getByTestId("summary-total")` | changed |
| Matcher | `toHaveText` | `toHaveText` | the same |
| Expected value | `"43.20"` | `"£43.20"` | changed: gained "£", lost nothing |
| The number in it | `43.20` | `43.20` | the same |
| Between expect and the matcher (not, soft) | `nothing` | `nothing` | the same |
| Before it on the line | `await` | `await` | the same |
| After it on the line | `;` | `;` | the same |
| How deep in braces (1 is the test's own body) | `1` | `1` | the same |

**Verdict: no rule of the check reports this line as removed, weakened or made conditional.** It reads exactly as the maintenance report's Change 4 says (report line 150). Compared with before: what it looks at changed, as shown in the table; the matcher is the same; the number is the same; the expected value gained "£" and lost nothing; it is still a plain awaited statement at the same depth.

### Assertion 5 · line 14 before · line 14 after

| | Before | After | Same? |
|---|---|---|---|
| The whole line | `await expect(page.getByRole("heading", { name: "Order placed" })).toBeVisible();` | `await expect(page.getByRole("heading", { name: "Order placed" })).toBeVisible();` | the same |
| What it looks at | `page.getByRole("heading", { name: "Order placed" })` | `page.getByRole("heading", { name: "Order placed" })` | the same |
| Matcher | `toBeVisible` | `toBeVisible` | the same |
| Expected value | `` | `` | the same |
| The number in it | `none` | `none` | the same |
| Between expect and the matcher (not, soft) | `nothing` | `nothing` | the same |
| Before it on the line | `await` | `await` | the same |
| After it on the line | `;` | `;` | the same |
| How deep in braces (1 is the test's own body) | `1` | `1` | the same |

**Verdict: unchanged.** The line is the same, character for character.

### Assertion 6 · line 15 before · line 15 after

| | Before | After | Same? |
|---|---|---|---|
| The whole line | `await expect(page.locator("#confirm-total")).toHaveText("43.20");` | `await expect(page.getByTestId("confirmation-total")).toHaveText("£43.20");` | changed |
| What it looks at | `page.locator("#confirm-total")` | `page.getByTestId("confirmation-total")` | changed |
| Matcher | `toHaveText` | `toHaveText` | the same |
| Expected value | `"43.20"` | `"£43.20"` | changed: gained "£", lost nothing |
| The number in it | `43.20` | `43.20` | the same |
| Between expect and the matcher (not, soft) | `nothing` | `nothing` | the same |
| Before it on the line | `await` | `await` | the same |
| After it on the line | `;` | `;` | the same |
| How deep in braces (1 is the test's own body) | `1` | `1` | the same |

**Verdict: no rule of the check reports this line as removed, weakened or made conditional.** It reads exactly as the maintenance report's Change 6 says (report line 178). Compared with before: what it looks at changed, as shown in the table; the matcher is the same; the number is the same; the expected value gained "£" and lost nothing; it is still a plain awaited statement at the same depth.

## The lines that are not assertions

| Line | Before | After | |
|---|---|---|---|
| 1 | `import { expect, test } from "@playwright/test";` | `import { expect, test } from "@playwright/test";` | the same |
| 6 | `test("checkout shows the right amounts and places the order", async ({ page }) => {` | `test("checkout shows the right amounts and places the order", async ({ page }) => {` | the same |
| 7 | `await page.goto("/");` | `await page.goto("/");` | the same |
| 13 | `await page.getByRole("button", { name: "Place order" }).click();` | `await page.getByRole("button", { name: "Buy now" }).click();` | changed, as the report's Change 5 says |
| 16 | `});` | `});` | the same |

Comment lines: 3 before and 3 after, each the same and on the same line. The comment that states the business rule is on line 10 after the repair.

## What the check reported

- Weakened: nothing.
- Not accounted for by the report: nothing.

Changes the check could not judge from the two files alone. Each is one the report calls for, word for word:

- line 8: the expected value gained characters: "40.00" is now "£40.00"
- line 8: the subject changed: page.locator("#subtotal") is now page.getByTestId("summary-subtotal")
- line 9: the expected value gained characters: "-4.00" is now "-£4.00"
- line 9: the subject changed: page.locator("#discount") is now page.getByTestId("summary-discount")
- line 11: the expected value gained characters: "7.20" is now "£7.20"
- line 11: the subject changed: page.locator("#tax") is now page.getByTestId("summary-tax")
- line 12: the expected value gained characters: "43.20" is now "£43.20"
- line 12: the subject changed: page.locator("#total") is now page.getByTestId("summary-total")
- line 15: the expected value gained characters: "43.20" is now "£43.20"
- line 15: the subject changed: page.locator("#confirm-total") is now page.getByTestId("confirmation-total")
- line 13: a statement changed in place: await page.getByRole("button", { name: "Place order" }).click(); is now await page.getByRole("button", { name: "Buy now" }).click();

## What this comparison cannot show

- It compares text. That a changed locator finds the right element is shown by running the test, not here. The record of
  that is the mutation run, `logs/mutation-run.txt` in the attempt folder.
- It reads the test file only. A weakening in the settings file, in the application, or in the command that runs the
  test would not appear in it.
- "As the report says" is only as good as the report.

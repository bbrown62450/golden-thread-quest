import { expect, test } from "@playwright/test";

/*
 * COUPLED ON PURPOSE. These two tests show the fault this quest is about. Do not copy them.
 *
 * The first test adds a customer called "Test User" and leaves it there. The second test
 * looks for a customer called "Test User" and upgrades it. It never creates one. So the
 * second test only passes because the first one ran before it, against the same application.
 *
 * What goes wrong, and it is recorded in logs/shuffle-run.txt:
 *
 *   - In the order written, on a freshly started application: both pass.
 *   - REVERSED: "upgrades Test User" runs first, finds no such customer, and fails.
 *   - A SECOND RUN against the same application: "adds Test User" fails, because the first
 *     run's "Test User" is still there and the application refuses a second one. This is the
 *     scenario: two testers, or one tester twice, and a customer called Test User.
 *
 * Three faults, all in these few lines:
 *   1. the second test depends on data it did not create;
 *   2. the name is fixed, so it collides with any other run;
 *   3. nothing is cleaned up, so the next run meets the last run's leftovers.
 *
 * The same behaviour, tested without these faults, is in isolated.spec.ts.
 */

test("coupled: adds Test User through the form", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Name").fill("Test User");
  await page.getByRole("button", { name: "Add customer" }).click();

  await expect(page.getByRole("status")).toHaveText("Added Test User.");
  await expect(page.getByRole("row").filter({ hasText: /^\s*Test User\s/ })).toContainText("basic");
});

test("coupled: upgrades Test User to the plus plan", async ({ page }) => {
  await page.goto("/");

  // Depends on the customer the test above left behind.
  await page.getByRole("button", { name: "Upgrade Test User", exact: true }).click();

  await expect(page.getByRole("row").filter({ hasText: /^\s*Test User\s/ })).toContainText("plus");
});

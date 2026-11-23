import { randomBytes } from "node:crypto";

import type { Page } from "@playwright/test";

import { expect, test, type Evidence } from "./support/evidence";

/*
 * Two tests for the playwright-failure-evidence quest, against the made-up order desk in
 * demo-app/orders-server.mjs.
 *
 * The first passes. It is here to show what a passing test leaves behind: one line.
 *
 * The second FAILS ON PURPOSE. It waits for the total of order ord-1003, which never appears.
 * Playwright's error says only that it waited and timed out. Why the total never appeared is
 * not in this file and not in the error. It has to be found in the failure bundle. That is the
 * point of the quest.
 *
 * Both tests import `test` from support/evidence.ts, which is all that is needed to have
 * evidence collected. Neither test mentions a trace, a screenshot or a log.
 *
 * The password is made up, afresh, each time a test runs. It is worth nothing: the application
 * accepts any password. It stands for a real one, so it is handed to `evidence.secret()` to be
 * kept out of the evidence, as a real one would have to be.
 *
 * The check script sets GTQ_CANARY_PASSWORD, so that it knows the password and can look for
 * exactly that string in the bundle afterwards. It is just as made up.
 */

async function signIn(page: Page, evidence: Evidence): Promise<void> {
  const typed = process.env.GTQ_CANARY_PASSWORD ?? `pw-${randomBytes(12).toString("hex")}`;
  evidence.secret(typed, "password");
  await page.goto("/");
  await page.getByLabel("Name").fill("Fixture Clerk");
  await page.getByLabel("Password").fill(typed);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByTestId("who")).toHaveText("Fixture Clerk");
}

test("the total of order ord-1001 is shown", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await page.getByRole("link", { name: "ord-1001" }).click();
  await expect(page.getByTestId("total")).toHaveText("Order total: 120.00");
});

test("FAILS ON PURPOSE: the total of order ord-1003 is shown", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await page.getByRole("link", { name: "ord-1003" }).click();
  await expect(page.getByTestId("total")).toBeVisible({ timeout: 5_000 });
});

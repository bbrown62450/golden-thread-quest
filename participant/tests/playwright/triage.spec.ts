import { randomBytes } from "node:crypto";

import type { Page } from "@playwright/test";

import { expect, test, type Evidence } from "./support/triage-evidence";

/*
 * Six tests for the playwright-failure-triage quest, against the made-up order desk in demo-app/triage-server.mjs.
 *
 * Each signs in, opens one order and checks the total the page shows. Each one fails, or can fail, when the check
 * script runs it under the conditions it arranges. Why each fails is deliberately not written in this file: this file's
 * text is copied into every failure bundle, and the bundles are classified by someone who has not been told.
 * The causes are in participant/context/playwright/ground-truth.md.
 *
 * The password is made up afresh each time. The application accepts any password.
 */

// helpers:start
async function signIn(page: Page, evidence: Evidence): Promise<void> {
  const typed = process.env.GTQ_CANARY_PASSWORD ?? `pw-${randomBytes(12).toString("hex")}`;
  evidence.secret(typed, "password");
  await page.goto("/");
  await page.getByLabel("Name").fill("Fixture Clerk");
  await page.getByLabel("Password").fill(typed);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByTestId("who")).toHaveText("Fixture Clerk");
}

async function openOrder(page: Page, id: string): Promise<void> {
  await page.getByRole("link", { name: id }).click();
  await expect(page.getByRole("heading", { name: `Order ${id}` })).toBeVisible();
}
// helpers:end

test("order ord-2001 shows its total", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await openOrder(page, "ord-2001");
  // 8 widgets at 12.50 and 1 toolkit at 20.00
  await expect(page.getByTestId("total")).toHaveText("Order total: 120.00");
});

test("order ord-2002 shows its total", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await openOrder(page, "ord-2002");
  // 3 widgets at 12.50
  const shown = await page.getByTestId("total").textContent();
  expect(shown).toBe("Order total: 37.50");
});

test("order ord-2003 shows its total", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await openOrder(page, "ord-2003");
  // 8 valves at 7.25 and 2 hoses at 4.50
  await expect(page.getByTestId("total")).toHaveText("Order total: 67.00");
});

test("order ord-2004 shows its total", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await openOrder(page, "ord-2004");
  // 2 widgets at 12.50 and 3 brackets at 3.20
  await expect(page.getByTestId("total")).toHaveText("Order total: 34.60");
});

test("order ord-2005 shows its total", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await openOrder(page, "ord-2005");
  // 12 lines of brackets, gaskets and hoses
  await expect(page.getByTestId("total")).toHaveText("Order total: 119.00");
});

test("order ord-2006 shows its total", async ({ page, evidence }) => {
  await signIn(page, evidence);
  await openOrder(page, "ord-2006");
  // 20 gaskets at 0.80 and 4 hoses at 4.50
  await expect(page.getByTestId("total")).toHaveText("Order total: 34.00");
});

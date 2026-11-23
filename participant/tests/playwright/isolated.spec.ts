import { randomUUID } from "node:crypto";

import { expect, test as base, type Locator, type Page } from "@playwright/test";

/*
 * Each test here makes the data it needs, uses it, removes it, and touches nothing else. So
 * the tests pass in any order, at the same time as each other, and twice in a row.
 *
 * The application under test is the made-up customer directory in demo-app/server.mjs.
 *
 * HOW A NAME IS MADE UNIQUE
 *   Every customer a test makes is called "<label> <run marker>-<random part>", for example
 *   "Ada fwd-3f9a1c2e-0b7e4d2a-6c1f-4a53-9e0b-5d2c8f7a1b34".
 *     - The random part is a fresh UUID, drawn for every single customer. It has 122 random
 *       bits. Two tests, two runs or two people cannot draw the same one in practice. It does
 *       not depend on the time, a counter, the test's title or which worker runs the test.
 *     - The run marker is the same for every customer of one run. It makes nothing unique. It
 *       is there so that a leftover can be traced to the run that left it.
 *
 * HOW CLEANUP WORKS
 *   The application hands back an id when it creates a customer. The `own` fixture below
 *   writes that id down at once, and after the test it removes exactly those ids.
 *     - It removes by id only. It never looks for customers by name or by pattern, so it
 *       cannot remove a customer it did not make, even one called "Test Userson".
 *     - It runs whether the test passed, failed halfway or timed out: Playwright runs the
 *       part of a fixture after `use()` in every one of those cases.
 *     - "Already gone" (404) is fine: a test whose subject is removing a customer has already
 *       removed it.
 *     - Anything else is an error, and fails the test, so a cleanup that did not work is
 *       never silent.
 */

type Customer = { id: string; name: string; plan: string };

type OwnData = {
  /** A name no other test or run can be using. */
  uniqueName(label: string): string;
  /** Create a customer through the application's own interface, and remember its id for cleanup. */
  create(label: string, plan?: "basic" | "plus"): Promise<Customer>;
  /** Remember the id of a customer this test made some other way (through the page), for cleanup. */
  adopt(id: string): void;
};

/** The same for every customer of one run. The check script sets it; otherwise it is drawn once per worker. */
const RUN_MARKER = process.env.GTQ_RUN_MARKER ?? `run-${randomUUID().slice(0, 8)}`;

const test = base.extend<{ own: OwnData }>({
  own: async ({ request }, use) => {
    const mine: string[] = []; // the ids of what THIS test created, and nothing else

    const own: OwnData = {
      uniqueName: (label) => `${label} ${RUN_MARKER}-${randomUUID()}`,
      create: async (label, plan = "basic") => {
        const response = await request.post("/api/customers", { data: { name: own.uniqueName(label), plan } });
        expect(response.status(), "the application should create the customer").toBe(201);
        const customer = (await response.json()) as Customer;
        mine.push(customer.id); // written down before the test does anything else with it
        return customer;
      },
      adopt: (id) => {
        mine.push(id);
      },
    };

    await use(own);

    // Everything below runs after the test, whether it passed, failed or timed out.
    const problems: string[] = [];
    for (const id of mine.reverse()) {
      const response = await request.delete(`/api/customers/${encodeURIComponent(id)}`);
      if (response.status() !== 204 && response.status() !== 404) {
        problems.push(`customer ${id}: status ${response.status()}`);
      }
    }
    expect(problems, "cleanup should remove every customer this test created").toEqual([]);
  },
});

/** The table row of one customer, found by its whole, unique name. */
function rowOf(page: Page, customer: { name: string }): Locator {
  return page.getByRole("row").filter({ has: page.getByRole("cell", { name: customer.name, exact: true }) });
}

test("a customer is listed with the plan it was given", async ({ page, own }) => {
  const ada = await own.create("Ada", "plus");

  await page.goto("/");

  await expect(rowOf(page, ada)).toHaveCount(1);
  await expect(rowOf(page, ada)).toContainText("plus");
});

test("upgrading one customer changes that customer and no other", async ({ page, own }) => {
  const grace = await own.create("Grace", "basic");
  const linus = await own.create("Linus", "basic");

  await page.goto("/");
  await page.getByRole("button", { name: `Upgrade ${grace.name}`, exact: true }).click();

  await expect(rowOf(page, grace)).toContainText("plus");
  await expect(rowOf(page, linus)).toContainText("basic");
});

test("removing one customer through the page removes that customer and no other", async ({ page, own }) => {
  const edsger = await own.create("Edsger");
  const barbara = await own.create("Barbara");

  await page.goto("/");
  await page.getByRole("button", { name: `Remove ${edsger.name}`, exact: true }).click();

  await expect(rowOf(page, edsger)).toHaveCount(0);
  await expect(rowOf(page, barbara)).toHaveCount(1);
  // Cleanup will find Edsger already gone (404) and remove Barbara.
});

test("a customer added through the form is listed", async ({ page, own }) => {
  const name = own.uniqueName("Katherine");

  await page.goto("/");
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("Plan").selectOption("plus");
  await page.getByRole("button", { name: "Add customer" }).click();

  // The page says which customer it added. Its id is written down straight away, before any
  // other check can fail, so that cleanup knows about it.
  const id = await page.getByRole("status").getAttribute("data-customer-id");
  expect(id, "the page should say which customer it added").toBeTruthy();
  own.adopt(id!);

  await expect(page.getByRole("status")).toHaveText(`Added ${name}.`);
  await expect(rowOf(page, { name })).toContainText("plus");
});

test("a second customer with a name already in use is refused", async ({ page, own }) => {
  const margaret = await own.create("Margaret");

  await page.goto("/");
  await page.getByLabel("Name").fill(margaret.name);
  await page.getByRole("button", { name: "Add customer" }).click();

  await expect(page.getByRole("alert")).toHaveText(`A customer called ${margaret.name} already exists.`);
  await expect(rowOf(page, margaret)).toHaveCount(1);
});

/*
 * This test FAILS ON PURPOSE, and only runs when asked: GTQ_FAIL_HALFWAY=1.
 * It creates two customers and then fails before it has finished. The check script runs it to
 * show that cleanup still removes both. In an ordinary run it is skipped.
 */
test("FAILS ON PURPOSE: cleanup still runs when a test fails halfway", async ({ page, own }) => {
  test.skip(process.env.GTQ_FAIL_HALFWAY !== "1", "only runs when GTQ_FAIL_HALFWAY=1");

  const alan = await own.create("Alan");
  await own.create("Hedy");
  await page.goto("/");
  await expect(rowOf(page, alan)).toHaveCount(1);

  expect("this test", "it fails here on purpose, halfway, with two customers created").toBe("finished");
});

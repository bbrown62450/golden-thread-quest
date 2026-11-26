import { randomUUID } from "node:crypto";

import { expect, test as base, type Locator, type Page } from "@playwright/test";

/*
 * Ten tests of the made-up customer directory in demo-app/server.mjs, each carrying one tag from each of the five
 * dimensions of participant/context/playwright/tag-scheme.md: feature, risk, read or write, layer and duration.
 *
 * The vocabulary is in support/tags.ts. tools/tagging-check.ts checks these tests against it: that each test has one
 * tag from every dimension and none from outside, and that what each test does is what its tags say.
 *
 * THE READ TESTS USE ONLY THE FOUR CUSTOMERS THE APPLICATION STARTS WITH. They create nothing, so they need no
 * clean-up, and they send nothing but reads. That is what the tag @read promises.
 *
 * THE WRITE TESTS MAKE THEIR OWN CUSTOMERS AND REMOVE THEM. Each customer has a name no other test or run can be
 * using, and is removed by its id after the test, whether the test passed or not. This is the `own` fixture of the
 * earlier data-isolation quest, copied here so that this file stands alone.
 */

type Customer = { id: string; name: string; plan: string };

type OwnData = {
  /** A name no other test or run can be using. */
  uniqueName(label: string): string;
  /** Create a customer through the application's own interface, and remember its id for clean-up. */
  create(label: string, plan?: "basic" | "plus"): Promise<Customer>;
  /** Remember the id of a customer this test made through the page, for clean-up. */
  adopt(id: string): void;
};

const test = base.extend<{ own: OwnData }>({
  own: async ({ request }, use) => {
    const mine: string[] = [];
    const own: OwnData = {
      uniqueName: (label) => `${label} tagging-${randomUUID()}`,
      create: async (label, plan = "basic") => {
        const name = own.uniqueName(label);
        const response = await request.post("/api/customers", { data: { name, plan } });
        expect(response.status(), "the application should create the customer").toBe(201);
        const answered = (await response.json()) as Customer;
        mine.push(answered.id);
        // The name and the plan returned are the ones that were SENT, not the ones the application answered with.
        return { id: answered.id, name, plan };
      },
      adopt: (id) => {
        mine.push(id);
      },
    };
    await use(own);
    const problems: string[] = [];
    for (const id of mine.reverse()) {
      const response = await request.delete(`/api/customers/${encodeURIComponent(id)}`);
      if (response.status() !== 204 && response.status() !== 404) problems.push(`customer ${id}: status ${response.status()}`);
    }
    expect(problems, "clean-up should remove every customer this test created").toEqual([]);
  },
});

/** The table row of one customer, found by its whole name. */
function rowOf(page: Page, customer: { name: string }): Locator {
  return page.getByRole("row").filter({ has: page.getByRole("cell", { name: customer.name, exact: true }) });
}

// ---------------------------------------------------------------- tests that only read

test(
  "the page lists a customer that was there before, with its plan",
  { tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@fast"] },
  async ({ page }) => {
    await page.goto("/");

    await expect(rowOf(page, { name: "Asha Verma" })).toHaveCount(1);
    await expect(rowOf(page, { name: "Asha Verma" })).toContainText("plus");
  },
);

test(
  "the list of customers comes back as data, each with an id, a name and a plan",
  { tag: ["@feature-list", "@risk-medium", "@read", "@layer-api", "@fast"] },
  async ({ request }) => {
    const response = await request.get("/api/customers");

    expect(response.status()).toBe(200);
    const customers = (await response.json()) as Customer[];
    expect(customers.find((one) => one.name === "Bo Lindqvist")).toEqual({ id: "seed-2", name: "Bo Lindqvist", plan: "basic" });
    for (const one of customers) expect(Object.keys(one).sort()).toEqual(["id", "name", "plan"]);
  },
);

test(
  "the form for adding a customer has a labelled name, a choice of two plans and a button",
  { tag: ["@feature-add", "@risk-low", "@read", "@layer-ui", "@fast"] },
  async ({ page }) => {
    await page.goto("/");

    await expect(page.getByLabel("Name")).toBeEditable();
    await expect(page.getByLabel("Plan").getByRole("option")).toHaveText(["basic", "plus"]);
    await expect(page.getByRole("button", { name: "Add customer" })).toBeEnabled();
  },
);

// ---------------------------------------------------------------- tests that write

test(
  "a customer created by a request is stored with the name and plan that were sent",
  { tag: ["@feature-add", "@risk-high", "@write", "@layer-api", "@fast"] },
  async ({ request, own }) => {
    const ada = await own.create("Ada", "plus");

    const stored = ((await (await request.get("/api/customers")).json()) as Customer[]).find((one) => one.id === ada.id);
    expect(stored).toEqual({ id: ada.id, name: ada.name, plan: "plus" });
    expect(ada.name).toContain("Ada tagging-");
  },
);

test(
  "a second customer with a name already in use is refused and not stored",
  { tag: ["@feature-add", "@risk-high", "@write", "@layer-api", "@fast"] },
  async ({ request, own }) => {
    const margaret = await own.create("Margaret");

    const again = await request.post("/api/customers", { data: { name: margaret.name, plan: "plus" } });
    // If the application wrongly creates it, clean-up must still know about it.
    if (again.status() === 201) own.adopt(((await again.json()) as Customer).id);

    expect(again.status()).toBe(409);
    const all = (await (await request.get("/api/customers")).json()) as Customer[];
    expect(all.filter((one) => one.name === margaret.name)).toEqual([{ id: margaret.id, name: margaret.name, plan: "basic" }]);
  },
);

test(
  "a customer added through the form is listed",
  { tag: ["@feature-add", "@risk-high", "@write", "@layer-ui", "@fast"] },
  async ({ page, own }) => {
    const name = own.uniqueName("Katherine");

    await page.goto("/");
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Plan").selectOption("plus");
    await page.getByRole("button", { name: "Add customer" }).click();

    // The page says which customer it added. The test waits until it names THIS customer, then writes down the id
    // for clean-up.
    await expect(page.getByRole("status")).toHaveText(`Added ${name}.`);
    const id = await page.getByRole("status").getAttribute("data-customer-id");
    expect(id, "the page should say which customer it added").toBeTruthy();
    own.adopt(id!);

    await expect(rowOf(page, { name })).toContainText("plus");
  },
);

test(
  "upgrading one customer changes that customer and no other",
  { tag: ["@feature-upgrade", "@risk-high", "@write", "@layer-ui", "@fast"] },
  async ({ page, own }) => {
    const grace = await own.create("Grace", "basic");
    const linus = await own.create("Linus", "basic");

    await page.goto("/");
    await page.getByRole("button", { name: `Upgrade ${grace.name}`, exact: true }).click();

    await expect(rowOf(page, grace)).toContainText("plus");
    await expect(rowOf(page, linus)).toContainText("basic");
  },
);

test(
  "removing one customer through the page removes that customer and no other",
  { tag: ["@feature-remove", "@risk-high", "@write", "@layer-ui", "@fast"] },
  async ({ page, own }) => {
    const edsger = await own.create("Edsger");
    const barbara = await own.create("Barbara");

    await page.goto("/");
    await page.getByRole("button", { name: `Remove ${edsger.name}`, exact: true }).click();

    await expect(rowOf(page, edsger)).toHaveCount(0);
    await expect(rowOf(page, barbara)).toHaveCount(1);
  },
);

test(
  "removing a customer that is not there is answered with not found",
  { tag: ["@feature-remove", "@risk-low", "@write", "@layer-api", "@fast"] },
  async ({ request }) => {
    // It changes nothing, and it is still a write: it sends a DELETE. The tag goes by what is sent.
    const response = await request.delete(`/api/customers/${randomUUID()}`);

    expect(response.status()).toBe(404);
  },
);

test(
  "sixty customers added one after another through the form are all listed",
  { tag: ["@feature-add", "@risk-high", "@write", "@layer-ui", "@slow"] },
  async ({ page, own }) => {
    const names: string[] = [];
    const ids: string[] = [];

    await page.goto("/");
    for (let number = 1; number <= 60; number += 1) {
      const name = own.uniqueName(`Bulk ${number}`);
      await page.getByLabel("Name").fill(name);
      await page.getByRole("button", { name: "Add customer" }).click();
      // Wait until the page names THIS customer, so that the id read next is its id and not the one before.
      await expect(page.getByRole("status")).toHaveText(`Added ${name}.`);
      const id = await page.getByRole("status").getAttribute("data-customer-id");
      expect(id, "the page should say which customer it added").toBeTruthy();
      expect(ids, "each customer added should have an id of its own").not.toContain(id);
      ids.push(id!);
      own.adopt(id!);
      names.push(name);
    }

    for (const name of names) await expect(rowOf(page, { name })).toHaveCount(1);
  },
);

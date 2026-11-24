import { expect, test, type Locator, type Page } from "@playwright/test";

import { navigation, precondition, proves } from "./support/proof";

/*
 * The checkout of the made-up shop in demo-app/checkout-server.corrected.mjs. Every product, price and code is invented.
 * Basket: 2 Trail mugs at 12.00 and 1 Field notebook at 16.00. Discount code WELCOME10.
 *
 * FOUR BUSINESS RULES, ONE TEST EACH
 *   R1  The discount is 10% of the subtotal.
 *   R2  Tax is 20% of what the customer pays for the goods, after the discount.
 *   R3  The total is the subtotal, less the discount, plus the tax.
 *   R4  The confirmation says the customer was charged the total they were shown.
 *
 * WHAT "PROVES" MEANS HERE, AND DOES NOT
 *   The checkout has one basket and one discount code. Each proof shows the rule's figure for that basket, on the page.
 *   It does not show the rule for any other basket, and R4 shows what a page says was charged: the application takes
 *   no money. Each piece of evidence says what it does not show.
 *
 * EVERY ASSERTION BELOW IS MARKED AS ONE OF THREE THINGS
 *   NAVIGATION    It shows the test got somewhere: a page opened, a heading is there. If it fails, the test fails. When
 *                 it passes it proves no rule, so nothing is captured.
 *   PRECONDITION  It shows the figures a rule starts from are the ones its arithmetic assumes. Without it, "the
 *                 discount is 4.00" means nothing. It is some other rule's business, or none, so nothing is captured.
 *   PROOF         It is the assertion that the rule held. This is the validation point, and the only place evidence is
 *                 captured: a picture of the part of the page the rule is about, and a record of the value asserted
 *                 and the value read. proves() makes the assertion itself, with the text given as hasExactlyTheText.
 */

/** The label and the amount of one line of the order summary. */
const line = (page: Page, testId: string): Locator[] => [page.getByTestId(testId).locator("xpath=preceding-sibling::dt[1]"), page.getByTestId(testId)];

async function openTheCheckout(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Checkout" })).toBeVisible(); // NAVIGATION: the checkout page opened. No rule.
}

test("R1 · the discount is 10% of the subtotal", async ({ page }, testInfo) => {
  await navigation(testInfo, "Open the checkout", () => openTheCheckout(page));

  await precondition(testInfo, "The subtotal is £40.00", async () => {
    await expect(page.getByTestId("summary-subtotal")).toHaveText("£40.00"); // PRECONDITION: what the 10% is taken of. Not R1.
  });

  // PROOF of R1. The assertion: the discount line reads -£4.00.
  await proves(testInfo, page, {
    id: "R1-discount",
    rule: "The discount is 10% of the subtotal",
    because: "10% of 40.00 is 4.00, shown as an amount taken off",
    doesNotShow: "that the discount is taken off what the customer pays. This line reads the same when the discount is printed and then ignored: R3 is where that is seen. Nor does it show the rate for any other subtotal. A flat 4.00 off would read the same",
    element: page.getByTestId("summary-discount"),
    elementIs: "the discount line of the order summary",
    hasExactlyTheText: "-£4.00",
    given: [["the subtotal", page.getByTestId("summary-subtotal")], ["the label of the discount line", line(page, "summary-discount")[0]]],
    picture: [...line(page, "summary-subtotal"), ...line(page, "summary-discount")],
  });
});

test("R2 · tax is 20% of the goods after the discount", async ({ page }, testInfo) => {
  await navigation(testInfo, "Open the checkout", () => openTheCheckout(page));

  await precondition(testInfo, "The subtotal is £40.00 and the discount is -£4.00, so the goods come to 36.00", async () => {
    await expect(page.getByTestId("summary-subtotal")).toHaveText("£40.00"); // PRECONDITION. Not R2.
    await expect(page.getByTestId("summary-discount")).toHaveText("-£4.00"); // PRECONDITION. This is R1's rule, proved in R1's test.
  });

  // PROOF of R2. The assertion: the tax line reads £7.20.
  await proves(testInfo, page, {
    id: "R2-tax",
    rule: "Tax is 20% of what the customer pays for the goods, after the discount",
    because: "40.00 less 4.00 is 36.00, and 20% of 36.00 is 7.20. On the 40.00 before the discount it would be 8.00",
    doesNotShow: "the rate for any other basket. A rate of 20.01% gives this same figure here. It is the tax shown, and R3 is where it is seen to be in the total",
    element: page.getByTestId("summary-tax"),
    elementIs: "the tax line of the order summary",
    hasExactlyTheText: "£7.20",
    given: [["the subtotal", page.getByTestId("summary-subtotal")], ["the discount", page.getByTestId("summary-discount")]],
    picture: [...line(page, "summary-subtotal"), ...line(page, "summary-discount"), ...line(page, "summary-tax")],
  });
});

test("R3 · the total is the subtotal, less the discount, plus the tax", async ({ page }, testInfo) => {
  await navigation(testInfo, "Open the checkout", () => openTheCheckout(page));

  await precondition(testInfo, "The subtotal is £40.00, the discount -£4.00 and the tax £7.20", async () => {
    await expect(page.getByTestId("summary-subtotal")).toHaveText("£40.00"); // PRECONDITION. Not R3.
    await expect(page.getByTestId("summary-discount")).toHaveText("-£4.00"); // PRECONDITION. R1's rule.
    await expect(page.getByTestId("summary-tax")).toHaveText("£7.20"); // PRECONDITION. R2's rule.
  });

  // This is where the discount is seen to be TAKEN OFF, and not only shown. A checkout that printed the discount and
  // added the tax to the full subtotal would pass R1 and R2 and fail here, reading £47.20.
  // PROOF of R3. The assertion: the total line reads £43.20.
  await proves(testInfo, page, {
    id: "R3-total",
    rule: "The total is the subtotal, less the discount, plus the tax",
    because: "40.00 less 4.00 plus 7.20 is 43.20",
    doesNotShow: "that any of the three figures it adds is right. It shows that they add up to the total",
    element: page.getByTestId("summary-total"),
    elementIs: "the total line of the order summary",
    hasExactlyTheText: "£43.20",
    given: [["the subtotal", page.getByTestId("summary-subtotal")], ["the discount", page.getByTestId("summary-discount")], ["the tax", page.getByTestId("summary-tax")]],
    picture: [...line(page, "summary-subtotal"), ...line(page, "summary-discount"), ...line(page, "summary-tax"), ...line(page, "summary-total")],
  });
});

test("R4 · the confirmation says the customer was charged the total they were shown", async ({ page }, testInfo) => {
  await navigation(testInfo, "Open the checkout", () => openTheCheckout(page));

  let totalShown = "";
  await precondition(testInfo, "A total is shown before the order, and is read", async () => {
    await expect(page.getByTestId("summary-total")).toHaveText(/^£\d+\.\d\d$/); // PRECONDITION: there is a total to compare the charge with. Whether it is the right total is R3's rule.
    totalShown = ((await page.getByTestId("summary-total").textContent()) ?? "").trim();
  });

  await navigation(testInfo, "Press \"Buy now\" and reach the confirmation", async () => {
    await page.getByRole("button", { name: "Buy now" }).click();
    await expect(page.getByRole("heading", { name: "Order placed" })).toBeVisible(); // NAVIGATION: the order went through. It says nothing of what was charged.
  });

  // PROOF of R4. The assertion: the confirmation's amount is the total that was read from the checkout page before the order.
  await proves(testInfo, page, {
    id: "R4-charge",
    rule: "The confirmation says the customer was charged the total they were shown",
    because: "it is the total that was on the checkout page before \"Buy now\" was pressed. The test read it then and compares the confirmation with it",
    doesNotShow: "that any money was taken, or how much. The application takes none. This is what the confirmation page says, set against what the checkout page said. Nor does it show the total was the right one: that is R3",
    element: page.getByTestId("confirmation-total"),
    elementIs: "the amount beside \"Total charged\" on the confirmation",
    hasExactlyTheText: totalShown,
    given: [["the total shown on the checkout page, read by the test before the order", totalShown]],
    picture: [page.getByTestId("confirmation-total").locator("xpath=..")],
  });
});

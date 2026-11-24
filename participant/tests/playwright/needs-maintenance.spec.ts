import { expect, test } from "@playwright/test";

// The checkout of the made-up shop in demo-app/checkout-server.mjs. Every product, price and code is invented.
// Basket: 2 Trail mugs at 12.00 and 1 Field notebook at 16.00. Discount code WELCOME10 takes 10% off.

test("checkout shows the right amounts and places the order", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#subtotal")).toHaveText("40.00");
  await expect(page.locator("#discount")).toHaveText("-4.00");
  // BUSINESS RULE: tax is 20% of what the customer pays for the goods, after the discount. 36.00 x 20% = 7.20.
  await expect(page.locator("#tax")).toHaveText("7.20");
  await expect(page.locator("#total")).toHaveText("43.20");
  await page.getByRole("button", { name: "Place order" }).click();
  await expect(page.getByRole("heading", { name: "Order placed" })).toBeVisible();
  await expect(page.locator("#confirm-total")).toHaveText("43.20");
});

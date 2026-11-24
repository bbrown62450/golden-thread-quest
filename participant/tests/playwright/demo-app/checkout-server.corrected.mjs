// A small made-up checkout page: THE CORRECTED VERSION, for the playwright-repair-test quest.
//
// It is the redesigned checkout, checkout-server.mjs, with one thing put right. The redesign worked the tax out on the
// subtotal before the discount. The owner of the tax rule in this made-up shop, the participant, ruled that a bug. Here
// the tax is again 20% of what the customer pays for the goods, after the discount. Two lines differ from
// checkout-server.mjs, both in amounts(), and nothing else but these comments. checkout-server.mjs itself is left as it
// was approved in the earlier quest.
//
// CHANGE NOTE FOR THE REDESIGN (what its author says changed):
//   1. The button that places the order is now labelled "Buy now".
//   2. The summary is a description list, not a table. Its amounts are found by test id: summary-subtotal,
//      summary-discount, summary-tax, summary-total. On the confirmation: confirmation-reference, confirmation-total.
//   3. Amounts are shown with a currency sign.
//
// It runs on this computer only (127.0.0.1), keeps nothing, and every product, price and code in it is invented.
//
//   node demo-app/checkout-server.corrected.mjs      listens on CHECKOUT_PORT (default 4801)
//
//   GET  /          the checkout page: the basket, the discount, the tax, the total and a button to place the order
//   POST /order     places the order and shows the confirmation
//   GET  /healthz   "ok"
//
// FOR THE TEST HARNESS ONLY. CHECKOUT_FAULT switches on one deliberate fault, so that a check can see whether a test
// notices it. It is not part of the application, and no test sets it.
//   tax-left-out-of-total   the total leaves the tax out
//   tax-rate-wrong          tax is worked out at 25%
//   tax-shown-wrong         the tax figure shown is worked out at 25%. The total is right
//   discount-ignored        the discount is shown and not taken off
//   total-ignores-discount  the total adds the tax to the subtotal, without the discount
//   subtotal-wrong          a quantity of 2 is counted as 1
//   button-dead             placing the order shows the checkout page again
//   confirmation-wrong      the confirmation shows the subtotal where the total belongs

import { createServer } from "node:http";

const port = Number(process.env.CHECKOUT_PORT ?? 4801);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error("checkout-server: CHECKOUT_PORT must be a whole number from 1 to 65535.");
  process.exit(1);
}
const FAULTS = ["tax-left-out-of-total", "tax-rate-wrong", "tax-shown-wrong", "discount-ignored", "total-ignores-discount", "subtotal-wrong", "button-dead", "confirmation-wrong"];
const fault = process.env.CHECKOUT_FAULT || "";
if (fault && !FAULTS.includes(fault)) {
  console.error(`checkout-server: CHECKOUT_FAULT must be one of ${FAULTS.join(", ")}.`);
  process.exit(1);
}

const BASKET = [{ name: "Trail mug", each: 12, quantity: 2 }, { name: "Field notebook", each: 16, quantity: 1 }];
const DISCOUNT = { code: "WELCOME10", rate: 0.1 };
const TAX_RATE = 0.2;

function amounts() {
  const subtotal = BASKET.reduce((sum, line) => sum + line.each * (fault === "subtotal-wrong" ? 1 : line.quantity), 0);
  const discount = subtotal * DISCOUNT.rate;
  const goods = fault === "discount-ignored" ? subtotal : subtotal - discount;
  // BUSINESS RULE: tax is 20% of what the customer pays for the goods, after the discount.
  const tax = goods * (fault === "tax-rate-wrong" ? 0.25 : TAX_RATE);
  let total = goods + tax;
  if (fault === "tax-left-out-of-total") total = goods;
  if (fault === "total-ignores-discount") total = subtotal + tax;
  return { subtotal, discount, tax, shownTax: fault === "tax-shown-wrong" ? goods * 0.25 : tax, total };
}

const money = (value) => `${value < 0 ? "-" : ""}£${Math.abs(value).toFixed(2)}`;

function page(title, body) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${title}</title></head><body>${body}</body></html>`;
}

function checkoutPage() {
  const a = amounts();
  const lines = BASKET.map((line) => `<tr><td>${line.name}</td><td>${line.quantity}</td><td>${money(line.each * line.quantity)}</td></tr>`).join("");
  return page("Checkout", `<h1>Checkout</h1>
<table id="basket"><thead><tr><th>Item</th><th>Quantity</th><th>Price</th></tr></thead><tbody>${lines}</tbody></table>
<dl data-testid="order-summary">
<dt>Subtotal</dt><dd data-testid="summary-subtotal">${money(a.subtotal)}</dd>
<dt>Discount (${DISCOUNT.code})</dt><dd data-testid="summary-discount">${money(-a.discount)}</dd>
<dt>Tax</dt><dd data-testid="summary-tax">${money(a.shownTax)}</dd>
<dt>Total</dt><dd data-testid="summary-total">${money(a.total)}</dd>
</dl>
<form method="post" action="/order"><button type="submit">Buy now</button></form>`);
}

function confirmationPage() {
  const a = amounts();
  return page("Order placed", `<h1>Order placed</h1>
<p>Reference <span data-testid="confirmation-reference">DEMO-0001</span></p>
<p>Total charged <span data-testid="confirmation-total">${money(fault === "confirmation-wrong" ? a.subtotal : a.total)}</span></p>`);
}

createServer((request, response) => {
  const send = (status, body, type = "text/html; charset=utf-8") => {
    response.writeHead(status, { "content-type": type, "cache-control": "no-store" });
    response.end(body);
  };
  if (request.method === "GET" && request.url === "/healthz") return send(200, "ok", "text/plain");
  if (request.method === "GET" && request.url === "/") return send(200, checkoutPage());
  if (request.method === "POST" && request.url === "/order") {
    request.resume();
    return send(200, fault === "button-dead" ? checkoutPage() : confirmationPage());
  }
  return send(404, page("Not found", "<h1>Not found</h1>"));
}).listen(port, "127.0.0.1", () => console.log(`checkout-server: http://127.0.0.1:${port}${fault ? `, fault ${fault}` : ""}`));

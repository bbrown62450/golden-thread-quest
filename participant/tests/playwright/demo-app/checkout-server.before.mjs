// A small made-up checkout page for the playwright-maintenance-report quest. THIS IS THE VERSION BEFORE THE REDESIGN.
// The version in use is checkout-server.mjs. The difference between the two is needs-maintenance.app-change.diff,
// beside the test.
//
// It runs on this computer only (127.0.0.1), keeps nothing, and every product, price and code in it is invented.
//
//   node demo-app/checkout-server.before.mjs      listens on CHECKOUT_PORT (default 4801)
//
//   GET  /          the checkout page: the basket, the discount, the tax, the total and a button to place the order
//   POST /order     places the order and shows the confirmation
//   GET  /healthz   "ok"
//
// THE RULE FOR TAX, in this version: tax is 20% of what the customer pays for the goods, which is the subtotal
// with the discount taken off.
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
  const tax = goods * (fault === "tax-rate-wrong" ? 0.25 : TAX_RATE);
  let total = goods + tax;
  if (fault === "tax-left-out-of-total") total = goods;
  if (fault === "total-ignores-discount") total = subtotal + tax;
  return { subtotal, discount, tax, shownTax: fault === "tax-shown-wrong" ? goods * 0.25 : tax, total };
}

const money = (value) => value.toFixed(2);

function page(title, body) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${title}</title></head><body>${body}</body></html>`;
}

function checkoutPage() {
  const a = amounts();
  const lines = BASKET.map((line) => `<tr><td>${line.name}</td><td>${line.quantity}</td><td>${money(line.each * line.quantity)}</td></tr>`).join("");
  return page("Checkout", `<h1>Checkout</h1>
<table id="basket"><thead><tr><th>Item</th><th>Quantity</th><th>Price</th></tr></thead><tbody>${lines}</tbody></table>
<table id="summary">
<tr><th>Subtotal</th><td id="subtotal">${money(a.subtotal)}</td></tr>
<tr><th>Discount (${DISCOUNT.code})</th><td id="discount">-${money(a.discount)}</td></tr>
<tr><th>Tax</th><td id="tax">${money(a.shownTax)}</td></tr>
<tr><th>Total</th><td id="total">${money(a.total)}</td></tr>
</table>
<form method="post" action="/order"><button type="submit">Place order</button></form>`);
}

function confirmationPage() {
  const a = amounts();
  return page("Order placed", `<h1>Order placed</h1>
<p>Reference <span id="confirm-reference">DEMO-0001</span></p>
<p>Total charged <span id="confirm-total">${money(fault === "confirmation-wrong" ? a.subtotal : a.total)}</span></p>`);
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
}).listen(port, "127.0.0.1", () => console.log(`checkout-server (before the redesign): http://127.0.0.1:${port}${fault ? `, fault ${fault}` : ""}`));

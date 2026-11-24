// A small made-up application for the playwright-failure-triage quest: an order desk with a pricing service behind it.
//
// It exists so that tests can fail against it in different ways, for different reasons. It runs on this computer only
// (127.0.0.1), keeps everything in memory, and forgets it when it stops. Every order, customer and sign-in is invented.
//
//   node demo-app/triage-server.mjs      the order desk listens on TRIAGE_PORT (default 4797),
//                                        and its pricing service on TRIAGE_PRICING_PORT (default 4798)
//
// The order desk:
//   GET  /                       the sign-in form
//   POST /session                signs in. ANY name and any non-empty password are accepted. Sets the cookie demo_session
//   GET  /orders                 the list of orders
//   GET  /orders/ID              the page of one order. Its script asks for the summary and the lines at the same time
//   GET  /api/orders/ID          the order's summary, as JSON. Takes about 150 ms
//   GET  /api/orders/ID/lines    the order's lines, priced, with the total. It asks the pricing service for prices
//   GET  /static/promo.png       always 404. Every page asks for it. Harmless
//   GET  /healthz                "ok"
// The pricing service, a second listener in this same process, standing for another team's service:
//   GET  /prices                 the price list, as JSON
//
// FOR THE TEST HARNESS ONLY. These are not part of the application. They are how the check script arranges a failure
// whose cause is outside the application's code. They are not logged, and no test calls them.
//   POST /__harness/pricing?state=down|up    stops or starts the pricing service's listener
//   POST /__harness/stall?ms=N               the next request for an order's lines freezes this whole process for N ms
//
// THE FAULTS BUILT INTO THE APPLICATION, ON PURPOSE. The quest's ground-truth file says which test meets which.
//   1. TOTALLING. totalOf() skips a line whose quantity is 1. It should count every line.
//   2. A RACE IN THE PAGE. The page draws the total when the SUMMARY arrives, from whatever lines it has by then, and does
//      not draw it again when the lines arrive. If the lines come second, the total stays 0.00. Lines come second only
//      when pricing them takes longer than the summary, which happens now and then for an order with many lines.
// And one piece of bad data in the seed: order ord-2004 has a line with a quantity of -3. Refusing it is correct.

import { randomBytes } from "node:crypto";
import { appendFileSync, mkdirSync } from "node:fs";
import http, { createServer } from "node:http";
import { dirname } from "node:path";

const port = Number(process.env.TRIAGE_PORT ?? 4797);
const pricingPort = Number(process.env.TRIAGE_PRICING_PORT ?? 4798);
for (const [name, value] of [["TRIAGE_PORT", port], ["TRIAGE_PRICING_PORT", pricingPort]]) {
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    console.error(`triage-server: ${name} must be a whole number from 1 to 65535.`);
    process.exit(1);
  }
}
const logFile = process.env.TRIAGE_SERVER_LOG || "";
if (logFile) mkdirSync(dirname(logFile), { recursive: true });

const PRICES = { widget: 12.5, bracket: 3.2, gasket: 0.8, toolkit: 20, valve: 7.25, hose: 4.5 };
const many = (count) => Array.from({ length: count }, (_, index) => [["bracket", "gasket", "hose"][index % 3], 2 + (index % 4)]);
const SEED = [
  { id: "ord-2001", customer: "Fixture Freight Ltd", lines: [["widget", 8], ["toolkit", 1]] },
  { id: "ord-2002", customer: "Sample Supplies Co", lines: [["widget", 3]] },
  { id: "ord-2003", customer: "Example Engines Inc", lines: [["valve", 8], ["hose", 2]] },
  { id: "ord-2004", customer: "Placeholder Pumps Ltd", lines: [["widget", 2], ["bracket", -3]] },
  { id: "ord-2005", customer: "Specimen Shipping Co", lines: many(12) },
  { id: "ord-2006", customer: "Mock Motors Inc", lines: [["gasket", 20], ["hose", 4]] },
];
const ORDERS = new Map(SEED.map((order, index) => [order.id, { ...order, record: index + 1 }]));
const sessions = new Map();   // cookie value -> { name, pageCode }: pageCode is the made-up token the order page sends
let stallNextLinesFor = 0;    // set by the harness

const round = (amount) => Math.round(amount * 100) / 100;

// FAULT 1 is here: `quantity > 1` should be `quantity >= 1`.
function totalOf(lines) {
  let total = 0;
  for (const line of lines) {
    if (line.quantity > 1) total += line.amount;
  }
  return round(total);
}

function log(method, path, status, started, note) {
  const line = `${new Date().toISOString()} ${method} ${path} ${status} ${Date.now() - started}ms${note ? ` ${note}` : ""}`;
  console.log(line);
  if (logFile) appendFileSync(logFile, line + "\n", "utf8");
}

const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function page(title, body) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${escapeHtml(title)} · Made-up order desk</title>
<style>
  body { font: 16px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 40rem; padding: 0 1rem; color: #1c2430; }
  header { display: flex; align-items: center; gap: 1rem; border-bottom: 1px solid #c8d0da; padding-bottom: .5rem; }
  header img { width: 48px; height: 48px; }
  table { border-collapse: collapse; width: 100%; } th, td { text-align: left; padding: .3rem .6rem; border-bottom: 1px solid #e3e8ee; }
  label { display: block; margin: .6rem 0; } input { font: inherit; padding: .3rem; }
  button { font: inherit; padding: .4rem 1rem; }
  .muted { color: #5b6878; } .problem { color: #8a1f11; }
</style>
</head>
<body>
<header><img src="/static/promo.png" alt=""><strong>Made-up order desk</strong><span class="muted">a demo application. Nothing here is real</span></header>
<main>
<h1>${escapeHtml(title)}</h1>
${body}
</main>
</body>
</html>`;
}

function cookieOf(request) {
  const found = /(?:^|;\s*)demo_session=([0-9a-f]+)/.exec(request.headers.cookie ?? "");
  return found ? found[1] : "";
}

async function readBody(request) {
  const parts = [];
  let size = 0;
  for await (const part of request) {
    size += part.length;
    if (size > 10_000) throw new Error("too large");
    parts.push(part);
  }
  return Buffer.concat(parts).toString("utf8");
}

const wait = (ms) => new Promise((done) => setTimeout(done, ms));

/** Asks the pricing service for the price list. Rejects with the connection's own error if it cannot be reached. */
function fetchPrices() {
  return new Promise((resolve, reject) => {
    const request = http.get({ host: "127.0.0.1", port: pricingPort, path: "/prices", timeout: 1000 }, (answer) => {
      const parts = [];
      answer.on("data", (part) => parts.push(part));
      answer.on("end", () => {
        try {
          resolve(JSON.parse(Buffer.concat(parts).toString("utf8")));
        } catch (error) {
          reject(error);
        }
      });
    });
    request.on("timeout", () => request.destroy(new Error("timed out after 1000 ms")));
    request.on("error", reject);
  });
}

// ---------------------------------------------------------------- the pricing service

const pricing = createServer((request, response) => {
  if (request.url === "/prices") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify(PRICES));
  } else {
    response.writeHead(404, { "content-type": "text/plain" });
    response.end("not found");
  }
});
const pricingUp = () => new Promise((done) => (pricing.listening ? done() : pricing.listen(pricingPort, "127.0.0.1", done)));
const pricingDown = () => new Promise((done) => {
  if (!pricing.listening) return done();
  pricing.close(done);
  pricing.closeAllConnections();
});

// ---------------------------------------------------------------- the order desk

const server = createServer(async (request, response) => {
  const started = Date.now();
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const path = url.pathname;
  const method = request.method ?? "GET";
  const send = (status, type, body, headers = {}) => {
    response.writeHead(status, { "content-type": type, "cache-control": "no-store", ...headers });
    response.end(body);
  };
  const done = (status, type, body, note, headers) => {
    send(status, type, body, headers);
    log(method, path, status, started, note);
  };
  const json = (status, body, note) => done(status, "application/json", JSON.stringify(body), note);
  try {
    if (method === "GET" && path === "/healthz") return send(200, "text/plain", "ok");
    if (method === "POST" && path.startsWith("/__harness/")) {            // the test harness. Not logged
      if (path === "/__harness/pricing") await (url.searchParams.get("state") === "down" ? pricingDown() : pricingUp());
      else if (path === "/__harness/stall") stallNextLinesFor = Math.max(0, Math.min(10_000, Number(url.searchParams.get("ms")) || 0));
      else return send(404, "text/plain", "no such harness switch");
      return send(200, "application/json", JSON.stringify({ pricing: pricing.listening ? "up" : "down", stallNextLinesFor }));
    }
    if (method === "GET" && path === "/static/promo.png") return done(404, "text/plain", "not found", "no such file");
    if (method === "GET" && path === "/") {
      return done(200, "text/html; charset=utf-8", page("Sign in", `
<form method="post" action="/session">
  <label>Name <input name="name" autocomplete="off" required></label>
  <label>Password <input name="password" type="password" autocomplete="off" required></label>
  <button type="submit">Sign in</button>
</form>`));
    }
    if (method === "POST" && path === "/session") {
      const form = new URLSearchParams(await readBody(request));
      const name = (form.get("name") ?? "").trim().slice(0, 60);
      if (!name || !form.get("password")) return done(400, "text/plain", "a name and a password are needed", "sign-in refused: a field was empty");
      const cookie = randomBytes(16).toString("hex");
      sessions.set(cookie, { name, pageCode: randomBytes(20).toString("hex") });
      return done(303, "text/plain", "signed in", "signed in", { location: "/orders", "set-cookie": `demo_session=${cookie}; Path=/; HttpOnly; SameSite=Lax` });
    }
    const session = sessions.get(cookieOf(request));
    if (method === "GET" && path === "/orders") {
      if (!session) return done(303, "text/plain", "sign in first", "not signed in", { location: "/" });
      const rows = [...ORDERS.values()].map((order) => `<tr><td><a href="/orders/${order.id}">${order.id}</a></td><td>${escapeHtml(order.customer)}</td><td>${order.lines.length}</td></tr>`).join("\n");
      return done(200, "text/html; charset=utf-8", page("Orders", `
<p>Signed in as <strong data-testid="who">${escapeHtml(session.name)}</strong>.</p>
<table><thead><tr><th>Order</th><th>Customer</th><th>Lines</th></tr></thead><tbody>
${rows}
</tbody></table>`));
    }
    const orderPage = /^\/orders\/(ord-\d+)$/.exec(path);
    if (method === "GET" && orderPage) {
      if (!session) return done(303, "text/plain", "sign in first", "not signed in", { location: "/" });
      const id = orderPage[1];
      const pageCode = session.pageCode;
      // FAULT 2 is in this script: showSummary() draws the total, and showLines() does not draw it again.
      return done(200, "text/html; charset=utf-8", page(`Order ${id}`, `
<p><a href="/orders">All orders</a></p>
<p data-testid="customer">Customer: loading…</p>
<p data-testid="total">Order total: loading…</p>
<div data-testid="lines"><p>Loading lines…</p></div>
<p data-testid="problem" class="problem" hidden></p>
<script>
  const apiToken = "${pageCode}";
  const state = { total: 0, failed: false };
  const ask = (path) => fetch(path, { headers: { Authorization: "Bearer " + apiToken } });
  const find = (name) => document.querySelector("[data-testid='" + name + "']");

  function showProblem(text) {
    state.failed = true;
    find("problem").hidden = false;
    find("problem").textContent = text;
    find("total").textContent = "Order total: unavailable";
    find("lines").innerHTML = "";
  }

  function showSummary(summary) {
    if (state.failed) return;
    find("customer").textContent = "Customer: " + summary.customer;
    find("total").textContent = "Order total: " + state.total.toFixed(2);
  }

  function showLines(answer) {
    if (state.failed) return;
    state.total = answer.total;
    const rows = answer.lines.map((line) => "<tr><td>" + line.item + "</td><td>" + line.quantity + "</td><td>" + line.amount.toFixed(2) + "</td></tr>").join("");
    find("lines").innerHTML = "<table><thead><tr><th>Item</th><th>Quantity</th><th>Amount</th></tr></thead><tbody>" + rows + "</tbody></table>";
  }

  async function load(path, show) {
    const answer = await ask(path);
    if (!answer.ok) {
      const body = await answer.json().catch(() => ({}));
      console.error("order page: " + path + " answered " + answer.status + " " + (body.error || ""));
      showProblem(body.message || "This order could not be loaded.");
      return;
    }
    show(await answer.json());
  }

  load("/api/orders/${id}", showSummary);
  load("/api/orders/${id}/lines", showLines);
</script>`));
    }
    const api = /^\/api\/orders\/(ord-\d+)(\/lines)?$/.exec(path);
    if (method === "GET" && api) {
      if (!session) return json(401, { error: "not_signed_in" }, "no session");
      if ((request.headers.authorization ?? "") !== `Bearer ${session.pageCode}`) return json(401, { error: "bad_token" }, "the token did not match the session");
      const order = ORDERS.get(api[1]);
      if (!order) return json(404, { error: "no_such_order", message: "There is no such order." }, "no such order");
      if (!api[2]) {
        await wait(150);
        return json(200, { id: order.id, customer: order.customer, lineCount: order.lines.length });
      }
      if (stallNextLinesFor > 0) {                                           // ordered by the harness: this whole process freezes
        const until = Date.now() + stallNextLinesFor;
        stallNextLinesFor = 0;
        while (Date.now() < until) { /* nothing else in this process can run */ }
      }
      const bad = order.lines.findIndex(([, quantity]) => !Number.isInteger(quantity) || quantity < 1);
      if (bad >= 0) {
        return json(422, { error: "invalid_order_data", order: order.id, line: bad + 1, quantity: order.lines[bad][1],
          message: `This order cannot be priced: line ${bad + 1} has a quantity of ${order.lines[bad][1]}. A quantity must be 1 or more.`, source: `seed data, record ${order.record}` },
          `REFUSED invalid order data: ${order.id} line ${bad + 1} has quantity ${order.lines[bad][1]} (seed data, record ${order.record})`);
      }
      let prices;
      try {
        prices = await fetchPrices();
      } catch (error) {
        const reason = error instanceof Error ? error.message : "unknown";
        return json(503, { error: "pricing_unavailable", message: "Prices are unavailable right now. Try again later.", detail: `could not reach the pricing service at 127.0.0.1:${pricingPort}: ${reason}` },
          `ERROR pricing service unreachable at 127.0.0.1:${pricingPort}: ${reason}`);
      }
      // Pricing takes a little time for each line. For an order with many lines it varies, and can outlast the summary.
      await wait(order.lines.length >= 10 ? 30 + Math.random() * 180 : 5 * order.lines.length);
      const lines = order.lines.map(([item, quantity]) => ({ item, quantity, amount: round(prices[item] * quantity) }));
      return json(200, { id: order.id, lines, total: totalOf(lines) }, `priced ${lines.length} lines`);
    }
    return done(404, "text/plain", "not found", "no such path");
  } catch (error) {
    return done(500, "text/plain", "the demo application failed", `ERROR unexpected: ${error instanceof Error ? error.message : "unknown"}`);
  }
});

await pricingUp();
server.listen(port, "127.0.0.1", () => {
  const line = `${new Date().toISOString()} triage-server: order desk on http://127.0.0.1:${port}, pricing service on 127.0.0.1:${pricingPort}`;
  console.log(line);
  if (logFile) appendFileSync(logFile, line + "\n", "utf8");
});

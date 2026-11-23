// A small made-up application for the playwright-failure-evidence quest: an order desk.
//
// It exists so that a test has something to fail against, and so that a failure leaves things
// worth capturing: a request that went wrong, a line in the browser's console, and a session
// cookie and a token that must NOT end up in the evidence. It runs on this computer only
// (127.0.0.1), keeps everything in memory, and forgets it when it stops. Every order, customer
// and sign-in in it is invented.
//
//   node demo-app/orders-server.mjs      listens on ORDERS_PORT, default 4794
//
// What it does:
//   GET  /                   the sign-in form
//   POST /session            signs in. ANY name and any non-empty password are accepted: it is a
//                            demo. Sets the cookie demo_session and redirects to /orders
//   GET  /orders             the list of orders. Needs the cookie
//   GET  /orders/ID          the page of one order. Its script asks /api/orders/ID for the lines
//                            and the total, sending the token the page was given
//   GET  /api/orders/ID      the order as JSON. Needs the cookie AND "Authorization: Bearer TOKEN"
//   GET  /static/promo.png   always 404. See below
//   GET  /healthz            "ok"
//
// TWO FAULTS ARE BUILT IN, ON PURPOSE
//   1. Order ord-1003 is for a region that has no price list. /api/orders/ord-1003 answers 500.
//   2. The order page does not handle that. Its script writes an error to the browser's console
//      and leaves "Loading order…" on the screen for ever. It shows the person nothing.
//   So a test that waits for the total of ord-1003 fails with a bare timeout, and nothing on the
//   screen says why. That is the quest's scenario.
//
// AND ONE THING THAT LOOKS LIKE A FAULT AND IS NOT
//   Every page asks for /static/promo.png, which does not exist, so every page has one 404. It is
//   harmless and it is there on pages that work. A diagnosis has to tell it from the real fault.
//
// THE MADE-UP SECRETS
//   The session cookie and the token are random, made when a person signs in, and worth nothing:
//   they open only this application, on this computer, until it stops. They stand for the real
//   ones a real application would have. Nothing here writes them to the log.
//
// THE LOG
//   One line per request, to standard output, and also to the file named by ORDERS_SERVER_LOG if
//   that is set: the time, the method, the path, the status, how long it took, and a note.

import { randomBytes } from "node:crypto";
import { appendFileSync, mkdirSync } from "node:fs";
import { createServer } from "node:http";
import { dirname } from "node:path";

const port = Number(process.env.ORDERS_PORT ?? 4794);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error(`orders-server: ORDERS_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.ORDERS_PORT)}.`);
  process.exit(1);
}
const logFile = process.env.ORDERS_SERVER_LOG || "";
if (logFile) mkdirSync(dirname(logFile), { recursive: true });

const PRICES = { "north-1": { widget: 12.5, bracket: 3.2, gasket: 0.8 } };   // there is no price list for north-2
const ORDERS = new Map([
  ["ord-1001", { id: "ord-1001", customer: "Fixture Freight Ltd", region: "north-1", lines: [["widget", 8], ["gasket", 25]] }],
  ["ord-1002", { id: "ord-1002", customer: "Sample Supplies Co", region: "north-1", lines: [["bracket", 40]] }],
  ["ord-1003", { id: "ord-1003", customer: "Example Engines Inc", region: "north-2", lines: [["widget", 3], ["bracket", 12]] }],
]);
const sessions = new Map();   // cookie value -> { name, pageCode }: pageCode is the made-up token the order page sends

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
  .muted { color: #5b6878; }
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

function send(response, status, type, body, headers = {}) {
  response.writeHead(status, { "content-type": type, "cache-control": "no-store", ...headers });
  response.end(body);
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

const server = createServer(async (request, response) => {
  const started = Date.now();
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const path = url.pathname;
  const method = request.method ?? "GET";
  const done = (status, type, body, note, headers) => {
    send(response, status, type, body, headers);
    if (path !== "/healthz") log(method, path, status, started, note);
  };
  try {
    if (method === "GET" && path === "/healthz") return done(200, "text/plain", "ok");
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
      const rows = [...ORDERS.values()].map((order) => `<tr><td><a href="/orders/${order.id}">${order.id}</a></td><td>${escapeHtml(order.customer)}</td><td>${order.region}</td></tr>`).join("\n");
      return done(200, "text/html; charset=utf-8", page("Orders", `
<p>Signed in as <strong data-testid="who">${escapeHtml(session.name)}</strong>.</p>
<table><thead><tr><th>Order</th><th>Customer</th><th>Region</th></tr></thead><tbody>
${rows}
</tbody></table>`));
    }
    const orderPage = /^\/orders\/(ord-\d+)$/.exec(path);
    if (method === "GET" && orderPage) {
      if (!session) return done(303, "text/plain", "sign in first", "not signed in", { location: "/" });
      const id = orderPage[1];
      const pageCode = session.pageCode;
      // FAULT 2 is in this script: when the answer is not OK it writes to the console and returns, and the page stays on "Loading order…".
      return done(200, "text/html; charset=utf-8", page(`Order ${id}`, `
<p><a href="/orders">All orders</a></p>
<div id="order" data-testid="order"><p data-testid="loading">Loading order…</p></div>
<script>
  const apiToken = "${pageCode}";
  async function loadOrder() {
    console.info("order page: asking for ${id}");
    const answer = await fetch("/api/orders/${id}", { headers: { Authorization: "Bearer " + apiToken } });
    if (!answer.ok) {
      console.error("order page: could not load ${id}. The server answered " + answer.status + " " + (await answer.text()));
      return;
    }
    const order = await answer.json();
    const rows = order.lines.map((line) => "<tr><td>" + line.item + "</td><td>" + line.quantity + "</td><td>" + line.amount.toFixed(2) + "</td></tr>").join("");
    document.getElementById("order").innerHTML =
      "<p>Customer: <strong>" + order.customer + "</strong></p>" +
      "<table><thead><tr><th>Item</th><th>Quantity</th><th>Amount</th></tr></thead><tbody>" + rows + "</tbody></table>" +
      "<p data-testid='total'>Order total: <strong>" + order.total.toFixed(2) + "</strong></p>";
    console.info("order page: showed ${id}");
  }
  loadOrder();
</script>`));
    }
    const orderApi = /^\/api\/orders\/(ord-\d+)$/.exec(path);
    if (method === "GET" && orderApi) {
      if (!session) return done(401, "application/json", JSON.stringify({ error: "not_signed_in" }), "no session");
      if ((request.headers.authorization ?? "") !== `Bearer ${session.pageCode}`) return done(401, "application/json", JSON.stringify({ error: "bad_token" }), "the token did not match the session");
      const order = ORDERS.get(orderApi[1]);
      if (!order) return done(404, "application/json", JSON.stringify({ error: "no_such_order" }), "no such order");
      const prices = PRICES[order.region];
      // FAULT 1: no price list for the order's region.
      if (!prices) {
        return done(500, "application/json", JSON.stringify({ error: "price_list_unavailable", detail: `no price list for region ${order.region}`, order: order.id }),
          `ERROR price_list_unavailable: no price list for region ${order.region}, needed by ${order.id}`);
      }
      const lines = order.lines.map(([item, quantity]) => ({ item, quantity, amount: Math.round(prices[item] * quantity * 100) / 100 }));
      const total = Math.round(lines.reduce((sum, line) => sum + line.amount, 0) * 100) / 100;
      return done(200, "application/json", JSON.stringify({ id: order.id, customer: order.customer, region: order.region, lines, total }), `priced ${lines.length} lines`);
    }
    return done(404, "text/plain", "not found", "no such path");
  } catch (error) {
    return done(500, "text/plain", "the demo application failed", `ERROR unexpected: ${error instanceof Error ? error.message : "unknown"}`);
  }
});

server.listen(port, "127.0.0.1", () => {
  const line = `${new Date().toISOString()} orders-server: listening on http://127.0.0.1:${port}`;
  console.log(line);
  if (logFile) appendFileSync(logFile, line + "\n", "utf8");
});

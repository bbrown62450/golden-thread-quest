// A small made-up application for the playwright-data-isolation quest: a customer directory.
//
// It exists so that tests have somewhere to create and remove data, and so that two tests can
// get in each other's way. It runs on this computer only (127.0.0.1), keeps its data in memory,
// and forgets everything when it stops. Every customer in it is invented.
//
//   node demo-app/server.mjs            listens on DEMO_PORT, default 4793
//
// What it does:
//   GET  /                      the page: a table of customers, a form to add one
//   POST /customers             the form's target. Redirects to /?added=ID
//   POST /customers/ID/upgrade  the "Upgrade" button. Sets the plan to plus
//   POST /customers/ID/remove   the "Remove" button
//   GET  /api/customers         every customer, as JSON
//   POST /api/customers         {name, plan} -> 201 with the new customer, id included
//   DELETE /api/customers/ID    204, or 404 if there is no such customer
//   GET  /api/stats             how many customers were created and removed since it started
//   GET  /healthz               "ok"
//
// Two rules matter to the tests. A customer's name must be unique: a second customer with a
// name already in use is refused with 409. And there is no "reset" or "delete all": the only
// way to remove a customer is by its id.
//
// It starts with four customers. They stand for data that was there before any test ran.

import { randomUUID } from "node:crypto";
import { createServer } from "node:http";

const port = Number(process.env.DEMO_PORT ?? 4793);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error(`demo-app: DEMO_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.DEMO_PORT)}.`);
  process.exit(1);
}

const PLANS = ["basic", "plus"];
const stats = { created: 0, removed: 0 };   // since the application started. The four below are not counted
const customers = new Map();
for (const [id, name, plan] of [
  ["seed-1", "Asha Verma", "plus"],
  ["seed-2", "Bo Lindqvist", "basic"],
  ["seed-3", "Carmen Ortiz", "basic"],
  ["seed-4", "Test Userson", "plus"],          // a real-looking customer whose name starts with "Test"
]) {
  customers.set(id, { id, name, plan });
}

const escapeHtml = (text) =>
  String(text).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

function nameProblem(name) {
  if (typeof name !== "string" || !name.trim()) return "A customer needs a name.";
  if (name.trim().length > 120) return "A name can be at most 120 characters.";
  return null;
}

function add(name, plan) {
  const problem = nameProblem(name);
  if (problem) return { status: 400, error: problem };
  if (!PLANS.includes(plan)) return { status: 400, error: "The plan must be basic or plus." };
  const clean = name.trim();
  for (const existing of customers.values()) {
    if (existing.name.toLowerCase() === clean.toLowerCase()) {
      return { status: 409, error: `A customer called ${clean} already exists.` };
    }
  }
  const customer = { id: randomUUID(), name: clean, plan };
  customers.set(customer.id, customer);
  stats.created += 1;
  return { status: 201, customer };
}

function page({ status = "", statusId = "", alert = "" } = {}) {
  const rows = [...customers.values()]
    .map(
      (one) => `      <tr data-customer-id="${escapeHtml(one.id)}">
        <td>${escapeHtml(one.name)}</td>
        <td>${escapeHtml(one.plan)}</td>
        <td>
          <form method="post" action="/customers/${encodeURIComponent(one.id)}/upgrade"><button aria-label="Upgrade ${escapeHtml(one.name)}">Upgrade</button></form>
          <form method="post" action="/customers/${encodeURIComponent(one.id)}/remove"><button aria-label="Remove ${escapeHtml(one.name)}">Remove</button></form>
        </td>
      </tr>`,
    )
    .join("\n");
  return `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Customer directory (made-up)</title>
<style>body{font:16px/1.5 system-ui,sans-serif;margin:2rem;max-width:50rem}td,th{padding:.25rem .75rem;text-align:left}form{display:inline}</style></head>
<body>
  <h1>Customer directory</h1>
  <p>A made-up application for a testing exercise. Nobody in it is real.</p>
  ${status ? `<p role="status" data-customer-id="${escapeHtml(statusId)}">${escapeHtml(status)}</p>` : ""}
  ${alert ? `<p role="alert">${escapeHtml(alert)}</p>` : ""}
  <table>
    <caption>Customers: ${customers.size}</caption>
    <thead><tr><th>Name</th><th>Plan</th><th>Actions</th></tr></thead>
    <tbody>
${rows}
    </tbody>
  </table>
  <h2>Add a customer</h2>
  <form method="post" action="/customers">
    <label>Name <input name="name" required maxlength="120"></label>
    <label>Plan <select name="plan"><option>basic</option><option>plus</option></select></label>
    <button>Add customer</button>
  </form>
</body>
</html>
`;
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    let text = "";
    request.on("data", (chunk) => {
      text += chunk;
      if (text.length > 10_000) reject(new Error("too large"));
    });
    request.on("end", () => resolve(text));
    request.on("error", reject);
  });
}

function send(response, status, body, type = "text/html; charset=utf-8", headers = {}) {
  response.writeHead(status, { "content-type": type, "cache-control": "no-store", ...headers });
  response.end(body);
}

const sendJson = (response, status, value) => send(response, status, value === undefined ? "" : JSON.stringify(value), "application/json; charset=utf-8");

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://127.0.0.1:${port}`);
    const parts = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
    const method = request.method;

    if (method === "GET" && url.pathname === "/healthz") return send(response, 200, "ok", "text/plain; charset=utf-8");

    if (method === "GET" && url.pathname === "/") {
      const added = customers.get(url.searchParams.get("added") ?? "");
      return send(response, 200, page(added ? { status: `Added ${added.name}.`, statusId: added.id } : {}));
    }

    if (method === "GET" && url.pathname === "/api/customers") return sendJson(response, 200, [...customers.values()]);

    if (method === "GET" && url.pathname === "/api/stats") return sendJson(response, 200, stats);

    if (method === "POST" && url.pathname === "/api/customers") {
      let wanted;
      try {
        wanted = JSON.parse(await readBody(request));
      } catch {
        return sendJson(response, 400, { error: "The request must be JSON." });
      }
      const result = add(wanted?.name, wanted?.plan ?? "basic");
      return sendJson(response, result.status, result.customer ?? { error: result.error });
    }

    if (method === "DELETE" && parts.length === 3 && parts[0] === "api" && parts[1] === "customers") {
      if (!customers.delete(parts[2])) return sendJson(response, 404, { error: "There is no such customer." });
      stats.removed += 1;
      return send(response, 204, "");
    }

    if (method === "POST" && url.pathname === "/customers") {
      const form = new URLSearchParams(await readBody(request));
      const result = add(form.get("name"), form.get("plan") ?? "basic");
      if (result.customer) return send(response, 303, "", "text/plain", { location: `/?added=${encodeURIComponent(result.customer.id)}` });
      return send(response, result.status, page({ alert: result.error }));
    }

    if (method === "POST" && parts.length === 3 && parts[0] === "customers" && ["upgrade", "remove"].includes(parts[2])) {
      const customer = customers.get(parts[1]);
      if (!customer) return send(response, 404, page({ alert: "There is no such customer." }));
      if (parts[2] === "upgrade") customer.plan = "plus";
      else {
        customers.delete(customer.id);
        stats.removed += 1;
      }
      return send(response, 303, "", "text/plain", { location: "/" });
    }

    return send(response, 404, "Not found", "text/plain; charset=utf-8");
  } catch (error) {
    return send(response, 500, "The demo application failed.", "text/plain; charset=utf-8");
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`demo-app: customer directory on http://127.0.0.1:${port}/ with ${customers.size} customers. Made-up data, kept in memory.`);
});

/*
 * The check for the playwright-failure-evidence quest. It produces three logs:
 *
 *   logs/capture-check.txt     a test failing on purpose, and what its failure bundle holds
 *   logs/passing-run.txt       a test passing, what it kept, and old evidence being deleted
 *   logs/redaction-check.txt   the scan of the bundle for secrets, and planted fake values being found
 *
 * Run it from participant/tests/playwright, with Node 22.18 or later:
 *
 *   node tools/failure-evidence-check.ts                 check everything. The handed-in bundle is read, not changed
 *   node tools/failure-evidence-check.ts --save-bundle   also replace the handed-in bundle with the one this run made
 *
 * It starts the made-up order desk (demo-app/orders-server.mjs) on this computer, runs the tests
 * in failure-evidence.spec.ts against it with evidence.config.ts, and stops it. It contacts
 * nothing else. Everything a run writes goes to a scratch folder that is deleted at the end.
 *
 * What it tests, and how:
 *
 *   - THE BUNDLE HOLDS WHAT IT SHOULD. Not "the files exist": each one is opened. The trace must
 *     be a zip with steps and page snapshots in it. The screenshot must be a PNG with a size.
 *     The console log, the failed requests and the server log must each hold the line about the
 *     request that went wrong. Each file's checksum must be the one bundle.json gives.
 *   - A PASSING TEST KEEPS ONE LINE. Every file the passing run left anywhere is listed, with its
 *     size. There must be no bundle, no trace and no screenshot.
 *   - OLD EVIDENCE IS DELETED. A bundle a day past its date, one a day short of it, and a folder
 *     that is not a bundle are put in place. After a run, only the first must be gone.
 *   - THE SCAN. It opens every file of the bundle, and every entry inside trace.zip, and looks
 *     line by line for the shapes secrets have: an Authorization header, a bearer token, a cookie
 *     with a value, a password field, a token assigned to a name, a private key, and the shapes
 *     of some well-known keys. It also looks for this computer's own folder, user and machine
 *     names. It does NOT know the secret values of the run: it is written apart from the code
 *     that removes them (support/evidence.ts), so that one can catch the other's mistakes.
 *   - THE SCAN CAN FAIL. A scan that could only say "none" would prove nothing. So:
 *       1. the same failing test is run with redaction turned OFF, into the scratch folder. The
 *          scan must find secrets in that bundle;
 *       2. fake values, made up when this script runs, are planted at known lines of a copy of the
 *          bundle, in plain files and inside the trace. The scan must find each one, at that file
 *          and that line, and nothing else.
 *   - THE REPORT NEVER SHOWS A VALUE. A finding is a file, a line number and a kind. It has no
 *     field for the value. The log is checked for every planted value all the same.
 *
 * What it cannot test: screenshot.png is a picture. A scan cannot read it. It is listed as "not
 * searched" and has to be looked at by a person.
 *
 * It ends with exit code 0 only if every check came out as expected.
 */

import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir, hostname, tmpdir, userInfo } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { looksBinary, readZip, writeZip } from "../support/zip.ts";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-failure-evidence", "playwright-attempt-003");
// tools/failure-evidence-planted-faults.ts points these elsewhere, so that its runs do not replace the real logs or bundle.
const LOGS = process.env.GTQ_CHECK_LOGS ?? join(ATTEMPT, "logs");
const HANDED_IN = process.env.GTQ_CHECK_BUNDLE ?? join(ATTEMPT, "failure-bundle");
const SAVE = process.argv.includes("--save-bundle");
const PORT = Number(process.env.ORDERS_PORT ?? 4794);
const BASE = `http://127.0.0.1:${PORT}`;
const SCRATCH = mkdtempSync(join(tmpdir(), "gtq-failure-evidence-"));

const PASSING = "the total of order ord-1001 is shown";
const FAILING = "FAILS ON PURPOSE: the total of order ord-1003 is shown";
const KEEP_DAYS = 14;
// The password the tests type, chosen here so that this script can look for exactly it afterwards. It is made up, and the
// application accepts any password. It is never written to a log.
const CANARY = `pw-canary-${randomBytes(10).toString("hex")}`;
const DAY = 86_400_000;

// ---------------------------------------------------------------- the logs

class Log {
  lines: string[];
  problems: string[];

  constructor(title: string) {
    this.lines = [title, "Recorded by tools/failure-evidence-check.ts. The application is a made-up order desk on this computer. Nothing in it is real."];
    this.problems = [];
  }

  out(...texts: string[]): void {
    this.lines.push(...(texts.length ? texts : [""]));
  }

  part(text: string): void {
    this.lines.push("", "=".repeat(78), text);
  }

  block(command: string, text: string, code: number): void {
    this.lines.push(`$ ${command}`, "-".repeat(78), text.trimEnd(), "-".repeat(78), `exit code: ${code}`);
  }

  check(label: string, ok: boolean): void {
    this.lines.push(`  ${ok ? "ok  " : "FAIL"} ${label}`);
    if (!ok) this.problems.push(label);
  }

  text(): string {
    return this.lines.join("\n");
  }

  save(name: string): boolean {
    const count = this.lines.filter((line) => /^ {2}(ok {2}|FAIL) /.test(line)).length;
    this.lines.push("", `RESULT: ${this.problems.length ? `${this.problems.length} OF ${count} CHECKS FAILED.` : `ALL CHECKS PASSED. ${count} checks.`}`);
    mkdirSync(LOGS, { recursive: true });
    writeFileSync(join(LOGS, name), this.lines.join("\n") + "\n", "utf8");
    console.log(`${name}: ${this.lines[this.lines.length - 1]}`);
    for (const problem of this.problems) console.log(`  FAILED: ${problem}`);
    return this.problems.length === 0;
  }
}

/** What Playwright printed, without colour codes, Node's own warnings, or this computer's folder names. */
function tidy(text: string): string {
  return text
    .replace(/\u001b\[[0-9;]*m/g, "")
    .split("\n")
    .filter((line) => !/Warning: |--trace-warnings|ExperimentalWarning/.test(line))
    .join("\n")
    .split(SCRATCH).join("SCRATCH")
    .split(REPO).join("REPO")
    .split(homedir()).join("HOME")
    .replace(/\n{3,}/g, "\n\n");
}

const sha256 = (data: Buffer): string => createHash("sha256").update(data).digest("hex");

function listFiles(folder: string): string[] {
  if (!existsSync(folder)) return [];
  const found: string[] = [];
  for (const entry of readdirSync(folder, { withFileTypes: true })) {
    const full = join(folder, entry.name);
    if (entry.isDirectory()) found.push(...listFiles(full));
    else found.push(full);
  }
  return found.sort();
}

// ---------------------------------------------------------------- the application and the tests

async function reachable(): Promise<boolean> {
  try {
    return (await fetch(`${BASE}/healthz`)).ok;
  } catch {
    return false;
  }
}

const SERVER_LOG = join(SCRATCH, "orders-server.log");

async function startApp(): Promise<ChildProcess> {
  if (await reachable()) throw new Error(`something is already listening on port ${PORT}. Stop it, or set ORDERS_PORT to a free port.`);
  const child = spawn(process.execPath, ["demo-app/orders-server.mjs"], { cwd: TESTS, env: { ...process.env, ORDERS_PORT: String(PORT), ORDERS_SERVER_LOG: SERVER_LOG }, stdio: "ignore" });
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (await reachable()) return child;
    await new Promise((done) => setTimeout(done, 100));
  }
  child.kill();
  throw new Error("the demo application did not start");
}

async function stopApp(child: ChildProcess): Promise<void> {
  await new Promise<void>((done) => {
    child.once("exit", () => done());
    child.kill();
  });
}

type Run = { code: number; output: string; command: string };

/** One Playwright run of one test, by its exact title. Bundles go to `bundles`, Playwright's own scratch output to `output`. */
function runTest(title: string, bundles: string, output: string, redact = true): Run {
  const exact = ` ${title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`;      // the whole title, as Playwright prints it after the file's name
  const done = spawnSync(process.execPath, [CLI, "test", "--config", "evidence.config.ts", "--output", output, "-g", exact], {
    cwd: TESTS,
    env: { ...process.env, ORDERS_PORT: String(PORT), ORDERS_SERVER_LOG: SERVER_LOG, GTQ_BUNDLES_DIR: bundles, GTQ_EVIDENCE_REDACT: redact ? "on" : "off", GTQ_CANARY_PASSWORD: CANARY, FORCE_COLOR: "0", CI: "" },
    encoding: "utf8",
  });
  return {
    code: done.status ?? 1,
    output: tidy(`${done.stdout}${done.stderr}`),
    command: `${redact ? "" : "GTQ_EVIDENCE_REDACT=off "}npx playwright test --config evidence.config.ts -g ${JSON.stringify(title)}`,
  };
}

const bundleFolders = (bundles: string): string[] =>
  existsSync(bundles) ? readdirSync(bundles, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => join(bundles, entry.name)).sort() : [];

// ---------------------------------------------------------------- the scan

type Finding = { file: string; line: number; kind: string };          // there is no field for the value, on purpose
type Scan = { searched: string[]; notSearched: string[]; findings: Finding[] };

const Q = String.raw`(?:\\?["'])?`;       // an optional quote, which inside a JSON string is written with a backslash
const NOT_DONE = String.raw`(?!\[REDACTED)`;
const SHAPES: [string, RegExp][] = [
  ["authorization header with a value", new RegExp(String.raw`authorization${Q}\s*[:=,]\s*(?:"value"\s*:\s*)?${Q}${NOT_DONE}(?:Bearer|Basic|Token)\s+${NOT_DONE}[A-Za-z0-9._~+/=-]{8,}`, "i")],
  ["bearer token", new RegExp(String.raw`\bBearer\s+${NOT_DONE}[A-Za-z0-9._~+/=-]{16,}`)],
  ["cookie with a value", new RegExp(String.raw`\b(?:set-)?cookie${Q}\s*[:=,]\s*(?:"value"\s*:\s*)?${Q}${NOT_DONE}[^"'\s;=]+=${NOT_DONE}[^"'\s;]{6,}`, "i")],
  ["cookie with a value", new RegExp(String.raw`"cookies":\[(?:[^\]]|\[REDACTED [^\]]*\])*"value":"${NOT_DONE}[^"]`)],       // a trace's own list of a request's cookies
  ["session cookie", new RegExp(String.raw`\b[a-z0-9_]*sess(?:ion)?[a-z0-9_]*=${NOT_DONE}[A-Za-z0-9%._-]{8,}`, "i")],
  ["password with a value", new RegExp(String.raw`\bpass(?:word|wd)${Q}\s*[:=]\s*${Q}${NOT_DONE}[^\s"'&,;\\]{6,}`, "i")],
  ["password with a value", new RegExp(String.raw`"name":"[^"]*pass(?:word|wd)[^"]*","value":"${NOT_DONE}[^"]`, "i")],          // a form field, as a trace writes it
  ["token or key assigned to a name", new RegExp(String.raw`\b(?:api[_-]?token|access[_-]?token|auth[_-]?token|api[_-]?key|client[_-]?secret|secret)${Q}\s*[:=]\s*${Q}${NOT_DONE}[A-Za-z0-9._~+/=-]{16,}`, "i")],
  ["private key", /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
  ["well-known key shape", /\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})/],
];
const OWN_NAMES = [homedir(), userInfo().username, hostname()].filter((name) => name.length >= 4);

function scanText(name: string, text: string, findings: Finding[]): void {
  text.split("\n").forEach((line, index) => {
    const kinds = new Set(SHAPES.filter(([, shape]) => shape.test(line)).map(([kind]) => kind));
    for (const kind of kinds) findings.push({ file: name, line: index + 1, kind });
    if (OWN_NAMES.some((own) => line.includes(own))) findings.push({ file: name, line: index + 1, kind: "this computer's folder, user or machine name" });
  });
}

/** Every file in the folder, and every entry inside each zip file in it. */
function scan(folder: string): Scan {
  const result: Scan = { searched: [], notSearched: [], findings: [] };
  for (const full of listFiles(folder)) {
    const name = relative(folder, full);
    const data = readFileSync(full);
    if (name.endsWith(".zip")) {
      for (const entry of readZip(data)) {
        const inside = `${name}!${entry.name}`;
        if (looksBinary(entry.data)) result.notSearched.push(inside);
        else {
          result.searched.push(inside);
          scanText(inside, entry.data.toString("utf8"), result.findings);
        }
      }
    } else if (looksBinary(data)) result.notSearched.push(name);
    else {
      result.searched.push(name);
      scanText(name, data.toString("utf8"), result.findings);
    }
  }
  return result;
}

/** How many times an exact string is in the folder: in any file, and in any entry of any zip file, text or not. */
function countExact(folder: string, value: string): { times: number; where: string[] } {
  const where: string[] = [];
  let times = 0;
  const look = (name: string, data: Buffer): void => {
    let at = data.indexOf(value);
    if (at >= 0) where.push(name);
    while (at >= 0) {
      times += 1;
      at = data.indexOf(value, at + value.length);
    }
  };
  for (const full of listFiles(folder)) {
    const name = relative(folder, full);
    const data = readFileSync(full);
    if (name.endsWith(".zip")) for (const entry of readZip(data)) look(`${name}!${entry.name}`, entry.data);
    else look(name, data);
  }
  return { times, where };
}

const report = (findings: Finding[]): string[] => findings.map((one) => `${one.file}: line ${one.line}: ${one.kind}`);
const REPORT_LINE = new RegExp(`^[A-Za-z0-9._!/-]+: line \\d+: (?:${[...new Set(SHAPES.map(([kind]) => kind)), "this computer's folder, user or machine name"].join("|")})$`);

// ---------------------------------------------------------------- what a bundle must hold

type Bundle = Record<string, any>;

function checkBundle(log: Log, folder: string, label: string): Bundle | null {
  const read = (name: string): Buffer | null => (existsSync(join(folder, name)) ? readFileSync(join(folder, name)) : null);
  log.out(`Files in ${label}:`);
  for (const full of listFiles(folder)) log.out(`  ${String(statSync(full).size).padStart(7)} bytes  ${relative(folder, full)}`);
  log.out();

  let bundle: Bundle | null = null;
  try {
    bundle = JSON.parse(read("bundle.json")?.toString("utf8") ?? "");
  } catch {
    bundle = null;
  }
  log.check(`${label}: bundle.json is there and names the failed test, "${FAILING}"`, bundle?.test?.title === FAILING && bundle?.result?.status === "failed");

  // 1. the trace
  let trace: { name: string; data: Buffer }[] = [];
  try {
    trace = readZip(read("trace.zip") ?? Buffer.alloc(0));
  } catch {
    trace = [];
  }
  const steps = (trace.find((entry) => entry.name === "trace.trace")?.data.toString("utf8") ?? "").split("\n").filter((line) => line !== "");
  const actions = steps.filter((line) => line.startsWith('{"type":"before"')).length;
  const snapshots = steps.filter((line) => line.startsWith('{"type":"frame-snapshot"')).length;
  const network = (trace.find((entry) => entry.name === "trace.network")?.data.toString("utf8") ?? "").split("\n").filter((line) => line !== "");
  log.out(`  trace.zip: ${trace.length} entries. Steps recorded: ${actions}. Page snapshots: ${snapshots}. Network entries: ${network.length}`);
  log.check(`${label}: TRACE. trace.zip opens, and holds the steps of the test (${actions}), snapshots of the page (${snapshots}) and the network (${network.length} entries) (criterion 1)`,
    actions >= 5 && snapshots >= 5 && network.length >= 4);
  log.check(`${label}: the trace's network file holds the request that was answered 500`, network.some((line) => line.includes("/api/orders/ord-1003") && line.includes('"status":500')));

  // 2. the screenshot
  const picture = read("screenshot.png") ?? Buffer.alloc(0);
  const isPng = picture.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
  const width = isPng ? picture.readUInt32BE(16) : 0;
  const height = isPng ? picture.readUInt32BE(20) : 0;
  log.out(`  screenshot.png: ${isPng ? `a PNG picture, ${width} by ${height}` : "NOT a PNG picture"}`);
  log.check(`${label}: SCREENSHOT. screenshot.png is a PNG picture of a page-sized area (criterion 1)`, isPng && width >= 300 && height >= 200);

  // 3. the console log
  const consoleLines = (read("console.log")?.toString("utf8") ?? "").split("\n").filter((line) => line !== "");
  log.check(`${label}: CONSOLE LOG. console.log has the page's own error line about ord-1003, with its time (criterion 1)`,
    consoleLines.some((line) => /^\d{4}-\d\d-\d\dT[\d:.]+Z \[error\] order page: could not load ord-1003/.test(line)));

  // 4. the failed requests
  let failed: Bundle[] = [];
  try {
    failed = JSON.parse(read("failed-requests.json")?.toString("utf8") ?? "");
  } catch {
    failed = [];
  }
  const fault = failed.find((one) => one.status === 500 && String(one.url).endsWith("/api/orders/ord-1003"));
  log.out(`  failed-requests.json: ${failed.length} requests: ${failed.map((one) => `${one.status ?? one.failure} ${String(one.url).replace(/^https?:\/\/[^/]+/, "")}`).join(", ")}`);
  log.check(`${label}: FAILED REQUESTS. failed-requests.json has the request answered 500, with the answer's body (criterion 1)`,
    Boolean(fault) && String(fault?.responseBody).includes("price_list_unavailable"));
  log.check(`${label}: requests.txt lists every request in order, the failed one among them`,
    /GET \/api\/orders\/ord-1003 -> 500/.test(read("requests.txt")?.toString("utf8") ?? ""));

  // 5. the error text
  const error = read("error.txt")?.toString("utf8") ?? "";
  log.check(`${label}: ERROR TEXT. error.txt has Playwright's message, the timeout, and the line of the test that raised it (criterion 1)`,
    error.includes("toBeVisible") && /Timeout: 5000ms/.test(error) && /failure-evidence\.spec\.ts:\d+:\d+/.test(error));

  // the two stretch goals
  log.check(`${label}: SERVER LOG (stretch goal). server.log holds the application's own line for the 500, inside the test's time window`,
    (read("server.log")?.toString("utf8") ?? "").split("\n").some((line) => {
      const at = Date.parse(line.slice(0, 24));
      return /GET \/api\/orders\/ord-1003 500 .*price_list_unavailable/.test(line) && at >= Date.parse(bundle?.startedAt) - 50 && at <= Date.parse(bundle?.endedAt) + 50;
    }));
  log.check(`${label}: server.log holds only lines from the test's own time window, not the application's whole log`,
    (read("server.log")?.toString("utf8") ?? "").split("\n").filter((line) => line !== "").every((line) => {
      const at = Date.parse(line.slice(0, 24));
      return at >= Date.parse(bundle?.startedAt) - 50 && at <= Date.parse(bundle?.endedAt) + 50;
    }));
  log.check(`${label}: COMMIT (stretch goal). bundle.json names a commit, says whether there were uncommitted changes, and gives a checksum of each file under test`,
    /^[0-9a-f]{40}$/.test(bundle?.commit?.sha ?? "") && typeof bundle?.commit?.uncommittedChanges === "boolean" && (bundle?.underTest?.length ?? 0) >= 3);

  // every file is the one bundle.json describes
  const listed: Bundle[] = bundle?.files ?? [];
  const onDisk = listFiles(folder).map((full) => relative(folder, full)).filter((name) => name !== "bundle.json").sort();
  log.check(`${label}: bundle.json lists exactly the files that are there (${onDisk.length}), and each one's checksum matches`,
    listed.length > 0 && JSON.stringify(listed.map((one) => one.name).sort()) === JSON.stringify(onDisk) &&
    listed.every((one) => sha256(read(one.name) ?? Buffer.alloc(0)) === one.sha256));
  log.check(`${label}: the bundle reports no problem of its own while it was being made`, Array.isArray(bundle?.problems) && bundle?.problems.length === 0);
  const kept = Date.parse(bundle?.kept?.deleteAfter) - Date.parse(bundle?.endedAt);
  log.out(`  bundle.json: ended ${bundle?.endedAt}. To be deleted after ${bundle?.kept?.deleteAfter}`);
  log.check(`${label}: the bundle says when it is to be deleted: ${KEEP_DAYS} days after the test ended, to the millisecond (criterion 6)`, bundle?.kept?.days === KEEP_DAYS && kept === KEEP_DAYS * DAY);
  return bundle;
}

// ---------------------------------------------------------------- the three logs

async function main(): Promise<boolean> {
  const app = await startApp();
  let allOk = true;
  try {
    // ============================================================ capture-check.txt
    const capture = new Log("A failing test and its failure bundle. playwright-failure-evidence, attempt playwright-attempt-003");
    capture.part("PART 1. The test that fails on purpose is run");
    const bundles = join(SCRATCH, "bundles");
    const output = join(SCRATCH, "playwright-output");
    const failing = runTest(FAILING, bundles, output);
    capture.block(failing.command, failing.output, failing.code);
    capture.check("the test failed: exit code 1, and Playwright counts 1 failed", failing.code === 1 && /\b1 failed\b/.test(failing.output));
    capture.check("the error Playwright printed says only that it waited and timed out. It names no cause",
      /Timeout: 5000ms/.test(failing.output) && !/500|price|north-2/.test(failing.output.replace(/Timeout: 5000ms|timeout 5000ms|:\d+:\d+/g, "")));
    const made = bundleFolders(bundles);
    capture.check("exactly one failure bundle was written", made.length === 1);
    const fresh = made[0] ?? join(bundles, "none");
    capture.part("PART 2. What the bundle of that run holds");
    const freshBundle = checkBundle(capture, fresh, "this run's bundle");
    const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: REPO, encoding: "utf8" }).stdout.trim();
    capture.check("the commit in the bundle is the commit git reports for this repository now", freshBundle?.commit?.sha === head);
    const spec = sha256(readFileSync(join(TESTS, "failure-evidence.spec.ts")));
    capture.check("the checksum the bundle gives for the test file is the checksum of the test file as it is now",
      (freshBundle?.underTest ?? []).some((one: Bundle) => String(one.file).endsWith("failure-evidence.spec.ts") && one.sha256 === spec));
    const left = listFiles(output).map((full) => relative(output, full));
    capture.out(`Playwright's own scratch folder after the run: ${left.join(", ") || "(empty)"}`);
    capture.check("Playwright itself saved no trace, screenshot or video of its own, so there is no second, unredacted copy",
      left.every((name) => !/\.(zip|png|jpe?g|webm|trace|network)$/i.test(name)));
    const freshScan = scan(fresh);
    capture.check("this run's bundle, scanned for secrets: none found", freshScan.findings.length === 0);

    if (SAVE) {
      capture.part("PART 3. --save-bundle: this run's bundle replaces the handed-in one");
      if (freshScan.findings.length === 0 && capture.problems.length === 0) {
        rmSync(HANDED_IN, { recursive: true, force: true });
        cpSync(fresh, HANDED_IN, { recursive: true });
        capture.out(`Copied to ${tidy(HANDED_IN)}.`);
      } else {
        capture.check("the bundle could be saved: every check above passed", false);
      }
    }
    capture.part(`PART ${SAVE ? 4 : 3}. The handed-in bundle, ${tidy(HANDED_IN)}`);
    capture.out("The same checks, on the bundle that is handed in. It was made by an earlier run of this script with --save-bundle.");
    if (existsSync(join(HANDED_IN, "bundle.json"))) checkBundle(capture, HANDED_IN, "the handed-in bundle");
    else capture.check("there is a handed-in bundle. Run this script once with --save-bundle", false);
    allOk = capture.save("capture-check.txt") && allOk;

    // ============================================================ passing-run.txt
    const passing = new Log("A passing test, and how long evidence is kept. playwright-failure-evidence, attempt playwright-attempt-003");
    passing.part("PART 1. The test that passes is run, into an empty folder");
    const quiet = join(SCRATCH, "passing-bundles");
    const quietOutput = join(SCRATCH, "passing-output");
    const passed = runTest(PASSING, quiet, quietOutput);
    passing.block(passed.command, passed.output, passed.code);
    passing.check("the test passed: exit code 0, and Playwright counts 1 passed", passed.code === 0 && /\b1 passed\b/.test(passed.output));
    passing.out("Everything the run left behind, in the evidence folder and in Playwright's own scratch folder:");
    const keptFiles = [...listFiles(quiet), ...listFiles(quietOutput)];
    let total = 0;
    for (const full of keptFiles) {
      total += statSync(full).size;
      passing.out(`  ${String(statSync(full).size).padStart(7)} bytes  ${tidy(full)}`);
    }
    passing.out(`  ${String(total).padStart(7)} bytes in all`);
    const line = existsSync(join(quiet, "passing-runs.log")) ? readFileSync(join(quiet, "passing-runs.log"), "utf8") : "";
    passing.out("passing-runs.log, whole:", ...line.trimEnd().split("\n").map((one) => `  ${one}`));
    passing.check("no failure bundle was written", bundleFolders(quiet).length === 0);
    passing.check("the evidence folder holds one file, passing-runs.log, with one line: the time, the title and how long the test took (criterion 2)",
      listFiles(quiet).length === 1 && new RegExp(`^\\d{4}-\\d\\d-\\d\\dT[\\d:.]+Z PASSED ${JSON.stringify(PASSING).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} in \\d+ms\\. Kept: this line only\\n$`).test(line));
    passing.check("no trace, screenshot, video, console log or request log was kept anywhere (criterion 2)",
      keptFiles.every((full) => !/\.(zip|png|jpe?g|webm)$|console\.log$|requests/i.test(full)));
    passing.check("in all, the passing run kept under 1,000 bytes", total < 1000);
    passing.check("the trace WAS recorded during the passing test and then thrown away: the same test, failing, would have had one",
      existsSync(join(fresh, "trace.zip")));

    passing.part(`PART 2. Evidence is deleted after ${KEEP_DAYS} days (criterion 6)`);
    const now = Date.now();
    const plant = (name: string, deleteAfter: number | null): void => {
      mkdirSync(join(quiet, name), { recursive: true });
      writeFileSync(join(quiet, name, "trace.zip"), "made up, to be deleted or kept\n");
      if (deleteAfter !== null) writeFileSync(join(quiet, name, "bundle.json"), JSON.stringify({ format: "gtq-failure-bundle/1", kept: { days: KEEP_DAYS, deleteAfter: new Date(deleteAfter).toISOString() } }));
    };
    plant("made-15-days-ago", now - DAY);          // its date passed yesterday
    plant("made-13-days-ago", now + DAY);          // its date is tomorrow
    plant("not-a-bundle", null);                   // a folder with no bundle.json: not ours to delete
    mkdirSync(join(quiet, "another-format"), { recursive: true });
    writeFileSync(join(quiet, "another-format", "bundle.json"), JSON.stringify({ format: "something-else/1", kept: { deleteAfter: new Date(now - 30 * DAY).toISOString() } }));
    const oldLine = `${new Date(now - 15 * DAY).toISOString()} PASSED "a made-up test, 15 days ago" in 10ms. Kept: this line only\n`;
    const recentLine = `${new Date(now - 13 * DAY).toISOString()} PASSED "a made-up test, 13 days ago" in 10ms. Kept: this line only\n`;
    writeFileSync(join(quiet, "passing-runs.log"), oldLine + recentLine + line, "utf8");
    passing.out("Put in place before the run: a bundle whose date passed yesterday (made 15 days ago), a bundle whose date is tomorrow",
      "(made 13 days ago), a folder that is not a bundle, a folder with a bundle.json of another format and an old date, and two",
      "made-up lines in passing-runs.log, 15 and 13 days old.");
    const again = runTest(PASSING, quiet, quietOutput);
    passing.block(again.command, again.output, again.code);
    const after = readFileSync(join(quiet, "passing-runs.log"), "utf8");
    passing.check("the bundle past its date was deleted", !existsSync(join(quiet, "made-15-days-ago")));
    passing.check("the bundle not yet at its date was kept, with its files", existsSync(join(quiet, "made-13-days-ago", "trace.zip")));
    passing.check("the folder that is not a bundle was left alone", existsSync(join(quiet, "not-a-bundle", "trace.zip")));
    passing.check("the folder with a bundle.json of another format was left alone, though its date is long past", existsSync(join(quiet, "another-format", "bundle.json")));
    passing.check("the passing line 15 days old was deleted, and the one 13 days old was kept", !after.includes("15 days ago") && after.includes("13 days ago"));
    passing.check("the run said what it deleted: 1 expired bundle, 1 kept, 2 folders left alone, 1 old line",
      /1 expired failure bundle\(s\) deleted, 1 kept, 2 folder\(s\) that are not bundles left alone, 1 old passing line\(s\) deleted/.test(again.output));
    const config = readFileSync(join(TESTS, "evidence.config.ts"), "utf8");
    passing.check(`the configuration file states the ${KEEP_DAYS} days in words and as the setting keepFailureBundleDays: ${KEEP_DAYS}`,
      config.includes(`keepFailureBundleDays: ${KEEP_DAYS},`) && config.includes(`kept for ${KEEP_DAYS} DAYS`));
    allOk = passing.save("passing-run.txt") && allOk;

    // ============================================================ redaction-check.txt
    const redaction = new Log("The scan of the failure bundle for secrets. playwright-failure-evidence, attempt playwright-attempt-003");
    redaction.out("A finding is reported as a file, a line and a kind. The value is never shown. Inside trace.zip, a file is written",
      "as trace.zip!NAME. The shapes looked for:", ...[...new Set(SHAPES.map(([kind]) => kind))].map((kind) => `  - ${kind}`), "  - this computer's folder, user or machine name");

    redaction.part(`PART 1. The handed-in bundle is scanned (criterion 3). ${tidy(HANDED_IN)}`);
    const handed = existsSync(HANDED_IN) ? scan(HANDED_IN) : { searched: [], notSearched: [], findings: [] };
    redaction.out(`Searched, line by line (${handed.searched.length}):`, ...handed.searched.map((name) => `  ${name}`));
    redaction.out(`Not searched, because it is not text (${handed.notSearched.length}):`, ...handed.notSearched.map((name) => `  ${name}`));
    redaction.out(`Found (${handed.findings.length}):`, ...(handed.findings.length ? report(handed.findings).map((one) => `  ${one}`) : ["  none"]));
    redaction.check("the scan opened trace.zip and searched the files inside it, not only the zip file's own bytes",
      ["trace.zip!trace.trace", "trace.zip!trace.network"].every((name) => handed.searched.includes(name)) && handed.searched.filter((name) => name.startsWith("trace.zip!resources/")).length >= 3);
    redaction.check("every text file of the bundle was searched: the error, the console log, the requests, the server log, bundle.json",
      ["error.txt", "console.log", "failed-requests.json", "requests.txt", "server.log", "bundle.json", "READ-ME-FIRST.md"].every((name) => handed.searched.includes(name)));
    redaction.check("the handed-in bundle holds no token, cookie, credential or name of this computer that the scan can find: 0 findings (criterion 3)",
      handed.searched.length > 0 && handed.findings.length === 0);
    redaction.check("the only file not searched is the screenshot, which is a picture and has to be looked at by a person",
      JSON.stringify(handed.notSearched) === JSON.stringify(["screenshot.png"]));
    const handedBundle: Bundle = existsSync(join(HANDED_IN, "bundle.json")) ? JSON.parse(readFileSync(join(HANDED_IN, "bundle.json"), "utf8")) : {};
    const replaced: Record<string, number> = handedBundle.redaction?.replacements ?? {};
    redaction.out("What the bundle says was replaced while it was made (kinds and counts, never values):", ...Object.entries(replaced).map(([kind, count]) => `  ${String(count).padStart(3)}  ${kind}`));
    redaction.check("\"none found\" is not because there was nothing: the bundle says it replaced a cookie, a password and a token, each at least once",
      ["by value: cookie", "by value: password", "by value: token"].every((kind) => (replaced[kind] ?? 0) >= 1));

    redaction.part("PART 2. Can the scan find what redaction removes? The same test, run with redaction turned OFF");
    const raw = join(SCRATCH, "unredacted-bundles");
    const unredacted = runTest(FAILING, raw, join(SCRATCH, "unredacted-output"), false);
    const rawFolder = bundleFolders(raw)[0] ?? join(raw, "none");
    redaction.out(`$ ${unredacted.command}`, `exit code: ${unredacted.code}. The bundle went to the scratch folder, which is deleted when this script ends.`,
      "Every secret in it is made up: the application accepts any password, and its cookie and token open nothing else.");
    const rawScan = scan(rawFolder);
    redaction.out(`Found in the unredacted bundle (${rawScan.findings.length}):`, ...report(rawScan.findings).map((one) => `  ${one}`));
    const kinds = new Set(rawScan.findings.map((one) => one.kind));
    redaction.check("the unredacted bundle is marked as such, in its folder's name and in its bundle.json", /UNREDACTED-/.test(rawFolder) && /"on": false/.test(existsSync(join(rawFolder, "bundle.json")) ? readFileSync(join(rawFolder, "bundle.json"), "utf8") : ""));
    redaction.check("with redaction off, the scan finds a cookie with a value", kinds.has("cookie with a value") || kinds.has("session cookie"));
    redaction.check("with redaction off, the scan finds the bearer token", kinds.has("bearer token"));
    redaction.check("with redaction off, the scan finds the password", kinds.has("password with a value"));
    redaction.check("with redaction off, the scan finds the token the page was given, inside a page snapshot in the trace",
      rawScan.findings.some((one) => one.kind === "token or key assigned to a name" && one.file.startsWith("trace.zip!")));
    redaction.check("with redaction off, the scan finds this computer's folder or user name, which a trace records",
      kinds.has("this computer's folder, user or machine name"));
    redaction.check("with redaction off, secrets are found inside the trace and outside it",
      rawScan.findings.some((one) => one.file.startsWith("trace.zip!")) && rawScan.findings.some((one) => !one.file.startsWith("trace.zip!")));
    redaction.check("so the 0 findings of part 1 are the work of the redaction, not of a scan that sees nothing", rawScan.findings.length >= 5 && handed.findings.length === 0);
    redaction.out("", "A second way of looking, that does not depend on shapes. This script chose the password the test typed, so it can look",
      "for exactly that string: in every file, and in every entry of the trace, text or not.");
    const inRaw = countExact(rawFolder, CANARY);
    const inFresh = countExact(fresh, CANARY);
    redaction.out(`  with redaction OFF: ${inRaw.times} times, in ${inRaw.where.join(", ") || "no file"}`, `  with redaction ON, in the bundle part 1 of capture-check.txt made in this same run: ${inFresh.times} times`);
    redaction.check("with redaction off, the password this script chose is in the bundle, inside the trace: where it was typed, and where it was sent",
      inRaw.times >= 2 && inRaw.where.includes("trace.zip!trace.trace"));
    redaction.check("with redaction on, the password this script chose is nowhere in the bundle: 0 times, in any file or any entry of the trace", existsSync(join(fresh, "trace.zip")) && inFresh.times === 0);

    redaction.part("PART 3. Planted fake values are found (criterion 4)");
    const copy = join(SCRATCH, "planted");
    if (existsSync(HANDED_IN)) cpSync(HANDED_IN, copy, { recursive: true });
    else mkdirSync(copy, { recursive: true });
    const hex = (bytes: number): string => randomBytes(bytes).toString("hex");
    const planted: { file: string; line: number; kind: string; value: string }[] = [];
    const plantLine = (file: string, atLine: number, text: string, kind: string, value: string): void => {
      const inZip = file.startsWith("trace.zip!");
      const zipPath = join(copy, "trace.zip");
      const entries = inZip ? readZip(readFileSync(zipPath)) : [];
      const entry = entries.find((one) => `trace.zip!${one.name}` === file);
      const lines = (inZip ? entry?.data.toString("utf8") ?? "" : existsSync(join(copy, file)) ? readFileSync(join(copy, file), "utf8") : "").split("\n");
      while (lines.length < atLine - 1) lines.push("");
      lines.splice(atLine - 1, 0, text);
      if (inZip) {
        if (entry) entry.data = Buffer.from(lines.join("\n"), "utf8");
        else entries.push({ name: file.slice("trace.zip!".length), data: Buffer.from(lines.join("\n"), "utf8") });
        writeFileSync(zipPath, writeZip(entries));
      } else writeFileSync(join(copy, file), lines.join("\n"), "utf8");
      planted.push({ file, line: atLine, kind, value });
    };
    const [fakeBearer, fakeCookie, fakeTyped, fakeAssigned, fakeKnown, fakeZipCookie, fakeZipBearer] =
      [hex(20), hex(16), `pw-${hex(9)}`, hex(20), `${"gh"}${"p_"}${hex(18)}`, hex(16), hex(20)];
    plantLine("console.log", 3, `2026-01-01T00:00:00.000Z [log] planted: request sent with Authorization: Bearer ${fakeBearer}`, "bearer token", fakeBearer);
    plantLine("failed-requests.json", 12, `      "cookie": "demo_session=${fakeCookie}",`, "cookie with a value", fakeCookie);
    plantLine("server.log", 2, `2026-01-01T00:00:00.000Z POST /session 303 0ms planted: body was name=Fixture+Clerk&password=${fakeTyped}`, "password with a value", fakeTyped);
    plantLine("error.txt", 5, `planted: pushed with ${fakeKnown}`, "well-known key shape", fakeKnown);
    plantLine("trace.zip!trace.network", 2, `{"type":"resource-snapshot","snapshot":{"request":{"headers":[{"name":"Cookie","value":"demo_session=${fakeZipCookie}"}]}}}`, "cookie with a value", fakeZipCookie);
    plantLine("trace.zip!resources/planted.html", 4, `<script>const apiToken = "${fakeAssigned}";</script>`, "token or key assigned to a name", fakeAssigned);
    plantLine("trace.zip!trace.trace", 3, `{"type":"log","message":"planted: fetch with headers {\\"Authorization\\": \\"Bearer ${fakeZipBearer}\\"}"}`, "bearer token", fakeZipBearer);
    const plantedScan = scan(copy);
    redaction.out(`${planted.length} fake values, made up when this script ran, were put into a copy of the handed-in bundle, at these places:`,
      ...planted.map((one) => `  ${one.file}: line ${one.line}: a fake ${one.kind}`));
    redaction.out(`Found in the copy (${plantedScan.findings.length}):`, ...report(plantedScan.findings).map((one) => `  ${one}`));
    for (const one of planted) {
      redaction.check(`the planted ${one.kind} in ${one.file} was found, at line ${one.line} (criterion 4)`,
        plantedScan.findings.some((found) => found.file === one.file && found.line === one.line && found.kind === one.kind));
    }
    const places = new Set(planted.map((one) => `${one.file}:${one.line}`));
    redaction.check("nothing was reported at any other place: every finding is at a line where a value was planted",
      plantedScan.findings.length >= planted.length && plantedScan.findings.every((found) => places.has(`${found.file}:${found.line}`)));

    redaction.part("PART 4. The report gives the file and the line, and never the value");
    const everything = [...report(handed.findings), ...report(rawScan.findings), ...report(plantedScan.findings)];
    redaction.check(`every one of the ${everything.length} report lines above is a file, a line number and a kind from the list, and nothing more`,
      everything.length > 0 && everything.every((one) => REPORT_LINE.test(one)));
    redaction.check("not one of the planted values, and not the password this script chose, is anywhere in this log", [...planted.map((one) => one.value), CANARY].every((value) => !redaction.text().includes(value)));
    redaction.check("no report line holds a run of 16 or more letters and digits, which is what a token looks like", everything.every((one) => !/[A-Za-z0-9]{16,}/.test(one.replace(/resources\/[0-9a-f]{40}/, "resources/"))));

    redaction.part("PART 5. The trace still opens after the secrets were taken out of it");
    const unzip = spawnSync("unzip", ["-tq", join(HANDED_IN, "trace.zip")], { encoding: "utf8" });
    if (unzip.error) redaction.out("The program `unzip` is not on this computer, so the trace was not tested with a second tool. NOT ASSESSED here.");
    else {
      redaction.out(`$ unzip -tq trace.zip`, `  ${tidy(`${unzip.stdout}${unzip.stderr}`).trim()}`);
      redaction.check("a second tool, the system's own unzip, tests the rewritten trace.zip and finds no error", unzip.status === 0);
    }
    allOk = redaction.save("redaction-check.txt") && allOk;
  } finally {
    await stopApp(app);
    rmSync(SCRATCH, { recursive: true, force: true });
  }
  return allOk;
}

main().then(
  (ok) => {
    console.log(`RESULT: ${ok ? "every check in the three logs passed." : "NOT ALL CHECKS PASSED. See above."}`);
    process.exit(ok ? 0 : 1);
  },
  (error) => {
    rmSync(SCRATCH, { recursive: true, force: true });
    console.error(`failure-evidence-check: ${error instanceof Error ? error.message : error}`);
    process.exit(1);
  },
);

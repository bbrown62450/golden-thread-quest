/*
 * The check for the playwright-failure-triage quest. It does two separate jobs.
 *
 *   node tools/failure-triage-check.ts --make-failures
 *       Produces the six failures and saves their evidence bundles as failures/failure-01 ... failure-06 in the
 *       attempt folder. It starts the made-up order desk (demo-app/triage-server.mjs) on this computer, arranges
 *       each failure, runs its test with triage.config.ts, and stops the application. It contacts nothing else.
 *       It writes logs/make-failures.txt. Run it once: a second run replaces the bundles with new ones.
 *
 *   node tools/failure-triage-check.ts
 *       Checks the triage report, participant/context/playwright/triage-report.md, against the bundles, and
 *       writes logs/triage-check.txt. It runs no test and starts nothing. It reads files only.
 *
 * Run it from participant/tests/playwright, with Node 22.18 or later.
 *
 * WHAT THE CHECK TESTS
 *   Of the bundles:
 *     - there are six, each with the files a triage needs, each file matching the checksum its bundle.json gives;
 *     - nothing in a bundle's name, or in the names of its files, says what kind of failure it is;
 *     - no bundle holds a cookie, a token, a password or this computer's names.
 *   Of the report, for every bundle:
 *     - it is classified, exactly once, with exactly one of the five classes (criterion 1). "flaky" is not one;
 *     - the classification cites at least one file, every cited file is IN THAT BUNDLE, and the written reason
 *       names every file it cites (criterion 2);
 *     - a failure whose bundle shows a retry that passed cites attempts.json and explains the retry (criterion 3);
 *     - an inconclusive one says which classes are still possible and what would settle it (criterion 4);
 *     - it states the next action and who takes it, and the "who" is the role the rules give that class (criterion 5);
 *     and no classification is given for a failure that has no bundle.
 *   That the check can fail: the report is broken in one way at a time, in memory, and each fault must be reported.
 *
 * WHAT IT DOES NOT TEST
 *   Whether a classification is RIGHT. The check does not know the causes. The last part of the log puts the
 *   report's classes beside the ground-truth file and counts the agreement, as a fact for the reader. It is not a
 *   pass or fail, and the check never reads the ground truth for anything else.
 *
 * The order of the six, and what is arranged for each, is fixed in FAILURES below. Which order each bundle is for is
 * no secret from this file: the causes are in participant/context/playwright/ground-truth.md, written first.
 */

import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir, hostname, tmpdir, userInfo } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { looksBinary, readZip } from "../support/zip.ts";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-failure-triage", "playwright-attempt-004");
// tools/failure-triage-planted-faults.ts points these elsewhere, so that its runs do not replace the real log.
const LOGS = process.env.GTQ_CHECK_LOGS ?? join(ATTEMPT, "logs");
const FAILURES_DIR = join(ATTEMPT, "failures");
const CONTEXT = join(PARTICIPANT, "context", "playwright");
const REPORT = process.env.GTQ_CHECK_REPORT ?? join(CONTEXT, "triage-report.md");
const PORT = Number(process.env.TRIAGE_PORT ?? 4797);
const BASE = `http://127.0.0.1:${PORT}`;

const CLASSES = ["product-bug", "test-defect", "environment", "data", "inconclusive"];
const OWNERS: Record<string, string> = {
  "product-bug": "the application's developers", "test-defect": "the owner of the test", "environment": "the platform team", "data": "the owner of the test data",
};
const NEEDED = ["error.txt", "test-source.txt", "screenshot.png", "screenshot-after-wait.png", "page-text.txt", "console.log", "requests.txt", "failed-requests.json",
  "api-responses.json", "server.log", "trace.zip", "attempts.json", "bundle.json", "READ-ME-FIRST.md"];
const REPEATS = 10;

type Arrange = "nothing" | "pricing-down" | "stall-once" | "until-retry-passes";
const FAILURES: { name: string; order: string; arrange: Arrange }[] = [
  { name: "failure-01", order: "ord-2004", arrange: "nothing" },
  { name: "failure-02", order: "ord-2005", arrange: "until-retry-passes" },
  { name: "failure-03", order: "ord-2002", arrange: "nothing" },
  { name: "failure-04", order: "ord-2006", arrange: "stall-once" },
  { name: "failure-05", order: "ord-2001", arrange: "nothing" },
  { name: "failure-06", order: "ord-2003", arrange: "pricing-down" },
];

// ---------------------------------------------------------------- the log

class Log {
  lines: string[];
  problems: string[];

  constructor(title: string, about: string) {
    this.lines = [title, "Recorded by tools/failure-triage-check.ts. The application is a made-up order desk on this computer. Nothing in it is real.", about];
    this.problems = [];
  }

  out(...texts: string[]): void {
    this.lines.push(...(texts.length ? texts : [""]));
  }

  part(text: string, ...more: string[]): void {
    this.lines.push("", "=".repeat(78), text, ...more);
  }

  check(label: string, ok: boolean): void {
    this.lines.push(`  ${ok ? "ok  " : "FAIL"} ${label}`);
    if (!ok) this.problems.push(label);
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

// ---------------------------------------------------------------- making the failures

async function reachable(): Promise<boolean> {
  try {
    return (await fetch(`${BASE}/healthz`)).ok;
  } catch {
    return false;
  }
}

async function harness(path: string): Promise<void> {
  for (let attempt = 1; ; attempt += 1) {
    try {
      const answer = await fetch(`${BASE}/__harness/${path}`, { method: "POST", headers: { connection: "close" } });
      if (!answer.ok) throw new Error(`the harness switch ${path} answered ${answer.status}`);
      return;
    } catch (error) {
      if (attempt >= 5) throw error;                                    // a connection left open from earlier can have gone stale
      await new Promise((done) => setTimeout(done, 200));
    }
  }
}

function runTest(order: string, bundles: string, scratch: string, serverLog: string, retries: number): { code: number; output: string } {
  const done = spawnSync(process.execPath, [CLI, "test", "--config", "triage.config.ts", "--output", join(scratch, "playwright-output"), "--retries", String(retries),
    "-g", ` order ${order} shows its total$`], {
    cwd: TESTS, encoding: "utf8",
    env: { ...process.env, TRIAGE_PORT: String(PORT), TRIAGE_SERVER_LOG: serverLog, GTQ_BUNDLES_DIR: bundles, GTQ_CANARY_PASSWORD: `pw-canary-${randomBytes(10).toString("hex")}`, FORCE_COLOR: "0", CI: "" },
  });
  return { code: done.status ?? 1, output: `${done.stdout}${done.stderr}` };
}

async function makeFailures(): Promise<boolean> {
  const log = new Log("Making the six failures. playwright-failure-triage, attempt playwright-attempt-004",
    "This log says what was arranged for each failure. It is NOT part of any bundle and was not given to whoever classified them.");
  const scratch = mkdtempSync(join(tmpdir(), "gtq-triage-"));
  const serverLog = join(scratch, "triage-server.log");
  if (await reachable()) throw new Error(`something is already listening on port ${PORT}. Stop it, or set TRIAGE_PORT to a free port.`);
  const app: ChildProcess = spawn(process.execPath, ["demo-app/triage-server.mjs"], { cwd: TESTS, env: { ...process.env, TRIAGE_PORT: String(PORT), TRIAGE_SERVER_LOG: serverLog }, stdio: "ignore" });
  try {
    for (let attempt = 0; attempt < 100 && !(await reachable()); attempt += 1) await new Promise((done) => setTimeout(done, 100));
    if (!(await reachable())) throw new Error("the demo application did not start");
    rmSync(FAILURES_DIR, { recursive: true, force: true });
    for (const failure of FAILURES) {
      log.part(`${failure.name}: the test for order ${failure.order}`);
      const bundles = join(scratch, failure.name);
      const folder = join(bundles, `order-${failure.order}-shows-its-total`);
      let runs = 0;
      let attempts: { result: string }[] = [];
      if (failure.arrange === "pricing-down") {
        await harness("pricing?state=down");
        log.out("Arranged: the pricing service is stopped before the run, and stays stopped for the repeats.");
      }
      do {
        runs += 1;
        rmSync(bundles, { recursive: true, force: true });
        if (failure.arrange === "stall-once") await harness("stall?ms=3200");
        runTest(failure.order, bundles, scratch, serverLog, 1);
        attempts = existsSync(join(folder, "attempts.json")) ? JSON.parse(readFileSync(join(folder, "attempts.json"), "utf8")).attempts : [];
      } while (failure.arrange === "until-retry-passes" && runs < 60 && !(attempts.length === 2 && attempts[0].result !== "passed" && attempts[1].result === "passed"));
      if (failure.arrange === "stall-once") log.out("Arranged: the server process is frozen once, for 3.2 seconds, while it answers the request for the order's lines. Not during the repeats.");
      if (failure.arrange === "until-retry-passes") log.out(`Arranged: nothing. The test was run until a run failed and then passed on its retry. That took ${runs} run${runs === 1 ? "" : "s"}.`);
      if (failure.arrange === "nothing") log.out("Arranged: nothing. The fault is in the application, the test or the data as they stand.");
      log.out(`Attempts in the run kept: ${attempts.map((one, index) => `attempt ${index + 1} ${one.result}`).join(", ") || "NONE"}`);
      log.check(`${failure.name}: the first attempt failed and left a bundle`, attempts.length >= 1 && attempts[0].result !== "passed" && existsSync(join(folder, "bundle.json")));
      let failed = 0;
      for (let repeat = 0; repeat < REPEATS; repeat += 1) {
        if (runTest(failure.order, join(scratch, "repeats", failure.name, String(repeat)), scratch, serverLog, 0).code !== 0) failed += 1;
      }
      if (failure.arrange === "pricing-down") await harness("pricing?state=up");
      log.out(`Run again ${REPEATS} times straight afterwards, each with no retry: failed ${failed} of ${REPEATS}.`);
      if (existsSync(join(folder, "attempts.json"))) {
        const held = JSON.parse(readFileSync(join(folder, "attempts.json"), "utf8"));
        held.repeated = { runs: REPEATS, failed, passed: REPEATS - failed, how: `The same test was run ${REPEATS} more times straight after the run above, each time once, with no retry.` };
        writeFileSync(join(folder, "attempts.json"), JSON.stringify(held, null, 2) + "\n", "utf8");
        cpSync(folder, join(FAILURES_DIR, failure.name), { recursive: true });
      }
    }
    const made = existsSync(FAILURES_DIR) ? readdirSync(FAILURES_DIR).sort() : [];
    log.part("In all");
    log.check(`six bundles were saved: ${made.join(", ")}`, JSON.stringify(made) === JSON.stringify(FAILURES.map((one) => one.name)));
  } finally {
    await new Promise<void>((done) => {
      app.once("exit", () => done());
      app.kill();
    });
    rmSync(scratch, { recursive: true, force: true });
  }
  return log.save("make-failures.txt");
}

// ---------------------------------------------------------------- reading the report

type Entry = { name: string; fields: Record<string, string>; repeated: string[]; reason: string };

function parseReport(text: string): Entry[] {
  const entries: Entry[] = [];
  for (const piece of text.split(/^(?=## failure-)/m).slice(1)) {
    const lines = piece.split("\n");
    const entry: Entry = { name: lines[0].slice(3).trim(), fields: {}, repeated: [], reason: "" };
    let at = 1;
    while (at < lines.length && !lines[at].trim()) at += 1;
    while (at < lines.length && lines[at].startsWith("- ")) {
      const cut = lines[at].indexOf(": ");
      const name = cut > 0 ? lines[at].slice(2, cut) : lines[at].slice(2).replace(/:$/, "");
      if (name in entry.fields) entry.repeated.push(name);
      else entry.fields[name] = cut > 0 ? lines[at].slice(cut + 2).trim() : "";
      at += 1;
    }
    entry.reason = lines.slice(at).join("\n").split(/^## /m)[0].trim();
    entries.push(entry);
  }
  return entries;
}

type Bundle = { name: string; files: string[]; retryPassed: boolean };

function readBundles(): Bundle[] {
  if (!existsSync(FAILURES_DIR)) return [];
  return readdirSync(FAILURES_DIR, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => {
    const folder = join(FAILURES_DIR, entry.name);
    const files = listFiles(folder).map((full) => relative(folder, full));
    if (files.includes("trace.zip")) {
      try {
        files.push(...readZip(readFileSync(join(folder, "trace.zip"))).map((one) => `trace.zip!${one.name}`));
      } catch {
        // an unreadable trace is reported by the bundle checks
      }
    }
    let retryPassed = false;
    try {
      const attempts: { result: string }[] = JSON.parse(readFileSync(join(folder, "attempts.json"), "utf8")).attempts;
      retryPassed = attempts.length > 1 && attempts[0].result !== "passed" && attempts.slice(1).some((one) => one.result === "passed");
    } catch {
      retryPassed = false;
    }
    return { name: entry.name, files, retryPassed };
  }).sort((a, b) => a.name.localeCompare(b.name));
}

/** Everything wrong with the report, as "failure-NN: what". An empty list means it keeps every rule this check knows. */
function checkReport(text: string, bundles: Bundle[]): string[] {
  const wrong: string[] = [];
  const entries = parseReport(text);
  const seen = new Set<string>();
  for (const entry of entries) {
    const say = (message: string): void => {
      wrong.push(`${entry.name}: ${message}`);
    };
    if (seen.has(entry.name)) say("it is classified more than once in the report");
    seen.add(entry.name);
    const bundle = bundles.find((one) => one.name === entry.name);
    if (!bundle) {
      say("it is classified, and there is no bundle of that name. A failure is not classified without its evidence");
      continue;
    }
    const given = entry.fields.class;
    if (entry.repeated.includes("class")) say("it is given more than one class");
    if (!given) say("it has no class");
    else if (!CLASSES.includes(given)) say(`its class is ${JSON.stringify(given)}, which is not one of the five: ${CLASSES.join(", ")}`);
    const cited = (entry.fields.cites ?? "").split(",").map((one) => one.trim().replace(/^`|`$/g, "")).filter(Boolean);
    if (!cited.length) say("it cites no file. A classification must cite at least one file in its bundle");
    for (const file of cited) {
      if (!bundle.files.includes(file)) say(`it cites ${file}, which is not in its bundle`);
      else if (!entry.reason.includes(file.split("!").pop() ?? file)) say(`it cites ${file} and its reason never mentions that file, so the citation supports nothing`);
    }
    if (entry.reason.length < 80) say("it gives no reason, or one too short to say what the cited files show");
    if (!entry.fields.next_action) say("it states no next action");
    if (!entry.fields.owner) say("it does not say who takes the next action");
    else if (given && OWNERS[given] && entry.fields.owner !== OWNERS[given]) say(`a ${given} goes to ${OWNERS[given]}, and it names ${entry.fields.owner}`);
    if (given === "inconclusive") {
      const possible = CLASSES.filter((one) => one !== "inconclusive" && (entry.fields.still_possible ?? "").includes(one));
      if (possible.length < 2) say("it is inconclusive and does not name at least two classes that are still possible");
      if (!entry.fields.would_settle || entry.fields.would_settle.length < 30) say("it is inconclusive and does not say what would settle it");
    } else if (entry.fields.would_settle || entry.fields.still_possible) {
      say("it has a class and also says the question is open. It is one or the other");
    }
    if (bundle.retryPassed) {
      if (!cited.includes("attempts.json")) say("its bundle shows a retry that passed, and it does not cite attempts.json");
      if (!entry.fields.retry_explained || entry.fields.retry_explained.length < 40) say("its bundle shows a retry that passed, and it does not explain what differed between the attempts");
    }
    if (/\bflak/i.test(`${given ?? ""} ${entry.fields.next_action ?? ""}`)) say("it uses \"flaky\" as a class or as the action. Flaky is not a cause");
  }
  for (const bundle of bundles) if (!seen.has(bundle.name)) wrong.push(`${bundle.name}: it has a bundle and the report does not classify it`);
  return wrong;
}

// ---------------------------------------------------------------- the scan of the bundles

const SHAPES: [string, RegExp][] = [
  ["bearer token", /\bBearer\s+(?!\[REDACTED)[A-Za-z0-9._~+/=-]{16,}/],
  ["cookie with a value", /\bdemo_session=(?!\[REDACTED)[A-Za-z0-9]{8,}/],
  ["cookie with a value", /"cookies":\[(?:[^\]]|\[REDACTED [^\]]*\])*"value":"(?!\[REDACTED)[^"]/],
  // The form field's name is put together here so that this file does not itself look like it holds one.
  ["password with a value", new RegExp(String.raw`\b${"pass"}${"word"}[=](?!\[REDACTED)[^\s"'&\\]{6,}|\bpw-(?:canary-)?[0-9a-f]{16,}`)],
  ["token assigned to a name", /\bapiToken\s*=\s*\\?"(?!\[REDACTED)[A-Za-z0-9]{16,}/],
];
const OWN_NAMES = [homedir(), userInfo().username, hostname()].filter((name) => name.length >= 4);

function scanBundle(folder: string): { searched: number; findings: string[] } {
  const findings: string[] = [];
  let searched = 0;
  const look = (name: string, data: Buffer): void => {
    if (looksBinary(data)) return;
    searched += 1;
    data.toString("utf8").split("\n").forEach((line, index) => {
      const kinds = new Set(SHAPES.filter(([, shape]) => shape.test(line)).map(([kind]) => kind));
      if (OWN_NAMES.some((own) => line.includes(own))) kinds.add("this computer's folder, user or machine name");
      for (const kind of kinds) findings.push(`${name}: line ${index + 1}: ${kind}`);
    });
  };
  for (const full of listFiles(folder)) {
    const name = relative(folder, full);
    const data = readFileSync(full);
    if (name.endsWith(".zip")) for (const entry of readZip(data)) look(`${name}!${entry.name}`, entry.data);
    else look(name, data);
  }
  return { searched, findings };
}

// ---------------------------------------------------------------- the check

function check(): boolean {
  const log = new Log("The check of the triage report. playwright-failure-triage, attempt playwright-attempt-004",
    "It reads the six failure bundles and the triage report. It runs no test. It does not know the causes of the failures.");
  const bundles = readBundles();
  const text = existsSync(REPORT) ? readFileSync(REPORT, "utf8") : "";
  const entries = parseReport(text);

  log.part("PART 1. The bundles, in the attempt folder's failures/");
  log.check(`there are six bundles, as the quest asks: ${bundles.map((one) => one.name).join(", ")}`, bundles.length >= 6);
  const hints = /bug|defect|environment|data|inconclusive|flak|race|stall|pricing|retry|slow/i;
  log.check("no bundle's name says what kind of failure it is: each is failure-NN and nothing more", bundles.every((one) => /^failure-\d\d$/.test(one.name) && !hints.test(one.name)));
  for (const bundle of bundles) {
    const folder = join(FAILURES_DIR, bundle.name);
    let listed: { name: string; sha256: string }[] = [];
    let attempts: { attempts: { attempt: number; result: string }[]; repeated: { runs: number; failed: number } | null } = { attempts: [], repeated: null };
    try {
      listed = JSON.parse(readFileSync(join(folder, "bundle.json"), "utf8")).files;
      attempts = JSON.parse(readFileSync(join(folder, "attempts.json"), "utf8"));
    } catch {
      listed = [];
    }
    const scan = scanBundle(folder);
    log.out(`${bundle.name}: ${bundle.files.filter((one) => !one.includes("!")).length} files. Attempts: ${attempts.attempts.map((one) => one.result).join(", then ") || "none recorded"}.` +
      ` Run again ${attempts.repeated?.runs ?? 0} times: failed ${attempts.repeated?.failed ?? "?"}. Scanned ${scan.searched} text files and trace entries: ${scan.findings.length} findings.`);
    log.check(`${bundle.name}: it holds every file a triage needs, and each file is the one its bundle.json describes, by checksum`,
      NEEDED.every((name) => bundle.files.includes(name)) && listed.length >= 10 && listed.every((one) => existsSync(join(folder, one.name)) && sha256(readFileSync(join(folder, one.name))) === one.sha256));
    log.check(`${bundle.name}: its first attempt failed, and it says how often the test failed when run again`,
      attempts.attempts.length >= 1 && attempts.attempts[0].result !== "passed" && attempts.repeated !== null && attempts.repeated.runs === REPEATS);
    log.check(`${bundle.name}: it holds no cookie, token or password, and none of this computer's names`, scan.searched >= 12 && scan.findings.length === 0);
    for (const one of scan.findings) log.out(`    ${one}`);
  }
  const withRetry = bundles.filter((one) => one.retryPassed).map((one) => one.name);
  log.out(`Bundles that show a retry that PASSED after a failed first attempt: ${withRetry.join(", ") || "none"}`);
  log.check("at least one bundle shows a failure that passed on its retry, as the quest asks", withRetry.length >= 1);

  log.part(`PART 2. The report, ${relative(REPO, REPORT)}`);
  const wrong = checkReport(text, bundles);
  log.out("What the report says:", "");
  for (const entry of entries) {
    log.out(`  ${entry.name}: ${entry.fields.class ?? "NO CLASS"}`, `      cites: ${entry.fields.cites ?? "NOTHING"}`, `      next action: ${entry.fields.next_action ?? "NONE"}`,
      `      who: ${entry.fields.owner ?? "NOBODY"}`, ...(entry.fields.would_settle ? [`      would settle it: ${entry.fields.would_settle}`] : []));
  }
  log.out("", `Rules broken (${wrong.length}):`, ...(wrong.length ? wrong.map((one) => `  ${one}`) : ["  none"]), "");
  const of = (name: string): Entry | undefined => entries.find((one) => one.name === name);
  log.check("every bundle is classified, and nothing is classified that has no bundle", bundles.every((one) => of(one.name)) && entries.every((one) => bundles.some((bundle) => bundle.name === one.name)));
  log.check("each failure has exactly one class, and it is one of the five (criterion 1)",
    entries.length === bundles.length && entries.every((one) => CLASSES.includes(one.fields.class ?? "") && !one.repeated.includes("class")) && new Set(entries.map((one) => one.name)).size === entries.length);
  log.check("no failure is classed as \"flaky\"", !wrong.some((one) => one.includes("flaky")) && entries.every((one) => !/flak/i.test(one.fields.class ?? "")));
  log.check("every classification cites at least one file, and every file it cites is in that failure's own bundle (criterion 2)",
    entries.every((one) => (one.fields.cites ?? "").trim() !== "") && !wrong.some((one) => /cites/.test(one)));
  let citations = 0;
  for (const entry of entries) citations += (entry.fields.cites ?? "").split(",").filter((one) => one.trim()).length;
  log.check(`each of the ${citations} citations is used: the written reason names the file it cites`, citations >= bundles.length && !wrong.some((one) => one.includes("never mentions")));
  log.check("no failure is classified without a cited file", !wrong.some((one) => one.includes("cites no file")));
  log.check("the failure that passed on its retry has a class of its own, cites attempts.json, and explains what differed between the attempts (criterion 3)",
    withRetry.length >= 1 && withRetry.every((name) => CLASSES.includes(of(name)?.fields.class ?? "") && (of(name)?.fields.retry_explained ?? "").length >= 40) && !wrong.some((one) => one.includes("retry that passed")));
  const open = entries.filter((one) => one.fields.class === "inconclusive");
  log.check(`inconclusive is used (${open.length} time${open.length === 1 ? "" : "s"}), and each use names the classes still possible and what would settle it (criterion 4)`,
    open.length >= 1 && !wrong.some((one) => one.includes("inconclusive and does not")));
  log.check("every classification states a next action and who takes it, and the \"who\" is the role the rules give that class (criterion 5)",
    entries.every((one) => one.fields.next_action && one.fields.owner) && !wrong.some((one) => /next action|who takes|goes to/.test(one)));
  log.check("the report breaks none of the rules this check knows", entries.length > 0 && wrong.length === 0);
  const rules = existsSync(join(CONTEXT, "triage-rules.md")) ? readFileSync(join(CONTEXT, "triage-rules.md"), "utf8") : "";
  log.check("the rules document has, for each of the four classes with a cause, a list headed \"The evidence must show\" (criterion 6)",
    ["product-bug", "test-defect", "environment", "data"].every((name) => new RegExp("### `" + name + "`[\\s\\S]*?The evidence must show \\*\\*(all|both)\\*\\* of").test(rules)) && rules.includes("### `inconclusive`"));

  log.part("PART 3. Can the check fail? The report is broken in one way at a time, in memory, and checked again",
    "Each case starts from the report as it is. \"Reported\" is every rule the check then says is broken.");
  const first = entries[0]?.name ?? "failure-01";
  const section = (name: string): string => text.slice(text.indexOf(`## ${name}`)).split(/^(?=## failure-)/m)[0] ?? "";
  const swap = (name: string, from: RegExp, to: string): string => text.replace(section(name), section(name).replace(from, to));
  const retryName = withRetry[0] ?? first;
  const openName = open[0]?.name ?? first;
  const cases: [string, string, string][] = [
    ["a failure classed as \"flaky\" (criteria 1 and 3)", swap(retryName, /^- class: .*$/m, "- class: flaky"), "not one of the five"],
    ["a failure given two classes (criterion 1)", swap(first, /^(- class: .*)$/m, "$1\n- class: test-defect"), "more than one class"],
    ["a failure with no class (criterion 1)", swap(first, /^- class: .*\n/m, ""), "has no class"],
    ["a classification that cites no file (criterion 2)", swap(first, /^- cites: .*$/m, "- cites:"), "cites no file"],
    ["a classification that cites a file that does not exist in the bundle (criterion 2)", swap(first, /^- cites: .*$/m, "- cites: stack-trace.txt"), "which is not in its bundle"],
    ["a classification that cites a real file its reason never uses (criterion 2)", swap(first, /^(- cites: .*)$/m, "$1, READ-ME-FIRST.md"), "never mentions that file"],
    ["a classification with no next action (criterion 5)", swap(first, /^- next_action: .*\n/m, ""), "states no next action"],
    ["a classification that names nobody to act (criterion 5)", swap(first, /^- owner: .*\n/m, ""), "does not say who takes"],
    ["a classification sent to the wrong role (criterion 5)", swap(first, /^- owner: .*$/m, "- owner: whoever is on call"), "goes to"],
    ["the retry-passing failure without its explanation of the retry (criterion 3)", swap(retryName, /^- retry_explained: .*\n/m, ""), "does not explain what differed"],
    ["the retry-passing failure that does not cite attempts.json (criterion 3)", swap(retryName, /attempts\.json,? ?/, ""), "does not cite attempts.json"],
    ["an inconclusive failure that does not say what would settle it (criterion 4)", swap(openName, /^- would_settle: .*\n/m, ""), "does not say what would settle it"],
    ["an inconclusive failure that names only one possible class (criterion 4)", swap(openName, /^- still_possible: .*$/m, "- still_possible: environment"), "at least two classes"],
    ["a failure left out of the report", text.replace(section(first), ""), "the report does not classify it"],
    ["a classification of a failure that has no bundle", text + "\n## failure-99\n\n- class: product-bug\n- cites: error.txt\n- next_action: fix it\n- owner: the application's developers\n\nA reason long enough to pass, naming error.txt and saying what is wrong in general terms.\n", "there is no bundle of that name"],
    ["a failure classified twice", text + "\n" + section(first), "classified more than once"],
  ];
  for (const [title, broken, expected] of cases) {
    const found = broken === text ? [] : checkReport(broken, bundles);
    log.out(`  CASE: ${title}`, ...(found.length ? found.map((one) => `    reported: ${one}`) : [`    reported: NOTHING${broken === text ? " (the case could not be set up)" : ""}`]));
    log.check(`${title}: reported`, found.some((one) => one.includes(expected)));
  }

  log.part("PART 4. For the reader: the report beside the ground truth",
    "This part is not a check of the report. The check does not use the ground truth to decide anything. It is here so that a reader can see how the classification, which",
    "was made from the bundles alone, compares with what was really planted. The ground truth, participant/context/playwright/ground-truth.md, was written first.");
  const truth = existsSync(join(CONTEXT, "ground-truth.md")) ? readFileSync(join(CONTEXT, "ground-truth.md"), "utf8") : "";
  const planted = new Map<string, string>();
  const expected = new Map<string, string>();
  for (const row of truth.matchAll(/^\| `(failure-\d\d)` \| ord-\d+ \| .*? \| `([a-z-]+)` \|/gm)) planted.set(row[1], row[2]);
  for (const row of truth.matchAll(/^\| `(failure-\d\d)` \| \**`([a-z-]+)`\** \|/gm)) expected.set(row[1], row[2]);
  log.out("", "  failure      true cause     a correct triage says   the report says   agree?");
  let agree = 0;
  for (const bundle of bundles) {
    const said = of(bundle.name)?.fields.class ?? "none";
    if (said === expected.get(bundle.name)) agree += 1;
    log.out(`  ${bundle.name}   ${(planted.get(bundle.name) ?? "?").padEnd(13)}  ${(expected.get(bundle.name) ?? "?").padEnd(22)}  ${said.padEnd(16)}  ${said === expected.get(bundle.name) ? "yes" : "NO"}`);
  }
  log.out("", `  The report agrees with what a correct triage should say for ${agree} of ${bundles.length}.`);
  const counts = CLASSES.map((name) => `${name} ${entries.filter((one) => one.fields.class === name).length}`).join(", ");
  log.out(`  Classes in the report: ${counts}.`);
  log.check("the ground truth names a true cause and a correct class for each of the six bundles, so the comparison above is complete", bundles.every((one) => planted.has(one.name) && expected.has(one.name)));
  return log.save("triage-check.txt");
}

const run = process.argv.includes("--make-failures") ? makeFailures() : Promise.resolve(check());
run.then(
  (ok) => process.exit(ok ? 0 : 1),
  (error) => {
    console.error(`failure-triage-check: ${error instanceof Error ? error.message : error}`);
    process.exit(1);
  },
);

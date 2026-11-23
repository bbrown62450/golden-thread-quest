/*
 * The check for the playwright-data-isolation quest. It produces the two logs:
 *
 *   logs/shuffle-run.txt     the coupled tests failing when reordered, and the isolated tests
 *                            passing forwards, reversed, shuffled, in parallel and twice at once
 *   logs/cleanup-check.txt   what the application held before the runs and after each of them
 *
 * Run it from participant/tests/playwright, with Node 22.18 or later:
 *
 *   node tools/data-isolation-check.ts
 *
 * It starts the made-up customer directory (demo-app/server.mjs) on this computer, runs the
 * tests against it with Playwright, and stops it. It contacts nothing else.
 *
 * What it tests, and how:
 *
 *   - ORDER. Playwright runs the tests of a file in the order they are written and has no
 *     shuffle. So this script runs the tests one at a time, each in its own Playwright run,
 *     in an order it chooses: as written, reversed, and shuffled with a seed it prints.
 *     Set GTQ_SHUFFLE_SEED to repeat a shuffle.
 *   - ONE APPLICATION. Every isolated run, in every order, is against the SAME running
 *     application, one after another, with no reset in between. So a test that left data
 *     behind, or leaned on another's, would show up in a later run.
 *   - BEFORE AND AFTER. Before the isolated runs it asks the application for every customer.
 *     After each run it asks again and compares: every customer that was there before must
 *     still be there, unchanged, and there must be no other.
 *   - THE CHECK CAN FAIL. The coupled tests leave "Test User" behind. The same comparison is
 *     run after them and must REPORT that leftover. A check that could only say "clean" would
 *     prove nothing.
 *   - REAL WORK WAS DONE. The application counts the customers created and removed since it
 *     started. If the tests created none, "nothing left behind" would be empty praise.
 *
 * It ends with exit code 0 only if every check came out as expected. For the coupled tests,
 * "as expected" means they FAILED when reordered.
 */

import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { randomInt, randomUUID } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Customer = { id: string; name: string; plan: string };
type Run = { code: number; output: string; passed: number; failed: number; skipped: number };

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
// Where the two logs are written. tools/planted-faults.ts points this elsewhere, so that its runs do not replace the real logs.
const LOGS = process.env.GTQ_CHECK_LOGS ?? join(PARTICIPANT, "evidence", "playwright-data-isolation", "playwright-attempt-002", "logs");
const PORT = Number(process.env.DEMO_PORT ?? 4793);
const BASE = `http://127.0.0.1:${PORT}`;

const COUPLED = ["coupled: adds Test User through the form", "coupled: upgrades Test User to the plus plan"];
const ISOLATED = [
  "a customer is listed with the plan it was given",
  "upgrading one customer changes that customer and no other",
  "removing one customer through the page removes that customer and no other",
  "a customer added through the form is listed",
  "a second customer with a name already in use is refused",
];
const HALFWAY = "FAILS ON PURPOSE: cleanup still runs when a test fails halfway";

// ---------------------------------------------------------------- the two logs

class Log {
  lines: string[];
  problems: string[];

  constructor(title: string) {
    this.lines = [title, "Recorded by tools/data-isolation-check.ts. The application is a made-up customer directory on this computer. Nobody in it is real."];
    this.problems = [];
  }

  out(text = ""): void {
    this.lines.push(text);
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
    .split(REPO).join("REPO")
    .split(homedir()).join("HOME")
    .replace(/\n{3,}/g, "\n\n");
}

// ---------------------------------------------------------------- the application

async function reachable(): Promise<boolean> {
  try {
    return (await fetch(`${BASE}/healthz`)).ok;
  } catch {
    return false;
  }
}

async function startApp(): Promise<ChildProcess> {
  if (await reachable()) {
    throw new Error(`something is already listening on port ${PORT}. Stop it, or set DEMO_PORT to a free port.`);
  }
  const child = spawn(process.execPath, ["demo-app/server.mjs"], { cwd: TESTS, env: { ...process.env, DEMO_PORT: String(PORT) }, stdio: "ignore" });
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

async function customers(): Promise<Customer[]> {
  return (await (await fetch(`${BASE}/api/customers`)).json()) as Customer[];
}

async function stats(): Promise<{ created: number; removed: number }> {
  return (await (await fetch(`${BASE}/api/stats`)).json()) as { created: number; removed: number };
}

// ---------------------------------------------------------------- running tests

function playwrightArgs(file: string, options: { title?: string; workers: number; parallel?: boolean; timeout?: number }): string[] {
  const args = ["test", "-c", "playwright.isolation.config.ts", file, `--workers=${options.workers}`];
  if (options.title) args.push("-g", options.title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (options.parallel) args.push("--fully-parallel");
  if (options.timeout) args.push(`--timeout=${options.timeout}`);
  return args;
}

function shown(args: string[]): string {
  return "npx playwright " + args.map((part) => (/[^\w=.:/@-]/.test(part) ? `'${part}'` : part)).join(" ");
}

function environment(marker: string, extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, DEMO_PORT: String(PORT), GTQ_RUN_MARKER: marker, FORCE_COLOR: "0", ...extra };
  delete env.NO_COLOR;
  return env;
}

function counted(code: number, raw: string): Run {
  const output = tidy(raw);
  const number = (word: string) => Number(new RegExp(`(\\d+) ${word}`).exec(output)?.[1] ?? 0);
  return { code, output, passed: number("passed"), failed: number("failed"), skipped: number("skipped") };
}

function run(args: string[], marker: string, extra: Record<string, string> = {}): Run {
  const done = spawnSync(process.execPath, [CLI, ...args], { cwd: TESTS, env: environment(marker, extra), encoding: "utf8" });
  return counted(done.status ?? 1, `${done.stdout}${done.stderr}`);
}

function runAsync(args: string[], marker: string): Promise<Run> {
  return new Promise((done) => {
    const child = spawn(process.execPath, [CLI, ...args], { cwd: TESTS, env: environment(marker) });
    let raw = "";
    child.stdout.on("data", (chunk) => (raw += chunk));
    child.stderr.on("data", (chunk) => (raw += chunk));
    child.on("exit", (code) => done(counted(code ?? 1, raw)));
  });
}

/** Run the given tests one at a time, in the given order, each in its own Playwright run. */
function inOrder(log: Log, file: string, titles: string[], marker: string, timeout?: number): Run[] {
  const runs: Run[] = [];
  titles.forEach((title, position) => {
    const args = playwrightArgs(file, { title, workers: 1, timeout });
    const result = run(args, marker);
    runs.push(result);
    log.out(`run ${position + 1} of ${titles.length}: ${title}`);
    log.block(shown(args), result.output, result.code);
  });
  return runs;
}

/** A shuffle that the same seed always repeats. */
function shuffled<T>(items: T[], seed: number): T[] {
  let state = seed >>> 0;
  const next = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const other = Math.floor(next() * (index + 1));
    [copy[index], copy[other]] = [copy[other], copy[index]];
  }
  return copy;
}

const marker = (word: string) => `${word}-${randomUUID().slice(0, 8)}`;
const allPassed = (runs: Run[]) => runs.every((one) => one.code === 0 && one.passed === 1 && one.failed === 0);

// ---------------------------------------------------------------- comparing before and after

type Difference = { leftovers: Customer[]; missing: Customer[]; altered: Customer[] };

function compare(before: Customer[], now: Customer[]): Difference {
  const then = new Map(before.map((one) => [one.id, one]));
  const current = new Map(now.map((one) => [one.id, one]));
  return {
    leftovers: now.filter((one) => !then.has(one.id)),
    missing: before.filter((one) => !current.has(one.id)),
    altered: before.filter((one) => current.has(one.id) && JSON.stringify(current.get(one.id)) !== JSON.stringify(one)),
  };
}

function describe(log: Log, title: string, now: Customer[], difference: Difference, tally: { created: number; removed: number }): void {
  log.out(title);
  log.out(`  customers in the application now:          ${now.length}`);
  log.out(`  created by tests since it started:         ${tally.created}`);
  log.out(`  removed since it started:                  ${tally.removed}`);
  log.out(`  left behind (not there before the runs):   ${difference.leftovers.length}${difference.leftovers.map((one) => `\n      ${JSON.stringify(one.name)}, id ${one.id}`).join("")}`);
  log.out(`  there before and now missing:              ${difference.missing.length}`);
  log.out(`  there before and now different:            ${difference.altered.length}`);
}

// ---------------------------------------------------------------- the check

async function main(): Promise<number> {
  const shuffle = new Log("Order and parallel runs. playwright-data-isolation, attempt playwright-attempt-002");
  const cleanup = new Log("What the runs left behind. playwright-data-isolation, attempt playwright-attempt-002");
  shuffle.out("Each block between dashed lines is what Playwright printed. Folder names of this computer are shown as REPO and HOME.");
  shuffle.out("Playwright runs a file's tests in the order written, so to reorder them each test is run on its own, one after another.");

  // ---- the coupled tests: three fresh applications, one for each demonstration
  shuffle.part("PART 1. The coupled tests, in the order written, on a freshly started application");
  let app = await startApp();
  let runs = inOrder(shuffle, "coupled.spec.ts", COUPLED, "coupled", 5000);
  shuffle.check("both pass: in this order, on an application nobody has used, the fault does not show", allPassed(runs));
  const afterCoupled = compare(STARTS_WITH, await customers());
  await stopApp(app);

  shuffle.part("PART 2. The coupled tests REVERSED, on a freshly started application (criterion 6)");
  app = await startApp();
  runs = inOrder(shuffle, "coupled.spec.ts", [...COUPLED].reverse(), "coupled", 5000);
  shuffle.check("\"upgrades Test User\" FAILS when it runs first: it needs a customer that only the other test creates", runs[0].code !== 0 && runs[0].failed === 1);
  shuffle.check("the failure is the missing customer: Playwright waited for the button \"Upgrade Test User\" and it never appeared",
    /Upgrade Test User/.test(runs[0].output) && /Timeout|waiting for/.test(runs[0].output));
  shuffle.check("\"adds Test User\" still passes when it runs second. Only the one that leaned on the other broke", runs[1].code === 0 && runs[1].passed === 1);
  await stopApp(app);

  shuffle.part("PART 3. The coupled tests run TWICE, in the order written, against the same application");
  shuffle.out("This is the scenario: two testers, or one tester twice, and a customer called Test User.");
  app = await startApp();
  runs = inOrder(shuffle, "coupled.spec.ts", [...COUPLED, ...COUPLED], "coupled", 5000);
  shuffle.check("the first time, both pass", allPassed(runs.slice(0, 2)));
  shuffle.check("the second time, \"adds Test User\" FAILS: the first run's Test User is still there, and the application refuses a second one",
    runs[2].code !== 0 && runs[2].failed === 1 && /already exists|status/.test(runs[2].output));
  await stopApp(app);

  // ---- the isolated tests: ONE application for every run that follows
  shuffle.part("PART 4. The isolated tests, in the order written (criterion 4)");
  shuffle.out("From here to the end, every run is against ONE running application, with no reset in between.");
  app = await startApp();
  const before = await customers();
  cleanup.part("PART 1. Before any isolated test ran: the data that was already there");
  cleanup.out("The application was started and asked for every customer. These four stand for data that existed before the tests:");
  for (const one of before) cleanup.out(`  ${JSON.stringify(one.name)}, plan ${one.plan}, id ${one.id}`);
  cleanup.check("the application starts with 4 customers, and none of them was made by a test", before.length === 4 && (await stats()).created === 0);
  cleanup.check("one of them, \"Test Userson\", has a name that starts with \"Test\". A cleanup that deleted by name pattern would take it", before.some((one) => one.name === "Test Userson"));

  let part = 1;
  const after = async (title: string, created: number): Promise<Difference> => {
    part += 1;
    const now = await customers();
    const difference = compare(before, now);
    const tally = await stats();
    cleanup.part(`PART ${part}. After ${title}`);
    describe(cleanup, "This script asked the application for every customer again, and compared with part 1:", now, difference, tally);
    cleanup.check(`the tests did real work: ${tally.created} customers were created in all so far, ${created} of them in this run`, tally.created >= created && created > 0);
    cleanup.check("no test data remains: the application holds no customer that was not there before the runs", difference.leftovers.length === 0);
    cleanup.check("no data that existed before was removed or altered: each of the 4 is still there with the same name, plan and id (criterion 7)",
      difference.missing.length === 0 && difference.altered.length === 0 && before.length === 4);
    return difference;
  };
  let made = 0;
  const createdSince = async (): Promise<number> => {
    const total = (await stats()).created;
    const fresh = total - made;
    made = total;
    return fresh;
  };

  runs = inOrder(shuffle, "isolated.spec.ts", ISOLATED, marker("fwd"));
  shuffle.check("all 5 pass in the order written", allPassed(runs) && runs.length === 5);
  await after("the run in the order written", await createdSince());

  shuffle.part("PART 5. The isolated tests REVERSED (criterion 4)");
  runs = inOrder(shuffle, "isolated.spec.ts", [...ISOLATED].reverse(), marker("rev"));
  shuffle.check("all 5 pass in reversed order", allPassed(runs) && runs.length === 5);
  await after("the reversed run", await createdSince());

  shuffle.part("PART 6. The isolated tests in RANDOM order (criterion 4)");
  // A shuffle of five can come out as the order written, or its reverse. Those two were run above, so such a
  // seed is passed over, and the next one is tried, until the order is a new one.
  let seed = Number(process.env.GTQ_SHUFFLE_SEED ?? randomInt(1, 2 ** 31));
  let order = shuffled(ISOLATED, seed);
  let passedOver = 0;
  while (order.join() === ISOLATED.join() || order.join() === [...ISOLATED].reverse().join()) {
    seed += 1;
    passedOver += 1;
    order = shuffled(ISOLATED, seed);
  }
  if (passedOver) shuffle.out(`${passedOver} seed(s) gave the order written or its reverse, which were run above, and were passed over.`);
  shuffle.out(`The shuffle's seed is ${seed}. Run this script with GTQ_SHUFFLE_SEED=${seed} to get the same order again.`);
  shuffle.out(`The order it gave, by position in the file: ${order.map((title) => ISOLATED.indexOf(title) + 1).join(", ")}`);
  runs = inOrder(shuffle, "isolated.spec.ts", order, marker("rnd"));
  shuffle.check("the shuffled order holds each of the 5 tests once", [...order].sort().join() === [...ISOLATED].sort().join());
  shuffle.check("all 5 pass in the shuffled order", allPassed(runs) && runs.length === 5);
  await after("the shuffled run", await createdSince());

  shuffle.part("PART 7. The isolated tests IN PARALLEL (criterion 5)");
  shuffle.out("One Playwright run of the whole file, with 5 workers and every test allowed to run at the same time as the others.");
  let args = playwrightArgs("isolated.spec.ts", { workers: 5, parallel: true });
  let result = run(args, marker("par"));
  shuffle.block(shown(args), result.output, result.code);
  shuffle.check("Playwright used 5 workers, so the 5 tests ran at the same time", /using 5 workers/.test(result.output));
  shuffle.check("all 5 pass in parallel. The sixth test, which fails on purpose, is skipped unless asked for", result.code === 0 && result.passed === 5 && result.failed === 0 && result.skipped === 1);
  await after("the parallel run", await createdSince());

  shuffle.part("PART 8. Stretch goal: the whole suite TWICE AT ONCE against the same application");
  shuffle.out("Two separate Playwright runs started together, each with 3 workers. This is two testers at the same time.");
  args = playwrightArgs("isolated.spec.ts", { workers: 3, parallel: true });
  const [first, second] = await Promise.all([runAsync(args, marker("twin-a")), runAsync(args, marker("twin-b"))]);
  shuffle.out("the first of the two:");
  shuffle.block(shown(args), first.output, first.code);
  shuffle.out("the second of the two:");
  shuffle.block(shown(args), second.output, second.code);
  shuffle.check("both runs pass all 5, though they shared one application and ran at once", [first, second].every((one) => one.code === 0 && one.passed === 5 && one.failed === 0));
  await after("the two runs at once", await createdSince());

  shuffle.part("PART 9. A test that fails halfway");
  shuffle.out("One test is made to fail after it has created two customers. It only runs when asked, with GTQ_FAIL_HALFWAY=1.");
  args = playwrightArgs("isolated.spec.ts", { title: HALFWAY, workers: 1 });
  result = run(args, marker("half"), { GTQ_FAIL_HALFWAY: "1" });
  shuffle.block(`GTQ_FAIL_HALFWAY=1 ${shown(args)}`, result.output, result.code);
  shuffle.check("the test FAILS, as it was made to, at the line that says it fails on purpose", result.code !== 0 && result.failed === 1 && /fails here on purpose/.test(result.output));
  shuffle.check("the failure is the test's own, not the cleanup's: no cleanup error was reported", !/cleanup should remove/.test(result.output));
  const halfway = await createdSince();
  const removedBefore = (await stats()).removed;
  const afterHalfway = await after("the test that fails halfway", halfway);
  cleanup.check("that test created 2 customers before it failed, and both are gone: cleanup ran although the test did not finish",
    halfway === 2 && afterHalfway.leftovers.length === 0 && removedBefore === (await stats()).created);

  const final = await customers();
  const total = await stats();
  await stopApp(app);

  cleanup.part(`PART ${part + 1}. The check can find leftovers: the coupled tests`);
  cleanup.out("The same comparison, run after the coupled tests of logs/shuffle-run.txt part 1, on their own fresh application.");
  cleanup.out(`  left behind (not there when the application started):   ${afterCoupled.leftovers.length}${afterCoupled.leftovers.map((one) => `\n      ${JSON.stringify(one.name)}, plan ${one.plan}`).join("")}`);
  cleanup.check("it reports 1 leftover, \"Test User\": the coupled tests clean nothing up, and this check sees it",
    afterCoupled.leftovers.length === 1 && afterCoupled.leftovers[0].name === "Test User");
  cleanup.check("so \"no test data remains\" above is a finding and not something this check always says", afterCoupled.leftovers.length > 0);

  cleanup.part(`PART ${part + 2}. In all`);
  cleanup.out(`Across every isolated run, against the one application: ${total.created} customers created by tests, ${total.removed} removed.`);
  cleanup.check("every customer a test created was removed: the two counts are the same", total.created === total.removed && total.created > 0);
  cleanup.check("at the end the application holds exactly what it held at the start, compared as a whole", JSON.stringify(final) === JSON.stringify(before));
  cleanup.check("\"Test Userson\" is still there, unchanged, though its name starts with \"Test\"", final.some((one) => one.id === "seed-4" && one.name === "Test Userson" && one.plan === "plus"));

  const ok = shuffle.save("shuffle-run.txt");
  return cleanup.save("cleanup-check.txt") && ok ? 0 : 1;
}

/** The four customers the application starts with. The coupled comparison is against these. */
const STARTS_WITH: Customer[] = [
  { id: "seed-1", name: "Asha Verma", plan: "plus" },
  { id: "seed-2", name: "Bo Lindqvist", plan: "basic" },
  { id: "seed-3", name: "Carmen Ortiz", plan: "basic" },
  { id: "seed-4", name: "Test Userson", plan: "plus" },
];

main().then(
  (code) => process.exit(code),
  (error) => {
    console.error(`data-isolation-check: ${error instanceof Error ? error.message : error}`);
    process.exit(1);
  },
);

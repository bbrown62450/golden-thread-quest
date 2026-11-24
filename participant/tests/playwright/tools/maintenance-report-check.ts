/*
 * The check for the playwright-maintenance-report quest. It does two separate jobs, in this order.
 *
 *   node tools/maintenance-report-check.ts --before
 *       Run BEFORE the report is written. It takes the checksum of the failing test, needs-maintenance.spec.ts, and
 *       runs that test against the checkout before the redesign and after it. It writes logs/before-report.txt in
 *       the attempt folder. That file is the "before" of the unchanged check, and the evidence the report cites.
 *
 *   node tools/maintenance-report-check.ts
 *       Run AFTER the report is written. It writes logs/unchanged-check.txt.
 *
 *   node tools/maintenance-report-check.ts --copy
 *       Prints the test as it would read after the report's changes, so that it can be compared with what a person
 *       makes of the same report. It writes nothing.
 *
 * Run it from participant/tests/playwright, with Node 22.18 or later. It starts the made-up checkout
 * (demo-app/checkout-server.mjs and checkout-server.before.mjs) on this computer, on 127.0.0.1, and stops it. It
 * contacts nothing else.
 *
 * IT NEVER WRITES TO THE TEST. Every change it tries is made to a COPY, in a scratch folder beside the test that it
 * deletes when it ends.
 *
 * WHAT THE CHECK TESTS
 *   1. UNCHANGED (criterion 5). The test's checksum now is the checksum taken by --before, the report was written
 *      after that, and the checksum is the same again when every run below has finished.
 *   2. THE REPORT (criteria 1, 3, 4 and 6). It has each part the quest asks for, cites evidence files that exist, and
 *      what it says of the failure is what the saved evidence says.
 *   3. THE CHANGE CAN BE CARRIED OUT FROM THE REPORT (criteria 2 and 7). The line-by-line list is read out of the
 *      report and applied to a copy of the test by this program. Each row must name a line, the text on it now, and
 *      the text to put there. A row whose "now" text is not what the file has stops the check.
 *   4. THE CHANGE DOES NOT WEAKEN THE TEST. The report lists what would show weakening. Each is tried here:
 *        W1  the copy has as many expect() calls as the test;
 *        W2  every amount in the test is in the copy, on the same line, with the same digits;
 *        W3  nothing that loosens a test was added: a contains or pattern match, soft, skip, fixme, only, a longer
 *            timeout, a negation, a try, or an assertion commented out;
 *        W4  only the lines the report lists differ. Every other line is the same, and no line was added or removed;
 *        W5  against the redesigned checkout the copy FAILS, at the tax line, expecting the amount the business rule
 *            gives. And against a scratch copy of that checkout with its two tax lines put back, the copy PASSES;
 *        W6  every deliberate fault that the test caught in the old checkout, the copy catches in the new one.
 *   5. THE TEMPTING FIXES, as a contrast. Three wrong ways of getting the test to pass are applied to further copies,
 *      and the same six questions are asked of each.
 *   6. That the check can fail: the report is spoiled in one way at a time, in memory, and each must be reported.
 *
 * WHAT IT DOES NOT TEST
 *   Whether the new tax figure is a bug. Nobody here can know: it is a question for whoever owns the rule. The check
 *   shows that the report does not answer it by editing the test.
 */

import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-maintenance-report", "playwright-attempt-005");
const LOGS = join(ATTEMPT, "logs");
const SPEC = join(TESTS, "needs-maintenance.spec.ts");
const REPORT = join(PARTICIPANT, "context", "playwright", "maintenance-report.md");
const BEFORE = join(LOGS, "before-report.txt");
const OLD_APP = "demo-app/checkout-server.before.mjs";
const NEW_APP = "demo-app/checkout-server.mjs";
const FAULTS = ["tax-left-out-of-total", "tax-rate-wrong", "tax-shown-wrong", "discount-ignored", "total-ignores-discount", "subtotal-wrong", "button-dead", "confirmation-wrong"];
const PARTS = ["## 1. Cause", "## 2. Evidence", "## 3. The proposed change", "## 4. The change, line by line", "## 5. The business assertion that must be preserved",
  "## 6. What would show that the change weakened the test", "## 7. A test change, or a possible product bug", "## 8. Options and effort", "## 9. The triage this follows"];

type Run = { status: string; line: number | null; message: string };
type Change = { number: number; line: number; now: string; to: string };

const sha = (text: string) => createHash("sha256").update(text).digest("hex");
const tidy = (text: string) => text.replace(/\u001b\[[0-9;]*m/g, "").split(REPO + "/").join("").split(REPO).join("REPO");

class Log {
  lines: string[];
  failed: string[] = [];
  count = 0;
  constructor(...head: string[]) { this.lines = [...head]; }
  out(...lines: string[]) { this.lines.push(...(lines.length ? lines : [""])); }
  part(title: string, ...lines: string[]) { this.lines.push("", "=".repeat(78), title, ...lines); }
  check(label: string, ok: boolean) {
    this.count += 1;
    this.lines.push(`  ${ok ? "ok  " : "FAIL"} ${label}`);
    if (!ok) this.failed.push(label);
  }
  save(file: string) {
    this.lines.push("", this.failed.length ? `RESULT: ${this.failed.length} OF ${this.count} CHECKS FAILED.` : `RESULT: ALL CHECKS PASSED. ${this.count} checks.`);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, this.lines.map(tidy).join("\n") + "\n");
    console.log(`${relative(ATTEMPT, file)}: ${this.lines[this.lines.length - 1]}`);
    for (const label of this.failed) console.log(`  FAILED: ${label}`);
  }
}

// ---------------------------------------------------------------- the application and the test runner

let port = 4801 + Math.floor(Math.random() * 400);

/**
 * The redesigned checkout with its two tax lines put back to what they were before the redesign, and nothing else
 * changed. Written to the scratch folder, never over the application. It is how the check asks "what would this test
 * do if only the layout had changed?".
 */
function layoutOnlyApp(scratch: string): string {
  let source = readFileSync(join(TESTS, NEW_APP), "utf8");
  for (const [now, was] of [["const tax = subtotal * (", "const tax = goods * ("], ['"tax-shown-wrong" ? subtotal * 0.25', '"tax-shown-wrong" ? goods * 0.25']]) {
    if (source.split(now).length !== 2) throw new Error("The redesigned checkout does not have the tax line this check expects to put back.");
    source = source.replace(now, was);
  }
  const file = join(scratch, "checkout-layout-only.mjs");
  writeFileSync(file, source);
  return file;
}

async function startApp(file: string, env: Record<string, string> = {}): Promise<ChildProcess> {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    port += 1;
    const child = spawn(process.execPath, [file], { cwd: TESTS, env: { ...process.env, CHECKOUT_PORT: String(port), ...env }, stdio: "ignore" });
    for (let wait = 0; wait < 40; wait += 1) {
      await new Promise((done) => setTimeout(done, 50));
      if (child.exitCode !== null) break;
      try {
        const answer = await fetch(`http://127.0.0.1:${port}/healthz`, { headers: { connection: "close" } });
        if (answer.ok) return child;
      } catch { /* not listening yet */ }
    }
    child.kill();
  }
  throw new Error(`The checkout could not be started from ${file}.`);
}

async function stopApp(child: ChildProcess) {
  child.kill();
  await new Promise((done) => (child.exitCode !== null ? done(null) : child.once("exit", done)));
}

function runTest(testDir: string | null): Run {
  const env: Record<string, string | undefined> = { ...process.env, CHECKOUT_PORT: String(port), GTQ_TEST_DIR: testDir ?? "", FORCE_COLOR: "0" };
  if (!testDir) delete env.GTQ_TEST_DIR;
  const done = spawnSync(process.execPath, [CLI, "test", "--config", "maintenance.config.ts", "--reporter", "json"], { cwd: TESTS, env, encoding: "utf8", maxBuffer: 32 * 1024 * 1024 });
  try {
    const report = JSON.parse(done.stdout);
    const spec = report.suites[0].specs[0];
    const result = spec.tests[0].results[0];
    const error = result.error ?? result.errors?.[0];
    const message = error ? tidy(String(error.message)).split("\n").filter((line) => /Locator:|Expected|Received|Timeout|Error:/.test(line)).map((line) => line.trim()).join(" | ") : "";
    return { status: result.status, line: error?.location?.line ?? null, message };
  } catch {
    return { status: "did not run", line: null, message: tidy((done.stderr || done.stdout || "").slice(0, 300)) };
  }
}

async function runAgainst(app: string, env: Record<string, string>, testDir: string | null): Promise<Run> {
  const child = await startApp(app, env);
  try { return runTest(testDir); } finally { await stopApp(child); }
}

const shown = (run: Run) => (run.status === "passed" ? "passed" : `${run.status} at line ${run.line ?? "?"}: ${run.message}`);

// ---------------------------------------------------------------- the report

function readChanges(report: string): Change[] {
  const changes: Change[] = [];
  const pattern = /^### Change (\d+) · line (\d+)\n+Now:\n+```ts\n([^\n]*)\n```\n+Change to:\n+```ts\n([^\n]*)\n```/gm;
  for (const match of report.matchAll(pattern)) changes.push({ number: Number(match[1]), line: Number(match[2]), now: match[3], to: match[4] });
  return changes;
}

function apply(source: string, changes: Change[]): { text: string; problems: string[] } {
  const lines = source.split("\n");
  const problems: string[] = [];
  const seen = new Set<number>();
  for (const change of changes) {
    if (seen.has(change.line)) problems.push(`Change ${change.number} is for line ${change.line}, which another change already covers.`);
    seen.add(change.line);
    if (lines[change.line - 1] === undefined) problems.push(`Change ${change.number} names line ${change.line}, and the test has ${lines.length - 1} lines.`);
    else if (lines[change.line - 1] !== change.now) problems.push(`Change ${change.number} says line ${change.line} now reads one thing, and the test has another there.`);
    else if (change.now === change.to) problems.push(`Change ${change.number} changes nothing on line ${change.line}.`);
    else lines[change.line - 1] = change.to;
  }
  return { text: lines.join("\n"), problems };
}

const amounts = (line: string) => line.match(/\d+\.\d\d/g) ?? [];
const LOOSENERS: [string, RegExp][] = [["a contains match", /toContainText|toContain\(/], ["a pattern match", /toMatch|toHaveText\(\s*\/|RegExp/], ["soft", /\.soft\b/],
  ["skip, fixme or fail", /test\.(skip|fixme|fail)|\.skip\(|\.fixme\(/], ["only", /\.only\b/], ["a longer timeout", /timeout\s*:|setTimeout\(|waitForTimeout/], ["a negation", /\.not\./],
  ["a try", /\btry\s*\{|\.catch\(/], ["an assertion commented out", /^\s*\/\/.*\bexpect\(/m]];

/** The six signs of weakening that need no browser: W1 to W4. Returns the ones found. */
function weakenedOnPaper(original: string, copy: string, listed: number[]): string[] {
  const found: string[] = [];
  const before = original.split("\n");
  const after = copy.split("\n");
  const count = (text: string) => (text.match(/\bexpect\(/g) ?? []).filter(() => true).length - (text.match(/^\s*\/\/.*\bexpect\(/gm) ?? []).length;
  if (count(copy) < count(original)) found.push(`W1: the copy has ${count(copy)} expect() calls and the test has ${count(original)}`);
  const lost: string[] = [];
  before.forEach((line, index) => {
    const mine = amounts(line);
    const theirs = amounts(after[index] ?? "");
    if (!line.trim().startsWith("//") && mine.join(",") !== theirs.join(",")) lost.push(`line ${index + 1} had ${mine.join(", ") || "no amount"} and now has ${theirs.join(", ") || "none"}`);
  });
  if (lost.length) found.push(`W2: an amount changed or went: ${lost.join("; ")}`);
  const loose = LOOSENERS.filter(([, pattern]) => pattern.test(copy) && !pattern.test(original)).map(([name]) => name);
  if (loose.length) found.push(`W3: added ${loose.join(", ")}`);
  const differ = before.map((line, index) => (line === after[index] ? 0 : index + 1)).filter(Boolean);
  const unlisted = differ.filter((line) => !listed.includes(line));
  if (before.length !== after.length) found.push(`W4: the copy has ${after.length - 1} lines and the test has ${before.length - 1}`);
  else if (unlisted.length) found.push(`W4: line ${unlisted.join(", ")} differs and the report does not list it`);
  return found;
}

// ---------------------------------------------------------------- the two jobs

async function before() {
  const log = new Log("Before the report is written. playwright-maintenance-report, attempt playwright-attempt-005",
    "Recorded by tools/maintenance-report-check.ts --before. The checkout is made up and ran on this computer only.");
  const source = readFileSync(SPEC, "utf8");
  log.part("THE TEST, AS IT IS BEFORE ANY REPORT");
  log.out("file:     participant/tests/playwright/needs-maintenance.spec.ts", `sha256:   ${sha(source)}`, `bytes:    ${Buffer.byteLength(source)}`, `lines:    ${source.split("\n").length - 1}`,
    `taken at: ${new Date().toISOString()}`, `report:   ${existsSync(REPORT) ? "participant/context/playwright/maintenance-report.md ALREADY EXISTS" : "participant/context/playwright/maintenance-report.md does not exist yet"}`);
  log.check("no maintenance report exists yet", !existsSync(REPORT));
  log.part("THE FAILURE (the evidence the report cites)");
  const old = await runAgainst(OLD_APP, {}, null);
  const now = await runAgainst(NEW_APP, {}, null);
  log.out(`Against the checkout BEFORE the redesign, ${OLD_APP}:`, `  ${shown(old)}`, `Against the checkout AFTER the redesign, ${NEW_APP}, which is the one in use:`, `  ${shown(now)}`);
  log.check("the test passed before the redesign", old.status === "passed");
  log.check("the test fails after it", now.status === "failed");
  const after = readFileSync(SPEC, "utf8");
  log.check("running the test did not change it: the checksum is the same", sha(after) === sha(source));
  log.save(BEFORE);
  return log.failed.length ? 1 : 0;
}

async function main() {
  const log = new Log("The unchanged check. playwright-maintenance-report, attempt playwright-attempt-005",
    "Recorded by tools/maintenance-report-check.ts. The checkout is made up and ran on this computer only, on 127.0.0.1.",
    "Every change tried below was made to a copy of the test in a scratch folder. The test itself was not written to.");
  const original = readFileSync(SPEC, "utf8");
  const report = existsSync(REPORT) ? readFileSync(REPORT, "utf8") : "";
  const beforeText = existsSync(BEFORE) ? readFileSync(BEFORE, "utf8") : "";
  const scratch = mkdtempSync(join(TESTS, ".maintenance-scratch-"));
  const copyDir = (name: string, text: string) => {
    const dir = join(scratch, name);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "copy.spec.ts"), text);
    return dir;
  };
  try {
    log.part("PART 1. The test file is unchanged when the report is written (criterion 5)");
    const recorded = beforeText.match(/^sha256:\s+([0-9a-f]{64})$/m)?.[1] ?? "";
    const takenAt = beforeText.match(/^taken at: (\S+)$/m)?.[1] ?? "";
    const reportTime = report ? statSync(REPORT).mtime.toISOString() : "";
    log.out("participant/tests/playwright/needs-maintenance.spec.ts",
      `  sha256 BEFORE the report was written, from logs/before-report.txt, taken at ${takenAt}:`, `    ${recorded}`,
      `  the report, participant/context/playwright/maintenance-report.md, was last written at ${reportTime}`,
      `  sha256 AFTER the report was written, taken now, at ${new Date().toISOString()}:`, `    ${sha(original)}`);
    log.check("logs/before-report.txt exists, and says that no report existed when it was taken", /maintenance-report\.md does not exist yet/.test(beforeText) && recorded.length === 64);
    log.check("the report was written after that checksum was taken", Boolean(report) && Boolean(takenAt) && reportTime > takenAt);
    log.check("the test's checksum now is the checksum taken before the report was written", recorded === sha(original));
    const tracked = spawnSync("git", ["ls-files", "--error-unmatch", relative(REPO, SPEC)], { cwd: REPO, encoding: "utf8" }).status === 0;
    const status = spawnSync("git", ["status", "--porcelain", "--", relative(REPO, SPEC)], { cwd: REPO, encoding: "utf8" }).stdout.trim();
    const blob = spawnSync("git", ["hash-object", relative(REPO, SPEC)], { cwd: REPO, encoding: "utf8" }).stdout.trim();
    log.out(`  git: ${tracked ? `the file is tracked, and git status says "${status || "unchanged"}"` : "the file is new and not yet committed, so git has no earlier version to compare. The checksum above is the comparison"}. git hash-object: ${blob}`);

    log.part("PART 2. The report has what the quest asks for, and what it says of the failure is what the evidence says (criteria 1, 3, 4, 6)");
    for (const part of PARTS) log.check(`the report has the part "${part.slice(3)}"`, report.includes(`\n${part}\n`));
    const cited = [...new Set([...report.matchAll(/`(participant\/[^`\s]+)`/g)].map((match) => match[1]))];
    const missing = cited.filter((path) => !existsSync(join(REPO, path)) && !/attempt-001/.test(path));
    log.out(`Files the report cites: ${cited.length}. ${cited.join(", ")}`);
    log.check("every file the report cites exists", cited.length >= 4 && missing.length === 0);
    const old = await runAgainst(OLD_APP, {}, null);
    const now = await runAgainst(NEW_APP, {}, null);
    log.out("", `The test, run now against the checkout before the redesign: ${shown(old)}`, `The test, run now against the checkout in use:              ${shown(now)}`);
    log.check("the test passes against the checkout before the redesign and fails against the one in use, as the report says", old.status === "passed" && now.status === "failed");
    log.check(`the report gives the line the test fails at, line ${now.line}, and the locator it could not find`, report.includes(`line ${now.line}`) && report.includes("#subtotal"));
    log.check("the report names the business assertion to preserve, with its line and its amount: the tax, 7.20", /## 5\.[\s\S]*line 11[\s\S]*7\.20[\s\S]*## 6\./i.test(report));
    log.check("the report says the tax figure is a POSSIBLE PRODUCT BUG and that the expected amount is not to be changed", /POSSIBLE PRODUCT BUG/.test(report) && /8\.00/.test(report));

    log.part("PART 3. The change can be carried out from the report alone (criteria 2 and 7)");
    const changes = readChanges(report);
    const result = apply(original, changes);
    log.out(`Changes read out of the report's part 4: ${changes.length}, for lines ${changes.map((change) => change.line).join(", ")}.`);
    for (const change of changes) log.out(`  line ${String(change.line).padStart(2)}  now: ${change.now.trim()}`, `           to:  ${change.to.trim()}`);
    log.check("every change names a line whose text now is exactly what the report says it is", changes.length > 0 && result.problems.length === 0);
    const stated = [...(report.match(/^Lines changed: ([\d, ]+)\. Lines not changed: ([\d, ]+)\.$/m) ?? [])];
    const lines = original.split("\n").length - 1;
    const listed = changes.map((change) => change.line);
    const rest = Array.from({ length: lines }, (_, index) => index + 1).filter((line) => !listed.includes(line));
    log.check(`the report's own summary of which lines change and which do not accounts for all ${lines} lines of the test`, stated[1] === listed.join(", ") && stated[2] === rest.join(", "));
    const copy = result.text;
    const changedDir = copyDir("as-the-report-says", copy);
    log.out("", "The copy made by applying those changes, and nothing else:", ...copy.split("\n").slice(5, 16).map((line, index) => `  ${String(index + 6).padStart(2)} ${listed.includes(index + 6) ? "*" : " "} ${line}`), "  * a line the report changes");

    log.part("PART 4. Does the change weaken the test? The report's own six signs, each tried (criterion 4)");
    const paper = weakenedOnPaper(original, copy, listed);
    log.check("W1: the copy has as many expect() calls as the test", !paper.some((sign) => sign.startsWith("W1")));
    log.check("W2: every amount in the test is still in the copy, on the same line, with the same digits", !paper.some((sign) => sign.startsWith("W2")));
    log.check("W3: nothing that loosens a test was added", !paper.some((sign) => sign.startsWith("W3")));
    log.check("W4: only the lines the report lists differ, and no line was added or removed", !paper.some((sign) => sign.startsWith("W4")));
    const changedNow = await runAgainst(NEW_APP, {}, changedDir);
    const layoutOnly = layoutOnlyApp(scratch);
    const changedLayoutOnly = await runAgainst(layoutOnly, {}, changedDir);
    log.out("", `The copy, against the checkout in use: ${shown(changedNow)}`,
      `The copy, against a scratch copy of that checkout with its two tax lines put back as they were before the redesign: ${shown(changedLayoutOnly)}`);
    log.check("W5: against the checkout in use the copy fails at line 11, the tax line, expecting £7.20 and receiving £8.00. The business assertion is alive and is the only thing failing",
      changedNow.status === "failed" && changedNow.line === 11 && changedNow.message.includes("£7.20") && changedNow.message.includes("£8.00"));
    log.check("W5: with the tax lines put back, the copy passes, all the way through the button and the confirmation. So the change is complete: the layout is dealt with, and nothing but the tax figure stands in the way", changedLayoutOnly.status === "passed");
    log.out("", "W6. Eight deliberate faults, one at a time, switched on by CHECKOUT_FAULT. The test against the OLD checkout. The copy against the NEW one with its tax lines put back.",
      "  fault                    the test, old checkout        the copy, new checkout");
    let caughtBefore = 0;
    let caughtAfter = 0;
    let missed: string[] = [];
    for (const fault of FAULTS) {
      const first = await runAgainst(OLD_APP, { CHECKOUT_FAULT: fault }, null);
      const second = await runAgainst(layoutOnly, { CHECKOUT_FAULT: fault }, changedDir);
      caughtBefore += first.status === "failed" ? 1 : 0;
      caughtAfter += second.status === "failed" ? 1 : 0;
      if (first.status === "failed" && second.status !== "failed") missed.push(fault);
      log.out(`  ${fault.padEnd(24)} ${(first.status === "failed" ? `caught at line ${first.line}` : "NOT CAUGHT").padEnd(29)} ${second.status === "failed" ? `caught at line ${second.line}` : "NOT CAUGHT"}`);
    }
    log.check(`W6: the test caught ${caughtBefore} of the 8 faults, and the copy caught ${caughtAfter}. Every fault the test caught, the copy catches`, caughtBefore === 8 && missed.length === 0);

    log.part("PART 5. The tempting fixes, as a contrast. Each makes the test pass. None is proposed");
    const tempting: [string, string, (text: string) => string][] = [
      ["delete the tax assertion, and set the totals to what the page shows", "deleted",
        (text) => text.split("\n").filter((line) => !line.includes("summary-tax") && !line.includes("BUSINESS RULE")).join("\n").split("£43.20").join("£44.00")],
      ["set the expected amounts to what the page shows now", "updated", (text) => text.split("£7.20").join("£8.00").split("£43.20").join("£44.00")],
      ["keep every line, and only check that an amount is shown", "loosened",
        (text) => text.replace('toHaveText("£7.20")', 'toContainText("£")').split('toHaveText("£43.20")').join("toHaveText(/£\\d+\\.\\d\\d/)")],
    ];
    for (const [title, name, edit] of tempting) {
      const wrong = edit(copy);
      const dir = copyDir(name, wrong);
      const run = await runAgainst(NEW_APP, {}, dir);
      const signs = weakenedOnPaper(original, wrong, listed);
      let let_through: string[] = [];
      for (const fault of FAULTS) {
        const faulty = await runAgainst(NEW_APP, { CHECKOUT_FAULT: fault }, dir);
        if (faulty.status !== "failed") let_through.push(fault);
      }
      log.out("", `TEMPTING FIX: ${title}.`, `  against the checkout in use: ${shown(run)}`, ...signs.map((sign) => `  SIGN ${sign}`),
        `  faults it lets through, of 8: ${let_through.length ? let_through.join(", ") : "none"}`);
      log.check(`"${title}" makes the test pass against the checkout in use, and at least one of the report's signs catches it`, run.status === "passed" && signs.length > 0);
    }
    log.out("", "The second of these lets no fault through and is still wrong. It passes because it has taken the new tax figure as correct, which is the",
      "one thing nobody has decided. Only the signs W2 and W5 show it.");

    log.part("PART 6. That this check can fail");
    const spoil = (label: string, expect: string, problems: string[]) => {
      log.out(`Spoiled: ${label}`, ...(problems.length ? problems.map((problem) => `    PROBLEM: ${problem}`) : ["    no problem reported"]));
      log.check(`reported: "${expect}"`, problems.some((problem) => problem.includes(expect)));
    };
    const first = changes[0];
    spoil("the report's first change gives the line's present text with one character different", `Change ${first.number} says line ${first.line} now reads one thing`,
      apply(original, [{ ...first, now: first.now.replace("#subtotal", "#sub-total") }, ...changes.slice(1)]).problems);
    spoil("the report's first change names line 80", "names line 80", apply(original, [{ ...first, line: 80 }, ...changes.slice(1)]).problems);
    spoil("two changes for one line", "which another change already covers", apply(original, [...changes, { ...changes[1], number: 99 }]).problems);
    spoil("the test file edited after the before-checksum was taken (one space added, in memory)", "the checksum differs", sha(original + " ") === recorded ? [] : ["the checksum differs from the one taken before the report was written"]);
    spoil("a change the report does not list, made to the copy (line 6, the test's title)", "W4: line 6 differs", weakenedOnPaper(original, copy.replace("checkout shows the right amounts", "checkout works"), listed));
    spoil("the expected tax changed in the copy from 7.20 to 8.00", "W2: an amount changed or went", weakenedOnPaper(original, copy.split("7.20").join("8.00"), listed));
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
  log.part("AT THE END");
  const last = readFileSync(SPEC, "utf8");
  log.out(`sha256 of participant/tests/playwright/needs-maintenance.spec.ts, after every run above: ${sha(last)}`);
  log.check("the test is still byte for byte what it was before the report was written, and the scratch folder is gone", sha(last) === (beforeText.match(/^sha256:\s+([0-9a-f]{64})$/m)?.[1] ?? "") && !existsSync(scratch));
  const still = await runAgainst(NEW_APP, {}, null);
  log.check("the handed-in test still fails against the checkout in use. The proposed change was not applied to it", still.status === "failed" && still.line === 8);
  log.save(join(LOGS, "unchanged-check.txt"));
  return log.failed.length ? 1 : 0;
}

if (process.argv.includes("--copy")) {
  // Prints the test as it would read after the report's changes. It writes nothing.
  const result = apply(readFileSync(SPEC, "utf8"), readChanges(readFileSync(REPORT, "utf8")));
  if (result.problems.length) console.error(result.problems.join("\n"));
  process.stdout.write(result.text);
  process.exit(result.problems.length ? 1 : 0);
}
process.exit(process.argv.includes("--before") ? await before() : await main());

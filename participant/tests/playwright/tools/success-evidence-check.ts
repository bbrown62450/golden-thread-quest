/*
 * The check for the playwright-success-evidence quest.
 *
 *   node tools/success-evidence-check.ts
 *
 * Run it from participant/tests/playwright, with Node 22.18 or later. It starts the made-up checkout
 * (demo-app/checkout-server.corrected.mjs) on this computer, on 127.0.0.1, and stops it. It contacts nothing else.
 *
 * WHAT IT WRITES, in the attempt folder
 *   validated/              the evidence of one passing run of meaningful-evidence.spec.ts: for each business rule a
 *                           record (.md) and a picture (.png), and run-output.txt, the run's own list of every step and
 *                           whether anything was captured at it. This folder is emptied and written again each time.
 *   logs/contrast-run.txt   what that run captured; then the same test with a rule broken, six ways; then a scan of
 *                           the validated folder for credentials and personal data.
 *
 * WHAT IT NEVER WRITES TO: the test, the helper, the settings and the application. Every broken application is the
 * corrected one started with its harness switch, or a copy of it in a scratch folder with one line changed. The
 * scratch folder is deleted at the end.
 *
 * WHAT IT DOES NOT SHOW
 *   The pictures are not read by this program. It checks that each is a picture, is the one its record names, and is
 *   much smaller than the page. What is in it is taken from the record's "Text inside the picture", which the helper
 *   reads from the same elements at the same moment. A person or a reader has to look at the pictures themselves.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-success-evidence", "playwright-attempt-007");
const VALIDATED = join(ATTEMPT, "validated");
const SPEC = join(TESTS, "meaningful-evidence.spec.ts");
const HELPER = join(TESTS, "support", "proof.ts");
const SETTINGS = join(TESTS, "success.config.ts");
const APP = join(TESTS, "demo-app", "checkout-server.corrected.mjs");
const PW_OUTPUT = join(REPO, "local-data", "playwright-success", "playwright-output");
const RULES = ["R1-discount", "R2-tax", "R3-total", "R4-charge"];

const sha = (data: string | Buffer) => createHash("sha256").update(data).digest("hex");
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

let nextPort = 5700 + Math.floor(Math.random() * 300);

async function startApp(file: string, env: Record<string, string> = {}): Promise<{ child: ChildProcess; port: number }> {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    nextPort += 1;
    const port = nextPort;
    const child = spawn(process.execPath, [file], { cwd: TESTS, env: { ...process.env, CHECKOUT_PORT: String(port), CHECKOUT_FAULT: "", ...env }, stdio: "ignore" });
    for (let wait = 0; wait < 40; wait += 1) {
      await new Promise((done) => setTimeout(done, 50));
      if (child.exitCode !== null) break;
      try {
        const answer = await fetch(`http://127.0.0.1:${port}/healthz`, { headers: { connection: "close" } });
        if (answer.ok) {
          await new Promise((done) => setTimeout(done, 120));
          if (child.exitCode === null) return { child, port };
          break;
        }
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

type TestRun = { title: string; rule: string; status: string; line: number | null; message: string; attachments: string[] };
type Suite = { tests: TestRun[]; exit: number | null; version: string; durations: number[] };

/** Runs the whole test file against one application, capturing into `proofDir`. Runs are one at a time: they share Playwright's output folder. */
async function runSuite(app: string, env: Record<string, string>, proofDir: string): Promise<Suite> {
  const { child, port } = await startApp(app, env);
  try {
    return await new Promise<Suite>((done) => {
      const runner = spawn(process.execPath, [CLI, "test", "--config", "success.config.ts", "--reporter", "json"], { cwd: TESTS, env: { ...process.env, CHECKOUT_PORT: String(port), GTQ_PROOF_DIR: proofDir, FORCE_COLOR: "0" } });
      let stdout = "";
      runner.stdout.on("data", (chunk) => { stdout += chunk; });
      runner.stderr.on("data", () => {});
      runner.on("close", (exit) => {
        try {
          const report = JSON.parse(stdout);
          const specs = (report.suites ?? []).flatMap((suite: any) => suite.specs ?? []);
          done({ exit, version: String(report.config?.version ?? "not given"), durations: specs.map((spec: any) => spec.tests?.[0]?.results?.[0]?.duration ?? 0), tests: specs.map((spec: any) => {
            const result = spec.tests?.[0]?.results?.[0] ?? {};
            const error = result.error ?? result.errors?.[0];
            const message = error ? tidy(String(error.message)).split("\n").filter((l) => /Locator:|Expected|Received|Error:/.test(l)).map((l) => l.trim()).join(" | ") : "";
            return { title: spec.title, rule: String(spec.title).split(" ")[0], status: result.status ?? "did not run", line: error?.location?.line ?? null, message, attachments: (result.attachments ?? []).map((a: any) => a.name) };
          }) });
        } catch { done({ exit, tests: [], version: "", durations: [] }); }
      });
    });
  } finally { await stopApp(child); }
}

// ---------------------------------------------------------------- reading the evidence

type Rec = { result: string; asserted: string; read: string; given: string[]; where: string; line: number; pictureSha: string; inPicture: string[]; text: string };

function readRecord(dir: string, id: string): Rec | null {
  const file = join(dir, `${id}.md`);
  if (!existsSync(file)) return null;
  const text = readFileSync(file, "utf8");
  const get = (pattern: RegExp) => text.match(pattern)?.[1] ?? "";
  return { result: get(/^- Result: (HELD|DID NOT HOLD)\b/m), asserted: get(/^- Asserted: .* has exactly the text `([^`]*)`$/m), read: get(/^- Read from the page at that moment: `([^`]*)`$/m),
    given: [...text.matchAll(/^- Given, ([^:]+): `([^`]*)`$/gm)].map((m) => `${m[1]} ${m[2]}`), where: get(/^- Asserted at: `([^`]*)`/m), line: Number(get(/^- Asserted at: `[^`]*, line (\d+)`/m)),
    pictureSha: get(/^- Picture: .*sha256 `([0-9a-f]{64})`$/m), inPicture: [...(get(/^- Text inside the picture: (.*)$/m)).matchAll(/`([^`]*)`/g)].map((m) => m[1]), text };
}

/** What is wrong with a record of a passing run, given the real checksum of its picture. Nothing, for a sound one. */
function recordProblems(record: Rec | null, pictureChecksum: string): string[] {
  if (!record) return ["there is no record"];
  const problems: string[] = [];
  if (record.result !== "HELD") problems.push(`the result is "${record.result}" and not HELD`);
  if (!record.asserted) problems.push("no asserted value can be read from it");
  if (record.read !== record.asserted) problems.push(`the value read, ${record.read || "none"}, is not the value asserted, ${record.asserted || "none"}`);
  if (record.pictureSha !== pictureChecksum) problems.push("the checksum it gives is not its picture's");
  if (!record.given.length) problems.push("it does not say what the value follows from");
  if (!/^- What this does not show: \S+( \S+){5,}/m.test(record.text)) problems.push("it does not say what it does not show");
  if (!record.line) problems.push("it does not say where in the test the value was asserted");
  if (!record.inPicture.some((text) => record.asserted && text.includes(record.asserted))) problems.push("the text inside its picture does not include the value asserted");
  return problems;
}

function pngSize(file: string): { width: number; height: number } | null {
  const data = readFileSync(file);
  if (data.length < 24 || data.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a" || data.subarray(12, 16).toString("latin1") !== "IHDR") return null;
  return { width: data.readUInt32BE(16), height: data.readUInt32BE(20) };
}

/** The names of the chunks of a PNG file. Text can be hidden in tEXt, iTXt, zTXt and eXIf chunks. */
function pngChunks(file: string): string[] {
  const data = readFileSync(file);
  const names: string[] = [];
  for (let at = 8; at + 8 <= data.length;) { const length = data.readUInt32BE(at); names.push(data.subarray(at + 4, at + 8).toString("latin1")); at += 12 + length; }
  return names;
}

// ---------------------------------------------------------------- the scan for credentials and personal data

const SCANS: [string, RegExp][] = [
  ["a credential by name", /(pass(word|wd)?|secret|token|api[_-]?key|authori[sz]ation|bearer|cookie|session[_-]?id|private[_-]?key)["']?\s*(:|=|\bis\b)/i],
  ["a bearer or basic credential", /\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}/i],
  // 32 or more such characters with a digit among them. A long path of words has no digit and is not a key.
  ["a long string of letters and digits, such as a key", /(?=[A-Za-z_+/=-]*\d)[A-Za-z0-9_+/=-]{32,}/],
  ["an email address", /[\w.+-]+@[\w-]+(\.[\w-]+)+/],
  ["a telephone number", /(?<![\w.])\+?\d[\d ()-]{8,}\d(?![\w.])/],
  ["a card-like number", /\b(?:\d[ -]?){13,19}\b/],
  ["a home folder", /\/Users\/[^\s/]+|\/home\/[^\s/]+|\/root\b|~\/|[A-Z]:\\Users\\/],
  ["an address with a query string or a name and password in it", /https?:\/\/\S+[?#]\S+|https?:\/\/[^\s/]+:[^\s/]+@/],
  ["a network address", /\b(?!127\.0\.0\.1\b)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/],
  ["a person's title and name", /\b(Mr|Mrs|Ms|Miss|Dr)\.? [A-Z][a-z]+/],
];
const ALLOWED_IN_PICTURE = /^(Subtotal|Discount \(WELCOME10\)|Tax|Total|-?£\d+\.\d\d|Total charged £\d+\.\d\d)$/;

/** Scans one text. `known` are checksums of the pictures, which are long strings and are not keys. Dates are not telephone numbers. */
function scan(text: string, known: string[]): string[] {
  let cleaned = text.replace(/\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z/g, "DATE");
  for (const checksum of known) cleaned = cleaned.split(checksum).join("CHECKSUM");
  return SCANS.filter(([, pattern]) => pattern.test(cleaned)).map(([name]) => name);
}

// ---------------------------------------------------------------- the ways a rule is broken

type Broken = { name: string; what: string; breaks: string; env?: Record<string, string>; edit?: [string, string]; expect: Record<string, string> };
// expect: for each rule's test, where it is expected to end: "holds", or "fails at PROOF", or "fails at PRECONDITION".
const BROKEN: Broken[] = [
  { name: "discount-is-20-percent", what: "the discount is worked out at 20%, not 10%", breaks: "R1", edit: ['const DISCOUNT = { code: "WELCOME10", rate: 0.1 };', 'const DISCOUNT = { code: "WELCOME10", rate: 0.2 };'],
    expect: { R1: "fails at PROOF", R2: "fails at PRECONDITION", R3: "fails at PRECONDITION", R4: "holds" } },
  { name: "tax-shown-wrong", what: "the tax figure shown is worked out at 25%. The total is right", breaks: "R2", env: { CHECKOUT_FAULT: "tax-shown-wrong" },
    expect: { R1: "holds", R2: "fails at PROOF", R3: "fails at PRECONDITION", R4: "holds" } },
  { name: "tax-left-out-of-total", what: "the total leaves the tax out", breaks: "R3", env: { CHECKOUT_FAULT: "tax-left-out-of-total" },
    expect: { R1: "holds", R2: "holds", R3: "fails at PROOF", R4: "holds" } },
  { name: "total-ignores-discount", what: "the discount is shown, and the total adds the tax to the full subtotal", breaks: "R3: the discount is not taken off", env: { CHECKOUT_FAULT: "total-ignores-discount" },
    expect: { R1: "holds", R2: "holds", R3: "fails at PROOF", R4: "holds" } },
  { name: "confirmation-wrong", what: "the confirmation shows the subtotal where the amount charged belongs", breaks: "R4", env: { CHECKOUT_FAULT: "confirmation-wrong" },
    expect: { R1: "holds", R2: "holds", R3: "holds", R4: "fails at PROOF" } },
  { name: "discount-ignored", what: "the discount is shown and is not taken off before the tax or the total", breaks: "R2 and R3", env: { CHECKOUT_FAULT: "discount-ignored" },
    expect: { R1: "holds", R2: "fails at PROOF", R3: "fails at PRECONDITION", R4: "holds" } },
  { name: "button-dead", what: "pressing \"Buy now\" shows the checkout page again", breaks: "no rule: the order cannot be placed", env: { CHECKOUT_FAULT: "button-dead" },
    expect: { R1: "holds", R2: "holds", R3: "holds", R4: "fails at NAVIGATION" } },
  { name: "subtotal-wrong", what: "a quantity of 2 is counted as 1, so the subtotal is 28.00", breaks: "no rule of the four: the basket is wrong", env: { CHECKOUT_FAULT: "subtotal-wrong" },
    expect: { R1: "fails at PRECONDITION", R2: "fails at PRECONDITION", R3: "fails at PRECONDITION", R4: "holds" } },
  { name: "tax-rate-20.01-percent", what: "the tax rate is 20.01%, which gives the same figures for this one basket", breaks: "R2, unseen", edit: ["const TAX_RATE = 0.2;", "const TAX_RATE = 0.2001;"],
    expect: { R1: "holds", R2: "holds", R3: "holds", R4: "holds" } },
  { name: "discount-rate-10.01-percent", what: "the discount rate is 10.01%, which gives the same figures for this one basket", breaks: "R1, unseen", edit: ['const DISCOUNT = { code: "WELCOME10", rate: 0.1 };', 'const DISCOUNT = { code: "WELCOME10", rate: 0.1001 };'],
    expect: { R1: "holds", R2: "holds", R3: "holds", R4: "holds" } },
];

async function main() {
  const log = new Log("The contrast run. playwright-success-evidence, attempt playwright-attempt-007", "Recorded by participant/tests/playwright/tools/success-evidence-check.ts.",
    "The checkout is made up and ran on this computer only, on 127.0.0.1. Every price, product and code in it is invented. It has no sign-in and holds no customer.",
    "Every broken application below was the corrected one with its harness switch set, or a copy in a scratch folder, deleted at the end. Paths are shown from the repository's top folder.");
  const scratch = mkdtempSync(join(TESTS, ".success-scratch-"));
  const spec = readFileSync(SPEC, "utf8");
  const appSource = readFileSync(APP, "utf8");
  const helper = readFileSync(HELPER, "utf8");
  const settings = readFileSync(SETTINGS, "utf8");
  try {
    // ============================================================ the passing run
    log.part("PART 1. The passing run, and what it captured (criteria 1, 2 and 4)");
    const passDir = join(scratch, "passing");
    const passing = await runSuite(APP, {}, passDir);
    rmSync(VALIDATED, { recursive: true, force: true });
    mkdirSync(VALIDATED, { recursive: true });
    for (const name of readdirSync(passDir)) cpSync(join(passDir, name), join(VALIDATED, name));
    writeFileSync(join(VALIDATED, "runner-output.txt"), ["What Playwright itself reported for the run, taken from its JSON report. Not written by the test or its helper.", "",
      `Playwright ${passing.version}. Command, run from participant/tests/playwright with CHECKOUT_PORT and GTQ_PROOF_DIR set:`, "  node ../../node_modules/@playwright/test/cli.js test --config success.config.ts --reporter json", "",
      ...passing.tests.map((t, index) => `  ${t.status.padEnd(7)} ${String(passing.durations[index]).padStart(4)} ms   ${t.title}\n          attached: ${t.attachments.join(", ") || "nothing"}`), "", `exit code ${passing.exit}`, ""].join("\n"));
    writeFileSync(join(VALIDATED, "README.md"), ["# Evidence captured at the validation points of one passing run", "",
      "The folder is named `validated` by the quest. The name claims nothing: what each item shows, and what it does not, is in the item.", "",
      "Evidence captured by one passing run of `participant/tests/playwright/meaningful-evidence.spec.ts`, against a made-up checkout on this computer.",
      "Written by `participant/tests/playwright/tools/success-evidence-check.ts`, which empties this folder and fills it again each time it runs.", "",
      "- `R1-discount.md` to `R4-charge.md`: one record for each business rule. Each says what the rule is, the value the test asserted, the value read",
      "  from the page at that moment, what that value follows from, and where in the test it was asserted.",
      "- `R1-discount.png` to `R4-charge.png`: a picture of the part of the page that rule is about, taken at the same moment. The record gives its checksum.",
      "- `run-output.txt`: every step of the run in order, marked NAVIGATION, PRECONDITION or PROOF, and whether anything was captured at it. It is",
      "  written by the test's own helper, so it is the test's word.",
      "- `runner-output.txt`: what Playwright itself reported: each test, whether it passed, and the files attached to it.", "",
      "There is one record and one picture for each rule, and no other capture. The checkout has one basket, so each item shows its rule's figure",
      "for that basket and for no other. The run that broke each rule on purpose is `../logs/contrast-run.txt`.", ""].join("\n"));
    const output = readFileSync(join(VALIDATED, "run-output.txt"), "utf8").trimEnd().split("\n");
    log.out("$ CHECKOUT_PORT=(a free port) GTQ_PROOF_DIR=SCRATCH/passing node ../../node_modules/@playwright/test/cli.js test --config success.config.ts --reporter json",
      `  (run from participant/tests/playwright. Playwright ${passing.version}. The lines below are from its JSON report. The folder was then copied to validated/.)`,
      ...passing.tests.map((t) => `  ${t.status.padEnd(7)} ${t.title}`), `  exit code ${passing.exit}`, "", "The run's own list of every step, validated/run-output.txt:", ...output.map((l) => `  ${l}`), "");
    log.check("the four tests ran and passed, and the exit code is 0", passing.tests.length === 4 && passing.tests.every((t) => t.status === "passed") && passing.exit === 0);
    const files = readdirSync(VALIDATED).sort();
    log.out(`Files in validated/: ${files.join(", ")}`);
    log.check("criterion 1: there is exactly one record and one picture for each of the four rules, and nothing else was captured",
      files.join() === [...RULES.flatMap((id) => [`${id}.md`, `${id}.png`]), "README.md", "run-output.txt", "runner-output.txt"].sort().join());
    const records = Object.fromEntries(RULES.map((id) => [id, readRecord(VALIDATED, id)])) as Record<string, Rec | null>;
    log.out("", "What each record says:");
    for (const id of RULES) {
      const r = records[id];
      log.out(`  ${id}`, `    result ${r?.result}    asserted ${r?.asserted}    read from the page ${r?.read}`, `    given: ${r?.given.join("; ")}`, `    asserted at ${r?.where}`, `    text inside the picture: ${r?.inPicture.join(" | ")}`);
    }
    const realShas = Object.fromEntries(RULES.map((id) => [id, sha(readFileSync(join(VALIDATED, `${id}.png`)))]));
    const faults = RULES.flatMap((id) => recordProblems(records[id], realShas[id]).map((problem) => `${id}: ${problem}`));
    log.out(...faults.map((f) => `  PROBLEM: ${f}`));
    log.check("criterion 4: every record says the rule HELD, gives the value asserted and the same value read from the page, names what that value follows from, and says what it does not show", faults.length === 0);
    const sizes = Object.fromEntries(RULES.map((id) => [id, pngSize(join(VALIDATED, `${id}.png`))]));
    log.out("", "The pictures:", ...RULES.map((id) => `  ${id}.png  ${sizes[id]?.width} x ${sizes[id]?.height} pixels, ${statSync(join(VALIDATED, `${id}.png`)).size} bytes, sha256 ${sha(readFileSync(join(VALIDATED, `${id}.png`)))}`));
    log.check("each picture is a PNG, and is the picture its record names: the checksum in the record is the file's", RULES.every((id) => sizes[id] !== null && records[id]?.pictureSha === sha(readFileSync(join(VALIDATED, `${id}.png`)))));
    log.check("each picture is a part of the page and not the page: under a tenth of the 1280 x 720 the browser showed", RULES.every((id) => sizes[id] !== null && sizes[id]!.width * sizes[id]!.height < 1280 * 720 / 10));
    const kinds = (kind: string) => output.filter((l) => l.slice(4).startsWith(kind));
    log.out("", `Steps in the run: ${output.length}. NAVIGATION ${kinds("NAVIGATION").length}, PRECONDITION ${kinds("PRECONDITION").length}, PROOF ${kinds("PROOF").length}.`);
    log.check("the run's own list has nine navigation and precondition steps and four proofs, one for each rule. That list is the helper's word. The two checks after this one are what show nothing else was captured",
      [...kinds("NAVIGATION"), ...kinds("PRECONDITION")].length === 9 && kinds("PROOF").length === 4 && RULES.every((id) => kinds("PROOF").filter((l) => l.includes(`Captured ${id}.md and ${id}.png.`)).length === 1));
    const kept = existsSync(PW_OUTPUT) ? (readdirSync(PW_OUTPUT, { recursive: true }) as string[]).filter((f) => statSync(join(PW_OUTPUT, f)).isFile()) : [];
    const stray = kept.filter((f) => !/(^|\/)attachments\/R\d-[\w-]+\.(md|png)$/.test(f) && f !== ".last-run.json");
    log.out(`Playwright's own output folder after the run: ${kept.length} files. Not a copy of an attached record or picture: ${stray.length ? stray.join(", ") : "none"}.`);
    log.check("criterion 2: Playwright itself kept nothing of any step, navigation or otherwise: no trace, no video, no screenshot. Its folder holds only its copies of the eight attached files", stray.length === 0 && kept.filter((f) => f.includes("attachments/")).length === 8);
    log.check("stretch goal: the evidence is attached to the report automatically. The report lists each test's record and picture, and nothing else", passing.tests.every((t) => { const id = RULES.find((r) => r.startsWith(t.rule))!; return t.attachments.join() === `${id}.md,${id}.png`; }));

    // ============================================================ the markings in the test
    log.part("PART 2. The test marks which assertions prove a rule (criterion 3)");
    const specLines = spec.split("\n");
    const expects = specLines.map((text, index) => ({ text, line: index + 1 })).filter((l) => /\bexpect\(/.test(l.text) && !l.text.trim().startsWith("//") && !l.text.trim().startsWith("*"));
    const provesCalls = specLines.map((text, index) => ({ text, line: index + 1 })).filter((l) => /^\s*await proves\(/.test(l.text));
    for (const e of expects) log.out(`  line ${String(e.line).padStart(3)}  ${(e.text.match(/\/\/ (NAVIGATION|PRECONDITION)/)?.[1] ?? "NOT MARKED").padEnd(12)}  ${e.text.trim().replace(/\s*\/\/.*$/, "")}`);
    for (const p of provesCalls) log.out(`  line ${String(p.line).padStart(3)}  PROOF         ${specLines[p.line - 2].trim()}`);
    log.check("every line of the test that has an expect() on it also has a comment saying NAVIGATION or PRECONDITION", expects.length > 0 && expects.every((e) => /\/\/ (NAVIGATION|PRECONDITION)/.test(e.text)));
    log.check("every call of proves() has a comment directly above it beginning \"PROOF of R\" and the rule's number, and there are four, one for each rule",
      provesCalls.length === 4 && provesCalls.every((p, index) => new RegExp(`^\\s*// PROOF of R${index + 1}\\. `).test(specLines[p.line - 2])));
    log.check("the line each record gives as \"asserted at\" is the line of that rule's proves() call in the test", RULES.every((id, index) => records[id]?.line === provesCalls[index]?.line));
    log.out("What this does not show: that the marks are right. That an assertion marked NAVIGATION proves no rule is a judgement. PROOF.md argues it.");

    // ============================================================ the contrast
    log.part("PART 3. The same test with a rule deliberately broken (criterion 5)",
      "For each way: where each rule's test ended, what its record then said, and whether its picture is the same file, byte for byte, as in the passing run.",
      "\"fails at PRECONDITION\" means the test stopped before its rule was checked, because a figure the rule starts from was already wrong. Nothing is captured then.");
    const passShas = Object.fromEntries(RULES.map((id) => [id, sha(readFileSync(join(VALIDATED, `${id}.png`)))]));
    const sameWhenBroken: string[] = [];
    const ended: Record<string, Record<string, string>> = {};
    const changedAtProof: Record<string, string[]> = { R1: [], R2: [], R3: [], R4: [] };
    for (const broken of BROKEN) {
      let app = APP;
      if (broken.edit) {
        if (appSource.split(broken.edit[0]).length !== 2) throw new Error(`The corrected checkout does not have, exactly once: ${broken.edit[0]}`);
        app = join(scratch, `checkout-${broken.name}.mjs`);
        writeFileSync(app, appSource.replace(broken.edit[0], broken.edit[1]));
      }
      const dir = join(scratch, broken.name);
      const run = await runSuite(app, broken.env ?? {}, dir);
      const said = existsSync(join(dir, "run-output.txt")) ? readFileSync(join(dir, "run-output.txt"), "utf8").trimEnd().split("\n") : [];
      log.out("", `BROKEN: ${broken.what}.   (${broken.name}; the rule it breaks: ${broken.breaks})`, broken.edit ? `  one line of a copy of the application: ${broken.edit[0]}  became  ${broken.edit[1]}` : `  the application's harness switch: CHECKOUT_FAULT=${broken.env!.CHECKOUT_FAULT}`);
      const ends: Record<string, string> = {};
      for (const id of RULES) {
        const rule = id.split("-")[0];
        const test = run.tests.find((t) => t.rule === rule);
        const failedAt = said.find((l) => l.startsWith(rule) && (l.includes("FAILED HERE") || l.includes("DID NOT HOLD")))?.slice(4).split(" ")[0] ?? "";
        const record = readRecord(dir, id);
        const picture = existsSync(join(dir, `${id}.png`)) ? sha(readFileSync(join(dir, `${id}.png`))) : "";
        ends[rule] = test?.status === "passed" ? "holds" : test?.status === "failed" ? `fails at ${failedAt}` : `${test?.status}`;
        const evidence = !record ? "no record and no picture: the rule's assertion was not reached"
          : `record says ${record.result}, asserted ${record.asserted}, read ${record.read}. picture ${picture === passShas[id] ? "IDENTICAL to the passing run's" : "DIFFERENT from the passing run's"}`;
        log.out(`  ${rule}  ${ends[rule].padEnd(22)} ${evidence}${test?.status === "failed" ? `\n      ${test.message}` : ""}`);
        if (record && record.result === "HELD" && picture === passShas[id] && record.read === records[id]!.read) sameWhenBroken.push(`${id} when ${broken.what}`);
        if (test?.status === "failed" && failedAt === "PROOF") {
          const changed = record?.result === "DID NOT HOLD" && record.read !== record.asserted && record.read !== records[id]!.read && picture !== "" && picture !== passShas[id];
          if (changed) changedAtProof[rule].push(broken.name);
          log.check(`${broken.name}: ${rule}'s assertion FAILS, its record says DID NOT HOLD with the value that was there, ${record?.read}, and its picture is not the passing run's`, changed);
        }
      }
      ended[broken.name] = ends;
      log.check(`${broken.name}: each rule's test ended where expected: ${RULES.map((id) => `${id.split("-")[0]} ${broken.expect[id.split("-")[0]]}`).join(", ")}`, RULES.every((id) => ends[id.split("-")[0]] === broken.expect[id.split("-")[0]]));
    }
    log.out("", "CAPTURES THAT WERE EXACTLY THE SAME AS IN THE PASSING RUN WHILE SOMETHING WAS BROKEN: the record held, the value read was the same, and the picture",
      "was byte for byte the same.", ...sameWhenBroken.map((s) => `  ${s}`),
      "Most of these are as they should be: the thing broken was another rule's, and this rule did hold. A capture that changed whenever anything",
      "went wrong would say nothing about its own rule. Three groups are LIMITS, and are checked just below.");
    log.out("", "For each rule, the ways of breaking it that made ITS OWN assertion fail with its evidence changed, worked out from the runs above:", ...Object.entries(changedAtProof).map(([rule, names]) => `  ${rule}: ${names.join(", ") || "NONE"}`));
    log.check("criterion 5: for each of the four rules, at least one of the runs above made that rule's own assertion fail, with its record and its picture changed", Object.values(changedAtProof).every((names) => names.length > 0));
    const same = (id: string, name: string) => sameWhenBroken.some((s) => s.startsWith(id) && s.endsWith(BROKEN.find((b) => b.name === name)!.what));
    log.check("LIMIT OBSERVED: when the discount is shown and not taken off, in either of the two ways tried, R1's capture is identical to the passing run's. The discount line does not show that the discount was applied",
      same("R1-discount", "discount-ignored") && same("R1-discount", "total-ignores-discount"));
    log.check("LIMIT OBSERVED: with a tax rate of 20.01%, or a discount rate of 10.01%, all four captures are identical to the passing run's and every test passes. The evidence shows each rule's figure for this basket and for no other",
      RULES.every((id) => same(id, "tax-rate-20.01-percent") && same(id, "discount-rate-10.01-percent")));
    log.check("LIMIT OBSERVED: when a figure a rule starts from is wrong, that rule's test stops at its precondition and leaves no record at all. With the subtotal wrong, R1, R2 and R3 leave nothing, though 10% of the wrong subtotal may still have been taken",
      ["R1", "R2", "R3"].every((rule) => ended["subtotal-wrong"]?.[rule] === "fails at PRECONDITION"));
    log.check("a failure of navigation is told apart from a failure of a rule: with the button dead, R4 fails at NAVIGATION and leaves no record, and the other three hold", ended["button-dead"]?.R4 === "fails at NAVIGATION");
    log.out("NOT TRIED: an element missing from the page altogether, a wrong sign or a wrong format of amount, and any basket but the one.");

    // ============================================================ the scan
    log.part("PART 4. A scan of the validated folder for a credential or personal data (criterion 6)",
      `Every text file in validated/ is searched for: ${SCANS.map(([name]) => name).join("; ")}.`,
      "The checksums of the pictures and the dates of the run are long strings of digits. They are set aside first, and are checked to be what they claim to be.");
    const checksums = RULES.map((id) => passShas[id]);
    let found = 0;
    let scanned = 0;
    let oddChunks = 0;
    for (const name of readdirSync(VALIDATED).sort()) {
      if (name.endsWith(".png")) {
        const chunks = pngChunks(join(VALIDATED, name));
        const hidden = chunks.filter((c) => !["IHDR", "IDAT", "IEND", "sRGB", "pHYs", "gAMA", "cHRM"].includes(c));
        const endsClean = chunks[chunks.length - 1] === "IEND";
        log.out(`  ${name.padEnd(18)} a picture. Its chunks: ${[...new Set(chunks)].join(", ")}. Chunks other than the image and its colour: ${hidden.length ? hidden.join(", ") : "none"}. Anything after the end of the image: ${endsClean ? "no" : "YES"}.`);
        oddChunks += hidden.length + (endsClean ? 0 : 1);
        continue;
      }
      const hits = scan(readFileSync(join(VALIDATED, name), "utf8"), checksums);
      scanned += 1;
      log.out(`  ${name.padEnd(18)} ${hits.length ? `FOUND: ${hits.join(", ")}` : "nothing found"}`);
      found += hits.length;
    }
    log.check(`the scan finds no credential and no personal data in any of the ${scanned} text files of validated/`, found === 0 && scanned === 7);
    log.check("no picture holds a chunk other than the image and its colour, and none has anything after the end of the image", oddChunks === 0);
    const inPictures = RULES.flatMap((id) => records[id]!.inPicture);
    log.out(`Text inside the four pictures, as the records give it: ${inPictures.join(" | ")}`);
    log.check("the text inside every picture is a label of the order summary or an amount of money, and nothing else", inPictures.length > 0 && inPictures.every((t) => ALLOWED_IN_PICTURE.test(t)));
    log.out("What the scan cannot do: read a picture. That the pictures hold only what the records say rests on the helper reading the same elements at the same moment.",
      "It is a list of patterns. It would miss a name with no title, a postal address, a date of birth, a short secret with no telling word beside it, and anything encoded.",
      "It reads validated/ only. THIS CRITERION IS MET MOSTLY BY THERE BEING NOTHING TO LEAK: the application has no sign-in, no account and no customer.", "",
      "That the scan can find something. One line is added to a copy of a record, in memory, and the scan must report it.",
      "The planted lines are described here and not printed, so that nothing in this log reads as one to another scanner.");
    const sample = records["R1-discount"]!.text;
    // Each planted line is put together here from pieces, and the log describes it without printing it, so that neither
    // this file nor the log holds anything that reads as a credential or a home folder to another scanner.
    const made = "abc" + "DEF123456" + "ghiJKL";
    const plants: [string, string, string][] = [
      ["a line with the word Authorization, then Bearer and 18 made-up characters", ["- Authori", "zation: Bea", "rer ", made].join(""), "a bearer or basic credential"],
      ["a line with a made-up email address at example.test", "- Contact: sam.reader" + "@" + "example.test", "an email address"],
      ["a line with the path of a made-up home folder", "- Saved to /" + "Users" + "/someone/Desktop/out", "a home folder"],
      ["a line with 40 made-up hexadecimal characters", "- Key: " + "9f8e7d6c5b4a3928".repeat(2) + "1706f5e4", "a long string of letters and digits, such as a key"],
      ["a line with a telephone number from a range kept for made-up use", "- Telephone: 01632 " + "960123", "a telephone number"],
      ["a line with the word password, an equals sign and a made-up word", "- pass" + "word = example", "a credential by name"],
      ["a line with client_secret in quotes, a colon and a made-up value", '- "client_' + 'secret": "s3"', "a credential by name"],
      ["a line with a 16-digit made-up card number", "- Card 4000 0000 " + "0000 0002", "a card-like number"],
      ["a line with a web address that has a query string", "- See https://shop.example.test/order" + "?session=abc", "an address with a query string or a name and password in it"],
      ["a line with a network address from a range kept for examples", "- From 192.0.2." + "44", "a network address"],
      ["a line with a title and a made-up surname", "- Placed by Dr " + "Example", "a person's title and name"],
    ];
    for (const [described, planted, expected] of plants) {
      const hits = scan(sample + planted + "\n", checksums);
      log.out(`  planted: ${described}`, `    found: ${hits.join(", ") || "nothing"}`);
      log.check(`reported: ${expected}`, hits.includes(expected));
    }

    // ============================================================ that the check can fail
    log.part("PART 5. That this check can fail", "A record is spoiled in memory and read again.");
    const spoiled = (change: (text: string) => string) => { const dir = join(scratch, "spoiled"); rmSync(dir, { recursive: true, force: true }); mkdirSync(dir); writeFileSync(join(dir, "R2-tax.md"), change(records["R2-tax"]!.text)); return recordProblems(readRecord(dir, "R2-tax"), passShas["R2-tax"]); };
    const spoil = (label: string, expect: string, change: (text: string) => string) => {
      const problems = spoiled(change);
      log.out(`Spoiled: ${label}`, ...(problems.length ? problems.map((p) => `    PROBLEM: ${p}`) : ["    no problem reported"]));
      log.check(`reported: "${expect}"`, problems.some((p) => p.includes(expect)));
    };
    log.check("the record as it is, read the same way, has no problem", spoiled((t) => t).length === 0);
    spoil("the value read changed to £8.00, with the result left as HELD", "is not the value asserted", (t) => t.replace("- Read from the page at that moment: `£7.20`", "- Read from the page at that moment: `£8.00`"));
    spoil("the checksum changed", "the checksum it gives is not its picture's", (t) => t.replace(/sha256 `[0-9a-f]{64}`/, "sha256 `" + "0".repeat(64) + "`"));
    spoil("the result changed to DID NOT HOLD", "and not HELD", (t) => t.replace("- Result: HELD", "- Result: DID NOT HOLD"));
    spoil("the lines saying what the value follows from taken out", "does not say what the value follows from", (t) => t.split("\n").filter((l) => !l.startsWith("- Given, ")).join("\n"));
    spoil("the line saying what it does not show taken out", "does not say what it does not show", (t) => t.split("\n").filter((l) => !l.startsWith("- What this does not show")).join("\n"));
    spoil("the place it was asserted taken out", "does not say where in the test", (t) => t.split("\n").filter((l) => !l.startsWith("- Asserted at")).join("\n"));
    spoil("the value asserted taken out of the text inside the picture", "does not include the value asserted", (t) => t.replace(" `£7.20`\n- Taken at", "\n- Taken at"));
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
  log.part("AT THE END");
  log.out(`sha256 of the test:        ${sha(readFileSync(SPEC, "utf8"))}`, `sha256 of the helper:      ${sha(readFileSync(HELPER, "utf8"))}`, `sha256 of the settings:    ${sha(readFileSync(SETTINGS, "utf8"))}`, `sha256 of the application: ${sha(readFileSync(APP, "utf8"))}`);
  log.check("the test, the helper, the settings and the application are byte for byte what they were at the start, and the scratch folder is gone",
    readFileSync(SPEC, "utf8") === spec && readFileSync(HELPER, "utf8") === helper && readFileSync(SETTINGS, "utf8") === settings && readFileSync(APP, "utf8") === appSource && !existsSync(scratch));
  log.save(join(ATTEMPT, "logs", "contrast-run.txt"));
  return log.failed.length ? 1 : 0;
}

process.exit(await main());

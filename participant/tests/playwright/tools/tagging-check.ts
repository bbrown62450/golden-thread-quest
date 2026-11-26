/*
 * The check for the playwright-tagging quest.
 *
 *   node tools/tagging-check.ts                 checks, and writes logs/tag-check.txt in the attempt folder
 *   node tools/tagging-check.ts --write-scheme  writes participant/context/playwright/tag-scheme.md from support/tags.ts, and stops
 *
 * Node 22.18 or later. It starts the made-up customer directory (demo-app/server.mjs) on this computer, on 127.0.0.1,
 * puts a recorder in front of it, runs the tests with Playwright, and stops both. It contacts nothing else.
 *
 * THE VOCABULARY IS IN ONE PLACE, support/tags.ts. The scheme document is written from it, and this check reads it.
 *
 * WHAT IT TESTS
 *   1. THE SCHEME (criteria 1, 6 and 7). The document on disk is, byte for byte, what the vocabulary gives. The five
 *      dimensions are the five asked for, each with at least two tags, each tag with a meaning. Each duration tag has
 *      a limit. The document on disk is no more than ONE_PAGE lines and characters.
 *   2. THE TAGS ON THE TESTS (criteria 2, 3 and 4). Playwright is asked to list the tests of tagged.spec.ts with their
 *      tags, so the tags are the ones Playwright itself would select by. Every tag must be in the vocabulary. Every
 *      test must have exactly one tag from each dimension. A test that does not is named.
 *   3. WHAT EACH TEST DOES, AGAINST WHAT ITS TAGS SAY (criteria 5 and 6). Each test is run alone, three times, through
 *      the recorder.
 *        read or write   @read: every request it sent was a GET or a HEAD. @write: at least one was not.
 *        layer           @layer-api: no request came from a browser. @layer-ui: at least one did. A request is taken
 *                        to come from a browser when it says so in its User-Agent.
 *        duration        the slowest of the three runs is within the limit its tag states.
 *   4. SELECTING BY TAG. The tests selected by @read are run together, and the recorder must see no write.
 *   5. That the check can fail: tagged.spec.ts is copied, one thing is changed in the copy, and the same checks are
 *      made of the copy. Each change must be reported, naming the test.
 *
 * WHAT IT NEVER WRITES TO: tagged.spec.ts, the vocabulary, the settings and the application. Every changed test file is
 * a copy named tagged.scratch-*.spec.ts beside it, deleted when the check ends.
 *
 * WHAT IT CANNOT TEST
 *   Whether a test's feature tag or risk tag is the right one. Those are judgements, made by the rule the scheme
 *   gives. The check can tell that a test has one. It cannot tell that it is true.
 *   Whether a test would write against another application. It sees what this run sent to this one, at the address
 *   the settings give. A request a test sent to another address would not be seen. Nor would a change made with a
 *   GET, or one a test makes only on some runs.
 *   A test that takes a page and never loads the application in it would read as having no browser. A test that
 *   sends requests through the browser's own client without opening a page would read as having one.
 *   Tests in any file but tagged.spec.ts. It is the one file the settings name.
 *   How long a test takes on another computer. The times are of this one, today. Whether the time Playwright reports
 *   for a test includes starting the browser was not established.
 *   Whether the document fits a printed page. "One page" here is a count of lines and characters.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createServer, request as httpRequest, type Server } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { DIMENSIONS, SELECTIONS, TAGS, type Dimension } from "../support/tags.ts";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-tagging", "playwright-attempt-009");
const SPEC = join(TESTS, "tagged.spec.ts");
const SCHEME = join(PARTICIPANT, "context", "playwright", "tag-scheme.md");
const ONE_PAGE = { lines: 66, characters: 3600 };   // what this check takes "one page" to mean: the lines of a typed page, and about the characters of a full page of prose
const KEYS = ["feature", "risk", "access", "layer", "duration"];
const LOGFILE = join(ATTEMPT, "logs", "tag-check.txt");
const RUNS = 3;

const sha = (data: string | Buffer) => createHash("sha256").update(data).digest("hex");
const tidy = (text: string) => text.replace(/\u001b\[[0-9;]*m/g, "").split(REPO + "/").join("").split(REPO).join("REPO");
const seconds = (ms: number) => `${(ms / 1000).toFixed(2)} s`;

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

// ---------------------------------------------------------------- the scheme document, written from the vocabulary

function schemeDocument(dimensions: Dimension[] = DIMENSIONS): string {
  const out = ["# Tag scheme for the Playwright tests of the customer directory", "",
    "**Every test carries exactly one tag from each of the five dimensions below, and no other tag.**" +
    " Written by `participant/tests/playwright/tools/tagging-check.ts` from `support/tags.ts`. Do not edit it by hand: the check compares the two.", ""];
  for (const dimension of dimensions) {
    out.push(`## ${dimension.name}: ${dimension.question}`, "", `Rule: ${dimension.rule}`, "", "| Tag | Meaning |", "|---|---|");
    for (const tag of dimension.tags) out.push(`| \`${tag.tag}\` | ${tag.means}${tag.limitMs ? `. **Limit: at most ${tag.limitMs / 1000} seconds**` : ""} |`);
    out.push("");
  }
  out.push("## Selections: runs made by combining tags, not by adding one", "", "| Run | Playwright's `--grep` | What it is |", "|---|---|---|");
  for (const selection of SELECTIONS) out.push(`| ${selection.name} | \`${selection.grep}\` | ${selection.means} |`);
  out.push("", "There is no `@smoke` tag. \"Smoke\" is the first selection above, so what it promises is what its two tags promise.", "");
  return out.join("\n");
}

// ---------------------------------------------------------------- the application, and the recorder in front of it

type Sent = { method: string; path: string; browser: boolean };

async function freePort(): Promise<number> {
  return new Promise((done, fail) => {
    const probe = createServer();
    probe.on("error", fail);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      probe.close(() => done(typeof address === "object" && address ? address.port : 0));
    });
  });
}

async function startApp(port: number): Promise<ChildProcess> {
  const child = spawn(process.execPath, ["demo-app/server.mjs"], { cwd: TESTS, env: { ...process.env, DEMO_PORT: String(port) }, stdio: "ignore" });
  for (let wait = 0; wait < 60; wait += 1) {
    await new Promise((done) => setTimeout(done, 50));
    try {
      if ((await fetch(`http://127.0.0.1:${port}/healthz`)).ok) return child;
    } catch { /* not listening yet */ }
  }
  child.kill();
  throw new Error("the application did not start");
}

/** Passes every request on to the application unchanged, and writes down its method, its path and whether a browser sent it. */
function startRecorder(port: number, appPort: number, sent: Sent[]): Promise<Server> {
  const server = createServer((incoming, outgoing) => {
    if (incoming.url !== "/healthz") {
      sent.push({ method: incoming.method ?? "?", path: (incoming.url ?? "").split("?")[0], browser: /Mozilla\//.test(String(incoming.headers["user-agent"] ?? "")) });
    }
    const forward = httpRequest({ host: "127.0.0.1", port: appPort, method: incoming.method, path: incoming.url, headers: incoming.headers }, (answer) => {
      outgoing.writeHead(answer.statusCode ?? 502, answer.headers);
      answer.pipe(outgoing);
    });
    forward.on("error", () => { if (!outgoing.headersSent) outgoing.writeHead(502); outgoing.end(); });
    incoming.pipe(forward);
  });
  return new Promise((done) => server.listen(port, "127.0.0.1", () => done(server)));
}

// ---------------------------------------------------------------- asking Playwright

type Listed = { title: string; line: number; tags: string[] };
type Ran = { status: string; ms: number; sent: Sent[] };

function playwright(args: string[], spec: string, port: number, jsonFile: string): Promise<number> {
  return new Promise((done) => {
    const child = spawn(process.execPath, [CLI, "test", "-c", "tagging.config.ts", "--reporter=json", ...args],
      { cwd: TESTS, env: { ...process.env, DEMO_PORT: String(port), TAGGING_SPEC: spec, PLAYWRIGHT_JSON_OUTPUT_FILE: jsonFile, PLAYWRIGHT_JSON_OUTPUT_NAME: jsonFile, FORCE_COLOR: "0" }, stdio: "ignore" });
    child.on("close", (code) => done(code ?? 1));
  });
}

async function listTests(spec: string, port: number, scratch: string, grep: string[] = []): Promise<Listed[]> {
  const file = join(scratch, "list.json");
  rmSync(file, { force: true });
  await playwright(["--list", ...grep], spec, port, file);
  if (!existsSync(file)) return [];
  const report = JSON.parse(readFileSync(file, "utf8"));
  const found: Listed[] = [];
  const walk = (suite: { specs?: { title: string; line: number; tags?: string[] }[]; suites?: unknown[] }) => {
    for (const one of suite.specs ?? []) found.push({ title: one.title, line: one.line, tags: (one.tags ?? []).map((tag) => "@" + tag) });
    for (const inner of (suite.suites ?? []) as never[]) walk(inner);
  };
  for (const suite of report.suites ?? []) walk(suite);
  return found;
}

async function runOne(spec: string, line: number, port: number, scratch: string, sent: Sent[]): Promise<Ran> {
  const file = join(scratch, "run.json");
  rmSync(file, { force: true });
  sent.length = 0;
  await playwright([`${spec}:${line}`], spec, port, file);
  const mine = sent.splice(0);
  if (!existsSync(file)) return { status: "did not run", ms: 0, sent: mine };
  const report = JSON.parse(readFileSync(file, "utf8"));
  let result: { status?: string; duration?: number } | undefined;
  const walk = (suite: { specs?: { tests?: { results?: { status?: string; duration?: number }[] }[] }[]; suites?: unknown[] }) => {
    for (const one of suite.specs ?? []) result ??= one.tests?.[0]?.results?.[0];
    for (const inner of (suite.suites ?? []) as never[]) walk(inner);
  };
  for (const suite of report.suites ?? []) walk(suite);
  return { status: result?.status ?? "did not run", ms: result?.duration ?? 0, sent: mine };
}

// ---------------------------------------------------------------- the rules

/** The tag a test carries for one dimension, or "" if it has none or more than one. */
const tagFor = (test: Listed, key: string) => {
  const mine = test.tags.filter((tag) => TAGS.get(tag) === key);
  return mine.length === 1 ? mine[0] : "";
};

/** Criteria 2, 3 and 4: what is wrong with the tags of these tests. Every problem names its test. */
function tagProblems(tests: Listed[]): string[] {
  const problems: string[] = [];
  for (const test of tests) {
    for (const tag of test.tags) if (!TAGS.has(tag)) problems.push(`"${test.title}" carries ${tag}, which is not in the vocabulary.`);
    for (const dimension of DIMENSIONS) {
      const mine = test.tags.filter((tag) => TAGS.get(tag) === dimension.key);
      if (mine.length === 0) problems.push(`"${test.title}" has no tag for the dimension ${dimension.name}.`);
      if (mine.length > 1) problems.push(`"${test.title}" has ${mine.length} tags for the dimension ${dimension.name}: ${mine.join(", ")}.`);
    }
  }
  const titles = tests.map((test) => test.title);
  for (const title of new Set(titles)) if (titles.filter((one) => one === title).length > 1) problems.push(`Two tests have the title "${title}", so a report could not tell them apart.`);
  return problems;
}

const writes = (ran: Ran) => [...new Set(ran.sent.filter((one) => !["GET", "HEAD"].includes(one.method)).map((one) => one.method))].sort();

/** Criteria 5 and 6: where what a test did is not what its tags say. */
function behaviourProblems(test: Listed, runs: Ran[]): string[] {
  const problems: string[] = [];
  const name = `"${test.title}"`;
  if (!runs.length || runs.some((ran) => ran.status !== "passed")) problems.push(`${name} did not pass in every run (${runs.map((ran) => ran.status).join(", ") || "no run"}), so what it does could not be compared with its tags.`);
  if (runs.some((ran) => ran.sent.length === 0)) problems.push(`${name} sent the application no request in at least one run, so its read-or-write and layer tags could not be judged.`);
  const wrote = [...new Set(runs.flatMap(writes))].sort();
  const access = tagFor(test, "access");
  if (access === "@read" && wrote.length) problems.push(`${name} is tagged @read and sent ${wrote.join(", ")}.`);
  if (access === "@write" && !wrote.length) problems.push(`${name} is tagged @write and sent nothing but reads.`);
  const browser = runs.some((ran) => ran.sent.some((one) => one.browser));
  const layer = tagFor(test, "layer");
  if (layer === "@layer-api" && browser) problems.push(`${name} is tagged @layer-api and a browser sent requests.`);
  if (layer === "@layer-ui" && !browser) problems.push(`${name} is tagged @layer-ui and no browser sent a request.`);
  const duration = tagFor(test, "duration");
  const limit = DIMENSIONS.find((dimension) => dimension.key === "duration")?.tags.find((tag) => tag.tag === duration)?.limitMs;
  const slowest = Math.max(0, ...runs.map((ran) => ran.ms));
  if (limit !== undefined && slowest > limit) problems.push(`${name} is tagged ${duration}, whose limit is ${seconds(limit)}, and its slowest run took ${seconds(slowest)}.`);
  return problems;
}

/** Criteria 1, 6 and 7: what is wrong with a vocabulary, or with the document on disk. */
function schemeProblems(dimensions: Dimension[], onDisk: string | null): string[] {
  const problems: string[] = [];
  const document = schemeDocument(dimensions);
  const keys = dimensions.map((dimension) => dimension.key);
  if (keys.length !== 5 || KEYS.some((key) => keys.filter((one) => one === key).length !== 1)) problems.push(`The dimensions are ${keys.join(", ") || "none"}. The five needed, once each, are ${KEYS.join(", ")}.`);
  for (const dimension of dimensions) {
    if (dimension.tags.length < 2) problems.push(`The dimension ${dimension.name} has ${dimension.tags.length} tags. With fewer than two a tag says nothing.`);
    if (dimension.rule.trim().split(/\s+/).length < 3) problems.push(`The dimension ${dimension.name} has no rule written for it.`);
    for (const tag of dimension.tags) {
      if (!/^@[a-z][a-z-]*$/.test(tag.tag)) problems.push(`${tag.tag} is not a tag: an @ and small letters and hyphens.`);
      if (tag.means.trim().split(/\s+/).length < 3) problems.push(`${tag.tag} has no meaning written for it.`);
      if (dimension.key === "duration" && !(typeof tag.limitMs === "number" && tag.limitMs > 0)) problems.push(`The duration tag ${tag.tag} has no limit.`);
      if (dimension.key === "duration" && /\d/.test(tag.means)) problems.push(`The meaning of the duration tag ${tag.tag} has a number in it. The limit is written once, as limitMs, so that the document cannot state two.`);
      if (dimension.key !== "duration" && tag.limitMs !== undefined) problems.push(`${tag.tag} is not a duration tag and has a limit.`);
    }
  }
  const all = dimensions.flatMap((dimension) => dimension.tags.map((tag) => tag.tag));
  if (new Set(all).size !== all.length) problems.push("A tag is in the vocabulary twice, so it would belong to two dimensions.");
  const limits = (dimensions.find((dimension) => dimension.key === "duration")?.tags ?? []).map((tag) => tag.limitMs ?? 0);
  if (new Set(limits).size !== limits.length) problems.push("Two duration tags have the same limit.");
  if (limits.some((limit, index) => index > 0 && limit <= limits[index - 1])) problems.push("The duration tags are not in order of their limits, shortest first.");
  if (onDisk === null) problems.push("There is no scheme document on disk.");
  else {
    if (onDisk !== document) problems.push("The scheme document on disk is not what the vocabulary gives. Write it again with --write-scheme.");
    const lines = onDisk.split("\n").length - 1;
    if (lines > ONE_PAGE.lines || onDisk.length > ONE_PAGE.characters) problems.push(`The scheme document on disk is ${lines} lines and ${onDisk.length} characters. One page is at most ${ONE_PAGE.lines} lines and ${ONE_PAGE.characters} characters.`);
  }
  return problems;
}

// ---------------------------------------------------------------- the run

async function main(): Promise<number> {
  const log = new Log("The tag check. playwright-tagging, attempt playwright-attempt-009",
    "Recorded by participant/tests/playwright/tools/tagging-check.ts.",
    "The application is the made-up customer directory, on this computer only. Nobody in it is real. Paths are from the repository's top folder.");
  rmSync(LOGFILE, { force: true });   // so that a run that stops early cannot leave an earlier result standing
  log.out(`Checked: tagged.spec.ts sha256 ${sha(readFileSync(SPEC)).slice(0, 16)}   support/tags.ts sha256 ${sha(readFileSync(join(TESTS, "support", "tags.ts"))).slice(0, 16)}`);
  const scratch = mkdtempSync(join(tmpdir(), "gtq-tagging-"));
  const before = sha(readFileSync(SPEC));
  const sent: Sent[] = [];
  const appPort = await freePort(), port = await freePort();
  const app = await startApp(appPort);
  const recorder = await startRecorder(port, appPort, sent);
  const stored = async () => JSON.stringify(await (await fetch(`http://127.0.0.1:${appPort}/api/customers`)).json());
  const atStart = await stored();
  const scratchSpecs: string[] = [];
  let ended = false;
  try {
    log.part("PART 1. The scheme (criteria 1, 6 and 7)");
    const document = schemeDocument();
    const onDisk = existsSync(SCHEME) ? readFileSync(SCHEME, "utf8") : null;
    for (const dimension of DIMENSIONS) log.out(`  ${dimension.name.padEnd(14)} ${dimension.tags.map((tag) => tag.tag + (tag.limitMs ? ` (at most ${tag.limitMs / 1000} s)` : "")).join("  ")}`);
    const problems = schemeProblems(DIMENSIONS, onDisk);
    log.out(...problems.map((problem) => `  PROBLEM: ${problem}`));
    log.check("the vocabulary and the document have no problem of any kind", problems.length === 0);
    log.check(`criterion 1: the dimensions are feature, risk, read or write, layer and duration, once each, each with a rule and two tags or more, and every one of the ${TAGS.size} tags has a meaning written for it`, !problems.some((p) => /The dimensions are|fewer than two|no meaning|no rule|not a tag|twice/.test(p)));
    log.check("criterion 6: each duration tag has a limit, written once, and the limits rise", DIMENSIONS.some((dimension) => dimension.key === "duration") && !problems.some((p) => /limit/.test(p)));
    log.check(`criterion 7: the scheme document on disk is ${onDisk === null ? "MISSING" : `${onDisk.split("\n").length - 1} lines and ${onDisk.length} characters`}, and one page is taken to be at most ${ONE_PAGE.lines} lines and ${ONE_PAGE.characters} characters`, onDisk !== null && !problems.some((p) => /One page|no scheme document/.test(p)));
    log.check("stretch goal: participant/context/playwright/tag-scheme.md on disk is, byte for byte, what the vocabulary gives", onDisk === document);

    log.part("PART 2. The tags on the tests (criteria 2, 3 and 4)", "Playwright was asked to list the tests of tagged.spec.ts with their tags. These are the tags it would select by.",
      "\"Every test\" below means every test of that one file. It is the only file the settings of this quest name.");
    const tests = await listTests("tagged.spec.ts", port, scratch);
    for (const test of tests) {
      log.out(`  line ${String(test.line).padStart(3)}  ${test.title}`, `            ${DIMENSIONS.map((dimension) => `${dimension.key}: ${tagFor(test, dimension.key) || "NONE"}`).join("   ")}`);
    }
    const tagged = tagProblems(tests);
    log.out(...tagged.map((problem) => `  PROBLEM: ${problem}`));
    log.check(`there are at least eight tests: ${tests.length}`, tests.length >= 8);
    log.check("criterion 2: every test of tagged.spec.ts carries exactly one tag from each of the five dimensions", tests.length > 0 && !tagged.some((p) => /has no tag|tags for the dimension/.test(p)));
    log.check("criterion 3: no test of tagged.spec.ts carries a tag from outside the vocabulary", tests.length > 0 && !tagged.some((p) => /not in the vocabulary/.test(p)));
    log.check("no two tests have the same title, so a test can be reported by name", !tagged.some((p) => /Two tests/.test(p)));
    for (const dimension of DIMENSIONS) {
      const unused = dimension.tags.filter((tag) => !tests.some((test) => test.tags.includes(tag.tag))).map((tag) => tag.tag);
      log.check(`every tag of the dimension ${dimension.name} is carried by at least one test${unused.length ? `. NOT USED: ${unused.join(", ")}` : ""}`, unused.length === 0);
    }

    log.part(`PART 3. What each test does, against what its tags say (criteria 5 and 6)`,
      `Each test was run alone, ${RUNS} times, through a recorder that writes down every request it sent to the application.`,
      "Read or write is judged by the methods of those requests. Layer by whether any of them says, in its User-Agent, that a browser sent it.",
      "Duration is the slowest run, by the time Playwright reports for the test.");
    const behaviour: string[] = [];
    const slowestOf = new Map<string, number>();
    for (const test of tests) {
      const runs: Ran[] = [];
      for (let run = 0; run < RUNS; run += 1) runs.push(await runOne("tagged.spec.ts", test.line, port, scratch, sent));
      const wrote = [...new Set(runs.flatMap(writes))].sort();
      const browser = runs.some((ran) => ran.sent.some((one) => one.browser));
      const found = behaviourProblems(test, runs);
      behaviour.push(...found);
      slowestOf.set(test.title, Math.max(...runs.map((ran) => ran.ms)));
      log.out(`  ${test.title}`,
        `      runs: ${runs.map((ran) => `${ran.status} ${seconds(ran.ms)}`).join(", ")}   requests in a run: ${runs.map((ran) => ran.sent.length).join(", ")}`,
        `      sent: ${wrote.length ? `reads, and ${wrote.join(", ")}` : "reads only"}   browser: ${browser ? "yes" : "no"}   tags: ${tagFor(test, "access")} ${tagFor(test, "layer")} ${tagFor(test, "duration")}`,
        ...found.map((problem) => `      PROBLEM: ${problem}`));
    }
    const of = (key: string, tag: string) => tests.filter((test) => tagFor(test, key) === tag);
    log.check(`every test passed in each of its ${RUNS} runs`, tests.length > 0 && !behaviour.some((p) => /did not pass/.test(p)));
    log.check(`criterion 5: each of the ${of("access", "@read").length} tests tagged @read sent only reads, and each of the ${of("access", "@write").length} tagged @write sent at least one write`, !behaviour.some((p) => /tagged @read|tagged @write|no request in/.test(p)) && of("access", "@read").length > 0 && of("access", "@write").length > 0);
    log.check(`each of the ${of("layer", "@layer-api").length} tests tagged @layer-api sent no request from a browser, and each of the ${of("layer", "@layer-ui").length} tagged @layer-ui sent at least one`, !behaviour.some((p) => /@layer-|no request in/.test(p)) && of("layer", "@layer-api").length > 0 && of("layer", "@layer-ui").length > 0);
    for (const tag of DIMENSIONS.find((dimension) => dimension.key === "duration")!.tags) {
      const mine = of("duration", tag.tag);
      const worst = Math.max(0, ...mine.map((test) => slowestOf.get(test.title) ?? 0));
      log.check(`criterion 6: each of the ${mine.length} tests tagged ${tag.tag} took at most ${seconds(tag.limitMs!)} in its slowest run. The slowest of them: ${seconds(worst)}`, mine.length > 0 && worst <= tag.limitMs!);
    }
    const fast = DIMENSIONS.find((dimension) => dimension.key === "duration")!.tags[0];
    const couldBeFast = of("duration", "@slow").filter((test) => (slowestOf.get(test.title) ?? 0) <= fast.limitMs!).map((test) => test.title);
    log.check(`no test tagged @slow ran within the limit of ${fast.tag} in all its runs, so none carries a looser tag than it needs${couldBeFast.length ? `: ${couldBeFast.join("; ")}` : ""}`, couldBeFast.length === 0);

    log.part("PART 4. Selecting by tag (criterion 5)");
    const readOnly = await listTests("tagged.spec.ts", port, scratch, ["--grep-invert", "@write"]);
    log.out(`With --grep-invert "@write", Playwright lists ${readOnly.length} tests:`, ...readOnly.map((test) => `  ${test.title}`));
    const same = (some: Listed[], others: Listed[]) => some.length > 0 && some.map((test) => test.title).sort().join("|") === others.map((test) => test.title).sort().join("|");
    const byRead = await listTests("tagged.spec.ts", port, scratch, ["--grep", "@read"]);
    log.out(`With --grep "@read", it lists ${byRead.length} tests.`);
    log.check("taking @write out, and selecting @read, each list exactly the tests the check found tagged @read", same(readOnly, of("access", "@read")) && same(byRead, of("access", "@read")));
    const byWrite = await listTests("tagged.spec.ts", port, scratch, ["--grep", "@write"]);
    log.check(`selecting @write lists the other ${byWrite.length} tests, and no test is in both lists`, same(byWrite, of("access", "@write")) && byRead.length + byWrite.length === tests.length);
    sent.length = 0;
    const code = await playwright(["--grep", "@read"], "tagged.spec.ts", port, join(scratch, "selection.json"));
    const seen = sent.splice(0);
    log.out(`The @read selection was then run. Requests the recorder saw: ${seen.length}. Methods: ${[...new Set(seen.map((one) => one.method))].sort().join(", ") || "none"}.`);
    log.check("criterion 5: run together, the tests selected by @read passed and sent the application nothing but reads", code === 0 && seen.length > 0 && seen.every((one) => ["GET", "HEAD"].includes(one.method)));
    for (const selection of SELECTIONS) {
      const chosen = await listTests("tagged.spec.ts", port, scratch, ["--grep", selection.grep]);
      log.out(`The selection "${selection.name}" (--grep "${selection.grep}") lists ${chosen.length} tests. Their slowest runs add up to ${seconds(chosen.reduce((sum, test) => sum + (slowestOf.get(test.title) ?? 0), 0))}, each run alone.`);
    }
    const smoke = await listTests("tagged.spec.ts", port, scratch, ["--grep", SELECTIONS[0].grep]);
    log.check("the selection that stands for \"smoke\" lists exactly the tests tagged both @risk-high and @fast", smoke.length > 0 && smoke.map((test) => test.title).sort().join("|") === tests.filter((test) => test.tags.includes("@risk-high") && test.tags.includes("@fast")).map((test) => test.title).sort().join("|"));

    log.part("PART 5. That this check can fail", "Each trial copies tagged.spec.ts to a file beside it, changes one thing in the copy, and makes the same checks of the copy.",
      "Playwright lists the copy, so the tags are read the same way. Where the change is to what a test does, that test is run, once.");
    const original = readFileSync(SPEC, "utf8");
    let number = 0;
    const trial = async (label: string, expects: string | string[], change: (text: string) => string, runTitle?: string) => {
      const wanted = [expects].flat();
      number += 1;
      const name = `tagged.scratch-${number}.spec.ts`;
      const changed = change(original);
      writeFileSync(join(TESTS, name), changed);
      scratchSpecs.push(name);
      const listed = await listTests(name, port, scratch);
      let found = tagProblems(listed);
      if (runTitle) {
        const target = listed.find((test) => test.title === runTitle);
        found = target ? [...found, ...behaviourProblems(target, [await runOne(name, target.line, port, scratch, sent)])] : ["THE TEST TO RUN WAS NOT FOUND IN THE COPY"];
      }
      rmSync(join(TESTS, name), { force: true });
      const hit = found.filter((problem) => wanted.some((expect) => problem.includes(expect)));
      log.out(`Changed: ${label}`, ...(changed === original ? ["    THE TEXT TO CHANGE WAS NOT FOUND"] : []), ...(found.length ? [...hit, ...found.filter((p) => !hit.includes(p))].slice(0, 3).map((problem) => `    PROBLEM: ${problem}`) : ["    no problem reported"]));
      for (const expect of wanted) log.check(`reported: ${expect}`, changed !== original && found.some((problem) => problem.includes(expect)));
    };
    const swap = (old: string, next: string) => (text: string) => (text.split(old).length === 2 ? text.replace(old, next) : text);
    const first = `{ tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@fast"] }`;
    const created = `{ tag: ["@feature-add", "@risk-high", "@write", "@layer-api", "@fast"] },\n  async ({ request, own }) => {\n    const ada`;
    const bulk = `{ tag: ["@feature-add", "@risk-high", "@write", "@layer-ui", "@slow"] }`;
    const T1 = "the page lists a customer that was there before, with its plan";
    const T4 = "a customer created by a request is stored with the name and plan that were sent";
    const T10 = "sixty customers added one after another through the form are all listed";
    log.out("", "-- The tags on the tests");
    await trial("the risk tag taken off one test", `"${T1}" has no tag for the dimension Risk.`, swap(first, `{ tag: ["@feature-list", "@read", "@layer-ui", "@fast"] }`));
    await trial("the duration tag of one test replaced by @smoke", [`"${T1}" carries @smoke, which is not in the vocabulary.`, `"${T1}" has no tag for the dimension Duration.`], swap(first, `{ tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@smoke"] }`));
    await trial("a tag put on a group of tests and not on the tests themselves", `" carries @regression, which is not in the vocabulary.`, (text) => text.replace("// ---------------------------------------------------------------- tests that only read\n", "test.describe(\"a group\", { tag: \"@regression\" }, () => {\n") .replace("// ---------------------------------------------------------------- tests that write\n", "});\n"));
    await trial("a test marked to be skipped", `"${T1}" did not pass in every run (skipped)`, swap(`test(\n  "${T1}"`, `test.skip(\n  "${T1}"`), T1);
    await trial("a second layer tag put on one test", `"${T1}" has 2 tags for the dimension Layer: @layer-ui, @layer-api.`, swap(first, `{ tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@layer-api", "@fast"] }`));
    await trial("a tag misspelt", `"${T1}" carries @risk-med, which is not in the vocabulary.`, swap(first, `{ tag: ["@feature-list", "@risk-med", "@read", "@layer-ui", "@fast"] }`));
    await trial("a tag written with a capital", `"${T1}" carries @Fast, which is not in the vocabulary.`, swap(first, `{ tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@Fast"] }`));
    await trial("a tag written into a test's title, where Playwright also reads tags from", `"${T1} @critical" carries @critical, which is not in the vocabulary.`, swap(`"${T1}"`, `"${T1} @critical"`));
    await trial("every tag taken off one test", `"${T1}" has no tag for the dimension Feature.`, swap(first, `{ tag: [] }`));
    log.out("(Two tests with one title are not tried here: Playwright itself refuses to load such a file.)");
    log.out("", "-- What a test does, against its tags");
    await trial("a test that creates and removes a customer tagged @read", `"${T4}" is tagged @read and sent DELETE, POST.`, swap(created, created.replace(`"@write"`, `"@read"`)), T4);
    await trial("a test that only reads tagged @write", `"${T1}" is tagged @write and sent nothing but reads.`, swap(first, first.replace(`"@read"`, `"@write"`)), T1);
    await trial("a test that opens the page tagged @layer-api", `"${T1}" is tagged @layer-api and a browser sent requests.`, swap(first, first.replace(`"@layer-ui"`, `"@layer-api"`)), T1);
    await trial("a test that opens no page tagged @layer-ui", `"${T4}" is tagged @layer-ui and no browser sent a request.`, swap(created, created.replace(`"@layer-api"`, `"@layer-ui"`)), T4);
    await trial("the test that adds sixty customers tagged @fast", `"${T10}" is tagged @fast, whose limit is 2.00 s, and its slowest run took`, swap(bulk, bulk.replace(`"@slow"`, `"@fast"`)), T10);
    await trial("a test made to fail", `"${T1}" did not pass in every run (failed)`, swap(`await expect(rowOf(page, { name: "Asha Verma" })).toContainText("plus");`, `await expect(rowOf(page, { name: "Asha Verma" })).toContainText("basic", { timeout: 500 });`), T1);
    log.out("", "-- The scheme");
    const spoiled = (label: string, expect: string, dimensions: Dimension[], text: string | null = null) => {
      const found = schemeProblems(dimensions, text ?? schemeDocument(dimensions));
      const hit = found.filter((problem) => problem.includes(expect));
      log.out(`Changed: ${label}`, ...[...hit, ...found.filter((p) => !hit.includes(p))].slice(0, 2).map((problem) => `    PROBLEM: ${problem}`));
      log.check(`reported: ${expect}`, hit.length > 0);
    };
    const copy = () => JSON.parse(JSON.stringify(DIMENSIONS)) as Dimension[];
    const altered = (change: (dimensions: Dimension[]) => void) => { const dimensions = copy(); change(dimensions); return dimensions; };
    const where = (dimensions: Dimension[], key: string) => dimensions.find((dimension) => dimension.key === key)!;
    log.out("Each of these is a copy of the vocabulary, in memory, with one thing changed. The document is written from the copy unless it says otherwise.");
    log.check("a copy of the vocabulary with nothing changed: nothing is reported", schemeProblems(copy(), document).length === 0);
    spoiled("the dimension Layer taken out", "The five needed, once each, are", altered((d) => { d.splice(3, 1); }));
    spoiled("the dimension Duration replaced by one called Priority, so there are still five", "The five needed, once each, are", altered((d) => { where(d, "duration").key = "priority"; }));
    spoiled("the limit taken off @slow", "The duration tag @slow has no limit.", altered((d) => { delete where(d, "duration").tags[1].limitMs; }));
    spoiled("both duration tags given one limit", "Two duration tags have the same limit.", altered((d) => { where(d, "duration").tags[1].limitMs = 2000; }));
    spoiled("a second limit written into a meaning", "has a number in it.", altered((d) => { where(d, "duration").tags[0].means = "At most 5 seconds for a test"; }));
    spoiled("the meaning of @risk-low left empty", "@risk-low has no meaning written for it.", altered((d) => { where(d, "risk").tags[2].means = ""; }));
    spoiled("the rule of the dimension Risk left empty", "The dimension Risk has no rule written for it.", altered((d) => { where(d, "risk").rule = ""; }));
    spoiled("the dimension Layer left with one tag", "The dimension Layer has 1 tags.", altered((d) => { where(d, "layer").tags.pop(); }));
    spoiled("@read put into the dimension Layer as well", "A tag is in the vocabulary twice", altered((d) => { where(d, "layer").tags.push({ tag: "@read", means: "The same tag again" }); }));
    spoiled("a tag written without its @", "risk-low is not a tag", altered((d) => { where(d, "risk").tags[2].tag = "risk-low"; }));
    spoiled("one limit in the document on disk edited by hand", "The scheme document on disk is not what the vocabulary gives.", DIMENSIONS, document.replace("at most 2 seconds", "at most 20 seconds"));
    spoiled("a tag added to the document by hand", "The scheme document on disk is not what the vocabulary gives.", DIMENSIONS, document.replace("| `@read` |", "| `@smoke` | The important ones |\n| `@read` |"));
    spoiled("thirty lines of notes added to the end of the document on disk", "One page is at most", DIMENSIONS, document + "A note.\n".repeat(30));
    log.out("Changed: no document on disk", ...schemeProblems(DIMENSIONS, null).map((problem) => `    PROBLEM: ${problem}`));
    log.check("reported: There is no scheme document on disk.", schemeProblems(DIMENSIONS, null).some((problem) => problem.includes("There is no scheme document on disk.")));
    log.check("the two changed documents really differ from the one on disk", document.includes("at most 2 seconds") && document.includes("| `@read` |"));

    log.part("AT THE END");
    const atEnd = await stored();
    log.check("the application holds the customers it started with and no other: every test removed what it made", atEnd === atStart && (JSON.parse(atEnd) as unknown[]).length === 4);
    ended = true;
  } catch (error) {
    log.out("", `THE CHECK STOPPED: ${String(error instanceof Error ? error.message : error).split("\n")[0]}`);
  } finally {
    for (const name of readdirSync(TESTS).filter((one) => /^tagged\.scratch-.*\.spec\.ts$/.test(one))) rmSync(join(TESTS, name), { force: true });
    recorder.close();
    app.kill();
    rmSync(scratch, { recursive: true, force: true });
  }
  log.check("the check ran to its end", ended);
  log.check("tagged.spec.ts is byte for byte what it was at the start, and no changed copy is left beside it", sha(readFileSync(SPEC)) === before && !readdirSync(TESTS).some((one) => one.startsWith("tagged.scratch-")));
  log.save(LOGFILE);
  return log.failed.length ? 1 : 0;
}

if (process.argv.includes("--write-scheme")) {
  mkdirSync(dirname(SCHEME), { recursive: true });
  writeFileSync(SCHEME, schemeDocument());
  console.log(`wrote ${relative(REPO, SCHEME)}: ${schemeDocument().split("\n").length - 1} lines, ${schemeDocument().length} characters`);
  process.exit(0);
}
process.exit(await main());

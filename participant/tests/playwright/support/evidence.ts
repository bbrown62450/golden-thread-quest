/*
 * Failure evidence for the playwright-failure-evidence quest.
 *
 * Import `test` from this file instead of from @playwright/test. Every test then gets a fixture,
 * `evidence`, that runs by itself:
 *
 *   WHILE THE TEST RUNS it listens: every console message, every page error, every request and
 *   its answer. It records a Playwright trace. All of this is held in memory or in a temporary file.
 *
 *   IF THE TEST FAILS it writes one folder, a "failure bundle", with:
 *       READ-ME-FIRST.md      what each file is, for a person who has never seen this test
 *       error.txt             the error message and where in the test it was raised
 *       screenshot.png        the page as it was when the test gave up
 *       console.log           everything the page wrote to the browser's console, with times
 *       failed-requests.json  every request that failed or was answered 400 or above, with the answer's body
 *       requests.txt          every request, one line each, so that the failed ones can be seen in order
 *       server.log            the application's own log for the time the test ran
 *       trace.zip             the Playwright trace: each step, the page's HTML before and after, the network
 *       bundle.json           the test, the times, the commit under test, a checksum of each file, what was redacted
 *
 *   IF THE TEST PASSES it throws the trace away and writes ONE line to passing-runs.log. No
 *   trace, no screenshot, no console log, no request log.
 *
 * SECRETS ARE TAKEN OUT BEFORE ANYTHING IS SAVED, in two ways that do not depend on each other:
 *
 *   1. By value. The fixture learns the secret values of this run as they go by: every cookie
 *      value, every Authorization header, and anything a test hands to `evidence.secret()`, such
 *      as a password it types. Each of those exact strings is replaced wherever it appears, in
 *      every text file and in every text entry inside the trace.
 *   2. By place. Whatever the value, the content of a cookie, set-cookie or authorization header,
 *      of "Bearer ...", of a form field called password, and of anything typed into a password
 *      field is replaced. This catches a secret the fixture never learned.
 *
 *   This computer's own names are replaced too: the home folder, the user name and the machine's
 *   name. A trace records the path of the test file, and that path holds the user name.
 *
 * WHAT IT CANNOT DO
 *   - A picture cannot be searched. A secret that is visible on the screen is in screenshot.png.
 *     So the trace is recorded without its film of screenshots, and the one screenshot must be
 *     looked at by a person before it is shared.
 *   - A secret that is encoded (base64, or URL-encoded with characters that change) is not found
 *     by value. One shorter than 8 characters is not replaced by value, because replacing a short
 *     string everywhere would damage the evidence.
 *
 * The settings come from the configuration file (evidence.config.ts), as the option
 * `evidenceSettings`. This file holds no test and no setting.
 */

import { execFileSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir, hostname, tmpdir, userInfo } from "node:os";
import { join, relative, resolve } from "node:path";

import { test as base, type ConsoleMessage, type Request } from "@playwright/test";

import { looksBinary, readZip, writeZip } from "./zip";

export type EvidenceSettings = {
  /** The folder failure bundles are written to. One folder per failed test. */
  bundlesDir: string;
  /** A failure bundle is deleted this many days after it was made. See support/retention.ts. */
  keepFailureBundleDays: number;
  /** Lines in passing-runs.log older than this many days are deleted. */
  keepPassingLineDays: number;
  /** The application's log file. The part of it for the time the test ran goes into the bundle. */
  serverLog: string;
  /** false turns redaction OFF. Only the check script does that, to show that the scan finds what redaction removes. */
  redact: boolean;
};

export type Evidence = {
  /** Tell the fixture about a secret value the test is about to use, so that it is removed from the evidence. */
  secret(value: string, kind: string): void;
};

export { BUNDLE_FORMAT } from "./retention";
import { BUNDLE_FORMAT } from "./retention";
const REPO = resolve(__dirname, "..", "..", "..", "..");
const SENSITIVE_HEADERS = new Set(["cookie", "set-cookie", "authorization", "proxy-authorization", "x-api-key"]);
const MIN_SECRET_LENGTH = 8;

type Seen = { started: string; ended?: string; method: string; url: string; type: string; status?: number; failure?: string; ms?: number; requestHeaders: Record<string, string>; responseHeaders?: Record<string, string>; body?: string };

class Redactor {
  on: boolean;
  values = new Map<string, string>();     // exact value -> what it is
  counts: Record<string, number> = {};
  tooShort = 0;

  constructor(on: boolean) {
    this.on = on;
    // This computer's names, longest first so that the folder is replaced before the name inside it.
    this.values.set(REPO, "REPO");
    this.values.set(homedir(), "HOME");
    const user = userInfo().username;
    if (user.length >= 4) this.values.set(user, "[user]");
    const host = hostname();
    if (host.length >= 4) this.values.set(host, "[machine]");
  }

  learn(value: string | undefined, kind: string): void {
    if (!value) return;
    if (value.length < MIN_SECRET_LENGTH) {
      this.tooShort += 1;
      return;
    }
    if (!this.values.has(value)) this.values.set(value, `[REDACTED ${kind}]`);
  }

  private count(kind: string, by: number): void {
    if (by > 0) this.counts[kind] = (this.counts[kind] ?? 0) + by;
  }

  text(input: string): string {
    if (!this.on) return input;
    let out = input;
    for (const [value, shown] of [...this.values].sort((a, b) => b[0].length - a[0].length)) {
      const pieces = out.split(value);
      if (pieces.length > 1) {
        this.count(`by value: ${shown.replace(/^\[REDACTED (.*)\]$/, "$1")}`, pieces.length - 1);
        out = pieces.join(shown);
      }
    }
    const byPlace = (pattern: RegExp, kind: string): void => {
      out = out.replace(pattern, (whole: string, before: string, value: string, after: unknown) => {
        if (value.includes("[REDACTED")) return whole;      // already replaced by value
        this.count(`by place: ${kind}`, 1);
        return `${before}[REDACTED ${kind}]${typeof after === "string" ? after : ""}`;
      });
    };
    // A header written as JSON, the way a trace's network file writes it: {"name":"cookie","value":"..."}
    byPlace(/("name"\s*:\s*"(?:cookie|set-cookie|authorization|proxy-authorization|x-api-key)"\s*,\s*"value"\s*:\s*")((?:[^"\\]|\\.)*)(")/gi, "header");
    byPlace(/(\bBearer\s+)([A-Za-z0-9._~+/=-]{8,})/g, "bearer token");
    byPlace(/(\bpassword=)([^&\s"'\\]+)/gi, "password field");
    // A form field written as JSON, the way a trace writes what a form sent: {"name":"password","value":"..."}
    byPlace(/("name"\s*:\s*"[^"]*pass(?:word|wd)[^"]*"\s*,\s*"value"\s*:\s*")((?:[^"\\]|\\.)*)(")/gi, "password field");
    // A trace also lists each request's cookies apart from its headers: "cookies":[{"name":"...","value":"..."}]
    out = out.replace(/("cookies"\s*:\s*\[)((?:[^\]]|\[REDACTED [^\]]*\])*)(\])/g, (_whole: string, before: string, inside: string, after: string) =>
      before + inside.replace(/("value"\s*:\s*")((?:[^"\\]|\\.)*)(")/g, (whole: string, open: string, value: string, close: string) => {
        if (value.includes("[REDACTED")) return whole;
        this.count("by place: cookie", 1);
        return `${open}[REDACTED cookie]${close}`;
      }) + after);
    return out;
  }

  headers(headers: Record<string, string>): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [name, value] of Object.entries(headers)) {
      if (this.on && SENSITIVE_HEADERS.has(name.toLowerCase())) {
        this.count("by place: header", 1);
        out[name] = "[REDACTED header]";
      } else {
        out[name] = this.text(value);
      }
    }
    return out;
  }

  /**
   * By place, in the trace's list of steps: whatever a test typed into a password field. Playwright writes, for each step,
   * the element it found. A step that found an <input type="password"> has its typed value replaced, even if the test
   * never said the value was a secret.
   */
  typedIntoPasswordFields(steps: string): string {
    if (!this.on) return steps;
    const lines = steps.split("\n");
    const parsed = lines.map((line) => {
      try {
        return JSON.parse(line) as { type?: string; callId?: string; message?: string; params?: { value?: unknown; text?: unknown } };
      } catch {
        return null;
      }
    });
    const calls = new Set<string>();
    for (const one of parsed) if (one?.type === "log" && one.callId && /type="password"/.test(one.message ?? "")) calls.add(one.callId);
    const shown = "[REDACTED typed into a password field]";
    return lines.map((line, index) => {
      const one = parsed[index];
      if (!one?.callId || !calls.has(one.callId)) return line;
      let changed = false;
      for (const key of ["value", "text"] as const) {
        const typed = one.params?.[key];
        if (one.type === "before" && typeof typed === "string" && !typed.includes("[REDACTED")) {
          one.params![key] = shown;
          changed = true;
        }
      }
      if (one.type === "log" && /^\s*(?:fill|type|pressSequentially)\("/.test(one.message ?? "") && !(one.message ?? "").includes("[REDACTED")) {
        one.message = `${/^\s*\w+/.exec(one.message ?? "")?.[0]}("${shown}")`;
        changed = true;
      }
      if (!changed) return line;
      this.count("by place: typed into a password field", 1);
      return JSON.stringify(one);
    }).join("\n");
  }

  /** The trace, with every text entry redacted. A picture or other binary entry is kept as it is. */
  zip(file: Buffer): { file: Buffer; entries: number; text: number; binary: number; secretInBinary: number } {
    const entries = readZip(file);
    let text = 0;
    let binary = 0;
    let secretInBinary = 0;
    for (const entry of entries) {
      if (looksBinary(entry.data)) {
        binary += 1;
        if (this.on) for (const value of this.values.keys()) if (entry.data.includes(value)) secretInBinary += 1;
        continue;
      }
      text += 1;
      const redacted = this.text(entry.data.toString("utf8"));
      entry.data = Buffer.from(entry.name.endsWith(".trace") ? this.typedIntoPasswordFields(redacted) : redacted, "utf8");
    }
    return { file: writeZip(entries), entries: entries.length, text, binary, secretInBinary };
  }
}

const READ_ME = `# Read me first

This folder is a failure bundle. A Playwright test failed, and this is everything that was kept about
that one failure. It is meant to be enough to find out why, without running the test again.

Start with \`bundle.json\`: which test, when, and the commit of the code under test.

| File | What it is |
|---|---|
| \`error.txt\` | The error message, and the line of the test that raised it |
| \`screenshot.png\` | The page as it was when the test gave up |
| \`console.log\` | Everything the page wrote to the browser's console, oldest first, with times |
| \`failed-requests.json\` | Every request that failed, or was answered with status 400 or above, with the answer's body |
| \`requests.txt\` | Every request the page made, one line each, oldest first |
| \`server.log\` | The application's own log, for the time the test ran |
| \`trace.zip\` | The Playwright trace: every step of the test, the page's HTML before and after it, and the network |
| \`bundle.json\` | The test, the times, the commit, a checksum of each file here, and what was redacted |

All times are UTC, in the same form in every file, so that lines from different files can be put in order.

To open the trace: \`npx playwright show-trace trace.zip\`. It can also be opened as an ordinary zip file. It
was recorded without its film of screenshots, so the viewer shows the page's HTML at each step and no pictures.

Secrets were removed before these files were saved. Where one was, the text \`[REDACTED ...]\` stands in its
place. The names \`HOME\`, \`REPO\`, \`[user]\` and \`[machine]\` stand for the folder and names of the computer
the test ran on. \`screenshot.png\` is a picture and could not be searched: look at it before sharing it.

This folder is deleted on the date \`bundle.json\` gives as \`deleteAfter\`.
`;

const sha256 = (data: Buffer | string): string => createHash("sha256").update(data).digest("hex");
const stripColour = (text: string): string => text.replace(/\u001b\[[0-9;]*m/g, "");

function commit(): { sha: string; uncommittedChanges: boolean | null; note: string } {
  try {
    const run = (args: string[]): string => execFileSync("git", args, { cwd: REPO, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    const dirty = run(["status", "--porcelain", "--", "participant/tests/playwright"]) !== "";
    return {
      sha: run(["rev-parse", "HEAD"]),
      uncommittedChanges: dirty,
      note: dirty
        ? "The tests folder had changes that were not committed. The commit alone does not say what code ran: see underTest for a checksum of each file."
        : "The tests folder had no uncommitted change.",
    };
  } catch {
    return { sha: "unknown", uncommittedChanges: null, note: "git could not be asked." };
  }
}

export const test = base.extend<{ evidenceSettings: EvidenceSettings; evidence: Evidence }>({
  evidenceSettings: [
    { bundlesDir: join(tmpdir(), "gtq-failure-bundles"), keepFailureBundleDays: 14, keepPassingLineDays: 14, serverLog: "", redact: true },
    { option: true },
  ],

  evidence: [
    async ({ context, page, evidenceSettings: settings, browserName, browser }, use, testInfo) => {
      const redactor = new Redactor(settings.redact);
      const consoleLines: string[] = [];
      const seen = new Map<Request, Seen>();
      const order: Seen[] = [];
      const waiting: Promise<unknown>[] = [];
      const started = new Date();
      const now = (): string => new Date().toISOString();

      context.on("console", (message: ConsoleMessage) => {
        const where = message.location();
        consoleLines.push(`${now()} [${message.type()}] ${message.text()}${where.url ? `  (${where.url}:${where.lineNumber})` : ""}`);
      });
      context.on("weberror", (error) => consoleLines.push(`${now()} [uncaught error] ${error.error().message}`));
      context.on("request", (request) => {
        const headers = request.headers();
        const authorization = headers["authorization"] ?? "";
        redactor.learn(authorization.replace(/^\S+\s+/, ""), "token");
        const row: Seen = { started: now(), method: request.method(), url: request.url(), type: request.resourceType(), requestHeaders: headers };
        seen.set(request, row);
        order.push(row);
      });
      context.on("requestfailed", (request) => {
        const row = seen.get(request);
        if (row) Object.assign(row, { ended: now(), failure: request.failure()?.errorText ?? "failed", ms: Date.now() - Date.parse(row.started) });
      });
      context.on("response", (response) => {
        const row = seen.get(response.request());
        if (!row) return;
        Object.assign(row, { ended: now(), status: response.status(), ms: Date.now() - Date.parse(row.started) });
        waiting.push((async () => {
          try {
            const all = await response.allHeaders();
            row.responseHeaders = all;
            for (const part of (all["set-cookie"] ?? "").split("\n")) redactor.learn(/^[^=]+=([^;]*)/.exec(part)?.[1], "cookie");
            if (response.status() >= 400) row.body = (await response.text()).slice(0, 4000);
          } catch {
            // The page went away before the answer could be read. The status is still recorded.
          }
        })());
      });

      await context.tracing.start({ snapshots: true, screenshots: false, sources: false, title: testInfo.title });
      await use({ secret: (value, kind) => redactor.learn(value, kind) });

      const failed = testInfo.status !== testInfo.expectedStatus;
      const ended = new Date();
      if (!failed) {
        await context.tracing.stop();       // no path: the trace is thrown away
        mkdirSync(settings.bundlesDir, { recursive: true });
        appendFileSync(join(settings.bundlesDir, "passing-runs.log"),
          `${ended.toISOString()} PASSED ${JSON.stringify(testInfo.title)} in ${ended.getTime() - started.getTime()}ms. Kept: this line only\n`, "utf8");
        return;
      }

      const slug = testInfo.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
      const stamp = started.toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
      const folder = join(settings.bundlesDir, `${settings.redact ? "" : "UNREDACTED-"}${stamp}-${slug}${testInfo.retry ? `-retry${testInfo.retry}` : ""}-${randomBytes(3).toString("hex")}`);
      mkdirSync(folder, { recursive: true });
      const problems: string[] = [];
      const files: { name: string; bytes: number; sha256: string }[] = [];
      const save = (name: string, data: Buffer | string): void => {
        writeFileSync(join(folder, name), data);
        files.push({ name, bytes: Buffer.byteLength(data), sha256: sha256(data) });
      };

      try {
        await page.screenshot({ path: join(folder, "screenshot.png"), fullPage: true });
        const picture = readFileSync(join(folder, "screenshot.png"));
        files.push({ name: "screenshot.png", bytes: picture.length, sha256: sha256(picture) });
      } catch (error) {
        problems.push(`no screenshot: ${error instanceof Error ? error.message.split("\n")[0] : "unknown"}`);
      }
      await Promise.all(waiting);
      for (const cookie of await context.cookies().catch(() => [])) redactor.learn(cookie.value, "cookie");

      const rawTrace = join(tmpdir(), `gtq-trace-${randomBytes(6).toString("hex")}.zip`);
      let traceNote: Record<string, number> | null = null;
      try {
        await context.tracing.stop({ path: rawTrace });
        const done = redactor.zip(readFileSync(rawTrace));
        if (done.secretInBinary) problems.push(`${done.secretInBinary} secret value(s) were found inside binary entries of the trace, where they cannot be replaced`);
        save("trace.zip", done.file);
        traceNote = { entries: done.entries, textEntriesRedacted: done.text, binaryEntriesKeptAsTheyWere: done.binary };
      } catch (error) {
        problems.push(`no trace: ${error instanceof Error ? error.message.split("\n")[0] : "unknown"}`);
      } finally {
        rmSync(rawTrace, { force: true });   // the unredacted trace never outlives the test
      }

      const errors = testInfo.errors.map((error, index) => [
        `Error ${index + 1} of ${testInfo.errors.length}`,
        stripColour(error.message ?? "(no message)"),
        "",
        stripColour(error.stack ?? "(no stack)").split("\n").filter((line) => /^\s+at /.test(line)).join("\n"),
      ].join("\n")).join("\n\n");
      save("error.txt", redactor.text([
        `Test: ${testInfo.title}`,
        `Test declared at: ${relative(REPO, testInfo.file)}:${testInfo.line}`,
        `Result: ${testInfo.status}. Expected: ${testInfo.expectedStatus}`,
        `Started ${started.toISOString()}, ended ${ended.toISOString()}`,
        "",
        errors || "(the test recorded no error)",
        "",
      ].join("\n")));
      save("console.log", redactor.text(consoleLines.join("\n") + (consoleLines.length ? "\n" : "")));
      const pathOf = (url: string): string => url.replace(/^https?:\/\/[^/]+/, "");
      save("requests.txt", redactor.text(order.map((row) =>
        `${row.started} ${row.method} ${pathOf(row.url)} -> ${row.failure ? `FAILED ${row.failure}` : row.status ?? "no answer before the test ended"}${row.ms === undefined ? "" : ` ${row.ms}ms`} (${row.type})`).join("\n") + "\n"));
      const bad = order.filter((row) => row.failure || (row.status ?? 0) >= 400);
      save("failed-requests.json", redactor.text(JSON.stringify(bad.map((row) => ({
        started: row.started, ended: row.ended ?? null, method: row.method, url: row.url, resourceType: row.type,
        status: row.status ?? null, failure: row.failure ?? null, durationMs: row.ms ?? null,
        requestHeaders: redactor.headers(row.requestHeaders), responseHeaders: row.responseHeaders ? redactor.headers(row.responseHeaders) : null,
        responseBody: row.body ?? null,
      })), null, 2) + "\n"));

      let serverLines: string[] = [];
      if (settings.serverLog && existsSync(settings.serverLog)) {
        const from = started.getTime() - 50;     // a little slack, since the log's time is taken when the answer is sent
        const to = ended.getTime() + 50;
        serverLines = readFileSync(settings.serverLog, "utf8").split("\n").filter((line) => {
          const at = Date.parse(line.slice(0, 24));
          return !Number.isNaN(at) && at >= from && at <= to;
        });
        save("server.log", redactor.text(serverLines.join("\n") + (serverLines.length ? "\n" : "")));
      } else {
        problems.push("no server log: the configuration names none, or the file is not there");
      }
      save("READ-ME-FIRST.md", READ_ME);

      const deleteAfter = new Date(ended.getTime() + settings.keepFailureBundleDays * 86_400_000).toISOString();
      const underTest = [testInfo.file, join(__dirname, "evidence.ts"), resolve(__dirname, "..", "demo-app", "orders-server.mjs")]
        .filter((file) => existsSync(file) && statSync(file).isFile())
        .map((file) => ({ file: relative(REPO, file), sha256: sha256(readFileSync(file)) }));
      writeFileSync(join(folder, "bundle.json"), redactor.text(JSON.stringify({
        format: BUNDLE_FORMAT,
        test: { title: testInfo.title, file: relative(REPO, testInfo.file), line: testInfo.line, retry: testInfo.retry },
        result: { status: testInfo.status, expected: testInfo.expectedStatus },
        startedAt: started.toISOString(),
        endedAt: ended.toISOString(),
        durationMs: ended.getTime() - started.getTime(),
        browser: { name: browserName, version: browser.version() },
        baseURL: testInfo.project.use.baseURL ?? null,
        commit: commit(),
        underTest,
        kept: { days: settings.keepFailureBundleDays, deleteAfter },
        counts: { consoleLines: consoleLines.length, requests: order.length, failedRequests: bad.length, serverLogLines: serverLines.length },
        trace: traceNote,
        redaction: settings.redact
          ? { on: true, replacements: redactor.counts, valuesTooShortToReplaceByValue: redactor.tooShort, notSearched: ["screenshot.png: a picture"] }
          : { on: false, warning: "REDACTION WAS OFF. THIS BUNDLE MAY HOLD SECRETS. It was made by the check script, to show that the scan finds them." },
        problems,
        files,
      }, null, 2) + "\n"), "utf8");
      console.log(`evidence: failure bundle written: ${relative(settings.bundlesDir, folder)}  (${files.length + 1} files${problems.length ? `, ${problems.length} PROBLEM(S): ${problems.join("; ")}` : ""})`);
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";

/*
 * Does the check notice a broken evidence setup? For the playwright-failure-evidence quest.
 *
 * It puts one fault at a time into the code that collects, redacts and deletes evidence, runs
 * tools/failure-evidence-check.ts, notes which of its checks failed, and takes the fault out
 * again. At the end it makes sure every file is byte for byte what it was. It writes
 * logs/planted-faults.txt.
 *
 * Each fault is a mistake the quest is about: evidence that is not captured, a secret that is
 * not removed, a passing test that keeps too much, evidence that is never deleted. If the check
 * still said "all passed" with one of them in place, the check would be proving nothing.
 *
 * While it runs, the check's own logs and the bundle it saves go to a scratch folder, so the real
 * logs and the handed-in bundle are not replaced. It changes source files while it runs. Do not
 * run the tests at the same time.
 *
 *   node tools/failure-evidence-planted-faults.ts          from participant/tests/playwright
 *
 * Exit code 0 if every fault was noticed and every file was restored.
 */

import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const LOGS = join(resolve(TESTS, "..", ".."), "evidence", "playwright-failure-evidence", "playwright-attempt-003", "logs");
const FIXTURE = "support/evidence.ts";
const RETENTION = "support/retention.ts";
const CONFIG = "evidence.config.ts";
const SPEC = "failure-evidence.spec.ts";

type Fault = { title: string; expect: string; edits: [string, string, string][] };     // [file, text to replace, replacement]

const CLEAN = "this run's bundle, scanned for secrets: none found";

const FAULTS: Fault[] = [
  {
    title: "A. The trace is not saved when a test fails (criterion 1)",
    expect: "TRACE. trace.zip opens",
    edits: [[FIXTURE, "await context.tracing.stop({ path: rawTrace });", "await context.tracing.stop();"]],
  },
  {
    title: "B. No screenshot is taken (criterion 1)",
    expect: "SCREENSHOT. screenshot.png is a PNG picture",
    edits: [[FIXTURE, "await page.screenshot({ path: join(folder, \"screenshot.png\"), fullPage: true });", "throw new Error(\"planted: no screenshot\");"]],
  },
  {
    title: "C. The console log keeps only what the browser itself wrote, not what the page's own script wrote (criterion 1)",
    expect: "CONSOLE LOG. console.log has the page's own error line",
    edits: [[FIXTURE, "const where = message.location();", "const where = message.location();\n        if (/^order page/.test(message.text())) return;"]],
  },
  {
    title: "D. A failed request is recorded without the body of its answer (criterion 1)",
    expect: "FAILED REQUESTS. failed-requests.json has the request answered 500",
    edits: [[FIXTURE, "if (response.status() >= 400) row.body", "if (response.status() >= 600) row.body"]],
  },
  {
    title: "E. Only requests that got no answer at all count as failed. One answered 500 does not (criterion 1)",
    expect: "FAILED REQUESTS. failed-requests.json has the request answered 500",
    edits: [[FIXTURE, "const bad = order.filter((row) => row.failure || (row.status ?? 0) >= 400);", "const bad = order.filter((row) => row.failure);"]],
  },
  {
    title: "F. The error file holds a fixed sentence, not Playwright's message (criterion 1)",
    expect: "ERROR TEXT. error.txt has Playwright's message",
    edits: [[FIXTURE, "stripColour(error.message ?? \"(no message)\"),", "\"A test failed.\","]],
  },
  {
    title: "G. A passing test keeps its trace too (criterion 2)",
    expect: "no trace, screenshot, video, console log or request log was kept anywhere",
    edits: [[FIXTURE, "await context.tracing.stop();       // no path: the trace is thrown away", "await context.tracing.stop({ path: join(settings.bundlesDir, \"passed-trace.zip\") });"]],
  },
  {
    title: "H. Playwright's own trace is switched on as well, so a second, unredacted copy is saved (criterion 3)",
    expect: "Playwright itself saved no trace, screenshot or video of its own",
    edits: [[CONFIG, "    screenshot: \"off\",\n", "    screenshot: \"only-on-failure\",\n"]],
  },
  {
    title: "I. Redaction does nothing at all (criterion 3)",
    expect: CLEAN,
    edits: [[FIXTURE, "    this.on = on;\n", "    this.on = false;\n"]],
  },
  {
    title: "J. The text files are redacted, but the trace is saved as Playwright wrote it (criterion 3)",
    expect: CLEAN,
    edits: [[FIXTURE, "const done = redactor.zip(readFileSync(rawTrace));", "const done = new Redactor(false).zip(readFileSync(rawTrace));"]],
  },
  {
    title: "K. Cookies are not learned, and are not redacted by place either. One alone would be made good by the other (criterion 3)",
    expect: CLEAN,
    edits: [
      [FIXTURE, "redactor.learn(/^[^=]+=([^;]*)/.exec(part)?.[1], \"cookie\");", "void part;"],
      [FIXTURE, "redactor.learn(cookie.value, \"cookie\");", "void cookie;"],
      [FIXTURE, "(?:cookie|set-cookie|authorization|proxy-authorization|x-api-key)\"\\s*,", "(?:authorization|proxy-authorization|x-api-key)\"\\s*,"],
      [FIXTURE, "        this.count(\"by place: cookie\", 1);\n        return `${open}[REDACTED cookie]${close}`;", "        return whole;"],
    ],
  },
  {
    title: "L. The token is not learned, and \"Bearer ...\" is not redacted by place (criterion 3)",
    expect: CLEAN,
    edits: [
      [FIXTURE, "redactor.learn(authorization.replace(/^\\S+\\s+/, \"\"), \"token\");", "void authorization;"],
      [FIXTURE, "    byPlace(/(\\bBearer\\s+)([A-Za-z0-9._~+/=-]{8,})/g, \"bearer token\");\n", ""],
    ],
  },
  {
    title: "M. The test does not say its password is a secret, and what is typed into a password field is not redacted by place (criterion 3)",
    expect: "the password this script chose is nowhere in the bundle",
    edits: [
      [SPEC, "  evidence.secret(typed, \"password\");\n", ""],
      [FIXTURE, "entry.name.endsWith(\".trace\") ? this.typedIntoPasswordFields(redacted) : redacted", "redacted"],
    ],
  },
  {
    title: "N. This computer's folder and user name are left in the evidence (criterion 3, and the quest's rule on personal data)",
    expect: CLEAN,
    edits: [
      [FIXTURE, "    this.values.set(REPO, \"REPO\");\n    this.values.set(homedir(), \"HOME\");\n", ""],
      [FIXTURE, "if (user.length >= 4) this.values.set(user, \"[user]\");", "void user;"],
    ],
  },
  {
    title: "O. Expired evidence is never deleted (criterion 6)",
    expect: "the bundle past its date was deleted",
    edits: [[RETENTION, "else if (deleteAfter <= now.getTime()) {", "else if (deleteAfter <= 0) {"]],
  },
  {
    title: "P. The cleanup deletes any folder with a bundle.json and an old date, whatever its format (criterion 6)",
    expect: "the folder with a bundle.json of another format was left alone",
    edits: [[RETENTION, "if (bundle.format === BUNDLE_FORMAT) deleteAfter", "deleteAfter"]],
  },
  {
    title: "Q. Evidence is kept for 30 days, though the configuration's own words say 14 (criterion 6)",
    expect: "14 days after the test ended, to the millisecond",
    edits: [[CONFIG, "  keepFailureBundleDays: 14,\n", "  keepFailureBundleDays: 30,\n"]],
  },
  {
    title: "R. The bundle holds the application's whole log, not the part for the test's own seconds (stretch goal; criterion 7)",
    expect: "server.log holds only lines from the test's own time window",
    edits: [[FIXTURE, "return !Number.isNaN(at) && at >= from && at <= to;", "return !Number.isNaN(at);"]],
  },
];

function check(scratch: string): { code: number; failed: string[]; summary: string[] } {
  const done = spawnSync(process.execPath, ["tools/failure-evidence-check.ts", "--save-bundle"], {
    cwd: TESTS, env: { ...process.env, GTQ_CHECK_LOGS: join(scratch, "logs"), GTQ_CHECK_BUNDLE: join(scratch, "bundle") }, encoding: "utf8",
  });
  const lines = `${done.stdout}`.split("\n");
  return {
    code: done.status ?? 1,
    failed: lines.filter((line) => line.startsWith("  FAILED: ")).map((line) => line.slice("  FAILED: ".length)),
    summary: lines.filter((line) => /^RESULT:/.test(line)),
  };
}

const FILES = [FIXTURE, RETENTION, CONFIG, SPEC];
const good = new Map(FILES.map((file) => [file, readFileSync(join(TESTS, file), "utf8")]));
const restore = (): void => {
  for (const [file, text] of good) writeFileSync(join(TESTS, file), text, "utf8");
};
const scratch = mkdtempSync(join(tmpdir(), "gtq-evidence-faults-"));
const out = [
  "Does the check notice a broken evidence setup? playwright-failure-evidence, attempt playwright-attempt-003",
  "Recorded by tools/failure-evidence-planted-faults.ts.",
  "",
  "Each fault below was put into the files under participant/tests/playwright that collect, redact and delete evidence",
  "(support/evidence.ts, support/retention.ts, evidence.config.ts, failure-evidence.spec.ts). The whole check",
  "(tools/failure-evidence-check.ts) was then run, and the fault was taken out again. Only this computer is used.",
  "\"Noticed\" means more than \"the check failed\": the check that failed must be the one the fault is about.",
  "",
];
const missed: string[] = [];

const clean = check(scratch);
out.push(`Before any fault: exit code ${clean.code}. ${clean.summary.join(" ")}`, "");
let ok = clean.code === 0;

try {
  for (const fault of FAULTS) {
    out.push(`PLANTED FAULT ${fault.title}`);
    const changed = new Map(good);
    let planted = true;
    for (const [file, from, to] of fault.edits) {
      const text = changed.get(file) ?? "";
      if (text.split(from).length !== 2) planted = false;
      changed.set(file, text.split(from).join(to));
    }
    if (!planted) {
      out.push("  COULD NOT BE PLANTED: the text to replace was not found once", "");
      missed.push(fault.title);
      continue;
    }
    for (const [file, text] of changed) writeFileSync(join(TESTS, file), text, "utf8");
    const result = check(scratch);
    restore();
    rmSync(join(scratch, "bundle"), { recursive: true, force: true });
    const noticed = result.code !== 0 && result.failed.some((line) => line.includes(fault.expect));
    out.push(`  the check's exit code: ${result.code}. ${result.summary.join(" ")}`, `  checks that failed (${result.failed.length}):`);
    out.push(...(result.failed.length ? result.failed.map((line) => `    ${line}`) : ["    NONE. THIS FAULT WAS NOT NOTICED."]));
    out.push(`  ${noticed ? "noticed, by the check it should trip" : `NOT NOTICED by the check it should trip, the one about "${fault.expect}"`}`, "");
    if (!noticed) missed.push(fault.title);
  }
} finally {
  restore();
  rmSync(scratch, { recursive: true, force: true });
}

const restored = FILES.every((file) => readFileSync(join(TESTS, file), "utf8") === good.get(file));
ok = ok && restored && missed.length === 0;
out.push(`After the last fault was taken out: the ${FILES.length} files are ${restored ? "byte for byte what they were" : "NOT what they were"} at the start.`, "");
out.push(`RESULT: ${ok ? `all ${FAULTS.length} planted faults were noticed by the check, and the files were restored.` : `NOT ALL AS EXPECTED: ${missed.join("; ") || "see above"}`}`);
mkdirSync(LOGS, { recursive: true });
writeFileSync(join(LOGS, "planted-faults.txt"), out.join("\n") + "\n", "utf8");
console.log(out[out.length - 1]);
process.exit(ok ? 0 : 1);

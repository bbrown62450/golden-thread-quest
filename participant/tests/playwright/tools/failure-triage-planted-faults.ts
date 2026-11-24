/*
 * Does the check notice a triage report that breaks the rules? For the playwright-failure-triage quest.
 *
 * tools/failure-triage-check.ts already breaks the REPORT in sixteen ways and shows each is reported. This script
 * does the other half: it breaks the CHECK. It puts one fault at a time into failure-triage-check.ts, each one a rule
 * the check silently stops enforcing, runs the check, and looks at whether the check's own "can the check fail?"
 * cases then catch it. If a weakened check still said "all passed", its part 3 would be proving nothing.
 *
 * While it runs, the check's log goes to a scratch folder, so the real log is not replaced. It changes
 * failure-triage-check.ts while it runs and restores it. It runs no test and starts nothing.
 *
 *   node tools/failure-triage-planted-faults.ts          from participant/tests/playwright
 *
 * Exit code 0 if every fault was noticed and the file was restored.
 */

import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const LOGS = join(resolve(TESTS, "..", ".."), "evidence", "playwright-failure-triage", "playwright-attempt-004", "logs");
const CHECK = "tools/failure-triage-check.ts";

type Fault = { title: string; expect: string; edits: [string, string, string][] };     // [file, text to replace, replacement]

const FAULTS: Fault[] = [
  {
    title: "A. Any word is accepted as a class, so \"flaky\" passes (criteria 1 and 3)",
    expect: "a failure classed as \"flaky\"",
    edits: [[CHECK, "    else if (!CLASSES.includes(given)) say(", "    else if (false) say("]],
  },
  {
    title: "B. Two classes on one failure are not noticed (criterion 1)",
    expect: "a failure given two classes",
    edits: [[CHECK, "    if (entry.repeated.includes(\"class\")) say(\"it is given more than one class\");", ""]],
  },
  {
    title: "C. A classification that cites nothing is accepted (criterion 2)",
    expect: "a classification that cites no file",
    edits: [[CHECK, "    if (!cited.length) say(", "    if (false) say("]],
  },
  {
    title: "D. A cited file need not be in the bundle (criterion 2)",
    expect: "cites a file that does not exist in the bundle",
    edits: [[CHECK, "      if (!bundle.files.includes(file)) say(`it cites ${file}, which is not in its bundle`);\n      else if", "      if"]],
  },
  {
    title: "E. A cited file need not be used in the reason (criterion 2)",
    expect: "cites a real file its reason never uses",
    edits: [[CHECK, "      else if (!entry.reason.includes(file.split(\"!\").pop() ?? file)) say(", "      else if (false) say("]],
  },
  {
    title: "F. A failure that passed on retry need not explain the retry (criterion 3)",
    expect: "without its explanation of the retry",
    edits: [[CHECK, "      if (!entry.fields.retry_explained || entry.fields.retry_explained.length < 40) say(", "      if (false) say("]],
  },
  {
    title: "G. A failure that passed on retry need not cite attempts.json (criterion 3)",
    expect: "does not cite attempts.json",
    edits: [[CHECK, "      if (!cited.includes(\"attempts.json\")) say(", "      if (false) say("]],
  },
  {
    title: "H. Inconclusive need not say what would settle it (criterion 4)",
    expect: "does not say what would settle it",
    edits: [[CHECK, "      if (!entry.fields.would_settle || entry.fields.would_settle.length < 30) say(", "      if (false) say("]],
  },
  {
    title: "I. Inconclusive need not name two possible classes (criterion 4)",
    expect: "names only one possible class",
    edits: [[CHECK, "      if (possible.length < 2) say(", "      if (false) say("]],
  },
  {
    title: "J. A classification need not state a next action (criterion 5)",
    expect: "a classification with no next action",
    edits: [[CHECK, "    if (!entry.fields.next_action) say(\"it states no next action\");", ""]],
  },
  {
    title: "K. A classification need not say who acts (criterion 5)",
    expect: "names nobody to act",
    edits: [[CHECK, "    if (!entry.fields.owner) say(\"it does not say who takes the next action\");\n    else if", "    if"]],
  },
  {
    title: "L. Any role may be given any class of failure (criterion 5)",
    expect: "sent to the wrong role",
    edits: [[CHECK, "given && OWNERS[given] && entry.fields.owner !== OWNERS[given]) say(", "false) say("]],
  },
  {
    title: "M. A bundle the report leaves out is not noticed",
    expect: "a failure left out of the report",
    edits: [[CHECK, "  for (const bundle of bundles) if (!seen.has(bundle.name)) wrong.push(", "  for (const bundle of [] as Bundle[]) if (!seen.has(bundle.name)) wrong.push("]],
  },
  {
    title: "N. A classification with no bundle behind it is accepted",
    expect: "a failure that has no bundle",
    edits: [[CHECK, "    if (!bundle) {\n      say(\"it is classified, and there is no bundle of that name. A failure is not classified without its evidence\");\n      continue;", "    if (!bundle) {\n      continue;"]],
  },
  {
    title: "O. A failure classified twice is not noticed (criterion 1)",
    expect: "a failure classified twice",
    edits: [[CHECK, "    if (seen.has(entry.name)) say(\"it is classified more than once in the report\");", ""]],
  },
  {
    title: "P. The scan of the bundles finds nothing, whatever they hold",
    expect: "holds no cookie, token or password",
    edits: [[CHECK, "    log.check(`${bundle.name}: it holds no cookie, token or password, and none of this computer's names`, scan.searched >= 12 && scan.findings.length === 0);",
      "    log.check(`${bundle.name}: it holds no cookie, token or password, and none of this computer's names`, scan.searched >= 12 && scan.findings.length === 0 && scanBundle(join(FAILURES_DIR, \"none\")).searched > 0);"]],
  },
];

function check(scratch: string): { code: number; failed: string[]; summary: string[] } {
  const done = spawnSync(process.execPath, [CHECK], { cwd: TESTS, env: { ...process.env, GTQ_CHECK_LOGS: join(scratch, "logs") }, encoding: "utf8" });
  const lines = `${done.stdout}`.split("\n");
  return {
    code: done.status ?? 1,
    failed: lines.filter((line) => line.startsWith("  FAILED: ")).map((line) => line.slice("  FAILED: ".length)),
    summary: lines.filter((line) => /RESULT:/.test(line)),
  };
}

const FILES = [CHECK];
const good = new Map(FILES.map((file) => [file, readFileSync(join(TESTS, file), "utf8")]));
const restore = (): void => {
  for (const [file, text] of good) writeFileSync(join(TESTS, file), text, "utf8");
};
const scratch = mkdtempSync(join(tmpdir(), "gtq-triage-faults-"));
const out = [
  "Does the check notice when it has itself been weakened? playwright-failure-triage, attempt playwright-attempt-004",
  "Recorded by tools/failure-triage-planted-faults.ts.",
  "",
  "Each fault below was put into participant/tests/playwright/tools/failure-triage-check.ts: one rule the check silently stops enforcing. The check was then",
  "run, and the fault was taken out again. Nothing is run but the check, which reads files only.",
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

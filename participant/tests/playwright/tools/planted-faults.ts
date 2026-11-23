/*
 * Does the check notice broken tests? For the playwright-data-isolation quest.
 *
 * It puts one fault at a time into isolated.spec.ts, runs tools/data-isolation-check.ts, notes
 * which of its checks failed, and takes the fault out again. At the end it makes sure the file
 * is byte for byte what it was. It writes logs/planted-faults.txt.
 *
 * Each fault is one of the mistakes the quest is about. If the check still said "all passed"
 * with one of them in place, the check would be proving nothing.
 *
 * While it runs, the check's own two logs go to a scratch folder, so the real logs are not
 * replaced. It changes isolated.spec.ts while it runs. Do not run the tests at the same time.
 *
 *   node tools/planted-faults.ts          from participant/tests/playwright
 *
 * Exit code 0 if every fault was noticed and the file was restored.
 */

import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TARGET = join(TESTS, "isolated.spec.ts");
const LOGS = join(resolve(TESTS, "..", ".."), "evidence", "playwright-data-isolation", "playwright-attempt-002", "logs");

type Fault = { title: string; expect: string; edits: [string, string][] };

const FAULTS: Fault[] = [
  {
    title: "A. Every test gives its customers a fixed name, not a unique one (criterion 2). This is the scenario's \"Test User\"",
    expect: "ran at once",
    edits: [["uniqueName: (label) => `${label} ${RUN_MARKER}-${randomUUID()}`,", "uniqueName: (label) => `Test ${label}`,"]],
  },
  {
    title: "B. Tests do not clean up at all (criterion 3)",
    expect: "no test data remains",
    edits: [["for (const id of mine.reverse()) {", "for (const id of [] as string[]) {"]],
  },
  {
    title: "C. Cleanup runs only after a pass. This is the quest's hint: debris exactly when the evidence is needed",
    expect: "cleanup ran although the test did not finish",
    edits: [
      ["own: async ({ request }, use) => {", "own: async ({ request }, use, testInfo) => {"],
      ["    await use(own);\n", "    await use(own);\n    if (testInfo.status !== testInfo.expectedStatus) return;\n"],
    ],
  },
  {
    title: "D. Cleanup also removes every customer whose name starts with \"Test\", to be thorough (criteria 3 and 7)",
    expect: "no data that existed before was removed or altered",
    edits: [[
      "    expect(problems, \"cleanup should remove every customer this test created\").toEqual([]);",
      "    for (const one of (await (await request.get(\"/api/customers\")).json()) as Customer[]) {\n" +
      "      if (one.name.startsWith(\"Test\")) await request.delete(`/api/customers/${one.id}`);\n" +
      "    }\n" +
      "    expect(problems, \"cleanup should remove every customer this test created\").toEqual([]);",
    ]],
  },
];

function check(logs: string): { code: number; failed: string[]; summary: string[] } {
  const done = spawnSync(process.execPath, ["tools/data-isolation-check.ts"], { cwd: TESTS, env: { ...process.env, GTQ_CHECK_LOGS: logs }, encoding: "utf8" });
  const lines = `${done.stdout}`.split("\n");
  return {
    code: done.status ?? 1,
    failed: lines.filter((line) => line.startsWith("  FAILED: ")).map((line) => line.slice("  FAILED: ".length)),
    summary: lines.filter((line) => /RESULT:/.test(line)),
  };
}

const good = readFileSync(TARGET, "utf8");
const scratch = mkdtempSync(join(tmpdir(), "gtq-planted-faults-"));
const out = [
  "Does the check notice broken tests? playwright-data-isolation, attempt playwright-attempt-002",
  "Recorded by tools/planted-faults.ts.",
  "",
  "Each fault below was put into participant/tests/playwright/isolated.spec.ts, the whole check",
  "(tools/data-isolation-check.ts) was run, and the fault was taken out again. Only this computer is used.",
  "",
];
const missed: string[] = [];

const clean = check(scratch);
out.push(`Before any fault: exit code ${clean.code}. ${clean.summary.join(" ")}`, "");
let ok = clean.code === 0;

try {
  for (const fault of FAULTS) {
    out.push(`PLANTED FAULT ${fault.title}`);
    let text = good;
    let planted = true;
    for (const [from, to] of fault.edits) {
      if (text.split(from).length !== 2) planted = false;
      text = text.replace(from, to);
    }
    if (!planted) {
      out.push("  COULD NOT BE PLANTED: the text to replace was not found once", "");
      missed.push(fault.title);
      continue;
    }
    writeFileSync(TARGET, text, "utf8");
    const result = check(scratch);
    writeFileSync(TARGET, good, "utf8");
    const noticed = result.code !== 0 && result.failed.some((line) => line.includes(fault.expect));
    out.push(`  the check's exit code: ${result.code}. ${result.summary.join(" ")}`, `  checks that failed (${result.failed.length}):`);
    out.push(...(result.failed.length ? result.failed.map((line) => `    ${line}`) : ["    NONE. THIS FAULT WAS NOT NOTICED."]));
    out.push(`  ${noticed ? "noticed, by the check it should trip" : `NOT NOTICED by the check it should trip, the one about "${fault.expect}"`}`, "");
    if (!noticed) missed.push(fault.title);
  }
} finally {
  writeFileSync(TARGET, good, "utf8");
  rmSync(scratch, { recursive: true, force: true });
}

const restored = readFileSync(TARGET, "utf8") === good;
ok = ok && restored && missed.length === 0;
out.push(`After the last fault was taken out: isolated.spec.ts is ${restored ? "byte for byte what" : "NOT what"} it was at the start.`, "");
out.push(`RESULT: ${ok ? `all ${FAULTS.length} planted faults were noticed by the check, and the file was restored.` : `NOT ALL AS EXPECTED: ${missed.join("; ") || "see above"}`}`);
mkdirSync(LOGS, { recursive: true });
writeFileSync(join(LOGS, "planted-faults.txt"), out.join("\n") + "\n", "utf8");
console.log(out[out.length - 1]);
process.exit(ok ? 0 : 1);

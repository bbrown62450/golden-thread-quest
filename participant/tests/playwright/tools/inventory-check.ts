/*
 * Makes the run record of the playwright-test-inventory quest: logs/inventory-run.txt in the attempt folder.
 *
 *   node tools/inventory-check.ts
 *
 * Node 22.18 or later. It runs the generator, tools/inventory.ts, as a command, the way a person would, and writes
 * down what it printed. It runs no test and starts no application.
 *
 * TWO READERS OF THE SAME FILES. The generator reads the test files as text. To see whether it read them rightly, this
 * check asks Playwright to LIST the tests of the same file and compares the two, test by test: title, line, tags,
 * identifier, purpose and source. LISTING IS NOT READING AS TEXT: `--list` loads the file, so the code at its top
 * level and in the bodies of its groups runs. No test's own body runs, and no application is started. That loading
 * is done by this check and never by the generator. The value scores are worked out again here, by a table written
 * separately from the generator's rule. That shows the generator follows the stated rule. It does not show the rule
 * is a good one.
 *
 * WHAT IT NEVER WRITES TO: inventoried.spec.ts, the requirements, and the inventory on disk. Every changed test file
 * is a copy named inventoried.scratch-*.spec.ts beside the original, deleted when the check ends. Every inventory it
 * generates goes to a temporary folder.
 *
 * WHAT IT CANNOT TEST
 *   Whether a purpose is true, or says anything worth saying. It can count its words and compare it with the title.
 *   Whether two tests with one purpose check the same thing. It reports them. A person looks.
 *   Whether a new teammate could find their way. It checks that each requirement's row lists exactly its tests.
 */

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { DIMENSIONS, TAGS } from "../support/tags.ts";
import { readRequirements, rowOf } from "./inventory.ts";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-test-inventory", "playwright-attempt-010");
const SPEC = join(TESTS, "inventoried.spec.ts");
const INVENTORY = join(PARTICIPANT, "context", "playwright", "inventory.md");
const REQUIREMENTS = join(PARTICIPANT, "context", "playwright", "directory-requirements.md");
const LOGFILE = join(ATTEMPT, "logs", "inventory-run.txt");
const scratch = mkdtempSync(join(tmpdir(), "gtq-inventory-"));

const sha = (data: string | Buffer) => createHash("sha256").update(data).digest("hex");
const tidy = (text: string) => text.replace(/\u001b\[[0-9;]*m/g, "").split(scratch).join("TEMP").split(REPO + "/").join("").split(REPO).join("REPO");

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
  /** Runs the generator as a command, writes down the command and what it printed, and returns both. */
  generate(...args: string[]): { code: number; text: string } {
    const done = spawnSync(process.execPath, ["--no-warnings", "tools/inventory.ts", ...args], { cwd: TESTS, encoding: "utf8" });
    const text = tidy((done.stdout + done.stderr).trimEnd());
    this.lines.push(`$ node tools/inventory.ts ${args.map(tidy).join(" ")}`, "-".repeat(78), text, "-".repeat(78), `exit code: ${done.status}`);
    return { code: done.status ?? -1, text };
  }
  save(file: string) {
    this.lines.push("", this.failed.length ? `RESULT: ${this.failed.length} OF ${this.count} CHECKS FAILED.` : `RESULT: ALL CHECKS PASSED. ${this.count} checks.`);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, this.lines.map(tidy).join("\n") + "\n");
    console.log(`${relative(ATTEMPT, file)}: ${this.lines[this.lines.length - 1]}`);
    for (const label of this.failed) console.log(`  FAILED: ${label}`);
  }
}

// ---------------------------------------------------------------- the second reader: Playwright's own list

type Listed = { title: string; line: number; tags: string[]; notes: Map<string, string[]> };

function playwrightList(spec: string): Listed[] {
  const file = join(scratch, "list.json");
  rmSync(file, { force: true });
  spawnSync(process.execPath, [CLI, "test", "-c", "inventory.config.ts", "--list", "--reporter=json"],
    { cwd: TESTS, env: { ...process.env, INVENTORY_SPEC: spec, PLAYWRIGHT_JSON_OUTPUT_FILE: file, PLAYWRIGHT_JSON_OUTPUT_NAME: file, FORCE_COLOR: "0" }, stdio: "ignore" });
  if (!existsSync(file)) return [];
  const found: Listed[] = [];
  const walk = (suite: any, prefix: string[]) => {
    for (const one of suite.specs ?? []) {
      const notes = new Map<string, string[]>();
      for (const note of one.tests?.[0]?.annotations ?? []) notes.set(note.type, [...(notes.get(note.type) ?? []), String(note.description ?? "")]);
      found.push({ title: [...prefix, one.title].join(" > "), line: one.line, tags: (one.tags ?? []).map((tag: string) => "@" + tag).sort(), notes });
    }
    for (const inner of suite.suites ?? []) walk(inner, [...prefix, inner.title]);
  };
  for (const suite of JSON.parse(readFileSync(file, "utf8")).suites ?? []) walk(suite, []);
  return found.sort((a, b) => a.line - b.line);
}

// ---------------------------------------------------------------- reading an inventory back, as a person would

type Row = { id: string; purpose: string; tags: string[]; source: string; value: string; where: string };

const section = (text: string, heading: string) => (text.split(`\n## ${heading}\n`)[1] ?? "").split("\n## ")[0];
const tableRows = (text: string) => text.split("\n").filter((line) => line.startsWith("| ") && !line.startsWith("|---")).slice(1).map((line) => line.slice(2, -2).split(" | "));
/** The identifiers in a cell such as "DIR-T01 (`file:12`), DIR-T02 (`file:30`)", with the place given for each. */
const placed = (cell: string) => [...(cell ?? "").matchAll(/([^\s,(]+) \(`([^`]+)`\)/g)].map((match) => ({ id: match[1], where: match[2] }));

function rowsOf(inventory: string): Row[] {
  return tableRows(section(inventory, "Every test")).map(([id, purpose, tags, source, value, where]) => ({ id, purpose, tags: (tags ?? "").split(" ").sort(), source, value, where: (where ?? "").replace(/`/g, "") }));
}

/** The value a test should have, from a table written here and not taken from the generator. */
const VALUE: Record<string, Record<string, string>> = {
  must: { "@risk-high": "high", "@risk-medium": "medium", "@risk-low": "low" },
  should: { "@risk-high": "medium", "@risk-medium": "low", "@risk-low": "low" },
  could: { "@risk-high": "low", "@risk-medium": "low", "@risk-low": "low" },
};

// ---------------------------------------------------------------- the run

const TAGS5 = `["@feature-list", "@risk-medium", "@read", "@layer-api", "@fast"]`;
function extra(title: string, notes: string[], tags = TAGS5): string {
  return `\ntest(\n  "${title}",\n  {\n    tag: ${tags},\n    annotation: [\n${notes.map((note) => `      ${note},\n`).join("")}    ],\n  },\n  async ({ request }) => {\n    expect((await request.get("/api/stats")).status()).toBe(200);\n  },\n);\n`;
}
const note = (type: string, text: string) => `{ type: "${type}", description: "${text}" }`;
const NEW_PURPOSE = "Show that the data interface gives the number of customers on each plan.";

function main(): number {
  const log = new Log("The inventory run. playwright-test-inventory, attempt playwright-attempt-010",
    "Recorded by participant/tests/playwright/tools/inventory-check.ts. Each block between dashed lines is what the generator printed.",
    "No test was run and no application was started. Where it says Playwright lists a file, Playwright loaded that file to list it, which the",
    "generator never does. TEMP stands for a temporary folder. Paths are from the repository's top folder,",
    "or, for test files, from participant/tests/playwright. Nothing here is from a real system: the directory and its customers are made up.");
  rmSync(LOGFILE, { force: true });
  const original = readFileSync(SPEC, "utf8");
  const allSpecs = () => readdirSync(TESTS).filter((one) => one.endsWith(".spec.ts") && !one.includes(".scratch-")).sort().map((one) => `${one} ${sha(readFileSync(join(TESTS, one)))}`).join("\n");
  const everySpecBefore = allSpecs();
  const before = { spec: sha(original), inventory: existsSync(INVENTORY) ? sha(readFileSync(INVENTORY)) : "", requirements: sha(readFileSync(REQUIREMENTS)) };
  log.out(`Read: inventoried.spec.ts sha256 ${before.spec.slice(0, 16)}   directory-requirements.md sha256 ${before.requirements.slice(0, 16)}`);
  let number = 0, ended = false;
  const copy = (text: string) => {
    number += 1;
    const name = `inventoried.scratch-${number}.spec.ts`;
    writeFileSync(join(TESTS, name), text);
    return name;
  };
  try {
    // ------------------------------------------------------------ part 1
    log.part("PART 1. Generated from the test files, twice, with identical results (criteria 1 and 5)");
    const first = log.generate("--out", join(scratch, "first.md"));
    const second = log.generate("--out", join(scratch, "second.md"));
    const a = readFileSync(join(scratch, "first.md")), b = readFileSync(join(scratch, "second.md"));
    log.out(`first:  ${a.length} bytes, sha256 ${sha(a)}`, `second: ${b.length} bytes, sha256 ${sha(b)}`);
    log.check("criterion 5: the two inventories are the same, byte for byte", first.code === 0 && second.code === 0 && a.equals(b) && a.length > 1000);
    log.check("criterion 5: the inventory holds nothing written as a date (2026-01-31) or as a time of day (12:30)", !/\b20\d\d-\d\d-\d\d\b|\b\d\d:\d\d(:\d\d)?\b/.test(a.toString()));
    log.out("", "The inventory on disk, participant/context/playwright/inventory.md, checked against what the generator would write now:");
    const upToDate = log.generate("--check");
    log.check("criterion 1: the inventory on disk is, byte for byte, what the generator gives from the test files today", upToDate.code === 0 && upToDate.text.includes("UP TO DATE") && existsSync(INVENTORY) && readFileSync(INVENTORY).equals(a));
    const source = readFileSync(join(TESTS, "tools", "inventory.ts"), "utf8");
    const imports = [...source.matchAll(/^import .* from "([^"]+)";$/gm)].map((match) => match[1]);
    log.out(`What the generator's own file imports: ${imports.join(", ")}.`);
    log.check("the generator imports nothing that could load or run a test: no child_process, no Playwright, and no test file", imports.length > 0 && imports.every((one) => /^node:(crypto|fs|path|url)$/.test(one) || one === "../support/tags.ts") && imports.length === (source.match(/^import\b/gm) ?? []).length && !/\bimport\(|require\(|child_process|playwright\/test/.test(source.replace(/\/\*[\s\S]*?\*\//g, "")));
    log.check("the generator's file has one call that writes a file, and it writes the inventory", (source.match(/writeFileSync\(|appendFileSync\(|createWriteStream\(|renameSync\(|copyFileSync\(|rmSync\(|unlinkSync\(/g) ?? []).length === 1 && source.includes("writeFileSync(out, inventory.text)"));
    log.out("", "Told to write the inventory over the test file:");
    const over = log.generate("--out", SPEC);
    log.check("the generator will not write to a file that is not .md, so it cannot be aimed at a test file", over.code === 2 && over.text.includes("ends in .md") && sha(readFileSync(SPEC)) === before.spec);

    // ------------------------------------------------------------ part 2
    log.part("PART 2. Every test has an identifier, a purpose, tags, a source and a value (criterion 2)",
      "The inventory on disk is read back here as a person would read it: the rows of its table 'Every test'.",
      "Playwright is then asked to list the tests of the same file, and the two are compared test by test.");
    const inventory = readFileSync(INVENTORY, "utf8");
    const rows = rowsOf(inventory);
    const listed = playwrightList("inventoried.spec.ts");
    const requirements = new Map(tableRows(section(readFileSync(REQUIREMENTS, "utf8"), "The requirements")).map(([id, importance]) => [id, importance]));
    for (const row of rows) log.out(`  ${row.id.padEnd(8)} ${row.source.padEnd(7)} ${row.value.padEnd(7)} ${row.where.padEnd(26)} ${row.purpose}`);
    log.check(`the inventory has one row for each test Playwright lists: ${rows.length} rows, ${listed.length} tests`, rows.length === listed.length && rows.length >= 8);
    log.check("criterion 2: every row has an identifier, a purpose, tags, a source, a value and a place, and none is 'none'", rows.length > 0 && rows.every((row) => [row.id, row.purpose, row.source, row.value, row.where, row.tags.join(" ")].every((cell) => cell && !cell.includes("none"))));
    log.check("criterion 2: no two rows have one identifier", new Set(rows.map((row) => row.id)).size === rows.length);
    log.check("criterion 2: every value is high, medium or low", rows.every((row) => ["high", "medium", "low"].includes(row.value)));
    const pairs = rows.map((row) => ({ row, test: listed.find((test) => `inventoried.spec.ts:${test.line}` === row.where) }));
    log.check("the place in each row is the line where Playwright says a test is declared", pairs.every(({ test }) => test !== undefined));
    log.check("the identifier in each row is the one Playwright reads from that test's annotations", pairs.every(({ row, test }) => test?.notes.get("id")?.join("|") === row.id));
    log.check("the purpose in each row is the one Playwright reads, character for character", pairs.every(({ row, test }) => test?.notes.get("purpose")?.join("|") === row.purpose));
    log.check("the source in each row is the one Playwright reads", pairs.every(({ row, test }) => test?.notes.get("source")?.join("|") === row.source));
    log.check("the tags in each row are the tags Playwright would select that test by", pairs.every(({ row, test }) => test?.tags.join(" ") === row.tags.join(" ")));
    log.check("each row has exactly one tag from each of the five dimensions of the tag scheme", rows.every((row) => DIMENSIONS.every((dimension) => row.tags.filter((tag) => TAGS.get(tag) === dimension.key).length === 1)));
    log.check("every source is a current requirement in directory-requirements.md", rows.every((row) => requirements.has(row.source)));
    const expected = (row: Row) => VALUE[requirements.get(row.source) ?? ""]?.[row.tags.find((tag) => TAGS.get(tag) === "risk") ?? ""];
    const wrong = rows.filter((row) => expected(row) !== row.value).map((row) => row.id);
    log.check(`the value in each row is what a table written in this check gives for its requirement's importance and its risk tag${wrong.length ? `. NOT: ${wrong.join(", ")}` : ""}`, wrong.length === 0);
    log.check("each of the three levels is the value of at least one test", ["high", "medium", "low"].every((level) => rows.some((row) => row.value === level)));
    const cells: string[] = [];
    const three = readRequirements("| A-1 | must | x |\n| A-2 | should | x |\n| A-3 | could | x |\n");
    for (const [source, importance] of [["A-1", "must"], ["A-2", "should"], ["A-3", "could"]]) {
      for (const risk of ["@risk-high", "@risk-medium", "@risk-low"]) {
        const got = rowOf({ file: "f", line: 1, title: "t", how: "", tags: [risk], notes: [{ type: "source", text: source }], unread: [] }, three).value;
        if (got !== VALUE[importance][risk]) cells.push(`${importance} with ${risk} gave ${got}`);
      }
    }
    log.check(`the generator's rule gives what that table gives in all nine cases, the ${9 - new Set(rows.map((row) => `${requirements.get(row.source)} ${row.tags.find((tag) => TAGS.get(tag) === "risk")}`)).size} that no test of the suite falls in among them${cells.length ? `. NOT: ${cells.join("; ")}` : ""}`, cells.length === 0);
    const titles = new Map(tableRows(section(inventory, "Titles")).map(([, where, title]) => [where.replace(/`/g, ""), title]));
    log.check("the title given for each test, at its place, is the title Playwright shows for the test at that line", pairs.every(({ row, test }) => titles.get(row.where) === test?.title) && titles.size === rows.length);

    // ------------------------------------------------------------ part 3
    log.part("PART 3. Finding the tests for a requirement (criterion 7)", "The table 'Find the tests for a requirement', against the sources Playwright reads from the tests.");
    const finder = tableRows(section(inventory, "Find the tests for a requirement"));
    let finderOk = finder.length === requirements.size && finder.length > 0;
    for (const [id, , , tests] of finder) {
      const mine = listed.filter((test) => test.notes.get("source")?.[0] === id).map((test) => test.notes.get("id")?.[0]).sort().join(", ");
      const shown = placed(tests).map((one) => one.id).sort().join(", ");
      log.out(`  ${id}: ${tests}`);
      if (shown !== mine || !requirements.has(id)) finderOk = false;
    }
    log.check(`criterion 7: each of the ${requirements.size} current requirements has a row, and the row lists exactly the tests whose source it is`, finderOk);
    const untested = finder.filter(([, , , tests]) => tests === "**none**").map(([id]) => id);
    log.check(`a requirement with no test is shown as having none: ${untested.join(", ") || "there is no such requirement"}`, untested.length > 0 && untested.every((id) => !rows.some((row) => row.source === id)) && inventory.includes(`With no test: **${untested.length}** (${untested.join(", ")})`));
    const places = finder.flatMap(([, , , tests]) => placed(tests));
    log.check(`criterion 7: beside each of the ${places.length} tests in those rows is its file and line, and it is the line where Playwright says that test is declared`, places.length === rows.length && places.every((one) => listed.some((test) => test.notes.get("id")?.[0] === one.id && `inventoried.spec.ts:${test.line}` === one.where)));

    // ------------------------------------------------------------ part 4
    log.part("PART 4. The duplicate the inventory found in the suite as it is (criterion 4)");
    const groups = section(inventory, "Possible duplicates").split("\n").filter((line) => line.startsWith("- ") || line.startsWith("  - "));
    log.out(...groups.map((line) => "  " + line));
    const samePurpose = new Map<string, string[]>();
    for (const test of listed) { const key = (test.notes.get("purpose")?.[0] ?? "").toLowerCase(); samePurpose.set(key, [...(samePurpose.get(key) ?? []), test.notes.get("id")?.[0] ?? "?"]); }
    const real = [...samePurpose.values()].filter((ids) => ids.length > 1);
    const overlap = section(inventory, "Possible overlap").split("\n").filter((line) => line.startsWith("- "));
    log.out("Possible overlap, a weaker sign: the same source and the same tags.", ...overlap.map((line) => "  " + line));
    const sameKind = new Map<string, string[]>();
    for (const test of listed) { const key = `${test.notes.get("source")?.[0]} ${test.tags.join(" ")}`; sameKind.set(key, [...(sameKind.get(key) ?? []), test.notes.get("id")?.[0] ?? "?"]); }
    const kinds = [...sameKind.values()].filter((ids) => ids.length > 1);
    log.check(`the tests Playwright reads with one source and one set of tags are ${kinds.map((ids) => ids.join(" and ")).join("; ")}, and the inventory reports those groups as possible overlap and no other`,
      kinds.length === overlap.length && kinds.length > 0 && kinds.every((ids) => overlap.some((line) => ids.every((id) => line.includes(`${id} (`)))));
    log.check(`criterion 4: the tests Playwright reads with one purpose are ${real.map((ids) => ids.join(" and ")).join("; ")}, and the inventory reports that group and no other`,
      real.length === 1 && groups.filter((line) => line.startsWith("- ")).length === 1 && real[0].every((id) => groups.some((line) => line.startsWith(`  - ${id} (`))) && first.text.includes(`POSSIBLE DUPLICATES ${real[0].join(" and ")}`));

    // ------------------------------------------------------------ part 5
    log.part("PART 5. What happens when the tests change", "Each trial copies inventoried.spec.ts to a file beside it, adds or changes one test in the copy, and runs the generator on the copy.",
      "The inventory is written to TEMP. Nothing is edited by hand.");
    const trial = (label: string, text: string, wantCode: number, wants: string[], criterion: string) => {
      const name = copy(text);
      const out = join(scratch, `trial-${number}.md`);
      log.out("", `-- ${label}`);
      const run = log.generate("--spec", name, "--out", out);
      rmSync(join(TESTS, name), { force: true });
      const said = wants.every((want) => run.text.includes(want.replace("SPEC", name)));
      log.check(criterion, text !== original && run.code === wantCode && said);
      return { run, out, name, written: existsSync(out) ? readFileSync(out, "utf8") : null };
    };
    const complete = extra("the number of customers on each plan comes back as data", [note("id", "DIR-T13"), note("purpose", NEW_PURPOSE), note("source", "DIR-09")]);
    const added = trial("A thirteenth test is added, with an identifier, a purpose and a source. Its source is DIR-09, the requirement that had no test.", original + complete, 0,
      ["13 tests.", "Incomplete: 0."], "criterion 6: the generator reads the added test and reports 13 tests, none incomplete");
    const addedRows = rowsOf(added.written ?? "");
    log.check("criterion 6: the new inventory has a row for DIR-T13 that the old one did not, with its purpose, its source and a value worked out for it",
      addedRows.length === rows.length + 1 && !rows.some((row) => row.id === "DIR-T13") && addedRows.some((row) => row.id === "DIR-T13" && row.purpose === NEW_PURPOSE && row.source === "DIR-09" && row.value === "low"));
    const addedListed = playwrightList(copy(original + complete));
    rmSync(join(TESTS, `inventoried.scratch-${number}.spec.ts`), { force: true });
    log.check("Playwright, asked to list that copy, lists thirteen tests too, the last with the identifier DIR-T13", addedListed.length === 13 && addedListed[12].notes.get("id")?.[0] === "DIR-T13");
    log.check("criterion 6: every other row is what it was", rows.every((row) => addedRows.some((now) => JSON.stringify(now) === JSON.stringify({ ...row, where: row.where.replace("inventoried.spec.ts", added.name) }))));
    log.check("criterion 7: DIR-09 now lists DIR-T13, where it listed none", /\| DIR-09 \| could \| .* \| DIR-T13 \(`[^`]+`\) \|/.test(added.written ?? "") && (added.written ?? "").includes("With no test: **0**"));

    trial("A test is added with no purpose.", original + extra("a test with no purpose", [note("id", "DIR-T13"), note("source", "DIR-09")]), 0,
      ["Incomplete: 1.", `INCOMPLETE DIR-T13 at SPEC:`, "it has no purpose"], "criterion 3: a test with no purpose is reported as incomplete, by its identifier and its place");
    trial("A test is added with no source requirement.", original + extra("a test with no source", [note("id", "DIR-T13"), note("purpose", NEW_PURPOSE)]), 0,
      ["Incomplete: 1.", `INCOMPLETE DIR-T13 at SPEC:`, "it has no source requirement"], "criterion 3: a test with no source is reported as incomplete");
    const bare = trial("A test is added with no identifier, no purpose and no source: only a title and tags.", original + extra("a test with nothing written about it", []), 0,
      ["Incomplete: 1.", "INCOMPLETE (no identifier, SPEC:", "it has no identifier; it has no purpose; it has no source requirement"], "criterion 3: a test with nothing written about it is reported, by its place, for all three");
    log.check("criterion 3: the inventory itself lists it under 'Incomplete', and shows it as not scored", (bare.written ?? "").includes("\n## Incomplete\n\n- **(no identifier, ") && /\| \*\*none\*\* \| \*\*none\*\* \| .* \| \*\*none\*\* \| not scored \|/.test(bare.written ?? ""));

    const shared = trial("A test is added with the identifier of another test, DIR-T02.", original + extra("a test with a borrowed identifier", [note("id", "DIR-T02"), note("purpose", NEW_PURPOSE), note("source", "DIR-09")]), 1,
      ["REJECTED: two tests have one identifier.", "  DIR-T02: SPEC:91", " AND SPEC:"], "two tests sharing an identifier are rejected, both are named by file and line, and the exit code is 1");
    log.check("when it rejects, the generator writes no inventory at all", shared.written === null);

    trial("A test is added whose purpose is that of DIR-T04, in other capitals, with commas added and without the full stop.",
      original + extra("a second look at storing a customer", [note("id", "DIR-T13"), note("purpose", "CATCHES the data interface storing a name, or a plan, other than the one it was sent"), note("source", "DIR-02")]), 0,
      ["Groups of possible duplicates: 2.", "POSSIBLE DUPLICATES DIR-T04 and DIR-T13"], "criterion 4: two tests with the same purpose, capitals and punctuation aside, are reported as possible duplicates");

    log.out("", "Purposes that say nothing:");
    trial("A test is added with a purpose of three words.", original + extra("a test with a short purpose", [note("id", "DIR-T13"), note("purpose", "Checks the stats."), note("source", "DIR-09")]), 0,
      ["Incomplete: 1.", "its purpose is 3 words long"], "a purpose of three words is reported as incomplete");
    trial("A test is added whose purpose is six letters, each a word.", original + extra("a test with an empty purpose", [note("id", "DIR-T13"), note("purpose", "a b c d e f"), note("source", "DIR-09")]), 0,
      ["Incomplete: 0."], "KNOWN LIMIT, shown and not hidden: a purpose of six words that say nothing is NOT reported. The rule counts words");
    trial("A test is added whose purpose is 'Show that' and then its own title.", original + extra("the number of customers on each plan comes back as data", [note("id", "DIR-T13"), note("purpose", "Show that the number of customers on each plan comes back as data."), note("source", "DIR-09")]), 0,
      ["Incomplete: 1.", "its purpose only repeats its title"], "a purpose that is 'Show that' and the title again is reported as incomplete");
    trial("A test is added whose purpose is its own title again.", original + extra("the number of customers on each plan comes back as data", [note("id", "DIR-T13"), note("purpose", "The number of customers on each plan comes back as data."), note("source", "DIR-09")]), 0,
      ["Incomplete: 1.", "its purpose only repeats its title"], "a purpose that only repeats the title is reported as incomplete");

    log.out("", "Sources that are not current requirements (stretch goal):");
    const withdrawn = trial("A test is added whose source is DIR-10, a requirement that was withdrawn.", original + extra("a test of a withdrawn requirement", [note("id", "DIR-T13"), note("purpose", "Show that a customer on plus can be put back on basic."), note("source", "DIR-10")]), 0,
      ["Incomplete: 1.", "its source, DIR-10, is a requirement that was withdrawn"], "stretch goal: a test whose source requirement was withdrawn is reported");
    log.check("stretch goal: the inventory lists it under 'Tests whose source is not a current requirement', with why the requirement was withdrawn, and does not score it", /## Tests whose source is not a current requirement\n\n- DIR-T13 \(`[^`]+`\): DIR-10, withdrawn\. \S/.test(withdrawn.written ?? "") && /\| DIR-T13 \| .* \| DIR-10 \| not scored \|/.test(withdrawn.written ?? ""));
    trial("A test is added whose source is DIR-99, which was never a requirement.", original + extra("a test of nothing", [note("id", "DIR-T13"), note("purpose", NEW_PURPOSE), note("source", "DIR-99")]), 0,
      ["its source, DIR-99, is not a requirement in the requirements document"], "a source that is not in the requirements document is reported");

    log.out("", "Things written where the generator cannot read them:");
    trial("The purpose of DIR-T01 is put in a variable, and the annotation names the variable.",
      original.replace(/\{ type: "purpose", description: "Catches the page leaving out[^"]*" \},/, `{ type: "purpose", description: PURPOSE_ONE },`).replace("type Customer =", `const PURPOSE_ONE = "Catches the page leaving out a customer that exists, or showing it with the wrong plan.";\n\ntype Customer =`), 0,
      ["INCOMPLETE DIR-T01", "its purpose is not written out as plain quoted text"], "a purpose that is not written out beside the test is reported, and not guessed");
    trial("The risk tag is taken off DIR-T01.", original.replace(`tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@fast"],`, `tag: ["@feature-list", "@read", "@layer-ui", "@fast"],`), 0,
      ["INCOMPLETE DIR-T01", "it has 0 risk tags, so it cannot be given a value"], "a test with no risk tag is reported, and not given a value");
    trial("A tag of DIR-T01 is misspelt: @fsat for @fast.", original.replace(`tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@fast"],`, `tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@fsat"],`), 0,
      ["INCOMPLETE DIR-T01", "it has a tag that is not in the tag scheme: @fsat"], "a tag that is not in the tag scheme is reported");

    // ------------------------------------------------------------ part 6
    log.part("PART 6. That the generator reads a harder file as Playwright does", "6a. A file written to be awkward to read as text, in ways the generator says it can read: groups inside groups with tags",
      "of their own, a tag in a group's title, single quotes, a title in back quotes, a test inside a comment, the word test( inside a string,",
      "regular expressions with braces and quotes in them, a division, a skipped test, a skipped group, a test with its details after a comment,",
      "and, inside tests, test.step and a conditional test.skip. The generator's reading is compared with Playwright's list.");
    const awkward = `import { expect, test } from "@playwright/test";

// test("a test inside a comment", { tag: "@fast" }, async () => {});
/* test("another inside a comment", async () => {}); */
const words = 'test("a test inside a string", async () => {})';
const shape = /[{"']+test\\(/;
const half = (words.length as number)! / 2; const more = [words].filter((one) => /it's {/.test(one));

test.describe("a group @ingroup", { tag: ["@grouped"] }, () => {
  test('first in the group', { tag: '@one', annotation: { type: 'id', description: 'AWK-1' } }, async () => {
    await test.step("a step, which is not a test", async () => {
      expect(words.length + shape.source.length + half + more.length).toBeGreaterThan(0);
    });
  });

  test.describe("an inner group", () => {
    test(\`second, with a title in back quotes\`, { tag: ["@two", "@three"] }, async ({ browserName }) => {
      test.skip(browserName === "webkit", "a condition, which is not a test");
      expect(\`\${[1, 2].map((n) => \`{\${n}}\`).join("")}\`.replace(/[{}]/g, "")).toBe("12");
    });
  });
});

test.describe.skip("a skipped group", () => {
  test("third, in a group that is skipped", /* a comment between the arguments */ { tag: "@four", annotation: [{ type: "id", description: "AWK-4" }] }, async () => {});
});

test.skip("a skipped test @inline", { annotation: [{ type: "id", description: "AWK-3" }, { type: "purpose", description: "Catches a skipped test being left out of the inventory altogether." }] }, async () => {});

test("a test with no details at all \\u00e9\\x41", async () => {
  expect(1 + 1).toBe(2);
});
`;
    const awkwardName = copy(awkward);
    const awkwardRun = log.generate("--spec", awkwardName, "--out", join(scratch, "awkward.md"));
    const theirs = playwrightList(awkwardName);
    rmSync(join(TESTS, awkwardName), { force: true });
    const awkwardText = existsSync(join(scratch, "awkward.md")) ? readFileSync(join(scratch, "awkward.md"), "utf8") : "";
    const ours = rowsOf(awkwardText);
    const ourTitles = new Map(tableRows(section(awkwardText, "Titles")).map(([, where, title]) => [where.replace(/`/g, ""), title]));
    log.out("Playwright lists:", ...theirs.map((test) => `  line ${String(test.line).padStart(2)}  ${test.title}   ${test.tags.join(" ")}`));
    log.check(`the generator finds the tests Playwright lists, and no test in a comment, a string or a step: ${ours.length} and ${theirs.length}`, awkwardRun.code === 0 && ours.length === theirs.length && theirs.length === 5);
    log.check("each is at the line Playwright gives, with the tags Playwright gives: a group's tag, a tag in a group's title and a tag in a test's title among them",
      theirs.every((test) => ours.some((row) => row.where === `${awkwardName}:${test.line}` && row.tags.filter((tag) => tag !== "**none**").join(" ") === test.tags.join(" "))) && theirs.some((test) => test.tags.includes("@ingroup")) && theirs.some((test) => test.tags.includes("@inline")));
    log.check("each, at its line, has the title Playwright shows, with the names of its groups before it and its escapes read", theirs.every((test) => ourTitles.get(`${awkwardName}:${test.line}`) === test.title) && theirs.some((test) => test.title.endsWith("\u00e9A")));
    log.check("each has the identifier Playwright reads for it, or none where Playwright reads none", theirs.every((test) => ours.some((row) => row.where === `${awkwardName}:${test.line}` && (test.notes.get("id")?.[0] ?? "**none**") === row.id)));
    log.check("the skipped test, and the test in the skipped group, are in the inventory and are each reported as not running", awkwardRun.text.includes("it is declared with test.skip") && /INCOMPLETE AWK-4 .*is declared with test\.describe\.skip, so it does not run/.test(awkwardRun.text));
    log.check("the generator did not ask for this file to be looked at: it read all of it", !awkwardRun.text.includes("LOOK AT"));

    log.out("", "6b. Ways of writing tests that the generator does NOT read. It must say so, and not pass over them in silence.",
      "Each file below is listed by Playwright and read by the generator. The two may differ. What matters is that the generator says where.");
    const unread = (label: string, body: string, wants: string[], criterion: string) => {
      const name = copy(`import { expect, test } from "@playwright/test";\n${body}\ntest("an ordinary test beside it", async () => { expect(1).toBe(1); });\n`);
      log.out("", `-- ${label}`);
      const run = log.generate("--spec", name, "--out", join(scratch, `unread-${number}.md`));
      const list = playwrightList(name);
      rmSync(join(TESTS, name), { force: true });
      const count = Number(/: (\d+) tests\./.exec(run.text)?.[1] ?? -1);
      log.out(`Playwright lists ${list.length} tests in this file. The generator found ${count}.`);
      log.check(criterion, list.length > 0 && wants.every((want) => run.text.includes(want)));
    };
    unread("Tests declared in a loop, each with a title worked out when the file runs.", "for (const plan of [\"basic\", \"plus\"]) test(`a customer on ${plan}`, async () => { expect(plan).toBeTruthy(); });",
      ["INCOMPLETE (no identifier", "its title is not written out as plain quoted text, so it may be more than one test when the file runs"], "a test whose title is worked out when the file runs is reported, with a warning that it may be more than one test");
    unread("`test` taken under another name.", "import { test as check } from \"@playwright/test\";\ncheck(\"a test declared under another name\", async () => { expect(1).toBe(1); });",
      ["LOOK AT", "it takes `test` under another name"], "a file that takes `test` under another name is reported as a file to look at");
    unread("`test.describe` given another name.", "const group = test.describe;\ngroup(\"a group under another name\", () => { test(\"inside it\", async () => { expect(1).toBe(1); }); });",
      ["LOOK AT", "it gives `test` or `test.describe` another name"], "a file that gives `test.describe` another name is reported as a file to look at");
    unread("A group whose body is one expression, with no braces.", "test.describe(\"a group with no braces\", { tag: \"@grouped\" }, () => test(\"inside it\", async () => { expect(1).toBe(1); }));",
      ["LOOK AT", "it has a group whose body is not written as `() => { ... }`"], "a group whose body has no braces is reported as a file to look at");
    unread("A test whose details are a variable.", "const DETAILS = { tag: \"@fast\" };\ntest(\"a test with details in a variable\", DETAILS, async () => { expect(1).toBe(1); });",
      ["its details are not written out as a plain object"], "a test whose details are a variable is reported as unreadable, and not as having none");
    unread("A group whose tags are a variable.", "const GROUP = [\"@grouped\"];\ntest.describe(\"a group with tags in a variable\", { tag: GROUP }, () => {\n  test(\"inside it\", async () => { expect(1).toBe(1); });\n});",
      ["a group it is in, at line", "could not be read: the tags are not written out as plain quoted text"], "a test in a group whose tags cannot be read is itself reported");
    const empty = copy("// a file with no test in it\nexport const nothing = 1;\n");
    log.out("", "-- A file in which there is no test.");
    const none = log.generate("--spec", empty, "--out", join(scratch, "empty.md"));
    rmSync(join(TESTS, empty), { force: true });
    log.check("a file in which no test is found is reported as a file to look at", none.text.includes("LOOK AT") && none.text.includes("no test was found in it"));

    // ------------------------------------------------------------ part 7
    log.part("PART 7. An inventory edited by hand, and one that is out of date");
    const edited = join(scratch, "edited.md");
    writeFileSync(edited, inventory.replace("| DIR-T03 | Catches the add form", "| DIR-T03 | Checks the add form"));
    log.out("A copy of the inventory with one purpose reworded by hand:");
    const hand = log.generate("--check", "--out", edited);
    log.check("an inventory edited by hand is reported as not what the test files give, and the exit code is 1", hand.code === 1 && hand.text.includes("NOT UP TO DATE") && readFileSync(edited, "utf8") !== inventory);
    log.check("with --check the generator did not put it right: the file is as it was left", readFileSync(edited, "utf8").includes("| DIR-T03 | Checks the add form"));
    const stale = copy(original + complete);
    log.out("", "The inventory of today's tests, checked against a copy of the test file with a thirteenth test added:");
    writeFileSync(join(scratch, "stale.md"), inventory);
    const late = log.generate("--check", "--spec", stale, "--out", join(scratch, "stale.md"));
    rmSync(join(TESTS, stale), { force: true });
    log.check("an inventory made before a test was added is reported as out of date", late.code === 1 && late.text.includes("NOT UP TO DATE"));

    // ------------------------------------------------------------ part 8
    log.part("PART 8. The whole folder, as it is: what an undocumented suite looks like",
      "The generator is pointed at every test file in participant/tests/playwright. The files of earlier quests were written before",
      "purposes and sources were, and are left as they were approved. Only some lines of what it printed are kept here.",
      "This inventory is written to TEMP and thrown away. The inventory that is handed in is of inventoried.spec.ts alone.");
    const everything = spawnSync(process.execPath, ["--no-warnings", "tools/inventory.ts", "--all", "--out", join(scratch, "all.md")], { cwd: TESTS, encoding: "utf8" });
    const lines = tidy(everything.stdout.trimEnd()).split("\n");
    const counted = lines.find((line) => line.startsWith("Incomplete: ")) ?? "";
    const incomplete = lines.filter((line) => line.startsWith("  INCOMPLETE "));
    log.out("$ node tools/inventory.ts --all --out TEMP/all.md", "-".repeat(78), lines[0], ...lines.filter((line) => line.startsWith("  LOOK AT")), counted, ...incomplete.slice(0, 3), `  ... and ${Math.max(0, incomplete.length - 3)} more lines beginning INCOMPLETE`, ...lines.filter((line) => !line.startsWith("  ") && line !== lines[0] && line !== counted), "-".repeat(78), `exit code: ${everything.status}`);
    const files = readdirSync(TESTS).filter((one) => one.endsWith(".spec.ts") && !one.includes(".scratch-"));
    const total = Number(/: (\d+) tests\./.exec(lines[0] ?? "")?.[1] ?? 0);
    log.check(`it reads the ${files.length} files in the folder whose names end in .spec.ts. It does not look in folders below, and does not ask any Playwright settings which files are tests`, (lines[0] ?? "").startsWith(`Read ${files.length} test files as text:`) && files.length >= 10);
    log.check(`by the generator's own count it finds ${total} tests: the ${rows.length} of inventoried.spec.ts, none reported, and ${incomplete.length} in the other files, each reported as incomplete. THE COUNT FOR THE OTHER FILES WAS NOT COMPARED WITH PLAYWRIGHT'S`,
      total === incomplete.length + rows.length && incomplete.length > 0 && !incomplete.some((line) => line.includes("inventoried.spec.ts")) && counted === `Incomplete: ${incomplete.length}.`);
    ended = true;
  } catch (error) {
    log.out("", `THE CHECK STOPPED: ${String(error instanceof Error ? error.message : error).split("\n")[0]}`);
  } finally {
    for (const name of readdirSync(TESTS).filter((one) => /^inventoried\.scratch-.*\.spec\.ts$/.test(one))) rmSync(join(TESTS, name), { force: true });
    rmSync(scratch, { recursive: true, force: true });
  }

  log.part("AT THE END");
  log.check("the check ran to its end", ended);
  log.check(`every one of the ${everySpecBefore.split("\n").length} test files in the folder, and the requirements, are byte for byte what they were at the start: the generator changed no test file`, allSpecs() === everySpecBefore && sha(readFileSync(SPEC)) === before.spec && sha(readFileSync(REQUIREMENTS)) === before.requirements);
  log.check("the inventory on disk is byte for byte what it was at the start, and no changed copy of the test file is left", sha(readFileSync(INVENTORY)) === before.inventory && !readdirSync(TESTS).some((one) => one.includes(".scratch-")));
  log.save(LOGFILE);
  return log.failed.length ? 1 : 0;
}

process.exit(main());

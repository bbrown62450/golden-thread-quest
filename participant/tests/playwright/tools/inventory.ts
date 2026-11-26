/*
 * The generator of the test inventory, for the playwright-test-inventory quest.
 *
 *   node tools/inventory.ts                       reads inventoried.spec.ts, writes participant/context/playwright/inventory.md
 *   node tools/inventory.ts --check               writes nothing. Exit 1 if the inventory on disk is not what would be written
 *   node tools/inventory.ts --spec A.spec.ts --spec B.spec.ts --out FILE.md   other test files, another place to write
 *   node tools/inventory.ts --all --out FILE.md   every *.spec.ts in this folder
 *
 * Node 22.18 or later. It needs nothing installed and contacts nothing.
 *
 * IT READS TEST FILES AS TEXT. It does not load them, does not run them and does not change them: it opens each test
 * file for reading and nothing else, and what it writes must be a file whose name ends in .md. Besides the test files
 * it reads the requirements document, and the tag vocabulary in support/tags.ts.
 *
 * WHAT IT CAN READ, AND WHAT IT DOES WHEN IT CANNOT. It has no TypeScript parser. It reads tests written the ordinary
 * way: `test("title", { details }, fn)` and `test.describe("group", { details }, () => { ... })`, with the title,
 * the tags and the annotations written out as plain quoted text. Anything else it does not guess at:
 *
 *   a title, a tag or an annotation that is a variable, or joined strings     the test is reported as incomplete
 *   a test with a title worked out when the file runs, as in a loop           one row, reported, though it may be many tests
 *   a test with a plain title declared in a loop                              NOT NOTICED: it is read as one test
 *   a group whose details or title it cannot read                             every test in the group is reported
 *   `test` under another name, a group whose body is not `() => { ... }`      the FILE is reported, under "Files to look at"
 *   a file in which it finds no test at all                                   the FILE is reported
 *
 * It can still be wrong without knowing it, for a file written unusually enough. tools/inventory-check.ts compares
 * its reading with Playwright's own list of the same file, which is the test of that.
 *
 * WHERE THE FACTS ABOUT A TEST ARE WRITTEN: beside the test, in the details Playwright itself takes.
 *
 *     test("the title", {
 *       tag: ["@feature-list", "@risk-medium", "@read", "@layer-ui", "@fast"],
 *       annotation: [
 *         { type: "id", description: "DIR-T01" },
 *         { type: "purpose", description: "Catches the page leaving out a customer that exists. It looks at one only." },
 *         { type: "source", description: "DIR-01" },
 *       ],
 *     }, async ({ page }) => { ... });
 *
 * THE VALUE SCORE IS NOT WRITTEN ANYWHERE. It is worked out, by the rule in VALUE_RULE below, from the importance of
 * the test's source requirement and the test's risk tag.
 *
 * WHAT IT REPORTS
 *   Incomplete            a test with no identifier, no purpose or no source; with two of one of them; with one it
 *                         cannot read; with a purpose of fewer than MIN_PURPOSE_WORDS words or one that only repeats
 *                         the title; with a source that is not a current requirement; with a tag that is not in the
 *                         tag scheme; or one that is skipped.
 *   Possible duplicates   two tests or more with the same purpose, capitals, spacing and punctuation aside.
 *   Possible overlap      two tests or more with the same source requirement and the same tags.
 *   Rejected              two tests with one identifier. Nothing is written, and the exit code is 1.
 *
 * The inventory holds no date and no time, its rows are in the order of their identifiers, and line ends are read as
 * one kind. So the same test files give the same inventory, byte for byte.
 *
 * Exit codes: 0 written (or, with --check, up to date). 1 rejected, or not up to date. 2 the command could not be read.
 */

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { TAGS } from "../support/tags.ts";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
export const DEFAULT_SPEC = "inventoried.spec.ts";
export const DEFAULT_REQUIREMENTS = join(PARTICIPANT, "context", "playwright", "directory-requirements.md");
export const DEFAULT_OUT = join(PARTICIPANT, "context", "playwright", "inventory.md");
export const MIN_PURPOSE_WORDS = 6;
const LEVELS = ["high", "medium", "low"] as const;
const START = { must: 0, should: 1, could: 2 } as const;
const DROP: Record<string, number> = { "@risk-high": 0, "@risk-medium": 1, "@risk-low": 2 };
export const VALUE_RULE = [
  "Start from the importance of the test's source requirement: must gives high, should gives medium, could gives low.",
  "Go down one level if the test's risk tag is `@risk-medium`, and two if it is `@risk-low`. No lower than low.",
  "A test with no current source requirement, or without exactly one risk tag, is **not scored**.",
  "So a value is never higher than the requirement's importance allows. It says which tests guard the rules that matter most against the worst faults. It does not say how good a test is.",
];

// ---------------------------------------------------------------- reading a test file as text

type Value = { kind: "string"; value: string } | { kind: "array"; items: Value[] } | { kind: "object"; entries: [string, Value][] } | { kind: "other" };
export type Found = { file: string; line: number; title: string; how: string; tags: string[]; notes: { type: string; text: string | null }[]; unread: string[] };

const isWord = (ch: string | undefined) => ch !== undefined && /[A-Za-z0-9_$]/.test(ch);

/** A reader over the text of one file. Every method takes a position and returns the position after what it read. */
class Reader {
  text: string;
  constructor(text: string) { this.text = text; }

  /** Past spaces, line ends and comments. */
  space(i: number): number {
    for (;;) {
      const ch = this.text[i];
      if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") i += 1;
      else if (this.text.startsWith("//", i)) { const end = this.text.indexOf("\n", i); i = end < 0 ? this.text.length : end; }
      else if (this.text.startsWith("/*", i)) { const end = this.text.indexOf("*/", i + 2); i = end < 0 ? this.text.length : end + 2; }
      else return i;
    }
  }

  /** A quoted string at i. Returns [its value, or null if it is a template with a ${value} in it; the position after it]. */
  string(i: number): [string | null, number] {
    const quote = this.text[i];
    let out = "", plain = true;
    i += 1;
    while (i < this.text.length && this.text[i] !== quote) {
      const ch = this.text[i];
      if (ch === "\\") {
        const rest = this.text.slice(i + 1, i + 12);
        const code = /^u\{([0-9a-fA-F]{1,6})\}/.exec(rest) ?? /^u([0-9a-fA-F]{4})/.exec(rest) ?? /^x([0-9a-fA-F]{2})/.exec(rest);
        if (code) { out += String.fromCodePoint(parseInt(code[1], 16)); i += 1 + code[0].length; continue; }
        out += ({ n: "\n", t: "\t", r: "\r", b: "\b", f: "\f", v: "\v", "0": "\0", "\n": "" } as Record<string, string>)[rest[0]] ?? rest[0];
        i += 2;
      } else if (quote === "`" && ch === "$" && this.text[i + 1] === "{") {
        plain = false;
        i = this.balanced(i + 1);
      } else { out += ch; i += 1; }
    }
    return [plain ? out : null, i + 1];
  }

  /** Whether a / at i begins a regular expression, and not a division: by what stands before it. */
  regexAt(i: number): boolean {
    let j = i - 1;
    while (j >= 0 && /\s/.test(this.text[j])) j -= 1;
    if (j < 0) return true;
    const ch = this.text[j];
    if (ch === "!" && (isWord(this.text[j - 1]) || this.text[j - 1] === ")" || this.text[j - 1] === "]")) return false;   // value! / 2
    if ("(,=:[!&|?{};>+-*%<~^".includes(ch)) return true;
    return /(?:^|[^A-Za-z0-9_$.])(?:return|typeof|case|in|of|void|delete|throw|new|else|do|await|yield)$/.test(this.text.slice(Math.max(0, j - 12), j + 1));
  }

  /** Past a regular expression that begins at i. */
  regex(i: number): number {
    i += 1;
    for (let inClass = false; i < this.text.length && this.text[i] !== "\n" && (inClass || this.text[i] !== "/"); i += 1) {
      if (this.text[i] === "\\") i += 1;
      else if (this.text[i] === "[") inClass = true;
      else if (this.text[i] === "]") inClass = false;
    }
    return i + 1;
  }

  /** If a string or a regular expression begins at i, the position after it. Otherwise -1. */
  quoted(i: number): number {
    const ch = this.text[i];
    if (ch === '"' || ch === "'" || ch === "`") return this.string(i)[1];
    if (ch === "/" && this.regexAt(i)) return this.regex(i);
    return -1;
  }

  /** From an opening bracket at i to just past the bracket that closes it. */
  balanced(i: number): number {
    const close = ({ "(": ")", "[": "]", "{": "}" } as Record<string, string>)[this.text[i]];
    i += 1;
    while (i < this.text.length) {
      i = this.space(i);
      const ch = this.text[i], after = this.quoted(i);
      if (after >= 0) i = after;
      else if (ch === close) return i + 1;
      else if (ch === "(" || ch === "[" || ch === "{") i = this.balanced(i);
      else i += 1;
    }
    return i;
  }

  /** Past one expression that is not plain text: to the comma or closing bracket that ends it. */
  expression(i: number): number {
    while (i < this.text.length) {
      i = this.space(i);
      const ch = this.text[i], after = this.quoted(i);
      if (after >= 0) i = after;
      else if (ch === "," || ch === ")" || ch === "]" || ch === "}" || ch === undefined) return i;
      else if (ch === "(" || ch === "[" || ch === "{") i = this.balanced(i);
      else i += 1;
    }
    return i;
  }

  /** One value written out in the file: a quoted string, a list, or an object. Anything else is "other". */
  value(i: number): [Value, number] {
    i = this.space(i);
    const ch = this.text[i];
    if (ch === '"' || ch === "'" || ch === "`") {
      const [value, after] = this.string(i);
      const end = this.space(after);
      if (value === null || !",)]}".includes(this.text[end] ?? ",")) return [{ kind: "other" }, this.expression(after)];   // a string with more after it, such as "a" + b
      return [{ kind: "string", value }, after];
    }
    if (ch === "[") {
      const start = i, items: Value[] = [];
      i = this.space(i + 1);
      while (i < this.text.length && this.text[i] !== "]") {
        const [item, after] = this.value(i);
        items.push(item);
        i = this.space(after);
        if (this.text[i] === ",") i = this.space(i + 1);
        else if (this.text[i] !== "]") return [{ kind: "other" }, this.balanced(start)];
      }
      return [{ kind: "array", items }, i + 1];
    }
    if (ch === "{") {
      const start = i, entries: [string, Value][] = [];
      i = this.space(i + 1);
      while (i < this.text.length && this.text[i] !== "}") {
        let key: string | null;
        if (this.text[i] === '"' || this.text[i] === "'") [key, i] = this.string(i);
        else { const word = /^[A-Za-z_$][A-Za-z0-9_$]*/.exec(this.text.slice(i, i + 80)); key = word ? word[0] : null; i += word ? word[0].length : 0; }
        i = this.space(i);
        if (key === null || this.text[i] !== ":") return [{ kind: "other" }, this.balanced(start)];   // a spread, a computed key, a shorthand
        const [item, after] = this.value(i + 1);
        entries.push([key, item]);
        i = this.space(after);
        if (this.text[i] === ",") i = this.space(i + 1);
        else if (this.text[i] !== "}") return [{ kind: "other" }, this.balanced(start)];
      }
      return [{ kind: "object", entries }, i + 1];
    }
    return [{ kind: "other" }, this.expression(i)];
  }
}

const strings = (value: Value | undefined): string[] | null => {
  if (!value) return [];
  if (value.kind === "string") return [value.value];
  if (value.kind === "array" && value.items.every((item) => item.kind === "string")) return value.items.map((item) => (item as { value: string }).value);
  return null;
};

/** What the details object of a test or a group says: its tags, its annotations, and what in it could not be read. */
function details(value: Value | undefined): { tags: string[]; notes: Found["notes"]; unread: string[] } {
  const out = { tags: [] as string[], notes: [] as Found["notes"], unread: [] as string[] };
  if (!value) return out;
  if (value.kind !== "object") { out.unread.push("its details are not written out as a plain object"); return out; }
  for (const [key, item] of value.entries) {
    if (key === "tag") {
      const tags = strings(item);
      if (tags === null) out.unread.push("its tags are not written out as plain quoted text");
      else out.tags.push(...tags);
    }
    if (key === "annotation") {
      const list = item.kind === "array" ? item.items : item.kind === "object" ? [item] : null;
      if (list === null) { out.unread.push("its annotations are not written out as a list"); continue; }
      for (const note of list) {
        const fields = note.kind === "object" ? new Map(note.entries) : null;
        const type = fields?.get("type"), text = fields?.get("description");
        if (!fields || type?.kind !== "string") out.unread.push("one of its annotations has no type written as plain quoted text");
        else out.notes.push({ type: type.value, text: text?.kind === "string" ? text.value : null });
      }
    }
  }
  return out;
}

const DECLARES = new Set(["", "only", "skip", "fixme", "fail"]);
const titleTags = (title: string) => title.match(/@[A-Za-z0-9_-]+/g) ?? [];

/** Every test declared in the text of one file, in the order it is written, and what about the file needs a person to look. */
export function readTests(file: string, text: string): { tests: Found[]; look: string[] } {
  const reader = new Reader(text);
  const tests: Found[] = [];
  const look: string[] = [];
  const groups: { tags: string[]; title: string; unread: string[]; closes: number }[] = [];
  let depth = 0, i = 0;
  const lineOf = (at: number) => text.slice(0, at).split("\n").length;

  // Ways of declaring tests that this reader does not follow. It says so for the file, and does not guess.
  const outside = text.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "");
  for (const [pattern, what] of [
    // `import { test as base }` followed by `const test = base.extend(...)` ends with the name `test`, which is read.
    [/\b(?:test|it)\s+as\s+[A-Za-z_$](?![\s\S]*\b(?:const|let|var)\s+test\s*=)/, "it takes `test` under another name (`test as ...`), and does not then make its own `test`"],
    [/=\s*(?:test|it)\s*(?:\.\s*describe\b[.\w]*)?\s*[;,\n)]/, "it gives `test` or `test.describe` another name"],
    [/\b(?:const|let|var)\s+(?!test\b|it\b)[A-Za-z_$][\w$]*\s*(?::[^=]+)?=\s*[\w$.]+\.extend\s*[<(]/, "it makes a test function with `.extend` under a name that is not `test`"],
    [/\b(?:test|it)\s*[\r\n]+\s*\./, "it writes `test` and what follows it on separate lines"],
  ] as [RegExp, string][]) if (pattern.test(outside)) look.push(what);

  while (i < text.length) {
    i = reader.space(i);
    const ch = text[i];
    if (ch === undefined) break;
    const past = reader.quoted(i);
    if (past >= 0) { i = past; continue; }
    if (ch === "{") { depth += 1; i += 1; continue; }
    if (ch === "}") {
      depth -= 1; i += 1;
      while (groups.length && groups[groups.length - 1].closes === depth) groups.pop();
      continue;
    }
    const called = !isWord(text[i - 1]) && text[i - 1] !== "." ? /^(?:test|it)((?:\.[A-Za-z]+)*)\s*\(/.exec(text.slice(i, i + 60)) : null;
    if (!called) { i += isWord(ch) ? (/^[A-Za-z0-9_$]+/.exec(text.slice(i, i + 200)) ?? [ch])[0].length : 1; continue; }
    const at = i, how = called[1].slice(1);
    i += called[0].length;
    const isGroup = how.split(".")[0] === "describe" && !how.includes("configure");
    if (!isGroup && !DECLARES.has(how)) continue;                       // test.step, test.use, test.beforeEach and the like
    const [first, afterFirst] = reader.value(i);
    if (first.kind !== "string" && how !== "" && !isGroup) continue;    // test.skip(condition, "why") inside a test: not a declaration
    let next = reader.space(afterFirst);
    if (text[next] !== ",") { i = afterFirst; continue; }               // one argument only: not a declaration
    // The second argument is the details if a third follows it, or if it is written as an object.
    const second = reader.space(next + 1);
    const [maybe, afterMaybe] = reader.value(second);
    const isDetails = maybe.kind === "object" || maybe.kind === "array" || maybe.kind === "string" || (text[second] !== "(" && !/^(?:async\b|function\b)/.test(text.slice(second, second + 9)) && text[reader.space(afterMaybe)] === ",");
    const read = details(isDetails ? maybe : undefined);
    const title = first.kind === "string" ? first.value : null;
    next = isDetails ? reader.space(afterMaybe) : next;
    if (isGroup) {
      const unread = [...read.unread.map((one) => one.replace(/^its /, "the ")), ...(title === null ? ["the title is not written out as plain quoted text"] : [])];
      const body = /^,\s*(?:async\s*)?(?:\(\s*\)\s*=>|function\s*\w*\s*\(\s*\))\s*\{/.exec(text.slice(next, next + 80));
      if (!body) {
        look.push(`at line ${lineOf(at)} it has a group whose body is not written as \`() => { ... }\`, so the tests in it may be read without the group's title and tags`);
        i = next;
        continue;
      }
      i = next + body[0].length;
      groups.push({ tags: [...read.tags, ...titleTags(title ?? "")], title: title ?? "(group title not readable)", closes: depth,
                    unread: [...unread.map((one) => `a group it is in, at line ${lineOf(at)}, could not be read: ${one}`),
                             ...(/\.(skip|fixme)\b/.test(how) ? [`a group it is in, at line ${lineOf(at)}, is declared with test.${how}, so it does not run`] : [])] });
      depth += 1;
      continue;
    }
    i = isDetails ? afterMaybe : next + 1;
    if (title === null) read.unread.push("its title is not written out as plain quoted text, so it may be more than one test when the file runs");
    tests.push({ file, line: lineOf(at), title: [...groups.map((group) => group.title), title ?? "(title not readable)"].join(" > "), how,
                 tags: [...new Set([...groups.flatMap((group) => group.tags), ...read.tags, ...titleTags(title ?? "")])], notes: read.notes,
                 unread: [...read.unread, ...groups.flatMap((group) => group.unread)] });
  }
  if (depth !== 0 || groups.length) look.push("its braces did not pair up as this reader counted them, so a group may have been read as longer or shorter than it is");
  if (!tests.length) look.push("no test was found in it");
  return { tests, look };
}

// ---------------------------------------------------------------- the requirements

export type Requirements = { current: Map<string, { importance: keyof typeof START; says: string }>; withdrawn: Map<string, string> };

export function readRequirements(text: string): Requirements {
  const out: Requirements = { current: new Map(), withdrawn: new Map() };
  for (const line of text.split("\n")) {
    const cells = /^\|(.+)\|\s*$/.exec(line)?.[1].split("|").map((cell) => cell.trim()) ?? [];
    if (!/^[A-Z]+-\d+$/.test(cells[0] ?? "")) continue;
    const importance = (cells[1] ?? "").toLowerCase();
    if (cells.length >= 3 && importance in START) out.current.set(cells[0], { importance: importance as keyof typeof START, says: cells.slice(2).join(" | ") });
    else out.withdrawn.set(cells[0], cells.slice(1).join(" | "));
  }
  return out;
}

// ---------------------------------------------------------------- one row for each test

export type Row = { id: string | null; purpose: string | null; source: string | null; value: string; tags: string[]; where: string; title: string; how: string; problems: string[] };

/** Two texts are the same if they differ only in capitals, spacing and punctuation. Letters of every alphabet count. */
const same = (text: string) => text.normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();

export function rowOf(test: Found, requirements: Requirements): Row {
  const problems = [...test.unread];
  const one = (type: string, what: string): string | null => {
    const mine = test.notes.filter((note) => note.type === type);
    if (mine.length === 0) { problems.push(`it has no ${what}`); return null; }
    if (mine.length > 1) { problems.push(`it has ${mine.length} annotations of the type "${type}", and one is wanted`); return null; }
    const text = mine[0].text;
    if (text === null) { problems.push(`its ${what} is not written out as plain quoted text`); return null; }
    if (!text.trim()) { problems.push(`its ${what} is empty`); return null; }
    return text.trim().replace(/\s+/g, " ");
  };
  const id = one("id", "identifier");
  const purpose = one("purpose", "purpose");
  const source = one("source", "source requirement");
  if (id !== null && !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(id)) problems.push("its identifier has a space or another character an identifier cannot have");
  if (purpose !== null) {
    const words = same(purpose).split(" ").filter(Boolean).length;
    if (words < MIN_PURPOSE_WORDS) problems.push(`its purpose is ${words} word${words === 1 ? "" : "s"} long, and fewer than ${MIN_PURPOSE_WORDS} cannot say what a test is for`);
    const title = same(test.title.split(" > ").pop() ?? "");
    if (same(purpose) === title || (title.length > 0 && same(purpose).replace(/^(?:show|shows|check|checks|test|tests|verify|verifies) that /, "") === title)) problems.push("its purpose only repeats its title");
  }
  let value = "not scored";
  const risks = test.tags.filter((tag) => TAGS.get(tag) === "risk");
  const strange = test.tags.filter((tag) => !TAGS.has(tag));
  if (strange.length) problems.push(`it has ${strange.length === 1 ? "a tag that is" : "tags that are"} not in the tag scheme: ${strange.join(" ")}`);
  if (source !== null) {
    const requirement = requirements.current.get(source);
    if (requirements.withdrawn.has(source)) problems.push(`its source, ${source}, is a requirement that was withdrawn`);
    else if (!requirement) problems.push(`its source, ${source}, is not a requirement in the requirements document`);
    else if (risks.length === 1 && risks[0] in DROP) value = LEVELS[Math.min(2, START[requirement.importance] + DROP[risks[0]])];
  }
  if (risks.length !== 1) problems.push(`it has ${risks.length} risk tags, so it cannot be given a value`);
  if (test.how) problems.push(`it is declared with test.${test.how}, so it does not run as an ordinary test`);
  return { id, purpose, source, value, tags: test.tags, where: `${test.file}:${test.line}`, title: test.title, how: test.how, problems };
}

/** Order with numbers read as numbers, so that T2 comes before T10. It does not depend on the computer's language settings. */
function natural(a: string, b: string): number {
  const parts = (text: string) => text.match(/\d+|\D+/g) ?? [];
  const x = parts(a), y = parts(b);
  for (let k = 0; k < Math.min(x.length, y.length); k += 1) {
    const both = /^\d/.test(x[k]) && /^\d/.test(y[k]);
    const order = both ? Number(x[k]) - Number(y[k]) || x[k].length - y[k].length : x[k] < y[k] ? -1 : x[k] > y[k] ? 1 : 0;
    if (order) return order;
  }
  return x.length - y.length;
}
const byId = (a: Row, b: Row) => (a.id === null ? 1 : 0) - (b.id === null ? 1 : 0) || natural(a.id ?? a.where, b.id ?? b.where) || natural(a.where, b.where);
const cell = (text: string) => text.replace(/\|/g, "\\|").replace(/\s+/g, " ");
const name = (row: Row) => row.id ?? `(no identifier, ${row.where})`;

export type Inventory = { rows: Row[]; sharedIds: Map<string, Row[]>; duplicates: [string, Row[]][]; overlaps: Row[][]; look: [string, string][]; text: string };

export function build(given: { name: string; text: string }[], requirementsName: string, requirementsGiven: string): Inventory {
  const files = given.map((file) => ({ name: file.name, text: file.text.replace(/\r\n?/g, "\n") })).sort((a, b) => natural(a.name, b.name));
  const requirementsText = requirementsGiven.replace(/\r\n?/g, "\n");
  const requirements = readRequirements(requirementsText);
  const read = files.map((file) => ({ file, ...readTests(file.name, file.text) }));
  const look = read.flatMap(({ file, look: mine }) => mine.map((what) => [file.name, what] as [string, string]));
  const rows = read.flatMap(({ tests }) => tests).map((test) => rowOf(test, requirements)).sort(byId);
  const group = (key: (row: Row) => string | null) => {
    const groups = new Map<string, Row[]>();
    for (const row of rows) { const k = key(row); if (k !== null && k !== "") groups.set(k, [...(groups.get(k) ?? []), row]); }
    return new Map([...groups].filter(([, mine]) => mine.length > 1));
  };
  const sharedIds = group((row) => row.id);
  const duplicates = [...group((row) => (row.purpose === null ? null : same(row.purpose)))].map(([, mine]) => [mine[0].purpose!, mine] as [string, Row[]]);
  const overlaps = [...group((row) => (row.source === null || !row.tags.length ? null : `${row.source} ${[...row.tags].sort().join(" ")}`)).values()];
  const incomplete = rows.filter((row) => row.problems.length);
  const sha = (text: string) => createHash("sha256").update(text).digest("hex").slice(0, 16);
  const untested = [...requirements.current].filter(([id]) => !rows.some((row) => row.source === id)).map(([id]) => id);
  const stale = rows.filter((row) => row.source !== null && !requirements.current.has(row.source));
  const place = (row: Row) => `${name(row)} (\`${row.where}\`)`;

  const out = ["# Test inventory", "",
    "**Generated. Do not edit this file.** Change the test, in its file, and run `node tools/inventory.ts` in `participant/tests/playwright` again.",
    "An identifier, a purpose and a source are written beside each test, in its `annotation` list. The value is worked out by the rule below.", "",
    "Generated by `participant/tests/playwright/tools/inventory.ts`, by reading these files as text. No test was run. The test files are in `participant/tests/playwright/`.", "",
    "| Read | sha256, first 16 characters |", "|---|---|",
    ...files.map((file) => `| \`${file.name}\` | \`${sha(file.text)}\` |`), `| \`${requirementsName}\` | \`${sha(requirementsText)}\` |`, "",
    "## Summary", "",
    `- Tests: **${rows.length}**, in ${files.length} file${files.length === 1 ? "" : "s"}.`,
    `- Incomplete: **${incomplete.length}**.`,
    `- Groups of possible duplicates: **${duplicates.length}**. Groups of possible overlap: **${overlaps.length}**.`,
    `- Current requirements: ${requirements.current.size}. With no test: **${untested.length}**${untested.length ? ` (${untested.join(", ")})` : ""}.`,
    `- Tests whose source is not a current requirement: **${stale.length}**.`,
    `- Files to look at, because the generator may not have read them fully: **${new Set(look.map(([file]) => file)).size}**.`, "",
    "## Find the tests for a requirement", "",
    "A test listed against a requirement serves it. It may not cover all of it: its purpose, in the next table, says what it catches and what it does not look at.", "",
    "| Requirement | Importance | What it says | Tests, and where each is |", "|---|---|---|---|",
    ...[...requirements.current].sort(([a], [b]) => natural(a, b)).map(([id, requirement]) => {
      const mine = rows.filter((row) => row.source === id).map(place);
      return `| ${id} | ${requirement.importance} | ${cell(requirement.says)} | ${mine.length ? mine.join(", ") : "**none**"} |`;
    }), "",
    "## Every test", "",
    "| ID | Purpose | Tags | Source | Value | Where |", "|---|---|---|---|---|---|",
    ...rows.map((row) => `| ${row.id ?? "**none**"} | ${row.purpose === null ? "**none**" : cell(row.purpose)} | ${row.tags.length ? cell(row.tags.join(" ")) : "**none**"} | ${row.source ?? "**none**"} | ${row.value} | \`${row.where}\` |`), "",
    "## Titles", "",
    "| ID | Where | The test's title, as Playwright shows it |", "|---|---|---|",
    ...rows.map((row) => `| ${row.id ?? "**none**"} | \`${row.where}\` | ${cell(row.title)} |`), "",
    "## Value", "",
    ...VALUE_RULE.map((line, index) => `${index + 1}. ${line}`), "",
    ...[...LEVELS, "not scored"].map((level) => { const mine = rows.filter((row) => row.value === level).map(name); return `- **${level}** (${mine.length}): ${mine.join(", ") || "none"}`; }), "",
    "## Incomplete", "",
    ...(incomplete.length ? incomplete.flatMap((row) => [`- **${name(row)}**, \`${row.where}\`, "${cell(row.title)}":`, ...row.problems.map((problem) => `  - ${problem}`)]) : ["None."]), "",
    "## Possible duplicates", "",
    "Tests with the same purpose, capitals and punctuation aside. The generator cannot tell whether they check the same thing. A person looks.", "",
    ...(duplicates.length ? duplicates.flatMap(([purpose, mine]) => [`- "${cell(purpose)}"`, ...mine.map((row) => `  - ${place(row)}, tags ${row.tags.join(" ") || "none"}`)]) : ["None."]), "",
    "## Possible overlap", "",
    "Tests with the same source requirement and the same tags. That is a weaker sign than one purpose: two such tests often check different things. Reworded purposes do not hide these.", "",
    ...(overlaps.length ? overlaps.map((mine) => `- ${mine[0].source}, ${[...mine[0].tags].sort().join(" ")}: ${mine.map(place).join(", ")}`) : ["None."]), "",
    "## Tests whose source is not a current requirement", "",
    ...(stale.length ? stale.map((row) => `- ${place(row)}: ${row.source}${requirements.withdrawn.has(row.source!) ? `, withdrawn. ${cell(requirements.withdrawn.get(row.source!)!)}` : ", which is not in the requirements document"}`) : ["None."]), "",
    "## Files to look at", "",
    "The generator reads files as text, and reads tests written the ordinary way. Where a file does something else, it says so here and does not guess. The tests of such a file may be missing from this inventory, or be without their group's title and tags.", "",
    ...(look.length ? look.map(([file, what]) => `- \`${file}\`: ${what}`) : ["None."]), ""];
  return { rows, sharedIds, duplicates, overlaps, look, text: out.join("\n") };
}

// ---------------------------------------------------------------- the command

export function main(argv: string[]): number {
  const specs: string[] = [];
  let out = DEFAULT_OUT, requirementsPath = DEFAULT_REQUIREMENTS, check = false, all = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i], next = argv[i + 1];
    if (arg === "--check") check = true;
    else if (arg === "--all") all = true;
    else if (arg === "--spec" && next) { specs.push(next); i += 1; }
    else if (arg === "--out" && next) { out = resolve(next); i += 1; }
    else if (arg === "--requirements" && next) { requirementsPath = resolve(next); i += 1; }
    else { console.log(`Not understood: ${arg}. See the top of tools/inventory.ts.`); return 2; }
  }
  if (!out.endsWith(".md")) { console.log("The inventory is written to a file whose name ends in .md, and to no other, so that it cannot be written over a test."); return 2; }
  const names = all ? readdirSync(TESTS).filter((one) => one.endsWith(".spec.ts") && !one.includes(".scratch-")).sort() : specs.length ? specs : [DEFAULT_SPEC];
  for (const one of names) {
    if (basename(one) !== one || !one.endsWith(".spec.ts") || !existsSync(join(TESTS, one))) { console.log(`There is no test file ${one} in participant/tests/playwright.`); return 2; }
  }
  if (!existsSync(requirementsPath)) { console.log("There is no requirements document at the path given."); return 2; }
  const files = names.map((one) => ({ name: one, text: readFileSync(join(TESTS, one), "utf8") }));
  const inventory = build(files, relative(REPO, requirementsPath).split("\\").join("/"), readFileSync(requirementsPath, "utf8"));
  const shown = relative(REPO, out).startsWith("..") ? basename(out) : relative(REPO, out).split("\\").join("/");

  if (inventory.sharedIds.size) {
    console.log("REJECTED: two tests have one identifier. An identifier names one test. Nothing was written.");
    for (const [id, mine] of inventory.sharedIds) console.log(`  ${id}: ${mine.map((row) => `${row.where} "${row.title}"`).join(" AND ")}`);
    return 1;
  }
  const incomplete = inventory.rows.filter((row) => row.problems.length);
  console.log(`Read ${files.length} test file${files.length === 1 ? "" : "s"} as text: ${inventory.rows.length} tests.`);
  for (const [file, what] of inventory.look) console.log(`  LOOK AT ${file}: ${what}.`);
  console.log(`Incomplete: ${incomplete.length}.`);
  for (const row of incomplete) console.log(`  INCOMPLETE ${name(row)} at ${row.where}, "${row.title}": ${row.problems.join("; ")}.`);
  console.log(`Groups of possible duplicates: ${inventory.duplicates.length}.`);
  for (const [purpose, mine] of inventory.duplicates) console.log(`  POSSIBLE DUPLICATES ${mine.map(name).join(" and ")}: the purpose of each is "${purpose}"`);
  console.log(`Groups of possible overlap: ${inventory.overlaps.length}.`);
  for (const mine of inventory.overlaps) console.log(`  POSSIBLE OVERLAP ${mine.map(name).join(" and ")}: each has the source ${mine[0].source} and the same tags`);
  if (check) {
    const onDisk = existsSync(out) ? readFileSync(out, "utf8").replace(/\r\n?/g, "\n") : null;
    const ok = onDisk === inventory.text;
    console.log(ok ? `UP TO DATE: ${shown} is what the test files give.` : `NOT UP TO DATE: ${shown} ${onDisk === null ? "is not there" : "is not what the files give. It was edited by hand, or a test file or the requirements changed since it was generated"}. Nothing was written.`);
    return ok ? 0 : 1;
  }
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, inventory.text);
  console.log(`Wrote ${shown}: ${inventory.text.split("\n").length - 1} lines, sha256 ${createHash("sha256").update(inventory.text).digest("hex").slice(0, 16)}.`);
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exit(main(process.argv.slice(2)));

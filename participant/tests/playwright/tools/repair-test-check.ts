/*
 * The check for the playwright-repair-test quest.
 *
 *   node tools/repair-test-check.ts --write
 *       Writes the two documents that are worked out from the files and are never typed by hand:
 *         repair.diff                 in the attempt folder: the test before the repair against the test after it,
 *                                     one hunk for each changed line, each labelled with the line of the maintenance
 *                                     report that called for it;
 *         assertion-comparison.md     in participant/context/playwright: every assertion before and after.
 *
 *   node tools/repair-test-check.ts
 *       Writes logs/weakening-check.txt and logs/mutation-run.txt in the attempt folder.
 *
 * Run it from participant/tests/playwright, with Node 22.18 or later. Run --write first: the plain run fails if the two
 * documents are not what --write produces. It needs the system's patch program. It starts the made-up checkout on this
 * computer, on 127.0.0.1, and stops it. It contacts nothing else.
 *
 * THE FILES IT READS. None of them is written to by this program.
 *   needs-maintenance.spec.ts                the test BEFORE the repair
 *   needs-maintenance.repaired.spec.ts       the test AFTER the repair
 *   participant/context/playwright/maintenance-report.md    the plan. Its part 4 is read for the six changes
 *   demo-app/checkout-server.corrected.mjs   the corrected application
 *   demo-app/checkout-server.mjs             the redesigned application in use, uncorrected
 *   demo-app/checkout-server.before.mjs      the application before the redesign
 *   repair.config.ts, maintenance.config.ts  the settings the test runs under now, and ran under before
 * Every weakened test and every broken application below is a COPY in a scratch folder, deleted at the end.
 *
 * THE WEAKENING CHECK. It compares two versions of a test and reports what was lost. It has two layers.
 *
 *   LAYER 1 reads only the two test files, as text, a line at a time. Comments, and the insides of quotes and
 *   template strings, are set aside first. It finds each expect() that opens and closes on one line, pairs those of
 *   the two files, and reports as WEAKENED:
 *     A1   an assertion with no counterpart after the change, or one inside a comment;
 *     A2   a different matcher (toHaveText became toContainText, toBe, toBeVisible, anything else), or an expect()
 *          that does not close on its own line and so cannot be read;
 *     A3   an expected value that is not a plain piece of text in quotes (a pattern, a variable, a list), an option
 *          added to the matcher, an expected value that lost a character it had, or one whose numbers differ;
 *     A4   a modifier between expect() and the matcher (not, soft, poll, resolves);
 *     A5   an assertion that is not "await expect(...).matcher(...);" on its own: the await gone, something before
 *          it on the line (if, a condition), or something after it (.catch, || true);
 *     A6   an assertion that sits deeper inside braces than it did (inside an if, a try, a loop, a callback);
 *     A7   an assertion that no longer looks at the page (its subject does not begin "page."), or whose subject now
 *          does something besides finding an element (an await, a function, an assignment);
 *     A8   a statement added or removed, or a line that held one statement and now holds more;
 *     A9   more than before of anything that can switch a test off, stop it early, replace what the application
 *          sends, or let it try again: the words skip, fixme, fail, only, return, throw, exit, route, fulfill,
 *          evaluate, setContent, addInitScript, addScriptTag, retries, a time limit, a try, a condition, a loop, a
 *          function, or a goto to anywhere but an address beginning "/";
 *     A10  the word expect used other than as a call more or fewer times than before (imported under another name,
 *          or defined again).
 *   Layer 1 also lists as TO BE ACCOUNTED FOR every change it cannot judge by itself: a subject that changed, an
 *   expected value that gained characters, a statement changed in place, a comment changed.
 *
 *   LAYER 2 reads the maintenance report. Every changed line must be a line the report lists, and must read exactly
 *   as the report's "Change to" says. A change Layer 1 left to be accounted for is settled here and only here.
 *
 *   A version is SOUND only if Layer 1 reports nothing weakened and Layer 2 accounts for every change.
 *
 * WHAT THE WEAKENING CHECK CANNOT SEE
 *   LAYER 1 IS A LIST OF KNOWN TRICKS, AND CAN BE BEATEN BY ONE THAT IS NOT ON IT. As first built it was given to an
 *   independent reader, who wrote eight weakened tests and predicted it would report none. It reported none. It was
 *   changed and now reports those eight (part 6B of the log). Known to remain: a regular expression between slashes
 *   with a quote in it throws the reading of that line off; "page" or "test" given another meaning (in the test's
 *   own parameter list, say) is not noticed; an assertion that does not fit on one line is reported as unreadable
 *   and not read. What holds the repair is Layer 2: with every line fixed to the report, there is no room for a
 *   trick. Layer 1 alone should not be trusted where there is no written plan to hold a change to.
 *   BOTH LAYERS read the test file and the report, and nothing else. Neither can see a weakening made anywhere
 *   else: in the settings file, in a file the test imports or the packages it resolves to, in the application's own
 *   markup, in environment variables such as the port, or in the command that runs the test. Layer 2 trusts the
 *   report: had the report proposed a weak change, Layer 2 would accept it.
 *   THEY READ TEXT, NOT MEANING. A subject that changed is "to be accounted for". Whether the new one finds the right
 *   element is something only running the test can show. That is what the mutation run is for.
 *
 * THE MUTATION RUN. The repaired test is run against the corrected application, where it must pass, and against
 * copies of that application with the tax rule broken in three different ways, where it must fail. Each copy is made
 * by changing one line of the source. The amounts each copy then sends are read back over HTTP and recorded, so the
 * record shows the figures a customer would be shown, and not only the line that was changed.
 *   The three ways were picked by the author, who knew what each would do. An independent reader then proposed ways
 *   of breaking the same rule that the test cannot catch, because the application has one basket and one discount
 *   and those faults give the right figures for it. Five are tried in part 6 of the log, and all five pass, before
 *   the repair and after it. So: the repaired test is shown to be no weaker than the test it replaces. It is NOT
 *   shown to guard the rule for any basket but the one.
 */

import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const CLI = join(PARTICIPANT, "node_modules", "@playwright", "test", "cli.js");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-repair-test", "playwright-attempt-006");
const LOGS = join(ATTEMPT, "logs");
const BEFORE_SPEC = join(TESTS, "needs-maintenance.spec.ts");
const AFTER_SPEC = join(TESTS, "needs-maintenance.repaired.spec.ts");
const REPORT = join(PARTICIPANT, "context", "playwright", "maintenance-report.md");
const COMPARISON = join(PARTICIPANT, "context", "playwright", "assertion-comparison.md");
const DIFF = join(ATTEMPT, "repair.diff");
const OLD_APP = join(TESTS, "demo-app", "checkout-server.before.mjs");
const IN_USE_APP = join(TESTS, "demo-app", "checkout-server.mjs");
const CORRECTED_APP = join(TESTS, "demo-app", "checkout-server.corrected.mjs");
const BEFORE_SHA = "346bc90d1453c9d9002beeebe2879cee96d76c81cdf0ddd877ff63867117ce0c"; // recorded by the earlier quest, before its report
const FAULTS = ["tax-left-out-of-total", "tax-rate-wrong", "tax-shown-wrong", "discount-ignored", "total-ignores-discount", "subtotal-wrong", "button-dead", "confirmation-wrong"];

const sha = (text: string) => createHash("sha256").update(text).digest("hex");
const tidy = (text: string) => text.replace(/\u001b\[[0-9;]*m/g, "").split(REPO + "/").join("").split(REPO).join("REPO");
const rel = (file: string) => relative(REPO, file);

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

// ================================================================ reading a test: its assertions and statements

type Assertion = {
  line: number; text: string; leading: string; pre: string[]; subject: string; modifiers: string[]; matcher: string; args: string[]; trailing: string; depth: number;
};
type Reading = { assertions: Assertion[]; commentedOut: number[]; statements: { line: number; text: string; ends: number }[]; comments: { line: number; text: string }[]; lines: string[]; looseExpects: number };

/** Where the bracket opened at `open` closes. Quotes are skipped. Returns -1 if it never closes. */
function closing(text: string, open: number): number {
  const pairs: Record<string, string> = { "(": ")", "[": "]", "{": "}" };
  const stack: string[] = [];
  for (let i = open; i < text.length; i += 1) {
    const c = text[i];
    if (c === '"' || c === "'" || c === "`") {
      for (i += 1; i < text.length && text[i] !== c; i += 1) if (text[i] === "\\") i += 1;
    } else if (pairs[c]) stack.push(pairs[c]);
    else if (c === ")" || c === "]" || c === "}") {
      if (stack.pop() !== c) return -1;
      if (!stack.length) return i;
    }
  }
  return -1;
}

/** Splits "a, b, { c: 1, d: 2 }" at the commas that are not inside a bracket or a quote. */
function splitArgs(text: string): string[] {
  const parts: string[] = [];
  let start = 0;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (c === '"' || c === "'" || c === "`") { for (i += 1; i < text.length && text[i] !== c; i += 1) if (text[i] === "\\") i += 1; }
    else if (c === "(" || c === "[" || c === "{") { const end = closing(text, i); if (end < 0) break; i = end; }
    else if (c === ",") { parts.push(text.slice(start, i).trim()); start = i + 1; }
  }
  const last = text.slice(start).trim();
  if (last) parts.push(last);
  return parts;
}

const LINE_END = /\r\n|[\n\r\u2028\u2029]/;

/**
 * Three copies of the source, each exactly as long as it, so that a position in one is the same position in the others.
 *   text       the source with every comment blanked out;
 *   structure  the same, with the inside of every quote and every template string blanked out as well;
 *   comments   only the comments.
 * A comment ends where JavaScript ends it: a line comment at any line terminator, a carriage return included, and a
 * block comment at its star-slash, wherever on a line that is. A template string runs over as many lines as it does.
 * NOT HANDLED: a regular expression written between slashes that has a quote in it, and ${ } inside a template.
 */
function strip(source: string): { text: string; structure: string; comments: string } {
  const text = [...source];
  const structure = [...source];
  const comments = [...source].map((c) => (LINE_END.test(c) ? c : " "));
  const blank = (list: string[], at: number) => { if (!LINE_END.test(list[at])) list[at] = " "; };
  for (let i = 0; i < source.length; i += 1) {
    const c = source[i];
    if (c === "/" && source[i + 1] === "/") {
      for (; i < source.length && !LINE_END.test(source[i]); i += 1) { comments[i] = source[i]; blank(text, i); blank(structure, i); }
      i -= 1;
    } else if (c === "/" && source[i + 1] === "*") {
      const end = source.indexOf("*/", i + 2);
      const stop = end < 0 ? source.length : end + 2;
      for (; i < stop; i += 1) { if (!LINE_END.test(source[i])) comments[i] = source[i]; blank(text, i); blank(structure, i); }
      i -= 1;
    } else if (c === '"' || c === "'" || c === "`") {
      for (i += 1; i < source.length && source[i] !== c && (c === "`" || !LINE_END.test(source[i])); i += 1) {
        blank(structure, i);
        if (source[i] === "\\" && i + 1 < source.length) { i += 1; blank(structure, i); }
      }
    }
  }
  return { text: text.join(""), structure: structure.join(""), comments: comments.join("") };
}

function read(source: string): Reading {
  const copies = strip(source);
  const lines = copies.text.split(LINE_END);
  const structureLines = copies.structure.split(LINE_END);
  const commentLines = copies.comments.split(LINE_END);
  const reading: Reading = { assertions: [], commentedOut: [], statements: [], comments: [], lines, looseExpects: (copies.structure.match(/\bexpect\b(?!\s*[.(])/g) ?? []).length };
  let depth = 0;
  lines.forEach((raw, index) => {
    const line = index + 1;
    const shape = structureLines[index];
    const comment = commentLines[index].trim();
    if (comment) {
      reading.comments.push({ line, text: comment });
      if (/\bexpect\s*[.(]/.test(comment)) reading.commentedOut.push(line);
    }
    if (!shape.trim()) return; // a blank line, a comment, or a line that lies inside a template string
    let found = false;
    let here = depth;
    for (let i = 0; i < shape.length; i += 1) {
      const c = shape[i];
      if (c === "{") here += 1;
      if (c === "}") here -= 1;
      if (shape.startsWith("expect", i) && !/[\w$.]/.test(shape[i - 1] ?? " ") && /^\s*[.(]/.test(shape.slice(i + 6))) {
        let at = i + 6;
        const pre: string[] = [];
        for (let more = shape.slice(at).match(/^\s*\.(\w+)/); more; more = shape.slice(at).match(/^\s*\.(\w+)/)) { pre.push(more[1]); at += more[0].length; }
        while (shape[at] === " ") at += 1;
        const subjectEnd = shape[at] === "(" ? closing(shape, at) : -1;
        const assertion: Assertion = { line, text: raw.trim(), leading: raw.slice(0, i).trim(), pre, subject: "", modifiers: [], matcher: "", args: [], trailing: "", depth: here };
        found = true;
        reading.assertions.push(assertion);
        if (subjectEnd < 0) { assertion.matcher = "(could not be read: it does not close on its line)"; continue; }
        assertion.subject = raw.slice(at + 1, subjectEnd).trim();
        at = subjectEnd + 1;
        const chain: string[] = [];
        for (let more = shape.slice(at).match(/^\s*\.(\w+)/); more; more = shape.slice(at).match(/^\s*\.(\w+)/)) { chain.push(more[1]); at += more[0].length; }
        assertion.matcher = chain.pop() ?? "(none)";
        assertion.modifiers = chain;
        const argsEnd = shape[at] === "(" ? closing(shape, at) : -1;
        if (argsEnd < 0) { assertion.trailing = raw.slice(at).trim() || "(no call)"; continue; }
        assertion.args = splitArgs(raw.slice(at + 1, argsEnd));
        assertion.trailing = raw.slice(argsEnd + 1).trim();
        i = argsEnd;
      }
    }
    depth = here;
    if (!found) reading.statements.push({ line, text: raw.trim(), ends: (shape.match(/;/g) ?? []).length });
  });
  return reading;
}

const plain = (arg: string | undefined) => (arg !== undefined && /^"(?:[^"\\]|\\.)*"$|^'(?:[^'\\]|\\.)*'$/.test(arg) ? arg.slice(1, -1) : null);
const numbers = (text: string | undefined) => (text ?? "").match(/\d+(?:\.\d+)?/g) ?? [];
/** The characters of `big` left over once `small` has been found in it in order. */
const gained = (small: string, big: string) => { let at = 0; let extra = ""; for (const c of big) { if (c === small[at]) at += 1; else extra += c; } return extra; };
const isSubsequence = (small: string, big: string) => { let at = 0; for (const c of big) if (c === small[at]) at += 1; return at === small.length; };
// Counted, not only looked for: a word is "new" if the test now has more of it than it had.
const DANGER: [string, RegExp][] = [["skip, fixme, fail or only, however it is written", /\b(skip|fixme|fail|only)\b/g], ["a return", /\breturn\b/g], ["a throw or an exit", /\bthrow\b|\bexit\b/g],
  ["a route that replaces what the application sends", /\b(route|fulfill|unroute|routeFromHAR)\b/g], ["code run inside the page", /\b(evaluate\w*|addInitScript|addScriptTag|setContent|exposeFunction)\b|\$eval/g],
  ["a page loaded from somewhere other than the application's own address", /\bgoto\s*\(\s*(?!["']\/)|\bdata:/g], ["retries", /retries/g], ["a time limit", /timeout|waitForTimeout/gi],
  ["a try or a catch", /\btry\b|\bcatch\b|\bfinally\b/g], ["a condition", /\bif\s*\(|\?\s|&&|\|\|/g], ["a loop", /\bfor\s*\(|\bwhile\s*\(|\.forEach\(/g], ["a function, which may never be called", /=>|\bfunction\b/g]];

type Change = { number: number; line: number; now: string; to: string; reportLine: number };
type Verdict = { weakened: string[]; toAccount: { line: number; what: string }[]; unaccounted: string[]; pairs: [Assertion | null, Assertion | null][] };

/** Pairs the assertions of two readings: first those that agree on matcher and numbers, in order, then what is left between them. */
function pair(before: Assertion[], after: Assertion[]): [Assertion | null, Assertion | null][] {
  const key = (a: Assertion) => `${a.matcher}|${numbers(a.args[0] ?? "").join(",")}`;
  const n = before.length;
  const m = after.length;
  const table = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i -= 1) for (let j = m - 1; j >= 0; j -= 1) table[i][j] = key(before[i]) === key(after[j]) ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
  const anchors: [number, number][] = [];
  for (let i = 0, j = 0; i < n && j < m;) {
    if (key(before[i]) === key(after[j])) { anchors.push([i, j]); i += 1; j += 1; } else if (table[i + 1][j] >= table[i][j + 1]) i += 1; else j += 1;
  }
  const pairs: [Assertion | null, Assertion | null][] = [];
  let i = 0;
  let j = 0;
  for (const [ai, aj] of [...anchors, [n, m] as [number, number]]) {
    while (i < ai && j < aj) { pairs.push([before[i], after[j]]); i += 1; j += 1; }
    while (i < ai) { pairs.push([before[i], null]); i += 1; }
    while (j < aj) { pairs.push([null, after[j]]); j += 1; }
    if (ai < n) { pairs.push([before[ai], after[aj]]); i = ai + 1; j = aj + 1; }
  }
  return pairs;
}

/** LAYER 1. Reads the two test files only. */
function layerOne(beforeText: string, afterText: string): Verdict {
  const before = read(beforeText);
  const after = read(afterText);
  const weakened: string[] = [];
  const toAccount: { line: number; what: string }[] = [];
  const pairs = pair(before.assertions, after.assertions);
  for (const [was, now] of pairs) {
    if (was && !now) { weakened.push(`A1: the assertion on line ${was.line} of the test before has no counterpart after: ${was.text}`); continue; }
    if (!was && now) { toAccount.push({ line: now.line, what: `an assertion was added on line ${now.line}` }); continue; }
    if (!was || !now) continue;
    const where = `line ${now.line}`;
    if (now.matcher !== was.matcher) weakened.push(`A2: ${where}: the matcher was ${was.matcher} and is now ${now.matcher}`);
    const wasText = plain(was.args[0]);
    const nowText = plain(now.args[0]);
    if (wasText !== null && nowText === null) weakened.push(`A3: ${where}: the expected value was the text "${wasText}" and is now ${now.args[0] ?? "nothing"}, which is not a plain piece of text in quotes`);
    if (now.args.length > was.args.length) weakened.push(`A3: ${where}: something was added after the expected value: ${now.args.slice(was.args.length).join(", ")}`);
    if (wasText !== null && nowText !== null && wasText !== nowText) {
      if (numbers(wasText).join(",") !== numbers(nowText).join(",")) weakened.push(`A3: ${where}: the expected value had the number ${numbers(wasText).join(", ") || "(none)"} and now has ${numbers(nowText).join(", ") || "(none)"}`);
      else if (!isSubsequence(wasText, nowText)) weakened.push(`A3: ${where}: the expected value "${wasText}" lost a character: it is now "${nowText}"`);
      else toAccount.push({ line: now.line, what: `the expected value gained characters: "${wasText}" is now "${nowText}"` });
    }
    const mods = [...now.pre, ...now.modifiers].filter((word) => ![...was.pre, ...was.modifiers].includes(word));
    if (mods.length) weakened.push(`A4: ${where}: ${mods.join(", ")} was put between expect and the matcher`);
    if (now.leading !== was.leading) weakened.push(`A5: ${where}: before the assertion the line had "${was.leading}" and now has "${now.leading}"`);
    if (now.trailing !== was.trailing) weakened.push(`A5: ${where}: after the assertion the line had "${was.trailing}" and now has "${now.trailing}"`);
    if (now.depth > was.depth) weakened.push(`A6: ${where}: the assertion is ${now.depth - was.depth} level of braces deeper than it was, so it is inside something that may not run`);
    if (was.subject.startsWith("page.") && !now.subject.startsWith("page.")) weakened.push(`A7: ${where}: the assertion looked at ${was.subject} and now looks at ${now.subject}, which is not the page`);
    else if (was.subject !== now.subject && /\bawait\b|=>|\bfunction\b|[^=!<>]=[^=>]/.test(now.subject.replace(/"[^"]*"|'[^']*'|`[^`]*`/g, ""))) weakened.push(`A7: ${where}: what the assertion looks at now does something besides finding an element: ${now.subject.length > 90 ? now.subject.slice(0, 90) + " ..." : now.subject}`);
    else if (was.subject !== now.subject) toAccount.push({ line: now.line, what: `the subject changed: ${was.subject} is now ${now.subject}` });
  }
  if (after.commentedOut.length > before.commentedOut.length) weakened.push(`A1: an assertion is commented out, on line ${after.commentedOut.join(", ")}`);
  // Statements that are not assertions.
  // Paired in order: statements that are the same in both, then what lies between them. One before and one after in
  // the same gap is a statement changed in place. Anything left over was added or removed.
  const bs = before.statements;
  const as = after.statements;
  const lcs = Array.from({ length: bs.length + 1 }, () => new Array<number>(as.length + 1).fill(0));
  for (let i = bs.length - 1; i >= 0; i -= 1) for (let j = as.length - 1; j >= 0; j -= 1) lcs[i][j] = bs[i].text === as[j].text ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  for (let i = 0, j = 0; i < bs.length || j < as.length;) {
    if (i < bs.length && j < as.length && bs[i].text === as[j].text) { i += 1; j += 1; continue; }
    const gapB: typeof bs = [];
    const gapA: typeof as = [];
    while (i < bs.length && j < as.length && bs[i].text !== as[j].text) { if (lcs[i + 1][j] >= lcs[i][j + 1]) { gapB.push(bs[i]); i += 1; } else { gapA.push(as[j]); j += 1; } }
    if (i >= bs.length) while (j < as.length) { gapA.push(as[j]); j += 1; }
    if (j >= as.length) while (i < bs.length) { gapB.push(bs[i]); i += 1; }
    // Within a gap, a statement before is taken to have become the statement after that begins most like it.
    const alike = (a: string, b: string) => { let n = 0; while (n < a.length && n < b.length && a[n] === b[n]) n += 1; return n; };
    for (const was of [...gapB]) {
      const best = [...gapA].sort((x, y) => alike(y.text, was.text) - alike(x.text, was.text))[0];
      if (!best || alike(best.text, was.text) < 12) continue;
      if (best.ends > was.ends) weakened.push(`A8: line ${best.line} held one statement and now holds more: ${best.text.length > 110 ? best.text.slice(0, 110) + " ..." : best.text}`);
      else toAccount.push({ line: best.line, what: `a statement changed in place: ${was.text} is now ${best.text}` });
      gapB.splice(gapB.indexOf(was), 1);
      gapA.splice(gapA.indexOf(best), 1);
    }
    for (const now of gapA) weakened.push(`A8: a statement was added on line ${now.line}: ${now.text.length > 110 ? now.text.slice(0, 110) + " ..." : now.text}`);
    for (const was of gapB) weakened.push(`A8: a statement was removed. It was on line ${was.line}: ${was.text}`);
  }
  const code = (r: Reading) => [...r.statements.map((s) => s.text), ...r.assertions.map((a) => a.text)].join("\n");
  const times = (pattern: RegExp, text: string) => (text.match(pattern) ?? []).length;
  const danger = DANGER.filter(([, pattern]) => times(pattern, code(after)) > times(pattern, code(before))).map(([name]) => name);
  if (danger.length) weakened.push(`A9: new in the test: ${danger.join(", ")}`);
  if (after.looseExpects !== before.looseExpects) weakened.push(`A10: the word expect appears ${after.looseExpects} time${after.looseExpects === 1 ? "" : "s"} without being called, and appeared ${before.looseExpects} before. It has been imported under another name, or defined again`);
  const commentsChanged = after.comments.filter((c) => !before.comments.some((d) => d.text === c.text));
  for (const c of commentsChanged) toAccount.push({ line: c.line, what: `a comment was added or changed: ${c.text}` });
  if (before.comments.filter((c) => !after.comments.some((d) => d.text === c.text)).length > commentsChanged.length) toAccount.push({ line: 0, what: "a comment was removed" });
  return { weakened, toAccount, unaccounted: [], pairs };
}

/** LAYER 2. Reads the report's changes. Every line that differs must be one the report lists, reading as the report says. */
function layerTwo(beforeText: string, afterText: string, changes: Change[]): string[] {
  const before = beforeText.split("\n");
  const after = afterText.split("\n");
  const problems: string[] = [];
  if (before.length !== after.length) problems.push(`the test had ${before.length - 1} lines and now has ${after.length - 1}. The report changes lines in place and adds or removes none`);
  for (let index = 0; index < Math.max(before.length, after.length); index += 1) {
    if (before[index] === after[index]) continue;
    const change = changes.find((c) => c.line === index + 1);
    if (!change) problems.push(`line ${index + 1} differs and the report does not list it`);
    else if (before[index] !== change.now) problems.push(`line ${index + 1} of the test before is not what the report's Change ${change.number} says it is`);
    else if (after[index] !== change.to) problems.push(`line ${index + 1} is not what the report's Change ${change.number} says to put there`);
  }
  for (const change of changes) if (before[change.line - 1] === after[change.line - 1]) problems.push(`the report's Change ${change.number} was not made: line ${change.line} is as it was`);
  return problems;
}

function judge(beforeText: string, afterText: string, changes: Change[]): Verdict {
  const verdict = layerOne(beforeText, afterText);
  verdict.unaccounted = layerTwo(beforeText, afterText, changes);
  return verdict;
}

function readChanges(report: string): Change[] {
  const changes: Change[] = [];
  const pattern = /^### Change (\d+) · line (\d+)\n+Now:\n+```ts\n([^\n]*)\n```\n+Change to:\n+```ts\n([^\n]*)\n```/gm;
  for (const match of report.matchAll(pattern)) changes.push({ number: Number(match[1]), line: Number(match[2]), now: match[3], to: match[4], reportLine: report.slice(0, match.index).split("\n").length });
  return changes;
}

// ================================================================ the two documents that are worked out, not typed

function makeDiff(beforeText: string, afterText: string, changes: Change[]): string {
  const before = beforeText.split("\n");
  const after = afterText.split("\n");
  const out = [
    "The repair of the checkout test. playwright-repair-test, attempt playwright-attempt-006.",
    "Written by participant/tests/playwright/tools/repair-test-check.ts --write, from the two files. Not typed by hand.",
    "One hunk for each line that differs. The words after the second @@ of a hunk say which line of the maintenance",
    "report, participant/context/playwright/maintenance-report.md, called for it. A line that differs and that the",
    "report does not call for is labelled NOT IN THE REPORT.",
    "",
    `--- a/${rel(BEFORE_SPEC)}`,
    `+++ b/${rel(AFTER_SPEC)}`,
  ];
  if (before.length !== after.length) return [...out, "THE TWO FILES DO NOT HAVE THE SAME NUMBER OF LINES. No line-for-line diff can be made.", ""].join("\n");
  before.forEach((line, index) => {
    if (line === after[index]) return;
    const change = changes.find((c) => c.line === index + 1 && c.now === line && c.to === after[index]);
    out.push(`@@ -${index + 1} +${index + 1} @@ ${change ? `maintenance report line ${change.reportLine}, "Change ${change.number} · line ${change.line}"` : "NOT IN THE REPORT"}`, `-${line}`, `+${after[index]}`);
  });
  return out.join("\n") + "\n";
}

const cell = (text: string) => "`" + text.replace(/\|/g, "\\|") + "`";

function makeComparison(beforeText: string, afterText: string, changes: Change[]): string {
  const verdict = judge(beforeText, afterText, changes);
  const beforeLines = beforeText.split("\n");
  const afterLines = afterText.split("\n");
  const out = [
    "# The assertions of the checkout test, before and after the repair",
    "",
    "Quest `playwright-repair-test`. Written by `participant/tests/playwright/tools/repair-test-check.ts --write`, which reads",
    "the two files and works this out. It was not typed by hand, and the check fails if this file is not what the program",
    "writes. The program was written by an AI assistant (Claude) at the participant's direction.",
    "",
    `- Before: \`${rel(BEFORE_SPEC)}\`, sha256 \`${sha(beforeText)}\``,
    `- After: \`${rel(AFTER_SPEC)}\`, sha256 \`${sha(afterText)}\``,
    `- The plan the repair follows: \`${rel(REPORT)}\`, part 4`,
    "",
    "The shop, its products, its prices and its discount code are made up.",
    "",
    "## In short",
    "",
    `- Assertions before: ${verdict.pairs.filter(([was]) => was).length}. Assertions after: ${verdict.pairs.filter(([, now]) => now).length}.`,
    `- Removed: ${verdict.pairs.filter(([was, now]) => was && !now).length}. Added: ${verdict.pairs.filter(([was, now]) => !was && now).length}.`,
    `- Reported as weakened by the check: ${verdict.weakened.length}.`,
    `- Changes that the maintenance report does not account for: ${verdict.unaccounted.length}.`,
    "",
    "## Each assertion, before and after",
    "",
    "An assertion here is one `expect(...)` with its matcher. \"What it looks at\" is the part inside `expect( )`.",
    "",
  ];
  verdict.pairs.forEach(([was, now], index) => {
    out.push(`### Assertion ${index + 1}${was ? ` · line ${was.line} before` : ""}${now ? ` · line ${now.line} after` : ""}`, "");
    out.push("| | Before | After | Same? |", "|---|---|---|---|");
    const row = (name: string, a: string | null, b: string | null, note = "") => out.push(`| ${name} | ${a === null ? "none" : cell(a)} | ${b === null ? "none" : cell(b)} | ${a === b ? "the same" : note || "DIFFERENT"} |`);
    row("The whole line", was?.text ?? null, now?.text ?? null, "changed");
    row("What it looks at", was?.subject ?? null, now?.subject ?? null, "changed");
    row("Matcher", was?.matcher ?? null, now?.matcher ?? null);
    const wasValue = was ? plain(was.args[0]) : null;
    const nowValue = now ? plain(now.args[0]) : null;
    row("Expected value", was ? was.args.join(", ") : null, now ? now.args.join(", ") : null, wasValue !== null && nowValue !== null && isSubsequence(wasValue, nowValue) ? `changed: gained ${JSON.stringify(gained(wasValue, nowValue))}, lost nothing` : "DIFFERENT");
    row("The number in it", was ? numbers(was.args[0] ?? "").join(", ") || "none" : null, now ? numbers(now.args[0] ?? "").join(", ") || "none" : null);
    row("Between expect and the matcher (not, soft)", was ? [...was.pre, ...was.modifiers].join(", ") || "nothing" : null, now ? [...now.pre, ...now.modifiers].join(", ") || "nothing" : null);
    row("Before it on the line", was?.leading ?? null, now?.leading ?? null);
    row("After it on the line", was?.trailing ?? null, now?.trailing ?? null);
    row("How deep in braces (1 is the test's own body)", was ? String(was.depth) : null, now ? String(now.depth) : null);
    const mine = [...verdict.weakened.filter((w) => now && w.includes(`line ${now.line}:`)), ...(was && !now ? ["removed"] : [])];
    const change = now ? changes.find((c) => c.line === now.line) : undefined;
    const exact = Boolean(now && was && change && change.now === beforeLines[was.line - 1] && change.to === afterLines[now.line - 1]);
    const elsewhere = verdict.weakened.length > mine.length || verdict.unaccounted.length > 0 ? " **But the check reported problems elsewhere in the test, listed under \"What the check reported\". They may stop this line from running.**" : "";
    let facts = "";
    if (was && now) {
      facts = [was.subject === now.subject ? "it looks at the same thing" : "what it looks at changed, as shown in the table", was.matcher === now.matcher ? "the matcher is the same" : "THE MATCHER DIFFERS",
        numbers(was.args[0]).join() === numbers(now.args[0]).join() ? "the number is the same" : "THE NUMBER DIFFERS",
        wasValue === nowValue ? "the expected value is the same" : wasValue !== null && nowValue !== null && isSubsequence(wasValue, nowValue) ? `the expected value gained ${JSON.stringify(gained(wasValue, nowValue))} and lost nothing` : "THE EXPECTED VALUE DIFFERS",
        now.leading === was.leading && now.trailing === was.trailing && now.depth === was.depth && !now.pre.length && !now.modifiers.length ? "it is still a plain awaited statement at the same depth" : "HOW IT IS CALLED DIFFERS"].join("; ");
    }
    out.push("", mine.length ? `**Verdict: WEAKENED.** ${mine.join(" ")}` : was && now && was.text === now.text ? `**Verdict: unchanged.** The line is the same, character for character.${elsewhere}`
      : exact ? `**Verdict: no rule of the check reports this line as removed, weakened or made conditional.** It reads exactly as the maintenance report's Change ${change!.number} says (report line ${change!.reportLine}). Compared with before: ${facts}.${elsewhere}`
        : `**Verdict: changed in a way the maintenance report does not call for.** Compared with before: ${facts}.`, "");
  });
  const reading = read(afterText);
  const beforeReading = read(beforeText);
  out.push("## The lines that are not assertions", "", "| Line | Before | After | |", "|---|---|---|---|");
  for (const line of [...new Set([...beforeReading.statements, ...reading.statements].map((st) => st.line))].sort((a, b) => a - b)) {
    const was = beforeReading.statements.find((st) => st.line === line);
    const now = reading.statements.find((st) => st.line === line);
    const change = changes.find((c) => c.line === line);
    out.push(`| ${line} | ${was ? cell(was.text) : "none"} | ${now ? cell(now.text) : "none"} | ${was && now && now.text === was.text ? "the same" : was && now && change && change.now.trim() === was.text && change.to.trim() === now.text ? `changed, as the report's Change ${change.number} says` : "DIFFERENT, AND NOT BY THE REPORT"} |`);
  }
  const sameComments = beforeReading.comments.length === reading.comments.length && beforeReading.comments.every((c, k) => reading.comments[k].text === c.text && reading.comments[k].line === c.line);
  const ruleLine = reading.comments.find((c) => /BUSINESS RULE/.test(c.text));
  out.push("", `Comment lines: ${beforeReading.comments.length} before and ${reading.comments.length} after, ${sameComments ? "each the same and on the same line" : "NOT ALL THE SAME"}. ${ruleLine ? `The comment that states the business rule is on line ${ruleLine.line} after the repair.` : "NO COMMENT STATES THE BUSINESS RULE AFTER THE REPAIR."}`,
    "", "## What the check reported", "",
    ...(verdict.weakened.length ? verdict.weakened.map((w) => `- WEAKENED: ${w}`) : ["- Weakened: nothing."]),
    ...(verdict.unaccounted.length ? verdict.unaccounted.map((w) => `- NOT ACCOUNTED FOR: ${w}`) : ["- Not accounted for by the report: nothing."]),
    "", verdict.unaccounted.length ? "Changes the check could not judge from the two files alone. NOT all of them are accounted for by the report: see above." : "Changes the check could not judge from the two files alone. Each is one the report calls for, word for word:", "",
    ...verdict.toAccount.map((t) => `- line ${t.line}: ${t.what}`),
    "", "## What this comparison cannot show", "",
    "- It compares text. That a changed locator finds the right element is shown by running the test, not here. The record of",
    "  that is the mutation run, `logs/mutation-run.txt` in the attempt folder.",
    "- It reads the test file only. A weakening in the settings file, in the application, or in the command that runs the",
    "  test would not appear in it.",
    "- \"As the report says\" is only as good as the report.", "");
  return out.join("\n");
}

// ================================================================ the application and the test runner

let nextPort = 5300 + Math.floor(Math.random() * 300);

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
          // Something else already listening on this port would answer too, and this child would then have stopped.
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

type Run = { status: string; line: number | null; message: string; ran: number; exit: number | null };

function runTest(port: number, testDir: string | null, extra: string[] = []): Promise<Run> {
  const env: Record<string, string | undefined> = { ...process.env, CHECKOUT_PORT: String(port), GTQ_TEST_DIR: testDir ?? "", FORCE_COLOR: "0" };
  if (!testDir) delete env.GTQ_TEST_DIR;
  return new Promise((done) => {
    const child = spawn(process.execPath, [CLI, "test", "--config", "repair.config.ts", "--reporter", "json", ...extra], { cwd: TESTS, env });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("close", (exit) => {
      try {
        const report = JSON.parse(stdout);
        const results = (report.suites ?? []).flatMap((suite: any) => suite.specs ?? []).flatMap((spec: any) => spec.tests ?? []).flatMap((test: any) => test.results ?? []);
        if (!results.length) return done({ status: "no test ran", line: null, message: "", ran: 0, exit });
        const result = results[0];
        const error = result.error ?? result.errors?.[0];
        const message = error ? tidy(String(error.message)).split("\n").filter((line) => /Locator:|Expected|Received|Timeout|Error:/.test(line)).map((line) => line.trim()).join(" | ") : "";
        done({ status: result.status, line: error?.location?.line ?? null, message, ran: results.length, exit });
      } catch {
        done({ status: "did not run", line: null, message: tidy((stderr || stdout || "").slice(0, 300)), ran: 0, exit });
      }
    });
  });
}

async function runAgainst(app: string, env: Record<string, string>, testDir: string | null, extra: string[] = []): Promise<Run> {
  const { child, port } = await startApp(app, env);
  try { return await runTest(port, testDir, extra); } finally { await stopApp(child); }
}

/** Runs the tasks a few at a time and gives their results in order. */
async function pool<T>(tasks: (() => Promise<T>)[], width = 4): Promise<T[]> {
  const results = new Array<T>(tasks.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(width, tasks.length) }, async () => {
    while (next < tasks.length) { const mine = next; next += 1; results[mine] = await tasks[mine](); }
  }));
  return results;
}

const shown = (run: Run) => (run.status === "passed" ? "passed" : `${run.status}${run.line ? ` at line ${run.line}` : ""}${run.message ? `: ${run.message}` : ""}`);

/** What the application shows a customer: the four amounts of the summary, then the total on the confirmation. */
async function amountsShown(app: string): Promise<Record<string, string>> {
  const { child, port } = await startApp(app);
  try {
    const page = await (await fetch(`http://127.0.0.1:${port}/`, { headers: { connection: "close" } })).text();
    const confirmation = await (await fetch(`http://127.0.0.1:${port}/order`, { method: "POST", headers: { connection: "close" } })).text();
    const pick = (html: string, id: string) => html.match(new RegExp(`data-testid="${id}">([^<]*)<`))?.[1] ?? "(not on the page)";
    return { subtotal: pick(page, "summary-subtotal"), discount: pick(page, "summary-discount"), tax: pick(page, "summary-tax"), total: pick(page, "summary-total"), charged: pick(confirmation, "confirmation-total"),
      button: page.match(/<button type="submit">([^<]*)</)?.[1] ?? "(none)" };
  } finally { await stopApp(child); }
}

// ---------------------------------------------------------------- the ways the rule is broken

type Mutant = { name: string; title: string; why: string; from: string; to: string; expectLine: number; expected: string; received: string };
const MUTANTS: Mutant[] = [
  { name: "tax-before-discount", title: "Tax worked out on the subtotal, before the discount is taken off",
    why: "It is the fault the redesign really shipped: one word, goods, became subtotal. The customer is charged tax on money they did not pay.",
    from: "  const tax = goods * (fault", to: "  const tax = subtotal * (fault", expectLine: 11, expected: "£7.20", received: "£8.00" },
  { name: "tax-rate-25", title: "The wrong rate: 25% where the rule says 20%",
    why: "The rule has two halves, a rate and what the rate is taken of. The first way breaks the second half. This breaks the first.",
    from: "const TAX_RATE = 0.2;", to: "const TAX_RATE = 0.25;", expectLine: 11, expected: "£7.20", received: "£9.00" },
  { name: "tax-not-charged", title: "The tax is shown correctly and is left out of what the customer is charged",
    why: "The tax line on the page stays right, so the assertion on the tax cannot see it. It asks whether the test guards the rule or only one figure.",
    from: "  let total = goods + tax;", to: "  let total = goods;", expectLine: 12, expected: "£43.20", received: "£36.00" },
];
const TAX_LINE = '  const tax = goods * (fault === "tax-rate-wrong" ? 0.25 : TAX_RATE);';
const HARMLESS = { name: "same-rule-written-differently", title: "CONTROL: the same rule written another way. The goods are worked out again inside the tax line, as the subtotal less the discount",
  from: "  const tax = goods * (fault", to: "  const tax = (subtotal - discount) * (fault" };
// Ways of breaking the rule that give the right figures for the one basket the application has. Proposed by an independent
// reader of this program. The test cannot catch them, before the repair or after it.
const SURVIVORS = [
  { name: "rate-0.2001", title: "a rate of 20.01%", from: "const TAX_RATE = 0.2;", to: "const TAX_RATE = 0.2001;" },
  { name: "eighteen-percent-of-subtotal", title: "18% of the subtotal before the discount, which is right only when the discount is 10%", from: TAX_LINE, to: "  const tax = subtotal * 0.18;" },
  { name: "tax-is-a-constant", title: "the tax is always 7.20, whatever is in the basket", from: TAX_LINE, to: "  const tax = 7.2;" },
  { name: "discount-hard-coded", title: "the discount taken off before tax is always 4.00, whatever the discount is", from: TAX_LINE, to: "  const tax = (subtotal - 4) * TAX_RATE;" },
  { name: "tax-capped", title: "the tax is never more than 7.20", from: TAX_LINE, to: "  const tax = Math.min(goods * TAX_RATE, 7.2);" },
];
const FAULT_LINES: Record<string, number> = { "tax-left-out-of-total": 12, "tax-rate-wrong": 11, "tax-shown-wrong": 11, "discount-ignored": 11, "total-ignores-discount": 12, "subtotal-wrong": 8, "button-dead": 14, "confirmation-wrong": 15 };

function mutantApp(scratch: string, name: string, from: string, to: string, base = CORRECTED_APP): string {
  const source = readFileSync(base, "utf8");
  if (source.split(from).length !== 2) throw new Error(`${rel(base)} does not have, exactly once, the line this check changes: ${from}`);
  const file = join(scratch, `checkout-${name}.mjs`);
  writeFileSync(file, source.replace(from, to));
  return file;
}

// ---------------------------------------------------------------- deliberately weakened versions of the repaired test

type Weak = { title: string; expect: string; edit: (text: string) => string };
const TAX = '  await expect(page.getByTestId("summary-tax")).toHaveText("£7.20");';
const swap = (from: string, to: string) => (text: string) => { if (text.split(from).length !== 2) throw new Error(`The repaired test does not have, exactly once: ${from}`); return text.replace(from, to); };
const WEAK: Weak[] = [
  { title: "THE SCENARIO'S REPAIR: the tax and the totals only have to contain a number", expect: "A3",
    edit: (t) => swap(TAX, '  await expect(page.getByTestId("summary-tax")).toHaveText(/\\d/);')(t).split('toHaveText("£43.20")').join("toHaveText(/\\d/)") },
  { title: "the tax assertion deleted", expect: "A1", edit: (t) => t.replace(TAX + "\n", "") },
  { title: "the tax assertion commented out", expect: "A1", edit: swap(TAX, "  // " + TAX.trim()) },
  { title: "the expected amounts set to what a wrong page shows: 8.00, 44.00, 44.00", expect: "A3", edit: (t) => t.split("£7.20").join("£8.00").split("£43.20").join("£44.00") },
  { title: "toHaveText became toContainText on the tax", expect: "A2", edit: swap(TAX, '  await expect(page.getByTestId("summary-tax")).toContainText("£");') },
  { title: "toHaveText became toBeVisible on the tax", expect: "A2", edit: swap(TAX, '  await expect(page.getByTestId("summary-tax")).toBeVisible();') },
  { title: "the tax checked only if it is on the page (an if on the same line)", expect: "A5", edit: swap(TAX, '  if (await page.getByTestId("summary-tax").isVisible()) await expect(page.getByTestId("summary-tax")).toHaveText("£7.20");') },
  { title: "the tax checked only when a condition holds (an if with braces)", expect: "A6",
    edit: swap(TAX, '  if ((await page.getByTestId("summary-tax").innerText()) === "£7.20") {\n  ' + TAX + "\n  }") },
  { title: "the tax assertion inside a try with an empty catch", expect: "A6", edit: swap(TAX, "  try {\n  " + TAX + "\n  } catch { /* ignore */ }") },
  { title: "a .catch() on the end of the tax assertion", expect: "A5", edit: swap(TAX, TAX.slice(0, -1) + ".catch(() => {});") },
  { title: "the await taken off the tax assertion", expect: "A5", edit: swap(TAX, TAX.replace("await ", "")) },
  { title: "expect.soft on the tax", expect: "A4", edit: swap(TAX, TAX.replace("expect(", "expect.soft(")) },
  { title: "the tax turned round: not £0.00", expect: "A4", edit: swap(TAX, '  await expect(page.getByTestId("summary-tax")).not.toHaveText("£0.00");') },
  { title: "the tax compared with itself: the expected value is read from the page", expect: "A3",
    edit: swap(TAX, '  const taxShown = await page.getByTestId("summary-tax").innerText();\n  await expect(page.getByTestId("summary-tax")).toHaveText(taxShown);') },
  { title: "a constant compared with itself", expect: "A7", edit: swap(TAX, '  await expect("£7.20").toBe("£7.20");') },
  { title: "an option added to the tax: ignoreCase", expect: "A3", edit: swap(TAX, '  await expect(page.getByTestId("summary-tax")).toHaveText("£7.20", { ignoreCase: true });') },
  { title: "the test switched off with fixme", expect: "A9", edit: swap('test("checkout shows', 'test.fixme("checkout shows') },
  { title: "a skip at the top of the test", expect: "A8", edit: swap('  await page.goto("/");', '  test.skip(true, "flaky since the redesign");\n  await page.goto("/");') },
  { title: "a return before the tax assertion", expect: "A8", edit: swap(TAX, "  return;\n" + TAX) },
  { title: "the page replaced by a stub: page.route answers with fixed amounts", expect: "A8",
    edit: swap('  await page.goto("/");', '  await page.route("**/", (route) => route.fulfill({ contentType: "text/html; charset=utf-8", body: \'<dl><dd data-testid="summary-subtotal">£40.00</dd><dd data-testid="summary-discount">-£4.00</dd><dd data-testid="summary-tax">£7.20</dd><dd data-testid="summary-total">£43.20</dd></dl><form method="post" action="/order"><button>Buy now</button></form>\' }));\n  await page.goto("/");') },
  { title: "the amounts written into the page before they are checked: page.evaluate", expect: "A8",
    edit: swap(TAX, '  await page.evaluate(() => { document.querySelector(\'[data-testid="summary-tax"]\')!.textContent = "£7.20"; });\n' + TAX) },
  { title: "retries switched on for the file", expect: "A8", edit: swap('test("checkout shows', 'test.describe.configure({ retries: 3 });\ntest("checkout shows') },
];
// Changes that Layer 1 cannot judge, and that are reported all the same, by Layer 2, because the report did not ask for them.
const STRICT: Weak[] = [
  { title: "an equal-looking locator the report did not write: locator('[data-testid=\"summary-tax\"]')", expect: "line 11 is not what the report's Change 3 says to put there",
    edit: swap(TAX, '  await expect(page.locator(\'[data-testid="summary-tax"]\')).toHaveText("£7.20");') },
  { title: "the tax assertion pointed at a different element with the same expected value: the total", expect: "line 11 is not what the report's Change 3 says to put there",
    edit: swap(TAX, '  await expect(page.getByTestId("summary-total")).toHaveText("£7.20");') },
  { title: "the test's title changed", expect: "line 6 differs and the report does not list it", edit: swap("checkout shows the right amounts", "checkout works") },
  { title: "one of the report's changes left undone: line 15 as it was", expect: "the report's Change 6 was not made", edit: swap('page.getByTestId("confirmation-total")).toHaveText("£43.20")', 'page.locator("#confirm-total")).toHaveText("43.20")') },
];

// Versions written by an independent reader who was given this program and asked to get a weakened test past Layer 1.
// `expect` is the rule Layer 1 now reports each under. As first built, it reported none of them: see PROOF.md.
const setLines = (changes: Record<number, string>) => (text: string) => { const lines = text.split("\n"); for (const [n, to] of Object.entries(changes)) lines[Number(n) - 1] = to; return lines.join("\n"); };
const LAST = '  await expect(page.getByTestId("confirmation-total")).toHaveText("£43.20");';
const ESCAPES: Weak[] = [
  { title: "a return hidden after a comment on the same line", expect: "A9", edit: setLines({ 10: "  /* BUSINESS RULE: tax is 20% after the discount. */ return;" }) },
  { title: "a block comment opened in the middle of line 7 and closed on line 15, so six lines of the test are a comment", expect: "A1",
    edit: setLines({ 7: '  await page.goto("/"); /*', 15: LAST + " // */" }) },
  { title: "the same six lines inside a template string", expect: "A1", edit: setLines({ 7: '  await page.goto("/"); void `', 15: LAST + " //`;" }) },
  { title: "expect itself replaced, on the import line, by a function that checks nothing", expect: "A10",
    edit: setLines({ 1: 'import { expect as real, test } from "@playwright/test"; const expect = (_: unknown) => ({ toHaveText: async (_t: string) => {}, toBeVisible: async () => {} });' }) },
  { title: "the page loaded from a data: address holding fixed amounts, and never from the application", expect: "A9",
    edit: setLines({ 7: '  await page.goto(\'data:text/html;charset=utf-8,<dd data-testid="summary-subtotal">£40.00</dd><dd data-testid="summary-discount">-£4.00</dd><dd data-testid="summary-tax">£7.20</dd><dd data-testid="summary-total">£43.20</dd><button>Buy now</button><h1>Order placed</h1><b data-testid="confirmation-total">£43.20</b>\');' }) },
  { title: "the tax written into the page from inside the assertion's own subject", expect: "A7",
    edit: setLines({ 11: '  await expect(page.getByTestId((await page.evaluateHandle(() => { document.querySelector(\'[data-testid="summary-tax"]\')!.textContent = "£7.20"; }), "summary-tax"))).toHaveText("£7.20");' }) },
  { title: "a return after a bare carriage return inside the comment line, which ends the comment for JavaScript", expect: "A9",
    edit: setLines({ 10: "  // BUSINESS RULE: tax is 20% of what the customer pays for the goods, after the discount. 36.00 x 20% = 7.20.\r  return;" }) },
  { title: "a skip written without a dot: test[\"skip\"]()", expect: "A9", edit: setLines({ 7: '  await page.goto("/"); test["skip"]();' }) },
];

// ================================================================ the two jobs

function write() {
  const before = readFileSync(BEFORE_SPEC, "utf8");
  const after = readFileSync(AFTER_SPEC, "utf8");
  const changes = readChanges(readFileSync(REPORT, "utf8"));
  mkdirSync(dirname(DIFF), { recursive: true });
  writeFileSync(DIFF, makeDiff(before, after, changes));
  writeFileSync(COMPARISON, makeComparison(before, after, changes));
  console.log(`Wrote ${rel(DIFF)} and ${rel(COMPARISON)}.`);
  return 0;
}

async function main() {
  const before = readFileSync(BEFORE_SPEC, "utf8");
  const after = readFileSync(AFTER_SPEC, "utf8");
  const report = readFileSync(REPORT, "utf8");
  const changes = readChanges(report);
  const corrected = readFileSync(CORRECTED_APP, "utf8");
  const scratch = mkdtempSync(join(TESTS, ".repair-scratch-"));
  const copyDir = (name: string, text: string) => {
    const dir = join(scratch, name);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "copy.spec.ts"), text);
    return dir;
  };
  const head = ["The checkout is made up and ran on this computer only, on 127.0.0.1. Every price, product and code in it is invented.",
    "Every weakened test and every broken application below was a copy in a scratch folder, deleted at the end. Paths are shown from the repository's top folder."];
  const weak = new Log("The weakening check. playwright-repair-test, attempt playwright-attempt-006", "Recorded by participant/tests/playwright/tools/repair-test-check.ts.", ...head);
  const mutation = new Log("The mutation run. playwright-repair-test, attempt playwright-attempt-006", "Recorded by participant/tests/playwright/tools/repair-test-check.ts.", ...head);
  try {
    // ------------------------------------------------------------ broken applications, used by both logs
    const mutantFiles = MUTANTS.map((m) => mutantApp(scratch, m.name, m.from, m.to));
    const harmless = mutantApp(scratch, HARMLESS.name, HARMLESS.from, HARMLESS.to);

    // ============================================================ THE WEAKENING CHECK
    weak.part("PART 1. What is compared");
    weak.out(`BEFORE  ${rel(BEFORE_SPEC)}`, `        sha256 ${sha(before)}`, `AFTER   ${rel(AFTER_SPEC)}`, `        sha256 ${sha(after)}`, `PLAN    ${rel(REPORT)}, part 4: ${changes.length} changes, for lines ${changes.map((c) => c.line).join(", ")}`);
    weak.check("the test before the repair is byte for byte the file the maintenance report was written for (the checksum the earlier quest recorded)", sha(before) === BEFORE_SHA);
    weak.check("the report's part 4 can be read: six changes, each with the line now and the line to put there", changes.length === 6 && changes.every((c) => c.now && c.to));

    weak.part("PART 2. The check, run on the repair (criteria 1, 2 and 3)");
    const verdict = judge(before, after, changes);
    weak.out("LAYER 1, from the two test files alone.", `  assertions before: ${read(before).assertions.length}. assertions after: ${read(after).assertions.length}.`,
      ...(verdict.weakened.length ? verdict.weakened.map((w) => `  WEAKENED: ${w}`) : ["  WEAKENED: nothing reported."]),
      "  Changes it cannot judge by itself, to be accounted for by the report:", ...verdict.toAccount.map((t) => `    line ${String(t.line).padStart(2)}: ${t.what}`),
      "LAYER 2, against the maintenance report.", ...(verdict.unaccounted.length ? verdict.unaccounted.map((u) => `  NOT ACCOUNTED FOR: ${u}`) : ["  Every line that differs is a line the report lists, and reads exactly as the report says to make it."]),
      `VERDICT ON THE REPAIR: ${verdict.weakened.length || verdict.unaccounted.length ? "NOT SOUND" : "SOUND"}`);
    const pairs = verdict.pairs;
    weak.check("criterion 2: no assertion is removed. Six before, six after, each paired with its counterpart on the same line", pairs.length === 6 && pairs.every(([was, now]) => was && now && was.line === now.line));
    weak.check("criterion 2: no assertion is loosened. Each has the same matcher and the same number, and each expected value gained exactly the one character £ and lost none",
      pairs.every(([was, now]) => was && now && was.matcher === now.matcher && numbers(was.args[0]).join() === numbers(now.args[0]).join()
        && (was.args.length === 0 ? now.args.length === 0 : now.args.length === 1 && isSubsequence(plain(was.args[0]) ?? "?", plain(now.args[0]) ?? "") && gained(plain(was.args[0]) ?? "", plain(now.args[0]) ?? "") === "£")));
    weak.check("criterion 2: no assertion is made conditional. Each is still a plain awaited statement in the test's own body, with nothing before or after it",
      pairs.every(([was, now]) => was && now && now.leading === "await" && now.trailing === ";" && now.depth === was.depth && !now.pre.length && !now.modifiers.length));
    weak.check("Layer 1 reports nothing weakened", verdict.weakened.length === 0);
    weak.check("criterion 1: the repair follows the report. All six of its changes are made, each exactly as written", verdict.unaccounted.length === 0 && changes.every((c) => after.split("\n")[c.line - 1] === c.to));
    const differing = before.split("\n").map((line, index) => (line === after.split("\n")[index] ? 0 : index + 1)).filter(Boolean);
    weak.out(`Lines that differ between the two files: ${differing.join(", ")}. Lines the report said would change: ${changes.map((c) => c.line).join(", ")}.`);
    weak.check("criterion 3: the lines that differ are exactly the lines the report said would change, and the test has the same number of lines", differing.join() === changes.map((c) => c.line).join() && before.split("\n").length === after.split("\n").length);
    weak.check("line 10, the comment that states the business rule, is unchanged", before.split("\n")[9] === after.split("\n")[9] && /BUSINESS RULE/.test(after.split("\n")[9]));

    weak.part("PART 3. The diff of the repair (criteria 1 and 3)");
    const diffNow = existsSync(DIFF) ? readFileSync(DIFF, "utf8") : "";
    weak.out(`${rel(DIFF).replace("playwright-attempt-006", "playwright-attempt-006")}`, ...diffNow.split("\n").filter((line) => line.startsWith("@@")).map((line) => `  ${line}`));
    weak.check("repair.diff is what this program writes from the two files. It was not adjusted by hand", diffNow === makeDiff(before, after, changes));
    const hunks = [...diffNow.matchAll(/^@@ -(\d+) \+(\d+) @@ maintenance report line (\d+), "Change (\d+) · line (\d+)"$/gm)];
    const reportLines = report.split("\n");
    weak.check("it has one hunk for each changed line, six, and every hunk is labelled with a line of the report", hunks.length === 6 && diffNow.split("\n").filter((line) => line.startsWith("@@")).length === 6);
    weak.check("each label is true: that line of the report is the heading of the change, and names the same line of the test",
      hunks.length === 6 && hunks.every((h) => reportLines[Number(h[3]) - 1] === `### Change ${h[4]} · line ${h[5]}` && h[1] === h[5] && h[2] === h[5]));
    const patched = join(scratch, "patched.spec.ts");
    const patch = spawnSync("patch", ["-s", "-o", patched, BEFORE_SPEC, DIFF], { encoding: "utf8" });
    weak.out(`  patch -o SCRATCH/patched.spec.ts needs-maintenance.spec.ts repair.diff: exit code ${patch.status}`);
    weak.check("applying repair.diff to the test before, with the system's patch program, gives the repaired test byte for byte", patch.status === 0 && existsSync(patched) && readFileSync(patched, "utf8") === after);

    weak.part("PART 4. The comparison of assertions (criterion 7)");
    const comparison = existsSync(COMPARISON) ? readFileSync(COMPARISON, "utf8") : "";
    weak.check(`${rel(COMPARISON)} is what this program writes from the two files. It was not adjusted by hand`, comparison === makeComparison(before, after, changes));
    weak.check("it has a section for each of the six assertions, and each shows the whole line before and the whole line after",
      pairs.every(([was, now], index) => was && now && comparison.includes(`### Assertion ${index + 1} · line ${was.line} before · line ${now.line} after`) && comparison.includes(cell(was.text)) && comparison.includes(cell(now.text))));
    weak.check("it gives no assertion the verdict WEAKENED, and none the verdict of a change the report does not call for", !/Verdict: WEAKENED|does not call for\.\*\*/.test(comparison));

    weak.part("PART 5. The check, run on deliberately weakened versions (criterion 6)",
      "Each version below is the repaired test with one thing done to it. LAYER 1 must report it from the test files alone.",
      "Beside each: what that version does when it is run. \"green\" is against the corrected application. \"broken rule\" is against",
      "the three applications of the mutation run and a fourth where only the tax figure shown is wrong. A weakened test that",
      "still fails against all four is one that running alone would never expose.");
    const fourBroken: [string, Record<string, string>][] = [...mutantFiles.map((file) => [file, {}] as [string, Record<string, string>]), [CORRECTED_APP, { CHECKOUT_FAULT: "tax-shown-wrong" }]];
    const weakRuns = await pool(WEAK.map((version, index) => async () => {
      const text = version.edit(after);
      const dir = copyDir(`weak-${index + 1}`, text);
      const green = await runAgainst(CORRECTED_APP, {}, dir);
      let caught = 0;
      for (const [file, env] of fourBroken) caught += (await runAgainst(file, env, dir)).status === "failed" ? 1 : 0;
      return { text, green, caught };
    }));
    let flagged = 0;
    let silent = 0;
    WEAK.forEach((version, index) => {
      const run = weakRuns[index];
      const found = layerOne(before, run.text);
      const second = layerTwo(before, run.text, changes);
      weak.out("", `WEAKENED VERSION ${index + 1}: ${version.title}.`, ...found.weakened.map((w) => `    WEAKENED: ${w}`), `    Layer 2 also reports ${second.length} line${second.length === 1 ? "" : "s"} the report does not account for.`,
        `    when run: against the corrected application it ${run.green.status === "passed" ? "PASSES (green)" : shown(run.green)}. With the rule broken it fails in ${run.caught} of 4.`);
      const ok = found.weakened.some((w) => w.startsWith(version.expect));
      flagged += ok ? 1 : 0;
      silent += run.green.status === "passed" && run.caught < 4 ? 1 : 0;
      weak.check(`version ${index + 1} is reported as weakened by Layer 1, under ${version.expect}`, ok);
    });
    weak.out("", `Reported as weakened: ${flagged} of ${WEAK.length}.`,
      `Of the ${WEAK.length}, ${silent} are green against the corrected application and let at least one broken rule through. Those are the dangerous ones: nothing but a check like this, or a mutation run, shows them.`);
    const scenario = weakRuns[0];
    weak.check("the scenario's own repair, \"contains a number\", is green against the corrected application, lets every one of the four broken rules through, and is reported", scenario.green.status === "passed" && scenario.caught === 0 && layerOne(before, scenario.text).weakened.length > 0);

    weak.part("PART 6. Changes Layer 1 cannot judge, which Layer 2 reports because the report did not ask for them",
      "The first is not a weakening at all. The check is strict on purpose: it reports any change the plan did not call for, and a person decides.");
    const strictRuns = await pool(STRICT.map((version, index) => async () => {
      const text = version.edit(after);
      const dir = copyDir(`strict-${index + 1}`, text);
      return { text, green: await runAgainst(CORRECTED_APP, {}, dir) };
    }));
    STRICT.forEach((version, index) => {
      const run = strictRuns[index];
      const found = layerOne(before, run.text);
      const second = layerTwo(before, run.text, changes);
      weak.out("", `VERSION S${index + 1}: ${version.title}.`, `    Layer 1: ${found.weakened.length ? found.weakened.join(" ") : "nothing reported as weakened"}.`, ...second.map((s) => `    NOT ACCOUNTED FOR: ${s}`),
        `    when run against the corrected application: ${shown(run.green)}`);
      weak.check(`version S${index + 1} is reported by Layer 2: "${version.expect}"`, second.some((s) => s.includes(version.expect)));
    });
    weak.check("Layer 1 by itself reports nothing for S1 and S2. Without a report to hold a change to, it would let a re-pointed locator through, and says so at the head of the program",
      layerOne(before, strictRuns[0].text).weakened.length === 0 && layerOne(before, strictRuns[1].text).weakened.length === 0);

    weak.part("PART 6B. Versions an independent reader wrote to get past Layer 1",
      "A reader was given this program as first built and asked for weakened tests that Layer 1 would not report. It wrote these eight.",
      "AS FIRST BUILT, LAYER 1 REPORTED NONE OF THE EIGHT. Layer 2 reported all eight. Layer 1 was then changed, and what follows is Layer 1 as it is now.");
    const escapeRuns = await pool(ESCAPES.map((version, index) => async () => {
      const text = version.edit(after);
      const dir = copyDir(`escape-${index + 1}`, text);
      const green = await runAgainst(CORRECTED_APP, {}, dir);
      let caught = 0;
      for (const [file, env] of fourBroken) caught += (await runAgainst(file, env, dir)).status === "failed" ? 1 : 0;
      return { text, green, caught };
    }));
    let escapesReported = 0;
    ESCAPES.forEach((version, index) => {
      const run = escapeRuns[index];
      const found = layerOne(before, run.text);
      const second = layerTwo(before, run.text, changes);
      escapesReported += found.weakened.length ? 1 : 0;
      weak.out("", `READER'S VERSION E${index + 1}: ${version.title}.`, ...(found.weakened.length ? found.weakened.map((w) => `    WEAKENED: ${w.length > 200 ? w.slice(0, 200) + " ..." : w}`) : ["    LAYER 1 REPORTS NOTHING."]),
        `    Layer 2 reports ${second.length} line${second.length === 1 ? "" : "s"} the report does not account for.`,
        `    when run: against the corrected application it ${run.green.status === "passed" ? "PASSES (green)" : shown(run.green).slice(0, 160)}. With the rule broken it fails in ${run.caught} of 4.`);
      weak.check(`version E${index + 1} is reported by Layer 2, which holds every line to the report`, second.length > 0);
    });
    weak.out("", `Layer 1, as it is now, reports ${escapesReported} of the 8. That it now catches these eight says nothing about a ninth.`);
    weak.check("Layer 1, as changed after the reader's findings, reports each of the eight, under the rule expected", ESCAPES.every((version, index) => layerOne(before, escapeRuns[index].text).weakened.some((w) => w.startsWith(version.expect))));

    weak.part("PART 7. What the check cannot see: a weakening that is not in the test file",
      "The repaired test, unchanged, run by a command that selects no test and is told that this is acceptable. The rule is broken",
      "(tax before the discount). The test file is exactly the repaired one, so the weakening check has nothing to report.");
    const blind = await runAgainst(mutantFiles[0], {}, null, ["--grep", "no test has this title", "--pass-with-no-tests"]);
    weak.out(`  the command's exit code: ${blind.exit}. tests that ran: ${blind.ran}. status: ${blind.status}.`,
      `  the weakening check on the same file: ${judge(before, after, changes).weakened.length + judge(before, after, changes).unaccounted.length} problems reported.`);
    weak.check("the command exits 0 with the rule broken, having run no test, and the weakening check reports nothing. This is recorded as a limit, not a pass", blind.exit === 0 && blind.ran === 0);
    weak.check("this program labels that run \"no test ran\", so the mutation run cannot count it as the test failing or as the test passing", blind.status === "no test ran");

    weak.part("PART 8. That this check can fail");
    const spoil = (label: string, expect: string, problems: string[]) => {
      weak.out(`Spoiled: ${label}`, ...(problems.length ? problems.map((problem) => `    PROBLEM: ${problem}`) : ["    no problem reported"]));
      weak.check(`reported: "${expect}"`, problems.some((problem) => problem.includes(expect)));
    };
    spoil("the diff with one hunk's label pointing at a different line of the report (in memory)", "not what this program writes", diffNow.replace(/maintenance report line \d+, "Change 3/, 'maintenance report line 1, "Change 3') === makeDiff(before, after, changes) ? [] : ["the diff is not what this program writes"]);
    spoil("the comparison with one \"After\" cell edited (in memory)", "not what this program writes", comparison.replace("£7.20", "£8.00") === makeComparison(before, after, changes) ? [] : ["the comparison is not what this program writes"]);
    spoil("the repaired test with nothing changed at all: the test before, offered as the repair", "the report's Change 1 was not made", layerTwo(before, before, changes));
    spoil("a report with one change fewer than the repair makes (Change 5 taken out, in memory)", "line 13 differs and the report does not list it", layerTwo(before, after, changes.filter((c) => c.number !== 5)));
    const sound = judge(before, after, changes);
    weak.check("and the repair itself, checked again at the end, is still sound", sound.weakened.length === 0 && sound.unaccounted.length === 0);

    // ============================================================ THE MUTATION RUN
    mutation.part("PART 1. What is run");
    mutation.out(`THE REPAIRED TEST      ${rel(AFTER_SPEC)}`, `                       sha256 ${sha(after)}`, `THE CORRECTED CHECKOUT ${rel(CORRECTED_APP)}`, `                       sha256 ${sha(corrected)}`,
      `SETTINGS               ${rel(join(TESTS, "repair.config.ts"))}: no retries, one worker, no trace, screenshot or video`,
      "", "How the corrected checkout differs from the redesigned one in use, demo-app/checkout-server.mjs, leaving comment lines aside:");
    const codeLines = (text: string) => text.split("\n").filter((line) => !line.trim().startsWith("//"));
    const inUse = codeLines(readFileSync(IN_USE_APP, "utf8"));
    const fixed = codeLines(corrected);
    const codeDiffers = inUse.map((line, index) => (line === fixed[index] ? "" : `    in use:    ${line.trim()}\n    corrected: ${fixed[index]?.trim()}`)).filter(Boolean);
    mutation.out(...codeDiffers);
    mutation.check("the corrected checkout differs from the one in use in two lines of code, both the tax, and in nothing else but comments", inUse.length === fixed.length && codeDiffers.length === 2
      && codeDiffers[0] === `    in use:    const tax = subtotal * (fault === "tax-rate-wrong" ? 0.25 : TAX_RATE);\n    corrected: ${TAX_LINE.trim()}`
      && codeDiffers[1] === '    in use:    return { subtotal, discount, tax, shownTax: fault === "tax-shown-wrong" ? subtotal * 0.25 : tax, total };\n    corrected: return { subtotal, discount, tax, shownTax: fault === "tax-shown-wrong" ? goods * 0.25 : tax, total };');
    const settings = readFileSync(join(TESTS, "repair.config.ts"), "utf8");
    const body = (text: string) => strip(text).text.slice(strip(text).text.indexOf("export default")).split("\n").map((line) => line.trim()).filter((line) => line && !/^(testMatch|outputDir):/.test(line));
    const earlier = readFileSync(join(TESTS, "maintenance.config.ts"), "utf8");
    mutation.check("the settings are those the test ran under before the repair: apart from which file is run and where output goes, the two settings files set the same things, retries 0 and the same two time limits among them",
      body(settings).join("\n") === body(earlier).join("\n") && body(settings).includes("retries: 0,") && body(settings).includes("expect: { timeout: 1_500 },"));
    mutation.check("the repaired test has no skip, fixme, fail, only or retries in it, however written", !/\b(skip|fixme|fail|only|retries)\b/.test(strip(after).text));

    mutation.part("PART 2. The repaired test against the corrected application (criterion 4)");
    const rightAmounts = await amountsShown(CORRECTED_APP);
    const green = await runAgainst(CORRECTED_APP, {}, null);
    mutation.out(`What the corrected checkout shows: subtotal ${rightAmounts.subtotal}, discount ${rightAmounts.discount}, tax ${rightAmounts.tax}, total ${rightAmounts.total}, charged on the confirmation ${rightAmounts.charged}. Button: "${rightAmounts.button}".`,
      `The repaired test: ${shown(green)}. Tests that ran: ${green.ran}. Exit code: ${green.exit}.`);
    mutation.check("the corrected checkout shows subtotal £40.00, discount -£4.00, and the amounts the business rule then gives: tax £7.20, total £43.20, and £43.20 charged",
      rightAmounts.subtotal === "£40.00" && rightAmounts.discount === "-£4.00" && rightAmounts.tax === "£7.20" && rightAmounts.total === "£43.20" && rightAmounts.charged === "£43.20");
    mutation.check("the repaired test PASSES against the corrected application. One test ran, and the command's exit code is 0", green.status === "passed" && green.ran === 1 && green.exit === 0);
    const unrepaired = await runAgainst(CORRECTED_APP, {}, copyDir("before", before));
    mutation.out(`For contrast, the test as it was before the repair, against the same application: ${shown(unrepaired)}`);
    mutation.check("the test before the repair fails there, at line 8. So the repair is what makes it pass", unrepaired.status === "failed" && unrepaired.line === 8);

    mutation.part("PART 3. The business rule, broken on purpose, three ways (criterion 5)",
      "THE RULE (line 10 of the test): tax is 20% of what the customer pays for the goods, after the discount. 36.00 x 20% = 7.20.",
      "Each broken application is a copy of the corrected one with ONE line of its source changed, written to a scratch folder.",
      "The corrected application itself is never written to. What each copy shows on its page was read back before the test ran.");
    const mutantAmounts = await pool(mutantFiles.map((file) => () => amountsShown(file)));
    const mutantRuns = await pool(mutantFiles.map((file) => () => runAgainst(file, {}, null)));
    MUTANTS.forEach((mutant, index) => {
      const a = mutantAmounts[index];
      const run = mutantRuns[index];
      mutation.out("", `WAY ${index + 1}: ${mutant.title}.`, `  why this way: ${mutant.why}`, `  the line:  ${mutant.from.trim()}`, `  became:    ${mutant.to.trim()}`,
        `  the page then shows: subtotal ${a.subtotal}, discount ${a.discount}, tax ${a.tax}, total ${a.total}, charged ${a.charged}. Button: "${a.button}".`,
        `  the repaired test: ${shown(run)}. Tests that ran: ${run.ran}. Exit code: ${run.exit}.`);
      mutation.check(`way ${index + 1}: the page shows a tax or a total that the rule does not give. Every amount is still on the page as an amount, and the subtotal, the discount and the button are as they were`,
        (a.tax !== rightAmounts.tax || a.total !== rightAmounts.total) && [a.subtotal, a.discount, a.tax, a.total, a.charged].every((amount) => /^-?£\d+\.\d\d$/.test(amount))
        && a.subtotal === rightAmounts.subtotal && a.discount === rightAmounts.discount && a.button === rightAmounts.button);
      mutation.check(`way ${index + 1}: the repaired test FAILS, at line ${mutant.expectLine}, expecting ${mutant.expected} and receiving ${mutant.received}`,
        run.status === "failed" && run.ran === 1 && run.exit !== 0 && run.line === mutant.expectLine && run.message.includes(`"${mutant.expected}"`) && run.message.includes(`"${mutant.received}"`));
    });
    mutation.out("", "The three ways were chosen by the author of the test's repair, who knew what each would do. They are a demonstration and not a search.",
      "Ways that the test does not catch are in part 6.");

    mutation.part("PART 4. Controls: that a failure means the rule, and a pass means something");
    const harmlessAmounts = await amountsShown(harmless);
    const harmlessRun = await runAgainst(harmless, {}, null);
    mutation.out(`${HARMLESS.title}.`, `  the line:  ${HARMLESS.from.trim()}`, `  became:    ${HARMLESS.to.trim()}`, `  the page then shows: tax ${harmlessAmounts.tax}, total ${harmlessAmounts.total}, charged ${harmlessAmounts.charged}.`, `  the repaired test: ${shown(harmlessRun)}`);
    mutation.check("a change to the tax line that keeps the rule leaves the amounts right and the test passing. So the test does not fail merely because that line was touched or a copy was made",
      harmlessRun.status === "passed" && harmlessAmounts.tax === "£7.20" && harmlessAmounts.total === "£43.20" && harmlessAmounts.charged === "£43.20");
    const inUseRun = await runAgainst(IN_USE_APP, {}, null);
    mutation.out("", `The redesigned checkout in use, which has the fault the report found: ${shown(inUseRun)}`);
    mutation.check("against the checkout in use, uncorrected, the repaired test fails at line 11 expecting £7.20 and receiving £8.00, as the maintenance report predicted", inUseRun.status === "failed" && inUseRun.line === 11 && inUseRun.message.includes('"£7.20"') && inUseRun.message.includes('"£8.00"'));
    const emptyDir = join(scratch, "no-tests");
    mkdirSync(emptyDir);
    const none = await runAgainst(mutantFiles[0], {}, emptyDir);
    mutation.out("", `A run in which no test is found, with the rule broken: status "${none.status}", tests that ran: ${none.ran}.`);
    mutation.check("this program labels such a run \"no test ran\". Everywhere in this record, \"fails\" means that one test ran and its status was failed", none.status === "no test ran" && none.ran === 0);

    mutation.part("PART 5. Eight more faults, switched on in the corrected application by its harness switch",
      "These were already in the application from the earlier quest. The test before the repair is run against the checkout before the",
      "redesign. The repaired test is run against the corrected checkout.",
      "  fault                    the test before, old checkout    the repaired test, corrected checkout");
    const oldRuns = await pool(FAULTS.map((fault) => () => runAgainst(OLD_APP, { CHECKOUT_FAULT: fault }, copyDir("before", before))));
    const newRuns = await pool(FAULTS.map((fault) => () => runAgainst(CORRECTED_APP, { CHECKOUT_FAULT: fault }, null)));
    FAULTS.forEach((fault, index) => mutation.out(`  ${fault.padEnd(24)} ${(oldRuns[index].status === "failed" ? `caught at line ${oldRuns[index].line}` : "NOT CAUGHT").padEnd(32)} ${newRuns[index].status === "failed" ? `caught at line ${newRuns[index].line}` : "NOT CAUGHT"}`));
    const oldCaught = oldRuns.filter((r) => r.status === "failed").length;
    const newCaught = newRuns.filter((r) => r.status === "failed").length;
    mutation.check(`the test before the repair caught ${oldCaught} of 8, and the repaired test catches ${newCaught} of 8. Every fault caught before is caught after, and at the same line`,
      oldCaught === 8 && newCaught === 8 && FAULTS.every((fault, index) => oldRuns[index].line === FAULT_LINES[fault] && newRuns[index].line === FAULT_LINES[fault] && newRuns[index].ran === 1));

    mutation.part("PART 6. What the test does NOT catch: the rule broken in ways that give the right figures for this one basket",
      "Proposed by an independent reader of this program. The application has one basket and one discount, so the test checks the rule at one",
      "point: 40.00 of goods, 10% off. A fault that agrees with the rule at that point passes. Each is tried twice: the repaired test against",
      "the corrected checkout with the fault, and the test before the repair against the checkout before the redesign with the same fault.");
    const survivorNew = SURVIVORS.map((sv) => mutantApp(scratch, sv.name, sv.from, sv.to));
    const survivorOld = SURVIVORS.map((sv) => mutantApp(scratch, `old-${sv.name}`, sv.from, sv.to, OLD_APP));
    const survivorAmounts = await pool(survivorNew.map((file) => () => amountsShown(file)));
    const survivorRunsNew = await pool(survivorNew.map((file) => () => runAgainst(file, {}, null)));
    const survivorRunsOld = await pool(survivorOld.map((file) => () => runAgainst(file, {}, copyDir("before", before))));
    SURVIVORS.forEach((sv, index) => mutation.out("", `NOT CAUGHT ${index + 1}: ${sv.title}.`, `  the line:  ${sv.from.trim()}`, `  became:    ${sv.to.trim()}`,
      `  the page then shows: tax ${survivorAmounts[index].tax}, total ${survivorAmounts[index].total}, charged ${survivorAmounts[index].charged}.`,
      `  the repaired test: ${shown(survivorRunsNew[index])}. The test before the repair, old checkout, same fault: ${shown(survivorRunsOld[index])}.`));
    const survive = SURVIVORS.filter((_, index) => survivorRunsNew[index].status === "passed").length;
    mutation.check(`all ${SURVIVORS.length} of these broken rules get past the repaired test. This is recorded as a limit of the test, and is not a pass`, survive === SURVIVORS.length);
    mutation.check("every one of them got past the test before the repair as well. The repair did not open this gap: the test never guarded the rule beyond one basket", survivorRunsOld.every((run) => run.status === "passed"));

    mutation.part("PART 7. The contrast: the scenario's repair, which only checks that a number is shown",
      "The same three broken applications, and the test as the scenario's repair would have left it. Its text is weakened version 1 of logs/weakening-check.txt.");
    const scenarioDir = copyDir("scenario", WEAK[0].edit(after));
    const scenarioGreen = await runAgainst(CORRECTED_APP, {}, scenarioDir);
    const scenarioRuns = await pool(mutantFiles.map((file) => () => runAgainst(file, {}, scenarioDir)));
    mutation.out(`  against the corrected application: ${shown(scenarioGreen)}`, ...MUTANTS.map((mutant, index) => `  way ${index + 1}, ${mutant.name}: ${shown(scenarioRuns[index])}`));
    mutation.check("the scenario's repair passes against the corrected application and against all three broken ones. It is green, and the pricing bug passes unnoticed", scenarioGreen.status === "passed" && scenarioRuns.every((r) => r.status === "passed"));
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
  for (const log of [weak, mutation]) {
    log.part("AT THE END");
    log.out(`sha256 of the test before the repair:  ${sha(readFileSync(BEFORE_SPEC, "utf8"))}`, `sha256 of the repaired test:           ${sha(readFileSync(AFTER_SPEC, "utf8"))}`, `sha256 of the corrected checkout:      ${sha(readFileSync(CORRECTED_APP, "utf8"))}`);
    log.check("the test before the repair, the repaired test and the corrected checkout are each byte for byte what they were at the start, and the scratch folder is gone",
      readFileSync(BEFORE_SPEC, "utf8") === before && readFileSync(AFTER_SPEC, "utf8") === after && readFileSync(CORRECTED_APP, "utf8") === corrected && !existsSync(scratch));
  }
  weak.save(join(LOGS, "weakening-check.txt"));
  mutation.save(join(LOGS, "mutation-run.txt"));
  return weak.failed.length || mutation.failed.length ? 1 : 0;
}

process.exit(process.argv.includes("--write") ? write() : await main());

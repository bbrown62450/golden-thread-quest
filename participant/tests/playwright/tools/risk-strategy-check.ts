/*
 * The check for the playwright-risk-strategy quest.
 *
 *   node tools/risk-strategy-check.ts
 *
 * Node 22.18 or later. It reads two files and writes one log. It starts no application and no browser, and contacts
 * nothing. It can be run from any folder: it finds the files from where this file is.
 *
 *   reads    participant/context/playwright/requirements.md
 *            participant/context/playwright/strategy.md
 *   writes   logs/strategy-check.txt, in the attempt folder (the folder is made if it is not there)
 *
 * IT IS WRITTEN FOR THIS STRATEGY'S FORM, not for any strategy. The headings, the field names, the five layers, the
 * three words of importance and the ranking rule are fixed here. A strategy laid out another way would be reported
 * as wrong. The trials of PART 4 also depend on sentences of this strategy, and say so when one is not found.
 *
 * WHAT problems() TESTS, by the quest's criteria
 *   1. The requirements file has one table under "The requirements", of at least eight rows, each with an identifier,
 *      one of three words of importance (not all the same) and at least four words. Anything in the file that looks
 *      like a requirement's identifier (REQ-13, REQ 13, Req-13a) must be a row of that table. A requirement written
 *      with no identifier at all is not seen. Every requirement is named by at least one risk, and no risk names one
 *      that does not exist. Section 6 lists every requirement once, with its importance and the risks, the layers and
 *      the untested risks that the risk blocks give for it, and nothing else in those cells.
 *   2. The two scales can be read, each clause's name agrees with its level, and none is given twice. Each risk gives
 *      a likelihood and an impact that are levels of those scales, each with a clause of that scale whose level is
 *      the one given, followed by at least four words. Its score is the two multiplied.
 *   3. Anything in the strategy that looks like a risk's identifier (R-20, R20, Risk 20) is a risk with its own
 *      heading in section 3. Nothing is written in section 3 before its first risk. Every line of a risk's block is
 *      one of its nine fields, written "- Name: value" on one line, each once. So a second line about a layer inside
 *      a block is reported, however it is written. A layer mentioned inside another field's sentence is not seen.
 *      The layer is one of unit, API, UI, manual, none. Each risk has a title of at least three words.
 *   4. Each risk has a reason for its layer of at least 15 words that no other risk has letter for letter, a cheapest
 *      test that would fail of at least 8 words, and a line saying what must exist first.
 *   5. Each risk says whether it needs a browser, and that agrees with its layer: unit, API and none do not, UI and
 *      manual do. That is fixed here and compared with the strategy's table of layers. Section 4 lists the two
 *      groups with their numbers, and the sentence counting the risks to be tested is there.
 *   6. The risks whose layer is "none" are exactly the rows of section 5's one table. Each row has seven cells: a
 *      reason of at least 8 words, what is done instead, a calendar date, and an "Accepted by" that is, letter for
 *      letter, the one the REQUIREMENTS file says can accept a risk. Section 5 repeats that line.
 *   7. Section 1 contains the score rule and the rule for equal scores in the words this program works by, and the
 *      sentence saying the higher level is taken. The ranked table of section 2, its one table, is what this program
 *      gets by working the ranking out again from the blocks and the requirements' importance.
 *   Also: section 7's one table has a row for each of the four test layers, listing the risks the blocks give it.
 *
 * WHAT IT CANNOT TEST
 *   Whether a likelihood or an impact is the right one, whether a layer is the cheapest that would catch the risk,
 *   or whether a reason is a good one. It counts words. It cannot weigh them. Those are for a person to read.
 *   Whether the higher level was taken where two clauses apply. It checks that the rule is stated, not that it was
 *   followed.
 *   Whether the one named as accepting a risk is a person, did accept it, or did so on that date. It compares two
 *   pieces of text.
 *   Whether a risk given to a test layer will ever be tested. A risk nobody means to test can be labelled "manual"
 *   and this check will not know. No test in the strategy exists: it is a plan.
 *   Whether a risk is missing altogether, or a sentence elsewhere in the document contradicts one it has checked.
 *   Text inside a comment or a code block is read like any other.
 */

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TESTS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PARTICIPANT = resolve(TESTS, "..", "..");
const REPO = resolve(PARTICIPANT, "..");
const ATTEMPT = join(PARTICIPANT, "evidence", "playwright-risk-strategy", "playwright-attempt-008");
const REQUIREMENTS = join(PARTICIPANT, "context", "playwright", "requirements.md");
const STRATEGY = join(PARTICIPANT, "context", "playwright", "strategy.md");
const IMPORTANCE = ["must", "should", "could"];   // in order: the first is the most important
const BROWSER: Record<string, string> = { unit: "no", API: "no", UI: "yes", manual: "yes", none: "no" };
const LAYERS = Object.keys(BROWSER);
const FIELDS = ["Requirement", "Likelihood", "Impact", "Score", "Layer", "Needs a browser", "Needs first", "Cheapest test that would fail", "Reason for the layer"];
const SCORE_RULE = "**Score = likelihood × impact.** The risks are ranked by score, highest first.";
const TIE_RULE = "**Equal scores are ordered by impact, highest first; then by the importance of the risk's most important requirement, must before should before could; then by risk number, lowest first.**";
const HIGHER_RULE = "**Where clauses of two levels both\napply, the higher level is taken**, on both scales.";

const sha = (data: string | Buffer) => createHash("sha256").update(data).digest("hex");
const tidy = (text: string) => text.split(REPO + "/").join("").split(REPO).join("REPO");
const words = (text: string) => text.split(/\s+/).filter((word) => /[A-Za-z0-9]/.test(word)).length;
const ids = (text: string, kind: "REQ" | "R") => [...text.matchAll(kind === "REQ" ? /\bREQ-\d+\b/g : /(?<![A-Za-z-])R-\d+\b/g)].map((m) => m[0]);
/** Anything that looks like an identifier, however it is written: REQ-13, REQ 13, Req-13a; R-20, R20, Risk 20. */
const looksLike = (text: string, kind: "REQ" | "R") => [...text.matchAll(kind === "REQ" ? /\bREQ[- ]?\d+[A-Za-z]?\b/gi : /(?<![A-Za-z-])(?:R|Risk)[- ]?\d+[A-Za-z]?\b/gi)].map((m) => m[0]);
const onlyIds = (cell: string, kind: "REQ" | "R") => (kind === "REQ" ? /^(REQ-\d+(, REQ-\d+)*)?$/ : /^(R-\d+(, R-\d+)*)?$/).test(cell.trim());
const tables = (text: string) => text.split("\n").filter((line, index, all) => line.trim().startsWith("|") && !(all[index - 1] ?? "").trim().startsWith("|")).length;
const same = (a: string[], b: string[]) => a.length === b.length && [...a].sort().every((value, index) => value === [...b].sort()[index]);
const list = (cell: string) => cell.split(",").map((part) => part.trim()).filter(Boolean);

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

// ---------------------------------------------------------------- reading the two documents

/** The rows of every table in a piece of Markdown, without each table's heading row and its row of dashes. */
function tableRows(text: string): string[][] {
  const rows: string[][] = [];
  let inTable = 0;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line.startsWith("|")) { inTable = 0; continue; }
    inTable += 1;
    if (inTable > 2) rows.push(line.slice(1, line.endsWith("|") ? -1 : undefined).split("|").map((cell) => cell.trim()));
  }
  return rows;
}

/** The text under a heading, up to the next heading of the same depth or less. "" if the heading is not there, or is there twice. */
function under(text: string, heading: string): string {
  const depth = heading.match(/^#+/)?.[0].length ?? 2;
  const lines = text.split("\n");
  const at = lines.map((line, index) => (line.startsWith(heading) ? index : -1)).filter((index) => index >= 0);
  if (at.length !== 1) return "";
  const rest = lines.slice(at[0] + 1);
  const end = rest.findIndex((line) => { const m = line.match(/^(#+) /); return m !== null && m[1].length <= depth; });
  return (end < 0 ? rest : rest.slice(0, end)).join("\n");
}

type Requirement = { id: string; importance: string; text: string };
type Risk = { id: string; title: string; fields: Map<string, string[]>; stray: string[] };
type Clause = { level: number; clause: string };
type Worked = { id: string; requirements: string[]; likelihood: number; impact: number; score: number; layer: string; importance: number };

const readRequirements = (text: string): Requirement[] =>
  tableRows(under(text, "## The requirements")).map((cells) => ({ id: cells[0] ?? "", importance: cells[1] ?? "", text: cells[2] ?? "" }));

function readRisks(strategy: string): Risk[] {
  return under(strategy, "## 3. ").split(/^### /m).slice(1).map((block) => {
    const [head, ...rest] = block.split("\n");
    const fields = new Map<string, string[]>();
    const stray: string[] = [];
    for (const line of rest) {
      if (!line.trim()) continue;
      const m = line.match(/^- ([A-Za-z ]+): (.+)$/);
      if (m && FIELDS.includes(m[1])) fields.set(m[1], [...(fields.get(m[1]) ?? []), m[2].trim()]);
      else stray.push(line.trim());
    }
    return { id: head.match(/^(R-\d+)\. /)?.[1] ?? head.trim(), title: head.replace(/^R-\d+\.\s*/, "").trim(), fields, stray };
  });
}

const field = (risk: Risk, name: string) => risk.fields.get(name)?.[0] ?? "";
const readClauses = (strategy: string, heading: string): Clause[] =>
  tableRows(under(under(strategy, "## 1. "), heading)).map((cells) => ({ level: Number(cells[0]), clause: cells[1] ?? "" }));

/** A level and its clause from a line such as "3 (L3a). It has happened here". */
function levelOf(value: string): { level: number; clause: string; ground: string } | null {
  const m = value.match(/^(\d+) \(([LI]\d[a-z])\)\.\s*(.*)$/);
  return m ? { level: Number(m[1]), clause: m[2], ground: m[3] } : null;
}

/** What the blocks give for each risk whose numbers can be read. Importance is that of its most important requirement: 0 is must. */
function workOut(risks: Risk[], requirements: Requirement[]): Worked[] {
  const out: Worked[] = [];
  for (const risk of risks) {
    const l = levelOf(field(risk, "Likelihood")), i = levelOf(field(risk, "Impact"));
    if (!l || !i || !/^R-\d+$/.test(risk.id)) continue;
    const named = ids(field(risk, "Requirement"), "REQ");
    const ranks = named.map((id) => IMPORTANCE.indexOf(requirements.find((r) => r.id === id)?.importance ?? "")).filter((rank) => rank >= 0);
    out.push({ id: risk.id, requirements: named, likelihood: l.level, impact: i.level, score: l.level * i.level, layer: field(risk, "Layer"), importance: ranks.length ? Math.min(...ranks) : IMPORTANCE.length });
  }
  return out;
}

/** The ranking rule of section 1, as TIE_RULE words it. */
const ranked = (worked: Worked[]) =>
  [...worked].sort((a, b) => b.score - a.score || b.impact - a.impact || a.importance - b.importance || Number(a.id.slice(2)) - Number(b.id.slice(2)));

function realDate(text: string): boolean {
  if (!/^\d{4}-\d\d-\d\d$/.test(text)) return false;
  const date = new Date(text + "T00:00:00Z");
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === text;
}

// ---------------------------------------------------------------- the rules

/** Every way the two documents fall short of the rules at the top of this file. Sorted, so the order is always the same. */
function problems(requirementsIn: string, strategyIn: string): string[] {
  const requirementsText = requirementsIn.replace(/\r\n/g, "\n"), strategy = strategyIn.replace(/\r\n/g, "\n");
  const found = new Set<string>();
  const say = (problem: string) => found.add(problem);
  const requirements = readRequirements(requirementsText);
  const risks = readRisks(strategy);
  const likelihoods = readClauses(strategy, "### Likelihood"), impacts = readClauses(strategy, "### Impact");
  const known = requirements.map((r) => r.id);

  // The requirements themselves.
  if (requirements.length < 8) say(`The requirements file has ${requirements.length} requirements in its tables, and the quest asks for at least eight.`);
  for (const r of requirements) {
    if (!/^REQ-\d+$/.test(r.id)) say(`A row of the requirements has "${r.id}" where an identifier belongs.`);
    if (!IMPORTANCE.includes(r.importance)) say(`${r.id} has the importance "${r.importance}", which is not one of ${IMPORTANCE.join(", ")}.`);
    if (known.filter((id) => id === r.id).length > 1) say(`${r.id} is in the requirements more than once.`);
    if (words(r.text) < 4) say(`${r.id} has a requirement of ${words(r.text)} words.`);
  }
  if (new Set(requirements.map((r) => r.importance)).size < 2) say("The requirements all have the same importance.");
  for (const id of new Set(looksLike(requirementsText, "REQ"))) if (!known.includes(id)) say(`The requirements file mentions ${id}, which is not a row of its table under "The requirements".`);
  if (tables(under(requirementsText, "## The requirements")) !== 1) say(`The requirements file has ${tables(under(requirementsText, "## The requirements"))} tables under "The requirements", and one is needed.`);
  const mayAccept = requirementsText.match(/^Who can accept a risk: (.+)\.$/m)?.[1] ?? "";
  if (words(mayAccept) < 4) say("The requirements file does not say who can accept a risk, in at least four words.");

  // The scales, the rules and the layers.
  const section1 = under(strategy, "## 1. ");
  for (const [name, scale] of [["likelihood", likelihoods], ["impact", impacts]] as const) {
    if (!scale.length) say(`Section 1 has no scale of ${name} that can be read.`);
    for (const c of scale) if (!Number.isInteger(c.level) || !/^[LI]\d[a-z]$/.test(c.clause) || Number(c.clause[1]) !== c.level) say(`The scale of ${name} has the clause "${c.clause}" at level "${c.level}", and the two do not agree.`);
    if (new Set(scale.map((c) => c.clause)).size !== scale.length) say(`The scale of ${name} gives one clause twice.`);
  }
  const layerRows = tableRows(under(section1, "### Layers"));
  if (!same(layerRows.map((cells) => cells[0]), LAYERS)) say(`The table of layers in section 1 does not have one row each for ${LAYERS.join(", ")}.`);
  for (const cells of layerRows) if (cells[0] in BROWSER && Object.hasOwn(BROWSER, cells[0]) && cells[2] !== BROWSER[cells[0]]) say(`The table of layers says "${cells[2]}" to whether ${cells[0]} needs a browser, and it is ${BROWSER[cells[0]]}.`);
  if (!section1.includes(SCORE_RULE)) say("Section 1 does not state the score as likelihood × impact, in the words this check works by.");
  if (!section1.includes(TIE_RULE)) say("Section 1 does not state the order of equal scores in the words this check works by: impact, then importance, then risk number.");
  if (!section1.includes(HIGHER_RULE)) say("Section 1 does not say which level is taken when clauses of two levels apply.");

  // Each risk.
  if (!risks.length) say("Section 3 has no risk that can be read.");
  const riskIds = risks.map((r) => r.id);
  for (const id of new Set(looksLike(strategy, "R"))) if (!riskIds.includes(id)) say(`The strategy mentions ${id}, which is not a risk with its own heading in section 3.`);
  for (const id of new Set(looksLike(strategy, "REQ"))) if (!known.includes(id)) say(`The strategy mentions ${id}, which is not in the requirements.`);
  if (under(strategy, "## 3. ").split(/^### /m)[0].trim()) say("Section 3 has text before its first risk, where nothing belongs to any risk.");
  for (const [section, name] of [["## 2. ", "2"], ["## 5. ", "5"], ["## 6. ", "6"], ["## 7. ", "7"]]) if (tables(under(strategy, section)) !== 1) say(`Section ${name} has ${tables(under(strategy, section))} tables, and one is needed.`);
  const reasons = new Map<string, string>();
  for (const risk of risks) {
    if (!/^R-\d+$/.test(risk.id)) { say(`A risk in section 3 is headed "${risk.id.slice(0, 40)}", which is not an identifier, a full stop and a title.`); continue; }
    if (riskIds.filter((id) => id === risk.id).length > 1) say(`${risk.id} is in section 3 more than once.`);
    if (words(risk.title) < 3) say(`${risk.id} has a title of ${words(risk.title)} words.`);
    for (const line of risk.stray) say(`${risk.id} has a line that is not one of its fields, written "- Name: value" on one line: "${line.slice(0, 50)}".`);
    for (const name of FIELDS) {
      const got = risk.fields.get(name)?.length ?? 0;
      if (got !== 1) say(`${risk.id} has ${got} lines giving ${name === "Layer" ? "a layer" : `"${name}"`}, and one is needed.`);
    }
    const requirement = field(risk, "Requirement");
    if (!/^REQ-\d+(, REQ-\d+)*$/.test(requirement)) say(`${risk.id} does not give its requirement as identifiers with commas between them, and nothing else.`);
    const levels: Record<string, number> = {};
    for (const [name, scale, letter] of [["Likelihood", likelihoods, "L"], ["Impact", impacts, "I"]] as const) {
      const lower = name.toLowerCase();
      const got = levelOf(field(risk, name));
      if (!got) { say(`${risk.id} does not give its ${lower} as a level and a clause, such as "2 (${letter}2a)."`); continue; }
      levels[name] = got.level;
      if (!scale.some((c) => c.level === got.level)) say(`${risk.id} gives a ${lower} of ${got.level}, which is not a level of the scale.`);
      const clause = scale.find((c) => c.clause === got.clause);
      if (!clause) say(`${risk.id} rests its ${lower} on the clause ${got.clause}, which is not in the scale of ${lower}.`);
      else if (clause.level !== got.level) say(`${risk.id} gives a ${lower} of ${got.level} and rests it on the clause ${got.clause}, which is of level ${clause.level}.`);
      if (words(got.ground) < 4) say(`${risk.id} follows the clause of its ${lower} with ${words(got.ground)} words, and at least 4 are needed.`);
    }
    const score = field(risk, "Score");
    if ("Likelihood" in levels && "Impact" in levels && score !== String(levels["Likelihood"] * levels["Impact"])) say(`${risk.id} gives a score of ${score || "nothing"}, which is not ${levels["Likelihood"]} × ${levels["Impact"]}.`);
    const layer = field(risk, "Layer");
    const knownLayer = LAYERS.includes(layer);
    if (risk.fields.get("Layer")?.length === 1 && !knownLayer) say(`${risk.id} has the layer "${layer.slice(0, 30)}", which is not one of ${LAYERS.join(", ")}.`);
    const browser = field(risk, "Needs a browser");
    if (browser !== "yes" && browser !== "no") say(`${risk.id} does not say yes or no to whether it needs a browser.`);
    else if (knownLayer && BROWSER[layer] !== browser) say(`${risk.id} says ${browser} to needing a browser, and its layer, ${layer}, is one that ${BROWSER[layer] === "yes" ? "needs one" : "needs none"}.`);
    const reason = field(risk, "Reason for the layer");
    if (words(reason) < 15) say(`${risk.id} gives a reason for its layer of ${words(reason)} word${words(reason) === 1 ? "" : "s"}, and at least 15 are needed: a label is not a reason.`);
    else if (reasons.has(reason)) say(`${risk.id} gives the same reason for its layer, letter for letter, as ${reasons.get(reason)}.`);
    else reasons.set(reason, risk.id);
    if (words(field(risk, "Cheapest test that would fail")) < 8) say(`${risk.id} describes its cheapest test that would fail in ${words(field(risk, "Cheapest test that would fail"))} words, and at least 8 are needed.`);
    if (words(field(risk, "Needs first")) < 1) say(`${risk.id} does not say what must exist before its test can be written.`);
  }
  const worked = workOut(risks, requirements);

  // Criterion 1: every requirement is covered.
  for (const id of known) if (!worked.some((w) => w.requirements.includes(id))) say(`${id} is named by no risk, so the strategy neither covers it nor lists it as untested.`);
  const coverage = tableRows(under(strategy, "## 6. "));
  for (const id of known) {
    const rows = coverage.filter((cells) => cells[0] === id);
    if (rows.length !== 1) { say(`Section 6 has ${rows.length} rows for ${id}, and one is needed.`); continue; }
    const mine = worked.filter((w) => w.requirements.includes(id));
    if (!onlyIds(rows[0][2] ?? "", "R") || !onlyIds(rows[0][4] ?? "", "R")) say(`Section 6 has something other than risk identifiers and commas in a cell for ${id}.`);
    if (!same(ids(rows[0][2] ?? "", "R"), mine.map((w) => w.id))) say(`Section 6 does not give for ${id} the risks whose blocks name it.`);
    if (!same(list(rows[0][3] ?? ""), [...new Set(mine.filter((w) => w.layer !== "none").map((w) => w.layer))])) say(`Section 6 does not give for ${id} the layers its risks are tested at.`);
    if (!same(ids(rows[0][4] ?? "", "R"), mine.filter((w) => w.layer === "none").map((w) => w.id))) say(`Section 6 does not give for ${id} the risks that are left untested.`);
    if ((rows[0][1] ?? "") !== requirements.find((r) => r.id === id)?.importance) say(`Section 6 gives ${id} an importance that is not the one in the requirements.`);
  }
  for (const cells of coverage) if (!known.includes(cells[0])) say(`Section 6 has a row for "${cells[0]}", which is not in the requirements.`);

  // Criterion 5: the two groups, and the count of tested risks.
  const section4 = under(strategy, "## 4. ");
  for (const [label, want] of [["Need a browser", "yes"], ["Do not need a browser", "no"]] as const) {
    const line = section4.split("\n").find((l) => l.startsWith(`**${label} (`)) ?? "";
    const listed = ids(line.replace(/^\*\*[^*]*\*\*/, ""), "R");
    if (!/^\*\*[^*]*\*\* R-\d+(, R-\d+)*\.$/.test(line)) say(`Section 4's line for "${label}" is not the label, risk identifiers with commas between them, and a full stop.`);
    const mine = risks.filter((r) => field(r, "Needs a browser") === want).map((r) => r.id);
    if (!same(listed, mine)) say(`Section 4 does not list under "${label}" exactly the risks whose blocks say ${want}.`);
    if (Number(line.match(/\((\d+)\)/)?.[1] ?? -1) !== mine.length) say(`Section 4 does not give, for "${label}", the number of risks whose blocks say ${want}: ${mine.length}.`);
  }
  const tested = worked.filter((w) => w.layer !== "none");
  const sentence = `Of the ${tested.length} risks that are to be tested, ${tested.filter((w) => BROWSER[w.layer] === "no").length} are to be tested without a browser.`;
  if (!section4.includes(sentence)) say(`Section 4 does not say: "${sentence}"`);

  // Criterion 6: what is left untested.
  const section5 = under(strategy, "## 5. ");
  const acceptor = section5.match(/^Who can accept a risk: (.+)\.$/m)?.[1] ?? "";
  if (!acceptor || acceptor !== mayAccept) say("Section 5 does not say who can accept a risk in the words the requirements file uses.");
  const untested = tableRows(section5);
  const none = worked.filter((w) => w.layer === "none");
  for (const w of none) if (untested.filter((cells) => cells[0] === w.id).length !== 1) say(`${w.id} has the layer none and does not have one row in section 5.`);
  for (const cells of untested) {
    const [id, requirement, score, why, instead, acceptedBy, on] = cells;
    if (cells.length !== 7) say(`A row of section 5, for "${id}", has ${cells.length} cells, and seven are needed.`);
    if (words(instead ?? "") < 1) say(`Section 5 does not say what is done instead of testing ${id}.`);
    const w = worked.find((x) => x.id === id);
    if (!w) { say(`Section 5 has a row for "${id}", which is not a risk of section 3 with levels that can be read.`); continue; }
    if (w.layer !== "none") say(`${id} is in section 5 as untested, and its layer is ${w.layer}.`);
    if (!same(ids(requirement ?? "", "REQ"), w.requirements)) say(`Section 5 gives ${id} requirements that are not its block's.`);
    if (score !== String(w.score)) say(`Section 5 gives ${id} a score of ${score}, and its block gives ${w.score}.`);
    if (words(why ?? "") < 8) say(`Section 5 gives ${words(why ?? "")} words for why ${id} is not tested, and at least 8 are needed.`);
    if (!mayAccept || (acceptedBy ?? "") !== mayAccept) say(`Section 5 does not give, as the one who accepted ${id}, the person it says can accept a risk: it says "${acceptedBy ?? ""}".`);
    if (!realDate(on ?? "")) say(`Section 5 gives no calendar date on which ${id} was accepted: it says "${on ?? ""}".`);
  }

  // Criterion 7: the ranking, worked out again.
  const table = tableRows(under(strategy, "## 2. "));
  const order = ranked(worked);
  if (table.length !== risks.length) say(`Section 2 has ${table.length} rows, and section 3 has ${risks.length} risks.`);
  if (!same(table.map((cells) => cells[1]), riskIds)) say("Section 2 does not name each risk of section 3 once.");
  order.forEach((w, index) => {
    const cells = table[index];
    if (!cells) return;
    if (cells[0] !== String(index + 1)) say(`Row ${index + 1} of section 2 is numbered "${cells[0]}".`);
    if (cells[1] !== w.id) { say(`By the scales and the ranking rule, rank ${index + 1} is ${w.id} (${w.likelihood} × ${w.impact} = ${w.score}, ${IMPORTANCE[w.importance] ?? "no importance"}). Section 2 has ${cells[1]} there.`); return; }
    if (cells[3] !== String(w.likelihood) || cells[4] !== String(w.impact) || cells[5] !== String(w.score)) say(`Section 2 gives ${w.id} a likelihood, an impact or a score that is not its block's.`);
    if (cells[6] !== w.layer) say(`Section 2 gives ${w.id} the layer ${cells[6]}, and its block says ${w.layer}.`);
    if (!same(ids(cells[2] ?? "", "REQ"), w.requirements) || !onlyIds(cells[2] ?? "", "REQ")) say(`Section 2 gives ${w.id} requirements that are not its block's.`);
  });

  // Section 7: each layer's risks.
  const timing = tableRows(under(strategy, "## 7. "));
  if (!same(timing.map((cells) => cells[0]), LAYERS.filter((name) => name !== "none"))) say("Section 7 does not have one row each for unit, API, UI and manual, and no other.");
  for (const layer of LAYERS.filter((name) => name !== "none")) {
    const rows = timing.filter((cells) => cells[0] === layer);
    if (rows.length !== 1 || !same(ids(rows[0][1] ?? "", "R"), worked.filter((w) => w.layer === layer).map((w) => w.id)) || !(onlyIds(rows[0][1] ?? "", "R") || rows[0][1] === "none")) say(`Section 7 does not list for the ${layer} layer exactly the risks whose blocks give that layer.`);
  }
  return [...found].sort();
}

// ---------------------------------------------------------------- the run

function main(): number {
  const log = new Log("The strategy check. playwright-risk-strategy, attempt playwright-attempt-008",
    "Recorded by participant/tests/playwright/tools/risk-strategy-check.ts. It read two files. It started no application and no browser.",
    "The shop, its requirements and its rules are made up. Paths are from the repository's top folder.");
  let requirementsText = "", strategy = "";
  try {
    requirementsText = readFileSync(REQUIREMENTS, "utf8").replace(/\r\n/g, "\n");
    strategy = readFileSync(STRATEGY, "utf8").replace(/\r\n/g, "\n");
  } catch (error) {
    log.check(`both documents can be read: ${error instanceof Error ? error.message : "an error"}`, false);
    log.save(join(ATTEMPT, "logs", "strategy-check.txt"));
    return 1;
  }
  const before = [sha(readFileSync(REQUIREMENTS)), sha(readFileSync(STRATEGY))];
  const requirements = readRequirements(requirementsText), risks = readRisks(strategy), worked = workOut(risks, requirements);

  log.part("PART 1. The two documents");
  log.out(`participant/context/playwright/requirements.md  sha256 ${before[0]}`, `participant/context/playwright/strategy.md      sha256 ${before[1]}`, "",
    `Requirements read: ${requirements.length}. ${IMPORTANCE.map((word) => `${word}: ${requirements.filter((r) => r.importance === word).length}`).join(". ")}.`,
    `Risks read from section 3: ${risks.length}. By layer: ${LAYERS.map((layer) => `${layer} ${worked.filter((w) => w.layer === layer).length}`).join(", ")}.`);

  log.part("PART 2. The check of the handed-in strategy against the handed-in requirements", "This is the one check of the handed-in documents. What problems() tests, and what it cannot, is at the top of the program.");
  const found = problems(requirementsText, strategy);
  log.out(...(found.length ? found.map((problem) => `  PROBLEM: ${problem}`) : ["  No problem found."]), "");
  log.check("the check finds no problem in the two documents", found.length === 0);

  log.part("PART 3. What the check worked out, for a reader", "Made by this program from the risk blocks of section 3 and the requirements. These lists are not further checks.", "They are here so that a person can compare them with the strategy's own tables, as PART 2 has.");
  log.out("Criterion 1. Each requirement, the risks that name it, and where they are tested:");
  for (const r of requirements) {
    const mine = worked.filter((w) => w.requirements.includes(r.id));
    log.out(`  ${r.id}  ${r.importance.padEnd(6)}  ${mine.map((w) => `${w.id} ${w.layer === "none" ? "UNTESTED" : w.layer}`).join(", ") || "NAMED BY NO RISK"}`);
  }
  log.out("", "Criteria 2 and 7. The ranking worked out again: score = likelihood × impact, then impact, then importance, then risk number:");
  ranked(worked).forEach((w, index) => log.out(`  ${String(index + 1).padStart(2)}  ${w.id}  ${w.likelihood} × ${w.impact} = ${w.score}  ${(IMPORTANCE[w.importance] ?? "?").padEnd(6)}  ${w.layer}`));
  log.out("", "Criteria 3 and 4. For each risk: lines giving a layer, lines that are not a field, and the words in its reason and in its cheapest test:");
  for (const risk of risks) log.out(`  ${risk.id}  layer lines: ${risk.fields.get("Layer")?.length ?? 0} (${field(risk, "Layer")})  other lines: ${risk.stray.length}  reason: ${words(field(risk, "Reason for the layer"))} words  cheapest test: ${words(field(risk, "Cheapest test that would fail"))} words`);
  const needs = risks.filter((risk) => field(risk, "Needs a browser") === "yes").map((risk) => risk.id), needsNot = risks.filter((risk) => field(risk, "Needs a browser") === "no").map((risk) => risk.id);
  log.out("", `Criterion 5. Need a browser (${needs.length}): ${needs.join(", ")}.`, `             Do not (${needsNot.length}): ${needsNot.join(", ")}.`);
  const rows = tableRows(under(strategy, "## 5. "));
  log.out("", "Criterion 6. Risks whose layer is none, and the row section 5 has for each:");
  for (const w of worked.filter((x) => x.layer === "none")) { const row = rows.find((cells) => cells[0] === w.id); log.out(`  ${w.id}  score ${w.score}  accepted by: ${row?.[5] || "NOBODY NAMED"}  on: ${row?.[6] || "NO DATE"}  reason: ${words(row?.[3] ?? "")} words`); }

  log.part("PART 4. That this check can fail", "Each of these is the two handed-in documents with one thing changed, in memory. Nothing is written.", "The problem each trial is for is printed first, then up to two others the same change caused.");
  const spoil = (label: string, expect: string, change: (text: string) => string, inRequirements = false) => {
    const original = inRequirements ? requirementsText : strategy;
    const changed = change(original);
    const got = inRequirements ? problems(changed, strategy) : problems(requirementsText, changed);
    const fresh = got.filter((problem) => !found.includes(problem));
    const hit = fresh.filter((problem) => problem.includes(expect));
    log.out(`Spoiled: ${label}`, ...(changed !== original ? [] : ["    THE TEXT TO SPOIL WAS NOT FOUND"]), ...(fresh.length ? [...hit, ...fresh.filter((problem) => !hit.includes(problem))].slice(0, 3).map((problem) => `    PROBLEM: ${problem}`) : ["    no new problem reported"]));
    log.check(`reported: "${expect}"`, changed !== original && hit.length > 0);
  };
  const swap = (old: string, next: string) => (text: string) => (text.split(old).length === 2 ? text.replace(old, next) : text);
  const row = (id: string, cells: (cells: string[]) => string[], section: string, column = 0) => (text: string) => {
    const line = under(text, section).split("\n").find((l) => l.startsWith("|") && l.slice(1).split("|")[column]?.trim() === id);
    return line && text.split(line).length === 2 ? text.replace(line, "| " + cells(line.slice(1, -1).split("|").map((c) => c.trim())).join(" | ") + " |") : text;
  };
  const drop = (pattern: RegExp) => (text: string) => text.replace(pattern, "");
  const R12 = "- Layer: unit\n- Needs a browser: no\n- Needs first: the formatting function moved";
  const R10 = "- Layer: UI\n- Needs a browser: yes\n- Needs first: nothing for the press";
  const R06 = "- Layer: API\n- Needs a browser: no\n- Needs first: nothing for the demo as it is";

  log.out("", "-- The requirements");
  spoil("a thirteenth requirement added to the table, which no risk names", "REQ-13 is named by no risk", swap("| REQ-12 |", "| REQ-13 | should | A receipt is sent by email | no |\n| REQ-12 |"), true);
  spoil("a thirteenth requirement added after a blank line under the table, where it is not read as a row", "mentions REQ-13, which is not a row of its table", (text) => text.replace(/(\| REQ-12 \|[^\n]*\n)/, "$1\n| REQ-13 | must | A refund returns the amount that was taken | no |\n"), true);
  spoil("a thirteenth requirement written as a sentence, outside any table", "mentions REQ-13, which is not a row of its table", (text) => text + "\nREQ-13: a refund returns the amount that was taken.\n", true);
  spoil("five requirements taken out", "and the quest asks for at least eight", drop(/^\| REQ-0[1-5] \|[^\n]*\n/gm), true);
  spoil("a requirement given the importance \"vital\"", "REQ-11 has the importance \"vital\"", swap("| REQ-11 | could |", "| REQ-11 | vital |"), true);
  spoil("a requirement given twice", "REQ-12 is in the requirements more than once", (text) => text.replace(/(\| REQ-12 \|[^\n]*\n)/, "$1$1"), true);
  spoil("a requirement moved from should to could, with the strategy left as it was", "Section 6 gives REQ-09 an importance that is not the one in the requirements", swap("| REQ-09 | should |", "| REQ-09 | could |"), true);

  log.out("", "-- Criterion 1: every requirement");
  spoil("the only risks that name REQ-12 made to name REQ-11", "REQ-12 is named by no risk", swap("- Requirement: REQ-12", "- Requirement: REQ-11"));
  spoil("a risk made to name a requirement that does not exist", "mentions REQ-99, which is not in the requirements", swap("- Requirement: REQ-01\n", "- Requirement: REQ-99\n"));
  spoil("a requirement named only in a remark after another", "does not give its requirement as identifiers with commas between them", swap("- Requirement: REQ-05\n", "- Requirement: REQ-05 (REQ-12 is out of scope here)\n"));
  spoil("section 6 made to say REQ-11 is tested at the UI layer", "Section 6 does not give for REQ-11 the layers", row("REQ-11", (c) => [c[0], c[1], c[2], "UI", c[4]], "## 6. "));
  spoil("a risk taken out of section 6's row for REQ-04", "Section 6 does not give for REQ-04 the risks whose blocks name it", row("REQ-04", (c) => [c[0], c[1], "R-04, R-06, R-09", c[3], c[4]], "## 6. "));
  spoil("an untested risk not shown as untested in section 6", "Section 6 does not give for REQ-03 the risks that are left untested", row("REQ-03", (c) => [c[0], c[1], c[2], c[3], ""], "## 6. "));
  spoil("a row of section 6 taken out", "Section 6 has 0 rows for REQ-10", drop(/^\| REQ-10 \| should \|[^\n]*\n/m));

  log.out("", "-- Criterion 2: likelihood and impact on the stated scales");
  spoil("a likelihood of 5", "gives a likelihood of 5, which is not a level of the scale", swap("- Likelihood: 2 (L2a). The sum has cases", "- Likelihood: 5 (L2a). The sum has cases"));
  spoil("a likelihood of 3 resting on a clause of level 2", "rests it on the clause L2a, which is of level 2", swap("- Likelihood: 3 (L3a). It has happened here", "- Likelihood: 3 (L2a). It has happened here"));
  spoil("an impact resting on a clause that is not in the scale", "which is not in the scale of impact", swap("- Impact: 2 (I2b). A penny or two", "- Impact: 2 (I2z). A penny or two"));
  spoil("an impact with nothing after its clause", "follows the clause of its impact with 0 words", swap("- Impact: 1 (I1a). A wait. The order and the money are right.", "- Impact: 1 (I1a)."));
  spoil("an impact given as a word, with no clause", "does not give its impact as a level and a clause", swap("- Impact: 2 (I2a). A discount shown as a positive amount", "- Impact: low. A discount shown as a positive amount"));
  spoil("a score that is not the two multiplied", "gives a score of 8, which is not 3 × 3", swap("- Score: 9\n- Layer: unit\n- Needs a browser: no\n- Needs first: the same function as R-01.\n", "- Score: 8\n- Layer: unit\n- Needs a browser: no\n- Needs first: the same function as R-01.\n"));
  spoil("a clause of the scale moved to another level", "and the two do not agree", swap("| 3 | L3b |", "| 2 | L3b |"));
  spoil("a clause of the scale given twice", "The scale of impact gives one clause twice", swap("| 2 | I2b |", "| 2 | I2a |"));

  log.out("", "-- Criterion 3: one layer for each risk");
  spoil("a second layer line, written the same way", "has 2 lines giving a layer", swap(R06, R06.replace("- Layer: API\n", "- Layer: API\n- Layer: UI\n")));
  spoil("a second layer line, written with a star", "has a line that is not one of its fields", swap(R06, R06.replace("- Layer: API\n", "- Layer: API\n* Layer: UI\n")));
  spoil("a second layer line, written \"- Layer (fallback): UI\"", "has a line that is not one of its fields", swap(R06, R06.replace("- Layer: API\n", "- Layer: API\n- Layer (fallback): UI\n")));
  spoil("the layer line taken out", "has 0 lines giving a layer", swap(R06, R06.replace("- Layer: API\n", "")));
  spoil("a layer that is not one of the five", "has the layer \"end-to-end\"", swap(R10, R10.replace("- Layer: UI", "- Layer: end-to-end")));
  spoil("a risk written as a paragraph above the first heading of section 3, with no block of its own", "mentions R-20, which is not a risk with its own heading in section 3", swap("### R-01. ", "**R-20.** Card numbers are written to the server's log.\n\n### R-01. "));
  spoil("a risk put under a new heading after section 3", "mentions R-20, which is not a risk with its own heading in section 3", swap("## 4. Which risks need a browser", "## 3a. Risks added late\n\n### R-20. A receipt shows the wrong total\n\n## 4. Which risks need a browser"));
  spoil("a risk added to section 3 with a heading and no fields", "R-20 has 0 lines giving a layer", swap("## 4. Which risks need a browser", "### R-20. A receipt shows the wrong total\n\n## 4. Which risks need a browser"));
  spoil("a risk given twice", "R-13 is in section 3 more than once", (text) => { const block = text.match(/### R-13\. [\s\S]*?(?=### R-14\. )/)?.[0]; return block ? text.replace(block, block + block) : text; });

  log.out("", "-- Criterion 4: a reason, not only a label");
  spoil("a reason that is only the layer's name", "gives a reason for its layer of 1 word", (text) => text.replace(/- Reason for the layer: the format is made by one function[^\n]*/, "- Reason for the layer: unit."));
  spoil("one risk given another's reason, letter for letter", "gives the same reason for its layer, letter for letter, as", (text) => {
    const first = text.match(/- Reason for the layer: the subtotal is a sum[^\n]*/)?.[0];
    return first ? text.replace(/- Reason for the layer: taking a percentage off[^\n]*/, () => first) : text;
  });
  spoil("a reason broken over two lines", "has a line that is not one of its fields", swap("Nothing about a page or a request can make that sum right or wrong,", "Nothing about a page or a request\ncan make that sum right or wrong,"));
  spoil("a cheapest test of three words", "describes its cheapest test that would fail in 3 words", (text) => text.replace(/- Cheapest test that would fail: send the same order request twice[^\n]*/, "- Cheapest test that would fail: test the order."));
  spoil("the line saying what must exist first taken out", "has 0 lines giving \"Needs first\"", drop(/- Needs first: a payment provider\.[^\n]*\n/));

  log.out("", "-- Criterion 5: browser and no browser");
  spoil("a UI risk made to say it needs no browser", "says no to needing a browser, and its layer, UI, is one that needs one", swap(R10, R10.replace("- Needs a browser: yes", "- Needs a browser: no")));
  spoil("a risk made to say \"sometimes\"", "does not say yes or no to whether it needs a browser", swap(R10, R10.replace("- Needs a browser: yes", "- Needs a browser: sometimes")));
  spoil("the table of layers made to say UI needs no browser", "The table of layers says \"no\" to whether UI needs a browser", swap("| UI | Playwright drives the page in a browser | yes |", "| UI | Playwright drives the page in a browser | no |"));
  spoil("a layer taken out of the table of layers", "The table of layers in section 1 does not have one row each", drop(/^\| manual \| A person follows[^\n]*\n/m));
  spoil("a risk taken out of the list of those that need a browser, with the number left right for the blocks", "Section 4 does not list under \"Need a browser\" exactly", swap("R-09, R-10, R-14, R-18.", "R-09, R-10, R-14."));
  spoil("the number changed in that list, with the list left right", "Section 4 does not give, for \"Need a browser\", the number", swap("**Need a browser (4):**", "**Need a browser (5):**"));
  spoil("a risk taken out of the list of those that need no browser", "Section 4 does not list under \"Do not need a browser\" exactly", swap("R-16, R-17, R-19.\n", "R-16, R-17.\n"));
  spoil("the count of risks tested without a browser changed", "Section 4 does not say: \"Of the 15 risks that are to be tested, 11", swap("11 are to be tested without a browser", "12 are to be tested without a browser"));

  log.out("", "-- Criterion 6: what is left untested");
  spoil("an untested risk's row taken out of section 5", "R-15 has the layer none and does not have one row in section 5", drop(/^\| R-15 \| REQ-03 \| 3 \|[^\n]*\n/m));
  spoil("a tested risk made untested in its block only", "R-12 has the layer none and does not have one row in section 5", swap(R12, R12.replace("- Layer: unit", "- Layer: none")));
  spoil("a tested risk added to section 5", "R-12 is in section 5 as untested, and its layer is unit", (text) => text.replace(/^(\| R-13 \| REQ-11 \| 2 \|[^\n]*\n)/m, "$1| R-12 | REQ-10 | 4 | It is only formatting and nobody has complained about it so far | Nothing | the participant, as product owner of the demo shop | 2026-11-25 |\n"));
  spoil("a row in section 5 for a risk that is not in section 3", "Section 5 has a row for \"R-99\"", (text) => text.replace(/^(\| R-13 \| REQ-11 \| 2 \|[^\n]*\n)/m, "$1| R-99 | REQ-10 | 2 | It is only formatting and nobody has complained about it so far | Nothing | the participant, as product owner of the demo shop | 2026-11-25 |\n"));
  spoil("the person who accepted an untested risk taken out", "does not give, as the one who accepted R-13, the person it says can accept a risk: it says \"\"", row("R-13", (c) => [...c.slice(0, 5), "", c[6]], "## 5. "));
  spoil("\"TBC\" written where that person belongs", "the one who accepted R-15, the person it says can accept a risk: it says \"TBC\"", row("R-15", (c) => [...c.slice(0, 5), "TBC", c[6]], "## 5. "));
  spoil("\"someone\" written where that person belongs", "the one who accepted R-15, the person it says can accept a risk: it says \"someone\"", row("R-15", (c) => [...c.slice(0, 5), "someone", c[6]], "## 5. "));
  spoil("the line saying who can accept a risk taken out", "Section 5 does not say who can accept a risk in the words the requirements file uses", drop(/^Who can accept a risk: [^\n]*\n/m));
  spoil("an acceptance dated the 31st of November", "gives no calendar date on which R-13 was accepted", row("R-13", (c) => [...c.slice(0, 6), "2026-11-31"], "## 5. "));
  spoil("an acceptance with no date", "gives no calendar date on which R-15 was accepted: it says \"\"", row("R-15", (c) => [...c.slice(0, 6), ""], "## 5. "));
  spoil("the reason an untested risk is not tested cut to two words", "words for why R-13 is not tested", row("R-13", (c) => [c[0], c[1], c[2], "Too hard.", ...c.slice(4)], "## 5. "));
  spoil("an untested risk's score changed in section 5", "Section 5 gives R-15 a score of 1, and its block gives 3", row("R-15", (c) => [c[0], c[1], "1", ...c.slice(3)], "## 5. "));
  spoil("an untested risk's requirement changed in section 5", "Section 5 gives R-15 requirements that are not its block's", row("R-15", (c) => [c[0], "REQ-04", ...c.slice(2)], "## 5. "));

  log.out("", "-- Criterion 7: the ranking can be rebuilt");
  const exchange = (a: string, b: string) => (text: string) => {
    const one = text.match(new RegExp(`^\\| (\\d+) \\| ${a} \\|[^\\n]*$`, "m")), two = text.match(new RegExp(`^\\| (\\d+) \\| ${b} \\|[^\\n]*$`, "m"));
    if (!one || !two) return text;
    return text.replace(one[0], "\u0000").replace(two[0], one[0].replace(`| ${one[1]} |`, `| ${two[1]} |`)).replace("\u0000", two[0].replace(`| ${two[1]} |`, `| ${one[1]} |`));
  };
  spoil("two rows of different scores changed places", "By the scales and the ranking rule, rank 7 is R-17 (3 × 3 = 9", exchange("R-17", "R-01"));
  spoil("two rows of equal score and different impact changed places", "By the scales and the ranking rule, rank 12 is R-10 (2 × 3 = 6", exchange("R-10", "R-05"));
  spoil("two rows equal in score and impact, and different in importance, changed places", "By the scales and the ranking rule, rank 5 is R-19 (3 × 3 = 9, must)", exchange("R-19", "R-07"));
  spoil("two rows equal in all but risk number changed places", "By the scales and the ranking rule, rank 1 is R-02 (3 × 3 = 9, must)", exchange("R-02", "R-03"));
  spoil("a likelihood and an impact raised in a risk's block, with clauses and score to match, and the ranked table left as it was", "By the scales and the ranking rule, rank 7 is R-12 (3 × 3 = 9, should)",
    (text) => text.replace("- Likelihood: 2 (L2a). There are cases: whole pounds, pence, zero and a negative amount.", "- Likelihood: 3 (L3a). There are cases: whole pounds, pence, zero and a negative amount.")
      .replace("- Impact: 2 (I2a). A discount shown as a positive amount tells the customer something untrue. The money is right.\n- Score: 4", "- Impact: 3 (I3a). A discount shown as a positive amount tells the customer something untrue. The money is right.\n- Score: 9"));
  spoil("a likelihood changed in the ranked table only", "Section 2 gives R-06 a likelihood, an impact or a score that is not its block's", row("R-06", (c) => [c[0], c[1], c[2], "3", c[4], c[5], c[6]], "## 2. ", 1));
  spoil("a layer changed in the ranked table only", "Section 2 gives R-06 the layer UI, and its block says API", row("R-06", (c) => [...c.slice(0, 6), "UI"], "## 2. ", 1));
  spoil("a requirement changed in the ranked table only", "Section 2 gives R-06 requirements that are not its block's", row("R-06", (c) => [c[0], c[1], "REQ-04", ...c.slice(3)], "## 2. ", 1));
  spoil("a rank number changed in the ranked table", "Row 19 of section 2 is numbered \"20\"", row("R-13", (c) => ["20", ...c.slice(1)], "## 2. ", 1));
  spoil("the last row taken out of the ranked table", "Section 2 has 18 rows, and section 3 has 19 risks", drop(/^\| 19 \| R-13 \|[^\n]*\n/m));
  spoil("one risk put in the ranked table twice, in place of another", "Section 2 does not name each risk of section 3 once", row("R-13", (c) => [c[0], "R-12", ...c.slice(2)], "## 2. ", 1));
  spoil("the stated rule for equal scores changed to \"by likelihood\"", "does not state the order of equal scores in the words this check works by", swap("**Equal scores are ordered by impact, highest first;", "**Equal scores are ordered by likelihood, highest first;"));
  spoil("the statement of the score taken out", "does not state the score as likelihood × impact", swap("**Score = likelihood × impact.**", "**Score.**"));
  spoil("the rule for two clauses of different levels taken out", "does not say which level is taken when clauses of two levels apply", swap("the higher level is taken**, on both scales.", "either may be taken**."));

  log.out("", "-- Forms the first version of this check did not see");
  spoil("a requirement added in a second table, with an identifier written REQ-13a", "mentions REQ-13a, which is not a row of its table", (text) => text + "\n## Added late\n\n| ID | Importance | Requirement | In the demo today |\n|---|---|---|---|\n| REQ-13a | must | A refund returns the amount that was taken | no |\n", true);
  spoil("a requirement written \"Req 13\" in a sentence", "mentions Req 13, which is not a row of its table", (text) => text + "\nReq 13: a refund returns the amount that was taken.\n", true);
  spoil("the line saying who can accept a risk taken out of the requirements", "The requirements file does not say who can accept a risk", drop(/^Who can accept a risk: [^\n]*\n/m), true);
  spoil("the acceptor changed to \"to be decided\" in section 5's line and in all its rows, and not in the requirements", "Section 5 does not say who can accept a risk in the words the requirements file uses", (text) => text.split("the participant, as product owner of the demo shop").join("to be decided"));
  spoil("a requirement of two words", "REQ-11 has a requirement of 2 words", (text) => text.replace(/^\| REQ-11 \| could \| [^|]* \|/m, "| REQ-11 | could | Be fast |"), true);
  spoil("a row of the requirements with no identifier", "where an identifier belongs", swap("| REQ-11 | could |", "| speed | could |"), true);
  spoil("every requirement made a must", "The requirements all have the same importance", (text) => text.replace(/^(\| REQ-\d+ \|) (should|could) \|/gm, "$1 must |"), true);
  spoil("a risk written \"Risk 20\" in a paragraph, with no block", "mentions Risk 20, which is not a risk with its own heading", swap("## 4. Which risks need a browser", "**Risk 20.** Card numbers are written to the server's log. Not tested.\n\n## 4. Which risks need a browser"));
  spoil("a risk written \"R20\" in section 6's untested column", "mentions R20, which is not a risk with its own heading", row("REQ-01", (c) => [c[0], c[1], c[2], c[3], "R20"], "## 6. "));
  spoil("words added beside the identifiers in section 6", "Section 6 has something other than risk identifiers and commas in a cell for REQ-01", row("REQ-01", (c) => [c[0], c[1], c[2], c[3], "the gift-card risk, which has no block"], "## 6. "));
  spoil("field lines written before the first risk of section 3", "Section 3 has text before its first risk", swap("### R-01. ", "- Layer: manual\n- Reason for the layer: every risk below is also checked by hand.\n\n### R-01. "));
  spoil("a well-formed line in a block that is not one of the nine fields", "has a line that is not one of its fields", swap(R06, R06.replace("- Layer: API\n", "- Layer: API\n- Fallback layer: UI\n")));
  spoil("a second table in section 2 that renders as a heading row only, putting another risk first", "Section 2 has 2 tables, and one is needed", swap("\nFifteen of the 19 risks are level", "\n| 1 | R-13 | REQ-11 | 3 | 3 | 9 | none |\n|---|---|---|---|---|---|---|\n\nFifteen of the 19 risks are level"));
  spoil("an untested risk's row moved into a second table in section 5", "Section 5 has 2 tables, and one is needed", (text) => { const line = text.match(/^\| R-19 \| REQ-04, REQ-08 \| 9 \|[^\n]*\n/m)?.[0]; return line ? text.replace(line, "").replace("The strategy was drafted by an AI assistant.", () => "| Risk | Requirement | Score | Why | Instead | Accepted by | On |\n|---|---|---|---|---|---|---|\n" + line + "\nThe strategy was drafted by an AI assistant.") : text; });
  spoil("an eighth cell added to a row of section 5", "has 8 cells, and seven are needed", (text) => text.replace(/^(\| R-13 \| REQ-11 \| 2 \|[^\n]*\|)$/m, "$1 withdrawn 2026-11-26 |"));
  spoil("what is done instead left empty", "Section 5 does not say what is done instead of testing R-15", row("R-15", (c) => [c[0], c[1], c[2], c[3], "", c[5], c[6]], "## 5. "));
  spoil("a fifth row added to section 7", "Section 7 does not have one row each for unit, API, UI and manual", (text) => text.replace(/^(\| manual \| none \|[^\n]*\n)/m, "$1| load | none | 5 runs | 2 seconds | 10 seconds | A guess |\n"));
  spoil("a full stop left as all that says what must exist first", "does not say what must exist before its test can be written", swap("- Needs first: nothing can be built that would make this testable.", "- Needs first: ."));
  spoil("a risk with a title of two words", "R-16 has a title of 2 words", swap("### R-16. A valid code is refused", "### R-16. Code refused"));
  spoil("a risk's heading with no full stop after its identifier", "is headed", swap("### R-16. A valid code is refused", "### R-16 A valid code is refused"));
  spoil("the scale of impact taken out", "Section 1 has no scale of impact that can be read", (text) => { const part = text.match(/### Impact: [\s\S]*?(?=### Ranking)/)?.[0]; return part ? text.replace(part, "### Impact: what it costs when it breaks\n\nHigh, medium or low.\n\n") : text; });
  spoil("an impact changed in the ranked table only", "Section 2 gives R-06 a likelihood, an impact or a score that is not its block's", row("R-06", (c) => [c[0], c[1], c[2], c[3], "2", c[5], c[6]], "## 2. ", 1));
  const moved = ((text: string) => { const one = text.match(/### R-01\. [\s\S]*?(?=### R-02\. )/)?.[0], two = text.match(/### R-02\. [\s\S]*?(?=### R-03\. )/)?.[0]; return one && two ? text.replace(one + two, two + one) : text; })(strategy);
  const afterMove = problems(requirementsText, moved);
  log.out("Not spoiled: the block of R-02 moved above the block of R-01 in section 3, with the ranked table left as it is", `    the text was ${moved !== strategy ? "changed" : "NOT CHANGED"}. problems reported: ${afterMove.length}, and for the documents as they are: ${found.length}`);
  log.check("the ranking does not depend on the order of the blocks: R-02 still ranks above R-03, and R-01 above R-04, by risk number", moved !== strategy && afterMove.length === found.length);

  log.out("", "-- Section 7, and the form of the file");
  spoil("a risk taken out of its layer's row in section 7", "Section 7 does not list for the unit layer exactly", row("unit", (c) => [c[0], c[1].replace(", R-16", ""), ...c.slice(2)], "## 7. "));
  const crlf = problems(requirementsText.replace(/\n/g, "\r\n"), strategy.replace(/\n/g, "\r\n"));
  log.out("Not spoiled: both documents with the other kind of line ending, which changes nothing a reader sees", `    problems reported: ${crlf.length}, and for the documents as they are: ${found.length}`);
  log.check("the other kind of line ending is reported as nothing: the same problems, no more and no fewer", crlf.length === found.length && crlf.every((problem, index) => problem === found[index]));

  log.part("AT THE END");
  log.out("The program has one line that writes a file, and it writes this log. So the documents were not changed by it. That is read from the code, not tested.");
  log.save(join(ATTEMPT, "logs", "strategy-check.txt"));
  return log.failed.length ? 1 : 0;
}

process.exit(main());

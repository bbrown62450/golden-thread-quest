import { createHash } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";

/*
 * Evidence of success, for the playwright-success-evidence quest.
 *
 * A test using this file has three kinds of step, and says which is which:
 *
 *   navigation()    getting to where a rule can be checked. It may hold assertions ("we arrived"). It captures NOTHING.
 *   precondition()  an assertion that the starting figures are the ones the rule's arithmetic assumes. It captures NOTHING.
 *   proves()        THE ASSERTION THAT A BUSINESS RULE HELD. This, and only this, captures evidence.
 *
 * WHAT proves() DOES, IN ORDER
 *   1. It makes the assertion: the element has exactly the expected text. Playwright waits for it as usual.
 *   2. Whether that passed or failed, it reads the element's text as it now is, and the texts the rule's value follows from.
 *   3. It takes a picture of the part of the page the rule is about, and of nothing else.
 *   4. It writes a record beside the picture: the rule, the value asserted, the value read, and whether the rule HELD.
 *   5. It attaches both to the test's report.
 *   6. If the assertion failed in step 1, it now fails the test with that same error. The failure is never swallowed:
 *      if anything in steps 2 to 5 goes wrong as well, the assertion's own error is still the one thrown.
 *   A passing assertion whose evidence could not be captured also fails the test. A proof with no evidence is not one.
 *   The same id used twice in one run fails the test: there is one piece of evidence for a rule, not the latest of several.
 *
 * WHAT THE RECORD'S WORDS MEAN
 *   "has exactly the text" is Playwright's toHaveText with a string: the whole text, case and all, with runs of white
 *   space counted as one space. "Read from the page" is read the same way, a moment later. On a page that is still
 *   changing the two could differ. The checkout's pages do not change once sent.
 *   "Text inside the picture" is the text of the elements the picture was asked to hold, as the page gives it. It is
 *   not read back out of the pixels.
 *
 * So the value in the record is not typed twice: "asserted" is the very value step 1 asserted, and "read" is read from
 * the page at that moment. When a rule does not hold, the record says DID NOT HOLD, shows the value that was there, and
 * the test fails.
 *
 * WHERE   GTQ_PROOF_DIR, or local-data/playwright-success/validated, which git ignores. The settings file empties it
 *         before every run, so that what is in it is from one run.
 */

export const PROOF_DIR = resolve(process.env.GTQ_PROOF_DIR ?? join(__dirname, "..", "..", "..", "..", "local-data", "playwright-success", "validated"));
const OUTPUT = join(PROOF_DIR, "run-output.txt");

function say(testInfo: TestInfo, kind: string, text: string) {
  mkdirSync(PROOF_DIR, { recursive: true });
  appendFileSync(OUTPUT, `${testInfo.title.split(" ")[0].padEnd(3)} ${kind.padEnd(13)} ${text}\n`);
}

/** The line of the test file that called proves(). */
function calledFrom(): string {
  const line = (new Error().stack ?? "").split("\n").find((entry) => /\.spec\.ts:\d+/.test(entry)) ?? "";
  const found = line.match(/([\w.-]+\.spec\.ts):(\d+)/);
  return found ? `${found[1]}, line ${found[2]}` : "(not known)";
}

async function quiet(what: string, steps: () => Promise<void>, testInfo: TestInfo, kind: string) {
  try {
    await steps();
    say(testInfo, kind, `${what}. Done. Nothing captured.`);
  } catch (error) {
    say(testInfo, kind, `${what}. FAILED HERE. Nothing captured.`);
    throw error;
  }
}

/** Getting there. Captures nothing. */
export const navigation = (testInfo: TestInfo, what: string, steps: () => Promise<void>) => quiet(what, steps, testInfo, "NAVIGATION");

/** The figures the rule starts from are the ones its arithmetic assumes. Captures nothing. */
export const precondition = (testInfo: TestInfo, what: string, steps: () => Promise<void>) => quiet(what, steps, testInfo, "PRECONDITION");

export type Proof = {
  /** The name of the two files, such as "R1-discount". */
  id: string;
  /** The business rule, in words. */
  rule: string;
  /** Why the expected value is the one the rule gives, as arithmetic. */
  because: string;
  /** What a reader must not take this evidence to show. It is written into the record. */
  doesNotShow: string;
  /** The element whose text is asserted. */
  element: Locator;
  /** What the element is, in words, for the record. */
  elementIs: string;
  /** The exact text asserted. */
  hasExactlyTheText: string;
  /** What the value follows from: a label and the element to read, or a text already read earlier in the test. */
  given: [string, Locator | string][];
  /** The elements to picture. The picture is the smallest rectangle that holds them all. */
  picture: Locator[];
};

const text = (value: string | null) => (value ?? "").replace(/\s+/g, " ").trim();

export async function proves(testInfo: TestInfo, page: Page, proof: Proof): Promise<void> {
  const where = calledFrom();
  mkdirSync(PROOF_DIR, { recursive: true });
  const pictureFile = join(PROOF_DIR, `${proof.id}.png`);
  const recordFile = join(PROOF_DIR, `${proof.id}.md`);
  if (existsSync(recordFile)) throw new Error(`Evidence "${proof.id}" was already captured in this run. A rule has one piece of evidence.`);

  let assertionFailed = false;
  let assertionError: unknown;
  try {
    await expect(proof.element).toHaveText(proof.hasExactlyTheText);
  } catch (error) {
    assertionFailed = true;
    assertionError = error;
  }
  try {
    const readText = async (target: Locator | string) => (typeof target === "string" ? target : await target.textContent({ timeout: 1_000 }).then(text, () => "(not on the page)"));
    const read = await readText(proof.element);
    const given: [string, string][] = [];
    for (const [label, target] of proof.given) given.push([label, await readText(target)]);

    let box: { x: number; y: number; width: number; height: number } | null = null;
    const shown: string[] = [];
    for (const part of proof.picture) {
      // The rectangle of the element's own text, not of the element, which may be as wide as the page. This reads the
      // page and changes nothing in it.
      const b = await part.evaluate((element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const r = range.getBoundingClientRect();
        return r.width && r.height ? { x: r.x, y: r.y, width: r.width, height: r.height } : null;
      }, undefined, { timeout: 1_000 }).catch(() => null);
      if (!b) continue;
      shown.push(await readText(part));
      const right = Math.max(b.x + b.width, box ? box.x + box.width : 0);
      const bottom = Math.max(b.y + b.height, box ? box.y + box.height : 0);
      const x = Math.min(b.x, box ? box.x : b.x);
      const y = Math.min(b.y, box ? box.y : b.y);
      box = { x, y, width: right - x, height: bottom - y };
    }
    let pictureLine = "- Picture: none. The part of the page the rule is about was not there.";
    if (box) {
      // A margin at the sides only. Above and below, the next line of the page starts at once, and it is not to be in the picture.
      const side = 8;
      const png = await page.screenshot({ clip: { x: Math.max(0, box.x - side), y: box.y, width: box.width + 2 * side, height: box.height } });
      writeFileSync(pictureFile, png);
      pictureLine = `- Picture: \`${proof.id}.png\`, of that part of the page and no more. sha256 \`${createHash("sha256").update(png).digest("hex")}\``;
    }
    const held = !assertionFailed;
    const record = [
      `# ${proof.id.split("-")[0]} · ${proof.rule}`,
      "",
      `- Result: ${held ? "HELD" : "DID NOT HOLD"}, for the one basket this test uses`,
      `- Asserted: ${proof.elementIs} has exactly the text \`${proof.hasExactlyTheText}\``,
      `- Read from the page at that moment: \`${read}\``,
      ...given.map(([label, value]) => `- Given, ${label}: \`${value}\``),
      `- Why that value: ${proof.because}`,
      `- What this does not show: ${proof.doesNotShow}`,
      `- Asserted at: \`${where}\`, in the test "${testInfo.title}"`,
      pictureLine,
      `- Text inside the picture: ${shown.map((each) => `\`${each}\``).join(" ") || "none"}`,
      `- Taken at: ${new Date().toISOString()}, from a made-up checkout running on this computer only`,
      "",
    ].join("\n");
    writeFileSync(recordFile, record);
    await testInfo.attach(`${proof.id}.md`, { path: recordFile, contentType: "text/markdown" });
    if (box) await testInfo.attach(`${proof.id}.png`, { path: pictureFile, contentType: "image/png" });
    say(testInfo, "PROOF", `${proof.rule}. Asserted \`${proof.hasExactlyTheText}\`, read \`${read}\`. ${held ? "HELD" : "DID NOT HOLD"}. Captured ${proof.id}.md${box ? ` and ${proof.id}.png` : ""}.`);
    if (!box && held) throw new Error(`The assertion of "${proof.id}" passed, and no picture of it could be taken.`);
  } catch (captureError) {
    if (assertionFailed) throw assertionError; // the rule's own failure is the one to report
    throw captureError;
  }
  if (assertionFailed) throw assertionError;
}

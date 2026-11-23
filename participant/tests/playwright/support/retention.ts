/*
 * How long evidence is kept, enforced. For the playwright-failure-evidence quest.
 *
 * A failure bundle says in its own bundle.json when it is to be deleted (kept.deleteAfter). This
 * removes the bundles whose date has passed, and the lines of passing-runs.log that are too old.
 * It runs before every test run, as Playwright's global setup, so nothing has to remember to run it.
 *
 * It is careful about what it deletes. It only looks at folders directly inside the bundles
 * folder. It removes a folder only if that folder holds a bundle.json of this format with a
 * deleteAfter date that has passed. Anything else is left alone and counted.
 */

import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export const BUNDLE_FORMAT = "gtq-failure-bundle/1";

export type Swept = { removed: string[]; kept: string[]; leftAlone: string[]; passingLinesRemoved: number; passingLinesKept: number };

export function removeExpired(bundlesDir: string, keepPassingLineDays: number, now: Date = new Date()): Swept {
  const swept: Swept = { removed: [], kept: [], leftAlone: [], passingLinesRemoved: 0, passingLinesKept: 0 };
  if (!existsSync(bundlesDir)) return swept;
  for (const entry of readdirSync(bundlesDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    let deleteAfter = Number.NaN;
    try {
      const bundle = JSON.parse(readFileSync(join(bundlesDir, entry.name, "bundle.json"), "utf8"));
      if (bundle.format === BUNDLE_FORMAT) deleteAfter = Date.parse(bundle.kept?.deleteAfter);
    } catch {
      // not a bundle, or not readable: left alone
    }
    if (Number.isNaN(deleteAfter)) swept.leftAlone.push(entry.name);
    else if (deleteAfter <= now.getTime()) {
      rmSync(join(bundlesDir, entry.name), { recursive: true, force: true });
      swept.removed.push(entry.name);
    } else swept.kept.push(entry.name);
  }
  const passing = join(bundlesDir, "passing-runs.log");
  if (existsSync(passing)) {
    const oldest = now.getTime() - keepPassingLineDays * 86_400_000;
    const lines = readFileSync(passing, "utf8").split("\n").filter((line) => line !== "");
    const keep = lines.filter((line) => {
      const at = Date.parse(line.slice(0, 24));
      return Number.isNaN(at) || at >= oldest;
    });
    swept.passingLinesRemoved = lines.length - keep.length;
    swept.passingLinesKept = keep.length;
    if (swept.passingLinesRemoved) writeFileSync(passing, keep.join("\n") + (keep.length ? "\n" : ""), "utf8");
  }
  return swept;
}

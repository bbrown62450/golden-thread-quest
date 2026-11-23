/*
 * Runs once before every test run that uses evidence.config.ts: removes the evidence that has
 * been kept as long as the configuration says. See support/retention.ts.
 */

import type { FullConfig } from "@playwright/test";

import type { EvidenceSettings } from "./evidence";
import { removeExpired } from "./retention";

export default function globalSetup(config: FullConfig): void {
  const settings = (config.projects[0].use as { evidenceSettings?: EvidenceSettings }).evidenceSettings;
  if (!settings) throw new Error("evidence: the configuration has no evidenceSettings");
  const swept = removeExpired(settings.bundlesDir, settings.keepPassingLineDays);
  console.log(
    `evidence: kept for ${settings.keepFailureBundleDays} days. Before this run: ${swept.removed.length} expired failure bundle(s) deleted, ` +
    `${swept.kept.length} kept, ${swept.leftAlone.length} folder(s) that are not bundles left alone, ${swept.passingLinesRemoved} old passing line(s) deleted.`,
  );
}

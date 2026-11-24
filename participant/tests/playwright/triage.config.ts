import { join, resolve } from "node:path";

import { defineConfig } from "@playwright/test";

import type { EvidenceSettings } from "./support/triage-evidence";

/*
 * Settings for the playwright-failure-triage quest only. The earlier quests' settings files are left as they were
 * approved and are not used here.
 *
 * The tests in triage.spec.ts run against the made-up order desk in demo-app/triage-server.mjs, on this computer only.
 *
 * RETRIES: 1. A test that fails is run once more, as many teams do. That is the habit the quest is about, so the bundle
 * records it: attempts.json in a failure's bundle holds every attempt, and what a passing retry looked like.
 * A retry never hides a failure here. The first failed attempt always leaves its bundle.
 *
 * Playwright's own trace, screenshot and video are off, for the reason given in evidence.config.ts: the fixture records
 * the trace itself and takes the secrets out before saving it.
 *
 * Bundles go to the repository's ignored local-data folder. Set GTQ_BUNDLES_DIR to send them elsewhere; the check
 * script does.
 */

const LOCAL = resolve(__dirname, "..", "..", "..", "local-data", "playwright-triage");

const port = Number(process.env.TRIAGE_PORT ?? 4797);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`TRIAGE_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.TRIAGE_PORT)}.`);
}

export const EVIDENCE: EvidenceSettings = {
  bundlesDir: process.env.GTQ_BUNDLES_DIR ?? join(LOCAL, "bundles"),
  keepFailureBundleDays: 14,
  keepPassingLineDays: 14,
  serverLog: process.env.TRIAGE_SERVER_LOG ?? join(LOCAL, "triage-server.log"),
  redact: true,
};

export default defineConfig<{ evidenceSettings: EvidenceSettings }>({
  testDir: ".",
  testMatch: ["triage.spec.ts"],
  outputDir: join(LOCAL, "playwright-output"),
  retries: 1,
  workers: 1,
  reporter: [["list"]],
  expect: { timeout: 2_000 },
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "off",
    screenshot: "off",
    video: "off",
    evidenceSettings: EVIDENCE,
  },
  webServer: {
    command: "node demo-app/triage-server.mjs",
    url: `http://127.0.0.1:${port}/healthz`,
    reuseExistingServer: true,
    timeout: 30_000,
    env: { TRIAGE_PORT: String(port), TRIAGE_SERVER_LOG: EVIDENCE.serverLog },
  },
});

import { join, resolve } from "node:path";

import { defineConfig } from "@playwright/test";

import type { EvidenceSettings } from "./support/evidence";

/*
 * Settings for the playwright-failure-evidence quest only. The earlier quests' settings files are
 * left as they were approved and are not used here.
 *
 * WHAT IS KEPT, AND FOR HOW LONG
 *
 *   When a test FAILS, one folder is kept, a "failure bundle", holding:
 *       the error message and where it was raised      error.txt
 *       a screenshot of the page                        screenshot.png
 *       the browser's console log                       console.log
 *       the failed requests, with the answers' bodies   failed-requests.json
 *       every request, one line each                    requests.txt
 *       the application's log for those seconds         server.log
 *       the Playwright trace, without its film          trace.zip
 *       the test, the times, the commit under test      bundle.json
 *     It is kept for 14 DAYS (keepFailureBundleDays below) and then deleted. The date is written
 *     in the bundle's own bundle.json, as kept.deleteAfter. Deleting is done by this
 *     configuration's global setup, before every run. Nothing has to remember to do it.
 *
 *   When a test PASSES, ONE LINE is kept, in passing-runs.log: the time, the test's title and how
 *     long it took. No trace, no screenshot, no console log, no request log. The line is kept for
 *     14 days (keepPassingLineDays).
 *
 *   Secrets are taken out before anything is saved. How is described in support/evidence.ts.
 *
 * WHY PLAYWRIGHT'S OWN trace, screenshot AND video SETTINGS ARE "off"
 *   Playwright's own "retain-on-failure" trace is saved as it is, with every cookie, every
 *   Authorization header and every typed password inside it, and Playwright has no setting to
 *   remove them. So the fixture in support/evidence.ts records the trace itself, and removes the
 *   secrets from it before it is saved. Leaving the built-in ones on would save a second,
 *   unredacted copy. Video is off because a film cannot be searched for secrets.
 *
 *   One thing Playwright still writes by itself when a test fails is error-context.md, in its
 *   scratch output folder: the error and an outline of the page. It is not copied into the
 *   bundle, and that folder is ignored by git and never handed in.
 *
 * WHERE
 *   Bundles go to the repository's ignored local-data folder, not into participant/. A bundle is
 *   handed in only by copying it, after it has been scanned.
 *   Set GTQ_BUNDLES_DIR to send them somewhere else. The check script does.
 *
 * The tests run against the made-up order desk in demo-app/orders-server.mjs, on this computer only.
 */

const LOCAL = resolve(__dirname, "..", "..", "..", "local-data", "playwright-evidence");

const port = Number(process.env.ORDERS_PORT ?? 4794);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`ORDERS_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.ORDERS_PORT)}.`);
}

export const EVIDENCE: EvidenceSettings = {
  bundlesDir: process.env.GTQ_BUNDLES_DIR ?? join(LOCAL, "bundles"),
  keepFailureBundleDays: 14,
  keepPassingLineDays: 14,
  serverLog: process.env.ORDERS_SERVER_LOG ?? join(LOCAL, "orders-server.log"),
  // Redaction is ON. Only tools/failure-evidence-check.ts turns it off, into a scratch folder it
  // deletes, to show that its scan finds what redaction removes.
  redact: process.env.GTQ_EVIDENCE_REDACT !== "off",
};

export default defineConfig<{ evidenceSettings: EvidenceSettings }>({
  testDir: ".",
  testMatch: ["failure-evidence.spec.ts"],
  // Playwright's own scratch output. With trace, screenshot and video off, nothing is left in it.
  outputDir: join(LOCAL, "playwright-output"),
  globalSetup: "./support/evidence-global-setup.ts",
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "off",
    screenshot: "off",
    video: "off",
    evidenceSettings: EVIDENCE,
  },
  webServer: {
    command: "node demo-app/orders-server.mjs",
    url: `http://127.0.0.1:${port}/healthz`,
    reuseExistingServer: true,
    timeout: 30_000,
    env: { ORDERS_PORT: String(port), ORDERS_SERVER_LOG: EVIDENCE.serverLog },
  },
});

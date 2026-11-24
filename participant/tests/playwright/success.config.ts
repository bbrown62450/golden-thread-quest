import { resolve } from "node:path";

import { defineConfig } from "@playwright/test";

/*
 * Settings for the playwright-success-evidence quest only. The earlier quests' settings files are left as they were
 * approved and are not used here.
 *
 * The test, meaningful-evidence.spec.ts, runs against the made-up checkout in demo-app/checkout-server.corrected.mjs,
 * on this computer only. This file starts no server: start the application first, or let
 * tools/success-evidence-check.ts do it.
 *
 *   CHECKOUT_PORT   the port the application listens on (default 4801)
 *   GTQ_PROOF_DIR   where evidence is captured to (default: local-data/playwright-success/validated, which git ignores)
 *
 * NOTHING IS CAPTURED BY DEFAULT. trace, screenshot and video are all "off", so Playwright itself keeps nothing of a
 * step, pass or fail. The only captures are those the test asks for by calling proves(), in support/proof.ts.
 *
 * No retries: a failure is a failure. One worker, so that the run's output is in the order the tests ran.
 */

const port = Number(process.env.CHECKOUT_PORT ?? 4801);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`CHECKOUT_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.CHECKOUT_PORT)}.`);
}

export default defineConfig({
  testDir: ".",
  testMatch: ["meaningful-evidence.spec.ts"],
  outputDir: resolve(__dirname, "..", "..", "..", "local-data", "playwright-success", "playwright-output"),
  globalSetup: "./support/proof-global-setup.ts",
  retries: 0,
  workers: 1,
  timeout: 15_000,
  reporter: [["list"]],
  expect: { timeout: 1_500 },
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "off", screenshot: "off", video: "off", viewport: { width: 1280, height: 720 } },
});

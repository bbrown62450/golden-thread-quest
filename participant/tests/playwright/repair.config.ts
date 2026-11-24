import { resolve } from "node:path";

import { defineConfig } from "@playwright/test";

/*
 * Settings for the playwright-repair-test quest only. The earlier quests' settings files are left as they were
 * approved and are not used here.
 *
 * The repaired test, needs-maintenance.repaired.spec.ts, runs against the made-up checkout, on this computer only.
 * This file starts no server: start the application first, or let tools/repair-test-check.ts do it.
 *
 *   CHECKOUT_PORT   the port the application listens on (default 4801)
 *   GTQ_TEST_DIR    the folder to find spec files in. The check sets it to run a COPY of a test from a scratch
 *                   folder. Not set: only needs-maintenance.repaired.spec.ts, here.
 *
 * No retries: a failure is a failure. No trace, screenshot or video: the pages hold nothing but made-up prices, and
 * the check reads the error and its line from the JSON report. The two time limits are the same as in
 * maintenance.config.ts, which the test ran under before it was repaired.
 */

const port = Number(process.env.CHECKOUT_PORT ?? 4801);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`CHECKOUT_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.CHECKOUT_PORT)}.`);
}
const elsewhere = process.env.GTQ_TEST_DIR;

export default defineConfig({
  testDir: elsewhere ? resolve(elsewhere) : ".",
  testMatch: elsewhere ? ["*.spec.ts"] : ["needs-maintenance.repaired.spec.ts"],
  outputDir: resolve(__dirname, "..", "..", "..", "local-data", "playwright-repair", "playwright-output"),
  retries: 0,
  workers: 1,
  timeout: 15_000,
  reporter: [["list"]],
  expect: { timeout: 1_500 },
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "off", screenshot: "off", video: "off" },
});

import { defineConfig } from "@playwright/test";

// Settings for the playwright-data-isolation quest only. The earlier quest's settings file,
// playwright.config.ts, is left as it was approved and is not used here.
//
// The tests run against the made-up customer directory in demo-app/server.mjs, on this
// computer only. If that application is already running on the port, it is used as it is, so
// that the check script can keep one application alive across many runs and look at its data
// before and after. Otherwise Playwright starts it and stops it.

const port = Number(process.env.DEMO_PORT ?? 4793);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`DEMO_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.DEMO_PORT)}.`);
}

export default defineConfig({
  testDir: ".",
  testMatch: ["coupled.spec.ts", "isolated.spec.ts"],
  // Run artifacts go to the repository's ignored local-data folder, not into participant/.
  outputDir: "../../../local-data/playwright-isolation-results",
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "off",
    screenshot: "off",
  },
  webServer: {
    command: "node demo-app/server.mjs",
    url: `http://127.0.0.1:${port}/healthz`,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});

import { defineConfig } from "@playwright/test";

// Settings for the playwright-test-inventory quest only. The other quests' settings files are left as they were approved.
//
// The tests run against the made-up customer directory in demo-app/server.mjs, on this computer only. If something is
// already answering on the port, it is used as it is: the check script puts a recorder there, in front of an
// application it started itself. Otherwise Playwright starts the application and stops it.
//
// INVENTORY_SPEC names the test file. It is inventoried.spec.ts unless the check script is trying a changed copy.

const port = Number(process.env.DEMO_PORT ?? 4793);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`DEMO_PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.DEMO_PORT)}.`);
}
const spec = process.env.INVENTORY_SPEC ?? "inventoried.spec.ts";
if (!/^inventoried(\.scratch-[a-z0-9-]+)?\.spec\.ts$/.test(spec)) {
  throw new Error("INVENTORY_SPEC must be inventoried.spec.ts or a scratch copy of it.");
}

export default defineConfig({
  testDir: ".",
  testMatch: [spec],
  // Run artifacts go to the repository's ignored local-data folder, not into participant/.
  outputDir: "../../../local-data/playwright-test-inventory-results",
  retries: 0,
  workers: 1,
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

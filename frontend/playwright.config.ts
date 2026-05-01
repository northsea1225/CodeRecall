import { defineConfig, devices } from "@playwright/test";

const isCI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",

  // backend fixture spawns a single uvicorn instance shared across tests;
  // running serially keeps the shared SQLite from racing on writes.
  fullyParallel: false,
  workers: 1,

  forbidOnly: isCI,
  retries: isCI ? 1 : 0,

  globalSetup: "./e2e/fixtures/backend.ts",

  reporter: isCI
    ? [["github"], ["html", { open: "never" }]]
    : [["list"]],

  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },

  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !isCI,
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chromium"] },
    },
  ],
});

import { defineConfig, devices } from "@playwright/test";

const isCI = !!process.env.CI;

const E2E_BACKEND_PORT = Number(process.env.E2E_BACKEND_PORT ?? 18000);
const E2E_API_BASE_URL = `http://localhost:${E2E_BACKEND_PORT}/api/v1`;

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
    // Always restart vite for e2e so the dynamic VITE_API_BASE_URL env below
    // actually applies (a previously-running dev server would have inherited
    // a stale env and `reuseExistingServer: true` would silently bypass us).
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe",
    env: {
      VITE_API_BASE_URL: E2E_API_BASE_URL,
    },
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chromium"] },
    },
  ],
});

import { randomBytes } from "node:crypto";

import { test, expect, getBackendURL } from "./fixtures/auth";

const PASSWORD = "e2e-test-pass-1234";

function uniqueUsername(prefix = "spec"): string {
  return `e2e_${prefix}_${Date.now()}_${randomBytes(2).toString("hex")}`;
}

test.describe("Auth flow", () => {
  test("register → auto-login → /mistakes", async ({ page }) => {
    const username = uniqueUsername("reg");

    await page.goto("/register");
    await page.locator('input[autocomplete="username"]').fill(username);
    await page.locator('input[autocomplete="new-password"]').fill(PASSWORD);
    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(/\/mistakes/);
  });

  test("login existing user → /dashboard", async ({ page, testUser }) => {
    // testUser is registered via API but never logged in via UI.
    await page.goto("/login");
    await page.locator('input[autocomplete="username"]').fill(testUser.username);
    await page.locator('input[autocomplete="current-password"]').fill(testUser.password);
    await page.locator('button[type="submit"]').click();

    // Login redirects to "/" which AuthGuard + index route resolves to /dashboard.
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("logout from app shell → /login", async ({ authenticatedPage: page }) => {
    await page.goto("/dashboard");
    // Wait for the AppLayout sider to mount; the username footer renders only after login.
    const sider = page.locator(".sider-user-footer");
    await expect(sider).toBeVisible();
    // Antd Button with type="text" renders as <button class="ant-btn">; the only one
    // inside the user-footer is the logout button regardless of i18n locale.
    await sider.locator("button").click();

    await expect(page).toHaveURL(/\/login/);
  });

  test("AuthGuard redirects unauthenticated /mistakes → /login", async ({ page }) => {
    await page.goto("/mistakes");
    await expect(page).toHaveURL(/\/login/);
  });

  test("authenticated session survives reload (initializeAuth)", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/dashboard/);

    await page.reload();
    // Still authenticated → no AuthGuard redirect.
    await expect(page).toHaveURL(/\/dashboard/);
  });
});

// Sanity check that the fixture-provided backend URL is reachable; if globalSetup
// silently failed we want a clear failure here rather than mysterious 404s in specs.
test("backend health check from spec context", async () => {
  const res = await fetch(`${getBackendURL()}/health`);
  expect(res.ok).toBe(true);
});

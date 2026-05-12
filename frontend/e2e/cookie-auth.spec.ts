/**
 * C-005 Part 2 cookie-auth regression specs.
 *
 * Scope (2 cases):
 *   1. cookie session persists across full page reload — verifies that the
 *      frontend's async initializeAuth → /auth/me cookie call hydrates the
 *      Zustand session on cold boot, not just on the post-login navigation.
 *   2. mutation request without X-CSRF-Token is rejected with 403 —
 *      verifies the backend CSRF guard fires when the cookie-injected request
 *      strips its X-CSRF-Token header.
 */
import { test, expect, getBackendURL } from "./fixtures/auth";

test.describe("Cookie auth (C-005 Part 2)", () => {
  test("cookie session persists across page reload", async ({
    authenticatedPage: page,
  }) => {
    // First load: AuthGuard initializes via /auth/me and renders the SPA shell.
    await page.goto("/mistakes");
    // Sidebar contains the username, which is a stable signal that the
    // store has populated from /auth/me (cookie-mode initializeAuth).
    await expect(page.locator(".sider-user-footer .sider-username").first()).toBeVisible({
      timeout: 10_000,
    });

    // Full reload: cookies stay (they live on the browser context, not the
    // page lifetime), so initializeAuth should rehydrate without redirecting
    // to /login.
    await page.reload();
    await expect(page.locator(".sider-user-footer .sider-username").first()).toBeVisible({
      timeout: 10_000,
    });
    // Confirm we did not bounce to /login.
    await expect(page).toHaveURL(/\/mistakes/);
  });

  test("mutation without X-CSRF-Token is rejected with 403", async ({
    authenticatedPage: page,
    testUser,
  }) => {
    // Issue a POST /mistakes from inside the browser using fetch directly,
    // explicitly NOT setting X-CSRF-Token. The csrf_token cookie is still
    // attached automatically (credentials: include), but the backend's
    // verify_csrf_for_mutation requires header == cookie == jwt.csrf.
    // Going through fetch (not axios) bypasses the request interceptor that
    // would normally inject the header.
    await page.goto("/");
    const result = await page.evaluate(
      async ({ base, payload }: { base: string; payload: unknown }) => {
        const res = await fetch(`${base}/mistakes`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        let body: unknown = null;
        try {
          body = await res.json();
        } catch {
          /* ignore parse errors */
        }
        return { status: res.status, body };
      },
      {
        base: `${getBackendURL()}/api/v1`,
        payload: {
          title: `csrf-block-${Date.now()}`,
          stem_markdown: "x",
          wrong_answer_markdown: "x",
          correct_answer_markdown: "x",
          error_reason_markdown: "x",
          language: "cpp",
          difficulty: 3,
          source: "",
          is_archived: false,
          category_id: 1,
          tags: [],
        },
      },
    );
    expect(result.status).toBe(403);
    expect(testUser.username).toBeTruthy();
    const body = result.body as { code?: string } | null;
    expect(body?.code).toBe("csrf_invalid");
  });
});

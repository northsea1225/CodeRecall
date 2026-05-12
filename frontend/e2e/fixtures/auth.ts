/**
 * Test-scoped fixture: register a fresh user against the e2e backend, then
 * inject the resulting auth state (cookies + X-CSRF-Token + window.__E2E_API_BASE)
 * into Playwright's browser context so the AuthGuard sees us as logged in.
 *
 * Cookie-mode (C-005 Part 2):
 *   - access_token cookie (HttpOnly) and csrf_token cookie (not HttpOnly) are
 *     parsed from Set-Cookie headers on /auth/register and injected via
 *     context.addCookies with explicit domain+path.
 *   - The X-CSRF-Token header value is preserved for tests that need to make
 *     mutation requests outside the browser context (e.g. seed scripts).
 *
 * window.__E2E_API_BASE shim:
 *   - The frontend's api.ts / authStore.ts both prefer window.__E2E_API_BASE
 *     over import.meta.env.VITE_API_BASE_URL because vite dev-server's env
 *     injection doesn't reliably flow from playwright's webServer.env to a
 *     dev server that may already be running.
 */
import { test as base, expect, type Page, type BrowserContext } from "@playwright/test";
import { randomBytes } from "node:crypto";

const PASSWORD = "e2e-test-pass-1234";

export interface TestUser {
  username: string;
  password: string;
  userId: number;
  /** Bearer token retained for API seed scripts; the browser uses cookies. */
  token: string;
  /** CSRF token value mirrored from the csrf_token cookie + X-CSRF-Token header. */
  csrfToken: string;
  accessCookie: string;
}

interface RegisterResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  token_exp_at: string;
}

interface AuthCookies {
  accessToken: string;
  csrfToken: string;
}

function parseSetCookie(setCookieList: string[]): AuthCookies {
  let accessToken = "";
  let csrfToken = "";
  for (const raw of setCookieList) {
    // Each entry: "name=value; Path=...; HttpOnly; SameSite=Lax; Max-Age=..."
    const firstSemi = raw.indexOf(";");
    const head = firstSemi >= 0 ? raw.slice(0, firstSemi) : raw;
    const eq = head.indexOf("=");
    if (eq < 0) continue;
    const name = head.slice(0, eq).trim();
    const value = head.slice(eq + 1).trim();
    if (name === "access_token") accessToken = value;
    else if (name === "csrf_token") csrfToken = value;
  }
  return { accessToken, csrfToken };
}

async function registerUser(backendURL: string): Promise<TestUser> {
  const username = `e2e_${Date.now()}_${randomBytes(3).toString("hex")}`;
  const res = await fetch(`${backendURL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password: PASSWORD }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`register failed: ${res.status} ${text}`);
  }
  const body = (await res.json()) as RegisterResponse;

  // Set-Cookie may be split across multiple headers; node 20+ exposes them
  // via headers.getSetCookie(). Fallback to raw 'set-cookie' for older runners.
  const setCookies =
    typeof res.headers.getSetCookie === "function"
      ? res.headers.getSetCookie()
      : (res.headers.get("set-cookie")?.split(/,(?=\s*\w+=)/) ?? []);
  const { accessToken: accessCookie, csrfToken: csrfFromCookie } = parseSetCookie(setCookies);

  // Prefer X-CSRF-Token header (canonical), fall back to cookie-parsed value.
  const csrfFromHeader = res.headers.get("X-CSRF-Token") ?? "";
  const csrfToken = csrfFromHeader || csrfFromCookie;

  if (!accessCookie || !csrfToken) {
    throw new Error(
      `register response missing auth cookies: access=${!!accessCookie} csrf=${!!csrfToken}`,
    );
  }

  return {
    username,
    password: PASSWORD,
    userId: body.user_id,
    token: body.access_token,
    csrfToken,
    accessCookie,
  };
}

async function injectAuth(page: Page, user: TestUser, backendURL: string): Promise<void> {
  // 1) Tell the frontend bundle which backend port to talk to (cookie-mode lives
  //    or dies by this — without the override, axios hits :8000 = the dev /
  //    grok2api default and never gets logged in).
  const apiBase = `${backendURL}/api/v1`;
  await page.addInitScript((base: string) => {
    (window as Window & { __E2E_API_BASE?: string }).__E2E_API_BASE = base;
  }, apiBase);

  // 2) Inject both auth cookies on the BACKEND host so the browser sends them
  //    on credentialed XHRs to /api/v1/*. Both backend and frontend use
  //    "localhost" as the host (see fixtures/backend.ts) so the csrf_token
  //    cookie (HttpOnly=false) is also visible to document.cookie in the
  //    frontend origin, which is what the axios interceptor needs to inject
  //    X-CSRF-Token on mutation requests.
  const backendURLParsed = new URL(backendURL);
  const cookieDomain = backendURLParsed.hostname; // "localhost"
  const ctx: BrowserContext = page.context();
  await ctx.addCookies([
    {
      name: "access_token",
      value: user.accessCookie,
      domain: cookieDomain,
      path: "/api/v1",
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    },
    {
      name: "csrf_token",
      value: user.csrfToken,
      domain: cookieDomain,
      path: "/api/v1",
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
    },
  ]);
}

export function getBackendURL(): string {
  const url = process.env.E2E_BACKEND_URL;
  if (!url) {
    throw new Error(
      "E2E_BACKEND_URL not set; globalSetup (fixtures/backend.ts) must run first",
    );
  }
  return url;
}

interface AuthFixtures {
  testUser: TestUser;
  authenticatedPage: Page;
}

export const test = base.extend<AuthFixtures>({
  testUser: async ({}, use) => {
    const user = await registerUser(getBackendURL());
    await use(user);
  },
  authenticatedPage: async ({ page, testUser }, use) => {
    await injectAuth(page, testUser, getBackendURL());
    await use(page);
  },
});

export { expect };

/**
 * Test-scoped fixture that registers a fresh user against the e2e backend, then
 * injects the resulting JWT into localStorage so the AuthGuard sees us as logged in.
 *
 * Usage:
 *   import { test, expect } from "./fixtures/auth";
 *   test("...", async ({ authenticatedPage, testUser }) => { ... });
 *
 * The token storage key (`coderecall_token`) and JSON shape must mirror
 * `frontend/src/stores/authStore.ts` — keep these in sync.
 */
import { test as base, expect, type Page } from "@playwright/test";
import { randomBytes } from "node:crypto";

const TOKEN_KEY = "coderecall_token";
const PASSWORD = "e2e-test-pass-1234";

export interface TestUser {
  username: string;
  password: string;
  userId: number;
  token: string;
}

interface RegisterResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
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
  return {
    username,
    password: PASSWORD,
    userId: body.user_id,
    token: body.access_token,
  };
}

async function injectToken(page: Page, user: TestUser): Promise<void> {
  await page.addInitScript(
    ({ key, payload }) => {
      window.localStorage.setItem(key, JSON.stringify(payload));
    },
    {
      key: TOKEN_KEY,
      payload: {
        token: user.token,
        username: user.username,
        userId: user.userId,
      },
    },
  );
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
    await injectToken(page, testUser);
    await use(page);
  },
});

export { expect };

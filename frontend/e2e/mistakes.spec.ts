/**
 * Mistakes flow MVP — keep specs decoupled from the heavy MistakeEditor form
 * (Monaco editor + ~20 antd Form items) by seeding via API and validating the
 * list / detail pages through the UI.
 *
 * Scope (3 cases):
 *   1. Click "new mistake" button → /mistakes/new editor loads.
 *   2. API-created mistake renders in the list page.
 *   3. API-created mistake's detail/edit page pre-fills with backend data.
 */
import { test, expect, getBackendURL } from "./fixtures/auth";

interface CategoryOut {
  id: number;
  name: string;
}

interface MistakeOut {
  id: number;
  title: string;
}

async function authedFetch(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${getBackendURL()}${path}`, {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
}

async function createCategory(token: string, name: string): Promise<CategoryOut> {
  const res = await authedFetch("/api/v1/categories", token, {
    method: "POST",
    body: JSON.stringify({ name, description: "", sort_order: 0 }),
  });
  if (!res.ok) throw new Error(`category create failed: ${res.status} ${await res.text()}`);
  return (await res.json()) as CategoryOut;
}

async function createMistake(
  token: string,
  categoryId: number,
  overrides: Partial<{ title: string; difficulty: number; language: string }> = {},
): Promise<MistakeOut> {
  const body = {
    title: overrides.title ?? `e2e-mistake-${Date.now()}`,
    stem_markdown: "题面：求斐波那契数列第 n 项。",
    wrong_answer_markdown: "递归无记忆化导致 TLE。",
    correct_answer_markdown: "动态规划 O(n) 时间复杂度。",
    error_reason_markdown: "忽略了重复子问题。",
    language: overrides.language ?? "cpp",
    difficulty: overrides.difficulty ?? 3,
    source: "",
    is_archived: false,
    category_id: categoryId,
    tags: ["dp"],
  };
  const res = await authedFetch("/api/v1/mistakes", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`mistake create failed: ${res.status} ${await res.text()}`);
  return (await res.json()) as MistakeOut;
}

test.describe("Mistakes UI", () => {
  test("click 'new mistake' button → editor route loads", async ({
    authenticatedPage: page,
    testUser,
  }) => {
    // Seed one category + one mistake so the list page (not the onboarding page) is rendered.
    const category = await createCategory(testUser.token, `e2e-cat-${Date.now()}`);
    await createMistake(testUser.token, category.id);

    await page.goto("/mistakes");
    // List page header has a primary "new" button at the top.
    await page
      .locator(".page-title-row button.ant-btn-primary")
      .first()
      .click();

    await expect(page).toHaveURL(/\/mistakes\/new/);
  });

  test("API-created mistake appears in the list", async ({
    authenticatedPage: page,
    testUser,
  }) => {
    const category = await createCategory(testUser.token, `e2e-cat-${Date.now()}-l`);
    const title = `e2e-list-${Date.now()}`;
    await createMistake(testUser.token, category.id, { title });

    await page.goto("/mistakes");
    // The title text is rendered exactly somewhere on the list page.
    await expect(page.getByText(title, { exact: true }).first()).toBeVisible();
  });

  test("mistake detail page pre-fills from backend", async ({
    authenticatedPage: page,
    testUser,
  }) => {
    const category = await createCategory(testUser.token, `e2e-cat-${Date.now()}-d`);
    const title = `e2e-detail-${Date.now()}`;
    const mistake = await createMistake(testUser.token, category.id, { title });

    await page.goto(`/mistakes/${mistake.id}/edit`);
    // Title input is the first Form.Item with name="title"; antd Input is rendered as <input>.
    const titleInput = page.locator('input#title, input[name="title"]').first();
    await expect(titleInput).toHaveValue(title);
  });
});

/**
 * Onboarding flow MVP — verifies the empty-state experience for fresh users.
 *
 * Trigger condition (mirrors MistakeList/index.tsx:208):
 *   hasFetched && !loading && !error && isUnfiltered && pagination.total === 0 &&
 *   !localStorage.getItem(`coderecall_ever_imported_${userId}`)
 *
 * Scope (3 cases):
 *   1. fresh user → OnboardingPage hero copy is visible.
 *   2. click "load demo" → list re-renders with seeded mistakes.
 *   3. importing flag pre-set → OnboardingPage stays hidden even with empty list.
 */
import { test, expect } from "./fixtures/auth";

const ONBOARDING_HERO_TEXT = "AC 的最后一块拼图";
const ONBOARDING_DEMO_BUTTON_TEXT = /载入经典错误 Demo/;

test.describe("Onboarding empty state", () => {
  test("fresh user lands on OnboardingPage", async ({ authenticatedPage: page }) => {
    await page.goto("/mistakes");

    // Hero title from `onboarding.heroTitle` (zh-CN) — exact phrase is unique to OnboardingPage.
    await expect(page.getByText(ONBOARDING_HERO_TEXT).first()).toBeVisible();
    // The demo button is a primary CTA and must be enabled.
    await expect(page.getByRole("button", { name: ONBOARDING_DEMO_BUTTON_TEXT })).toBeVisible();
  });

  test("loadDemo seeds mistakes and the list takes over", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/mistakes");
    await expect(page.getByText(ONBOARDING_HERO_TEXT).first()).toBeVisible();

    const demoButton = page.getByRole("button", { name: ONBOARDING_DEMO_BUTTON_TEXT });
    await demoButton.click();

    // After import succeeds, OnboardingPage unmounts and the list page renders.
    // Confirm by checking the hero text is gone (best signal that the empty-state branch flipped).
    await expect(page.getByText(ONBOARDING_HERO_TEXT)).toHaveCount(0, { timeout: 10_000 });
    // demoImportPayload.json contains 4 classic C++ mistakes; the first one's title
    // ("线段树区间求和漏判懒标记下推") is unique enough to look for.
    await expect(page.getByText(/线段树|背包|Dijkstra|int 溢出/).first()).toBeVisible();
  });

  test("ever-imported flag suppresses OnboardingPage", async ({
    authenticatedPage: page,
    testUser,
  }) => {
    // Pre-seed the localStorage flag before the page boots, mirroring what
    // OnboardingPage.handleLoadDemo writes after a successful import.
    await page.addInitScript((userId) => {
      window.localStorage.setItem(`coderecall_ever_imported_${userId}`, "1");
    }, testUser.userId);

    await page.goto("/mistakes");
    // No onboarding hero, even though the list is empty.
    await expect(page.getByText(ONBOARDING_HERO_TEXT)).toHaveCount(0);
    // The empty-list branch in MistakeList still renders the page header copy.
    // We don't assert on its text (i18n-volatile) — absence of OnboardingPage is the
    // contract being verified.
  });
});

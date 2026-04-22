# W4 Day 2 — Codex Engineering Report

Date: 2026-04-20

---

## Task #13: Test Suite Baseline

### Backend (pytest)

Command: `.venv/bin/pytest --tb=short -q`

Result: **75 passed, 0 failures** in 29.56s ✓

### Frontend (vitest)

Command: `npm run test -- --run`

Result: **28 passed across 7 test files**, 0 failures ✓

```
src/pages/MistakeEditor/form.test.ts        (3 tests)
src/utils/monacoLanguage.test.ts            (2 tests)
src/services/reviewService.test.ts          (7 tests)
src/stores/uiStore.test.ts                  (2 tests)
src/services/api.test.ts                    (2 tests)
src/stores/reviewStore.test.ts              (8 tests)
src/stores/mistakeStore.test.ts             (4 tests)
```

### TypeScript

Command: `npx tsc --noEmit`

Result: **0 errors** ✓

---

## Task #14: Boundary Case Audit

### Scenario 1 — Empty DB / no mistakes (due_count=0, empty list)

**File:** `frontend/src/pages/Dashboard/index.tsx`

- Line 28: `dueCount` initialises to `0`, so no crash before API responds.
- Line 124–129: When `dueCount === 0`, the "Start Review" button renders with text "今日无到期题，仍可随机复习" and uses strategy `"random"`. No conditional render that could white-screen.
- Line 149–195: When `totalMistakes === 0`, a dedicated empty-state card is rendered (lines 150–160) with an "Add First Mistake" CTA. The `panel-grid` section is only rendered when `totalMistakes > 0` — no white-screen risk.
- Error state (line 95–108): Full-page `<Result status="500">` with retry button.

**Verdict: PASS** — Empty DB is fully handled with a clean empty-state UI and no white-screen scenarios.

---

### Scenario 2 — All mastered (session starts with progress.total === 0)

**File:** `frontend/src/pages/Review/index.tsx` lines 139–156

```tsx
if (sessionId && progress.total === 0 && !completed) {
  return (
    <ReviewPageState
      status="success"
      title="恭喜！今天没有需要复习的错题"
      resultSubtitle="休息一下，或去录入新的错题。"
      ...
    />
  );
}
```

The backend `startReviewSession` returns a session with `total_count=0` when all items are mastered (or none are due). The store sets `progress.total = response.total_count` at line 119 (`reviewStore.ts`). The Review page guards this with the block above.

- Pre-session start (`!sessionId && !loading`): A strategy selector and "开始复习" button are shown (lines 82–107). The user can still start a session; the empty-queue guard fires after the session is created.
- Dashboard: When `dueCount === 0` (all mastered), the button still allows random review.

**Verdict: PASS** — All-mastered case produces a "恭喜" success message with navigation options, not an empty or broken view.

---

### Scenario 3 — AI timeout / SSE failure doesn't break main review flow

**File:** `frontend/src/hooks/useAiAnalysisStream.ts` lines 86–109

The `source.onerror` handler:
1. Closes the EventSource.
2. Sets `snapshot.status = "error"` with a human-readable Chinese error string.
3. Preserves any already-received `content` in state.

**File:** `frontend/src/components/review/AiAnalysisPanel.tsx` lines 58–74

When `status === "error"`, an Ant Design `<Alert type="error">` is shown with a 重试 button. The rest of the review UI (DiffViewer, SelfRateGroup) is rendered independently in `AnswerView` — the AI panel failure does not affect self-rating or navigation.

**File:** `backend/app/api/routes/ai.py` lines 84–88

Backend sends a named `event: error` SSE event on `AiAnalysisError`. The frontend `source.onerror` catches generic errors; the named `event: error` lands in `source.onerror` because `EventSource` treats non-`message` events as errors by default. The error message is surfaced.

**Minor concern:** `source.addEventListener("error", ...)` is not used for the named `event: error` SSE event from the backend. The backend sends `event: error\ndata: {...}`, but the frontend only registers `source.onerror`, which handles network-level errors. The named SSE error event would require `source.addEventListener("error", ...)`. In practice the stream ends after this event and `onerror` fires, so the user does still see an error panel, but the structured `code`/`message` payload from the backend is not parsed in this path (the `messageEvent.data` check at line 90 would be empty for a network error). This is a minor UX gap — error message falls back to the generic "AI 分析失败，请稍后重试。" string.

**Verdict: PASS** (with minor note) — The review flow continues regardless of AI failure. Self-rating and navigation are unaffected. The specific backend error message is not surfaced in the named-SSE-error path, but a friendly fallback is shown.

---

## Task #15: 4xx/5xx Frontend Error Handling Audit

### API Layer

**File:** `frontend/src/services/api.ts` lines 49–61

The axios response interceptor converts all non-2xx responses into `ApiClientError` with:
- `message`: backend `payload.message` → `error.message` → `"Request failed."` (never `undefined` or empty)
- `status`: HTTP status code
- `code`: backend error code
- `detail`: backend detail object

`extractApiErrorMessage()` (lines 23–38) always returns a non-empty string.

### 1. Submit Review (submitRate)

**File:** `frontend/src/stores/reviewStore.ts` lines 254–258

```ts
} catch (error) {
  set({ submitting: false, error: extractApiErrorMessage(error) });
}
```

The error string is set in store state. The Review page renders it at line 182 as `<Alert type="error" message={error} showIcon />`. Visible to user.

**Verdict: PASS** — 4xx/5xx produces a visible in-page Alert with a human-readable message.

### 2. Fetch Mistakes (fetchList in MistakeList)

**File:** `frontend/src/stores/mistakeStore.ts` lines 73–76

```ts
} catch (error) {
  set({ loading: false, error: extractApiErrorMessage(error) });
}
```

**File:** `frontend/src/pages/MistakeList/index.tsx` line 245

```tsx
{error ? <Alert type="error" message={error} showIcon /> : null}
```

**Verdict: PASS** — Error is displayed in-page above the table.

### 3. Start Session (startSession)

**File:** `frontend/src/stores/reviewStore.ts` lines 131–136

```ts
} catch (error) {
  set({ ...defaultState, loading: false, error: extractApiErrorMessage(error) });
}
```

The Review page renders the error at line 117–137 as a full-page `<ReviewPageState status="error">` with retry button.

**Verdict: PASS** — 4xx/5xx during session start produces a full-page error view with retry.

### 4. Network errors (fetch fails)

Axios treats network errors (no response) as `AxiosError` with `error.response === undefined`. `extractApiErrorMessage` falls through to `error.message` (the axios network error message, e.g. "Network Error"). This is human-readable.

**File:** `frontend/src/services/api.ts` line 54

```ts
payload?.message ?? error.message ?? "Request failed."
```

When `payload` is undefined (no response), `error.message` is used — axios sets this to "Network Error" for connection failures.

**Verdict: PASS** — Network errors produce "Network Error" message, not `undefined` or empty string.

### 5. MistakeEditor save errors

**File:** `frontend/src/pages/MistakeEditor/index.tsx` lines 159–167

```ts
} catch (saveError) {
  if (saveError instanceof Error && saveError.message === "Category is required.") {
    showToast("error", saveError.message);
  } else if (!(saveError instanceof Error && saveError.name === "Error" && saveError.message === "")) {
    showToast("error", saveError instanceof Error ? saveError.message : "Save failed.");
  }
}
```

The `else if` guard (`name === "Error" && message === ""`) is intended to silently swallow Ant Design form validation rejections (which throw an empty Error). For actual API errors, `showToast("error", ...)` is called.

**Minor concern (lines 162–164):** The guard condition `saveError.name === "Error" && saveError.message === ""` will also silently swallow any genuine `Error` with an empty message string. In practice Ant Design form validation does produce exactly this, and API errors always have a message from the interceptor, so this is safe in current usage — but fragile.

**Verdict: PASS** (with minor note) — API errors surface as toast notifications with human-readable messages.

---

## Summary

| Task | Result |
|------|--------|
| #13 Backend tests | 75/75 passed, 0 failures |
| #13 Frontend tests | 28/28 passed, 0 failures |
| #13 TypeScript | 0 errors |
| #14 Scenario 1 (empty DB) | PASS |
| #14 Scenario 2 (all mastered) | PASS |
| #14 Scenario 3 (AI timeout) | PASS (minor: named SSE error payload not parsed) |
| #15 Submit review errors | PASS |
| #15 Fetch mistakes errors | PASS |
| #15 Start session errors | PASS |
| #15 Network errors | PASS |
| #15 MistakeEditor save errors | PASS (minor: empty-Error guard is fragile) |

### Minor Issues (no blocker)

1. **`frontend/src/hooks/useAiAnalysisStream.ts` line 86–109**: The backend named SSE `event: error` with structured JSON payload is not parsed in the `onerror` handler. The fallback message "AI 分析失败，请稍后重试。" is shown instead of the backend's specific error message. Fix: add `source.addEventListener("error", handler)` alongside `source.onerror`.

2. **`frontend/src/pages/MistakeEditor/index.tsx` lines 162–164**: The silent-swallow guard for Ant Design form validation (`name === "Error" && message === ""`) is fragile. A genuine API error that somehow arrives with an empty message would be swallowed. Consider checking `error instanceof ApiClientError` instead.

import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock("./api", () => ({
  api: {
    get: mockGet,
    post: mockPost,
  },
}));

import {
  getDueCount,
  getNextReviewItem,
  getReviewCapability,
  getReviewSummary,
  revealReviewItem,
  startReviewSession,
  submitReviewResult,
} from "./reviewService";

describe("reviewService", () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it("startReviewSession posts strategy and limit payload", async () => {
    mockPost.mockResolvedValue({
      data: {
        id: 7,
        strategy: "random",
        started_at: "2026-04-28T08:00:00Z",
        total_count: 2,
        completed_count: 0,
        next_item: null,
      },
    });

    await startReviewSession({ strategy: "spaced_repetition", limit: 3 });

    expect(mockPost).toHaveBeenCalledWith("/review/sessions", {
      strategy: "spaced_repetition",
      limit: 3,
    });
  });

  it("getNextReviewItem requests the next endpoint with session id", async () => {
    mockGet.mockResolvedValue({
      data: {
        next_item: null,
        progress: { completed: 1, total: 2 },
      },
    });

    await getNextReviewItem(42);

    expect(mockGet).toHaveBeenCalledWith("/review/sessions/42/next");
  });

  it("submitReviewResult posts payload to the submit endpoint", async () => {
    mockPost.mockResolvedValue({
      data: {
        id: 90,
        mistake_id: 11,
        session_id: 7,
        review_mode: "random",
        user_result: "good",
        shown_at: "2026-04-28T08:00:00Z",
        answered_at: "2026-04-28T08:01:00Z",
        time_spent_ms: 12000,
        note: "ok",
        progress: { completed: 1, total: 2 },
      },
    });

    await submitReviewResult(7, {
      mistake_id: 11,
      user_result: "good",
      shown_at: "2026-04-28T08:00:00Z",
      time_spent_ms: 12000,
      note: "ok",
    });

    expect(mockPost).toHaveBeenCalledWith("/review/sessions/7/submit", {
      mistake_id: 11,
      user_result: "good",
      shown_at: "2026-04-28T08:00:00Z",
      time_spent_ms: 12000,
      note: "ok",
    });
  });

  it("getReviewSummary requests the summary endpoint", async () => {
    mockGet.mockResolvedValue({
      data: {
        total_count: 2,
        completed_count: 2,
        result_counts: { again: 0, hard: 0, good: 2, easy: 0 },
        duration_ms: 1000,
      },
    });

    await getReviewSummary(7);

    expect(mockGet).toHaveBeenCalledWith("/review/sessions/7/summary");
  });

  it("getReviewCapability requests the capability endpoint", async () => {
    mockGet.mockResolvedValue({
      data: {
        ai_analysis_enabled: true,
        model: "gpt-5.4-mini",
      },
    });

    await getReviewCapability();

    expect(mockGet).toHaveBeenCalledWith("/review/capability");
  });

  it("getDueCount requests the due-count endpoint", async () => {
    mockGet.mockResolvedValue({
      data: {
        due_count: 3,
        as_of: "2026-05-02T08:00:00Z",
      },
    });

    const payload = await getDueCount();

    expect(mockGet).toHaveBeenCalledWith("/review/due-count");
    expect(payload.due_count).toBe(3);
  });

  it("revealReviewItem requests the reveal endpoint", async () => {
    mockGet.mockResolvedValue({
      data: {
        mistake_id: 11,
        title: "两数之和",
        stem_markdown: "题面",
        wrong_answer_markdown: "wrong",
        correct_answer_markdown: "correct",
        error_reason_markdown: "reason",
        language: "python",
        difficulty: 2,
        category_name: "哈希表",
        tag_names: [],
      },
    });

    await revealReviewItem(11);

    expect(mockGet).toHaveBeenCalledWith("/review/items/11/reveal");
  });
});

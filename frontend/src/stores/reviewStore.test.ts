import { describe, expect, it, vi } from "vitest";

import { createReviewStore } from "./reviewStore";

describe("reviewStore", () => {
  const firstItem = {
    mistake_id: 11,
    title: "两数之和哈希遗漏",
    stem_markdown: "给定数组 nums 和 target。",
    language: "python",
    difficulty: 2,
    category_name: "哈希表",
    tag_names: ["哈希", "边界"],
    shown_at: "2026-04-24T08:00:00Z",
  };

  const revealPayload = {
    mistake_id: 11,
    title: "两数之和哈希遗漏",
    stem_markdown: "给定数组 nums 和 target。",
    wrong_answer_markdown: "for i in range(len(nums)): pass",
    correct_answer_markdown: "seen = {}",
    error_reason_markdown: "没有先判断补数。",
    language: "python",
    difficulty: 2,
    category_name: "哈希表",
    tag_names: ["哈希", "边界"],
  };

  it("startSession stores current item and progress", async () => {
    const getCapability = vi.fn().mockResolvedValue({
      ai_analysis_enabled: true,
      model: "gpt-5.4-mini",
    });
    const store = createReviewStore({
      startSession: vi.fn().mockResolvedValue({
        id: 7,
        strategy: "random",
        started_at: "2026-04-24T08:00:00Z",
        total_count: 2,
        completed_count: 0,
        next_item: firstItem,
      }),
      getNextItem: vi.fn(),
      revealItem: vi.fn(),
      submitResult: vi.fn(),
      getSummary: vi.fn(),
      getCapability,
    });

    await store.getState().startSession();

    expect(getCapability).toHaveBeenCalledTimes(1);
    expect(store.getState().sessionId).toBe(7);
    expect(store.getState().strategy).toBe("random");
    expect(store.getState().progress).toEqual({ completed: 0, total: 2 });
    expect(store.getState().currentItem).toEqual(firstItem);
    expect(store.getState().capability).toEqual({
      ai_analysis_enabled: true,
      model: "gpt-5.4-mini",
    });
    expect(store.getState().error).toBeNull();
  });

  it("startSession defaults to the current strategy when payload omits strategy", async () => {
    const startSession = vi.fn().mockResolvedValue({
      id: 8,
      strategy: "due_first",
      started_at: "2026-05-02T08:00:00Z",
      total_count: 1,
      completed_count: 0,
      next_item: firstItem,
    });
    const store = createReviewStore({
      startSession,
      getNextItem: vi.fn(),
      revealItem: vi.fn(),
      submitResult: vi.fn(),
      getSummary: vi.fn(),
      getCapability: vi.fn(),
    });
    store.setState({ strategy: "due_first" });

    await store.getState().startSession();

    expect(startSession).toHaveBeenCalledWith({
      strategy: "due_first",
      limit: 10,
    });
  });

  it("startSession stores error when session bootstrap fails", async () => {
    const store = createReviewStore({
      startSession: vi.fn().mockRejectedValue(new Error("session bootstrap failed")),
      getNextItem: vi.fn(),
      revealItem: vi.fn(),
      submitResult: vi.fn(),
      getSummary: vi.fn(),
      getCapability: vi.fn().mockResolvedValue({
        ai_analysis_enabled: true,
        model: "gpt-5.4-mini",
      }),
    });

    await store.getState().startSession();

    expect(store.getState().sessionId).toBeNull();
    expect(store.getState().loading).toBe(false);
    expect(store.getState().error).toBe("session bootstrap failed");
  });

  it("showAnswer loads reveal payload and enters showingAnswer state", async () => {
    const revealItem = vi.fn().mockResolvedValue(revealPayload);
    const store = createReviewStore({
      startSession: vi.fn().mockResolvedValue({
        id: 7,
        strategy: "random",
        started_at: "2026-04-24T08:00:00Z",
        total_count: 1,
        completed_count: 0,
        next_item: firstItem,
      }),
      getNextItem: vi.fn(),
      revealItem,
      submitResult: vi.fn(),
      getSummary: vi.fn(),
      getCapability: vi.fn(),
    });

    await store.getState().startSession();
    await store.getState().showAnswer();

    expect(revealItem).toHaveBeenCalledWith(11);
    expect(store.getState().showingAnswer).toBe(true);
    expect(store.getState().revealedData).toEqual(revealPayload);
  });

  it("loadNext switches to completed state when queue is exhausted", async () => {
    const getSummary = vi.fn().mockResolvedValue({
      total_count: 2,
      completed_count: 2,
      result_counts: {
        again: 1,
        hard: 0,
        good: 1,
        easy: 0,
      },
      duration_ms: 120000,
    });
    const store = createReviewStore({
      startSession: vi.fn().mockResolvedValue({
        id: 7,
        strategy: "random",
        started_at: "2026-04-24T08:00:00Z",
        total_count: 2,
        completed_count: 1,
        next_item: firstItem,
      }),
      getNextItem: vi.fn().mockResolvedValue({
        next_item: null,
        progress: {
          completed: 2,
          total: 2,
        },
      }),
      revealItem: vi.fn(),
      submitResult: vi.fn(),
      getSummary,
      getCapability: vi.fn(),
    });

    await store.getState().startSession();
    await store.getState().loadNext();

    expect(getSummary).toHaveBeenCalledWith(7);
    expect(store.getState().completed).toBe(true);
    expect(store.getState().currentItem).toBeNull();
    expect(store.getState().summary?.result_counts.again).toBe(1);
  });

  it("submitRate advances to the next item when session is not finished", async () => {
    const secondItem = {
      ...firstItem,
      mistake_id: 12,
      title: "滑动窗口边界错位",
    };
    const getNextItem = vi.fn().mockResolvedValue({
      next_item: secondItem,
      progress: {
        completed: 1,
        total: 2,
      },
    });
    const submitResult = vi.fn().mockResolvedValue({
      id: 90,
      mistake_id: 11,
      session_id: 7,
      review_mode: "random",
      user_result: "good",
      shown_at: "2026-04-24T08:01:00Z",
      answered_at: "2026-04-24T08:02:00Z",
      note: "",
      progress: {
        completed: 1,
        total: 2,
      },
    });
    const store = createReviewStore({
      startSession: vi.fn().mockResolvedValue({
        id: 7,
        strategy: "random",
        started_at: "2026-04-24T08:00:00Z",
        total_count: 2,
        completed_count: 0,
        next_item: firstItem,
      }),
      getNextItem,
      revealItem: vi.fn().mockResolvedValue(revealPayload),
      submitResult,
      getSummary: vi.fn(),
      getCapability: vi.fn(),
    });

    await store.getState().startSession();
    await store.getState().showAnswer();
    await store.getState().submitRate("good", { time_spent_ms: 42000, note: "keep going" });

    expect(submitResult).toHaveBeenCalledWith(7, {
      mistake_id: 11,
      user_result: "good",
      shown_at: "2026-04-24T08:00:00Z",
      time_spent_ms: 42000,
      note: "keep going",
    });
    expect(getNextItem).toHaveBeenCalledWith(7);
    expect(store.getState().currentItem).toEqual(secondItem);
    expect(store.getState().showingAnswer).toBe(false);
    expect(store.getState().submitting).toBe(false);
  });

  it("submitRate marks session completed when last item is submitted", async () => {
    const getSummary = vi.fn().mockResolvedValue({
      total_count: 1,
      completed_count: 1,
      result_counts: {
        again: 0,
        hard: 0,
        good: 1,
        easy: 0,
      },
      duration_ms: 120000,
    });
    const store = createReviewStore({
      startSession: vi.fn().mockResolvedValue({
        id: 7,
        strategy: "random",
        started_at: "2026-04-24T08:00:00Z",
        total_count: 1,
        completed_count: 0,
        next_item: firstItem,
      }),
      getNextItem: vi.fn(),
      revealItem: vi.fn().mockResolvedValue(revealPayload),
      submitResult: vi.fn().mockResolvedValue({
        id: 90,
        mistake_id: 11,
        session_id: 7,
        review_mode: "random",
        user_result: "good",
        shown_at: "2026-04-24T08:01:00Z",
        answered_at: "2026-04-24T08:02:00Z",
        note: "",
        progress: {
          completed: 1,
          total: 1,
        },
      }),
      getSummary,
      getCapability: vi.fn(),
    });

    await store.getState().startSession();
    await store.getState().showAnswer();
    await store.getState().submitRate("good");

    expect(getSummary).toHaveBeenCalledWith(7);
    expect(store.getState().completed).toBe(true);
    expect(store.getState().summary?.completed_count).toBe(1);
    expect(store.getState().currentItem).toBeNull();
  });

  it("submitRate keeps error state when submission fails", async () => {
    const store = createReviewStore({
      startSession: vi.fn().mockResolvedValue({
        id: 7,
        strategy: "random",
        started_at: "2026-04-24T08:00:00Z",
        total_count: 1,
        completed_count: 0,
        next_item: firstItem,
      }),
      getNextItem: vi.fn(),
      revealItem: vi.fn().mockResolvedValue(revealPayload),
      submitResult: vi.fn().mockRejectedValue(new Error("submit failed")),
      getSummary: vi.fn(),
      getCapability: vi.fn(),
    });

    await store.getState().startSession();
    await store.getState().showAnswer();
    await store.getState().submitRate("again");

    expect(store.getState().submitting).toBe(false);
    expect(store.getState().error).toBe("submit failed");
    expect(store.getState().currentItem).toEqual(firstItem);
    expect(store.getState().showingAnswer).toBe(true);
  });
});

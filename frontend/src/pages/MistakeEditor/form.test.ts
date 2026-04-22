import { describe, expect, it } from "vitest";

import { createEmptyDraft, draftToCreatePayload, draftToUpdatePayload, mistakeToDraft } from "./form";

describe("mistake editor form mapping", () => {
  it("creates a blank draft with safe defaults", () => {
    expect(createEmptyDraft()).toEqual({
      title: "",
      stem_markdown: "",
      wrong_answer_markdown: "",
      correct_answer_markdown: "",
      error_reason_markdown: "",
      category_id: undefined,
      tags: [],
      language: "plaintext",
      difficulty: 3,
      source: "",
      status: "new",
    });
  });

  it("maps api mistake detail into draft fields", () => {
    expect(
      mistakeToDraft({
        id: 1,
        title: "Hash map miss",
        stem_markdown: "stem",
        wrong_answer_markdown: "wrong",
        correct_answer_markdown: "correct",
        error_reason_markdown: "reason",
        language: "python",
        difficulty: 4,
        source: "LeetCode",
        status: "new",
        review_count: 0,
        last_reviewed_at: null,
        next_review_at: null,
        ease_factor: 2.5,
        interval_days: 0,
        repetition: 0,
        is_archived: false,
        category: {
          id: 2,
          name: "哈希表",
          description: "",
          parent_id: null,
          sort_order: 0,
          created_at: "2026-04-18T08:00:00Z",
          updated_at: "2026-04-18T08:00:00Z",
        },
        tags: [
          {
            id: 7,
            name: "边界条件",
            created_at: "2026-04-18T08:00:00Z",
            updated_at: "2026-04-18T08:00:00Z",
          },
        ],
        created_at: "2026-04-18T08:00:00Z",
        updated_at: "2026-04-18T08:00:00Z",
      }),
    ).toMatchObject({
      category_id: 2,
      tags: ["边界条件"],
      difficulty: 4,
      language: "python",
    });
  });

  it("builds create and update payloads from draft", () => {
    const draft = {
      title: "Title",
      stem_markdown: "Stem",
      wrong_answer_markdown: "Wrong",
      correct_answer_markdown: "Correct",
      error_reason_markdown: "Reason",
      category_id: 3,
      tags: ["双指针"],
      language: "typescript",
      difficulty: 5,
      source: "Interview",
      status: "new" as const,
    };

    expect(draftToCreatePayload(draft)).toEqual({
      ...draft,
      category_id: 3,
      tags: ["双指针"],
    });

    expect(draftToUpdatePayload(draft)).toEqual({
      title: "Title",
      stem_markdown: "Stem",
      wrong_answer_markdown: "Wrong",
      correct_answer_markdown: "Correct",
      error_reason_markdown: "Reason",
      category_id: 3,
      tags: ["双指针"],
      language: "typescript",
      difficulty: 5,
      source: "Interview",
    });
  });
});

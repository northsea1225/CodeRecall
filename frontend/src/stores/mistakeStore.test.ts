import { describe, expect, it, vi } from "vitest";

import { createMistakeStore } from "./mistakeStore";

describe("mistakeStore", () => {
  it("fetchList updates items and pagination from service response", async () => {
    const listMistakes = vi.fn().mockResolvedValue({
      items: [
        {
          id: 1,
          title: "Off by one",
          stem_markdown: "",
          wrong_answer_markdown: "",
          correct_answer_markdown: "",
          error_reason_markdown: "",
          language: "python",
          difficulty: 2,
          source: "LeetCode",
          status: "new",
          category: {
            id: 2,
            name: "数组",
            description: "",
            parent_id: null,
            sort_order: 0,
            created_at: "2026-04-18T08:00:00Z",
            updated_at: "2026-04-18T08:00:00Z",
          },
          tags: [],
          created_at: "2026-04-18T08:00:00Z",
          updated_at: "2026-04-18T08:00:00Z",
        },
      ],
      total: 1,
      pagination: {
        total: 1,
        page: 2,
        page_size: 10,
      },
    });

    const store = createMistakeStore({ listMistakes });

    store.getState().setFilter({ page: 2, pageSize: 10, categoryId: 2, keyword: "hash" });
    await store.getState().fetchList();

    expect(listMistakes).toHaveBeenCalledWith({
      page: 2,
      page_size: 10,
      category_id: 2,
      keyword: "hash",
      language: undefined,
    });
    expect(store.getState().list).toHaveLength(1);
    expect(store.getState().pagination.page).toBe(2);
    expect(store.getState().error).toBeNull();
  });

  it("reset restores default filters", () => {
    const store = createMistakeStore({
      listMistakes: vi.fn(),
    });

    store.getState().setFilter({ page: 3, pageSize: 50, categoryId: 9, keyword: "hash" });
    store.getState().reset();

    expect(store.getState().filters).toEqual({
      page: 1,
      pageSize: 10,
      categoryId: undefined,
      keyword: "",
      language: undefined,
    });
  });

  it("resets page to 1 when keyword, category, or language changes", () => {
    const store = createMistakeStore({
      listMistakes: vi.fn(),
    });

    store.getState().setFilter({ page: 4, pageSize: 10 });
    expect(store.getState().filters.page).toBe(4);

    store.getState().setFilter({ keyword: "binary search" });
    expect(store.getState().filters.page).toBe(1);

    store.getState().setFilter({ page: 3 });
    store.getState().setFilter({ categoryId: 7 });
    expect(store.getState().filters.page).toBe(1);

    store.getState().setFilter({ page: 2 });
    store.getState().setFilter({ language: "python" });
    expect(store.getState().filters.page).toBe(1);
  });

  it("keeps current page when only pagination changes", () => {
    const store = createMistakeStore({
      listMistakes: vi.fn(),
    });

    store.getState().setFilter({ page: 5, pageSize: 20 });

    expect(store.getState().filters).toEqual({
      page: 5,
      pageSize: 20,
      categoryId: undefined,
      keyword: "",
      language: undefined,
    });
  });
});

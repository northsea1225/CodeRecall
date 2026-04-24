import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";

import { extractApiErrorMessage } from "../services/api";
import { listMistakes as listMistakesService } from "../services/mistakeService";
import type { Mistake, PaginationMeta } from "../types/mistake";

export interface MistakeFilters {
  page: number;
  pageSize: number;
  categoryId?: number;
  keyword: string;
  language?: string;
}

export interface MistakeStoreState {
  list: Mistake[];
  pagination: PaginationMeta;
  filters: MistakeFilters;
  hasFetched: boolean;
  loading: boolean;
  error: string | null;
  fetchList: () => Promise<void>;
  setFilter: (filters: Partial<MistakeFilters>) => void;
  reset: () => void;
}

interface MistakeStoreDeps {
  listMistakes: typeof listMistakesService;
}

const defaultFilters: MistakeFilters = {
  page: 1,
  pageSize: 10,
  categoryId: undefined,
  keyword: "",
  language: undefined,
};

const defaultPagination: PaginationMeta = {
  total: 0,
  page: 1,
  page_size: 10,
};

export const createMistakeStore = (
  deps: MistakeStoreDeps = { listMistakes: listMistakesService },
) =>
  createStore<MistakeStoreState>((set, get) => ({
    list: [],
    pagination: defaultPagination,
    filters: defaultFilters,
    hasFetched: false,
    loading: false,
    error: null,
    fetchList: async () => {
      set({ loading: true, error: null });

      try {
        const { filters } = get();
        const response = await deps.listMistakes({
          page: filters.page,
          page_size: filters.pageSize,
          category_id: filters.categoryId,
          language: filters.language,
          keyword: filters.keyword,
        });

        set({
          list: response.items,
          pagination: response.pagination,
          hasFetched: true,
          loading: false,
          error: null,
        });
      } catch (error) {
        set({
          hasFetched: true,
          loading: false,
          error: extractApiErrorMessage(error),
        });
      }
    },
    setFilter: (filters) =>
      set((state) => {
        const nextFilters = {
          ...state.filters,
          ...filters,
        };

        if ("categoryId" in filters || "keyword" in filters || "language" in filters) {
          nextFilters.page = filters.page ?? 1;
        }

        return { filters: nextFilters };
      }),
    reset: () =>
      set({
        filters: defaultFilters,
        pagination: defaultPagination,
        error: null,
        hasFetched: false,
      }),
  }));

export const mistakeStore = createMistakeStore();

export const useMistakeStore = <T,>(selector: (state: MistakeStoreState) => T): T =>
  useStore(mistakeStore, selector);

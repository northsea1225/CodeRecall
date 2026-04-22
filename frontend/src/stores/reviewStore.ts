import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";

import { extractApiErrorMessage } from "../services/api";
import {
  getNextReviewItem as getNextReviewItemService,
  getReviewCapability as getReviewCapabilityService,
  getReviewSummary as getReviewSummaryService,
  revealReviewItem as revealReviewItemService,
  startReviewSession as startReviewSessionService,
  submitReviewResult as submitReviewResultService,
} from "../services/reviewService";
import type {
  ReviewCapability,
  ReviewItem,
  ReviewProgress,
  ReviewResult,
  ReviewReveal,
  ReviewSessionStartPayload,
  ReviewStrategy,
  ReviewSubmitPayload,
  ReviewSummary,
} from "../types/review";

export interface ReviewStoreState {
  sessionId: number | null;
  strategy: ReviewStrategy | null;
  progress: ReviewProgress;
  capability: ReviewCapability;
  currentItem: ReviewItem | null;
  showingAnswer: boolean;
  revealedData: ReviewReveal | null;
  loading: boolean;
  submitting: boolean;
  completed: boolean;
  summary: ReviewSummary | null;
  error: string | null;
  userAttemptMarkdown: string;
  setUserAttemptMarkdown: (value: string) => void;
  clearUserAttempt: () => void;
  startSession: (payload?: Partial<ReviewSessionStartPayload>) => Promise<void>;
  loadNext: () => Promise<void>;
  showAnswer: () => Promise<void>;
  submitRate: (userResult: ReviewResult, options?: Omit<ReviewSubmitPayload, "mistake_id" | "user_result">) => Promise<void>;
  exitSession: () => void;
  reset: () => void;
}

interface ReviewStoreDeps {
  startSession: typeof startReviewSessionService;
  getNextItem: typeof getNextReviewItemService;
  revealItem: typeof revealReviewItemService;
  submitResult: typeof submitReviewResultService;
  getSummary: typeof getReviewSummaryService;
  getCapability: typeof getReviewCapabilityService;
}

const defaultProgress: ReviewProgress = {
  completed: 0,
  total: 0,
};

const defaultCapability: ReviewCapability = {
  ai_analysis_enabled: false,
};

const defaultState = {
  sessionId: null,
  strategy: null,
  progress: defaultProgress,
  capability: defaultCapability,
  currentItem: null,
  showingAnswer: false,
  revealedData: null,
  loading: false,
  submitting: false,
  completed: false,
  summary: null,
  error: null,
  userAttemptMarkdown: "",
};

export const createReviewStore = (
  deps: ReviewStoreDeps = {
    startSession: startReviewSessionService,
    getNextItem: getNextReviewItemService,
    revealItem: revealReviewItemService,
    submitResult: submitReviewResultService,
    getSummary: getReviewSummaryService,
    getCapability: getReviewCapabilityService,
  },
) =>
  createStore<ReviewStoreState>((set, get) => ({
    ...defaultState,
    setUserAttemptMarkdown: (value) => set({ userAttemptMarkdown: value }),
    clearUserAttempt: () => set({ userAttemptMarkdown: "" }),

    // 状态机：idle -> loading_session -> showing_stem -> showing_answer -> submitting
    // -> next_question / completed / error
    startSession: async (payload) => {
      const nextStrategy = payload?.strategy ?? get().strategy ?? "random";
      set({
        ...defaultState,
        loading: true,
      });

      try {
        let capability = defaultCapability;
        try {
          capability = (await deps.getCapability()) ?? defaultCapability;
        } catch {
          capability = defaultCapability;
        }

        const response = await deps.startSession({
          strategy: nextStrategy,
          limit: payload?.limit ?? 10,
        });

        set({
          sessionId: response.id,
          strategy: response.strategy,
          progress: {
            completed: response.completed_count,
            total: response.total_count,
          },
          capability,
          currentItem: response.next_item,
          showingAnswer: false,
          revealedData: null,
          loading: false,
          submitting: false,
          completed: false,
          summary: null,
          error: null,
        });
      } catch (error) {
        set({
          ...defaultState,
          loading: false,
          error: extractApiErrorMessage(error),
        });
      }
    },

    loadNext: async () => {
      const sessionId = get().sessionId;
      if (!sessionId) {
        return;
      }

      set({ loading: true, error: null, userAttemptMarkdown: "" });

      try {
        const response = await deps.getNextItem(sessionId);

        if (!response.next_item && response.progress.total > 0) {
          const summary = await deps.getSummary(sessionId);
          set({
            progress: response.progress,
            currentItem: null,
            showingAnswer: false,
            revealedData: null,
            loading: false,
            submitting: false,
            completed: true,
            summary,
            error: null,
            userAttemptMarkdown: "",
          });
          return;
        }

        set({
          progress: response.progress,
          currentItem: response.next_item,
          showingAnswer: false,
          revealedData: null,
          loading: false,
          completed: false,
          summary: null,
          error: null,
          userAttemptMarkdown: "",
        });
      } catch (error) {
        set({
          loading: false,
          error: extractApiErrorMessage(error),
        });
      }
    },

    showAnswer: async () => {
      const currentItem = get().currentItem;
      if (!currentItem) {
        return;
      }

      if (get().showingAnswer && get().revealedData) {
        return;
      }

      set({ loading: true, error: null });

      try {
        const revealedData = await deps.revealItem(currentItem.mistake_id);
        set({
          showingAnswer: true,
          revealedData,
          loading: false,
          error: null,
        });
      } catch (error) {
        set({
          loading: false,
          error: extractApiErrorMessage(error),
        });
      }
    },

    submitRate: async (userResult, options) => {
      const sessionId = get().sessionId;
      const currentItem = get().currentItem;
      if (!sessionId || !currentItem) {
        return;
      }

      set({ submitting: true, error: null });

      try {
        const response = await deps.submitResult(sessionId, {
          mistake_id: currentItem.mistake_id,
          user_result: userResult,
          shown_at: options?.shown_at ?? currentItem.shown_at,
          time_spent_ms: options?.time_spent_ms,
          note: options?.note,
        });

        if (response.progress.completed >= response.progress.total) {
          const summary = await deps.getSummary(sessionId);
          set({
            progress: response.progress,
            currentItem: null,
            showingAnswer: false,
            revealedData: null,
            loading: false,
            submitting: false,
            completed: true,
            summary,
            error: null,
            userAttemptMarkdown: "",
          });
          return;
        }

        set({
          progress: response.progress,
          showingAnswer: false,
          revealedData: null,
        });

        await get().loadNext();
        set({ submitting: false });
      } catch (error) {
        set({
          submitting: false,
          error: extractApiErrorMessage(error),
        });
      }
    },

    exitSession: () => {
      set({ ...defaultState });
    },

    reset: () => {
      set({ ...defaultState });
    },
  }));

export const reviewStore = createReviewStore();

export const useReviewStore = <T,>(selector: (state: ReviewStoreState) => T): T =>
  useStore(reviewStore, selector);

export const preloadReviewCapability = async (): Promise<ReviewCapability> => getReviewCapabilityService();

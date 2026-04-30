import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";

import { createEmptyDraft } from "../pages/MistakeEditor/form";
import type { MistakeDraft } from "../pages/MistakeEditor/form";

interface DraftStoreState {
  drafts: Record<string, MistakeDraft>;
  ensureDraft: (key: string) => MistakeDraft;
  replaceDraft: (key: string, draft: MistakeDraft) => void;
  patchDraft: (key: string, draft: Partial<MistakeDraft>) => void;
  clearDraft: (key: string) => void;
  clearAll: () => void;
}

const createDraftStore = () =>
  createStore<DraftStoreState>((set, get) => ({
    drafts: {},
    ensureDraft: (key) => {
      const existing = get().drafts[key];
      if (existing) {
        return existing;
      }

      const draft = createEmptyDraft();
      set((state) => ({
        drafts: {
          ...state.drafts,
          [key]: draft,
        },
      }));
      return draft;
    },
    replaceDraft: (key, draft) =>
      set((state) => ({
        drafts: {
          ...state.drafts,
          [key]: draft,
        },
      })),
    patchDraft: (key, draft) =>
      set((state) => ({
        drafts: {
          ...state.drafts,
          [key]: {
            ...(state.drafts[key] ?? createEmptyDraft()),
            ...draft,
          },
        },
      })),
    clearDraft: (key) =>
      set((state) => {
        const nextDrafts = { ...state.drafts };
        delete nextDrafts[key];
        return { drafts: nextDrafts };
      }),
    clearAll: () => set({ drafts: {} }),
  }));

export const draftStore = createDraftStore();

export const useDraftStore = <T,>(selector: (state: DraftStoreState) => T): T =>
  useStore(draftStore, selector);

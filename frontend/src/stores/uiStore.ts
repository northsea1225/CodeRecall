import i18next from "i18next";
import { createStore } from "zustand/vanilla";
import { useStore } from "zustand";

export type UITheme = "light" | "dark";
export type UILanguage = "zh-CN" | "en-US";
export type ToastType = "success" | "error" | "info" | "warning";
const THEME_STORAGE_KEY = "cr-theme";
const LANGUAGE_STORAGE_KEY = "cr-language";

export interface ToastPayload {
  id: number;
  type: ToastType;
  content: string;
}

interface UIStoreState {
  globalLoading: boolean;
  theme: UITheme;
  language: UILanguage;
  toast: ToastPayload | null;
  setGlobalLoading: (loading: boolean) => void;
  showToast: (type: ToastType, content: string) => void;
  clearToast: () => void;
  setTheme: (theme: UITheme) => void;
  toggleTheme: () => void;
  initializeTheme: () => void;
  toggleLanguage: () => void;
  initializeLanguage: () => void;
}

const isTheme = (value: string | null): value is UITheme => value === "light" || value === "dark";
const isLanguage = (v: string | null): v is UILanguage => v === "zh-CN" || v === "en-US";

const syncTheme = (theme: UITheme): void => {
  if (typeof globalThis.localStorage !== "undefined") {
    globalThis.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }

  if (typeof globalThis.document !== "undefined") {
    globalThis.document.documentElement.setAttribute("data-theme", theme);
  }
};

const syncLanguage = (language: UILanguage): void => {
  if (typeof globalThis.localStorage !== "undefined") {
    globalThis.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }

  void i18next.changeLanguage(language);
};

export const createUIStore = () =>
  createStore<UIStoreState>((set, get) => ({
    globalLoading: false,
    theme: "light",
    language: "zh-CN",
    toast: null,
    setGlobalLoading: (loading) => set({ globalLoading: loading }),
    showToast: (type, content) =>
      set({
        toast: {
          id: Date.now(),
          type,
          content,
        },
      }),
    clearToast: () => set({ toast: null }),
    setTheme: (theme) => {
      syncTheme(theme);
      set({ theme });
    },
    toggleTheme: () => {
      const nextTheme = get().theme === "dark" ? "light" : "dark";
      syncTheme(nextTheme);
      set({ theme: nextTheme });
    },
    initializeTheme: () => {
      const storedTheme =
        typeof globalThis.localStorage === "undefined"
          ? null
          : globalThis.localStorage.getItem(THEME_STORAGE_KEY);
      const theme = isTheme(storedTheme) ? storedTheme : "light";
      syncTheme(theme);
      set({ theme });
    },
    toggleLanguage: () => {
      const nextLanguage = get().language === "zh-CN" ? "en-US" : "zh-CN";
      syncLanguage(nextLanguage);
      set({ language: nextLanguage });
    },
    initializeLanguage: () => {
      const storedLanguage =
        typeof globalThis.localStorage === "undefined"
          ? null
          : globalThis.localStorage.getItem(LANGUAGE_STORAGE_KEY);
      const language = isLanguage(storedLanguage) ? storedLanguage : "zh-CN";
      syncLanguage(language);
      set({ language });
    },
  }));

export const uiStore = createUIStore();

export const useUIStore = <T,>(selector: (state: UIStoreState) => T): T =>
  useStore(uiStore, selector);

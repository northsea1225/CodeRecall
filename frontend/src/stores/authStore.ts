import { create } from "zustand";

import { draftStore } from "./draftStore";
import { reviewStore } from "./reviewStore";

interface AuthState {
  token: string | null;
  username: string | null;
  userId: number | null;
  login: (token: string, username: string, userId: number) => void;
  logout: () => void;
  initializeAuth: () => void;
}

const TOKEN_KEY = "coderecall_token";

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  username: null,
  userId: null,
  login: (token, username, userId) => {
    localStorage.setItem(TOKEN_KEY, JSON.stringify({ token, username, userId }));
    set({ token, username, userId });
  },
  logout: () => {
    const userId = useAuthStore.getState().userId;
    localStorage.removeItem(TOKEN_KEY);
    if (userId !== null) {
      localStorage.removeItem(`coderecall_ever_imported_${userId}`);
    }
    set({ token: null, username: null, userId: null });
    reviewStore.getState().reset();
    draftStore.getState().clearAll();
  },
  initializeAuth: () => {
    const raw = localStorage.getItem(TOKEN_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw);
      if (parsed?.token && parsed?.userId) {
        const parts = parsed.token.split(".");
        if (parts.length === 3) {
          const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
          const padded = b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "=");
          const { exp } = JSON.parse(atob(padded));
          if (typeof exp === "number" && exp * 1000 > Date.now()) {
            set({
              token: typeof parsed.token === "string" ? parsed.token : null,
              username: typeof parsed.username === "string" ? parsed.username : null,
              userId: typeof parsed.userId === "number" ? parsed.userId : null,
            });
            return;
          }
        }
      }
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
    }
  },
}));

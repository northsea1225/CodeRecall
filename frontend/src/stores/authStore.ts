import { create } from "zustand";

import { draftStore } from "./draftStore";
import { reviewStore } from "./reviewStore";

interface AuthState {
  username: string | null;
  userId: number | null;
  tokenExpAt: number | null;
  initialized: boolean;
  setSession: (s: {
    username?: string | null;
    userId?: number | null;
    tokenExpAt?: number | null;
  }) => void;
  logout: () => void;
  initializeAuth: () => Promise<void>;
}

const SESSION_KEY = "coderecall_session";
const LEGACY_TOKEN_KEY = "coderecall_token";
const API_BASE =
  (typeof window !== "undefined" && (window as Window & { __E2E_API_BASE?: string }).__E2E_API_BASE) ||
  (import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

interface MeResponse {
  id: number;
  username: string;
  token_exp_at?: string | null;
}

async function fetchMe(authHeader?: string): Promise<MeResponse | null> {
  try {
    const headers: Record<string, string> = {};
    if (authHeader) headers["Authorization"] = authHeader;
    const res = await fetch(`${API_BASE}/auth/me`, {
      credentials: "include",
      headers,
    });
    if (!res.ok) return null;
    return (await res.json()) as MeResponse;
  } catch {
    return null;
  }
}

function persistSession(state: {
  username: string | null;
  userId: number | null;
  tokenExpAt: number | null;
}): void {
  if (state.username !== null || state.userId !== null) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(state));
  } else {
    localStorage.removeItem(SESSION_KEY);
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  username: null,
  userId: null,
  tokenExpAt: null,
  initialized: false,
  setSession: (s) => {
    set((prev) => {
      const next = {
        username: s.username !== undefined ? s.username : prev.username,
        userId: s.userId !== undefined ? s.userId : prev.userId,
        tokenExpAt: s.tokenExpAt !== undefined ? s.tokenExpAt : prev.tokenExpAt,
      };
      persistSession(next);
      return { ...next, initialized: prev.initialized };
    });
  },
  logout: () => {
    const userId = useAuthStore.getState().userId;
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    if (userId !== null) {
      localStorage.removeItem(`coderecall_ever_imported_${userId}`);
    }
    set((prev) => ({
      username: null,
      userId: null,
      tokenExpAt: null,
      initialized: prev.initialized,
    }));
    reviewStore.getState().reset();
    draftStore.getState().clearAll();
  },
  initializeAuth: async () => {
    // 1. Try cookie-based session
    const me = await fetchMe();
    if (me !== null) {
      const expMs = me.token_exp_at ? new Date(me.token_exp_at).getTime() : null;
      persistSession({ username: me.username, userId: me.id, tokenExpAt: expMs });
      set({ username: me.username, userId: me.id, tokenExpAt: expMs, initialized: true });
      localStorage.removeItem(LEGACY_TOKEN_KEY);
      return;
    }

    // 2. Legacy migration: localStorage Bearer (24h compat window)
    const legacyRaw = localStorage.getItem(LEGACY_TOKEN_KEY);
    if (legacyRaw) {
      try {
        const parsed = JSON.parse(legacyRaw) as { token?: unknown };
        if (typeof parsed.token === "string") {
          const meLegacy = await fetchMe(`Bearer ${parsed.token}`);
          if (meLegacy !== null) {
            const expMs = meLegacy.token_exp_at ? new Date(meLegacy.token_exp_at).getTime() : null;
            persistSession({
              username: meLegacy.username,
              userId: meLegacy.id,
              tokenExpAt: expMs,
            });
            set({
              username: meLegacy.username,
              userId: meLegacy.id,
              tokenExpAt: expMs,
              initialized: true,
            });
            localStorage.removeItem(LEGACY_TOKEN_KEY);
            return;
          }
        }
      } catch {
        /* swallow legacy parse error */
      }
    }

    // 3. No session
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    set({ username: null, userId: null, tokenExpAt: null, initialized: true });
  },
}));

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === SESSION_KEY && e.newValue === null) {
      const state = useAuthStore.getState();
      if (state.username !== null) {
        state.logout();
      }
    }
  });
}

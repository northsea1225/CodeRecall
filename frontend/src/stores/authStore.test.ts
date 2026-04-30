import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "./authStore";

const TOKEN_KEY = "coderecall_token";

function base64UrlEncode(input: string): string {
  return btoa(input).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function makeJwt(payload: Record<string, unknown>): string {
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = base64UrlEncode(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

describe("authStore", () => {
  const storage = new Map<string, string>();

  beforeEach(() => {
    storage.clear();
    vi.stubGlobal("localStorage", {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    });
    useAuthStore.setState({ token: null, username: null, userId: null });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("initializeAuth", () => {
    it("rejects extra fields and only keeps token/username/userId", () => {
      const futureExp = Math.floor(Date.now() / 1000) + 3600;
      const token = makeJwt({ exp: futureExp });
      storage.set(
        TOKEN_KEY,
        JSON.stringify({
          token,
          username: "alice",
          userId: 7,
          role: "admin",
          _bypass: true,
        }),
      );

      useAuthStore.getState().initializeAuth();

      const state = useAuthStore.getState() as Record<string, unknown>;
      expect(state.token).toBe(token);
      expect(state.username).toBe("alice");
      expect(state.userId).toBe(7);
      expect(state.role).toBeUndefined();
      expect(state._bypass).toBeUndefined();
    });

    it("clears expired tokens and leaves the store at null", () => {
      const pastExp = Math.floor(Date.now() / 1000) - 60;
      const token = makeJwt({ exp: pastExp });
      storage.set(TOKEN_KEY, JSON.stringify({ token, username: "alice", userId: 1 }));

      useAuthStore.getState().initializeAuth();

      expect(useAuthStore.getState().token).toBeNull();
      expect(useAuthStore.getState().userId).toBeNull();
      expect(storage.has(TOKEN_KEY)).toBe(false);
    });

    it("ignores payload when parsed.token is not a string", () => {
      const futureExp = Math.floor(Date.now() / 1000) + 3600;
      storage.set(
        TOKEN_KEY,
        JSON.stringify({ token: { exp: futureExp }, username: "alice", userId: 1 }),
      );

      useAuthStore.getState().initializeAuth();

      expect(useAuthStore.getState().token).toBeNull();
      expect(useAuthStore.getState().username).toBeNull();
      expect(useAuthStore.getState().userId).toBeNull();
    });
  });

  describe("logout", () => {
    it("clears coderecall_ever_imported_${userId} along with the token", () => {
      useAuthStore.setState({ token: "tok", username: "alice", userId: 9 });
      storage.set(TOKEN_KEY, "{}");
      storage.set("coderecall_ever_imported_9", "1");
      storage.set("coderecall_ever_imported_99", "1");

      useAuthStore.getState().logout();

      expect(storage.has(TOKEN_KEY)).toBe(false);
      expect(storage.has("coderecall_ever_imported_9")).toBe(false);
      expect(storage.has("coderecall_ever_imported_99")).toBe(true);
      expect(useAuthStore.getState().token).toBeNull();
      expect(useAuthStore.getState().userId).toBeNull();
    });
  });
});

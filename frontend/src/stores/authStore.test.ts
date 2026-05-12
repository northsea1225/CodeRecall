import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "./authStore";

const SESSION_KEY = "coderecall_session";
const LEGACY_TOKEN_KEY = "coderecall_token";

describe("authStore", () => {
  const storage = new Map<string, string>();
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    storage.clear();
    vi.stubGlobal("localStorage", {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    });
    useAuthStore.setState({
      username: null,
      userId: null,
      tokenExpAt: null,
      initialized: false,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    globalThis.fetch = originalFetch;
  });

  describe("setSession", () => {
    it("persists username/userId/tokenExpAt to localStorage and store", () => {
      const expMs = Date.now() + 7200_000;
      useAuthStore.getState().setSession({ username: "alice", userId: 7, tokenExpAt: expMs });

      const state = useAuthStore.getState();
      expect(state.username).toBe("alice");
      expect(state.userId).toBe(7);
      expect(state.tokenExpAt).toBe(expMs);
      expect(JSON.parse(storage.get(SESSION_KEY) ?? "{}")).toEqual({
        username: "alice",
        userId: 7,
        tokenExpAt: expMs,
      });
    });

    it("partial update preserves other fields", () => {
      useAuthStore.getState().setSession({ username: "alice", userId: 7, tokenExpAt: 100 });
      useAuthStore.getState().setSession({ tokenExpAt: 200 });

      const state = useAuthStore.getState();
      expect(state.username).toBe("alice");
      expect(state.userId).toBe(7);
      expect(state.tokenExpAt).toBe(200);
    });
  });

  describe("logout", () => {
    it("clears session + legacy token + coderecall_ever_imported_${userId}", () => {
      useAuthStore.setState({
        username: "alice",
        userId: 9,
        tokenExpAt: 100,
        initialized: true,
      });
      storage.set(SESSION_KEY, "{}");
      storage.set(LEGACY_TOKEN_KEY, "{}");
      storage.set("coderecall_ever_imported_9", "1");
      storage.set("coderecall_ever_imported_99", "1");

      useAuthStore.getState().logout();

      expect(storage.has(SESSION_KEY)).toBe(false);
      expect(storage.has(LEGACY_TOKEN_KEY)).toBe(false);
      expect(storage.has("coderecall_ever_imported_9")).toBe(false);
      expect(storage.has("coderecall_ever_imported_99")).toBe(true);
      expect(useAuthStore.getState().username).toBeNull();
      expect(useAuthStore.getState().userId).toBeNull();
      expect(useAuthStore.getState().tokenExpAt).toBeNull();
    });
  });

  describe("initializeAuth", () => {
    it("populates session from successful /auth/me cookie call", async () => {
      const expIso = new Date(Date.now() + 7200_000).toISOString();
      globalThis.fetch = vi.fn(
        async () =>
          new Response(
            JSON.stringify({ id: 7, username: "alice", token_exp_at: expIso }),
            { status: 200 },
          ),
      ) as unknown as typeof fetch;

      await useAuthStore.getState().initializeAuth();

      const state = useAuthStore.getState();
      expect(state.username).toBe("alice");
      expect(state.userId).toBe(7);
      expect(state.initialized).toBe(true);
      expect(state.tokenExpAt).toBe(new Date(expIso).getTime());
    });

    it("clears session when /auth/me returns 401 and no legacy token", async () => {
      globalThis.fetch = vi.fn(
        async () => new Response("Unauthorized", { status: 401 }),
      ) as unknown as typeof fetch;

      await useAuthStore.getState().initializeAuth();

      const state = useAuthStore.getState();
      expect(state.username).toBeNull();
      expect(state.userId).toBeNull();
      expect(state.initialized).toBe(true);
    });

    it("migrates legacy localStorage Bearer token via fallback fetch", async () => {
      storage.set(
        LEGACY_TOKEN_KEY,
        JSON.stringify({ token: "legacy-bearer", username: "alice", userId: 5 }),
      );
      const expIso = new Date(Date.now() + 7200_000).toISOString();
      const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const headers = init?.headers as Record<string, string> | undefined;
        if (headers?.Authorization === "Bearer legacy-bearer") {
          return new Response(
            JSON.stringify({ id: 5, username: "alice", token_exp_at: expIso }),
            { status: 200 },
          );
        }
        return new Response("Unauthorized", { status: 401 });
      });
      globalThis.fetch = fetchMock as unknown as typeof fetch;

      await useAuthStore.getState().initializeAuth();

      const state = useAuthStore.getState();
      expect(state.username).toBe("alice");
      expect(state.userId).toBe(5);
      expect(state.initialized).toBe(true);
      expect(storage.has(LEGACY_TOKEN_KEY)).toBe(false);
    });
  });
});

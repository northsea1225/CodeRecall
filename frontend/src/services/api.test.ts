import { AxiosError, AxiosHeaders } from "axios";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "../stores/authStore";
import { routerBridge } from "../utils/routerBridge";
import { api, ApiClientError, extractApiErrorMessage, refreshApi } from "./api";

function makeResponse<T>(
  config: InternalAxiosRequestConfig,
  data: T,
  status = 200,
): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: {},
    config,
  };
}

function makeAxiosError(
  config: InternalAxiosRequestConfig,
  status: number,
  code: string,
): AxiosError {
  return new AxiosError(
    "Request failed",
    undefined,
    config,
    undefined,
    makeResponse(config, { code, message: code, detail: {} }, status),
  );
}

describe("extractApiErrorMessage", () => {
  it("prefers backend message from standard error payload", () => {
    const error = new AxiosError("Request failed", undefined, undefined, undefined, {
      data: {
        code: "mistake_not_found",
        message: "Mistake not found.",
        detail: { mistake_id: 42 },
      },
      status: 404,
      statusText: "Not Found",
      headers: {},
      config: {} as never,
    });

    expect(extractApiErrorMessage(error)).toBe("Mistake not found.");
  });

  it("falls back to axios message when payload is unknown", () => {
    const error = new AxiosError("Network Error");

    expect(extractApiErrorMessage(error)).toBe("Network Error");
  });
});

describe("api token refresh lifecycle (cookie mode)", () => {
  const originalApiAdapter = api.defaults.adapter;
  const originalRefreshAdapter = refreshApi.defaults.adapter;
  const storage = new Map<string, string>();
  let setSessionSpy: ReturnType<typeof vi.spyOn>;
  let logoutSpy: ReturnType<typeof vi.spyOn>;
  let navigateSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-04T00:00:00.000Z"));
    vi.spyOn(Math, "random").mockReturnValue(0);
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
      initialized: true,
    });
    setSessionSpy = vi.spyOn(useAuthStore.getState(), "setSession");
    logoutSpy = vi.spyOn(useAuthStore.getState(), "logout").mockImplementation(() => {});
    navigateSpy = vi.spyOn(routerBridge, "navigate").mockImplementation(() => {});
  });

  afterEach(() => {
    api.defaults.adapter = originalApiAdapter;
    refreshApi.defaults.adapter = originalRefreshAdapter;
    useAuthStore.setState({
      username: null,
      userId: null,
      tokenExpAt: null,
      initialized: false,
    });
    routerBridge.reset();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("refreshes silently before sending request when tokenExpAt is within five minutes", async () => {
    const newExpIso = new Date(Date.now() + 7200_000).toISOString();
    useAuthStore.setState({
      username: "alice",
      userId: 1,
      tokenExpAt: Date.now() + 60_000, // 1 min remaining, below 5min threshold
      initialized: true,
    });

    const refreshAdapter = vi.fn<AxiosAdapter>(async (config) =>
      makeResponse(config, {
        access_token: "ignored",
        token_type: "bearer",
        username: "alice",
        user_id: 1,
        token_exp_at: newExpIso,
      }),
    );
    const apiAdapter = vi.fn<AxiosAdapter>(async (config) => makeResponse(config, { ok: true }));
    refreshApi.defaults.adapter = refreshAdapter;
    api.defaults.adapter = apiAdapter;

    await api.get("/some-route");

    expect(refreshAdapter).toHaveBeenCalledOnce();
    expect(setSessionSpy).toHaveBeenCalledWith({
      tokenExpAt: new Date(newExpIso).getTime(),
    });
  });

  it("shares one refresh request across concurrent authenticated requests", async () => {
    const newExpIso = new Date(Date.now() + 7200_000).toISOString();
    useAuthStore.setState({
      username: "alice",
      userId: 1,
      tokenExpAt: Date.now() + 60_000,
      initialized: true,
    });

    let resolveRefresh!: (response: AxiosResponse) => void;
    const refreshResponse = new Promise<AxiosResponse>((resolve) => {
      resolveRefresh = resolve;
    });
    const refreshAdapter = vi.fn<AxiosAdapter>(() => refreshResponse);
    const apiAdapter = vi.fn<AxiosAdapter>(async (config) => makeResponse(config, { ok: true }));
    refreshApi.defaults.adapter = refreshAdapter;
    api.defaults.adapter = apiAdapter;

    const requests = Promise.all([
      api.get("/some-route"),
      api.get("/some-route"),
      api.get("/some-route"),
    ]);
    await Promise.resolve();
    await Promise.resolve();
    expect(refreshAdapter).toHaveBeenCalledOnce();

    resolveRefresh(
      makeResponse({ headers: new AxiosHeaders() } as InternalAxiosRequestConfig, {
        access_token: "ignored",
        token_type: "bearer",
        username: "alice",
        user_id: 1,
        token_exp_at: newExpIso,
      }),
    );
    await requests;

    expect(apiAdapter).toHaveBeenCalledTimes(3);
  });

  it("logs out and navigates when refresh fails", async () => {
    useAuthStore.setState({
      username: "alice",
      userId: 1,
      tokenExpAt: Date.now() + 7200_000,
      initialized: true,
    });
    const refreshAdapter = vi.fn<AxiosAdapter>((config) =>
      Promise.reject(makeAxiosError(config, 401, "token_expired")),
    );
    const apiAdapter = vi.fn<AxiosAdapter>((config) =>
      Promise.reject(makeAxiosError(config, 401, "token_expired")),
    );
    refreshApi.defaults.adapter = refreshAdapter;
    api.defaults.adapter = apiAdapter;

    await expect(api.get("/some-route")).rejects.toBeInstanceOf(ApiClientError);

    expect(refreshAdapter).toHaveBeenCalledOnce();
    expect(logoutSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith("/login", { replace: true });
  });

  it("retries original request once after 401 refresh succeeds", async () => {
    const newExpIso = new Date(Date.now() + 7200_000).toISOString();
    useAuthStore.setState({
      username: "alice",
      userId: 1,
      tokenExpAt: Date.now() + 7200_000,
      initialized: true,
    });
    const refreshAdapter = vi.fn<AxiosAdapter>(async (config) =>
      makeResponse(config, {
        access_token: "ignored",
        token_type: "bearer",
        username: "alice",
        user_id: 1,
        token_exp_at: newExpIso,
      }),
    );
    const originalRequests: InternalAxiosRequestConfig[] = [];
    const apiAdapter = vi.fn<AxiosAdapter>(async (config) => {
      originalRequests.push(config);
      if (originalRequests.length === 1) {
        throw makeAxiosError(config, 401, "token_expired");
      }
      return makeResponse(config, { ok: true });
    });
    refreshApi.defaults.adapter = refreshAdapter;
    api.defaults.adapter = apiAdapter;

    const response = await api.get("/some-route");

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ ok: true });
    expect(apiAdapter).toHaveBeenCalledTimes(2);
    expect(refreshAdapter).toHaveBeenCalledOnce();
  });
});

describe("routerBridge fallback", () => {
  it("invokes the registered navigate when present", () => {
    const fn = vi.fn();
    routerBridge.register(fn);
    routerBridge.navigate("/x", { replace: true });
    expect(fn).toHaveBeenCalledWith("/x", { replace: true });
  });

  it("does not throw when navigate is not registered", () => {
    routerBridge.reset();
    expect(() => routerBridge.navigate("/y")).not.toThrow();
  });
});

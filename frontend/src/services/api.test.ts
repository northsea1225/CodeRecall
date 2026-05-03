import { AxiosError, AxiosHeaders } from "axios";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "../stores/authStore";
import { routerBridge } from "../utils/routerBridge";
import { api, ApiClientError, extractApiErrorMessage, refreshApi } from "./api";

function base64UrlEncode(input: string): string {
  return btoa(input).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function makeJwt(payload: Record<string, unknown>): string {
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = base64UrlEncode(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

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

describe("api 401 interceptor", () => {
  let logoutSpy: ReturnType<typeof vi.spyOn>;
  let navigateSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    logoutSpy = vi.spyOn(useAuthStore.getState(), "logout").mockImplementation(() => {});
    navigateSpy = vi.spyOn(routerBridge, "navigate").mockImplementation(() => {});
  });

  afterEach(() => {
    logoutSpy.mockRestore();
    navigateSpy.mockRestore();
  });

  it("logs out and synchronously navigates to /login on 401", async () => {
    const error = new AxiosError(
      "Unauthorized",
      undefined,
      { headers: new AxiosHeaders() } as never,
      undefined,
      {
        data: { code: "auth_required", message: "Token expired.", detail: {} },
        status: 401,
        statusText: "Unauthorized",
        headers: {},
        config: { headers: new AxiosHeaders() } as never,
      },
    );

    const handlers = (api.interceptors.response as unknown as {
      handlers: Array<{ rejected?: (e: unknown) => unknown } | null>;
    }).handlers.filter(Boolean);
    expect(handlers.length).toBeGreaterThan(0);
    const rejectedHandler = handlers[0]!.rejected!;

    await expect(rejectedHandler(error)).rejects.toBeInstanceOf(ApiClientError);

    expect(logoutSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith("/login", { replace: true });
  });

  it("does not navigate or logout on non-401 errors", async () => {
    const error = new AxiosError(
      "Server Error",
      undefined,
      { headers: new AxiosHeaders() } as never,
      undefined,
      {
        data: { code: "internal_error", message: "boom", detail: {} },
        status: 500,
        statusText: "Server Error",
        headers: {},
        config: { headers: new AxiosHeaders() } as never,
      },
    );

    const handlers = (api.interceptors.response as unknown as {
      handlers: Array<{ rejected?: (e: unknown) => unknown } | null>;
    }).handlers.filter(Boolean);
    const rejectedHandler = handlers[0]!.rejected!;

    await expect(rejectedHandler(error)).rejects.toBeInstanceOf(ApiClientError);

    expect(logoutSpy).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
  });
});

describe("api token refresh lifecycle", () => {
  const storage = new Map<string, string>();
  const originalApiAdapter = api.defaults.adapter;
  const originalRefreshAdapter = refreshApi.defaults.adapter;
  let setTokenSpy: ReturnType<typeof vi.spyOn>;
  let logoutSpy: ReturnType<typeof vi.spyOn>;
  let navigateSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    storage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-02T00:00:00.000Z"));
    vi.spyOn(Math, "random").mockReturnValue(0);
    vi.stubGlobal("localStorage", {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    });
    useAuthStore.setState({ token: null, username: null, userId: null });
    setTokenSpy = vi.spyOn(useAuthStore.getState(), "setToken");
    logoutSpy = vi.spyOn(useAuthStore.getState(), "logout").mockImplementation(() => {});
    navigateSpy = vi.spyOn(routerBridge, "navigate").mockImplementation(() => {});
  });

  afterEach(() => {
    api.defaults.adapter = originalApiAdapter;
    refreshApi.defaults.adapter = originalRefreshAdapter;
    useAuthStore.setState({ token: null, username: null, userId: null });
    routerBridge.reset();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("refreshes silently before sending request when token expires within five minutes", async () => {
    const oldToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 60 });
    const newToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 7200 });
    useAuthStore.setState({ token: oldToken, username: "alice", userId: 1 });

    const refreshAdapter = vi.fn<AxiosAdapter>(async (config) =>
      makeResponse(config, {
        access_token: newToken,
        token_type: "bearer",
        username: "alice",
        user_id: 1,
      }),
    );
    const originalRequests: InternalAxiosRequestConfig[] = [];
    const apiAdapter = vi.fn<AxiosAdapter>(async (config) => {
      originalRequests.push(config);
      return makeResponse(config, { ok: true });
    });
    refreshApi.defaults.adapter = refreshAdapter;
    api.defaults.adapter = apiAdapter;

    await api.get("/some-route");

    expect(refreshAdapter).toHaveBeenCalledOnce();
    expect(AxiosHeaders.from(originalRequests[0].headers).get("Authorization")).toBe(
      `Bearer ${newToken}`,
    );
    expect(setTokenSpy).toHaveBeenCalledWith(newToken);
  });

  it("shares one refresh request across concurrent authenticated requests", async () => {
    const oldToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 60 });
    const newToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 7200 });
    useAuthStore.setState({ token: oldToken, username: "alice", userId: 1 });

    let resolveRefresh!: (response: AxiosResponse) => void;
    const refreshResponse = new Promise<AxiosResponse>((resolve) => {
      resolveRefresh = resolve;
    });
    const refreshAdapter = vi.fn<AxiosAdapter>(() => refreshResponse);
    const originalRequests: InternalAxiosRequestConfig[] = [];
    const apiAdapter = vi.fn<AxiosAdapter>(async (config) => {
      originalRequests.push(config);
      return makeResponse(config, { ok: true });
    });
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
        access_token: newToken,
        token_type: "bearer",
        username: "alice",
        user_id: 1,
      }),
    );
    await requests;

    expect(apiAdapter).toHaveBeenCalledTimes(3);
    expect(
      originalRequests.every(
        (config) =>
          AxiosHeaders.from(config.headers).get("Authorization") === `Bearer ${newToken}`,
      ),
    ).toBe(true);
  });

  it("logs out and navigates when refresh fails", async () => {
    const oldToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 7200 });
    useAuthStore.setState({ token: oldToken, username: "alice", userId: 1 });
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
    const oldToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 7200 });
    const newToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 7300 });
    useAuthStore.setState({ token: oldToken, username: "alice", userId: 1 });
    const refreshAdapter = vi.fn<AxiosAdapter>(async (config) =>
      makeResponse(config, {
        access_token: newToken,
        token_type: "bearer",
        username: "alice",
        user_id: 1,
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
    expect(AxiosHeaders.from(originalRequests[1].headers).get("Authorization")).toBe(
      `Bearer ${newToken}`,
    );
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

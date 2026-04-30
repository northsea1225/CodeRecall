import { AxiosError, AxiosHeaders } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "../stores/authStore";
import { routerBridge } from "../utils/routerBridge";
import { api, ApiClientError, extractApiErrorMessage } from "./api";

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

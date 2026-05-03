import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "../stores/authStore";
import { routerBridge } from "../utils/routerBridge";
import type { AuthResponse } from "./authService";

export interface ApiErrorPayload {
  code?: string;
  message?: string;
  detail?: unknown;
}

export class ApiClientError extends Error {
  code?: string;
  detail?: unknown;
  status?: number;

  constructor(message: string, options?: ApiErrorPayload & { status?: number }) {
    super(message);
    this.name = "ApiClientError";
    this.code = options?.code;
    this.detail = options?.detail;
    this.status = options?.status;
  }
}

export const extractApiErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as ApiErrorPayload | undefined;
    return payload?.message ?? error.message ?? "Request failed.";
  }

  if (error instanceof ApiClientError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Request failed.";
};

export const apiBaseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: apiBaseURL,
});

export const refreshApi = axios.create({
  baseURL: apiBaseURL,
});

interface RefreshableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  skipAuthRefresh?: boolean;
}

const REFRESH_THRESHOLD_MS = 5 * 60 * 1000;
const JITTER_MS = 60 * 1000;

let refreshPromise: Promise<string> | null = null;

function decodeJwtExpMs(token: string): number | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;

  try {
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "=");
    const { exp } = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof exp === "number" ? exp * 1000 : null;
  } catch {
    return null;
  }
}

function logoutAndRedirect(): void {
  useAuthStore.getState().logout();
  routerBridge.navigate("/login", { replace: true });
}

async function refreshTokenOnce(currentToken: string): Promise<string> {
  if (refreshPromise !== null) return refreshPromise;

  refreshPromise = refreshApi
    .post<AuthResponse>("/auth/refresh", null, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })
    .then((response) => {
      const nextToken = response.data.access_token;
      useAuthStore.getState().setToken(nextToken);
      return nextToken;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

async function ensureFreshToken(token: string): Promise<string> {
  const expMs = decodeJwtExpMs(token);
  if (expMs === null) return token;

  const jitter = Math.floor(Math.random() * JITTER_MS);
  if (expMs - Date.now() > REFRESH_THRESHOLD_MS + jitter) return token;

  return refreshTokenOnce(token);
}

api.interceptors.request.use(async (config) => {
  const { token } = useAuthStore.getState();
  if (!token || (config as RefreshableConfig).skipAuthRefresh) return config;

  const freshToken = await ensureFreshToken(token);
  config.headers.set("Authorization", `Bearer ${freshToken}`);
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorPayload>) => {
    const original = error.config as RefreshableConfig | undefined;
    if (error.response?.status === 401 && original && !original._retry && !original.skipAuthRefresh) {
      const { token } = useAuthStore.getState();
      if (token) {
        try {
          original._retry = true;
          const freshToken = await refreshTokenOnce(token);
          original.headers.set("Authorization", `Bearer ${freshToken}`);
          return api.request(original);
        } catch {
          logoutAndRedirect();
        }
      } else {
        logoutAndRedirect();
      }
    }

    const payload = error.response?.data;
    return Promise.reject(
      new ApiClientError(payload?.message ?? error.message ?? "Request failed.", {
        code: payload?.code,
        detail: payload?.detail,
        status: error.response?.status,
      }),
    );
  },
);

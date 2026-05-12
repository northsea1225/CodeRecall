import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "../stores/authStore";
import { routerBridge } from "../utils/routerBridge";
import { CSRF_HEADER, getCsrfTokenFromCookie } from "../utils/csrf";
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

declare global {
  interface Window {
    __E2E_API_BASE?: string;
  }
}

// E2E test harness can override the API base URL by setting window.__E2E_API_BASE
// before app boots (via Playwright `page.addInitScript`). This is needed because
// vite import.meta.env is build-time-replaced for production but the e2e backend
// runs on a dynamic port. In normal dev/prod, the window override is undefined
// and we fall back to VITE_API_BASE_URL (build-time) → :8000 default.
export const apiBaseURL =
  (typeof window !== "undefined" && window.__E2E_API_BASE) ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

export const api = axios.create({ baseURL: apiBaseURL, withCredentials: true });
export const refreshApi = axios.create({ baseURL: apiBaseURL, withCredentials: true });

interface RefreshableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  skipAuthRefresh?: boolean;
}

const REFRESH_THRESHOLD_MS = 5 * 60 * 1000;
const JITTER_MS = 60 * 1000;
const MUTATION_METHODS = new Set(["post", "put", "patch", "delete"]);

let refreshPromise: Promise<void> | null = null;

function logoutAndRedirect(): void {
  useAuthStore.getState().logout();
  routerBridge.navigate("/login", { replace: true });
}

async function refreshTokenOnce(): Promise<void> {
  if (refreshPromise !== null) return refreshPromise;

  refreshPromise = refreshApi
    .post<AuthResponse>("/auth/refresh", null)
    .then((response) => {
      const expIso = response.data?.token_exp_at;
      const expMs = expIso ? new Date(expIso).getTime() : null;
      useAuthStore.getState().setSession({ tokenExpAt: expMs });
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

async function ensureFreshToken(): Promise<void> {
  const { tokenExpAt } = useAuthStore.getState();
  if (tokenExpAt === null) return;

  const jitter = Math.floor(Math.random() * JITTER_MS);
  if (tokenExpAt - Date.now() > REFRESH_THRESHOLD_MS + jitter) return;

  await refreshTokenOnce();
}

api.interceptors.request.use(async (config) => {
  const requestConfig = config as RefreshableConfig;
  if (requestConfig.skipAuthRefresh) return config;

  const { username } = useAuthStore.getState();
  if (username !== null) {
    await ensureFreshToken();
  }

  if (MUTATION_METHODS.has((config.method ?? "get").toLowerCase())) {
    const csrf = getCsrfTokenFromCookie();
    if (csrf) {
      config.headers.set(CSRF_HEADER, csrf);
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorPayload>) => {
    const original = error.config as RefreshableConfig | undefined;
    if (error.response?.status === 401 && original && !original._retry && !original.skipAuthRefresh) {
      try {
        original._retry = true;
        await refreshTokenOnce();
        if (MUTATION_METHODS.has((original.method ?? "get").toLowerCase())) {
          const csrf = getCsrfTokenFromCookie();
          if (csrf) {
            original.headers.set(CSRF_HEADER, csrf);
          }
        }
        return api.request(original);
      } catch {
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

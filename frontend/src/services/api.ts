import axios, { AxiosError } from "axios";

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
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorPayload>) => {
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

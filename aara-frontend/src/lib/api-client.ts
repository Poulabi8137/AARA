"use client";

import axios, { type AxiosRequestConfig } from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Endpoints whose own 401 response is a normal credential/token error, not
// a signal that an authenticated session's access token has expired. The
// refresh-and-retry dance below must never run for these, or a plain wrong
// password turns into a doomed refresh attempt followed by a hard redirect
// that wipes the error message before the user can read it.
const AUTH_ENDPOINTS_EXCLUDED_FROM_REFRESH = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
];

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false;
  return AUTH_ENDPOINTS_EXCLUDED_FROM_REFRESH.some((path) =>
    url.includes(path),
  );
}

apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAuthEndpoint(originalRequest.url)
    ) {
      const refreshToken = localStorage.getItem("refreshToken");
      if (!refreshToken) {
        // No session to refresh; surface the original 401 as-is.
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      try {
        const response = await fetch(
          `${apiClient.defaults.baseURL}/auth/refresh`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          },
        );

        if (!response.ok) {
          throw new Error("Token refresh failed");
        }

        const data = await response.json();

        localStorage.setItem("accessToken", data.access_token);
        localStorage.setItem("refreshToken", data.refresh_token);

        return apiClient(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        if (
          typeof window !== "undefined" &&
          window.location.pathname !== "/login"
        ) {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;

export type ApiResponse<T> = T;
export type ApiError = {
  message: string;
  status?: number;
  code?: string;
  details?: Record<string, unknown>;
};

export class ApiClientError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

/**
 * FastAPI returns `{"detail": "..."}` for HTTPException and
 * `{"detail": [{"msg": "...", "loc": [...]}]}` for pydantic validation
 * errors. Normalize both shapes into a single human-readable message.
 */
function extractErrorMessage(data: any, fallback: string): string {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d: any) => d?.msg ?? String(d)).join(" ");
  }
  return data?.message || fallback;
}

function toApiClientError(error: unknown): ApiClientError {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      // Request never reached the server: backend down, CORS block, DNS failure, etc.
      return new ApiClientError(
        "Unable to connect to server. Please check if the backend is running.",
        undefined,
        "NETWORK_ERROR",
      );
    }

    return new ApiClientError(
      extractErrorMessage(
        error.response.data,
        error.message || "Something went wrong.",
      ),
      error.response.status,
      error.response.data?.code,
      error.response.data?.details,
    );
  }

  if (error instanceof Error) {
    return new ApiClientError(error.message);
  }

  return new ApiClientError("Something went wrong.");
}

function isRetryable(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  // No response at all = network/connection failure -> worth retrying.
  if (!error.response) return true;
  // Only retry server-side failures, never 4xx client errors (bad
  // credentials, validation errors, etc. will never succeed on retry).
  return error.response.status >= 500;
}

export async function apiRequest<T>(
  config: AxiosRequestConfig,
  options?: {
    retry?: number;
    retryDelay?: (attempt: number) => number;
  },
): Promise<T> {
  const {
    retry = 2,
    retryDelay = (attempt: number) => Math.min(500 * 2 ** attempt, 4000),
  } = options || {};

  let lastError: unknown;

  for (let attempt = 0; attempt <= retry; attempt++) {
    try {
      return await apiClient(config);
    } catch (error) {
      lastError = error;

      if (attempt < retry && isRetryable(error)) {
        await new Promise((resolve) =>
          setTimeout(resolve, retryDelay(attempt)),
        );
        continue;
      }

      throw toApiClientError(error);
    }
  }

  throw toApiClientError(lastError);
}

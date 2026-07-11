import { apiRequest } from "@/lib/api-client";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface MessageResponse {
  message: string;
}

export const authService = {
  login: (data: LoginRequest) =>
    apiRequest<TokenResponse>({ method: "POST", url: "/auth/login", data }),

  register: (data: RegisterRequest) =>
    apiRequest<TokenResponse>({ method: "POST", url: "/auth/register", data }),

  logout: () =>
    apiRequest<void>({ method: "POST", url: "/auth/logout" }).catch(
      () => undefined,
    ),

  me: () => apiRequest<UserProfile>({ method: "GET", url: "/auth/me" }),

  refresh: (refresh_token: string) =>
    apiRequest<TokenResponse>({
      method: "POST",
      url: "/auth/refresh",
      data: { refresh_token },
    }),

  forgotPassword: (email: string) =>
    apiRequest<MessageResponse>({
      method: "POST",
      url: "/auth/forgot-password",
      data: { email },
    }),

  resetPassword: (token: string, new_password: string) =>
    apiRequest<MessageResponse>({
      method: "POST",
      url: "/auth/reset-password",
      data: { token, new_password },
    }),
};

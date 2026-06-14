import { create } from 'zustand';
import { AuthState, User } from './types';
import { apiClient, clearPersistedAuth, TOKEN_KEY, USER_KEY, REFRESH_KEY, COOKIE_NAME, setCookie } from './api-client';

interface JwtPayload {
  sub?: string;
  exp?: number;
  role?: string;
  type?: string;
  [key: string]: unknown;
}

function decodeJWTPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1])) as JwtPayload;
    if (typeof payload !== 'object' || payload === null) return null;
    return payload;
  } catch {
    return null;
  }
}

function isTokenExpired(payload: JwtPayload): boolean {
  if (!payload.exp) return false;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now;
}

function isValidAccessToken(payload: JwtPayload | null): boolean {
  if (!payload) return false;
  if (!payload.sub || typeof payload.sub !== 'string') return false;
  if (payload.type && payload.type !== 'access') return false;
  if (isTokenExpired(payload)) return false;
  return true;
}

function persistAuth(token: string, user: User, refreshToken?: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
  setCookie(COOKIE_NAME, token, 1800);
}

interface AuthStoreState extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
  hydrate: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthStoreState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.login(email, password);
      const { access_token, refresh_token } = response.data;
      const payload = decodeJWTPayload(access_token);
      if (!isValidAccessToken(payload)) {
        throw new Error('Invalid token received from server');
      }
      const user: User = {
        id: payload!.sub as string,
        email,
        name: email.split('@')[0],
        role: payload?.role as string | undefined,
        createdAt: new Date().toISOString(),
      };
      persistAuth(access_token, user, refresh_token);
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Login failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  signup: async (email: string, password: string, name: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.signup(email, password, name);
      const { access_token, refresh_token } = response.data;
      const payload = decodeJWTPayload(access_token);
      if (!isValidAccessToken(payload)) {
        throw new Error('Invalid token received from server');
      }
      const user: User = {
        id: payload!.sub as string,
        email,
        name,
        role: payload?.role as string | undefined,
        createdAt: new Date().toISOString(),
      };
      persistAuth(access_token, user, refresh_token);
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Signup failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    clearPersistedAuth();
    set({ user: null, isAuthenticated: false, isLoading: false, error: null });
  },

  setUser: (user) => set({ user, isAuthenticated: !!user }),

  hydrate: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      clearPersistedAuth();
      set({ user: null, isAuthenticated: false, isLoading: false, error: null });
      return;
    }

    const payload = decodeJWTPayload(token);
    if (!isValidAccessToken(payload)) {
      clearPersistedAuth();
      set({ user: null, isAuthenticated: false, isLoading: false, error: null });
      return;
    }

    try {
      const response = await apiClient.getMe();
      const { id, name, email, role, created_at } = response.data;
      const user: User = { id, name, email, role, createdAt: created_at };
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch {
      const raw = localStorage.getItem(USER_KEY);
      if (raw) {
        try {
          const cachedUser: User = JSON.parse(raw);
          set({ user: cachedUser, isAuthenticated: true, isLoading: false, error: null });
          return;
        } catch {
          // cached user is corrupted
        }
      }
      clearPersistedAuth();
      set({ user: null, isAuthenticated: false, isLoading: false, error: null });
    }
  },

  clearError: () => set({ error: null }),
}));

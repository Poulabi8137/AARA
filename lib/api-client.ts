import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TOKEN_KEY = 'authToken';
const REFRESH_KEY = 'refreshToken';
const USER_KEY = 'authUser';
const COOKIE_NAME = 'auth_token';

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null): void {
  failedQueue.forEach((p) => {
    if (error) {
      p.reject(error);
    } else {
      p.resolve(token!);
    }
  });
  failedQueue = [];
}

function clearPersistedAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(REFRESH_KEY);
  document.cookie = `${COOKIE_NAME}=; path=/; max-age=0`;
}

function setCookie(name: string, value: string, maxAgeSeconds: number): void {
  document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

interface CustomAxiosConfig extends InternalAxiosRequestConfig {
  _isRetry?: boolean;
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem(TOKEN_KEY);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as CustomAxiosConfig | undefined;
        if (!originalRequest) return Promise.reject(error);

        if (error.response?.status !== 401 || originalRequest._isRetry) {
          return Promise.reject(error);
        }

        if (isRefreshing) {
          return new Promise<string>((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return this.client(originalRequest);
          });
        }

        isRefreshing = true;
        originalRequest._isRetry = true;

        const refreshToken = localStorage.getItem(REFRESH_KEY);

        if (!refreshToken) {
          clearPersistedAuth();
          isRefreshing = false;
          return Promise.reject(error);
        }

        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = response.data;

          localStorage.setItem(TOKEN_KEY, access_token);
          if (refresh_token) {
            localStorage.setItem(REFRESH_KEY, refresh_token);
          }
          setCookie(COOKIE_NAME, access_token, 1800);

          processQueue(null, access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return this.client(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          clearPersistedAuth();
          if (typeof window !== 'undefined') {
            window.location.href = '/auth/login';
          }
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
    );
  }

  async getMe() {
    return this.client.get('/auth/me');
  }

  async login(email: string, password: string) {
    return this.client.post('/auth/login', { email, password });
  }

  async signup(email: string, password: string, name: string) {
    return this.client.post('/auth/register', { email, password, name });
  }

  async refresh(refreshToken: string) {
    return this.client.post('/auth/refresh', { refresh_token: refreshToken });
  }

  async updateProfile(data: { name?: string; email?: string }) {
    return this.client.put('/auth/me', data);
  }

  async listProjects() {
    return this.client.get('/projects');
  }

  async createProject(title: string, description?: string) {
    return this.client.post('/projects', { title, description });
  }

  async getProject(id: string) {
    return this.client.get(`/projects/${id}`);
  }

  async updateProject(id: string, data: any) {
    return this.client.put(`/projects/${id}`, data);
  }

  async deleteProject(id: string) {
    return this.client.delete(`/projects/${id}`);
  }

  async getProjectResearchOutputs(id: string) {
    return this.client.get(`/projects/${id}/research-outputs`);
  }

  async runWorkflow(projectId: string, query: string, objective?: string) {
    return this.client.post('/agents/run', { project_id: projectId, query, objective });
  }

  async getExecutionStatus(executionId: string) {
    return this.client.get(`/agents/executions/${executionId}/status`);
  }

  async listExecutions() {
    return this.client.get('/agents/executions');
  }

  async getExecution(executionId: string) {
    return this.client.get(`/agents/executions/${executionId}`);
  }

  async listSessions() {
    return this.client.get('/sessions');
  }

  async createSession(projectId: string, sessionName: string) {
    return this.client.post('/sessions', { project_id: projectId, session_name: sessionName });
  }

  async listReports() {
    return this.client.get('/reports');
  }

  async generateReport(data: { content: string; sections: string[]; format?: string }) {
    return this.client.post('/reports/generate', data);
  }
}

export { clearPersistedAuth, TOKEN_KEY, REFRESH_KEY, USER_KEY, COOKIE_NAME, setCookie };
export const apiClient = new APIClient();

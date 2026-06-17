import { create } from 'zustand'
import { apiClient } from '@/lib/api-client'
import type { User } from '@/lib/types'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
  getMe: () => Promise<void>
  clearError: () => void
  hydrate: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('authToken') : null,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.login(email, password)
      const data = res.data
      const name = data.user?.name || email.split('@')[0]
      set({
        user: { id: data.user?.id || '', name, email, createdAt: new Date().toISOString() },
        token: data.access_token,
        isLoading: false,
      })
      localStorage.setItem('authToken', data.access_token)
      if (data.refresh_token) localStorage.setItem('refreshToken', data.refresh_token)
    } catch (err: any) {
      set({ isLoading: false, error: err?.response?.data?.detail || 'Login failed' })
      throw err
    }
  },

  signup: async (name: string, email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.signup(email, password, name)
      const data = res.data
      set({
        user: data.user || { id: '', name, email, createdAt: new Date().toISOString() },
        token: data.access_token,
        isLoading: false,
      })
      localStorage.setItem('authToken', data.access_token)
      if (data.refresh_token) localStorage.setItem('refreshToken', data.refresh_token)
    } catch (err: any) {
      set({ isLoading: false, error: err?.response?.data?.detail || 'Signup failed' })
      throw err
    }
  },

  logout: () => {
    set({ user: null, token: null, error: null })
    localStorage.removeItem('authToken')
    localStorage.removeItem('refreshToken')
    document.cookie = 'auth_token=; path=/; max-age=0'
  },

  getMe: async () => {
    try {
      const res = await apiClient.getMe()
      const data = res.data
      set({ user: data })
    } catch {
      set({ user: null, token: null })
    }
  },

  clearError: () => set({ error: null }),

  hydrate: () => {
    const token = localStorage.getItem('authToken')
    if (token) {
      set({ token })
    }
  },
}))

export interface Project {
  id: string
  title: string
  description?: string
  status: string
  created_at?: string
}

interface ResearchState {
  projects: Project[]
  currentProject: Project | null
  isLoading: boolean
  error: string | null
  fetchProjects: () => Promise<void>
  createProject: (title: string, description?: string) => Promise<Project | null>
  setCurrentProject: (project: Project | null) => void
}

export const useResearchStore = create<ResearchState>((set) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.listProjects()
      set({ projects: res.data.projects || res.data, isLoading: false })
    } catch (err: any) {
      set({ isLoading: false, error: err?.response?.data?.detail || 'Failed to fetch projects' })
    }
  },

  createProject: async (title: string, description?: string) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.createProject(title, description)
      set({ isLoading: false })
      return res.data
    } catch (err: any) {
      set({ isLoading: false, error: err?.response?.data?.detail || 'Failed to create project' })
      return null
    }
  },

  setCurrentProject: (project) => set({ currentProject: project }),
}))

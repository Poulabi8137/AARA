"use client";

import { apiRequest } from "../lib/api-client";

export interface ResearchProject {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: "active" | "archived";
  research_goal?: string | null;
  key_questions?: string[] | null;
  session_count: number;
  paper_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CreateProjectData {
  workspace_id: string;
  name: string;
  description?: string;
  research_goal?: string;
  key_questions?: string[];
}

export interface UpdateProjectData {
  name?: string;
  description?: string;
  research_goal?: string;
  key_questions?: string[];
  status?: "active" | "archived";
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const projectService = {
  list: (workspace_id: string, page = 1, page_size = 20) =>
    apiRequest<PaginatedResponse<ResearchProject>>({
      method: "GET",
      url: "/projects",
      params: { workspace_id, page, page_size },
    }),

  getOne: (id: string) =>
    apiRequest<ResearchProject>({ method: "GET", url: `/projects/${id}` }),

  create: (data: CreateProjectData) =>
    apiRequest<ResearchProject>({ method: "POST", url: "/projects", data }),

  update: (id: string, data: UpdateProjectData) =>
    apiRequest<ResearchProject>({
      method: "PATCH",
      url: `/projects/${id}`,
      data,
    }),

  delete: (id: string) =>
    apiRequest<void>({ method: "DELETE", url: `/projects/${id}` }),

  archive: (id: string) =>
    apiRequest<ResearchProject>({
      method: "POST",
      url: `/projects/${id}/archive`,
    }),

  duplicate: (id: string) =>
    apiRequest<ResearchProject>({
      method: "POST",
      url: `/projects/${id}/duplicate`,
    }),
};

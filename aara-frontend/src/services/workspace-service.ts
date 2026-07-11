"use client";

import { apiRequest } from "../lib/api-client";

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  ownerId: string;
  memberCount: number;
  status: "active" | "archived";
  createdAt: string;
  updatedAt: string;
}

export interface CreateWorkspaceData {
  name: string;
  description?: string;
}

export interface UpdateWorkspaceData {
  name?: string;
  description?: string;
  status?: "active" | "archived";
}

export interface WorkspaceMember {
  id: string;
  workspaceId: string;
  userId: string;
  role: "owner" | "editor" | "viewer" | "member";
  joinedAt: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const workspaceService = {
  // GET /workspaces returns PaginatedResponse<WorkspaceResponse>
  // (`{ items, total, page, page_size, total_pages }`), not a bare array
  // (backend/app/api/routes/workspaces.py:21, response_model=PaginatedResponse[...]).
  getAll: () =>
    apiRequest<PaginatedResponse<Workspace>>({
      method: "GET",
      url: "/workspaces",
      params: { page: 1, page_size: 100 },
    }),

  getOne: (id: string) =>
    apiRequest<Workspace>({ method: "GET", url: `/workspaces/${id}` }),

  create: (data: CreateWorkspaceData) =>
    apiRequest<Workspace>({ method: "POST", url: "/workspaces", data }),

  update: (id: string, data: UpdateWorkspaceData) =>
    apiRequest<Workspace>({ method: "PATCH", url: `/workspaces/${id}`, data }),

  delete: (id: string) =>
    apiRequest<void>({ method: "DELETE", url: `/workspaces/${id}` }),

  addMember: (workspaceId: string, userId: string, role: string) =>
    apiRequest<WorkspaceMember>({
      method: "POST",
      url: `/workspaces/${workspaceId}/members`,
      data: { userId, role },
    }),

  removeMember: (workspaceId: string, userId: string) =>
    apiRequest<void>({
      method: "DELETE",
      url: `/workspaces/${workspaceId}/members/${userId}`,
    }),
};

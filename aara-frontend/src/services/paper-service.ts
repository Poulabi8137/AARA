"use client";

import { apiRequest } from "../lib/api-client";

export interface Paper {
  id: string;
  workspace_id: string;
  project_id?: string | null;
  title: string;
  authors?: string[] | null;
  abstract?: string | null;
  source?: string | null;
  file_path?: string | null;
  file_type?: string | null;
  file_size?: number | null;
  doi?: string | null;
  arxiv_id?: string | null;
  url?: string | null;
  publication_year?: number | null;
  venue?: string | null;
  citation_count: number;
  status?: string | null;
  version: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PaperListFilter {
  workspace_id: string;
  project_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface UpdatePaperData {
  title?: string;
  authors?: string[];
  abstract?: string;
  doi?: string;
  arxiv_id?: string;
  url?: string;
  publication_year?: number;
  venue?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Matches backend/app/api/routes/library.py, prefix /api/v1/library — not
// /papers (that endpoint doesn't exist). Every param below is snake_case
// because that's what FastAPI's Query(...) declarations expect; camelCase
// params are silently dropped and the request falls back to defaults.
export const paperService = {
  list: (filter: PaperListFilter) =>
    apiRequest<PaginatedResponse<Paper>>({
      method: "GET",
      url: "/library",
      params: filter,
    }),

  getOne: (id: string) =>
    apiRequest<Paper>({ method: "GET", url: `/library/${id}` }),

  upload: (file: File, workspace_id: string, project_id?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{
      id: string;
      title: string;
      status: string;
      version: number;
    }>({
      method: "POST",
      url: "/library/upload",
      params: { workspace_id, project_id },
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  update: (id: string, data: UpdatePaperData) =>
    apiRequest<Paper>({ method: "PATCH", url: `/library/${id}`, data }),

  delete: (id: string) =>
    apiRequest<void>({ method: "DELETE", url: `/library/${id}` }),

  replace: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{
      id: string;
      title: string;
      status: string;
      version: number;
    }>({
      method: "POST",
      url: `/library/${id}/replace`,
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  versions: (id: string) =>
    apiRequest<
      {
        version: number;
        file_type: string | null;
        file_size: number | null;
        created_at: string | null;
      }[]
    >({
      method: "GET",
      url: `/library/${id}/versions`,
    }),

  checkDuplicate: (workspace_id: string, content_hash?: string, doi?: string) =>
    apiRequest<{
      is_duplicate: boolean;
      existing_paper: Paper | null;
      confidence: number;
    }>({
      method: "POST",
      url: "/library/check-duplicate",
      params: { workspace_id, content_hash, doi },
    }),
};

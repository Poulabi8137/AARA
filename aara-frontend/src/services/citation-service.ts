"use client";

import { apiRequest } from "../lib/api-client";

export interface Citation {
  id: string;
  workspace_id: string;
  paper_id?: string | null;
  raw_citation_text?: string | null;
  formatted_citation?: string | null;
  style: string;
  source_type: string;
  authors?: string[] | null;
  title?: string | null;
  year?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateCitationData {
  paperId: string;
  style: string;
  formattedCitation?: string;
  rawCitation?: string;
}

export interface UpdateCitationData {
  style?: string;
  formattedCitation?: string;
  rawCitation?: string;
  isSelected?: boolean;
}

export interface CitationFilter {
  workspace_id: string;
  page?: number;
  page_size?: number;
}

export const citationService = {
  // GET /citations requires workspace_id (citations.py::list_citations) and
  // returns a paginated envelope, not a bare array or paper_id-filterable list.
  getAll: (filters: CitationFilter) =>
    apiRequest<PaginatedResponse<Citation>>({
      method: "GET",
      url: "/citations",
      params: filters,
    }),

  getOne: (id: string) =>
    apiRequest<Citation>({ method: "GET", url: `/citations/${id}` }),

  create: (data: CreateCitationData) =>
    apiRequest<Citation>({ method: "POST", url: "/citations", data }),

  update: (id: string, data: UpdateCitationData) =>
    apiRequest<Citation>({ method: "PATCH", url: `/citations/${id}`, data }),

  delete: (id: string) =>
    apiRequest<void>({ method: "DELETE", url: `/citations/${id}` }),

  // Matches backend/app/api/routes/citations.py: POST /citations/export
  // with a JSON body, returning { format, content, filename } — not a GET
  // with a path-joined id list returning a blob (that route doesn't exist).
  export: (
    citationIds: string[],
    format: "bibtex" | "ris" | "apa" | "mla" | "ieee",
  ) =>
    apiRequest<{ format: string; content: string; filename: string }>({
      method: "POST",
      url: "/citations/export",
      data: { citation_ids: citationIds, format },
    }),
};

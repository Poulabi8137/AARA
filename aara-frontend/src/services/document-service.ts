"use client";

import { apiRequest } from "../lib/api-client";

export type DocumentFormat = "markdown" | "docx" | "pdf" | "html";

export interface AaraDocument {
  id: string;
  workspace_id: string;
  session_id?: string | null;
  format: DocumentFormat;
  title: string;
  content?: string | null;
  file_path?: string | null;
  file_size?: number | null;
  status: string;
  version: number;
  citation_count: number;
  template_used?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GenerateDocumentData {
  workspace_id: string;
  session_id?: string;
  project_id?: string;
  format: DocumentFormat;
  title: string;
  template?: string;
  sections?: string[];
}

export interface DocumentExportResult {
  format: string;
  content: string;
  filename: string;
  mime_type?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Matches backend/app/api/routes/documents.py. Note: DocumentResponse has no
// project_id — documents only carry session_id, so project-scoping has to
// join client-side against this project's session ids.
export const documentService = {
  list: (workspace_id: string, page = 1, page_size = 50) =>
    apiRequest<PaginatedResponse<AaraDocument>>({
      method: "GET",
      url: "/documents",
      params: { workspace_id, page, page_size },
    }),

  getOne: (id: string) =>
    apiRequest<AaraDocument>({ method: "GET", url: `/documents/${id}` }),

  generate: (data: GenerateDocumentData) =>
    apiRequest<AaraDocument>({
      method: "POST",
      url: "/documents/generate",
      data,
    }),

  export: (id: string, format: DocumentFormat) =>
    apiRequest<DocumentExportResult>({
      method: "POST",
      url: `/documents/${id}/export`,
      data: { format },
    }),
};

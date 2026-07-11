export const queryKeys = {
  workspaces: ["workspaces"],
  workspace: (id: string) => ["workspaces", id],
  workspaceProjects: (workspaceId: string) => [
    "workspaces",
    workspaceId,
    "projects",
  ],
  projects: (workspaceId: string) => ["projects", { workspaceId }],
  project: (id: string) => ["projects", id],
  papers: ["papers"],
  paper: (id: string) => ["papers", id],
  paperCitations: (paperId: string) => ["papers", paperId, "citations"],
  citations: ["citations"],
  citation: (id: string) => ["citations", id],
  conversations: ["conversations"],
  conversation: (id: string) => ["conversations", id],
  conversationMessages: (conversationId: string) => [
    "conversations",
    conversationId,
    "messages",
  ],
  dashboard: ["dashboard"],
  dashboardWorkspaces: ["dashboard", "workspaces"],
  dashboardPapers: ["dashboard", "papers"],
  dashboardCitations: ["dashboard", "citations"],
  dashboardAI: ["dashboard", "ai"],
} as const;

export type QueryKeys = typeof queryKeys;

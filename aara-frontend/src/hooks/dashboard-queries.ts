"use client";

import { useQuery } from "@tanstack/react-query";
import { apiRequest, ApiClientError } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

// GET /dashboard/stats returns 404 when the user has no workflow-linked
// activity yet (DashboardService.get_dashboard_stats returns None in that
// case). That's a valid "no data yet" response, not a fetch failure, so it
// must resolve to null instead of surfacing as a query error.
export function useDashboardStats() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      try {
        return await apiRequest<any>({
          method: "GET",
          url: "/dashboard/stats",
        });
      } catch (error) {
        if (error instanceof ApiClientError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useDashboardActivity() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "activity"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/dashboard/activity",
        params: { limit: 20 },
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

// /library and /citations both require a workspace_id (papers/citations are
// scoped to a workspace) and return a paginated envelope, neither of which
// fits a workspace-agnostic dashboard overview. The dashboard-specific
// endpoints below return plain arrays of the caller's most recent workspace.
export function useDashboardPapers(workspaceId: string | undefined) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "papers", workspaceId],
    queryFn: () =>
      apiRequest<any[]>({
        method: "GET",
        url: `/dashboard/workspaces/${workspaceId}/papers`,
        params: { limit: 10 },
      }),
    enabled: isAuthenticated && !!workspaceId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useDashboardCitations(workspaceId: string | undefined) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "citations", workspaceId],
    queryFn: () =>
      apiRequest<any[]>({
        method: "GET",
        url: `/dashboard/workspaces/${workspaceId}/citations`,
        params: { limit: 10 },
      }),
    enabled: isAuthenticated && !!workspaceId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export interface WorkflowTimelineEvent {
  event_id: string;
  type: string;
  timestamp: string | null;
  data: Record<string, unknown>;
  agent_id?: string | null;
  status?: string | null;
}

export function useWorkflowTimeline(workflowId: string | null | undefined) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "workflow-timeline", workflowId],
    queryFn: () =>
      apiRequest<WorkflowTimelineEvent[]>({
        method: "GET",
        url: `/dashboard/workflows/${workflowId}/timeline`,
      }),
    enabled: isAuthenticated && !!workflowId,
    staleTime: 1000 * 30,
    gcTime: 1000 * 60 * 5,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export interface EvaluationScore {
  metric: string;
  score: number;
  details: Record<string, unknown> | null;
}

export function useWorkflowEvaluation(workflowId: string | null | undefined) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "workflow-evaluation", workflowId],
    queryFn: () =>
      apiRequest<EvaluationScore[]>({
        method: "GET",
        url: `/dashboard/workflows/${workflowId}/evaluation`,
      }),
    enabled: isAuthenticated && !!workflowId,
    staleTime: 1000 * 30,
    gcTime: 1000 * 60 * 5,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useDashboardAI() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["dashboard", "ai"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/dashboard/ai/stats",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

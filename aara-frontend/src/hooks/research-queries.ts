"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export interface SubmitResearchQueryData {
  query: string;
  project_id: string;
  max_papers?: number;
  research_direction?: string;
}

export function useSubmitResearchQuery() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: SubmitResearchQueryData) =>
      apiRequest<{
        session_id: string;
        workflow_id: string;
        status: string;
        message: string;
      }>({ method: "POST", url: "/research/queries", data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["research", "sessions", { projectId: variables.project_id }],
      });
      toast({
        title: "Research started",
        description: "Watch it run live in Agent Workspace.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to start research",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useResearchOverview() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "overview"],
    queryFn: () =>
      apiRequest<{
        projects?: number;
        papers?: number;
        notes?: number;
        ideas?: number;
        activeProjects?: number;
        completedProjects?: number;
        inProgressProjects?: number;
        staleProjects?: number;
      }>({
        method: "GET",
        url: "/research/overview",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useResearchActivity() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "activity"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/activity",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useResearchCards() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "cards"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/cards",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useResearchNotes() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "notes"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/notes",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useResearchReadingQueue() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "reading-queue"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/reading-queue",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useResearchSavedPapers() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "saved-papers"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/saved-papers",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useResearchRecentActivity() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "recent-activity"],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/recent-activity",
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

export function useTriggerAnalysis() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (sessionId: string) =>
      apiRequest<any>({
        method: "POST",
        url: `/research/sessions/${sessionId}/analysis`,
      }),
    onSuccess: (session) => {
      queryClient.invalidateQueries({
        queryKey: ["research", "sessions", { projectId: session.project_id }],
      });
      toast({
        title: "Analysis complete",
        description: "Gaps and themes have been updated.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Analysis failed",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useTriggerIdeas() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (sessionId: string) =>
      apiRequest<any>({
        method: "POST",
        url: `/research/sessions/${sessionId}/ideas`,
      }),
    onSuccess: (session) => {
      queryClient.invalidateQueries({
        queryKey: ["research", "sessions", { projectId: session.project_id }],
      });
      toast({ title: "Ideas generated" });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Idea generation failed",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export interface GenerateScopingSuggestionData {
  topic: string;
}

// Reuses the existing /ai/generate endpoint (AIService.generate) — a real
// LLM call, not a scripted response. If no provider key is configured it
// still returns 200 with an honest "No LLM provider is configured" message
// (see AIService.generate), so this never has to fake a suggestion.
export function useGenerateScopingSuggestion() {
  return useMutation({
    mutationFn: (data: GenerateScopingSuggestionData) =>
      apiRequest<{ text: string; finish_reason: string | null }>({
        method: "POST",
        url: "/ai/generate",
        data: {
          prompt: `A researcher wants to study: "${data.topic}"\n\nSuggest 2-3 focused research directions they could pursue, and roughly how many papers (between 10 and 100) would be a reasonable scope to review. Be concise — a few sentences, not a report.`,
          context:
            "You are a research scoping assistant inside AARA, an autonomous AI research platform. Help the researcher narrow a broad topic into an actionable research direction.",
        },
      }),
  });
}

export function useResearchSessions(projectId?: string) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["research", "sessions", { projectId }],
    queryFn: () =>
      apiRequest<any>({
        method: "GET",
        url: "/research/sessions",
        // Backend query param is snake_case (research.py::list_sessions) —
        // sending camelCase here previously matched nothing, silently
        // returning every session for the user instead of this project's.
        params: { project_id: projectId },
      }),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
    refetchOnWindowFocus: false,
  });
}

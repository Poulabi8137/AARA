"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  projectService,
  type ResearchProject,
  type CreateProjectData,
  type UpdateProjectData,
} from "@/services/project-service";
import { queryKeys } from "@/lib/query-keys";
import { useToast } from "@/hooks/use-toast";
import { useAuthStore } from "@/stores/auth-store";

export function useProjects(workspaceId: string | null | undefined) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: queryKeys.projects(workspaceId ?? ""),
    queryFn: () => projectService.list(workspaceId as string),
    enabled: isAuthenticated && !!workspaceId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useProject(id: string) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: queryKeys.project(id),
    queryFn: async () => {
      const result = await projectService.getOne(id);
      return result;
    },
    enabled: isAuthenticated && !!id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateProjectData) => projectService.create(data),
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects(newProject.workspace_id),
      });
      toast({
        title: "Project created",
        description: `"${newProject.name}" is ready to work in.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to create project",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateProjectData }) =>
      projectService.update(id, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.project(updated.id), updated);
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects(updated.workspace_id),
      });
      toast({ title: "Project updated" });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to update project",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useArchiveProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: string) => projectService.archive(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.project(updated.id), updated);
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects(updated.workspace_id),
      });
      toast({ title: "Project archived" });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to archive project",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

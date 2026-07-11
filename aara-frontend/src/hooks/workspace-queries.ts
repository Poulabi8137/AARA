"use client";

import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  workspaceService,
  type Workspace,
  type CreateWorkspaceData,
  type UpdateWorkspaceData,
  type PaginatedResponse,
} from "@/services/workspace-service";
import { queryKeys } from "@/lib/query-keys";
import { useToast } from "@/hooks/use-toast";
import { useWorkspaceStore } from "@/stores/workspace-store";

/**
 * Resolves which workspace is "current" for scoping projects/papers.
 * Defaults to the first workspace returned by the API until the user
 * picks one via the workspace switcher (persisted after that).
 */
export function useCurrentWorkspaceId() {
  const { data: workspaces } = useWorkspaces();
  const { currentWorkspaceId, setCurrentWorkspaceId } = useWorkspaceStore();

  useEffect(() => {
    if (!currentWorkspaceId && workspaces && workspaces.length > 0) {
      setCurrentWorkspaceId(workspaces[0].id);
    }
  }, [currentWorkspaceId, workspaces, setCurrentWorkspaceId]);

  return currentWorkspaceId ?? workspaces?.[0]?.id ?? null;
}

export function useWorkspaces() {
  return useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: workspaceService.getAll,
    select: (data) => data.items,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useWorkspace(id: string) {
  return useQuery({
    queryKey: queryKeys.workspace(id),
    queryFn: () => workspaceService.getOne(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: workspaceService.create,
    onSuccess: (newWorkspace) => {
      // The workspaces cache holds the raw paginated response
      // ({items, total, ...}), not a bare array -- useWorkspaces()'s
      // `select` only transforms data at the read site, it doesn't change
      // what's actually stored under this query key. Splicing into it as
      // if it were Workspace[] throws ("old is not iterable"); invalidate
      // and refetch instead, same pattern useCreateProject already uses.
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces });
      toast({
        title: "Workspace created",
        description: `Workspace "${newWorkspace.name}" has been created successfully.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to create workspace",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useUpdateWorkspace() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWorkspaceData }) =>
      workspaceService.update(id, data),
    onSuccess: (updatedWorkspace) => {
      queryClient.setQueryData(
        queryKeys.workspace(updatedWorkspace.id),
        updatedWorkspace,
      );
      // See useCreateWorkspace: this cache holds PaginatedResponse<Workspace>,
      // so update the item inside `items`, not the object itself.
      queryClient.setQueryData(
        queryKeys.workspaces,
        (old: PaginatedResponse<Workspace> | undefined) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((w) =>
              w.id === updatedWorkspace.id ? updatedWorkspace : w,
            ),
          };
        },
      );
      toast({
        title: "Workspace updated",
        description: `Workspace "${updatedWorkspace.name}" has been updated successfully.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to update workspace",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: workspaceService.delete,
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData(
        queryKeys.workspaces,
        (old: PaginatedResponse<Workspace> | undefined) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.filter((w) => w.id !== deletedId),
            total: Math.max(0, old.total - 1),
          };
        },
      );
      queryClient.removeQueries({ queryKey: queryKeys.workspace(deletedId) });
      toast({
        title: "Workspace deleted",
        description: "Workspace has been deleted successfully.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to delete workspace",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useAddWorkspaceMember() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      workspaceId,
      userId,
      role,
    }: {
      workspaceId: string;
      userId: string;
      role: string;
    }) => workspaceService.addMember(workspaceId, userId, role),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspace(variables.workspaceId),
      });
      toast({
        title: "Member added",
        description: "Member has been added to the workspace successfully.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to add member",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useRemoveWorkspaceMember() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      workspaceId,
      userId,
    }: {
      workspaceId: string;
      userId: string;
    }) => workspaceService.removeMember(workspaceId, userId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workspace(variables.workspaceId),
      });
      toast({
        title: "Member removed",
        description: "Member has been removed from the workspace successfully.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to remove member",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

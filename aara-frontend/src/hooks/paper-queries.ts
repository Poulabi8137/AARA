"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  paperService,
  type Paper,
  type PaperListFilter,
  type UpdatePaperData,
} from "@/services/paper-service";
import { useToast } from "@/hooks/use-toast";

function papersQueryKey(filter: PaperListFilter) {
  return ["papers", filter] as const;
}

export function usePapers(filter: PaperListFilter) {
  return useQuery({
    queryKey: papersQueryKey(filter),
    queryFn: () => paperService.list(filter),
    enabled: !!filter.workspace_id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function usePaper(id: string) {
  return useQuery({
    queryKey: ["papers", "detail", id],
    queryFn: () => paperService.getOne(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useUploadPaper() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      file,
      workspace_id,
      project_id,
    }: {
      file: File;
      workspace_id: string;
      project_id?: string;
    }) => paperService.upload(file, workspace_id, project_id),
    onSuccess: (paper) => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      toast({
        title: "Paper uploaded",
        description: `"${paper.title}" was added to the library.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to upload paper",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useUpdatePaper() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdatePaperData }) =>
      paperService.update(id, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(["papers", "detail", updated.id], updated);
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      toast({ title: "Paper updated" });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to update paper",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useDeletePaper() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: string) => paperService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      toast({ title: "Paper deleted" });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to delete paper",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

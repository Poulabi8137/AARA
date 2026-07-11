"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  citationService,
  type Citation,
  type UpdateCitationData,
  type CitationFilter,
} from "@/services/citation-service";
import { queryKeys } from "@/lib/query-keys";
import { useToast } from "@/hooks/use-toast";

export function useCitations(filters: CitationFilter) {
  return useQuery({
    queryKey: [...queryKeys.citations, filters],
    queryFn: () => citationService.getAll(filters),
    enabled: !!filters.workspace_id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useCitation(id: string) {
  return useQuery({
    queryKey: queryKeys.citation(id),
    queryFn: () => citationService.getOne(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useCreateCitation() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: citationService.create,
    onSuccess: (newCitation) => {
      queryClient.setQueryData(
        queryKeys.citations,
        (old: Citation[] | undefined) => {
          if (!old) return [newCitation];
          return [...old, newCitation];
        },
      );
      toast({
        title: "Citation created",
        description: `Citation has been created successfully.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to create citation",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useUpdateCitation() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCitationData }) =>
      citationService.update(id, data),
    onSuccess: (updatedCitation) => {
      queryClient.setQueryData(
        queryKeys.citation(updatedCitation.id),
        updatedCitation,
      );
      queryClient.setQueryData(
        queryKeys.citations,
        (old: Citation[] | undefined) => {
          if (!old) return [updatedCitation];
          return old.map((c) =>
            c.id === updatedCitation.id ? updatedCitation : c,
          );
        },
      );
      queryClient.invalidateQueries({
        queryKey: queryKeys.paperCitations(updatedCitation.paper_id ?? ""),
      });
      toast({
        title: "Citation updated",
        description: `Citation has been updated successfully.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to update citation",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useDeleteCitation() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: citationService.delete,
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData(
        queryKeys.citations,
        (old: Citation[] | undefined) => {
          if (!old) return [];
          return old.filter((c) => c.id !== deletedId);
        },
      );
      queryClient.removeQueries({ queryKey: queryKeys.citation(deletedId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.citations });
      toast({
        title: "Citation deleted",
        description: "Citation has been deleted successfully.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to delete citation",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useExportCitations() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      ids,
      format,
    }: {
      ids: string[];
      format: "bibtex" | "ris" | "apa" | "mla" | "ieee";
    }) => citationService.export(ids, format),
    onSuccess: (result) => {
      const blob = new Blob([result.content], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", result.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast({
        title: "Citations exported",
        description: "Citations have been exported successfully.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to export citations",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

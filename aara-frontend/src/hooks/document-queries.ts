"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  documentService,
  type GenerateDocumentData,
  type DocumentFormat,
} from "@/services/document-service";
import { useToast } from "@/hooks/use-toast";
import { useAuthStore } from "@/stores/auth-store";

export function useDocuments(workspaceId: string | undefined) {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ["documents", workspaceId],
    queryFn: () => documentService.list(workspaceId as string),
    enabled: isAuthenticated && !!workspaceId,
    staleTime: 1000 * 60 * 2,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useGenerateDocument() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: GenerateDocumentData) => documentService.generate(data),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({
        queryKey: ["documents", doc.workspace_id],
      });
      toast({
        title: "Draft generated",
        description: `"${doc.title}" is ready to edit.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to generate document",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useExportDocument() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, format }: { id: string; format: DocumentFormat }) =>
      documentService.export(id, format),
    onSuccess: (result) => {
      const blob = new Blob([result.content], {
        type: result.mime_type || "text/plain",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: "Export ready", description: result.filename });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to export document",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

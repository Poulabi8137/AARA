"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  aiService,
  type Conversation,
  type CreateConversationData,
  type ChatMessage,
  type CreateMessageData,
  type GenerateRequest,
  type GenerateResponse,
} from "@/services/ai-service";
import { queryKeys } from "@/lib/query-keys";
import { useToast } from "@/hooks/use-toast";

export function useConversations(workspaceId?: string) {
  return useQuery({
    queryKey: [...queryKeys.conversations, { workspaceId }],
    queryFn: () => aiService.getConversations(workspaceId),
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: queryKeys.conversation(id),
    queryFn: () => aiService.getConversation(id),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useConversationMessages(conversationId: string) {
  return useQuery({
    queryKey: queryKeys.conversationMessages(conversationId),
    queryFn: () => aiService.getMessages(conversationId),
    enabled: !!conversationId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    retry: 3,
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: aiService.createConversation,
    onSuccess: (newConversation) => {
      queryClient.setQueryData(
        queryKeys.conversations,
        (old: Conversation[] | undefined) => {
          if (!old) return [newConversation];
          return [...old, newConversation];
        },
      );
      toast({
        title: "Conversation created",
        description: `Conversation "${newConversation.title}" has been created successfully.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to create conversation",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useUpdateConversation() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<CreateConversationData>;
    }) => aiService.updateConversation(id, data),
    onSuccess: (updatedConversation) => {
      queryClient.setQueryData(
        queryKeys.conversation(updatedConversation.id),
        updatedConversation,
      );
      queryClient.setQueryData(
        queryKeys.conversations,
        (old: Conversation[] | undefined) => {
          if (!old) return [updatedConversation];
          return old.map((c) =>
            c.id === updatedConversation.id ? updatedConversation : c,
          );
        },
      );
      toast({
        title: "Conversation updated",
        description: `Conversation "${updatedConversation.title}" has been updated successfully.`,
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to update conversation",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: aiService.deleteConversation,
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData(
        queryKeys.conversations,
        (old: Conversation[] | undefined) => {
          if (!old) return [];
          return old.filter((c) => c.id !== deletedId);
        },
      );
      queryClient.removeQueries({
        queryKey: queryKeys.conversation(deletedId),
      });
      queryClient.removeQueries({
        queryKey: queryKeys.conversationMessages(deletedId),
      });
      toast({
        title: "Conversation deleted",
        description: "Conversation has been deleted successfully.",
      });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to delete conversation",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useAddMessage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: aiService.addMessage,
    onSuccess: (newMessage) => {
      queryClient.setQueryData(
        queryKeys.conversationMessages(newMessage.conversationId),
        (old: ChatMessage[] | undefined) => {
          if (!old) return [newMessage];
          return [...old, newMessage];
        },
      );
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to add message",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

export function useGenerateAI() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: aiService.generate,
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to generate response",
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    },
  });
}

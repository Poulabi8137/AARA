"use client";

import { apiRequest } from "../lib/api-client";

export interface Conversation {
  id: string;
  workspaceId: string;
  title: string;
  model: string;
  systemPrompt?: string;
  messages: ChatMessage[];
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface CreateConversationData {
  workspaceId: string;
  title?: string;
  model?: string;
  systemPrompt?: string;
  isPublic?: boolean;
}

export interface CreateMessageData {
  conversationId: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown>;
}

export interface GenerateRequest {
  prompt: string;
  context?: string;
  model?: string;
  maxTokens?: number;
  temperature?: number;
  stream?: boolean;
}

export interface GenerateResponse {
  text: string;
  tokens?: number;
  model?: string;
  finishReason?: string;
  stream?: boolean;
}

export const aiService = {
  getConversations: (workspaceId?: string) =>
    apiRequest<Conversation[]>({
      method: "GET",
      url: "/ai/conversations",
      params: { workspaceId },
    }),

  getConversation: (id: string) =>
    apiRequest<Conversation>({ method: "GET", url: `/ai/conversations/${id}` }),

  createConversation: (data: CreateConversationData) =>
    apiRequest<Conversation>({
      method: "POST",
      url: "/ai/conversations",
      data,
    }),

  updateConversation: (id: string, data: Partial<CreateConversationData>) =>
    apiRequest<Conversation>({
      method: "PATCH",
      url: `/ai/conversations/${id}`,
      data,
    }),

  deleteConversation: (id: string) =>
    apiRequest<void>({ method: "DELETE", url: `/ai/conversations/${id}` }),

  getMessages: (conversationId: string) =>
    apiRequest<ChatMessage[]>({
      method: "GET",
      url: `/ai/conversations/${conversationId}/messages`,
    }),

  addMessage: (data: CreateMessageData) =>
    apiRequest<ChatMessage>({ method: "POST", url: "/ai/messages", data }),

  generate: (data: GenerateRequest) =>
    apiRequest<GenerateResponse>({ method: "POST", url: "/ai/generate", data }),
};

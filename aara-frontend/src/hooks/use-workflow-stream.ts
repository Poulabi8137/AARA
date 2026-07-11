"use client";

import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/stores/auth-store";

export interface WorkflowStreamEvent {
  event_id: string;
  type: string;
  workflow_id: string;
  timestamp: string | null;
  data: Record<string, unknown>;
  agent_id?: string | null;
  status?: string | null;
  step_id?: string | null;
  percentage?: number | null;
  message?: string | null;
  error?: string | null;
}

export type StreamConnectionState =
  "idle" | "connecting" | "open" | "reconnecting" | "closed" | "error";

const TERMINAL_TYPES = new Set([
  "workflow.completed",
  "workflow.failed",
  "workflow.cancelled",
]);

const MAX_RECONNECT_DELAY_MS = 15000;

/**
 * Live event feed for a workflow via the backend SSE endpoint
 * (GET /dashboard/workflows/{id}/stream). Uses `fetch` + a streamed reader
 * rather than the native EventSource API because EventSource cannot send
 * an Authorization header, and this backend has no cookie-based session —
 * auth is bearer-token only (see api-client.ts).
 */
export function useWorkflowStream(workflowId: string | null | undefined) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [events, setEvents] = useState<WorkflowStreamEvent[]>([]);
  const [connectionState, setConnectionState] =
    useState<StreamConnectionState>("idle");

  const stoppedRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    stoppedRef.current = false;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    async function connect() {
      if (stoppedRef.current) return;

      if (!workflowId || !accessToken) {
        setEvents([]);
        setConnectionState("idle");
        return;
      }

      if (attempt === 0) setEvents([]);
      setConnectionState(attempt === 0 ? "connecting" : "reconnecting");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const baseURL =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const response = await fetch(
          `${baseURL}/dashboard/workflows/${workflowId}/stream`,
          {
            headers: {
              Accept: "text/event-stream",
              Authorization: `Bearer ${accessToken}`,
            },
            signal: controller.signal,
          },
        );

        if (!response.ok || !response.body) {
          throw new Error(`Stream request failed: ${response.status}`);
        }

        setConnectionState("open");
        attempt = 0;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!stoppedRef.current) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";

          for (const frame of frames) {
            const dataLine = frame
              .split("\n")
              .find((line) => line.startsWith("data:"));
            if (!dataLine) continue;

            try {
              const parsed: WorkflowStreamEvent = JSON.parse(
                dataLine.slice("data:".length).trim(),
              );
              setEvents((prev) => [...prev, parsed]);
              if (TERMINAL_TYPES.has(parsed.type)) {
                stoppedRef.current = true;
                setConnectionState("closed");
              }
            } catch {
              // Malformed frame — skip rather than tearing down the stream.
            }
          }
        }

        if (!stoppedRef.current) {
          // Connection closed by the server without a terminal event.
          throw new Error("Stream ended unexpectedly");
        }
      } catch {
        if (controller.signal.aborted || stoppedRef.current) return;
        setConnectionState("error");
        attempt += 1;
        const delay = Math.min(1000 * 2 ** attempt, MAX_RECONNECT_DELAY_MS);
        reconnectTimer = setTimeout(connect, delay);
      }
    }

    connect();

    return () => {
      stoppedRef.current = true;
      abortRef.current?.abort();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [workflowId, accessToken]);

  return { events, connectionState };
}

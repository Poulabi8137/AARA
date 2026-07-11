"use client";

import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useResearchSessions } from "@/hooks/research-queries";

export interface SessionSummary {
  id: string;
  query: string;
  status: string;
  created_at: string | null;
  workflow_id: string | null;
  results?: Record<string, any> | null;
  [key: string]: any;
}

const SESSION_PARAM = "session";

/**
 * Every session-scoped tab (Agent Workspace, Timeline, Gaps, Ideas, Review)
 * used to keep its own local `useState` for "which session is selected,"
 * defaulting independently and resetting on every tab switch — so picking a
 * session in one tab had no effect on any other. This hook makes the `?session=`
 * URL param the single source of truth instead, so switching tabs (or sharing
 * a link) keeps the same session in view everywhere.
 *
 * Callers must be rendered inside a <Suspense> boundary, since useSearchParams
 * requires one (see reset-password/page.tsx for the established pattern).
 */
export function useSessionSelection(projectId: string) {
  const { data: sessionsPage, isLoading } = useResearchSessions(projectId);
  const sessions = useMemo(
    () => (sessionsPage?.items ?? []) as SessionSummary[],
    [sessionsPage],
  );

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramSessionId = searchParams.get(SESSION_PARAM);

  const defaultSession =
    sessions.find(
      (s) => s.status === "running" || s.status === "in_progress",
    ) ?? sessions[0];
  const selectedSession =
    sessions.find((s) => s.id === paramSessionId) ?? defaultSession;

  function selectSession(sessionId: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set(SESSION_PARAM, sessionId);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  return {
    sessions,
    isLoading,
    selectedSession,
    selectedSessionId: selectedSession?.id ?? null,
    selectSession,
  };
}

/** Builds an href to another project tab that carries the current session
 * selection forward, so cross-tab links don't drop context. */
export function sessionTabHref(
  projectId: string,
  segment: string | null,
  sessionId: string | null | undefined,
) {
  const base = segment
    ? `/projects/${projectId}/${segment}`
    : `/projects/${projectId}`;
  return sessionId
    ? `${base}?${SESSION_PARAM}=${encodeURIComponent(sessionId)}`
    : base;
}

"use client";

import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api-client";

export type QualityCapability =
  | "plagiarism"
  | "ai_detection"
  | "publication_readiness"
  | "submission_assistant";

export interface QualityCheckResult {
  status: string;
  capability: string;
  message: string;
}

// Phase 5 provider interfaces: real endpoints, but every capability
// currently resolves to an honest "not configured" response since no
// third-party plagiarism/AI-detection/publication-readiness/submission
// integration is wired up yet (see backend/app/services/quality_providers.py).
export function useRunQualityCheck() {
  return useMutation({
    mutationFn: ({
      capability,
      text,
    }: {
      capability: QualityCapability;
      text: string;
    }) =>
      apiRequest<QualityCheckResult>({
        method: "POST",
        url: `/quality/${capability}/check`,
        data: { text },
      }),
  });
}

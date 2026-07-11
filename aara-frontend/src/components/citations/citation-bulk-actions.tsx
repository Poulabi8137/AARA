import React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Citation } from "./citation-card";

interface CitationBulkActionsProps {
  selectedCount: number;
  citations: Citation[];
  className?: string;
}

export function CitationBulkActions({
  selectedCount,
  citations,
  className,
}: CitationBulkActionsProps) {
  if (selectedCount === 0) return null;

  const formatSelectedCount = () => {
    if (selectedCount === 1) return "1 citation selected";
    return `${selectedCount} citations selected`;
  };

  return (
    <Card className={cn("mb-6", className)}>
      <CardContent className="px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">{formatSelectedCount()}</span>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="h-8 text-xs">
                <svg
                  className="w-3 h-3 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2h-2M8 16v-4m0 0l4-4m-4 4l4-4"
                  />
                </svg>
                Export
              </Button>
              <Button variant="ghost" size="sm" className="h-8 text-xs">
                <svg
                  className="w-3 h-3 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2h-2M8 16v-4m0 0l4-4m-4 4l4-4m4 4v4m0-4l-4 4m4-4l-4-4"
                  />
                </svg>
                Copy
              </Button>
              <Button variant="ghost" size="sm" className="h-8 text-xs">
                <svg
                  className="w-3 h-3 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2h-2M8 16v-4m0 0l4-4m-4 4l4-4m4 4v4m0-4l-4 4m4-4l-4-4"
                  />
                </svg>
                Merge
              </Button>
              <Button variant="ghost" size="sm" className="h-8 text-xs">
                <svg
                  className="w-3 h-3 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7h14zM10 11v6m4-6v6m1-10V8a1 1 0 00-1-1h-2a1 1 0 00-1 1v8a1 1 0 001 1h2a1 1 0 001 1h2a1 1 0 001-1V8a1 1 0 00-1-1h-2a1 1 0 00-1 1v8a1 1 0 001 1h2a1 1 0 001 1h2a1 1 0 001-1V8a1 1 0 00-1-1h-2a1 1 0 00-1 1v8a1 1 0 00 1 1h2a1 1 0 00 1 1h2z"
                  />
                </svg>
                Delete
              </Button>
              <Button variant="ghost" size="sm" className="h-8 text-xs">
                <svg
                  className="w-3 h-3 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.517 4.674c.3.921-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.517-4.674a1 1 0 00-.363-1.118L2.98 9.102c-.783-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                  />
                </svg>
                Favorite
              </Button>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => {}}
          >
            Clear Selection
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

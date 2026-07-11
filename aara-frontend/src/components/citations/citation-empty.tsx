import React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

interface CitationEmptyProps {
  className?: string;
  type?: "no-citations" | "no-results" | "empty-collection" | "empty-favorites";
}

export function CitationEmpty({
  className,
  type = "no-citations",
}: CitationEmptyProps) {
  const getEmptyStateContent = () => {
    switch (type) {
      case "no-citations":
        return {
          icon: (
            <svg
              className="w-12 h-12 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          ),
          title: "No citations found",
          description:
            "You haven't added any citations to your collection yet. Start by adding your first citation or importing references.",
          actionText: "Add First Citation",
        };
      case "no-results":
        return {
          icon: (
            <svg
              className="w-12 h-12 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 14l6-6m-6 0l6 6"
              />
            </svg>
          ),
          title: "No search results",
          description:
            "We couldn't find any citations matching your search. Try adjusting your search terms or filters.",
          actionText: "Try Different Search",
        };
      case "empty-collection":
        return {
          icon: (
            <svg
              className="w-12 h-12 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          ),
          title: "Empty collection",
          description:
            "Your citation collection is currently empty. Add citations to build your research bibliography.",
          actionText: "Start Adding Citations",
        };
      case "empty-favorites":
        return {
          icon: (
            <svg
              className="w-12 h-12 text-muted-foreground"
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
          ),
          title: "No favorites yet",
          description:
            "Save your favorite citations by clicking the heart icon. Your favorites will appear here for quick access.",
          actionText: "Explore Citations",
        };
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const { icon, title, description, actionText } = getEmptyStateContent()!;

  return (
    <CardContent
      className={cn(
        "flex flex-col items-center justify-center py-12 px-4 text-center",
        className,
      )}
    >
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground text-sm max-w-sm mb-6">
        {description}
      </p>
      <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium">
        {actionText}
      </button>
    </CardContent>
  );
}

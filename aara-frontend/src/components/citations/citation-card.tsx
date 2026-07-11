import React from "react";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

export interface Citation {
  id: string;
  style?: string;
  formattedCitation?: string;
  rawCitation?: string;
  isSelected?: boolean;
  paperId?: string;
  workspaceId?: string;
  createdAt?: string;
  updatedAt?: string;
  // Display fields (may be absent for service-sourced citations)
  title?: string;
  authors?: string[];
  year?: number;
  journal?: string;
  doi?: string;
  citationCount?: number;
  tags?: string[];
  status?: string;
  isFavorite?: boolean;
  abstract?: string;
}

interface CitationCardProps {
  citation: Citation;
  className?: string;
  isSelected?: boolean;
  onSelect?: () => void;
  onClick?: () => void;
}

export function CitationCard({
  citation,
  className,
  isSelected,
  onSelect,
  onClick,
}: CitationCardProps) {
  const getStyleColor = () => {
    switch (citation.style) {
      case "apa":
        return "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400";
      case "mla":
        return "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400";
      case "chicago":
        return "bg-purple-100 text-purple-700 dark:bg-purple-950/30 dark:text-purple-400";
      case "ieee":
        return "bg-orange-100 text-orange-700 dark:bg-orange-950/30 dark:text-orange-400";
      case "bibtex":
        return "bg-gray-100 text-gray-700 dark:bg-gray-950/30 dark:text-gray-400";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  const getStatusColor = () => {
    switch (citation.status) {
      case "published":
        return "bg-green-100 text-green-800 border-green-200 dark:bg-green-950/30 dark:text-green-400";
      case "draft":
        return "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950/30 dark:text-blue-400";
      case "pending":
        return "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-950/30 dark:text-yellow-400";
      case "archived":
        return "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-950/30 dark:text-gray-400";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-950/30 dark:text-gray-400";
    }
  };

  const renderFavoriteButton = () => (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 w-8 p-0 hover:bg-transparent"
      onClick={(e) => {
        e.stopPropagation();
        // Placeholder for favorite toggle logic
      }}
      aria-label={
        citation.isFavorite ? "Remove from favorites" : "Add to favorites"
      }
    >
      <svg
        className={cn(
          "w-4 h-4",
          citation.isFavorite
            ? "fill-current text-yellow-500"
            : "text-muted-foreground",
        )}
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
    </Button>
  );

  const formatAuthors = (authors?: string[]) => {
    if (!authors || authors.length === 0) return "Unknown Author";
    if (authors.length <= 2) return authors.join(" & ");
    return `${authors[0]} et al.`;
  };

  const getCitationStylePreview = () => {
    const a = citation.authors ?? [];
    const title = citation.title ?? "Untitled";
    const journal = citation.journal ?? "";
    const year = citation.year ?? "";
    if (citation.formattedCitation) {
      return (
        <div className="text-xs font-mono bg-muted/50 p-2 rounded border-l-4 border-blue-500">
          <div className="text-muted-foreground line-clamp-2">
            {citation.formattedCitation}
          </div>
        </div>
      );
    }
    switch (citation.style) {
      case "apa":
        return (
          <div className="text-xs font-mono bg-muted/50 p-2 rounded border-l-4 border-blue-500">
            <div className="font-semibold mb-1">APA Format:</div>
            <div className="text-muted-foreground line-clamp-1">
              {a.join(", ")} ({year}). {title}. {journal}.
            </div>
          </div>
        );
      case "mla":
        return (
          <div className="text-xs font-mono bg-muted/50 p-2 rounded border-l-4 border-green-500">
            <div className="font-semibold mb-1">MLA Format:</div>
            <div className="text-muted-foreground line-clamp-1">
              {a.join(", ")}. &quot;{title}.&quot; {journal}, {year}.
            </div>
          </div>
        );
      case "chicago":
        return (
          <div className="text-xs font-mono bg-muted/50 p-2 rounded border-l-4 border-purple-500">
            <div className="font-semibold mb-1">Chicago Format:</div>
            <div className="text-muted-foreground line-clamp-1">
              {a.join(", ")}. {title}. {journal}, {year}.
            </div>
          </div>
        );
      case "ieee":
        return (
          <div className="text-xs font-mono bg-muted/50 p-2 rounded border-l-4 border-orange-500">
            <div className="font-semibold mb-1">IEEE Format:</div>
            <div className="text-muted-foreground line-clamp-1">
              {a
                .map((auth) => auth.split(" ").slice(0, 2).join(" "))
                .join(", ")}
              , &quot;{title},&quot;
            </div>
          </div>
        );
      case "bibtex":
        return (
          <div className="text-xs font-mono bg-muted/50 p-2 rounded border-l-4 border-gray-500">
            <div className="font-semibold mb-1">BibTeX Format:</div>
            <div className="text-muted-foreground line-clamp-1 font-sans">
              {`@article{${a.join(" and ")}, ${title}, ${journal}, ${year}}`}
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick?.()}
      className="cursor-pointer"
    >
      <Card
        className={cn(
          "h-full cursor-pointer transition-all",
          isSelected &&
            "ring-2 ring-blue-500 bg-blue-50/50 dark:bg-blue-950/20",
          className,
        )}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-lg line-clamp-2">
              {citation.title}
            </CardTitle>
            {renderFavoriteButton()}
          </div>

          <CardDescription className="line-clamp-1">
            {formatAuthors(citation.authors)}{" "}
            {citation.year ? `(${citation.year})` : ""}
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground line-clamp-1">
              {citation.journal}
            </p>

            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={cn(
                  "text-xs px-2 py-1 rounded-full border",
                  getStatusColor(),
                )}
              >
                {citation.status}
              </span>
              <span
                className={cn("text-xs px-2 py-1 rounded", getStyleColor())}
              >
                {citation.style?.toUpperCase() ?? "APA"}
              </span>
              {(citation.tags ?? []).slice(0, 2).map((tag) => (
                <span
                  key={tag}
                  className="text-xs bg-muted/50 text-muted-foreground px-2 py-1 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-muted-foreground">
                {citation.citationCount ?? 0} citations
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => onClick?.()}
              >
                View Details
              </Button>
            </div>

            <div className="pt-2 border-t border-border">
              {getCitationStylePreview()}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function CitationCardCompact({
  citation,
  isSelected,
  onSelect,
  onClick,
  className,
}: CitationCardProps) {
  return (
    <div
      className={`cursor-pointer p-3 border rounded-lg hover:bg-muted/50 transition-colors ${isSelected ? "ring-2 ring-blue-500 bg-blue-50/50" : ""} ${className ?? ""}`}
      onClick={() => onClick?.()}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium line-clamp-1">
          {citation.title || citation.style?.toUpperCase()}
        </span>
        <span className="text-xs text-muted-foreground shrink-0">
          {citation.year ?? ""}
        </span>
      </div>
      {citation.authors && citation.authors.length > 0 && (
        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
          {citation.authors[0]}
          {citation.authors.length > 1 ? " et al." : ""}
        </p>
      )}
    </div>
  );
}

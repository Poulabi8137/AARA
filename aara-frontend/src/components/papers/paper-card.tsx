import React from "react";
import { Star } from "lucide-react";
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

export interface Paper {
  id: string;
  title: string;
  authors?: string[];
  // component display fields (optional — may come from service)
  publication?: string;
  journal?: string;
  year?: number;
  doi?: string;
  abstract?: string;
  keywords?: string[];
  readingStatus?: string;
  isFavorite?: boolean;
  tags?: string[];
  venue?: string;
  // service fields
  type?: string;
  status?: string;
  workspaceId?: string;
  createdAt?: string;
  updatedAt?: string;
  url?: string;
  pdfUrl?: string;
  volume?: string;
  issue?: string;
  pages?: string;
}

interface PaperCardProps {
  paper: Paper;
  className?: string;
  variant?: "default" | "compact";
  onClick?: (paper: Paper) => void;
}

export function PaperCard({
  paper,
  className,
  variant = "default",
  onClick,
}: PaperCardProps) {
  const getReadingStatusColor = () => {
    switch (paper.readingStatus) {
      case "completed":
        return "bg-aara-good-soft text-[var(--aara-good)] border-transparent";
      case "reading":
        return "bg-primary/10 text-primary border-transparent";
      case "paused":
        return "bg-aara-warning-soft text-[var(--aara-warning)] border-transparent";
      default:
        return "bg-muted text-muted-foreground border-transparent";
    }
  };

  const formatAuthors = (authors?: string[]) => {
    if (!authors || authors.length === 0) return "Unknown Author";
    if (authors.length <= 2) return authors.join(" & ");
    return `${authors[0]} et al.`;
  };

  const publication = paper.publication ?? paper.journal ?? "";
  const readingStatus = paper.readingStatus ?? paper.status ?? "not-started";

  const renderFavoriteButton = () => (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 w-8 p-0 hover:bg-transparent"
      onClick={(e) => {
        e.stopPropagation();
      }}
      aria-label={
        paper.isFavorite ? "Remove from favorites" : "Add to favorites"
      }
    >
      <Star
        className={cn(
          "size-4",
          paper.isFavorite
            ? "fill-current text-[var(--aara-signal)]"
            : "text-muted-foreground",
        )}
      />
    </Button>
  );

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick?.(paper)}
      className="cursor-pointer"
    >
      <Card
        className={cn(
          "h-full cursor-pointer transition-all",
          variant === "compact" && "p-4",
          className,
        )}
      >
        <CardHeader className={cn("pb-3", variant === "compact" && "pb-2")}>
          <div className="flex items-start justify-between gap-2">
            <CardTitle
              className={cn(
                "line-clamp-2",
                variant === "compact" ? "text-base" : "text-lg",
              )}
            >
              {paper.title}
            </CardTitle>
            {renderFavoriteButton()}
          </div>

          {variant !== "compact" && (
            <CardDescription className="line-clamp-1">
              {formatAuthors(paper.authors)}
            </CardDescription>
          )}
        </CardHeader>

        <CardContent className={cn("pt-0", variant === "compact" && "pt-2")}>
          {variant !== "compact" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground line-clamp-2">
                {publication}
                {paper.year ? `, ${paper.year}` : ""}
              </p>

              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={cn(
                    "text-xs px-2 py-1 rounded-full border",
                    getReadingStatusColor(),
                  )}
                >
                  {readingStatus.replace("-", " ")}
                </span>
                {(paper.keywords ?? []).slice(0, 2).map((keyword) => (
                  <span
                    key={keyword}
                    className="text-xs bg-muted/50 text-muted-foreground px-2 py-1 rounded"
                  >
                    {keyword}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-muted-foreground">
                  {(paper.tags ?? []).length > 0 && `${paper.tags![0]} • `}
                  {paper.doi ?? ""}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => onClick?.(paper)}
                >
                  View Details
                </Button>
              </div>
            </div>
          )}

          {variant === "compact" && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                {publication}
                {paper.year ? `, ${paper.year}` : ""} •{" "}
                {formatAuthors(paper.authors)}
              </p>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 flex-wrap">
                  <span
                    className={cn(
                      "text-xs px-1.5 py-0.5 rounded",
                      getReadingStatusColor(),
                    )}
                  >
                    {readingStatus.charAt(0).toUpperCase() +
                      readingStatus.slice(1)}
                  </span>
                  {paper.isFavorite && (
                    <Star className="size-3 fill-current text-[var(--aara-signal)]" />
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs p-0"
                  onClick={() => onClick?.(paper)}
                >
                  View
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function PaperCardCompact({
  paper,
  className,
  onClick,
}: Omit<PaperCardProps, "variant">) {
  return (
    <PaperCard
      paper={paper}
      className={className}
      onClick={onClick}
      variant="compact"
    />
  );
}

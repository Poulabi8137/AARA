import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import type { Paper } from "./paper-card";

interface PaperTableProps {
  papers: Paper[];
  className?: string;
  onRowClick?: (paper: Paper) => void;
}

interface SortConfig {
  key: string;
  direction: "asc" | "desc";
}

export function PaperTable({ papers, className, onRowClick }: PaperTableProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);
  const [columnVisibility, setColumnVisibility] = useState<
    Record<string, boolean>
  >({
    title: true,
    authors: true,
    venue: true,
    year: true,
    readingStatus: true,
    tags: true,
    actions: true,
  });

  const sortedPapers = useMemo(() => {
    if (!sortConfig) return papers;

    return [...papers].sort((a, b) => {
      const aValue = (a as unknown as Record<string, unknown>)[sortConfig.key];
      const bValue = (b as unknown as Record<string, unknown>)[sortConfig.key];

      if (typeof aValue === "string" && typeof bValue === "string") {
        return sortConfig.direction === "asc"
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === "number" && typeof bValue === "number") {
        return sortConfig.direction === "asc"
          ? aValue - bValue
          : bValue - aValue;
      }

      return 0;
    });
  }, [papers, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (current?.key === key) {
        return { key, direction: current.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "asc" };
    });
  };

  const getSortIcon = (key: string) => {
    if (sortConfig?.key !== key) {
      return (
        <svg
          className="w-4 h-4 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16V4m0 0L3 8m4-4v12m10-8v8m0 0l4-4m-4 4l-4-4"
          />
        </svg>
      );
    }

    return sortConfig.direction === "asc" ? (
      <svg
        className="w-4 h-4 text-blue-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 4h13M3 4l4 4M3 4l4-4m4 16H3m4 0l4-4m-4 4l-4-4"
        />
      </svg>
    ) : (
      <svg
        className="w-4 h-4 text-blue-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 4h13M3 4l4 4M3 4l4-4m4 16H3m4 0l4-4m-4 4l-4-4"
        />
      </svg>
    );
  };

  const getReadingStatusColor = (status: string | undefined) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800 border-green-200 dark:bg-green-950/30 dark:text-green-400";
      case "reading":
        return "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950/30 dark:text-blue-400";
      case "paused":
        return "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-950/30 dark:text-yellow-400";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-950/30 dark:text-gray-400";
    }
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="px-6">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">Paper Table</CardTitle>
          <div className="flex items-center gap-2">
            <ColumnVisibilityToggle
              columnVisibility={columnVisibility}
              onColumnVisibilityChange={setColumnVisibility}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-6">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {columnVisibility.title && (
                  <th
                    className="text-left py-3 px-4 font-medium text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => handleSort("title")}
                  >
                    <div className="flex items-center gap-2">
                      Title
                      {getSortIcon("title")}
                    </div>
                  </th>
                )}
                {columnVisibility.authors && (
                  <th
                    className="text-left py-3 px-4 font-medium text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => handleSort("authors")}
                  >
                    <div className="flex items-center gap-2">
                      Authors
                      {getSortIcon("authors")}
                    </div>
                  </th>
                )}
                {columnVisibility.venue && (
                  <th
                    className="text-left py-3 px-4 font-medium text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => handleSort("venue")}
                  >
                    <div className="flex items-center gap-2">
                      Venue
                      {getSortIcon("venue")}
                    </div>
                  </th>
                )}
                {columnVisibility.year && (
                  <th
                    className="text-left py-3 px-4 font-medium text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => handleSort("year")}
                  >
                    <div className="flex items-center gap-2">
                      Year
                      {getSortIcon("year")}
                    </div>
                  </th>
                )}
                {columnVisibility.readingStatus && (
                  <th
                    className="text-left py-3 px-4 font-medium text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => handleSort("readingStatus")}
                  >
                    <div className="flex items-center gap-2">
                      Status
                      {getSortIcon("readingStatus")}
                    </div>
                  </th>
                )}
                {columnVisibility.tags && (
                  <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
                    Tags
                  </th>
                )}
                {columnVisibility.actions && (
                  <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
                    Actions
                  </th>
                )}
              </tr>
            </thead>

            <tbody>
              {sortedPapers.map((paper, index) => (
                <motion.tr
                  key={paper.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.05 }}
                  className={cn(
                    "border-b border-border hover:bg-muted/50 transition-colors cursor-pointer",
                    onRowClick && "cursor-pointer",
                  )}
                  onClick={() => onRowClick?.(paper)}
                >
                  {columnVisibility.title && (
                    <td className="py-3 px-4">
                      <div className="font-medium text-sm line-clamp-2">
                        {paper.title}
                      </div>
                    </td>
                  )}
                  {columnVisibility.authors && (
                    <td className="py-3 px-4">
                      <div className="text-sm text-muted-foreground line-clamp-1">
                        {Array.isArray(paper.authors)
                          ? paper.authors.join(", ")
                          : paper.authors}
                      </div>
                    </td>
                  )}
                  {columnVisibility.venue && (
                    <td className="py-3 px-4">
                      <div className="text-sm text-muted-foreground line-clamp-1">
                        {paper.venue}
                      </div>
                    </td>
                  )}
                  {columnVisibility.year && (
                    <td className="py-3 px-4">
                      <div className="text-sm font-medium text-muted-foreground">
                        {paper.year}
                      </div>
                    </td>
                  )}
                  {columnVisibility.readingStatus && (
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border",
                          getReadingStatusColor(paper.readingStatus),
                        )}
                      >
                        {(paper.readingStatus ?? "not-started").replace(
                          "-",
                          " ",
                        )}
                      </span>
                    </td>
                  )}
                  {columnVisibility.tags && (
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {Array.isArray(paper.tags) &&
                          paper.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-muted/50 text-muted-foreground"
                            >
                              {tag}
                            </span>
                          ))}
                        {Array.isArray(paper.tags) && paper.tags.length > 3 && (
                          <span className="text-xs text-muted-foreground">
                            +{paper.tags.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                  )}
                  {columnVisibility.actions && (
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            onRowClick?.(paper);
                          }}
                          aria-label="View paper details"
                        >
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7 1.514-1.162 2.458-2.977 2.458-4.917C24 5.523 19.523 1 12 1S0 5.523 0 12c0 1.94 1.944 3.755 2.458 4.917.554-1.162 1.262-2.326 2.102-3.373"
                            />
                          </svg>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            // Placeholder for favorite action
                          }}
                          aria-label="Add to favorites"
                        >
                          <svg
                            className={cn(
                              "w-4 h-4",
                              paper.isFavorite
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
                      </div>
                    </td>
                  )}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

interface ColumnVisibilityToggleProps {
  columnVisibility: Record<string, boolean>;
  onColumnVisibilityChange: (visibility: Record<string, boolean>) => void;
}

function ColumnVisibilityToggle({
  columnVisibility,
  onColumnVisibilityChange,
}: ColumnVisibilityToggleProps) {
  const columns: { key: string; label: string }[] = [
    { key: "title", label: "Title" },
    { key: "authors", label: "Authors" },
    { key: "venue", label: "Venue" },
    { key: "year", label: "Year" },
    { key: "readingStatus", label: "Status" },
    { key: "tags", label: "Tags" },
    { key: "actions", label: "Actions" },
  ];

  return (
    <div className="relative group">
      <Button variant="outline" size="sm" className="h-8">
        Columns
        <svg
          className="w-4 h-4 ml-2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 5v14m0 0l-4-4m4 4l4-4"
          />
        </svg>
      </Button>

      <div className="absolute right-0 top-full mt-2 hidden group-hover:block z-50">
        <Card className="p-4 min-w-48">
          <div className="space-y-2">
            {columns.map((column) => (
              <label
                key={column.key}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={
                    columnVisibility[
                      column.key as keyof typeof columnVisibility
                    ]
                  }
                  onChange={(e) => {
                    onColumnVisibilityChange({
                      ...columnVisibility,
                      [column.key]: e.target.checked,
                    });
                  }}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium">{column.label}</span>
              </label>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

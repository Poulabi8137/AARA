import React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import type { Paper } from "./paper-card";

interface PaperDetailsProps {
  paper: Paper | null;
  isOpen: boolean;
  onClose: () => void;
}

export function PaperDetails({ paper, isOpen, onClose }: PaperDetailsProps) {
  const getReadingStatusColor = () => {
    if (!paper) return "";
    switch (paper.readingStatus) {
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

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <AnimatePresence>
      {isOpen && paper && (
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 20, stiffness: 100 }}
          className="fixed inset-y-0 right-0 z-50 w-full lg:w-96 bg-background border-l border-border overflow-hidden"
        >
          <Card className="rounded-none border-x-0 border-t-0 h-full">
            <CardHeader className="px-6 py-4 border-b border-border">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-semibold">
                  Paper Details
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  className="h-8 w-8 p-0"
                  aria-label="Close details"
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
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-6 overflow-y-auto h-full">
              <div className="space-y-6">
                {/* Title */}
                <div>
                  <h2 className="text-xl font-semibold leading-tight mb-2">
                    {paper.title}
                  </h2>
                  <p className="text-muted-foreground">
                    {paper.publication}, {paper.year}
                  </p>
                </div>

                {/* Authors */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Authors
                  </h3>
                  <p className="text-sm">{(paper.authors ?? []).join(", ")}</p>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      DOI
                    </h3>
                    <p className="text-sm font-mono text-blue-600 dark:text-blue-400">
                      {paper.doi}
                    </p>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Venue
                    </h3>
                    <p className="text-sm">{paper.venue}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Year
                    </h3>
                    <p className="text-sm font-medium">{paper.year}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Status
                    </h3>
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border",
                        getReadingStatusColor(),
                      )}
                    >
                      {(paper.readingStatus ?? "").replace("-", " ")}
                    </span>
                  </div>
                </div>

                {/* Abstract */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Abstract
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {paper.abstract}
                  </p>
                </div>

                {/* Keywords */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Keywords
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(paper.keywords ?? []).map((keyword) => (
                      <span
                        key={keyword}
                        className="px-2 py-1 bg-muted/50 text-muted-foreground rounded text-xs font-medium"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Tags */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Tags
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(paper.tags ?? []).map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-400 rounded text-xs font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* References Placeholder */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    References
                  </h3>
                  <div className="border border-dashed border-border rounded-lg p-4 text-center">
                    <svg
                      className="w-8 h-8 text-muted-foreground mx-auto mb-2"
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
                    <p className="text-xs text-muted-foreground">
                      References will be populated from backend API
                    </p>
                  </div>
                </div>

                {/* Notes Placeholder */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Notes
                  </h3>
                  <div className="border border-dashed border-border rounded-lg p-4 text-center">
                    <svg
                      className="w-8 h-8 text-muted-foreground mx-auto mb-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                    <p className="text-xs text-muted-foreground">
                      Personal notes and annotations will be saved here
                    </p>
                  </div>
                </div>

                {/* Attachments Placeholder */}
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Attachments
                  </h3>
                  <div className="border border-dashed border-border rounded-lg p-4 text-center">
                    <svg
                      className="w-8 h-8 text-muted-foreground mx-auto mb-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.363 8.321L20.88 12H16.5l-1.5 2-2-2-4 4-2-2-4 4"
                      />
                    </svg>
                    <p className="text-xs text-muted-foreground">
                      PDF files and other attachments will be listed here
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-4 border-t border-border">
                  <div className="flex gap-3">
                    <Button className="flex-1">
                      <svg
                        className="w-4 h-4 mr-2"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4m0 12v4"
                        />
                      </svg>
                      Download PDF
                    </Button>
                    <Button variant="outline" className="flex-1">
                      <svg
                        className="w-4 h-4 mr-2"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                        />
                      </svg>
                      Add Note
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Overlay for mobile */}
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
    </AnimatePresence>
  );
}

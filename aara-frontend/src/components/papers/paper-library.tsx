import React, { useState } from "react";
import { FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { PaperCard, PaperCardCompact } from "./paper-card";
import { PaperTable } from "./paper-table";
import { SearchInterface } from "./search-interface";
import { FilterSidebar } from "./filter-sidebar";
import { PaperDetails } from "./paper-details";
import { PaperSkeleton } from "./paper-skeleton";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { usePapers } from "@/hooks/paper-queries";
import { useToast } from "@/hooks/use-toast";
import type { Paper } from "./paper-card";

interface PaperLibraryProps {
  className?: string;
  workspaceId: string;
  projectId?: string;
}

export function PaperLibrary({
  className,
  workspaceId,
  projectId,
}: PaperLibraryProps) {
  const [view, setView] = useState<"grid" | "list" | "table">("grid");
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const {
    data: papersPage,
    isLoading,
    error,
  } = usePapers({
    workspace_id: workspaceId,
    project_id: projectId,
  });
  const papers = (papersPage?.items ?? []) as unknown as Paper[];
  const { toast } = useToast();

  const openPaperDetails = (paper: Paper) => {
    setSelectedPaper(paper);
    setIsDetailsOpen(true);
  };

  const viewCount = papers.length;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <PaperSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    toast({
      variant: "destructive",
      title: "Error loading papers",
      description: error instanceof Error ? error.message : "Please try again.",
    });
  }

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <PaperLibraryHeader
        view={view}
        onViewChange={setView}
        viewCount={viewCount}
        onToggleFilter={() => setIsFilterOpen(!isFilterOpen)}
      />

      <div className="flex flex-1 overflow-hidden">
        <FilterSidebar
          isOpen={isFilterOpen}
          onClose={() => setIsFilterOpen(false)}
        />

        <main className="flex-1 overflow-auto p-6">
          <SearchInterface className="mb-6" />

          {papers.length === 0 ? (
            <EmptyWorkspace
              icon={<FileText className="size-10" />}
              title="No papers yet"
              description="Papers this project's research sessions retrieve will show up here, or upload one directly."
            />
          ) : (
            <motion.div
              key={view}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {view === "grid" && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {papers.map((paper) => (
                    <PaperCard
                      key={paper.id}
                      paper={paper}
                      onClick={() => openPaperDetails(paper)}
                    />
                  ))}
                </div>
              )}
              {view === "list" && (
                <div className="space-y-3">
                  {papers.map((paper) => (
                    <PaperCardCompact
                      key={paper.id}
                      paper={paper}
                      onClick={() => openPaperDetails(paper)}
                    />
                  ))}
                </div>
              )}
              {view === "table" && (
                <PaperTable
                  papers={papers}
                  onRowClick={(paper) => openPaperDetails(paper)}
                />
              )}
            </motion.div>
          )}
        </main>
      </div>

      <PaperDetails
        paper={selectedPaper}
        isOpen={isDetailsOpen}
        onClose={() => setIsDetailsOpen(false)}
      />
    </div>
  );
}

interface PaperLibraryHeaderProps {
  view: "grid" | "list" | "table";
  onViewChange: (view: "grid" | "list" | "table") => void;
  viewCount: number;
  onToggleFilter: () => void;
}

function PaperLibraryHeader({
  view,
  onViewChange,
  viewCount,
  onToggleFilter,
}: PaperLibraryHeaderProps) {
  return (
    <Card className="rounded-none border-x-0 border-t-0">
      <CardHeader className="px-6">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold">
            Paper Library ({viewCount} papers)
          </CardTitle>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 rounded-lg border bg-background p-1">
              <Button
                variant={view === "grid" ? "default" : "ghost"}
                size="sm"
                onClick={() => onViewChange("grid")}
                className="h-8 w-8 p-0"
                aria-label="Grid view"
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
                    d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                  />
                </svg>
              </Button>
              <Button
                variant={view === "list" ? "default" : "ghost"}
                size="sm"
                onClick={() => onViewChange("list")}
                className="h-8 w-8 p-0"
                aria-label="List view"
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
                    d="M4 6h16M4 10h16M4 14h16M4 18h16"
                  />
                </svg>
              </Button>
              <Button
                variant={view === "table" ? "default" : "ghost"}
                size="sm"
                onClick={() => onViewChange("table")}
                className="h-8 w-8 p-0"
                aria-label="Table view"
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
                    d="M3 10h18M3 14h18m-6-4h6m-6 0a2 2 0 11-4 0 2 2 0 014 0zm-6 0a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
              </Button>
            </div>

            <Button
              variant="outline"
              onClick={onToggleFilter}
              className="md:hidden"
              aria-label="Toggle filters"
            >
              Filters
            </Button>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

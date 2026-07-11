import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { CitationCard, CitationCardCompact } from "./citation-card";
import { CitationTable } from "./citation-table";
import { CitationStyles } from "./citation-styles";
import { CitationDetails } from "./citation-details";
import { CitationSearch } from "./citation-search";
import { CitationBulkActions } from "./citation-bulk-actions";
import { CitationSkeleton } from "./citation-skeleton";
import { CitationEmpty } from "./citation-empty";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { motion } from "framer-motion";
import { useCitations } from "@/hooks/citation-queries";
import { useToast } from "@/hooks/use-toast";
import type { Citation } from "./citation-card";

interface CitationManagerProps {
  className?: string;
  workspaceId: string;
}

export function CitationManager({
  className,
  workspaceId,
}: CitationManagerProps) {
  const [view, setView] = useState<"card" | "table" | "grouped">("card");
  const [selectedCitations, setSelectedCitations] = useState<string[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(
    null,
  );
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [activeStyle, setActiveStyle] = useState<
    "apa" | "mla" | "chicago" | "ieee" | "bibtex"
  >("apa");

  const {
    data: citationsPage,
    isLoading,
    error,
  } = useCitations({ workspace_id: workspaceId });
  const citations = (citationsPage?.items ?? []) as unknown as Citation[];
  const { toast } = useToast();
  void activeStyle; // used by CitationStyles

  const openCitationDetails = (citation: Citation) => {
    setSelectedCitation(citation);
    setIsDetailsOpen(true);
  };

  const toggleCitationSelection = (citationId: string) => {
    setSelectedCitations((prev) =>
      prev.includes(citationId)
        ? prev.filter((id) => id !== citationId)
        : [...prev, citationId],
    );
  };

  const selectAllCitations = () => {
    setSelectedCitations(citations.map((c) => c.id));
  };

  const clearSelection = () => {
    setSelectedCitations([]);
  };

  const viewCount = citations.length;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <CitationSkeleton />
      </div>
    );
  }

  if (error) {
    toast({
      variant: "destructive",
      title: "Error loading citations",
      description: error instanceof Error ? error.message : "Please try again.",
    });
  }

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <CitationManagerHeader
        view={view}
        onViewChange={setView}
        viewCount={viewCount}
        selectedCount={selectedCitations.length}
        onSelectAll={selectAllCitations}
        onClearSelection={clearSelection}
      />

      <div className="flex flex-1 overflow-hidden">
        <CitationSearch className="mb-4" />
      </div>

      <div className="flex-1 min-h-0 overflow-auto px-6">
        <CitationStyles
          activeStyle={activeStyle}
          onStyleChange={setActiveStyle}
          className="mb-6"
        />

        {citations.length === 0 ? (
          <CitationEmpty type="no-citations" className="my-8" />
        ) : (
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {view === "card" && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {citations.map((citation) => (
                  <CitationCard
                    key={citation.id}
                    citation={citation}
                    isSelected={selectedCitations.includes(citation.id)}
                    onSelect={() => toggleCitationSelection(citation.id)}
                    onClick={() => openCitationDetails(citation)}
                  />
                ))}
              </div>
            )}
            {view === "table" && (
              <CitationTable
                citations={citations}
                selectedCitations={selectedCitations}
                onSelect={toggleCitationSelection}
                onSelectAll={selectAllCitations}
                onCitationClick={(citation) => openCitationDetails(citation)}
              />
            )}
            {view === "grouped" && (
              <div className="space-y-6">
                {["Published", "Draft", "Pending", "Archived"].map((status) => {
                  const filtered = citations.filter((c) => c.status === status);
                  if (filtered.length === 0) return null;

                  return (
                    <div key={status}>
                      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-primary" />
                        {status} ({filtered.length})
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filtered.map((citation) => (
                          <CitationCardCompact
                            key={citation.id}
                            citation={citation}
                            isSelected={selectedCitations.includes(citation.id)}
                            onSelect={() =>
                              toggleCitationSelection(citation.id)
                            }
                            onClick={() => openCitationDetails(citation)}
                          />
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}
      </div>

      <CitationBulkActions
        selectedCount={selectedCitations.length}
        citations={citations.filter((c) => selectedCitations.includes(c.id))}
      />

      <CitationDetails
        citation={selectedCitation}
        isOpen={isDetailsOpen}
        onClose={() => setIsDetailsOpen(false)}
      />
    </div>
  );
}

interface CitationManagerHeaderProps {
  view: "card" | "table" | "grouped";
  onViewChange: (view: "card" | "table" | "grouped") => void;
  viewCount: number;
  selectedCount: number;
  onSelectAll: () => void;
  onClearSelection: () => void;
}

function CitationManagerHeader({
  view,
  onViewChange,
  viewCount,
  selectedCount,
  onSelectAll,
  onClearSelection,
}: CitationManagerHeaderProps) {
  return (
    <Card className="rounded-none border-x-0 border-t-0">
      <CardHeader className="px-6">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold">
            Citation Manager ({viewCount} citations)
          </CardTitle>

          {selectedCount > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                {selectedCount} selected
              </span>
              <button
                onClick={onClearSelection}
                className="text-sm text-primary hover:text-primary/80 font-medium"
              >
                Clear Selection
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4 mt-4">
          <div className="hidden md:flex items-center gap-2 rounded-lg border bg-background p-1">
            <button
              onClick={() => onViewChange("card")}
              className={cn(
                "px-3 py-1 rounded text-sm font-medium transition-colors",
                view === "card"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              Card View
            </button>
            <button
              onClick={() => onViewChange("table")}
              className={cn(
                "px-3 py-1 rounded text-sm font-medium transition-colors",
                view === "table"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              Table View
            </button>
            <button
              onClick={() => onViewChange("grouped")}
              className={cn(
                "px-3 py-1 rounded text-sm font-medium transition-colors",
                view === "grouped"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              Grouped View
            </button>
          </div>

          <div className="flex md:hidden items-center gap-1 rounded-lg border bg-background p-1">
            <button
              onClick={() => onViewChange("card")}
              className={cn(
                "px-2 py-1 rounded text-xs font-medium transition-colors",
                view === "card"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              Card
            </button>
            <button
              onClick={() => onViewChange("table")}
              className={cn(
                "px-2 py-1 rounded text-xs font-medium transition-colors",
                view === "table"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              Table
            </button>
            <button
              onClick={() => onViewChange("grouped")}
              className={cn(
                "px-2 py-1 rounded text-xs font-medium transition-colors",
                view === "grouped"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              Grouped
            </button>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

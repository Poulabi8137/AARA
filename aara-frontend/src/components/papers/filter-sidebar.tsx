import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";

interface FilterSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface YearRange {
  min: number;
  max: number;
}

interface Author {
  id: string;
  name: string;
  papers: number;
}

interface Venue {
  id: string;
  name: string;
  papers: number;
}

interface Tag {
  id: string;
  name: string;
  count: number;
}

export function FilterSidebar({ isOpen, onClose }: FilterSidebarProps) {
  const [yearRange, setYearRange] = useState<YearRange>({
    min: 2020,
    max: 2024,
  });
  const [selectedYears, setSelectedYears] = useState<number[]>([]);
  const [selectedAuthors, setSelectedAuthors] = useState<string[]>([]);
  const [selectedVenues, setSelectedVenues] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [selectedFavorites, setSelectedFavorites] = useState(false);
  const [selectedUploaded, setSelectedUploaded] = useState(false);
  const [selectedImported, setSelectedImported] = useState(false);

  const authors: Author[] = [
    { id: "1", name: "Dr. Sarah Chen", papers: 3 },
    { id: "2", name: "Prof. Michael Roberts", papers: 2 },
    { id: "3", name: "Dr. Alex Martinez", papers: 5 },
    { id: "4", name: "Dr. Priya Sharma", papers: 4 },
    { id: "5", name: "Prof. Robert Kim", papers: 1 },
  ];

  const venues: Venue[] = [
    { id: "1", name: "Journal of Computer Science", papers: 2 },
    { id: "2", name: "Nature Medicine", papers: 1 },
    { id: "3", name: "Science Direct", papers: 2 },
    { id: "4", name: "Environmental Research", papers: 1 },
    { id: "5", name: "IEEE Access", papers: 1 },
    { id: "6", name: "Data Science Journal", papers: 1 },
  ];

  const tags: Tag[] = [
    { id: "1", name: "machine-learning", count: 4 },
    { id: "2", name: "climate-change", count: 2 },
    { id: "3", name: "ai-research", count: 3 },
    { id: "4", name: "deep-learning", count: 2 },
    { id: "5", name: "neural-networks", count: 2 },
    { id: "6", name: "research-methods", count: 3 },
    { id: "7", name: "optimization", count: 1 },
    { id: "8", name: "algorithms", count: 2 },
  ];

  const years = Array.from(
    { length: yearRange.max - yearRange.min + 1 },
    (_, i) => yearRange.min + i,
  );

  const statusOptions = [
    {
      id: "reading",
      label: "Reading",
      color: "bg-blue-100 text-blue-800 border-blue-200",
    },
    {
      id: "completed",
      label: "Completed",
      color: "bg-green-100 text-green-800 border-green-200",
    },
    {
      id: "paused",
      label: "Paused",
      color: "bg-yellow-100 text-yellow-800 border-yellow-200",
    },
    {
      id: "not-started",
      label: "Not Started",
      color: "bg-gray-100 text-gray-800 border-gray-200",
    },
  ];

  const handleYearToggle = (year: number) => {
    setSelectedYears((prev) =>
      prev.includes(year) ? prev.filter((y) => y !== year) : [...prev, year],
    );
  };

  const handleAuthorToggle = (authorId: string) => {
    setSelectedAuthors((prev) =>
      prev.includes(authorId)
        ? prev.filter((id) => id !== authorId)
        : [...prev, authorId],
    );
  };

  const handleVenueToggle = (venueId: string) => {
    setSelectedVenues((prev) =>
      prev.includes(venueId)
        ? prev.filter((id) => id !== venueId)
        : [...prev, venueId],
    );
  };

  const handleTagToggle = (tagId: string) => {
    setSelectedTags((prev) =>
      prev.includes(tagId)
        ? prev.filter((id) => id !== tagId)
        : [...prev, tagId],
    );
  };

  const handleStatusToggle = (statusId: string) => {
    setSelectedStatuses((prev) =>
      prev.includes(statusId)
        ? prev.filter((id) => id !== statusId)
        : [...prev, statusId],
    );
  };

  const clearAllFilters = () => {
    setSelectedYears([]);
    setSelectedAuthors([]);
    setSelectedVenues([]);
    setSelectedTags([]);
    setSelectedStatuses([]);
    setSelectedFavorites(false);
    setSelectedUploaded(false);
    setSelectedImported(false);
  };

  const activeFiltersCount =
    selectedYears.length +
    selectedAuthors.length +
    selectedVenues.length +
    selectedTags.length +
    selectedStatuses.length +
    (selectedFavorites ? 1 : 0) +
    (selectedUploaded ? 1 : 0) +
    (selectedImported ? 1 : 0);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 20, stiffness: 100 }}
          className="fixed inset-y-0 right-0 z-50 w-80 lg:w-96 bg-background border-l border-border overflow-hidden"
        >
          <div className="flex flex-col h-full">
            <Card className="rounded-none border-x-0 border-t-0 h-full">
              <CardHeader className="px-4 py-3 border-b border-border">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold">
                    Filters
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="h-8 w-8 p-0 lg:hidden"
                    aria-label="Close filters"
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

                {activeFiltersCount > 0 && (
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-muted-foreground">
                      {activeFiltersCount} active filter
                      {activeFiltersCount !== 1 ? "s" : ""}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearAllFilters}
                      className="h-6 text-xs text-blue-600 hover:text-blue-700 p-0"
                    >
                      Clear All
                    </Button>
                  </div>
                )}
              </CardHeader>

              <CardContent className="flex-1 overflow-y-auto p-4 space-y-6">
                {/* Year Range */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Year Range</h3>
                  <div className="flex items-center gap-3 mb-2">
                    <input
                      type="number"
                      value={yearRange.min}
                      onChange={(e) =>
                        setYearRange((prev) => ({
                          ...prev,
                          min: parseInt(e.target.value) || 0,
                        }))
                      }
                      className="w-20 px-2 py-1 text-sm border border-border rounded"
                      min={1900}
                      max={yearRange.max}
                    />
                    <span className="text-sm text-muted-foreground">to</span>
                    <input
                      type="number"
                      value={yearRange.max}
                      onChange={(e) =>
                        setYearRange((prev) => ({
                          ...prev,
                          max:
                            parseInt(e.target.value) ||
                            new Date().getFullYear(),
                        }))
                      }
                      className="w-20 px-2 py-1 text-sm border border-border rounded"
                      min={yearRange.min}
                      max={new Date().getFullYear()}
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {years.map((year) => (
                      <button
                        key={year}
                        onClick={() => handleYearToggle(year)}
                        className={cn(
                          "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
                          selectedYears.includes(year)
                            ? "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/30 dark:text-blue-400"
                            : "bg-muted/50 text-muted-foreground border-border hover:bg-muted",
                        )}
                      >
                        {year}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Authors */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Authors</h3>
                  <div className="space-y-2">
                    {authors.map((author) => (
                      <label
                        key={author.id}
                        className="flex items-center justify-between p-2 rounded hover:bg-muted/50 cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={selectedAuthors.includes(author.id)}
                            onChange={() => handleAuthorToggle(author.id)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm font-medium">
                            {author.name}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {author.papers}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Venues */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Venues</h3>
                  <div className="space-y-2">
                    {venues.map((venue) => (
                      <label
                        key={venue.id}
                        className="flex items-center justify-between p-2 rounded hover:bg-muted/50 cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={selectedVenues.includes(venue.id)}
                            onChange={() => handleVenueToggle(venue.id)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="text-sm font-medium">
                            {venue.name}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {venue.papers}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Tags */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => (
                      <button
                        key={tag.id}
                        onClick={() => handleTagToggle(tag.id)}
                        className={cn(
                          "px-2 py-1 rounded text-xs font-medium transition-colors",
                          selectedTags.includes(tag.id)
                            ? "bg-blue-100 text-blue-800 dark:bg-blue-950/30 dark:text-blue-400"
                            : "bg-muted/50 text-muted-foreground hover:bg-muted",
                        )}
                      >
                        {tag.name} ({tag.count})
                      </button>
                    ))}
                  </div>
                </div>

                {/* Status */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Reading Status</h3>
                  <div className="space-y-2">
                    {statusOptions.map((status) => (
                      <label
                        key={status.id}
                        className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedStatuses.includes(status.id)}
                          onChange={() => handleStatusToggle(status.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span
                          className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border",
                            status.color,
                          )}
                        >
                          {status.label}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Checkboxes */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Other Options</h3>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedFavorites}
                        onChange={(e) => setSelectedFavorites(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium">
                        Favorites only
                      </span>
                    </label>
                    <label className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedUploaded}
                        onChange={(e) => setSelectedUploaded(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium">
                        Uploaded by me
                      </span>
                    </label>
                    <label className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedImported}
                        onChange={(e) => setSelectedImported(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium">Imported</span>
                    </label>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
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

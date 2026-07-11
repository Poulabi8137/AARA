import React, { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface SearchInterfaceProps {
  className?: string;
  onSearch?: (query: string) => void;
}

interface RecentSearch {
  id: string;
  query: string;
  timestamp: Date;
}

interface SearchSuggestion {
  id: string;
  text: string;
  category: "recent" | "popular" | "trending";
}

export function SearchInterface({ className, onSearch }: SearchInterfaceProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const [filterChips, setFilterChips] = useState<string[]>([]);
  const searchRef = useRef<HTMLDivElement>(null);

  const popularSuggestions: SearchSuggestion[] = [
    { id: "1", text: "machine learning", category: "popular" },
    { id: "2", text: "climate change", category: "popular" },
    { id: "3", text: "neural networks", category: "popular" },
    { id: "4", text: "data science", category: "popular" },
    { id: "5", text: "AI research", category: "trending" },
    { id: "6", text: "deep learning", category: "trending" },
    { id: "7", text: "algorithm", category: "trending" },
    { id: "8", text: "publication", category: "recent" },
  ];

  const filterOptions = [
    "2024",
    "2023",
    "2022",
    "Machine Learning",
    "Computer Science",
    "Nature",
    "Science",
  ];

  useEffect(() => {
    // Client-only localStorage read: must run in an effect to stay SSR-safe
    // (a lazy useState initializer would run during SSR too and cause a hydration mismatch).
    const savedSearches = localStorage.getItem("recentSearches");
    if (savedSearches) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRecentSearches(JSON.parse(savedSearches));
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (
        searchRef.current &&
        !searchRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const suggestions = query.trim()
    ? popularSuggestions.filter((suggestion) =>
        suggestion.text.toLowerCase().includes(query.toLowerCase()),
      )
    : [];

  const handleSearch = (searchQuery: string) => {
    if (searchQuery.trim()) {
      const newSearch: RecentSearch = {
        id: Date.now().toString(),
        query: searchQuery,
        timestamp: new Date(),
      };

      setRecentSearches((prev) => [newSearch, ...prev.slice(0, 4)]);
      localStorage.setItem(
        "recentSearches",
        JSON.stringify([newSearch, ...recentSearches.slice(0, 4)]),
      );

      onSearch?.(searchQuery);
      setQuery("");
      setIsOpen(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch(query);
    }
  };

  const removeRecentSearch = (id: string) => {
    setRecentSearches((prev) => prev.filter((search) => search.id !== id));
    const updatedSearches = recentSearches.filter((search) => search.id !== id);
    localStorage.setItem("recentSearches", JSON.stringify(updatedSearches));
  };

  const addFilterChip = (filter: string) => {
    if (!filterChips.includes(filter)) {
      setFilterChips((prev) => [...prev, filter]);
    }
  };

  const removeFilterChip = (filter: string) => {
    setFilterChips((prev) => prev.filter((f) => f !== filter));
  };

  const clearAllFilters = () => {
    setFilterChips([]);
  };

  const formatRelativeTime = (date: Date) => {
    const diffInMinutes = Math.floor(
      (new Date().getTime() - date.getTime()) / (1000 * 60),
    );
    if (diffInMinutes < 60) {
      return `${diffInMinutes}m ago`;
    }
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    }
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  return (
    <div ref={searchRef} className={cn("relative w-full", className)}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
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
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search papers, authors, venues..."
          className="block w-full pl-10 pr-4 py-2.5 border border-border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute inset-y-0 right-0 flex items-center pr-3"
            aria-label="Clear search"
          >
            <svg
              className="w-4 h-4 text-muted-foreground hover:text-foreground"
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
          </button>
        )}
      </div>

      {/* Suggestions Dropdown */}
      {isOpen && (query || recentSearches.length > 0) && (
        <Card className="absolute top-full mt-2 w-full z-50 shadow-lg border border-border">
          <CardContent className="p-0">
            {query && suggestions.length > 0 && (
              <div className="p-3">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Suggestions
                </h3>
                <div className="space-y-1">
                  {suggestions.slice(0, 5).map((suggestion) => (
                    <button
                      key={suggestion.id}
                      onClick={() => handleSearch(suggestion.text)}
                      className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-muted transition-colors flex items-center gap-2"
                    >
                      <svg
                        className="w-3 h-3 text-muted-foreground"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 14-0zM10 14l6-6m-6 0l6 6"
                        />
                      </svg>
                      {suggestion.text}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {recentSearches.length > 0 && (
              <div className="p-3 border-t border-border">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Recent Searches
                  </h3>
                  <button
                    onClick={() => setRecentSearches([])}
                    className="text-xs text-blue-500 hover:text-blue-600 font-medium"
                  >
                    Clear All
                  </button>
                </div>
                <div className="space-y-1">
                  {recentSearches.map((search) => (
                    <div
                      key={search.id}
                      className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-muted transition-colors group"
                    >
                      <button
                        onClick={() => handleSearch(search.query)}
                        className="text-sm flex-1 text-left"
                      >
                        <div className="font-medium">{search.query}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {formatRelativeTime(search.timestamp)}
                        </div>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeRecentSearch(search.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1"
                        aria-label="Remove from recent searches"
                      >
                        <svg
                          className="w-3 h-3 text-muted-foreground"
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
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {filterChips.length > 0 && (
              <div className="p-3 border-t border-border bg-muted/30">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Active Filters
                  </h3>
                  <button
                    onClick={clearAllFilters}
                    className="text-xs text-blue-500 hover:text-blue-600 font-medium"
                  >
                    Clear All
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {filterChips.map((filter) => (
                    <span
                      key={filter}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-950/30 text-blue-800 dark:text-blue-400 rounded-full text-xs font-medium"
                    >
                      {filter}
                      <button
                        onClick={() => removeFilterChip(filter)}
                        className="hover:text-blue-900 dark:hover:text-blue-300"
                        aria-label={`Remove ${filter} filter`}
                      >
                        <svg
                          className="w-3 h-3"
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
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick Filter Chips */}
      <div className="mt-3 flex flex-wrap gap-2">
        {filterOptions.slice(0, 6).map((filter) => (
          <button
            key={filter}
            onClick={() => addFilterChip(filter)}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
              filterChips.includes(filter)
                ? "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-700"
                : "bg-muted/50 text-muted-foreground border-border hover:bg-muted",
            )}
          >
            {filter}
          </button>
        ))}
        <button
          onClick={() => setIsOpen(true)}
          className="px-3 py-1 rounded-full text-xs font-medium border border-dashed border-muted-foreground/50 text-muted-foreground hover:border-muted-foreground hover:bg-muted/30 transition-colors"
        >
          + Add Filter
        </button>
      </div>
    </div>
  );
}

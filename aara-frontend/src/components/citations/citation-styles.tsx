import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface CitationStylesProps {
  className?: string;
  activeStyle: "apa" | "mla" | "chicago" | "ieee" | "bibtex";
  onStyleChange: (style: "apa" | "mla" | "chicago" | "ieee" | "bibtex") => void;
}

export function CitationStyles({
  className,
  activeStyle,
  onStyleChange,
}: CitationStylesProps) {
  const styles = [
    {
      id: "apa",
      name: "APA",
      description: "American Psychological Association",
      example: "Smith, J. (2024). Title. Journal, 12(3), 123-145.",
    },
    {
      id: "mla",
      name: "MLA",
      description: "Modern Language Association",
      example:
        'Smith, John. "Title." Journal, vol. 12, no. 3, 2024, pp. 123-145.',
    },
    {
      id: "chicago",
      name: "Chicago",
      description: "Chicago Manual of Style",
      example: 'Smith, John. "Title." Journal 12, no. 3 (2024): 123-145.',
    },
    {
      id: "ieee",
      name: "IEEE",
      description: "Institute of Electrical and Electronics Engineers",
      example: 'J. Smith, "Title," Journal, vol. 12, no. 3, pp. 123-145, 2024.',
    },
    {
      id: "bibtex",
      name: "BibTeX",
      description: "Bibliography database",
      example:
        "@article{smith2024title, author={Smith, John}, title={Title}, journal={Journal}, year={2024}}",
    },
  ];

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="px-6">
        <CardTitle className="text-lg font-semibold">Citation Styles</CardTitle>
      </CardHeader>

      <CardContent className="px-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {styles.map((style) => (
            <button
              key={style.id}
              onClick={() =>
                onStyleChange(
                  style.id as "apa" | "mla" | "chicago" | "ieee" | "bibtex",
                )
              }
              className={cn(
                "p-4 rounded-lg border transition-all text-left",
                activeStyle === style.id
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                  : "border-border hover:border-muted-foreground hover:bg-muted/50",
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm">{style.name}</h3>
                {activeStyle === style.id && (
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                )}
              </div>
              <p className="text-xs text-muted-foreground mb-2">
                {style.description}
              </p>
              <div className="text-xs font-mono text-muted-foreground line-clamp-2">
                {style.example}
              </div>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

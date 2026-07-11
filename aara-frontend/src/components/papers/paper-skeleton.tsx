import React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface PaperSkeletonProps {
  className?: string;
  variant?: "default" | "compact";
}

export function PaperSkeleton({
  className,
  variant = "default",
}: PaperSkeletonProps) {
  return (
    <Card className={cn("h-full", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-muted rounded animate-pulse" />
            {variant === "default" && (
              <div className="h-3 bg-muted rounded animate-pulse w-3/4" />
            )}
          </div>
          <div className="w-4 h-4 bg-muted rounded animate-pulse" />
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {variant === "default" && (
          <div className="space-y-3">
            <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
            <div className="flex items-center gap-2">
              <div className="h-5 w-16 bg-muted rounded animate-pulse" />
              <div className="h-5 w-20 bg-muted rounded animate-pulse" />
            </div>
            <div className="flex items-center justify-between pt-2">
              <div className="h-3 bg-muted rounded animate-pulse w-24" />
              <div className="h-7 w-16 bg-muted rounded animate-pulse" />
            </div>
          </div>
        )}

        {variant === "compact" && (
          <div className="space-y-2">
            <div className="h-3 bg-muted rounded animate-pulse w-3/4" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-5 w-12 bg-muted rounded animate-pulse" />
                <div className="w-3 h-3 bg-muted rounded animate-pulse" />
              </div>
              <div className="h-6 w-12 bg-muted rounded animate-pulse" />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

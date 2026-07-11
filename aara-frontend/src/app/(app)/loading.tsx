import React from "react";

export default function DashboardLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div
            className="size-2.5 animate-pulse rounded-full bg-primary/60"
            style={{ animationDelay: "0ms" }}
          />
          <div
            className="size-2.5 animate-pulse rounded-full bg-primary/60"
            style={{ animationDelay: "150ms" }}
          />
          <div
            className="size-2.5 animate-pulse rounded-full bg-primary/60"
            style={{ animationDelay: "300ms" }}
          />
        </div>
        <p className="text-xs text-muted-foreground/60">Loading…</p>
      </div>
    </div>
  );
}

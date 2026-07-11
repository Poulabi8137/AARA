import React from "react";
import { cn } from "@/lib/utils";

interface WorkspaceHeaderProps {
  title: string;
  breadcrumbs?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function WorkspaceHeader({
  title,
  breadcrumbs,
  actions,
  className,
}: WorkspaceHeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-10 flex h-16 items-center justify-between border-b border-border/60 bg-background/80 backdrop-blur-xl px-4 md:px-6",
        className,
      )}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {breadcrumbs && <div className="hidden md:block">{breadcrumbs}</div>}
        <h1 className="text-lg font-semibold tracking-tight truncate">
          {title}
        </h1>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

import React from "react";
import { cn } from "@/lib/utils";

interface EmptyWorkspaceProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyWorkspace({
  title = "No workspace selected",
  description = "Select a workspace from the sidebar to get started",
  icon,
  action,
  className,
}: EmptyWorkspaceProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center min-h-[400px] p-8 text-center",
        className,
      )}
    >
      <div className="mb-5 flex items-center justify-center">
        {icon || (
          <div className="flex size-14 items-center justify-center rounded-2xl bg-muted/50">
            <svg
              className="w-6 h-6 text-muted-foreground/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          </div>
        )}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
      <p className="mb-6 max-w-sm text-sm text-muted-foreground/80 leading-relaxed">
        {description}
      </p>
      {action}
    </div>
  );
}

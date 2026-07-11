import React from "react";
import { cn } from "@/lib/utils";

interface WorkspacePanelProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
  side?: "right" | "left";
}

export function WorkspacePanel({
  children,
  title,
  className,
  side = "right",
}: WorkspacePanelProps) {
  return (
    <aside
      className={cn(
        "hidden lg:flex w-80 flex-col border-l bg-background",
        side === "left" && "border-r border-l-0",
        className,
      )}
    >
      {title && (
        <div className="flex h-16 items-center border-b px-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            {title}
          </h2>
        </div>
      )}
      <div className="flex-1 overflow-y-auto p-4">{children}</div>
    </aside>
  );
}

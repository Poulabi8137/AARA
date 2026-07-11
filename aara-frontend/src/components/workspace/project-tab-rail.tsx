"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { projectNavItems, projectTabHref } from "@/lib/project-nav-config";

interface ProjectTabRailProps {
  projectId: string;
  projectName?: string;
}

export function ProjectTabRail({
  projectId,
  projectName,
}: ProjectTabRailProps) {
  const pathname = usePathname();

  return (
    <div className="space-y-1 pt-2">
      <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/60">
        {projectName || "Project"}
      </div>
      <nav className="space-y-0.5">
        {projectNavItems.map((item) => {
          const href = projectTabHref(projectId, item.segment);
          const isActive = item.segment
            ? pathname === href || pathname?.startsWith(`${href}/`)
            : pathname === href;
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              href={href}
              title={item.description}
              className={cn(
                "group relative flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-sm transition-all",
                isActive
                  ? "bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground/80 hover:bg-muted hover:text-foreground",
              )}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary shadow-glow" />
              )}
              <Icon
                className={cn("size-3.5 shrink-0", isActive && "text-primary")}
              />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";

interface WorkspaceLayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
  header?: React.ReactNode;
  panel?: React.ReactNode;
}

export function WorkspaceLayout({
  children,
  sidebar,
  header,
  panel,
}: WorkspaceLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <div className="flex flex-1 overflow-hidden">
        <WorkspaceSidebar
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed((c) => !c)}
        >
          {sidebar}
        </WorkspaceSidebar>
        <div className="flex flex-1 flex-col overflow-hidden">
          {header}
          <main className="flex-1 overflow-auto p-4 md:p-6">
            <div className="mx-auto max-w-7xl">{children}</div>
          </main>
        </div>
        {panel}
      </div>
    </div>
  );
}

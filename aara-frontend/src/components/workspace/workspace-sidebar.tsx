"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { primaryNavItems } from "@/lib/nav-config";
import { Logo } from "@/components/layout/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { useAuthStore } from "@/stores/auth-store";

interface WorkspaceSidebarProps {
  children?: React.ReactNode;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  className?: string;
}

export function WorkspaceSidebar({
  children,
  collapsed = false,
  onToggleCollapsed,
  className,
}: WorkspaceSidebarProps) {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);

  return (
    <aside
      className={cn(
        "hidden md:flex h-full flex-col border-r bg-sidebar transition-[width] duration-200",
        collapsed ? "w-[68px]" : "w-64",
        className,
      )}
    >
      <div
        className={cn(
          "flex h-16 items-center border-b px-4",
          collapsed ? "justify-center px-2" : "justify-between",
        )}
      >
        <Link href="/research/new">
          <Logo collapsed={collapsed} />
        </Link>
        {!collapsed && onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="size-4" />
          </button>
        )}
      </div>

      <nav className="flex flex-col gap-0.5 px-2 pt-3">
        {primaryNavItems.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                collapsed && "justify-center px-2",
                isActive
                  ? "bg-accent text-accent-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
              )}
              <Icon className="size-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {isActive && !collapsed && (
                <span className="ml-auto size-1.5 rounded-full bg-primary/60" />
              )}
            </Link>
          );
        })}
      </nav>

      {children && (
        <div className="mt-2 flex-1 overflow-y-auto px-2">{children}</div>
      )}
      {!children && <div className="flex-1" />}

      <div className="border-t p-2 space-y-0.5">
        {collapsed && onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="flex w-full items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Expand sidebar"
          >
            <PanelLeftOpen className="size-4" />
          </button>
        )}
        <ThemeToggle collapsed={collapsed} />
        <div
          className={cn(
            "flex items-center gap-2.5 rounded-md px-3 py-2",
            collapsed && "justify-center px-2",
          )}
        >
          <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
            {(user?.display_name || user?.email || "U")[0].toUpperCase()}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">
                {user?.display_name || "Account"}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {user?.email || ""}
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

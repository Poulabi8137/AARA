"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  collapsed?: boolean;
}

// Icon/label visibility is driven by the `.dark` class via CSS (not React
// state) so there's no client-only mounted-gate and no hydration mismatch —
// resolvedTheme is only read inside the click handler, which never runs
// during SSR.
export function ThemeToggle({ collapsed }: ThemeToggleProps) {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
        collapsed && "justify-center px-2",
      )}
    >
      <Moon className="size-4 shrink-0 dark:hidden" />
      <Sun className="hidden size-4 shrink-0 dark:block" />
      {!collapsed && (
        <>
          <span className="dark:hidden">Dark mode</span>
          <span className="hidden dark:inline">Light mode</span>
        </>
      )}
    </button>
  );
}

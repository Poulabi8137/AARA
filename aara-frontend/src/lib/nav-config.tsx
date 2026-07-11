import { Sparkles, LayoutGrid, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

// Redesigned 2026-07-02: research work happens inside a project workspace
// (/projects/[id]/...), not on top-level pages. Settings is account-level.
// See aara-information-architecture memory for that rationale.
//
// Superseded same day (Phase 1 of the landing-experience directive):
// /research/new is now the default post-login destination and primary
// entry point for starting research — "Dashboard" (project list) is
// relabeled "My Research" per that directive's own wording, href unchanged.
export const primaryNavItems: NavItem[] = [
  { label: "New Research", href: "/research/new", icon: Sparkles },
  { label: "My Research", href: "/dashboard", icon: LayoutGrid },
  { label: "Settings", href: "/settings", icon: Settings },
];

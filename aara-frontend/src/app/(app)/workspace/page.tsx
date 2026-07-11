import { redirect } from "next/navigation";

// Retired in the 2026-07-02 IA redesign: workspace is now a scoping
// dimension (header switcher), not a top-level destination. Creating a
// workspace is handled from the Dashboard's empty state instead.
export default function WorkspacePageRedirect() {
  redirect("/dashboard");
}

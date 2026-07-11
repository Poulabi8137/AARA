import { redirect } from "next/navigation";

// Retired in the 2026-07-02 IA redesign: this page's content (overview
// stats, active-research cards, notes, reading queue, saved papers) was
// fragmented at the wrong altitude — it's all project-scoped and now lives
// inside /projects/[id]/* tabs. See aara-information-architecture memory.
// Superseded 2026-07-02 (Phase 1): /research/new is now the primary
// research-entry landing page and default post-login destination.
export default function ResearchPageRedirect() {
  redirect("/research/new");
}

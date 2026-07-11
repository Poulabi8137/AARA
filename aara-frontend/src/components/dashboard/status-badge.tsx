import { cn } from "@/lib/utils";

type Status = "good" | "warning" | "serious" | "critical" | "neutral";

const STATUS_MAP: Record<string, Status> = {
  published: "good",
  active: "good",
  completed: "good",
  running: "warning",
  in_progress: "warning",
  "in-progress": "warning",
  draft: "warning",
  pending: "neutral",
  archived: "neutral",
  failed: "critical",
  error: "critical",
  stale: "serious",
};

const STYLES: Record<Status, string> = {
  good: "bg-aara-good-soft text-[var(--aara-good)]",
  warning: "bg-aara-warning-soft text-[var(--aara-warning)]",
  serious: "bg-aara-serious-soft text-[var(--aara-serious)]",
  critical: "bg-aara-critical-soft text-[var(--aara-critical)]",
  neutral: "bg-muted text-muted-foreground",
};

interface StatusBadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const key = status?.toLowerCase().replace(/\s+/g, "_") ?? "";
  const tone = STATUS_MAP[key] ?? "neutral";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium capitalize",
        STYLES[tone],
        className,
      )}
    >
      <span
        className="size-1.5 shrink-0 rounded-full bg-current"
        aria-hidden="true"
      />
      {label ?? status.replace(/_/g, " ")}
    </span>
  );
}

import { cn } from "@/lib/utils";

interface LogoProps {
  collapsed?: boolean;
  className?: string;
}

export function Logo({ collapsed, className }: LogoProps) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <svg
        viewBox="0 0 32 32"
        className="size-7 shrink-0 text-primary"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M16 2 L29 9 V23 L16 30 L3 23 V9 Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <circle cx="16" cy="16" r="4.5" fill="currentColor" />
        <path
          d="M16 2 V11.5 M29 9 L21 14 M29 23 L21 18 M16 30 V20.5 M3 23 L11 18 M3 9 L11 14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
      {!collapsed && (
        <span className="text-[15px] font-semibold tracking-tight text-foreground">
          AARA
        </span>
      )}
    </div>
  );
}

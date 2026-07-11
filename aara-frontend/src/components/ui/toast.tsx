"use client";

import * as React from "react";
import { useToast } from "@/components/ui/use-toast";

export interface ToastProps {
  id?: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: ToastActionElement;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  variant?: "default" | "destructive";
  duration?: number;
}

export type ToastActionElement = React.ReactElement<{
  altText?: string;
  onClick?: () => void;
  children?: React.ReactNode;
}>;

export interface ToasterProps {
  toasts?: ToastProps[];
}

function Toast({
  title,
  description,
  variant = "default",
  onOpenChange,
  open = true,
}: ToastProps) {
  if (!open) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className={`relative w-full rounded-lg border p-4 shadow-panel ${
        variant === "destructive"
          ? "border-[var(--aara-critical)]/40 bg-aara-critical-soft text-foreground"
          : "border-border bg-card text-foreground"
      }`}
    >
      {title && <div className="pr-5 text-sm font-semibold">{title}</div>}
      {description && (
        <div className="mt-1 pr-5 text-sm text-muted-foreground">
          {description}
        </div>
      )}
      <button
        className="absolute right-2 top-2 rounded p-1 text-xs text-muted-foreground opacity-70 hover:bg-muted hover:opacity-100"
        onClick={() => onOpenChange?.(false)}
        aria-label="Close"
      >
        ✕
      </button>
    </div>
  );
}

export function Toaster() {
  const { toasts } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map(({ id, ...props }) => (
        <div key={id} className="pointer-events-auto">
          <Toast {...props} />
        </div>
      ))}
    </div>
  );
}

Toast.displayName = "Toast";

export { Toast };

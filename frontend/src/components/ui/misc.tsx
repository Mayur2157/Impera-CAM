import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-border bg-surface", className)} {...props} />;
}

type Tone = "info" | "warn" | "break" | "tie";

const toneStyles: Record<Tone, string> = {
  info: "bg-info-bg text-info",
  warn: "bg-warn-bg text-warn",
  break: "bg-break-bg text-break",
  tie: "bg-tie-bg text-tie",
};
const toneIcons = { info: Info, warn: TriangleAlert, break: CircleAlert, tie: CircleCheck };

/** A notice. Errors use role="alert" so screen readers announce them when they appear. */
export function Alert({
  tone = "info",
  title,
  children,
  action,
  className,
}: {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const Icon = toneIcons[tone];
  return (
    <div
      role={tone === "break" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-md px-4 py-3 text-sm", toneStyles[tone], className)}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-text">{children}</div>}
      </div>
      {action}
    </div>
  );
}

export function Progress({ value, label, className }: { value: number; label: string; className?: string }) {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={v}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-surface-2", className)}
    >
      <div
        className="h-full rounded-full bg-primary transition-[width] duration-500"
        style={{ width: `${v}%` }}
      />
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-md bg-surface-2", className)} />;
}

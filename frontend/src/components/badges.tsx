import { CircleCheck, CircleX, Clock, LoaderCircle } from "lucide-react";

import type { Status } from "@/api/types";
import { cn } from "@/lib/cn";

const pill =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap";

const statusLook: Record<Status, { label: string; cls: string; Icon: typeof Clock; spin?: boolean }> = {
  queued: { label: "Queued", cls: "bg-surface-2 text-muted", Icon: Clock },
  running: { label: "Processing", cls: "bg-info-bg text-info", Icon: LoaderCircle, spin: true },
  done: { label: "Done", cls: "bg-tie-bg text-tie", Icon: CircleCheck },
  error: { label: "Failed", cls: "bg-break-bg text-break", Icon: CircleX },
};

export function StatusPill({ status, label }: { status: Status; label?: string }) {
  const { label: text, cls, Icon, spin } = statusLook[status];
  return (
    <span className={cn(pill, cls)}>
      <Icon className={cn("size-3.5", spin && "animate-spin")} aria-hidden />
      {label ?? text}
    </span>
  );
}

/** The balance check: the share of rows whose running balance ties. */
export function ChainBadge({ chain }: { chain: number }) {
  const pct = Math.round(chain * 1000) / 10;
  const ties = chain >= 0.98;
  return (
    <span
      className={cn(pill, ties ? "bg-tie-bg text-tie" : "bg-break-bg text-break")}
      title="Rows whose running balance ties"
    >
      {ties ? <CircleCheck className="size-3.5" aria-hidden /> : <CircleX className="size-3.5" aria-hidden />}
      {pct}% balance check
    </span>
  );
}

// the scorecard's grades (app/analysis/profiler.py), best first
const riskLook: [prefix: string, cls: string][] = [
  ["LOW RISK", "bg-tie-bg text-tie"],
  ["MODERATE-LOW", "bg-info-bg text-info"],
  ["MODERATE", "bg-warn-bg text-warn"],
  ["HIGH", "bg-break-bg text-break"],
  ["VERY HIGH", "bg-break-bg text-break"],
];

export function RiskBadge({ rating }: { rating: string | null | undefined }) {
  if (!rating) return <span className="text-sm text-muted">—</span>;
  const cls =
    riskLook.find(([prefix]) => rating.toUpperCase().startsWith(prefix))?.[1] ?? "bg-surface-2 text-muted";
  return <span className={cn(pill, cls)}>{rating}</span>;
}

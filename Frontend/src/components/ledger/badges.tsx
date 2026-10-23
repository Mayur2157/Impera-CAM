import { cn } from "@/lib/utils";
import { formatINR, maskAccount } from "@/lib/format";
import type { RiskRating, Status } from "@/lib/api/types";
import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

export function Money({ value, paise, className }: { value: number | null | undefined; paise?: boolean | undefined; className?: string }) {
  return <span className={cn("tabular-nums", className)}>{formatINR(value, { paise })}</span>;
}

export function MaskedAccount({ value, className }: { value: string | null | undefined; className?: string }) {
  const m = value?.startsWith("••••") ? value : maskAccount(value);
  return <span className={cn("font-mono tabular-nums", className)} aria-label={`Account ending ${m.slice(-4)}`}>{m}</span>;
}

const pill = "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium tabular-nums whitespace-nowrap";

export function StatusPill({ status }: { status: Status }) {
  const map = {
    queued: { cls: "border-border bg-muted text-muted-foreground", icon: Clock, label: "Queued" },
    running: { cls: "border-primary/30 bg-accent text-primary", icon: Loader2, label: "Running" },
    done: { cls: "border-tie/30 bg-tie-soft text-tie", icon: CheckCircle2, label: "Done" },
    error: { cls: "border-break/30 bg-break-soft text-break", icon: XCircle, label: "Error" },
  }[status];
  const Icon = map.icon;
  return (
    <span className={cn(pill, map.cls)}>
      <Icon className={cn("size-3.5", status === "running" && "animate-spin")} aria-hidden />
      {map.label}
    </span>
  );
}

/** Signature element: % of rows where prev balance − debit + credit = printed balance. */
export function BalanceCheckBadge({ chain, className }: { chain: number; className?: string }) {
  const pct = chain * 100;
  const tone = pct >= 99.995 ? "border-tie/30 bg-tie-soft text-tie" : pct >= 98 ? "border-warn/30 bg-warn-soft text-warn" : "border-break/30 bg-break-soft text-break";
  const label = pct >= 99.995 ? "100%" : `${pct.toFixed(2)}%`;
  return (
    <span className={cn(pill, tone, className)} title="Share of rows where previous balance − debit + credit equals the printed balance">
      <span aria-hidden className="font-mono">Σ</span> Balance check {label}
    </span>
  );
}

export function riskTone(r: RiskRating) {
  if (r === "PRIME" || r === "MODERATE-LOW") return "tie";
  if (r === "MODERATE") return "warn";
  return "break";
}

export function RiskGradeBadge({ rating }: { rating: RiskRating }) {
  const t = riskTone(rating);
  const cls = t === "tie" ? "border-tie/30 bg-tie-soft text-tie" : t === "warn" ? "border-warn/30 bg-warn-soft text-warn" : "border-break/30 bg-break-soft text-break";
  return <span className={cn(pill, cls, "uppercase tracking-wide")}>{rating}</span>;
}

export function ScoreGauge({ value, rating, size = 160 }: { value: number; rating?: RiskRating; size?: number }) {
  const r = 70, c = Math.PI * r;
  const pct = Math.max(0, Math.min(100, value)) / 100;
  const t = rating ? riskTone(rating) : "tie";
  const stroke = t === "tie" ? "stroke-tie" : t === "warn" ? "stroke-warn" : "stroke-break";
  return (
    <div className="inline-flex flex-col items-center" role="img" aria-label={`Credit score index ${value} out of 100`}>
      <svg width={size} height={size * 0.6} viewBox="0 0 160 96">
        <path d="M10 86 A70 70 0 0 1 150 86" fill="none" className="stroke-muted" strokeWidth="12" strokeLinecap="round" />
        <path d="M10 86 A70 70 0 0 1 150 86" fill="none" className={cn(stroke, "transition-[stroke-dashoffset] duration-700")} strokeWidth="12" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
        <text x="80" y="78" textAnchor="middle" className="fill-foreground font-serif text-[32px] font-semibold tabular-nums">{value}</text>
        <text x="80" y="94" textAnchor="middle" className="fill-muted-foreground text-[10px]">of 100</text>
      </svg>
    </div>
  );
}

export function TenantStatus({ status }: { status: "active" | "suspended" }) {
  return status === "active"
    ? <span className="inline-flex rounded-full border px-2 py-0.5 text-xs">Active</span>
    : <span className="inline-flex rounded-full border border-break/40 px-2 py-0.5 text-xs text-break">Suspended</span>;
}

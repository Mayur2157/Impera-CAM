const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-IN");
const day = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" });
const dayTime = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const DASH = "—";

/** ₹ with Indian digit grouping: 12,34,567.80 */
export function formatINR(v: number | null | undefined): string {
  return v === null || v === undefined || Number.isNaN(v) ? DASH : inr.format(v);
}

export function formatNumber(v: number | null | undefined): string {
  return v === null || v === undefined || Number.isNaN(v) ? DASH : num.format(v);
}

export function formatPct(v: number | null | undefined, digits = 1): string {
  return v === null || v === undefined || Number.isNaN(v) ? DASH : `${v.toFixed(digits)}%`;
}

/** The API sends naive UTC timestamps ("2026-10-23T09:15:00"); read them as UTC. */
export function parseApiDate(s: string | null | undefined): Date | null {
  if (!s) return null;
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) || s.length <= 10 ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(s: string | null | undefined): string {
  const d = parseApiDate(s);
  return d ? day.format(d) : DASH;
}

export function formatDateTime(s: string | null | undefined): string {
  const d = parseApiDate(s);
  return d ? dayTime.format(d) : DASH;
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${formatNumber(n)} ${n === 1 ? one : many}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

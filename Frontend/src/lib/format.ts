const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const inrPaise = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-IN");

export function formatINR(v: number | null | undefined, opts?: { paise?: boolean | undefined }) {
  if (v == null || Number.isNaN(v)) return "—";
  return (opts?.paise ? inrPaise : inr).format(v);
}

export function formatNumber(v: number | null | undefined) {
  if (v == null) return "—";
  return num.format(v);
}

export function formatPct(v: number | null | undefined, digits = 1) {
  if (v == null) return "—";
  return `${v.toFixed(digits)}%`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** dd MMM yyyy in the user's local zone */
export function formatDate(v: string | Date | null | undefined) {
  if (!v) return "—";
  const d = typeof v === "string" ? new Date(v) : v;
  if (Number.isNaN(d.getTime())) return "—";
  return `${String(d.getDate()).padStart(2, "0")} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function formatDateTime(v: string | Date | null | undefined) {
  if (!v) return "—";
  const d = typeof v === "string" ? new Date(v) : v;
  return `${formatDate(d)}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function formatRelative(v: string | null | undefined) {
  if (!v) return "Never";
  const diff = Date.now() - new Date(v).getTime();
  const m = Math.round(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.round(h / 24);
  if (d < 30) return `${d} d ago`;
  return formatDate(v);
}

export function maskAccount(v: string | null | undefined) {
  if (!v) return "—";
  const digits = v.replace(/[^0-9A-Za-z]/g, "");
  return `••••${digits.slice(-4)}`;
}

export function maskPAN(v: string | null | undefined) {
  if (!v || v.length !== 10) return "—";
  return `${v.slice(0, 5)}••••${v.slice(9)}`;
}

export function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

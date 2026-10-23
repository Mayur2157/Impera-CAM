import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, ErrorState } from "@/components/ledger/states";
import { api } from "@/lib/api/client";
import type { AdminOverview } from "@/lib/api/types";
import { formatNumber, formatDateTime } from "@/lib/format";

export const Route = createFileRoute("/admin/")({
  head: () => ({ meta: [{ title: "Overview — Impera staff console" }, { name: "description", content: "Platform-wide tenants, volume, queues and workers." }] }),
  component: Overview,
});

function Overview() {
  const q = useQuery({ queryKey: ["admin", "overview"], queryFn: () => api<AdminOverview>("/api/v1/admin/overview"), refetchInterval: 15_000 });
  if (q.isLoading) return <><PageHeader title="Overview" /><Skeleton className="h-64" /></>;
  if (q.error || !q.data) return <><PageHeader title="Overview" /><ErrorState error={q.error} onRetry={() => q.refetch()} /></>;
  const o = q.data;
  const ocrDown = o.workers.ocr === 0 && o.queue.ocr > 0;
  const tiles: [string, string][] = [
    ["Tenants", formatNumber(o.tenants)], ["Active in 30 days", formatNumber(o.active_tenants_30d)],
    ["Statements · 30 days", formatNumber(o.statements_30d)], ["Pages · 30 days", formatNumber(o.pages_30d)],
    ["Queue · CPU", formatNumber(o.queue.cpu)], ["Queue · OCR", formatNumber(o.queue.ocr)],
    ["Workers online", `${formatNumber(o.workers.cpu)} CPU · ${formatNumber(o.workers.ocr)} OCR`], ["OCR device", o.ocr_device],
  ];
  return (
    <>
      <PageHeader title="Overview" description={<>Refreshes every 15 seconds · last update {formatDateTime(new Date(q.dataUpdatedAt))}</>} />
      {ocrDown && (
        <div role="alert" className="mb-6 flex gap-2 rounded-lg border border-break/40 bg-break-soft p-4 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-break" aria-hidden />
          <span><strong>No OCR workers online</strong> while {formatNumber(o.queue.ocr)} scanned statements are waiting. Start an OCR worker.</span>
        </div>
      )}
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map(([k, v]) => (
          <div key={k} className="rounded-lg border bg-card p-5">
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">{k}</dt>
            <dd className={`mt-2 font-semibold tabular-nums ${k === "OCR device" ? "font-mono text-lg" : "font-serif text-2xl"}`}>{v}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}

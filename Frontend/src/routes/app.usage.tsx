import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { PageHeader, ErrorState, EmptyState } from "@/components/ledger/states";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { useUsage, type UsageParams } from "@/lib/api/hooks";
import type { Usage } from "@/lib/api/types";
import { formatDate, formatNumber } from "@/lib/format";

export const Route = createFileRoute("/app/usage")({
  head: () => ({ meta: [{ title: "Usage — Impera CAM" }, { name: "description", content: "Statements and pages processed, by day, API key or user." }] }),
  component: UsagePage,
});

const iso = (d: Date) => d.toISOString().slice(0, 10);
const daysAgo = (n: number) => iso(new Date(Date.now() - n * 86400000));
type Row = Usage["series"][number];
const GROUPS: { id: UsageParams["group_by"]; label: string }[] = [{ id: "day", label: "Day" }, { id: "api_key", label: "API key" }, { id: "user", label: "User" }];

function UsagePage() {
  const [from, setFrom] = useState(daysAgo(29));
  const [to, setTo] = useState(iso(new Date()));
  const [preset, setPreset] = useState<string>("30");
  const [group, setGroup] = useState<UsageParams["group_by"]>("day");
  const usage = useUsage({ from, to, group_by: group });

  function applyPreset(v: string) { if (!v) return; setPreset(v); setFrom(daysAgo(Number(v) - 1)); setTo(iso(new Date())); }
  const label = (r: Row) => (group === "day" ? formatDate(r.label) : r.label);

  function exportCsv() {
    if (!usage.data) return;
    const esc = (s: string) => `"${s.replace(/"/g, '""')}"`;
    const head = [group === "day" ? "date" : group, "statements", "pages"].join(",");
    const lines = usage.data.series.map((r) => [esc(r.label), r.statements, r.pages].join(","));
    const blob = new Blob([[head, ...lines].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `usage_${from}_${to}_${group}.csv`; a.click();
    URL.revokeObjectURL(a.href);
  }

  const columns: Column<Row>[] = [
    { key: "label", header: group === "day" ? "Date" : group === "api_key" ? "API key" : "User", cell: label, sortValue: (r) => r.key },
    { key: "s", header: "Statements", align: "right", cell: (r) => formatNumber(r.statements), sortValue: (r) => r.statements },
    { key: "p", header: "Pages", align: "right", cell: (r) => formatNumber(r.pages), sortValue: (r) => r.pages },
  ];

  return (
    <>
      <PageHeader title="Usage" description="Statements and pages processed by your organisation." actions={<Button variant="outline" onClick={exportCsv} disabled={!usage.data?.series.length}><Download className="size-4" aria-hidden /> Export CSV</Button>} />

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div className="space-y-1.5">
          <span className="text-sm font-medium" id="preset-l">Range</span>
          <ToggleGroup type="single" variant="outline" value={preset} onValueChange={applyPreset} aria-labelledby="preset-l">
            {["7", "30", "90"].map((d) => <ToggleGroupItem key={d} value={d}>{d} days</ToggleGroupItem>)}
          </ToggleGroup>
        </div>
        <div className="space-y-1.5"><Label htmlFor="u-from">From</Label><Input id="u-from" type="date" value={from} max={to} onChange={(e) => { setFrom(e.target.value); setPreset(""); }} className="w-40" /></div>
        <div className="space-y-1.5"><Label htmlFor="u-to">To</Label><Input id="u-to" type="date" value={to} min={from} max={iso(new Date())} onChange={(e) => { setTo(e.target.value); setPreset(""); }} className="w-40" /></div>
        <div className="space-y-1.5">
          <span className="text-sm font-medium" id="group-l">Group by</span>
          <ToggleGroup type="single" variant="outline" value={group} onValueChange={(v) => v && setGroup(v as UsageParams["group_by"])} aria-labelledby="group-l">
            {GROUPS.map((g) => <ToggleGroupItem key={g.id} value={g.id}>{g.label}</ToggleGroupItem>)}
          </ToggleGroup>
        </div>
      </div>

      {usage.isLoading ? <Skeleton className="h-80" /> : usage.error ? <ErrorState error={usage.error} onRetry={() => usage.refetch()} /> : usage.data && (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="min-w-0 space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <Tile label="Statements" value={usage.data.totals.statements} />
              <Tile label="Pages" value={usage.data.totals.pages} />
            </div>
            {!usage.data.series.length ? <EmptyState title="No usage in this range" description="Pick a wider range or upload a statement." /> : (
              <>
                <figure className="rounded-lg border bg-card p-4" aria-label="Usage chart">
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={usage.data.series.map((r) => ({ ...r, name: label(r) }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} minTickGap={16} />
                        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={48} />
                        <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => formatNumber(v)} />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                        <Bar dataKey="statements" name="Statements" stackId="a" fill="var(--primary)" />
                        <Bar dataKey="pages" name="Pages" stackId="a" fill="var(--muted-foreground)" fillOpacity={0.45} radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </figure>
                <DataTable caption="Usage" columns={columns} rows={usage.data.series} rowKey={(r) => r.key} pageSize={31} />
              </>
            )}
          </div>
          <aside className="h-fit rounded-lg border bg-card p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Your plan</p>
            <p className="mt-1 font-serif text-2xl font-semibold">{usage.data.plan.name}</p>
            <dl className="mt-4 space-y-2 text-sm">
              <Row k="Monthly statements" v={usage.data.plan.monthly_statement_quota == null ? "Unlimited" : formatNumber(usage.data.plan.monthly_statement_quota)} />
              <Row k="Files per job" v={formatNumber(usage.data.plan.max_files_per_job)} />
              <Row k="Max file size" v={`${formatNumber(usage.data.plan.max_upload_mb)} MB`} />
            </dl>
            <Button asChild variant="outline" className="mt-5 w-full"><a href="mailto:sales@impera.example?subject=Change%20plan">Contact us to change plan</a></Button>
          </aside>
        </div>
      )}
    </>
  );
}

function Tile({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border bg-card p-4"><p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-1 font-serif text-2xl font-semibold tabular-nums">{formatNumber(value)}</p></div>;
}
function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between gap-3"><dt className="text-muted-foreground">{k}</dt><dd className="tabular-nums">{v}</dd></div>;
}

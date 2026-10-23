import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, ErrorState } from "@/components/ledger/states";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { ConfirmDialog } from "@/components/ledger/actions";
import { FieldError } from "@/components/ledger/auth-layout";
import { useAdminRevokeKey, useAdminTenant, useUpdateAdminTenant } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import type { AdminTenantDetail, ApiKey, Member } from "@/lib/api/types";
import { formatDate, formatNumber, formatRelative } from "@/lib/format";
import { TenantStatus } from "@/components/ledger/badges";

export const Route = createFileRoute("/admin/tenants/$id")({
  head: () => ({ meta: [{ title: "Tenant — Impera staff console" }, { name: "description", content: "Tenant profile, members, usage, keys and limits." }] }),
  component: TenantPage,
});

function TenantPage() {
  const { id } = Route.useParams();
  const t = useAdminTenant(id);
  const update = useUpdateAdminTenant();
  const revoke = useAdminRevokeKey();
  const [statusOpen, setStatusOpen] = useState(false);
  const [revoking, setRevoking] = useState<ApiKey | null>(null);
  const back = <Button asChild variant="outline"><Link to="/admin/tenants"><ArrowLeft className="size-4" aria-hidden /> All tenants</Link></Button>;

  if (t.isLoading) return <><PageHeader title="Tenant" actions={back} /><Skeleton className="h-96" /></>;
  if (t.error || !t.data) return <><PageHeader title="Tenant" actions={back} /><ErrorState error={t.error} onRetry={() => t.refetch()} /></>;
  const d = t.data;
  const suspended = d.status === "suspended";

  const mcols: Column<Member>[] = [
    { key: "e", header: "Email", cell: (m) => m.email },
    { key: "r", header: "Role", cell: (m) => <span className="capitalize">{m.role}</span> },
    { key: "a", header: "Active", cell: (m) => (m.is_active ? "Yes" : "No") },
    { key: "l", header: "Last login", cell: (m) => formatRelative(m.last_login_at) },
  ];
  const kcols: Column<ApiKey>[] = [
    { key: "n", header: "Name", cell: (k) => k.name },
    { key: "p", header: "Key", cell: (k) => <span className="font-mono text-xs">{k.prefix}…</span> },
    { key: "s", header: "Scopes", cell: (k) => <div className="flex gap-1">{k.scopes.map((s) => <Badge key={s} variant="secondary" className="font-mono text-[11px] font-normal">{s}</Badge>)}</div> },
    { key: "u", header: "Last used", cell: (k) => formatRelative(k.last_used_at) },
    { key: "q", header: "Requests (30 d)", align: "right", cell: (k) => formatNumber(k.requests_30d) },
    { key: "x", header: "", align: "right", cell: (k) => k.revoked_at ? <span className="text-xs text-muted-foreground">Revoked</span> : <Button variant="ghost" size="sm" className="text-break hover:text-break" onClick={() => setRevoking(k)}>Revoke</Button> },
  ];

  return (
    <>
      <PageHeader title={d.name} description={<span className="flex flex-wrap items-center gap-2"><TenantStatus status={d.status} /> {d.plan} · {formatNumber(d.users)} users · created {formatDate(d.created_at)} · <span className="font-mono">{d.id}</span></span>}
        actions={<>{back}<Button variant={suspended ? "default" : "outline"} className={suspended ? undefined : "border-break/40 text-break hover:text-break"} onClick={() => setStatusOpen(true)}>{suspended ? "Reactivate" : "Suspend"}</Button></>} />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0 space-y-8">
          <section aria-labelledby="u30">
            <h2 id="u30" className="mb-3 font-serif text-xl font-semibold">Usage · 30 days</h2>
            <div className="h-60 rounded-lg border bg-card p-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={d.usage.map((r) => ({ ...r, name: formatDate(r.label).slice(0, 6) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} minTickGap={16} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={40} />
                  <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => formatNumber(v)} />
                  <Bar dataKey="statements" name="Statements" fill="var(--primary)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section aria-labelledby="mem"><h2 id="mem" className="mb-3 font-serif text-xl font-semibold">Members</h2>
            <DataTable caption="Members" columns={mcols} rows={d.members} rowKey={(m) => m.id} empty={<p className="p-6 text-center text-sm text-muted-foreground">No members listed.</p>} /></section>
          <section aria-labelledby="keys"><h2 id="keys" className="mb-3 font-serif text-xl font-semibold">API keys</h2>
            <DataTable caption="API keys" columns={kcols} rows={d.api_keys} rowKey={(k) => k.id} empty={<p className="p-6 text-center text-sm text-muted-foreground">No API keys.</p>} /></section>
        </div>
        <LimitsForm d={d} onSave={(b) => update.mutateAsync({ id: d.id, ...b })} />
      </div>

      <ConfirmDialog open={statusOpen} onOpenChange={setStatusOpen} destructive={!suspended}
        title={suspended ? `Reactivate ${d.name}?` : `Suspend ${d.name}?`}
        description={suspended ? "Users regain full access and API keys work again straight away." : "All users become read-only — they can't upload. Every API key is rejected until you reactivate. Existing results stay available."}
        confirmLabel={suspended ? "Reactivate" : "Suspend"} typeToConfirm={suspended ? undefined : d.name}
        onConfirm={async () => {
          try { await update.mutateAsync({ id: d.id, status: suspended ? "active" : "suspended" }); toast.success(suspended ? "Tenant reactivated" : "Tenant suspended"); }
          catch (e) { toast.error(errorMessage(e)); throw e; }
        }} />
      <ConfirmDialog open={!!revoking} onOpenChange={(o) => { if (!o) setRevoking(null); }} destructive title="Revoke this API key?" description={<>“{revoking?.name}” stops working immediately for this customer.</>} confirmLabel="Revoke key"
        onConfirm={async () => { if (!revoking) return; try { await revoke.mutateAsync(revoking.id); toast.success("API key revoked"); } catch (e) { toast.error(errorMessage(e)); throw e; } }} />
    </>
  );
}

function LimitsForm({ d, onSave }: { d: AdminTenantDetail; onSave: (b: { plan: string; max_files: number; max_upload_mb: number; monthly_statement_quota: number | null }) => Promise<unknown> }) {
  const init = () => ({ plan: d.plan, files: String(d.max_files), mb: String(d.max_upload_mb), quota: d.monthly_statement_quota == null ? "" : String(d.monthly_statement_quota) });
  const [f, setF] = useState(init);
  const [err, setErr] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  useEffect(() => setF(init()), [d.id, d.plan, d.max_files, d.max_upload_mb, d.monthly_statement_quota]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const files = Number(f.files), mb = Number(f.mb), quota = f.quota.trim() === "" ? null : Number(f.quota);
    if (!f.plan.trim()) return setErr("Plan name is required.");
    if (!Number.isInteger(files) || files < 1) return setErr("Files per job must be a whole number of at least 1.");
    if (!Number.isInteger(mb) || mb < 1) return setErr("Max MB must be a whole number of at least 1.");
    if (quota !== null && (!Number.isInteger(quota) || quota < 0)) return setErr("Monthly quota must be a whole number, or blank for unlimited.");
    setErr(undefined); setBusy(true);
    try { await onSave({ plan: f.plan.trim(), max_files: files, max_upload_mb: mb, monthly_statement_quota: quota }); toast.success("Plan & limits saved"); }
    catch (e2) { toast.error(errorMessage(e2)); }
    finally { setBusy(false); }
  }
  const field = (id: keyof typeof f, label: string, type = "number", hint?: string) => (
    <div className="space-y-1.5">
      <Label htmlFor={`lim-${id}`}>{label}</Label>
      <Input id={`lim-${id}`} type={type} min={type === "number" ? 0 : undefined} value={f[id]} onChange={(e) => setF({ ...f, [id]: e.target.value })} aria-describedby="lim-err" />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
  return (
    <form method="post" onSubmit={submit} noValidate className="h-fit space-y-4 rounded-lg border bg-card p-5" aria-labelledby="lim-h">
      <h2 id="lim-h" className="text-base font-semibold">Edit plan & limits</h2>
      {field("plan", "Plan", "text")}
      {field("files", "Max files per job")}
      {field("mb", "Max MB per file")}
      {field("quota", "Monthly statement quota", "number", "Leave blank for unlimited.")}
      <FieldError id="lim-err" message={err} />
      <Button type="submit" disabled={busy} className="w-full">{busy ? "Saving…" : "Save changes"}</Button>
    </form>
  );
}

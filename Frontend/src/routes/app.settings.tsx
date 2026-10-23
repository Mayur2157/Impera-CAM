import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Clock } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, ErrorState } from "@/components/ledger/states";
import { FieldError } from "@/components/ledger/auth-layout";
import { ChangePasswordDialog } from "@/components/ledger/change-password";
import { useOrg, useUpdateOrg } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/format";

export const Route = createFileRoute("/app/settings")({
  head: () => ({ meta: [{ title: "Settings — Impera CAM" }, { name: "description", content: "Organisation, plan, data retention and your profile." }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const { me, isAdmin } = useAuth();
  const org = useOrg();
  const save = useUpdateOrg();
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | undefined>();
  const [pw, setPw] = useState(false);
  useEffect(() => { if (org.data) setName(org.data.name); }, [org.data]);

  if (org.isLoading) return <><PageHeader title="Settings" /><Skeleton className="h-96" /></>;
  if (org.error || !org.data) return <><PageHeader title="Settings" /><ErrorState error={org.error} onRetry={() => org.refetch()} /></>;
  const o = org.data;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setErr("Organisation name can't be empty."); return; }
    setErr(undefined);
    try { await save.mutateAsync({ name: name.trim() }); toast.success("Organisation name saved"); } catch (e) { setErr(errorMessage(e)); }
  }

  return (
    <>
      <PageHeader title="Settings" />
      <div className="max-w-3xl space-y-6">
        <Card title="Organisation">
          <form method="post" onSubmit={submit} className="space-y-3" noValidate>
            <Label htmlFor="org-name">Organisation name</Label>
            <div className="flex flex-wrap gap-2">
              <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} disabled={!isAdmin} className="max-w-sm" maxLength={120} aria-describedby="org-err" />
              {isAdmin && <Button type="submit" disabled={save.isPending || name.trim() === o.name}>{save.isPending ? "Saving…" : "Save"}</Button>}
            </div>
            <FieldError id="org-err" message={err} />
            {!isAdmin && <p className="text-xs text-muted-foreground">Only owners and admins can change this.</p>}
            <p className="text-xs text-muted-foreground">Created {formatDate(o.created_at)}</p>
          </form>
        </Card>

        <Card title="Plan & limits">
          <dl className="grid gap-3 sm:grid-cols-3">
            {[["Plan", o.plan], ["Files per job", formatNumber(o.max_files)], ["Max file size", `${formatNumber(o.max_upload_mb)} MB`]].map(([k, v]) => (
              <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="mt-0.5 font-medium tabular-nums">{v}</dd></div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-muted-foreground">To change plan, contact <a className="underline" href="mailto:sales@impera.example">sales@impera.example</a>.</p>
        </Card>

        <div role="note" className="flex gap-3 rounded-lg border bg-card p-5 text-sm">
          <Clock className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
          <div><p className="font-medium">Data retention</p><p className="mt-0.5 text-muted-foreground">Uploads and workbooks are deleted after {formatNumber(o.retention_hours)} hours.</p></div>
        </div>

        <Card title="Your profile">
          {me && (
            <dl className="grid gap-3 sm:grid-cols-2">
              <div><dt className="text-xs text-muted-foreground">Email</dt><dd className="mt-0.5">{me.email}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Role</dt><dd className="mt-0.5 capitalize">{me.role}</dd></div>
            </dl>
          )}
          <Button variant="outline" className="mt-4" onClick={() => setPw(true)}>Change password</Button>
        </Card>

        <section aria-labelledby="danger" className="rounded-lg border border-break/40 p-5">
          <h2 id="danger" className="text-base font-semibold text-break">Danger zone</h2>
          <p className="mt-1 text-sm"><strong>Delete organisation</strong> — contact support to delete your organisation and all its data.</p>
        </section>
      </div>
      <ChangePasswordDialog open={pw} onOpenChange={setPw} />
    </>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border bg-card p-5" aria-label={title}><h2 className="mb-4 text-base font-semibold">{title}</h2>{children}</section>;
}

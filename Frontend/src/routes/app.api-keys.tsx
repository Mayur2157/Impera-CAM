import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, KeyRound, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PageHeader, EmptyState, ErrorState } from "@/components/ledger/states";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { ConfirmDialog, CopyButton } from "@/components/ledger/actions";
import { FieldError } from "@/components/ledger/auth-layout";
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import type { ApiKey, Scope } from "@/lib/api/types";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber, formatRelative } from "@/lib/format";

export const Route = createFileRoute("/app/api-keys")({
  head: () => ({ meta: [{ title: "API keys — Impera CAM" }, { name: "description", content: "Create and revoke API keys for the Impera CAM REST API." }] }),
  component: ApiKeysPage,
});

const SCOPES: { id: Scope; label: string; hint: string }[] = [
  { id: "jobs:write", label: "jobs:write", hint: "Upload statements" },
  { id: "jobs:read", label: "jobs:read", hint: "Read job status and results" },
];

function ApiKeysPage() {
  const { me, isAdmin } = useAuth();
  const keys = useApiKeys(isAdmin);
  const [createOpen, setCreateOpen] = useState(false);
  const [secret, setSecret] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<ApiKey | null>(null);
  const revoke = useRevokeApiKey();

  const header = (
    <PageHeader
      title="API keys"
      description="Keys let your own loan systems call the Impera CAM API directly — upload statements and read results without signing in."
      actions={isAdmin ? <Button onClick={() => setCreateOpen(true)}><Plus className="size-4" aria-hidden /> Create API key</Button> : undefined}
    />
  );

  if (me && !isAdmin) {
    return (
      <>
        {header}
        <EmptyState
          icon={<KeyRound className="size-6" aria-hidden />}
          title="Only owners and admins manage API keys"
          description="API keys give your organisation's servers access to statements and results. Ask an owner or admin to create one for you."
          action={<Button asChild variant="outline"><Link to="/app/docs">Read the API docs</Link></Button>}
        />
      </>
    );
  }

  const columns: Column<ApiKey>[] = [
    { key: "name", header: "Name", cell: (k) => <span className="font-medium">{k.name}</span>, sortValue: (k) => k.name.toLowerCase() },
    { key: "prefix", header: "Key", cell: (k) => <span className="font-mono text-xs">{k.prefix}…</span> },
    { key: "scopes", header: "Scopes", cell: (k) => <div className="flex flex-wrap gap-1">{k.scopes.map((s) => <Badge key={s} variant="secondary" className="font-mono text-[11px] font-normal">{s}</Badge>)}</div> },
    { key: "created", header: "Created", cell: (k) => <div className="text-sm"><div>{formatDate(k.created_at)}</div><div className="text-xs text-muted-foreground">{k.created_by}</div></div>, sortValue: (k) => k.created_at },
    { key: "used", header: "Last used", cell: (k) => <span className="text-sm">{formatRelative(k.last_used_at)}</span>, sortValue: (k) => k.last_used_at },
    { key: "req", header: "Requests (30 d)", align: "right", cell: (k) => formatNumber(k.requests_30d), sortValue: (k) => k.requests_30d },
    { key: "status", header: "Status", cell: (k) => k.revoked_at
      ? <Badge variant="outline" className="text-muted-foreground">Revoked {formatDate(k.revoked_at)}</Badge>
      : <Badge variant="outline">Active</Badge> },
    { key: "act", header: "", align: "right", cell: (k) => k.revoked_at ? null : (
      <Button variant="ghost" size="sm" className="text-break hover:text-break" onClick={() => setRevoking(k)}>Revoke</Button>
    ) },
  ];

  return (
    <>
      {header}
      {keys.error ? <ErrorState error={keys.error} onRetry={() => keys.refetch()} /> : keys.data && keys.data.length === 0 ? (
        <EmptyState
          icon={<KeyRound className="size-6" aria-hidden />}
          title="No API keys yet"
          description="Create a key to let your loan origination system upload statements and fetch CAM results over the REST API. Keep keys on your servers only."
          action={<Button onClick={() => setCreateOpen(true)}><Plus className="size-4" aria-hidden /> Create API key</Button>}
        />
      ) : (
        <DataTable caption="API keys" columns={columns} rows={keys.data} rowKey={(k) => k.id} loading={keys.isLoading} rowClassName={(k) => (k.revoked_at ? "opacity-60" : undefined)} />
      )}

      <CreateKeyDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={(s) => { setCreateOpen(false); setSecret(s); }} />
      <SecretDialog secret={secret} onClose={() => setSecret(null)} />
      <ConfirmDialog
        open={!!revoking}
        onOpenChange={(o) => { if (!o) setRevoking(null); }}
        title="Revoke this API key?"
        description="Any system using it will stop working immediately. This can't be undone."
        confirmLabel="Revoke key"
        destructive
        typeToConfirm={revoking?.name}
        onConfirm={async () => {
          if (!revoking) return;
          try { await revoke.mutateAsync(revoking.id); toast.success("API key revoked"); }
          catch (e) { toast.error(errorMessage(e)); throw e; }
        }}
      />
    </>
  );
}

function CreateKeyDialog({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (o: boolean) => void; onCreated: (secret: string) => void }) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Scope[]>(["jobs:read", "jobs:write"]);
  const [err, setErr] = useState<string | undefined>();
  const create = useCreateApiKey();

  function reset() { setName(""); setScopes(["jobs:read", "jobs:write"]); setErr(undefined); create.reset(); }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setErr("Give the key a name, e.g. the system that will use it."); return; }
    if (!scopes.length) { setErr("Pick at least one scope."); return; }
    try {
      const r = await create.mutateAsync({ name: name.trim(), scopes });
      reset();
      onCreated(r.secret);
    } catch (e) { setErr(errorMessage(e)); }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent>
        <form method="post" onSubmit={submit} className="space-y-5" noValidate>
          <DialogHeader>
            <DialogTitle>Create API key</DialogTitle>
            <DialogDescription>Name it after the system that will use it, so you know what breaks if you revoke it.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="key-name">Name</Label>
            <Input id="key-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="LOS production" maxLength={60} aria-invalid={!!err && !name.trim()} aria-describedby="key-err" autoFocus />
          </div>
          <fieldset className="space-y-3">
            <legend className="mb-2 text-sm font-medium">Scopes</legend>
            {SCOPES.map((s) => (
              <div key={s.id} className="flex items-start gap-3">
                <Checkbox id={`scope-${s.id}`} checked={scopes.includes(s.id)} onCheckedChange={(c) => setScopes((p) => (c ? [...p, s.id] : p.filter((x) => x !== s.id)))} />
                <Label htmlFor={`scope-${s.id}`} className="flex flex-col items-start gap-0.5 font-normal">
                  <span className="font-mono text-sm">{s.label}</span>
                  <span className="text-xs text-muted-foreground">{s.hint}</span>
                </Label>
              </div>
            ))}
          </fieldset>
          <FieldError id="key-err" message={err} />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>{create.isPending ? "Creating…" : "Create key"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SecretDialog({ secret, onClose }: { secret: string | null; onClose: () => void }) {
  const [ack, setAck] = useState(false);
  const close = () => { setAck(false); onClose(); };
  return (
    <Dialog open={!!secret} onOpenChange={(o) => { if (!o && ack) close(); }}>
      <DialogContent
        onEscapeKeyDown={(e) => { if (!ack) e.preventDefault(); }}
        onPointerDownOutside={(e) => { if (!ack) e.preventDefault(); }}
        onInteractOutside={(e) => { if (!ack) e.preventDefault(); }}
      >
        <DialogHeader>
          <DialogTitle>Your new API key</DialogTitle>
          <DialogDescription>Send it in the <span className="font-mono">X-API-Key</span> header from your servers.</DialogDescription>
        </DialogHeader>
        <div role="alert" className="flex gap-2 rounded-md border border-warn/40 bg-warn-soft p-3 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
          <span><strong>Store it now — you won't see it again.</strong> We only keep a fingerprint, so we can't show it later.</span>
        </div>
        <div className="flex gap-2">
          <Input readOnly value={secret ?? ""} aria-label="API key secret" className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
          <CopyButton value={secret ?? ""} />
        </div>
        <div className="flex items-center gap-2">
          <Checkbox id="ack-copied" checked={ack} onCheckedChange={(c) => setAck(c === true)} />
          <Label htmlFor="ack-copied" className="font-normal">I've copied it somewhere safe</Label>
        </div>
        <DialogFooter>
          <Button onClick={close} disabled={!ack}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

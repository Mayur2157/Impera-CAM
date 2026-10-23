import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Lock, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PageHeader, EmptyState, ErrorState } from "@/components/ledger/states";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { ConfirmDialog, CopyButton } from "@/components/ledger/actions";
import { FieldError } from "@/components/ledger/auth-layout";
import { useCreateInvite, useDeleteInvite, useInvites, useMembers, useRemoveMember, useUpdateMember } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import type { CreatedInvite, Invite, Member, Role } from "@/lib/api/types";
import { useAuth } from "@/lib/auth";
import { formatDate, formatRelative } from "@/lib/format";

export const Route = createFileRoute("/app/team")({
  head: () => ({ meta: [{ title: "Team — Impera CAM" }, { name: "description", content: "Manage members and invites for your organisation." }] }),
  component: TeamPage,
});

function TeamPage() {
  const { me, isAdmin } = useAuth();
  const members = useMembers();
  const invites = useInvites(isAdmin);
  const update = useUpdateMember();
  const remove = useRemoveMember();
  const delInvite = useDeleteInvite();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [created, setCreated] = useState<CreatedInvite | null>(null);
  const [removing, setRemoving] = useState<Member | null>(null);
  const [revoking, setRevoking] = useState<Invite | null>(null);

  if (me && !isAdmin) {
    return <><PageHeader title="Team" /><EmptyState icon={<Users className="size-6" aria-hidden />} title="Only owners and admins manage the team" description="Ask an owner or admin of your organisation to invite people or change roles." /></>;
  }

  const patch = (id: string, b: { role?: Role; is_active?: boolean }) =>
    update.mutate({ id, ...b }, { onSuccess: () => toast.success("Member updated"), onError: (e) => toast.error(errorMessage(e)) });

  const cols: Column<Member>[] = [
    { key: "email", header: "Email", cell: (m) => <span className="font-medium">{m.email}{m.id === me?.id && <span className="ml-2 text-xs text-muted-foreground">(you)</span>}</span>, sortValue: (m) => m.email },
    { key: "role", header: "Role", cell: (m) => m.role === "owner" ? (
      <span className="inline-flex items-center gap-1.5 text-sm"><Lock className="size-3.5 text-muted-foreground" aria-hidden />Owner</span>
    ) : (
      <Select value={m.role} onValueChange={(v) => patch(m.id, { role: v as Role })} disabled={m.id === me?.id}>
        <SelectTrigger className="h-8 w-28" aria-label={`Role for ${m.email}`}><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="admin">Admin</SelectItem><SelectItem value="member">Member</SelectItem></SelectContent>
      </Select>
    ) },
    { key: "active", header: "Active", cell: (m) => <Switch checked={m.is_active} disabled={m.role === "owner" || m.id === me?.id} onCheckedChange={(c) => patch(m.id, { is_active: c })} aria-label={`${m.email} active`} /> },
    { key: "login", header: "Last login", cell: (m) => formatRelative(m.last_login_at), sortValue: (m) => m.last_login_at },
    { key: "joined", header: "Joined", cell: (m) => formatDate(m.created_at), sortValue: (m) => m.created_at },
    { key: "x", header: "", align: "right", cell: (m) => m.role === "owner" || m.id === me?.id ? null : <Button variant="ghost" size="sm" className="text-break hover:text-break" onClick={() => setRemoving(m)}>Remove</Button> },
  ];
  const icols: Column<Invite>[] = [
    { key: "email", header: "Email", cell: (i) => i.email },
    { key: "role", header: "Role", cell: (i) => <span className="capitalize">{i.role}</span> },
    { key: "sent", header: "Created", cell: (i) => formatDate(i.created_at) },
    { key: "exp", header: "Expires", cell: (i) => formatDate(i.expires_at) },
    { key: "x", header: "", align: "right", cell: (i) => <Button variant="ghost" size="sm" className="text-break hover:text-break" onClick={() => setRevoking(i)}>Revoke</Button> },
  ];

  return (
    <>
      <PageHeader title="Team" description="People in your organisation and what they can do." actions={<Button onClick={() => setInviteOpen(true)}><UserPlus className="size-4" aria-hidden /> Invite member</Button>} />
      {members.error ? <ErrorState error={members.error} onRetry={() => members.refetch()} /> : (
        <DataTable caption="Members" columns={cols} rows={members.data} rowKey={(m) => m.id} loading={members.isLoading} rowClassName={(m) => (m.is_active ? undefined : "opacity-60")} />
      )}

      <h2 className="mb-3 mt-10 font-serif text-xl font-semibold">Pending invites</h2>
      {invites.error ? <ErrorState error={invites.error} onRetry={() => invites.refetch()} /> : invites.data && !invites.data.length ? (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">No pending invites.</p>
      ) : <DataTable caption="Pending invites" columns={icols} rows={invites.data} rowKey={(i) => i.id} loading={invites.isLoading} />}

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} onCreated={(c) => { setInviteOpen(false); setCreated(c); }} />
      <Dialog open={!!created} onOpenChange={(o) => { if (!o) setCreated(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite link ready</DialogTitle>
            <DialogDescription>No email is sent — share this link with them yourself. It expires {created ? formatDate(created.expires_at) : ""}.</DialogDescription>
          </DialogHeader>
          <div className="flex gap-2"><Input readOnly value={created?.invite_url ?? ""} aria-label="Invite link" className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} /><CopyButton value={created?.invite_url ?? ""} /></div>
          <DialogFooter><Button onClick={() => setCreated(null)}>Done</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog open={!!removing} onOpenChange={(o) => { if (!o) setRemoving(null); }} title="Remove this member?" description={<>{removing?.email} will lose access to your organisation straight away.</>} confirmLabel="Remove" destructive
        onConfirm={async () => { if (!removing) return; try { await remove.mutateAsync(removing.id); toast.success("Member removed"); } catch (e) { toast.error(errorMessage(e)); throw e; } }} />
      <ConfirmDialog open={!!revoking} onOpenChange={(o) => { if (!o) setRevoking(null); }} title="Revoke this invite?" description="The invite link will stop working." confirmLabel="Revoke" destructive
        onConfirm={async () => { if (!revoking) return; try { await delInvite.mutateAsync(revoking.id); toast.success("Invite revoked"); } catch (e) { toast.error(errorMessage(e)); throw e; } }} />
    </>
  );
}

function InviteDialog({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (o: boolean) => void; onCreated: (c: CreatedInvite) => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "member">("member");
  const [err, setErr] = useState<string | undefined>();
  const create = useCreateInvite();
  const reset = () => { setEmail(""); setRole("member"); setErr(undefined); };
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { setErr("Enter a valid email address."); return; }
    try { const c = await create.mutateAsync({ email: email.trim(), role }); reset(); onCreated(c); } catch (e) { setErr(errorMessage(e)); }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent>
        <form method="post" onSubmit={submit} className="space-y-5" noValidate>
          <DialogHeader><DialogTitle>Invite member</DialogTitle><DialogDescription>You'll get a link to share. Admins can manage keys, team and settings; members can upload and view results.</DialogDescription></DialogHeader>
          <div className="space-y-2"><Label htmlFor="inv-email">Email</Label><Input id="inv-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus aria-describedby="inv-err" /></div>
          <div className="space-y-2">
            <Label htmlFor="inv-role">Role</Label>
            <Select value={role} onValueChange={(v) => setRole(v as "admin" | "member")}>
              <SelectTrigger id="inv-role"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="member">Member</SelectItem><SelectItem value="admin">Admin</SelectItem></SelectContent>
            </Select>
          </div>
          <FieldError id="inv-err" message={err} />
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" disabled={create.isPending}>{create.isPending ? "Creating…" : "Create invite"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

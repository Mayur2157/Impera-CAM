import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthLayout, FieldError } from "@/components/ledger/auth-layout";
import { PasswordStrength } from "@/components/ledger/password-strength";
import { ErrorState } from "@/components/ledger/states";
import { acceptInvite, useInviteInfo } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";

export const Route = createFileRoute("/invite/$token")({
  head: () => ({
    meta: [
      { title: "Accept invitation — Impera CAM" },
      { name: "description", content: "Join your team on Impera CAM." },
      { property: "og:title", content: "Accept invitation — Impera CAM" },
      { property: "og:description", content: "Join your team on Impera CAM." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: InvitePage,
});

function InvitePage() {
  const { token } = Route.useParams();
  const info = useInviteInfo(token);
  const { signIn } = useAuth();
  const nav = useNavigate();
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pw.length < 8) return setErr("Use at least 8 characters");
    setBusy(true);
    setErr(undefined);
    try {
      const r = await acceptInvite({ token, password: pw });
      signIn(r.access_token);
      nav({ to: "/app" });
    } catch (x) {
      setErr(errorMessage(x));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Join your team" subtitle="Set a password to accept the invitation.">
      {info.isLoading && <div className="space-y-3"><Skeleton className="h-16 w-full" /><Skeleton className="h-10 w-full" /></div>}
      {info.error && <ErrorState error={info.error} onRetry={() => info.refetch()} />}
      {info.data && (
        <form method="post" onSubmit={submit} className="space-y-4" noValidate>
          <div className="rounded-lg border bg-card p-4 text-sm">
            <p><span className="text-muted-foreground">Organisation:</span> <strong>{info.data.org_name}</strong></p>
            <p><span className="text-muted-foreground">Role:</span> <span className="capitalize">{info.data.role}</span></p>
            <p><span className="text-muted-foreground">Email:</span> {info.data.email}</p>
            <p className="mt-1 text-xs text-muted-foreground">Expires {formatDate(info.data.expires_at)}</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pw">Password</Label>
            <Input id="pw" type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} aria-describedby="pw-s pw-e" />
            <PasswordStrength id="pw-s" value={pw} />
            <FieldError id="pw-e" message={err} />
          </div>
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "Joining…" : "Accept and join"}</Button>
        </form>
      )}
    </AuthLayout>
  );
}

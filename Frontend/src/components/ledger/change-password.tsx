import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useChangePassword } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import { PasswordStrength } from "./password-strength";

export function ChangePasswordDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const m = useChangePassword();
  const close = (o: boolean) => { if (!o) { setCur(""); setNext(""); setErr(null); } onOpenChange(o); };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>Use at least 8 characters.</DialogDescription>
        </DialogHeader>
        <form method="post"
          className="space-y-4"
          onSubmit={async (e) => {
            e.preventDefault();
            if (next.length < 8) return setErr("New password must be at least 8 characters.");
            try {
              await m.mutateAsync({ current_password: cur, new_password: next });
              toast.success("Password changed");
              close(false);
            } catch (x) { setErr(errorMessage(x)); }
          }}
        >
          <div className="space-y-1.5"><Label htmlFor="cur">Current password</Label><Input id="cur" type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} /></div>
          <div className="space-y-1.5"><Label htmlFor="new">New password</Label><Input id="new" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} /><PasswordStrength id="new-s" value={next} /></div>
          {err && <p role="alert" className="text-sm text-break">{err}</p>}
          <DialogFooter><Button type="submit" disabled={m.isPending}>{m.isPending ? "Saving…" : "Change password"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

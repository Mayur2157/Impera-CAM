import { useState, type ReactNode } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      type="button" variant="outline" size="sm"
      onClick={async () => {
        await navigator.clipboard.writeText(value);
        setDone(true);
        toast.success("Copied to clipboard");
        setTimeout(() => setDone(false), 1500);
      }}
    >
      {done ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
      {done ? "Copied" : label}
    </Button>
  );
}

export function ConfirmDialog({
  open, onOpenChange, title, description, confirmLabel = "Confirm", destructive, typeToConfirm, onConfirm, children,
}: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: ReactNode;
  confirmLabel?: string; destructive?: boolean; typeToConfirm?: string | undefined; onConfirm: () => void | Promise<void>; children?: ReactNode;
}) {
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const ok = !typeToConfirm || typed === typeToConfirm;
  return (
    <AlertDialog open={open} onOpenChange={(o) => { if (!o) setTyped(""); onOpenChange(o); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description && <AlertDialogDescription>{description}</AlertDialogDescription>}
        </AlertDialogHeader>
        {children}
        {typeToConfirm && (
          <div className="space-y-2">
            <Label htmlFor="confirm-type">Type <span className="font-mono">{typeToConfirm}</span> to confirm</Label>
            <Input id="confirm-type" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={!ok || busy}
            className={destructive ? "bg-break text-break-foreground hover:bg-break/90" : undefined}
            onClick={async (e) => {
              e.preventDefault();
              setBusy(true);
              try { await onConfirm(); onOpenChange(false); setTyped(""); } finally { setBusy(false); }
            }}
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

import { cn } from "@/lib/utils";

export function scorePassword(p: string) {
  let s = 0;
  if (p.length >= 8) s++;
  if (p.length >= 12) s++;
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++;
  if (/\d/.test(p)) s++;
  if (/[^A-Za-z0-9]/.test(p)) s++;
  return Math.min(4, s);
}

export function PasswordStrength({ value, id }: { value: string; id: string }) {
  const s = value ? scorePassword(value) : 0;
  const labels = ["Too short", "Weak", "Fair", "Good", "Strong"];
  const tone = s <= 1 ? "bg-break" : s === 2 ? "bg-warn" : "bg-tie";
  return (
    <div id={id} className="space-y-1" aria-live="polite">
      <div className="flex gap-1" aria-hidden>
        {[0, 1, 2, 3].map((i) => <div key={i} className={cn("h-1 flex-1 rounded-full bg-muted", value && i < s && tone)} />)}
      </div>
      {value && <p className="text-xs text-muted-foreground">Strength: {labels[s]}</p>}
    </div>
  );
}

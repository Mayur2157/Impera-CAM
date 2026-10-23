import type { ReactNode } from "react";
import { Logo } from "./brand";

export function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle?: ReactNode; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="font-serif text-3xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-6 text-sm text-muted-foreground">{footer}</div>}
        </main>
      </div>
      <aside className="ledger-rule relative hidden border-l bg-card lg:flex lg:items-center lg:justify-center" aria-hidden>
        <div className="w-[26rem] rounded-lg border bg-background p-6 shadow-soft">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Balance check</p>
          <div className="mt-4 space-y-2 font-mono text-sm tabular-nums">
            {[
              ["3,25,000.00", "−45,000.00", "+0.00", "2,80,000.00"],
              ["2,80,000.00", "−0.00", "+1,12,500.00", "3,92,500.00"],
              ["3,92,500.00", "−18,250.00", "+0.00", "3,74,250.00"],
            ].map((r, i) => (
              <div key={i} className="flex items-center justify-between gap-2 border-b pb-2 last:border-0">
                <span className="text-muted-foreground">{r[0]}</span>
                <span className="text-break">{r[1]}</span>
                <span className="text-tie">{r[2]}</span>
                <span>= {r[3]}</span>
                <span className="text-tie">✓</span>
              </div>
            ))}
          </div>
          <p className="mt-5 text-sm text-muted-foreground">Every row reconciled against the printed balance before a single ratio is computed.</p>
        </div>
      </aside>
    </div>
  );
}

export function FieldError({ id, message }: { id: string; message?: string | undefined }) {
  if (!message) return null;
  return <p id={id} role="alert" className="text-sm text-break">{message}</p>;
}

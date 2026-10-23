import type { ReactNode } from "react";
import { PublicFooter, PublicHeader } from "./brand";

export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <PublicHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p role="note" className="mb-6 inline-block rounded-md border border-warn/30 bg-warn-soft px-3 py-1 text-xs font-semibold uppercase tracking-wider text-warn">Draft — placeholder text, not legal advice</p>
        <h1 className="font-serif text-4xl font-semibold">{title}</h1>
        <div className="mt-8 space-y-5 text-muted-foreground [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-foreground">{children}</div>
      </main>
      <PublicFooter />
    </div>
  );
}

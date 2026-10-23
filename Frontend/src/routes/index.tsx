import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, FileUp, Lock, ScanLine, ShieldCheck, Sigma } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PublicFooter, PublicHeader } from "@/components/ledger/brand";
import { BalanceCheckBadge, RiskGradeBadge, ScoreGauge } from "@/components/ledger/badges";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Impera CAM — Bank statements to a verified CAM in seconds" },
      { name: "description", content: "Upload Indian bank-statement PDFs and get a balance-verified Credit Appraisal Memo for NBFCs, banks and DSAs, via portal or API." },
      { property: "og:title", content: "Impera CAM — Bank statements to a verified CAM in seconds" },
      { property: "og:description", content: "Balance-verified Credit Appraisal Memos from bank-statement PDFs, via portal or REST API." },
    ],
  }),
  component: Landing,
});

const snippet = `curl -X POST https://api.impera.example/api/v1/jobs \\
  -H "X-API-Key: icam_live_…" \\
  -F "files[]=@statement.pdf"

# → 201 {"job_id": "job_9Xr1", "files": [...]}`;

function Landing() {
  return (
    <div className="min-h-screen">
      <PublicHeader />
      <main>
        <section className="ledger-rule border-b">
          <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1.2fr_1fr] lg:py-28">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-primary">For NBFCs, banks, co-operative banks & DSAs</p>
              <h1 className="mt-4 font-serif text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">Bank statements to a verified CAM in seconds</h1>
              <p className="mt-6 max-w-xl text-lg text-muted-foreground">Upload any Indian bank-statement PDF — digital or scanned. Every row is reconciled against the printed balance before a single ratio reaches your credit committee.</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" asChild><Link to="/signup">Start free <ArrowRight className="size-4" /></Link></Button>
                <Button size="lg" variant="outline" asChild><Link to="/pricing">See pricing</Link></Button>
              </div>
            </div>
            <div className="rounded-xl border bg-card p-6 shadow-soft" aria-label="Sample CAM summary">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Sample · Demo Traders Pvt Ltd</p>
                  <p className="mt-1 font-medium">HDFC Bank · <span className="font-mono">••••4821</span></p>
                  <p className="text-sm text-muted-foreground">Apr – Sep 2024 · 6 months</p>
                </div>
                <RiskGradeBadge rating="PRIME" />
              </div>
              <div className="mt-4 flex justify-center"><ScoreGauge value={82} rating="PRIME" /></div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                {[["ABB", "₹4,12,500"], ["FOIR", "38.4%"], ["DSCR", "1.76×"], ["Bounces", "0"]].map(([k, v]) => (
                  <div key={k} className="rounded-md bg-muted px-3 py-2"><dt className="text-xs text-muted-foreground">{k}</dt><dd className="font-semibold tabular-nums">{v}</dd></div>
                ))}
              </dl>
              <div className="mt-4"><BalanceCheckBadge chain={1} /></div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6" aria-labelledby="how">
          <h2 id="how" className="font-serif text-3xl font-semibold">How it works</h2>
          <ol className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              { icon: FileUp, t: "Upload", d: "Drop up to your plan's file limit of PDFs. Password-protected statements welcome — the password is never stored." },
              { icon: ScanLine, t: "Read & verify", d: "Digital text is parsed directly; scanned pages go to GPU OCR. Every row's running balance is checked." },
              { icon: Sigma, t: "Get the CAM", d: "Score, risk grade, ABB, FOIR, DSCR, EMIs, bounces and counterparties — plus an Excel export." },
            ].map((s, i) => (
              <li key={s.t} className="rounded-lg border bg-card p-6 shadow-soft">
                <div className="flex items-center gap-3"><span className="font-mono text-sm text-muted-foreground">0{i + 1}</span><s.icon className="size-5 text-primary" aria-hidden /></div>
                <h3 className="mt-4 text-lg font-semibold">{s.t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{s.d}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="border-y bg-card" aria-labelledby="proof">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2">
            <div>
              <h2 id="proof" className="font-serif text-3xl font-semibold">The balance check, explained</h2>
              <p className="mt-4 text-muted-foreground">For every transaction we compute <span className="font-mono text-foreground">previous balance − debit + credit</span> and compare it with the balance printed on the statement. The badge shows the share of rows that tie out.</p>
              <ul className="mt-6 space-y-3 text-sm">
                <li className="flex items-center gap-3"><BalanceCheckBadge chain={1} /> every row ties — numerically verified</li>
                <li className="flex items-center gap-3"><BalanceCheckBadge chain={0.9934} /> a few rows need review</li>
                <li className="flex items-center gap-3"><BalanceCheckBadge chain={0.962} /> verification failed — don't rely on it</li>
              </ul>
            </div>
            <div className="rounded-lg border bg-background p-5 font-mono text-sm tabular-nums">
              <div className="grid grid-cols-5 gap-2 border-b pb-2 text-xs uppercase text-muted-foreground"><span>Prev</span><span>Debit</span><span>Credit</span><span>Printed</span><span /></div>
              {[["3,25,000", "45,000", "—", "2,80,000", true], ["2,80,000", "—", "1,12,500", "3,92,500", true], ["3,92,500", "18,250", "—", "3,47,250", false]].map((r, i) => (
                <div key={i} className={`grid grid-cols-5 gap-2 border-b py-2 last:border-0 ${r[4] ? "" : "bg-break-soft"}`}>
                  <span>{r[0]}</span><span>{r[1]}</span><span>{r[2]}</span><span>{r[3]}</span>
                  <span className={r[4] ? "text-tie" : "text-break"}>{r[4] ? "✓ tie" : "✗ CHECK"}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2" aria-labelledby="api">
          <div>
            <h2 id="api" className="font-serif text-3xl font-semibold">Built for your loan system</h2>
            <p className="mt-4 text-muted-foreground">Create an API key in the portal and call the same REST API from your LOS. Upload, poll, fetch the CAM as JSON or Excel.</p>
          </div>
          <pre className="overflow-x-auto rounded-lg border bg-foreground p-5 font-mono text-sm text-background"><code>{snippet}</code></pre>
        </section>

        <section className="border-t bg-card" aria-labelledby="sec">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
            <h2 id="sec" className="font-serif text-3xl font-semibold">Security & DPDP</h2>
            <div className="mt-8 grid gap-6 md:grid-cols-3">
              {[
                { icon: Lock, t: "Encrypted, short retention", d: "Statements and results are deleted automatically after your organisation's retention window." },
                { icon: ShieldCheck, t: "Privacy by default", d: "Account numbers and PAN are masked everywhere. No personal data in URLs, titles or logs." },
                { icon: Sigma, t: "Built for the DPDP Act", d: "Explicit consent at signup, purpose-limited processing and per-organisation isolation." },
              ].map((s) => (
                <div key={s.t}><s.icon className="size-5 text-primary" aria-hidden /><h3 className="mt-3 font-semibold">{s.t}</h3><p className="mt-1 text-sm text-muted-foreground">{s.d}</p></div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-20 text-center sm:px-6">
          <h2 className="font-serif text-3xl font-semibold">Underwrite on numbers that tie out</h2>
          <div className="mt-6 flex justify-center gap-3">
            <Button size="lg" asChild><Link to="/signup">Create an account</Link></Button>
            <Button size="lg" variant="outline" asChild><Link to="/login" search={{ next: undefined }}>Sign in</Link></Button>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}

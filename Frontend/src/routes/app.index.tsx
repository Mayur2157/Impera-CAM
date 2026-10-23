import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, BookOpen, KeyRound, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { RiskGradeBadge, StatusPill } from "@/components/ledger/badges";
import { EmptyState, ErrorState, PageHeader } from "@/components/ledger/states";
import { useHealth, useJobs, useUsage } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatNumber, formatPct } from "@/lib/format";

export const Route = createFileRoute("/app/")({
  head: () => ({ meta: [{ title: "Dashboard — Impera CAM" }, { name: "description", content: "This month's statements, usage against plan and recent results." }] }),
  component: Dashboard,
});

const iso = (d: Date) => d.toISOString().slice(0, 10);

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

function Dashboard() {
  const { me, isAdmin } = useAuth();
  const now = new Date();
  const usage = useUsage({ from: iso(new Date(now.getFullYear(), now.getMonth(), 1, 12)), to: iso(now), group_by: "day" });
  const jobs = useJobs(50, 0);
  const health = useHealth();

  const all = jobs.data?.items ?? [];
  const chains = all.flatMap((j) => j.files.flatMap((f) => (f.result ? [f.result.chain] : [])));
  const avgChain = chains.length ? chains.reduce((a, b) => a + b, 0) / chains.length : null;
  const inProgress = all.filter((j) => j.status === "queued" || j.status === "running").length;
  const recent = all.flatMap((j) => j.files.map((f, i) => ({ j, f, i }))).slice(0, 5);
  const noOcr = health.data && (health.data.workers.ocr === 0 || !!health.data.ocr_warning);

  const quota = usage.data?.plan.monthly_statement_quota ?? null;
  const used = usage.data?.totals.statements ?? 0;

  return (
    <>
      <PageHeader
        title={`${greeting()}`}
        description={me ? <>{me.org_name} · {now.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</> : undefined}
        actions={<Button asChild><Link to="/app/statements/new"><Upload className="size-4" aria-hidden /> Upload statements</Link></Button>}
      />

      {noOcr && (
        <div role="status" className="mb-6 flex gap-2 rounded-lg border border-warn/40 bg-warn-soft p-3 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
          <span><strong>Scanned statements may take longer right now.</strong> Text-based PDFs are not affected.</span>
        </div>
      )}

      <section aria-label="This month" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {usage.isLoading ? [0, 1].map((i) => <Skeleton key={i} className="h-32" />) : usage.error ? (
          <div className="sm:col-span-2"><ErrorState error={usage.error} onRetry={() => usage.refetch()} /></div>
        ) : usage.data && (
          <>
            <Stat label="Statements this month" value={formatNumber(used)}>
              {quota ? (
                <div className="mt-3 space-y-1">
                  <Progress value={Math.min(100, (used / quota) * 100)} aria-label="Share of monthly quota used" />
                  <p className="text-xs text-muted-foreground tabular-nums">{formatNumber(used)} of {formatNumber(quota)} quota · {formatPct((used / quota) * 100, 0)}</p>
                </div>
              ) : <p className="mt-1 text-xs text-muted-foreground">No monthly quota on your plan</p>}
            </Stat>
            <Stat label="Pages this month" value={formatNumber(usage.data.totals.pages)} />
          </>
        )}
        {jobs.isLoading ? [0, 1].map((i) => <Skeleton key={i} className="h-32" />) : (
          <>
            <Stat label="Average balance check" value={avgChain == null ? "—" : formatPct(avgChain * 100)}>
              <p className="mt-1 text-xs text-muted-foreground">Across your last {formatNumber(chains.length)} finished files</p>
            </Stat>
            <Stat label="Jobs in progress" value={formatNumber(inProgress)}>
              {inProgress > 0 && <Link to="/app/statements" className="mt-1 inline-block text-xs underline">View statements</Link>}
            </Stat>
          </>
        )}
      </section>

      <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_280px]">
        <section aria-labelledby="recent">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 id="recent" className="font-serif text-xl font-semibold">Recent statements</h2>
            <Link to="/app/statements" className="text-sm underline-offset-2 hover:underline">See all</Link>
          </div>
          {jobs.isLoading ? <Skeleton className="h-48" /> : jobs.error ? <ErrorState error={jobs.error} onRetry={() => jobs.refetch()} /> : !recent.length ? (
            <EmptyState title="No statements yet" description="Upload a bank-statement PDF to get your first verified CAM." action={<Button asChild><Link to="/app/statements/new">Upload your first statement</Link></Button>} />
          ) : (
            <ul className="divide-y rounded-lg border bg-card shadow-soft">
              {recent.map(({ j, f, i }) => (
                <li key={`${j.id}-${f.id}`} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    {f.status === "done"
                      ? <Link to="/app/statements/$jobId/files/$index" params={{ jobId: j.id, index: String(i) }} className="truncate font-medium hover:underline">{f.name}</Link>
                      : <Link to="/app/statements/$jobId" params={{ jobId: j.id }} className="truncate font-medium hover:underline">{f.name}</Link>}
                    <p className="text-xs text-muted-foreground tabular-nums">{formatDateTime(j.created)}</p>
                  </div>
                  {f.result?.score != null && <span className="font-semibold tabular-nums">{f.result.score}</span>}
                  {f.result?.risk_rating && <RiskGradeBadge rating={f.result.risk_rating} />}
                  <StatusPill status={f.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-labelledby="quick">
          <h2 id="quick" className="mb-3 font-serif text-xl font-semibold">Quick actions</h2>
          <div className="flex flex-col gap-2">
            <Button asChild variant="outline" className="justify-start"><Link to="/app/statements/new"><Upload className="size-4" aria-hidden /> Upload statements</Link></Button>
            {isAdmin && <Button asChild variant="outline" className="justify-start"><Link to="/app/api-keys"><KeyRound className="size-4" aria-hidden /> Create API key</Link></Button>}
            <Button asChild variant="outline" className="justify-start"><Link to="/app/docs"><BookOpen className="size-4" aria-hidden /> Read the API docs</Link></Button>
          </div>
        </section>
      </div>
    </>
  );
}

function Stat({ label, value, children }: { label: string; value: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-5 shadow-soft">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 font-serif text-3xl font-semibold tabular-nums">{value}</p>
      {children}
    </div>
  );
}

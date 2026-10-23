import { useMemo, useState, type ReactNode } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Download, Printer, Clock, FileX, Info, Check, X } from "lucide-react";
import { toast } from "sonner";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, Pie, PieChart, Cell, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ErrorState, EmptyState } from "@/components/ledger/states";
import { BalanceCheckBadge, MaskedAccount, Money, RiskGradeBadge, ScoreGauge } from "@/components/ledger/badges";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { useCamResult, useTransactions, downloadExcel } from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/client";
import type { CamResult, ScoreKey, Txn } from "@/lib/api/types";
import { formatDate, formatINR, formatNumber, formatPct } from "@/lib/format";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/statements/$jobId_/files/$index")({
  head: () => ({ meta: [{ title: "Credit appraisal memo — Impera CAM" }, { name: "description", content: "Credit appraisal memo for a verified bank statement." }] }),
  component: CamPage,
});

const SCORE_LABELS: Record<ScoreKey, string> = {
  cashflow_margin_score: "Cash-flow margin", liquidity_abb_score: "Liquidity (ABB)", debt_capacity_score: "Debt capacity",
  emi_regularity_score: "EMI regularity", facility_compliance_score: "Facility compliance", bounce_behavior_score: "Bounce behaviour",
  transaction_risk_score: "Transaction risk", income_concentration_score: "Income concentration",
};
const monthLabel = (m: string) => { const [y, mo] = m.split("-"); return formatDate(`${y}-${mo}-01`).slice(3); };
const lakh = (v: number) => v >= 1e7 ? `₹${(v / 1e7).toFixed(1)} Cr` : `₹${(v / 1e5).toFixed(1)} L`;

function CamPage() {
  const { jobId, index } = Route.useParams();
  const i = Number(index);
  const q = useCamResult(jobId, i);
  const back = <Link to="/app/statements/$jobId" params={{ jobId }} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground print:hidden"><ArrowLeft className="size-4" /> Back to job</Link>;

  if (q.isLoading) return <div className="space-y-4">{back}<Skeleton className="h-40" /><Skeleton className="h-96" /></div>;
  if (q.error instanceof ApiError && q.error.status === 409)
    return <div className="space-y-4">{back}<EmptyState icon={<Clock className="size-6" />} title="Still processing" description="This statement isn't finished yet. The memo appears as soon as verification completes." action={<Button asChild><Link to="/app/statements/$jobId" params={{ jobId }}>Watch progress</Link></Button>} /></div>;
  if (q.error instanceof ApiError && q.error.status === 410)
    return <div className="space-y-4">{back}<EmptyState icon={<FileX className="size-6" />} title="This result has expired" description="Results are deleted after your organisation's retention period. Resubmit the PDF to analyse it again." action={<Button asChild><Link to="/app/statements/new">Resubmit the PDF</Link></Button>} /></div>;
  if (q.error || !q.data) return <div className="space-y-4">{back}<ErrorState error={q.error} onRetry={() => q.refetch()} /></div>;

  return <TooltipProvider><div className="space-y-6">{back}<Memo r={q.data} jobId={jobId} i={i} /></div></TooltipProvider>;
}

function Memo({ r, jobId, i }: { r: CamResult; jobId: string; i: number }) {
  const mobile = useIsMobile();
  const [dl, setDl] = useState(false);
  const a = r.account, s = r.score;

  async function download() {
    setDl(true);
    try {
      const blob = await downloadExcel(jobId, i);
      const url = URL.createObjectURL(blob);
      const el = document.createElement("a");
      el.href = url; el.download = `${r.file.filename.replace(/\.pdf$/i, "")}.xlsx`; el.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(errorMessage(e)); } finally { setDl(false); }
  }

  const sections: { id: string; label: string; node: ReactNode }[] = [
    { id: "overview", label: "Overview", node: <Overview r={r} /> },
    { id: "cash", label: "Cash flow", node: <CashFlow r={r} /> },
    { id: "income", label: "Income", node: <Income r={r} /> },
    { id: "debt", label: "Debt", node: <Debt r={r} /> },
    { id: "cp", label: "Counterparties", node: <Counterparties r={r} /> },
    { id: "risk", label: "Risk", node: <Risk r={r} /> },
    { id: "txns", label: "Transactions", node: <Transactions jobId={jobId} i={i} r={r} /> },
    { id: "verify", label: "Verification", node: <Verification r={r} /> },
  ];

  return (
    <>
      <header className="sticky top-0 z-20 -mx-4 border-b bg-background/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6 print:static">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Credit appraisal memo</p>
            <h1 className="mt-1 font-serif text-2xl font-semibold tracking-tight sm:text-3xl">{a.account_holder}</h1>
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-3">
              <Meta k="Bank">{a.bank_name}</Meta>
              <Meta k="Account"><MaskedAccount value={a.account_number_masked} /></Meta>
              <Meta k="Facility">{a.facility_type}</Meta>
              <Meta k="Period">{a.analysis_period} · {a.months_count} mo</Meta>
              <Meta k="Data">{a.data_sufficiency}</Meta>
              <Meta k="Check"><BalanceCheckBadge chain={r.file.chain} /></Meta>
            </dl>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <ScoreGauge value={s.credit_score_index} rating={s.risk_rating} size={140} />
              <div className="mt-1"><RiskGradeBadge rating={s.risk_rating} /></div>
              {s.score_before_caps !== s.credit_score_index && <p className="mt-1 text-xs tabular-nums text-muted-foreground">Before caps: {s.score_before_caps}</p>}
            </div>
            <div className="flex flex-col gap-2 print:hidden">
              <Button size="sm" onClick={download} disabled={dl}><Download className="size-4" /> {dl ? "Preparing…" : "Excel"}</Button>
              <Button size="sm" variant="outline" onClick={() => window.print()}><Printer className="size-4" /> Print / PDF</Button>
            </div>
          </div>
        </div>
      </header>

      {mobile ? (
        <div className="space-y-10">{sections.map((x) => <section key={x.id} aria-labelledby={`h-${x.id}`}><h2 id={`h-${x.id}`} className="mb-4 font-serif text-xl font-semibold">{x.label}</h2>{x.node}</section>)}</div>
      ) : (
        <>
          <Tabs defaultValue="overview" className="print:hidden">
            <TabsList className="h-auto flex-wrap">{sections.map((x) => <TabsTrigger key={x.id} value={x.id}>{x.label}</TabsTrigger>)}</TabsList>
            {sections.map((x) => <TabsContent key={x.id} value={x.id} className="mt-6">{x.node}</TabsContent>)}
          </Tabs>
          {/* Print: every section except the long transaction list */}
          <div className="hidden space-y-8 print:block">{sections.filter((x) => x.id !== "txns").map((x) => <section key={x.id} className="break-inside-avoid"><h2 className="mb-3 font-serif text-lg font-semibold">{x.label}</h2>{x.node}</section>)}</div>
        </>
      )}
    </>
  );
}

function Meta({ k, children }: { k: string; children: ReactNode }) {
  return <div className="flex min-w-0 items-center gap-2"><dt className="text-muted-foreground">{k}</dt><dd className="min-w-0 truncate font-medium tabular-nums">{children}</dd></div>;
}
function Card({ title, children, className }: { title?: string; children: ReactNode; className?: string }) {
  return <div className={cn("rounded-lg border bg-card p-5 shadow-soft", className)}>{title && <h3 className="mb-4 text-sm font-semibold">{title}</h3>}{children}</div>;
}
function Kpi({ label, value, hint }: { label: string; value: ReactNode; hint?: string | undefined }) {
  return <div className="rounded-lg border bg-card p-4"><p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-1.5 text-xl font-semibold tabular-nums">{value}</p>{hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}</div>;
}

function Overview({ r }: { r: CamResult }) {
  const m = r.metrics, s = r.score;
  const keys = Object.keys(SCORE_LABELS) as ScoreKey[];
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Average bank balance" value={<Money value={m.abb} />} />
        <Kpi label="Monthly eligible income" value={<Money value={m.monthly_eligible_income} />} />
        <Kpi label="Net cash flow" value={<Money value={m.net_cash_flow} />} />
        <Kpi label="Total monthly EMI" value={<Money value={m.total_monthly_emi} />} />
        {m.dscr != null ? <Kpi label="DSCR" value={m.dscr_display} hint={m.foir_percentage != null ? `FOIR ${formatPct(m.foir_percentage)}` : undefined} />
          : <Kpi label={m.foir_percentage != null ? "FOIR" : "DSCR"} value={m.foir_percentage != null ? formatPct(m.foir_percentage) : m.dscr_display} />}
        <Kpi label="Outward bounces" value={formatNumber(m.outward_bounces)} />
        <Kpi label="Cash share of inflows" value={formatPct(m.cash_share_of_inflows_pct)} />
        {m.average_limit_utilization_pct != null && <Kpi label="OD/CC utilisation" value={formatPct(m.average_limit_utilization_pct)} />}
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card title="Scorecard">
          <ul className="space-y-3">
            {keys.map((k) => {
              const v = s.scorecard_breakdown[k], max = s.max_points[k];
              const reason = s.unscored_reasons.find((x) => x.toLowerCase().startsWith(SCORE_LABELS[k].split(" ")[0]!.toLowerCase()));
              return (
                <li key={k}>
                  <div className="mb-1 flex justify-between text-sm"><span>{SCORE_LABELS[k]}</span><span className="tabular-nums text-muted-foreground">{v == null ? "Not scored" : `${v} / ${max}`}</span></div>
                  {v == null ? <p className="text-xs text-muted-foreground">{reason ?? "Not enough data to score this factor."}</p>
                    : <div className="h-2 rounded-full bg-muted" role="img" aria-label={`${v} of ${max}`}><div className="h-2 rounded-full bg-primary" style={{ width: `${(v / max) * 100}%` }} /></div>}
                </li>
              );
            })}
          </ul>
        </Card>
        <div className="space-y-6">
          {s.hard_cap_rules_applied.length > 0 && (
            <Card title="Hard caps applied">
              <ul className="space-y-2 text-sm">{s.hard_cap_rules_applied.map((h, n) => (
                <li key={h} className={cn("rounded-md border px-3 py-2", n === 0 ? "border-warn/30 bg-warn-soft text-warn font-medium" : "")}>{h}{n === 0 && <span className="ml-2 text-xs font-normal">(binding)</span>}</li>
              ))}</ul>
            </Card>
          )}
          <Card title="Strengths"><List items={s.strengths} tone="tie" empty="None recorded." /></Card>
          <Card title="Red flags"><List items={s.red_flags} tone="break" empty="No red flags." /></Card>
        </div>
      </div>
    </div>
  );
}
function List({ items, tone, empty }: { items: string[]; tone: "tie" | "break"; empty: string }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  const Icon = tone === "tie" ? Check : X;
  return <ul className="space-y-2 text-sm">{items.map((x) => <li key={x} className="flex gap-2"><Icon className={cn("mt-0.5 size-4 shrink-0", tone === "tie" ? "text-tie" : "text-break")} aria-hidden />{x}</li>)}</ul>;
}

const tipStyle = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, color: "var(--popover-foreground)" };

function CashFlow({ r }: { r: CamResult }) {
  const data = r.monthly.map((x) => ({ ...x, label: monthLabel(x.month) }));
  const cols: Column<CamResult["monthly"][number]>[] = [
    { key: "m", header: "Month", cell: (x) => monthLabel(x.month) },
    { key: "in", header: "Inflow", align: "right", cell: (x) => <Money value={x.inflow} /> },
    { key: "out", header: "Outflow", align: "right", cell: (x) => <Money value={x.outflow} /> },
    { key: "net", header: "Net", align: "right", cell: (x) => <Money value={x.net} className={x.net < 0 ? "text-break" : ""} /> },
    { key: "cb", header: "Closing balance", align: "right", cell: (x) => <Money value={x.closing_balance} /> },
    { key: "abb", header: "ABB", align: "right", cell: (x) => <Money value={x.abb} /> },
  ];
  return (
    <div className="space-y-6">
      <Card title="Monthly inflow vs outflow">
        <div className="h-72">
          <ResponsiveContainer>
            <ComposedChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} />
              <YAxis tickFormatter={lakh} tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} width={70} />
              <RTooltip formatter={(v: number) => formatINR(v)} contentStyle={tipStyle} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="inflow" name="Inflow" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="outflow" name="Outflow" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
              <Line dataKey="closing_balance" name="Closing balance" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
              <Line dataKey="abb" name="ABB" stroke="var(--chart-3)" strokeWidth={2} strokeDasharray="4 3" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <DataTable caption="Monthly cash flow" columns={cols} rows={r.monthly} rowKey={(x) => x.month} />
    </div>
  );
}

const PIE = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
function Income({ r }: { r: CamResult }) {
  const el = r.income.eligible, ex = r.income.excluded;
  const elCols: Column<typeof el[number]>[] = [
    { key: "c", header: "Category", cell: (x) => x.category },
    { key: "n", header: "Count", align: "right", cell: (x) => formatNumber(x.count) },
    { key: "a", header: "Amount", align: "right", cell: (x) => <Money value={x.amount} /> },
    { key: "m", header: "Monthly", align: "right", cell: (x) => <Money value={x.monthly} /> },
  ];
  const exCols: Column<typeof ex[number]>[] = [
    { key: "c", header: "Category", cell: (x) => x.category },
    { key: "n", header: "Count", align: "right", cell: (x) => formatNumber(x.count) },
    { key: "a", header: "Amount", align: "right", cell: (x) => <Money value={x.amount} /> },
    { key: "r", header: "Why excluded", cell: (x) => <span className="text-muted-foreground">{x.reason}</span> },
  ];
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <div><h3 className="mb-3 text-sm font-semibold">Eligible inflows</h3><DataTable caption="Eligible inflows" columns={elCols} rows={el} rowKey={(x) => x.category} /></div>
        <div><h3 className="mb-3 text-sm font-semibold">Excluded inflows</h3><DataTable caption="Excluded inflows" columns={exCols} rows={ex} rowKey={(x) => x.category} /></div>
      </div>
      <Card title="Eligible income by category">
        <div className="h-56">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={el} dataKey="amount" nameKey="category" innerRadius={55} outerRadius={85} paddingAngle={2}>
                {el.map((x, n) => <Cell key={x.category} fill={PIE[n % PIE.length]} />)}
              </Pie>
              <RTooltip formatter={(v: number) => formatINR(v)} contentStyle={tipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="mt-2 space-y-1 text-sm">{el.map((x, n) => <li key={x.category} className="flex items-center gap-2"><span className="size-2.5 rounded-sm" style={{ background: PIE[n % PIE.length] }} />{x.category}</li>)}</ul>
      </Card>
    </div>
  );
}

function Debt({ r }: { r: CamResult }) {
  const cols: Column<CamResult["debt"]["loans"][number]>[] = [
    { key: "l", header: "Lender", cell: (x) => x.lender },
    { key: "e", header: "Monthly EMI", align: "right", sortValue: (x) => x.monthly_emi, cell: (x) => <Money value={x.monthly_emi} /> },
    { key: "i", header: "Instalments", align: "right", cell: (x) => formatNumber(x.installments) },
    { key: "t", header: "Total paid", align: "right", cell: (x) => <Money value={x.total_paid} /> },
    { key: "d", header: "Last paid", cell: (x) => formatDate(x.last_paid) },
    { key: "s", header: "Status", cell: (x) => x.status },
    { key: "b", header: "Linked bounces", align: "right", cell: (x) => <span className={x.linked_bounces ? "text-break font-medium" : ""}>{x.linked_bounces}</span> },
  ];
  return <DataTable caption="Loans" columns={cols} rows={r.debt.loans} rowKey={(x) => x.lender} empty={<EmptyState title="No loan repayments found" />} />;
}

function Counterparties({ r }: { r: CamResult }) {
  const block = (title: string, list: CamResult["counterparties"]["top_inward"]) => (
    <Card title={title}>
      <ul className="space-y-3">{list.map((c) => (
        <li key={c.name}>
          <div className="mb-1 flex justify-between gap-3 text-sm"><span className="truncate">{c.name}</span><span className="tabular-nums text-muted-foreground"><Money value={c.total} /> · {formatPct(c.share_pct)}</span></div>
          <div className="h-1.5 rounded-full bg-muted"><div className="h-1.5 rounded-full bg-primary" style={{ width: `${Math.min(100, c.share_pct)}%` }} /></div>
          <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">{c.count} transactions</p>
        </li>
      ))}</ul>
    </Card>
  );
  return <div className="grid gap-6 md:grid-cols-2">{block("Top inward (who pays them)", r.counterparties.top_inward)}{block("Top outward (who they pay)", r.counterparties.top_outward)}</div>;
}

function Conf({ v }: { v: number }) {
  const cls = v >= 0.75 ? "border-break/30 bg-break-soft text-break" : v >= 0.5 ? "border-warn/30 bg-warn-soft text-warn" : "border-border bg-muted text-muted-foreground";
  return <span className={cn("inline-flex rounded-full border px-2 py-0.5 text-xs font-medium tabular-nums", cls)}>{Math.round(v * 100)}% confidence</span>;
}
function Risk({ r }: { r: CamResult }) {
  const k = r.risk;
  return (
    <div className="space-y-6">
      <div><h3 className="mb-3 text-sm font-semibold">Bounces</h3>
        <DataTable caption="Bounces" rows={k.bounces} rowKey={(x) => x.date + x.amount} empty={<EmptyState title="No bounces" description="No returned cheques or failed debits in this period." />}
          columns={[
            { key: "d", header: "Date", cell: (x) => formatDate(x.date) },
            { key: "t", header: "Type", cell: (x) => x.type },
            { key: "a", header: "Amount", align: "right", cell: (x) => <Money value={x.amount} /> },
            { key: "n", header: "Narration", cell: (x) => <span className="font-mono text-xs">{x.narration}</span> },
          ]} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Structuring alerts">
          {k.structuring.length ? <ul className="space-y-2 text-sm">{k.structuring.map((x) => <li key={x.date + x.amount} className="flex items-center justify-between gap-3"><span className="tabular-nums">{formatDate(x.date)} · <Money value={x.amount} /></span><Conf v={x.confidence} /></li>)}</ul> : <p className="text-sm text-muted-foreground">None detected.</p>}
          <p className="mt-3 text-xs text-muted-foreground">Cash deposits just under reporting thresholds.</p>
        </Card>
        <Card title="Rapid in-out">
          {k.rapid_in_out.length ? <ul className="space-y-2 text-sm">{k.rapid_in_out.map((x) => <li key={x.credit_date + x.amount} className="flex items-center justify-between gap-3"><span className="tabular-nums">{formatDate(x.credit_date)} → {formatDate(x.debit_date)} · <Money value={x.amount} /></span><Conf v={x.confidence} /></li>)}</ul> : <p className="text-sm text-muted-foreground">None detected.</p>}
          <p className="mt-3 text-xs text-muted-foreground">Money that arrives and leaves almost immediately.</p>
        </Card>
      </div>
    </div>
  );
}

const TX_PAGE = 100;
function Transactions({ jobId, i, r }: { jobId: string; i: number; r: CamResult }) {
  const [page, setPage] = useState(0);
  const [onlyCheck, setOnlyCheck] = useState(false);
  const [cat, setCat] = useState("all");
  const q = useTransactions(jobId, i, page * TX_PAGE, TX_PAGE);
  const issues = useMemo(() => new Map(r.validation.flagged_rows.map((f) => [f.row, f.issue])), [r]);
  const cats = useMemo(() => Array.from(new Set((q.data?.items ?? []).map((t) => t.category))).sort(), [q.data]);
  const rows = (q.data?.items ?? []).filter((t) => (!onlyCheck || t.status === "CHECK") && (cat === "all" || t.category === cat));

  const cols: Column<Txn>[] = [
    { key: "d", header: "Date", cell: (t) => <span className="whitespace-nowrap">{formatDate(t.date)}</span> },
    { key: "n", header: "Narration", cell: (t) => <span className="block max-w-[260px] truncate text-left font-mono text-xs" title={t.narration}>{t.narration}</span> },
    { key: "r", header: "Reference", cell: (t) => <span className="font-mono text-xs">{t.reference}</span> },
    { key: "dr", header: "Debit", align: "right", cell: (t) => t.debit ? <Money value={t.debit} paise /> : "" },
    { key: "cr", header: "Credit", align: "right", cell: (t) => t.credit ? <Money value={t.credit} paise /> : "" },
    { key: "b", header: "Balance", align: "right", cell: (t) => <Money value={t.balance} paise /> },
    { key: "c", header: "Category", cell: (t) => t.category },
    { key: "cp", header: "Counterparty", cell: (t) => t.counterparty },
    { key: "s", header: "Status", cell: (t) => t.status === "OK" ? <span className="text-xs text-tie">OK</span> : (
      <Tooltip><TooltipTrigger asChild><button type="button" className="inline-flex items-center gap-1 rounded-full border border-break/30 bg-break-soft px-2 py-0.5 text-xs font-medium text-break">CHECK <Info className="size-3" aria-hidden /></button></TooltipTrigger>
        <TooltipContent className="max-w-xs">{issues.get(t.sno) ?? "Printed balance doesn't match previous balance − debit + credit."} (page {t.page})</TooltipContent></Tooltip>
    ) },
  ];

  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2"><Switch id="chk" checked={onlyCheck} onCheckedChange={setOnlyCheck} /><Label htmlFor="chk">Only rows needing review</Label></div>
        <Select value={cat} onValueChange={setCat}>
          <SelectTrigger className="w-48" aria-label="Category"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="all">All categories</SelectItem>{cats.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
        </Select>
        {(onlyCheck || cat !== "all") && <span className="text-xs text-muted-foreground">Filters apply to the {TX_PAGE} rows on this page.</span>}
      </div>
      <DataTable caption="Transactions" columns={cols} rows={rows} rowKey={(t) => String(t.sno)} loading={q.isLoading}
        total={q.data?.total ?? 0} page={page} pageSize={TX_PAGE} onPageChange={setPage}
        rowClassName={(t) => t.status === "CHECK" ? "bg-break-soft/60" : undefined}
        empty={<EmptyState title="No matching rows" description="No rows on this page match the filters." />} />
    </div>
  );
}

function Verification({ r }: { r: CamResult }) {
  const v = r.validation;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
      <div className="space-y-6">
        <Card title="How the balance check works">
          <p className="text-sm leading-relaxed">For every row we take the previous balance, subtract the debit and add the credit. If the result equals the balance printed on the statement, the row <span className="font-medium text-tie">ties</span>. If not, it <span className="font-medium text-break">breaks</span> and is flagged for review — usually a misread digit, a missing row or an edited PDF.</p>
          <p className="mt-3 font-mono text-xs text-muted-foreground">previous balance − debit + credit = printed balance</p>
        </Card>
        <Card>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-muted-foreground">Strategy</dt><dd className="font-medium">{v.strategy}</dd></div>
            <div><dt className="text-muted-foreground">Chain mode</dt><dd className="font-medium">{v.chain_mode}</dd></div>
            <div><dt className="text-muted-foreground">Pass rate</dt><dd className="mt-1"><BalanceCheckBadge chain={v.pass_rate} /></dd></div>
            <div><dt className="text-muted-foreground">Rows read</dt><dd className="font-medium tabular-nums">{formatNumber(r.file.rows)}</dd></div>
            <div className="col-span-2"><dt className="text-muted-foreground">Completeness</dt><dd className="font-medium">{r.file.completeness}</dd></div>
          </dl>
        </Card>
      </div>
      <div><h3 className="mb-3 text-sm font-semibold">Flagged rows</h3>
        <DataTable caption="Flagged rows" rows={v.flagged_rows} rowKey={(x) => String(x.row)}
          empty={<EmptyState icon={<Check className="size-6 text-tie" />} title="Every row ties" description="No balance breaks found." />}
          columns={[{ key: "r", header: "Row", cell: (x) => <span className="font-mono">#{x.row}</span> }, { key: "i", header: "Issue", cell: (x) => x.issue }]} />
      </div>
    </div>
  );
}

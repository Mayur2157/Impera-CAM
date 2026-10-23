import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Search, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, EmptyState, ErrorState } from "@/components/ledger/states";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { StatusPill, BalanceCheckBadge, RiskGradeBadge } from "@/components/ledger/badges";
import { useJobs } from "@/lib/api/hooks";
import type { JobSummary } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { bestChain, worstGrade } from "@/lib/jobs";

export const Route = createFileRoute("/app/statements/")({
  head: () => ({ meta: [{ title: "Statements — Impera CAM" }, { name: "description", content: "History of uploaded bank statements and their verification results." }] }),
  component: History,
});

const PAGE = 20;

function History() {
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const jobs = useJobs(PAGE, page * PAGE);

  const rows = useMemo(() => {
    const items = jobs.data?.items ?? [];
    const s = q.trim().toLowerCase();
    return s ? items.filter((j) => j.files.some((f) => f.name.toLowerCase().includes(s))) : items;
  }, [jobs.data, q]);

  const cols: Column<JobSummary>[] = [
    { key: "date", header: "Uploaded", sortValue: (j) => j.created, cell: (j) => (
      <Link to="/app/statements/$jobId" params={{ jobId: j.id }} className="font-medium text-primary hover:underline">{formatDateTime(j.created)}</Link>
    ) },
    { key: "files", header: "Files", cell: (j) => (
      <div className="max-w-xs text-left">
        <div className="truncate">{j.files[0]?.name}</div>
        {j.files.length > 1 && <div className="text-xs text-muted-foreground">+{j.files.length - 1} more</div>}
      </div>
    ) },
    { key: "status", header: "Status", sortValue: (j) => j.status, cell: (j) => <StatusPill status={j.status} /> },
    { key: "chain", header: "Best balance check", sortValue: (j) => bestChain(j), cell: (j) => { const c = bestChain(j); return c == null ? <span className="text-muted-foreground">—</span> : <BalanceCheckBadge chain={c} />; } },
    { key: "grade", header: "Worst risk grade", cell: (j) => { const g = worstGrade(j); return g ? <RiskGradeBadge rating={g} /> : <span className="text-muted-foreground">—</span>; } },
  ];

  const upload = <Button asChild><Link to="/app/statements/new"><Upload className="size-4" /> Upload statements</Link></Button>;

  return (
    <>
      <PageHeader title="Statements" description="Every upload, its balance check and risk grade." actions={upload} />
      {jobs.error ? <ErrorState error={jobs.error} onRetry={() => jobs.refetch()} /> : (
        <>
          {(jobs.data?.total ?? 0) > 0 && (
            <div className="relative mb-4 max-w-sm">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by file name" aria-label="Search by file name" className="pl-9" />
            </div>
          )}
          <DataTable
            caption="Statement jobs" columns={cols} rows={rows} rowKey={(j) => j.id} loading={jobs.isLoading}
            total={q ? rows.length : jobs.data?.total ?? 0} page={page} pageSize={PAGE} onPageChange={setPage}
            empty={q
              ? <EmptyState title="No matching files" description="Try a different file name." />
              : <EmptyState title="No statements yet" description="Upload a bank-statement PDF to get your first verified CAM." action={<Button asChild><Link to="/app/statements/new">Upload your first statement</Link></Button>} />}
          />
        </>
      )}
    </>
  );
}

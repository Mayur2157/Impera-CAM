import { useEffect, useRef, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Download, FileSearch, Info, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PageHeader, ErrorState } from "@/components/ledger/states";
import { StatusPill, BalanceCheckBadge, RiskGradeBadge } from "@/components/ledger/badges";
import { useJob, downloadExcel } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/client";
import type { FileTask, Job } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

export const Route = createFileRoute("/app/statements/$jobId")({
  head: () => ({ meta: [{ title: "Statement job — Impera CAM" }, { name: "description", content: "Live processing status for an uploaded statement job." }] }),
  component: JobPage,
});

/** 1 s, ×1.5 while unchanged, max 3 s, reset on change; paused while tab hidden; stops at done/error. */
function useBackoffJob(id: string) {
  const [interval, setIntervalMs] = useState(1000);
  const [visible, setVisible] = useState(true);
  const last = useRef<string>("");
  useEffect(() => {
    const on = () => setVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", on);
    return () => document.removeEventListener("visibilitychange", on);
  }, []);
  const q = useJob(id, false);
  const { refetch } = q;
  const finished = q.data && (q.data.status === "done" || q.data.status === "error");
  useEffect(() => {
    if (!q.data) return;
    const sig = JSON.stringify(q.data);
    setIntervalMs((ms) => (sig !== last.current ? 1000 : Math.min(3000, ms * 1.5)));
    last.current = sig;
  }, [q.dataUpdatedAt, q.data]);
  useEffect(() => {
    if (!q.data || finished || !visible || q.error) return;
    const t = setTimeout(() => void refetch({ cancelRefetch: false }), interval);
    return () => clearTimeout(t);
  }, [finished, visible, interval, q.dataUpdatedAt, q.error, q.data, refetch]);
  return q;
}

function JobPage() {
  const { jobId } = Route.useParams();
  const job = useBackoffJob(jobId);
  const back = <Button variant="ghost" size="sm" asChild><Link to="/app/statements"><ArrowLeft className="size-4" /> All statements</Link></Button>;

  if (job.isLoading) return <><PageHeader title="Statement job" actions={back} /><Skeleton className="h-64" /></>;
  if (job.error || !job.data) return <><PageHeader title="Statement job" actions={back} /><ErrorState error={job.error} onRetry={() => job.refetch()} /></>;
  const j = job.data;

  return (
    <TooltipProvider>
      <PageHeader
        title="Statement job"
        description={<span className="tabular-nums">Uploaded {formatDateTime(j.created)} · <span className="font-mono">{j.id}</span> · OCR {j.use_ocr ? `on, ${j.dpi} dpi` : "off"}</span>}
        actions={back}
      />
      <section className="mb-6 rounded-lg border bg-card p-5" aria-live="polite">
        <div className="mb-2 flex items-center justify-between gap-4">
          <StatusPill status={j.status} />
          <span className="text-sm tabular-nums text-muted-foreground">{j.progress}% overall</span>
        </div>
        <Progress value={j.progress} aria-label="Overall progress" />
      </section>
      <ul className="space-y-3">
        {j.files.map((f, i) => <FileRow key={f.id} job={j} file={f} index={i} />)}
      </ul>
    </TooltipProvider>
  );
}

function FileRow({ job, file: f, index }: { job: Job; file: FileTask; index: number }) {
  const [dl, setDl] = useState(false);
  const r = f.result;

  async function download() {
    setDl(true);
    try {
      const blob = await downloadExcel(job.id, index);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(r?.filename ?? f.name).replace(/\.pdf$/i, "")}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally { setDl(false); }
  }

  return (
    <li className="rounded-lg border bg-card p-5 shadow-soft">
      <div className="flex flex-wrap items-center gap-3">
        <span className="min-w-0 flex-1 truncate font-medium">{f.name}</span>
        <StatusPill status={f.status} />
      </div>

      {f.status !== "done" && f.status !== "error" && (
        <div className="mt-3 space-y-1.5">
          <Progress value={f.progress} aria-label={`Progress for ${f.name}`} />
          <p className="flex justify-between text-sm text-muted-foreground"><span>{f.message}</span><span className="tabular-nums">{f.progress}%</span></p>
          {f.message === "waiting for OCR worker" && (
            <p className="flex gap-2 text-xs text-muted-foreground"><Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />Scanned statements are queued for the GPU OCR reader. This can take a minute when it's busy.</p>
          )}
        </div>
      )}

      {f.status === "error" && <p role="alert" className="mt-3 text-sm text-break">{f.error ?? "This file couldn't be processed."}</p>}

      {f.status === "done" && r && (
        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
          <Stat label="Rows" value={formatNumber(r.rows)} />
          <BalanceCheckBadge chain={r.chain} />
          <Stat label="Flagged" value={formatNumber(r.flagged)} />
          {r.is_partial && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="inline-flex items-center gap-1 rounded-full border border-warn/30 bg-warn-soft px-2.5 py-0.5 text-xs font-medium text-warn">Partial PDF</button>
              </TooltipTrigger>
              <TooltipContent>{r.completeness}</TooltipContent>
            </Tooltip>
          )}
          {r.score != null && <Stat label="Score" value={String(r.score)} />}
          {r.risk_rating && <RiskGradeBadge rating={r.risk_rating} />}
          <div className="ml-auto flex gap-2">
            <Button size="sm" asChild><Link to="/app/statements/$jobId/files/$index" params={{ jobId: job.id, index: String(index) }}><FileSearch className="size-4" /> View CAM</Link></Button>
            <Button size="sm" variant="outline" onClick={download} disabled={dl}><Download className="size-4" /> {dl ? "Preparing…" : "Download Excel"}</Button>
          </div>
        </div>
      )}
    </li>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <span className="text-sm"><span className="text-muted-foreground">{label} </span><span className="font-medium tabular-nums">{value}</span></span>;
}

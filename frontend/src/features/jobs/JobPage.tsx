import { ArrowLeft, ChartColumn, Download, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import { ApiError } from "@/api/client";
import { useJob } from "@/api/hooks";
import type { FileTask, Job } from "@/api/types";
import { ChainBadge, RiskBadge, StatusPill } from "@/components/badges";
import { ErrorState, LoadingState, PageHeader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { buttonStyles } from "@/components/ui/styles";
import { Card, Progress } from "@/components/ui/misc";
import { downloadFile } from "@/lib/download";
import { formatDateTime, formatNumber, plural } from "@/lib/format";

function jobSummary(job: Job): string {
  const done = job.files.filter((f) => f.status === "done").length;
  const failed = job.files.filter((f) => f.status === "error").length;
  if (job.status === "queued") return "Waiting for a worker to pick this upload up.";
  if (job.status === "running")
    return `${done + failed} of ${plural(job.files.length, "statement")} finished.`;
  if (failed && done) return `${plural(done, "statement")} analysed, ${failed} failed.`;
  if (failed)
    return job.files.length === 1
      ? "The statement couldn't be analysed."
      : "None of the statements could be analysed.";
  return `${plural(done, "statement")} analysed.`;
}

function DownloadButton({ jobId, index, file }: { jobId: string; index: number; file: FileTask }) {
  const [busy, setBusy] = useState(false);
  const onClick = async () => {
    setBusy(true);
    try {
      await downloadFile(
        `/api/v1/jobs/${jobId}/files/${index}/download`,
        file.result?.filename ?? "statement.xlsx",
      );
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "The workbook couldn't be downloaded. Try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Button variant="secondary" loading={busy} onClick={onClick}>
      {!busy && <Download className="size-4" aria-hidden />} Download Excel
      <span className="sr-only"> for {file.name}</span>
    </Button>
  );
}

function FileCard({ job, file, index }: { job: Job; file: FileTask; index: number }) {
  const r = file.result;
  return (
    <Card className="space-y-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="min-w-0 font-semibold break-all">{file.name}</h2>
        <StatusPill status={file.status} />
      </div>

      {(file.status === "queued" || file.status === "running") && (
        <div className="space-y-2">
          <Progress value={file.progress} label={`Progress for ${file.name}`} />
          <p className="text-sm text-muted">
            {file.message ? capitalise(file.message) : "Waiting in the queue"}…
          </p>
        </div>
      )}

      {file.status === "error" && (
        <p className="text-sm text-break">
          {file.error ?? "This statement couldn't be analysed."} Check the PDF (and its password), then upload
          it again.
        </p>
      )}

      {file.status === "done" && r && (
        <>
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-muted">Transactions</dt>
              <dd className="mt-0.5 font-medium">{formatNumber(r.rows)}</dd>
            </div>
            <div>
              <dt className="text-muted">Need review</dt>
              <dd className="mt-0.5 font-medium">{formatNumber(r.flagged)}</dd>
            </div>
            <div>
              <dt className="text-muted">Score</dt>
              <dd className="mt-0.5 font-medium">
                {r.score == null ? "—" : `${formatNumber(r.score)} / 100`}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Risk</dt>
              <dd className="mt-0.5">
                <RiskBadge rating={r.risk_rating} />
              </dd>
            </div>
          </dl>
          <div className="flex flex-wrap items-center gap-2">
            <ChainBadge chain={r.chain} />
            {r.info.bank && <span className="text-sm text-muted">{r.info.bank}</span>}
          </div>
          {r.is_partial && (
            <p className="flex gap-2 text-sm text-warn">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden /> {r.completeness}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Link to={`/app/statements/${job.id}/files/${index}`} className={buttonStyles()}>
              <ChartColumn className="size-4" aria-hidden /> Open analysis
              <span className="sr-only"> for {file.name}</span>
            </Link>
            <DownloadButton jobId={job.id} index={index} file={file} />
          </div>
        </>
      )}
    </Card>
  );
}

function capitalise(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function JobPage() {
  const { jobId = "" } = useParams();
  const job = useJob(jobId);
  const back = (
    <Link
      to="/app/statements"
      className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-text"
    >
      <ArrowLeft className="size-4" aria-hidden /> All statements
    </Link>
  );

  if (job.isPending)
    return (
      <>
        {back}
        <LoadingState label="Loading this upload" rows={2} />
      </>
    );
  if (job.isError) {
    const gone = job.error instanceof ApiError && job.error.status === 404;
    return (
      <>
        {back}
        <ErrorState
          error={
            gone
              ? new Error(
                  "It may have been removed after the retention period, or it belongs to another organisation.",
                )
              : job.error
          }
          title={gone ? "This upload wasn't found" : undefined}
          onRetry={gone ? undefined : () => void job.refetch()}
        />
      </>
    );
  }

  const data = job.data;
  return (
    <>
      {back}
      <PageHeader
        title={`Upload of ${formatDateTime(data.created)}`}
        description={<span aria-live="polite">{jobSummary(data)}</span>}
        actions={<StatusPill status={data.status} />}
      />
      <div className="space-y-4">
        {data.files.map((file, index) => (
          <FileCard key={file.id} job={data} file={file} index={index} />
        ))}
      </div>
    </>
  );
}

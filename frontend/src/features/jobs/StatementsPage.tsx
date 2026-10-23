import { ChevronLeft, ChevronRight, FilePlus2 } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { useJobs } from "@/api/hooks";
import type { FileTask } from "@/api/types";
import { ChainBadge, RiskBadge, StatusPill } from "@/components/badges";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { buttonStyles } from "@/components/ui/styles";
import { Card } from "@/components/ui/misc";
import { formatDateTime, formatNumber } from "@/lib/format";

import { fileHref } from "./links";

const PAGE = 20;

function Score({ file }: { file: FileTask }) {
  const s = file.result?.score;
  return <span className="font-medium">{s === null || s === undefined ? "—" : formatNumber(s)}</span>;
}

export function StatementsPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const jobs = useJobs(PAGE, (page - 1) * PAGE);

  const newButton = (
    <Link to="/app/new" className={buttonStyles()}>
      <FilePlus2 className="size-4" aria-hidden /> New analysis
    </Link>
  );
  const header = (
    <PageHeader
      title="Statements"
      description="Every statement your organisation has uploaded."
      actions={newButton}
    />
  );

  if (jobs.isPending)
    return (
      <>
        {header}
        <LoadingState label="Loading statements" />
      </>
    );
  if (jobs.isError)
    return (
      <>
        {header}
        <ErrorState error={jobs.error} onRetry={() => void jobs.refetch()} />
      </>
    );

  const { items, total } = jobs.data;
  if (total === 0) {
    return (
      <>
        {header}
        <EmptyState title="No statements yet" action={newButton}>
          Upload a bank statement PDF to get its transactions, balance check and credit score.
        </EmptyState>
      </>
    );
  }

  const rows = items.flatMap((job) => job.files.map((file, index) => ({ job, file, index })));
  const pages = Math.max(1, Math.ceil(total / PAGE));
  const go = (p: number) => setParams(p === 1 ? {} : { page: String(p) });

  return (
    <>
      {header}
      {/* table from 640px up; stacked cards below so nothing scrolls sideways on a phone */}
      <Card className="hidden overflow-x-auto sm:block">
        <table className="w-full text-sm">
          <caption className="sr-only">Uploaded statements, newest first</caption>
          <thead className="border-b border-border text-left text-xs text-muted uppercase">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">
                Statement
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Uploaded
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Status
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Balance check
              </th>
              <th scope="col" className="px-4 py-3 text-right font-medium">
                Score
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Risk
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map(({ job, file, index }) => (
              <tr key={file.id} className="hover:bg-surface-2">
                <td className="max-w-72 px-4 py-3">
                  <Link
                    to={fileHref(job, index, file)}
                    className="block truncate font-medium text-primary hover:underline"
                  >
                    {file.name}
                  </Link>
                  {file.result?.info.bank && (
                    <span className="text-xs text-muted">{file.result.info.bank}</span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-muted">{formatDateTime(job.created)}</td>
                <td className="px-4 py-3">
                  <StatusPill status={file.status} />
                </td>
                <td className="px-4 py-3">{file.result ? <ChainBadge chain={file.result.chain} /> : "—"}</td>
                <td className="px-4 py-3 text-right">
                  <Score file={file} />
                </td>
                <td className="px-4 py-3">
                  <RiskBadge rating={file.result?.risk_rating} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <ul className="space-y-3 sm:hidden" aria-label="Uploaded statements, newest first">
        {rows.map(({ job, file, index }) => (
          <li key={file.id}>
            <Card className="space-y-2 p-4">
              <Link
                to={fileHref(job, index, file)}
                className="block font-medium break-all text-primary hover:underline"
              >
                {file.name}
              </Link>
              <p className="text-xs text-muted">{formatDateTime(job.created)}</p>
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={file.status} />
                {file.result && <ChainBadge chain={file.result.chain} />}
                <RiskBadge rating={file.result?.risk_rating} />
              </div>
              {file.result?.score != null && (
                <p className="text-sm">
                  Score <Score file={file} />
                </p>
              )}
            </Card>
          </li>
        ))}
      </ul>

      <nav aria-label="Pages" className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
        <p className="text-muted">
          Uploads {formatNumber((page - 1) * PAGE + 1)}–{formatNumber(Math.min(page * PAGE, total))} of{" "}
          {formatNumber(total)}
        </p>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => go(page - 1)}>
            <ChevronLeft className="size-4" aria-hidden /> Previous
          </Button>
          <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => go(page + 1)}>
            Next <ChevronRight className="size-4" aria-hidden />
          </Button>
        </div>
      </nav>
    </>
  );
}

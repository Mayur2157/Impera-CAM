import { CircleAlert, Inbox, Lock, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, Skeleton } from "@/components/ui/misc";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** Placeholder rows shaped like the content; the label is for screen readers. */
export function LoadingState({ label = "Loading", rows = 4 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-14 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <Inbox className="size-8 text-muted" aria-hidden />
      <h2 className="text-base font-semibold">{title}</h2>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
      {action}
    </Card>
  );
}

/** What went wrong and what to do next; 403 reads as "no permission", not as a fault. */
export function ErrorState({
  error,
  onRetry,
  title,
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}) {
  const status = error instanceof ApiError ? error.status : null;
  const message = error instanceof Error ? error.message : "Something unexpected went wrong.";
  const forbidden = status === 403;
  const Icon = forbidden ? Lock : CircleAlert;
  return (
    <Card role="alert" className="flex flex-col items-center gap-3 px-6 py-10 text-center">
      <Icon className="size-8 text-break" aria-hidden />
      <h2 className="text-base font-semibold">
        {title ?? (forbidden ? "You don't have access to this" : "This couldn't be loaded")}
      </h2>
      <p className="max-w-md text-sm text-muted">{message}</p>
      {onRetry && !forbidden && (
        <Button variant="secondary" onClick={onRetry}>
          <RefreshCw className="size-4" aria-hidden /> Try again
        </Button>
      )}
    </Card>
  );
}

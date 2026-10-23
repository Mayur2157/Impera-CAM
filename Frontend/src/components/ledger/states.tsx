import type { ReactNode } from "react";
import { AlertTriangle, Inbox, Lock, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, errorMessage } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ title, description, action, icon }: { title: string; description?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed bg-card px-6 py-14 text-center">
      <div className="mb-4 rounded-full bg-muted p-3 text-muted-foreground">{icon ?? <Inbox className="size-6" aria-hidden />}</div>
      <h2 className="text-base font-semibold">{title}</h2>
      {description && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  if (error instanceof ApiError && error.status === 403) return <ForbiddenState className={className} />;
  return (
    <div role="alert" className={cn("flex flex-col items-center rounded-lg border border-break/30 bg-break-soft px-6 py-10 text-center", className)}>
      <AlertTriangle className="mb-3 size-6 text-break" aria-hidden />
      <h2 className="text-base font-semibold">That didn't load</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{errorMessage(error)}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RotateCw className="size-4" aria-hidden /> Retry
        </Button>
      )}
    </div>
  );
}

export function ForbiddenState({ className }: { className?: string | undefined }) {
  return (
    <div role="alert" className={cn("flex flex-col items-center rounded-lg border bg-card px-6 py-10 text-center", className)}>
      <Lock className="mb-3 size-6 text-muted-foreground" aria-hidden />
      <h2 className="text-base font-semibold">You don't have permission</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">Ask an owner or admin of your organisation for access.</p>
    </div>
  );
}

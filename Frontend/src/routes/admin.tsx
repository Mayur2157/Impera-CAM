import { createFileRoute, Link, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { ArrowLeft, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ledger/states";
import { Logo } from "@/components/ledger/brand";
import { useMe } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/admin")({
  ssr: false, // token lives in sessionStorage; guard runs client-side
  head: () => ({ meta: [{ title: "Staff console — Impera CAM" }, { name: "robots", content: "noindex" }] }),
  component: AdminLayout,
});

function AdminLayout() {
  const { ready, token } = useAuth();
  const me = useMe(ready && !!token);
  const nav = useNavigate();

  useEffect(() => {
    if (ready && !token) nav({ to: "/login", search: { next: window.location.pathname }, replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, token]);

  if (!ready || !token || me.isLoading) return <div className="space-y-4 p-8" aria-busy="true"><Skeleton className="h-10 w-64" /><Skeleton className="h-40" /></div>;
  if (me.error || !me.data) return <div className="p-8"><ErrorState error={me.error} onRetry={() => me.refetch()} /></div>;
  if (!me.data.is_superuser) return <NotFound />;

  return (
    <div className="min-h-screen">
      <div className="flex h-8 items-center justify-center gap-2 bg-staff text-xs font-semibold text-staff-foreground">
        <Shield className="size-3.5" aria-hidden /> Impera staff console
      </div>
      <header className="flex h-14 items-center gap-2 border-b px-3 sm:gap-6 sm:px-6">
        <span className="hidden sm:block"><Logo /></span>
        <nav aria-label="Staff console" className="flex gap-1 text-sm">
          <Link to="/admin" activeOptions={{ exact: true }} className="rounded px-3 py-1.5 text-muted-foreground hover:bg-muted" activeProps={{ className: "bg-muted text-foreground font-medium" }}>Overview</Link>
          <Link to="/admin/tenants" className="rounded px-3 py-1.5 text-muted-foreground hover:bg-muted" activeProps={{ className: "bg-muted text-foreground font-medium" }}>Tenants</Link>
        </nav>
        <Button asChild variant="ghost" size="sm" className="ml-auto"><Link to="/app"><ArrowLeft className="size-4" aria-hidden /><span className="sr-only sm:not-sr-only">Back to portal</span></Link></Button>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6"><Outlet /></main>
    </div>
  );
}

function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="mt-2 font-serif text-3xl font-semibold">Page not found</h1>
      <Button asChild className="mt-6"><Link to="/app">Go to dashboard</Link></Button>
    </main>
  );
}

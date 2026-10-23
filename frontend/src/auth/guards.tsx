import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import type { Role } from "@/api/types";
import { ErrorState, LoadingState } from "@/components/states";

import { useAuth } from "./AuthProvider";

/** Pages under /app. The server checks every call; this only routes the user. */
export function RequireAuth() {
  const { status, error, retry } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <LoadingState label="Signing you in" rows={3} />
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="mx-auto max-w-xl p-6">
        <ErrorState error={error} onRetry={retry} title="Your account couldn't be loaded" />
      </div>
    );
  }
  if (status === "signed-out") {
    const next = location.pathname + location.search;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }
  return <Outlet />;
}

/** Hide a page from roles that can't use it (the API refuses them anyway). */
export function RequireRole({
  roles,
  superuser,
  children,
}: {
  roles?: Role[];
  superuser?: boolean;
  children: ReactNode;
}) {
  const { me } = useAuth();
  const allowed = superuser ? !!me?.is_superuser : !roles || (me && roles.includes(me.role));
  if (!allowed) {
    const why = superuser
      ? "This page is for Impera staff."
      : "This page is for organisation owners and admins. Ask one of them if you need access.";
    return <ErrorState error={new Error(why)} title="You don't have access to this" />;
  }
  return <>{children}</>;
}

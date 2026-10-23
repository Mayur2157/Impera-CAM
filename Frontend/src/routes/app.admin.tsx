import { createFileRoute, redirect } from "@tanstack/react-router";

// Staff console moved to /admin; keep the old address working.
export const Route = createFileRoute("/app/admin")({
  beforeLoad: () => { throw redirect({ to: "/admin", replace: true }); },
});

import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { TenantStatus } from "@/components/ledger/badges";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { PageHeader, ErrorState } from "@/components/ledger/states";
import { DataTable, type Column } from "@/components/ledger/data-table";
import { useAdminTenants } from "@/lib/api/hooks";
import type { AdminTenant } from "@/lib/api/types";
import { formatDate, formatNumber } from "@/lib/format";

export const Route = createFileRoute("/admin/tenants/")({
  head: () => ({ meta: [{ title: "Tenants — Impera staff console" }, { name: "description", content: "All customer organisations with 30-day usage." }] }),
  component: Tenants,
});

const SIZE = 20;

function Tenants() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(0);
  const p = { query, limit: SIZE, offset: page * SIZE, ...(status !== "all" ? { status } : {}) };
  const t = useAdminTenants(p);

  const cols: Column<AdminTenant>[] = [
    { key: "name", header: "Organisation", cell: (r) => <Link to="/admin/tenants/$id" params={{ id: r.id }} className="font-medium hover:underline">{r.name}</Link>, sortValue: (r) => r.name },
    { key: "plan", header: "Plan", cell: (r) => r.plan, sortValue: (r) => r.plan },
    { key: "status", header: "Status", cell: (r) => <TenantStatus status={r.status} /> },
    { key: "users", header: "Users", align: "right", cell: (r) => formatNumber(r.users), sortValue: (r) => r.users },
    { key: "s", header: "Statements · 30 d", align: "right", cell: (r) => formatNumber(r.statements_30d), sortValue: (r) => r.statements_30d },
    { key: "p", header: "Pages · 30 d", align: "right", cell: (r) => formatNumber(r.pages_30d), sortValue: (r) => r.pages_30d },
    { key: "c", header: "Created", cell: (r) => formatDate(r.created_at), sortValue: (r) => r.created_at },
  ];

  return (
    <>
      <PageHeader title="Tenants" />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input value={query} onChange={(e) => { setQuery(e.target.value); setPage(0); }} placeholder="Search organisations" aria-label="Search organisations" className="pl-8" />
        </div>
        <ToggleGroup type="single" variant="outline" value={status} onValueChange={(v) => { if (v) { setStatus(v); setPage(0); } }} aria-label="Filter by status">
          <ToggleGroupItem value="all">All</ToggleGroupItem>
          <ToggleGroupItem value="active">Active</ToggleGroupItem>
          <ToggleGroupItem value="suspended">Suspended</ToggleGroupItem>
        </ToggleGroup>
      </div>
      {t.error ? <ErrorState error={t.error} onRetry={() => t.refetch()} /> : (
        <DataTable caption="Tenants" columns={cols} rows={t.data?.items} rowKey={(r) => r.id} loading={t.isLoading}
          total={t.data?.total ?? 0} page={page} pageSize={SIZE} onPageChange={setPage}
          empty={<p className="p-6 text-center text-sm text-muted-foreground">No organisations match.</p>} />
      )}
    </>
  );
}

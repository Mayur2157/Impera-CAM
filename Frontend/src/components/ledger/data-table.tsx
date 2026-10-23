import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number | null;
  align?: "left" | "right";
  className?: string;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string;
  loading?: boolean;
  empty?: ReactNode;
  caption: string;
  /** Server pagination; omit for client pagination over rows */
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (p: number) => void;
  rowClassName?: (row: T) => string | undefined;
}

export function DataTable<T>({ columns, rows, rowKey, loading, empty, caption, total, page: extPage, pageSize = 20, onPageChange, rowClassName }: Props<T>) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [intPage, setIntPage] = useState(0);
  const server = onPageChange !== undefined;
  const page = server ? extPage ?? 0 : intPage;
  const setPage = server ? onPageChange! : setIntPage;

  const sorted = useMemo(() => {
    if (!rows || !sort) return rows ?? [];
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortValue) return rows;
    return [...rows].sort((a, b) => {
      const va = col.sortValue!(a), vb = col.sortValue!(b);
      if (va == null) return 1;
      if (vb == null) return -1;
      return (va < vb ? -1 : va > vb ? 1 : 0) * sort.dir;
    });
  }, [rows, sort, columns]);

  const count = server ? total ?? 0 : sorted.length;
  const visible = server ? sorted : sorted.slice(page * pageSize, page * pageSize + pageSize);
  const pages = Math.max(1, Math.ceil(count / pageSize));

  if (loading) {
    return (
      <div className="space-y-2 rounded-lg border bg-card p-4" aria-busy="true" aria-label={`Loading ${caption}`}>
        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
      </div>
    );
  }
  if (!visible.length && empty) return <>{empty}</>;

  return (
    <div className="rounded-lg border bg-card shadow-soft">
      {/* Desktop table */}
      <div className="hidden overflow-x-auto sm:block">
        <table className="w-full text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b bg-muted/50">
              {columns.map((c) => {
                const active = sort?.key === c.key;
                return (
                  <th key={c.key} scope="col" aria-sort={active ? (sort!.dir === 1 ? "ascending" : "descending") : undefined}
                    className={cn("px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-muted-foreground", c.align === "right" ? "text-right" : "text-left")}>
                    {c.sortValue ? (
                      <button type="button" className="inline-flex items-center gap-1 hover:text-foreground"
                        onClick={() => setSort(active ? { key: c.key, dir: sort!.dir === 1 ? -1 : 1 } : { key: c.key, dir: 1 })}>
                        {c.header}
                        {active ? (sort!.dir === 1 ? <ArrowUp className="size-3" aria-hidden /> : <ArrowDown className="size-3" aria-hidden />) : <ArrowUpDown className="size-3 opacity-50" aria-hidden />}
                      </button>
                    ) : c.header}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={rowKey(r)} className={cn("border-b last:border-0 hover:bg-muted/30", rowClassName?.(r))}>
                {columns.map((c) => (
                  <td key={c.key} className={cn("px-4 py-3 tabular-nums", c.align === "right" && "text-right", c.className)}>{c.cell(r)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Mobile cards */}
      <ul className="divide-y sm:hidden" aria-label={caption}>
        {visible.map((r) => (
          <li key={rowKey(r)} className={cn("space-y-1.5 p-4", rowClassName?.(r))}>
            {columns.map((c) => (
              <div key={c.key} className="flex items-start justify-between gap-4 text-sm">
                <span className="text-xs uppercase tracking-wide text-muted-foreground">{c.header}</span>
                <span className="text-right tabular-nums">{c.cell(r)}</span>
              </div>
            ))}
          </li>
        ))}
      </ul>
      {pages > 1 && (
        <nav className="flex items-center justify-between border-t px-4 py-2.5 text-sm" aria-label="Pagination">
          <span className="text-muted-foreground tabular-nums">Page {page + 1} of {pages} · {count} total</span>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)} aria-label="Previous page"><ChevronLeft className="size-4" /></Button>
            <Button variant="ghost" size="sm" disabled={page >= pages - 1} onClick={() => setPage(page + 1)} aria-label="Next page"><ChevronRight className="size-4" /></Button>
          </div>
        </nav>
      )}
    </div>
  );
}

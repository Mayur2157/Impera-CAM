import { FileSpreadsheet } from "lucide-react";

import { cn } from "@/lib/cn";

export function Brand({ compact, className }: { compact?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold tracking-tight", className)}>
      <span className="grid size-8 place-items-center rounded-md bg-primary text-primary-fg">
        <FileSpreadsheet className="size-4.5" aria-hidden />
      </span>
      {!compact && <span className="text-lg">Impera CAM</span>}
    </span>
  );
}

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { CopyButton } from "./actions";
import { cn } from "@/lib/utils";

export function CodeBlock({ code, label, className }: { code: string; label?: string; className?: string }) {
  return (
    <div className={cn("relative min-w-0 max-w-full rounded-lg border bg-muted/50", className)}>
      <div className="flex items-center justify-between border-b px-3 py-1.5">
        <span className="text-xs text-muted-foreground">{label ?? ""}</span>
        <CopyButton value={code} />
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed"><code>{code}</code></pre>
    </div>
  );
}

type J = unknown;

function Leaf({ v }: { v: J }) {
  if (v === null) return <span className="text-muted-foreground">null</span>;
  if (typeof v === "string") return <span className="text-primary">"{v}"</span>;
  return <span className="tabular-nums">{String(v)}</span>;
}

function Node({ k, v, depth }: { k: string | null; v: J; depth: number }) {
  const [open, setOpen] = useState(depth < 1);
  const isObj = v !== null && typeof v === "object";
  const key = k !== null ? <span className="text-muted-foreground">{k}: </span> : null;
  if (!isObj) return <div className="pl-4">{key}<Leaf v={v} /></div>;
  const entries = Array.isArray(v) ? v.map((x, i) => [String(i), x] as const) : Object.entries(v as Record<string, J>);
  const br = Array.isArray(v) ? ["[", "]"] : ["{", "}"];
  return (
    <div className={depth ? "pl-4" : undefined}>
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="inline-flex items-center rounded hover:bg-muted focus-visible:outline-2">
        <ChevronRight className={cn("size-3 transition-transform", open && "rotate-90")} aria-hidden />
        {key}<span>{br[0]}</span>
        {!open && <span className="text-muted-foreground"> {entries.length} {Array.isArray(v) ? "items" : "keys"} {br[1]}</span>}
      </button>
      {open && <>{entries.map(([ck, cv]) => <Node key={ck} k={ck} v={cv} depth={depth + 1} />)}<div className="pl-4">{br[1]}</div></>}
    </div>
  );
}

export function JsonViewer({ value, label }: { value: J; label?: string }) {
  return (
    <div className="rounded-lg border bg-muted/50">
      <div className="flex items-center justify-between border-b px-3 py-1.5">
        <span className="text-xs text-muted-foreground">{label ?? "JSON"}</span>
        <CopyButton value={JSON.stringify(value, null, 2)} label="Copy JSON" />
      </div>
      <div className="max-h-[32rem] overflow-auto p-3 font-mono text-xs leading-relaxed"><Node k={null} v={value} depth={0} /></div>
    </div>
  );
}

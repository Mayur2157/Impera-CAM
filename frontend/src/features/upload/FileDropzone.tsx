import { FileText, Upload, X } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";

import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";

import { checkFiles, type Limits, type Rejection } from "./fileChecks";

interface Props {
  files: File[];
  onChange: (files: File[]) => void;
  limits: Limits | null;
  disabled?: boolean;
}

export function FileDropzone({ files, onChange, limits, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hintId = useId();
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState<Rejection[]>([]);

  const add = (picked: File[]) => {
    const result = checkFiles(picked, files, limits);
    setRejected(result.rejected);
    if (result.accepted.length) onChange([...files, ...result.accepted]);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (!disabled) add(Array.from(e.dataTransfer.files));
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-border bg-surface",
          disabled && "opacity-60",
        )}
      >
        <Upload className="size-8 text-muted" aria-hidden />
        <div>
          <p className="font-medium">Drag bank statement PDFs here</p>
          <p id={hintId} className="mt-1 text-sm text-muted">
            {limits ? `Up to ${limits.maxFiles} files, ${limits.maxMb} MB each.` : "PDF files only."} Each
            file is analysed separately.
          </p>
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          aria-describedby={hintId}
          className="min-h-10 rounded-md border border-border bg-surface px-4 text-sm font-medium hover:bg-surface-2 disabled:cursor-not-allowed"
        >
          Choose files
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          hidden
          onChange={(e) => {
            add(Array.from(e.target.files ?? []));
            e.target.value = ""; // picking the same file again still fires
          }}
        />
      </div>

      <div aria-live="polite">
        {rejected.length > 0 && (
          <ul className="space-y-1 rounded-md bg-break-bg px-4 py-3 text-sm text-break">
            {rejected.map((r) => (
              <li key={r.name + r.reason}>
                <span className="font-medium break-all">{r.name}</span> {r.reason}.
              </li>
            ))}
          </ul>
        )}
      </div>

      {files.length > 0 && (
        <ul
          className="divide-y divide-border rounded-lg border border-border bg-surface"
          aria-label="Files to analyse"
        >
          {files.map((f, i) => (
            <li key={`${f.name}:${f.size}`} className="flex items-center gap-3 px-4 py-2.5">
              <FileText className="size-4 shrink-0 text-muted" aria-hidden />
              <span className="min-w-0 flex-1 truncate text-sm">{f.name}</span>
              <span className="shrink-0 text-xs text-muted">{formatBytes(f.size)}</span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChange(files.filter((_, j) => j !== i))}
                className="grid size-9 shrink-0 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text"
              >
                <X className="size-4" aria-hidden />
                <span className="sr-only">Remove {f.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

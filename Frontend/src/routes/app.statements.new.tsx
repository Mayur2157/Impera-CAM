import { useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { FileText, UploadCloud, X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, ErrorState } from "@/components/ledger/states";
import { useCreateJob, useOrg } from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/client";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/statements/new")({
  head: () => ({ meta: [{ title: "Upload statements — Impera CAM" }, { name: "description", content: "Upload bank-statement PDFs for verification and CAM generation." }] }),
  component: UploadPage,
});

function friendly(e: unknown) {
  if (e instanceof ApiError) {
    if (e.status === 400) return e.message;
    if (e.status === 429) return `Too many statements are still processing. ${e.retryAfter ? `Try again in ${e.retryAfter} s.` : "Try again shortly."}`;
    if (e.status === 503) return "Processing is temporarily unavailable. Please try again in a few minutes.";
  }
  return errorMessage(e);
}

function UploadPage() {
  const org = useOrg();
  const create = useCreateJob();
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [problems, setProblems] = useState<string[]>([]);
  const [drag, setDrag] = useState(false);
  const [password, setPassword] = useState("");
  const [bank, setBank] = useState("");
  const [ocr, setOcr] = useState(true);
  const [dpi, setDpi] = useState("300");
  const [pct, setPct] = useState(0);

  if (org.isLoading) return <><PageHeader title="Upload statements" /><Skeleton className="h-64" /></>;
  if (org.error || !org.data) return <><PageHeader title="Upload statements" /><ErrorState error={org.error} onRetry={() => org.refetch()} /></>;
  const { max_files, max_upload_mb, status } = org.data;
  const suspended = status === "suspended";

  function add(list: FileList | null) {
    if (!list) return;
    const next = [...files];
    const errs: string[] = [];
    for (const f of Array.from(list)) {
      if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) { errs.push(`${f.name} isn't a PDF.`); continue; }
      if (f.size > max_upload_mb * 1024 * 1024) { errs.push(`${f.name} is ${formatBytes(f.size)} — your plan allows up to ${max_upload_mb} MB per file.`); continue; }
      if (next.some((x) => x.name === f.name && x.size === f.size)) continue;
      if (next.length >= max_files) { errs.push(`Your plan allows up to ${max_files} files per job. ${f.name} was not added.`); continue; }
      next.push(f);
    }
    setFiles(next);
    setProblems(errs);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!files.length) { setProblems(["Add at least one PDF."]); return; }
    const fd = new FormData();
    files.forEach((f) => fd.append("files[]", f));
    if (password) fd.append("password", password);
    if (bank.trim()) fd.append("bank", bank.trim());
    fd.append("use_ocr", String(ocr));
    fd.append("dpi", dpi);
    setPct(0);
    create.mutate({ fd, onProgress: setPct }, {
      onSuccess: (r) => navigate({ to: "/app/statements/$jobId", params: { jobId: r.job_id } }),
    });
  }

  const busy = create.isPending;

  return (
    <>
      <PageHeader title="Upload statements" description={`PDF only · up to ${max_files} files per job · ${max_upload_mb} MB each.`} />
      <form method="post" onSubmit={submit} className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <div
            role="button" tabIndex={0} aria-label="Choose PDF files or drop them here"
            onClick={() => input.current?.click()}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.current?.click(); } }}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files); }}
            className={cn("flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed bg-card px-6 py-14 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              drag ? "border-primary bg-accent" : "hover:border-primary/50", (busy || suspended) && "pointer-events-none opacity-60")}
          >
            <UploadCloud className="mb-3 size-8 text-muted-foreground" aria-hidden />
            <p className="font-medium">Drop bank-statement PDFs here</p>
            <p className="mt-1 text-sm text-muted-foreground">or click to choose files</p>
            <input ref={input} type="file" accept="application/pdf,.pdf" multiple hidden onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
          </div>

          {problems.length > 0 && (
            <ul role="alert" className="space-y-1 rounded-md border border-warn/30 bg-warn-soft p-3 text-sm text-warn">
              {problems.map((p) => <li key={p} className="flex gap-2"><AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />{p}</li>)}
            </ul>
          )}

          {files.length > 0 && (
            <ul className="divide-y rounded-lg border bg-card" aria-label="Selected files">
              {files.map((f, i) => (
                <li key={f.name + f.size} className="flex items-center gap-3 px-4 py-3 text-sm">
                  <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0 flex-1 truncate">{f.name}</span>
                  <span className="tabular-nums text-muted-foreground">{formatBytes(f.size)}</span>
                  <Button type="button" variant="ghost" size="sm" disabled={busy} aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}><X className="size-4" /></Button>
                </li>
              ))}
              <li className="px-4 py-2 text-xs tabular-nums text-muted-foreground">{files.length} of {max_files} files</li>
            </ul>
          )}

          {busy && (
            <div aria-live="polite" className="space-y-1.5">
              <div className="flex justify-between text-sm"><span>Uploading…</span><span className="tabular-nums">{pct}%</span></div>
              <Progress value={pct} aria-label="Upload progress" />
            </div>
          )}
          {create.error && <p role="alert" className="rounded-md border border-break/30 bg-break-soft p-3 text-sm text-break">{friendly(create.error)}</p>}
        </div>

        <aside className="space-y-5 rounded-lg border bg-card p-5">
          <div className="space-y-1.5">
            <Label htmlFor="pw">PDF password <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <Input id="pw" type="password" autoComplete="off" value={password} onChange={(e) => setPassword(e.target.value)} disabled={busy} />
            <p className="text-xs text-muted-foreground">Used once to open the file. Never stored.</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="bank">Bank name <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <Input id="bank" value={bank} onChange={(e) => setBank(e.target.value)} disabled={busy} placeholder="e.g. HDFC Bank" />
            <p className="text-xs text-muted-foreground">Only needed if the statement shows the bank as a logo, not as text.</p>
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="ocr">Read scanned pages (OCR)</Label>
              <p className="text-xs text-muted-foreground">Recommended for scanned or photographed statements.</p>
            </div>
            <Switch id="ocr" checked={ocr} onCheckedChange={setOcr} disabled={busy} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dpi">OCR quality</Label>
            <Select value={dpi} onValueChange={setDpi} disabled={busy || !ocr}>
              <SelectTrigger id="dpi"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="200">200 dpi — faster</SelectItem>
                <SelectItem value="300">300 dpi — recommended</SelectItem>
                <SelectItem value="400">400 dpi — faint scans</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" className="w-full" disabled={busy || suspended || !files.length}>
            {busy ? "Uploading…" : `Upload ${files.length || ""} ${files.length === 1 ? "statement" : "statements"}`.replace("  ", " ")}
          </Button>
          {suspended && <p className="text-xs text-break">Your organisation is suspended; uploads are disabled.</p>}
        </aside>
      </form>
    </>
  );
}

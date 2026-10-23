import { useEffect, useRef, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { FileText, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ledger/states";
import { StatusPill } from "@/components/ledger/badges";
import { CodeBlock, JsonViewer } from "@/components/ledger/code";
import { api, errorMessage } from "@/lib/api/client";
import type { CamResult, CreateJobResponse, Job } from "@/lib/api/types";
import { API_BASE_DISPLAY } from "@/lib/api/snippets";
import { formatBytes } from "@/lib/format";

export const Route = createFileRoute("/app/playground")({
  head: () => ({ meta: [{ title: "API playground — Impera CAM" }, { name: "description", content: "Try the Impera CAM API with your signed-in session." }] }),
  component: Playground,
});

type Poll = { n: number; at: string; body: Job };

function Playground() {
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<"idle" | "uploading" | "polling" | "done" | "error">("idle");
  const [created, setCreated] = useState<CreateJobResponse | null>(null);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [result, setResult] = useState<CamResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const cancel = useRef(false);

  useEffect(() => () => { cancel.current = true; }, []);

  function reset() { cancel.current = true; setPhase("idle"); setCreated(null); setPolls([]); setResult(null); setErr(null); }

  async function run() {
    if (!file) return;
    cancel.current = false;
    setErr(null); setPolls([]); setResult(null); setCreated(null);
    try {
      setPhase("uploading");
      const fd = new FormData();
      fd.append("files[]", file);
      const c = await api<CreateJobResponse>("/api/v1/jobs", { method: "POST", body: fd });
      setCreated(c);
      setPhase("polling");
      let delay = 1000, n = 0, job: Job;
      for (;;) {
        if (cancel.current) return;
        job = await api<Job>(`/api/v1/jobs/${c.job_id}`);
        n += 1;
        const snap: Poll = { n, at: new Date().toLocaleTimeString("en-IN"), body: job };
        setPolls((p) => [snap, ...p].slice(0, 30));
        if (job.status === "done" || job.status === "error") break;
        await new Promise((r) => setTimeout(r, delay));
        delay = Math.min(delay * 1.5, 3000);
      }
      if (job.status === "error" || job.files[0]?.status === "error") { setErr(job.files[0]?.error ?? "Processing failed."); setPhase("error"); return; }
      const r = await api<CamResult>(`/api/v1/jobs/${c.job_id}/files/0/result`);
      if (cancel.current) return;
      setResult(r); setPhase("done");
    } catch (e) { setErr(errorMessage(e)); setPhase("error"); }
  }

  const jobId = created?.job_id ?? "$JOB_ID";
  const curl = `curl -X POST "${API_BASE_DISPLAY}/api/v1/jobs" \\
  -H "X-API-Key: icam_live_YOUR_KEY" \\
  -F "files[]=@${file ? "statement.pdf" : "statement.pdf"}"

curl "${API_BASE_DISPLAY}/api/v1/jobs/${jobId}" \\
  -H "X-API-Key: icam_live_YOUR_KEY"

curl "${API_BASE_DISPLAY}/api/v1/jobs/${jobId}/files/0/result" \\
  -H "X-API-Key: icam_live_YOUR_KEY"`;

  const busy = phase === "uploading" || phase === "polling";
  const latest = polls[0]?.body;

  return (
    <>
      <PageHeader
        title="API playground"
        description="Runs real API calls with your signed-in session — you never paste a key here. Jobs you run appear in Statements and count toward usage."
        actions={<Button asChild variant="outline"><Link to="/app/docs">API docs</Link></Button>}
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="min-w-0 space-y-6">
          <section className="rounded-lg border bg-card p-5" aria-labelledby="pg-1">
            <h2 id="pg-1" className="mb-3 text-sm font-semibold">1. Upload a PDF</h2>
            <div className="space-y-2">
              <Label htmlFor="pg-file">Statement PDF</Label>
              <Input id="pg-file" type="file" accept="application/pdf,.pdf" disabled={busy} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              {file && <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><FileText className="size-3.5" aria-hidden />{formatBytes(file.size)}</p>}
            </div>
            <div className="mt-4 flex gap-2">
              <Button onClick={run} disabled={!file || busy}><Play className="size-4" aria-hidden />{phase === "uploading" ? "Uploading…" : phase === "polling" ? "Polling…" : "Run"}</Button>
              {phase !== "idle" && <Button variant="outline" onClick={reset}><RotateCcw className="size-4" aria-hidden /> Reset</Button>}
            </div>
            {err && <p role="alert" className="mt-3 text-sm text-break">{err}</p>}
          </section>

          <section className="rounded-lg border bg-card p-5" aria-labelledby="pg-2" aria-live="polite">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="pg-2" className="text-sm font-semibold">2. Poll the job</h2>
              {latest && <StatusPill status={latest.status} />}
            </div>
            {polls.length === 0 ? <p className="text-sm text-muted-foreground">Each <span className="font-mono">GET /api/v1/jobs/{"{job_id}"}</span> response appears here.</p> : (
              <ol className="max-h-96 space-y-2 overflow-auto">
                {polls.map((p) => (
                  <li key={p.n}>
                    <details open={p.n === polls[0]?.n}>
                      <summary className="cursor-pointer text-xs text-muted-foreground tabular-nums">Poll #{p.n} · {p.at} · {p.body.status} · {p.body.progress}%</summary>
                      <pre className="mt-1 overflow-x-auto rounded bg-muted/50 p-2 font-mono text-[11px]">{JSON.stringify(p.body, null, 2)}</pre>
                    </details>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        <div className="min-w-0 space-y-6">
          <section aria-labelledby="pg-3">
            <h2 id="pg-3" className="mb-3 text-sm font-semibold">3. CamResult</h2>
            {result ? <JsonViewer value={result} label="GET …/files/0/result" /> : <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">The result JSON appears when the job is done.</p>}
          </section>
          <section aria-labelledby="pg-4">
            <h2 id="pg-4" className="mb-3 text-sm font-semibold">Equivalent cURL</h2>
            <CodeBlock code={curl} label="Replace the placeholder with a key from API keys" />
          </section>
        </div>
      </div>
    </>
  );
}

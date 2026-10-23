import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { ApiError, upload } from "@/api/client";
import { useHealth, useUsage } from "@/api/hooks";
import type { CreatedJob } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { PageHeader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { inputStyles } from "@/components/ui/styles";
import { Alert, Card, Progress } from "@/components/ui/misc";
import { plural } from "@/lib/format";

import { FileDropzone } from "./FileDropzone";

export function NewAnalysisPage() {
  const { me } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const usage = useUsage();
  const health = useHealth();

  const [files, setFiles] = useState<File[]>([]);
  const [password, setPassword] = useState("");
  const [useOcr, setUseOcr] = useState(true);
  const [dpi, setDpi] = useState("300");
  const [bank, setBank] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  const suspended = me?.org_status === "suspended";
  const plan = usage.data?.plan;
  const limits = plan ? { maxFiles: plan.max_files_per_job, maxMb: plan.max_upload_mb } : null;
  const uploading = progress !== null;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!files.length) {
      setError("Add at least one PDF statement to analyse.");
      return;
    }
    setError(null);
    const form = new FormData();
    for (const f of files) form.append("files", f, f.name);
    if (password) form.append("password", password);
    form.append("use_ocr", String(useOcr));
    form.append("dpi", dpi);
    if (bank.trim()) form.append("bank", bank.trim());

    abortRef.current = new AbortController();
    setProgress(0);
    try {
      const job = await upload<CreatedJob>("/api/v1/jobs", form, setProgress, abortRef.current.signal);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success(`${plural(job.files, "statement")} queued for analysis`);
      navigate(`/app/statements/${job.job_id}`);
    } catch (err) {
      if ((err as Error).name === "AbortError") setError("Upload cancelled. Nothing was sent for analysis.");
      else
        setError(
          err instanceof ApiError || err instanceof Error ? err.message : "The upload failed. Try again.",
        );
      setProgress(null);
    }
  };

  return (
    <>
      <PageHeader
        title="New analysis"
        description="Upload bank statements to extract every transaction, check the running balance and score the account."
      />

      <form onSubmit={onSubmit} noValidate className="space-y-6">
        {suspended && (
          <Alert tone="warn" title="Uploads are paused">
            Your organisation is suspended, so new statements can't be analysed.
          </Alert>
        )}
        {health.data?.ocr_warning && useOcr && (
          <Alert tone="info" title="Scanned statements may wait">
            {health.data.ocr_warning} Digital PDFs are not affected.
          </Alert>
        )}
        {usage.isError && (
          <Alert tone="info">
            Your plan's limits couldn't be loaded; they'll be checked when you upload.
          </Alert>
        )}

        <FileDropzone files={files} onChange={setFiles} limits={limits} disabled={uploading || suspended} />

        <Card className="p-5">
          <fieldset disabled={uploading || suspended} className="grid gap-5 sm:grid-cols-2">
            <legend className="mb-4 text-base font-semibold">Options</legend>
            <Field
              label="PDF password (if the statements are protected)"
              type="password"
              autoComplete="off"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              hint="Used for every file in this upload, then discarded — it is never stored."
            />
            <Field
              label="Bank name (optional)"
              value={bank}
              onChange={(e) => setBank(e.target.value)}
              maxLength={100}
              hint="Only needed when the statement shows the bank's name as a logo."
            />
            <div className="flex items-start gap-3 sm:col-span-2">
              <input
                id="use_ocr"
                type="checkbox"
                checked={useOcr}
                onChange={(e) => setUseOcr(e.target.checked)}
                className="mt-0.5 size-5 shrink-0 accent-(--primary)"
                aria-describedby="use_ocr-hint"
              />
              <div>
                <label htmlFor="use_ocr" className="text-sm font-medium">
                  Read scanned pages (OCR)
                </label>
                <p id="use_ocr-hint" className="text-xs text-muted">
                  Needed for photographed or scanned statements. Scanned pages take longer.
                </p>
              </div>
            </div>
            {useOcr && (
              <div className="space-y-1.5">
                <label htmlFor="dpi" className="block text-sm font-medium">
                  Scan quality
                </label>
                <select id="dpi" value={dpi} onChange={(e) => setDpi(e.target.value)} className={inputStyles}>
                  <option value="200">Faster (200 dpi)</option>
                  <option value="300">Standard (300 dpi)</option>
                  <option value="400">Small print (400 dpi)</option>
                </select>
              </div>
            )}
          </fieldset>
        </Card>

        {error && <Alert tone="break">{error}</Alert>}

        {uploading && (
          <div className="space-y-2" aria-live="polite">
            <Progress value={progress} label="Upload progress" />
            <p className="text-sm text-muted">
              {progress < 100 ? `Uploading… ${progress}%` : "Checking files and queueing them for analysis…"}
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={uploading} disabled={suspended}>
            {files.length ? `Analyse ${plural(files.length, "statement")}` : "Analyse statements"}
          </Button>
          {uploading && progress < 100 && (
            <Button variant="secondary" onClick={() => abortRef.current?.abort()}>
              Cancel upload
            </Button>
          )}
        </div>
      </form>
    </>
  );
}

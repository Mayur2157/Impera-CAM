// Shapes from agentic/features/customer-portal/api-contract.md — change both together.

export type Status = "queued" | "running" | "done" | "error";
export type Role = "owner" | "admin" | "member";

export interface Me {
  id: string;
  email: string;
  role: Role;
  is_superuser: boolean;
  tenant_id: string;
  org_name: string;
  org_status: "active" | "suspended";
  plan: string;
}

export interface TokenOut {
  access_token: string;
  token_type: "bearer";
}

export interface FileSummary {
  rows: number;
  chain: number;
  flagged: number;
  is_partial: boolean;
  completeness: string;
  filename: string;
  info: { bank: string | null };
  score?: number | null;
  risk_rating?: string | null;
}

export interface FileTask {
  id: string;
  name: string;
  status: Status;
  progress: number;
  message: string | null;
  error: string | null;
  result: FileSummary | null;
}

export interface Job {
  id: string;
  status: Status;
  created: string;
  use_ocr: boolean;
  dpi: number;
  bank: string | null;
  progress: number;
  files: FileTask[];
}

export interface Page<T> {
  items: T[];
  total: number;
}

export interface CreatedJob {
  job_id: string;
  files: number;
}

export interface UsageReport {
  plan: {
    name: string;
    max_files_per_job: number;
    max_upload_mb: number;
    monthly_statement_quota: number | null;
  };
  totals: { statements: number; pages: number };
  month_to_date: { statements: number; pages: number };
  series: { key: string; label: string; statements: number; pages: number }[];
}

export interface Health {
  status: "ok" | "degraded";
  db: string;
  redis: string;
  queues: Record<string, number>;
  workers: Record<string, number>;
  ocr_device: string | null;
  ocr_warning: string | null;
}

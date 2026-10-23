// Types for every shape in the API CONTRACT. Do not add fields outside it.

export type Status = "queued" | "running" | "done" | "error";
export type Role = "owner" | "admin" | "member";
export type OrgStatus = "active" | "suspended";

export interface TokenResponse { access_token: string; token_type: "bearer" }
export interface RegisterRequest { email: string; password: string; org_name: string; accept_terms: true }
export interface LoginRequest { username: string; password: string }
export interface Me {
  id: string; email: string; role: Role; is_superuser: boolean;
  tenant_id: string; org_name: string; org_status: OrgStatus; plan: string;
}
export interface ChangePasswordRequest { current_password: string; new_password: string }
export interface AcceptInviteRequest { token: string; password: string }
export interface InviteInfo { email: string; org_name: string; role: Role; expires_at: string }

export interface FileSummary {
  rows: number; chain: number; flagged: number; is_partial: boolean; completeness: string;
  filename: string; info: { bank: string }; score?: number; risk_rating?: RiskRating;
}
export type RiskRating = "PRIME" | "MODERATE-LOW" | "MODERATE" | "HIGH" | "VERY HIGH";
export interface FileTask {
  id: string; name: string; status: Status; progress: number; message: string;
  error: string | null; result: FileSummary | null;
}
export interface Job {
  id: string; status: Status; created: string; use_ocr: boolean; dpi: 200 | 300 | 400;
  bank: string | null; progress: number; files: FileTask[];
}
export type JobSummary = Job;
export interface CreateJobResponse { job_id: string; files: FileTask[] }
export interface Paged<T> { items: T[]; total: number }

export type ScoreKey =
  | "cashflow_margin_score" | "liquidity_abb_score" | "debt_capacity_score" | "emi_regularity_score"
  | "facility_compliance_score" | "bounce_behavior_score" | "transaction_risk_score" | "income_concentration_score";

export interface CamResult {
  file: FileSummary;
  account: {
    account_holder: string; bank_name: string; account_number_masked: string; facility_type: string;
    account_type: string; customer_persona: string; analysis_period: string; months_count: number;
    data_sufficiency: string;
  };
  score: {
    credit_score_index: number; risk_rating: RiskRating; score_before_caps: number;
    scorecard_breakdown: Record<ScoreKey, number | null>;
    max_points: Record<ScoreKey, number>;
    hard_cap_rules_applied: string[]; strengths: string[]; red_flags: string[]; unscored_reasons: string[];
  };
  metrics: {
    abb: number; monthly_eligible_income: number; net_cash_flow: number; total_monthly_emi: number;
    total_monthly_debt_service: number; foir_percentage: number | null; dscr: number | null; dscr_display: string;
    outward_bounces: number; loan_emi_bounces_count: number; cash_share_of_inflows_pct: number;
    average_limit_utilization_pct: number | null; gross_bank_inflows: number; gross_debits: number;
  };
  monthly: { month: string; inflow: number; outflow: number; net: number; closing_balance: number; abb: number }[];
  income: {
    eligible: { category: string; count: number; amount: number; monthly: number }[];
    excluded: { category: string; count: number; amount: number; reason: string }[];
  };
  debt: { loans: { lender: string; monthly_emi: number; installments: number; total_paid: number; last_paid: string; status: string; linked_bounces: number }[] };
  counterparties: {
    top_inward: Counterparty[]; top_outward: Counterparty[];
  };
  risk: {
    bounces: { date: string; type: string; amount: number; narration: string }[];
    structuring: { date: string; amount: number; confidence: number }[];
    rapid_in_out: { credit_date: string; debit_date: string; amount: number; confidence: number }[];
  };
  validation: { strategy: string; chain_mode: string; pass_rate: number; flagged_rows: { row: number; issue: string }[] };
}
export interface Counterparty { name: string; count: number; total: number; share_pct: number }

export interface Txn {
  sno: number; date: string; value_date: string; narration: string; reference: string;
  debit: number | null; credit: number | null; balance: number; category: string; counterparty: string;
  status: "OK" | "CHECK"; page: number;
}

export type Scope = "jobs:read" | "jobs:write";
export interface ApiKey {
  id: string; name: string; prefix: string; scopes: Scope[]; created_at: string; created_by: string;
  last_used_at: string | null; revoked_at: string | null; requests_30d: number;
}
export interface CreatedApiKey extends ApiKey { secret: string }

export interface Usage {
  plan: { name: string; max_files_per_job: number; max_upload_mb: number; monthly_statement_quota: number | null };
  totals: { statements: number; pages: number };
  series: { key: string; label: string; statements: number; pages: number }[];
}

export interface Org {
  id: string; name: string; plan: string; status: OrgStatus; max_files: number; max_upload_mb: number;
  created_at: string; retention_hours: number;
}
export interface Member { id: string; email: string; role: Role; is_active: boolean; created_at: string; last_login_at: string | null }
export interface Invite { id: string; email: string; role: Role; created_at: string; expires_at: string }
export interface CreatedInvite { id: string; invite_url: string; expires_at: string }

export interface AdminOverview {
  tenants: number; active_tenants_30d: number; statements_30d: number; pages_30d: number;
  queue: { cpu: number; ocr: number }; workers: { cpu: number; ocr: number }; ocr_device: string;
}
export interface AdminTenant {
  id: string; name: string; plan: string; status: OrgStatus; users: number;
  statements_30d: number; pages_30d: number; created_at: string;
}
export interface AdminTenantDetail extends AdminTenant {
  max_files: number; max_upload_mb: number; monthly_statement_quota: number | null;
  members: Member[]; usage: Usage["series"]; api_keys: ApiKey[];
}
export interface AdminTenantPatch {
  plan?: string; max_files?: number; max_upload_mb?: number; monthly_statement_quota?: number | null; status?: OrgStatus;
}

export interface Health {
  status: string; db: string; redis: string; queues: { cpu: number; ocr: number };
  workers: { cpu: number; ocr: number }; ocr_device: string; ocr_warning: string | null;
}

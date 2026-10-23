// Seeded, obviously fake Indian data. Built lazily (no module-scope side effects).
import type {
  ApiKey, CamResult, FileSummary, FileTask, Invite, Job, Member, Org, Txn, AdminTenant, Role, RiskRating,
} from "../types";

export interface MockUser { id: string; email: string; password: string; role: Role; is_superuser: boolean; tenant_id: string; is_active: boolean; created_at: string; last_login_at: string | null }
export interface MockTenant extends Org { monthly_statement_quota: number | null }

export interface MockDb {
  users: MockUser[];
  tenants: MockTenant[];
  jobs: (Job & { tenant_id: string; startedAt?: number })[];
  keys: (ApiKey & { tenant_id: string })[];
  invites: (Invite & { tenant_id: string; token: string })[];
  otherTenants: AdminTenant[];
  seq: number;
}

function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

const daysAgo = (d: number, h = 0) => new Date(Date.now() - d * 86400000 - h * 3600000).toISOString();

export function summary(name: string, i: number): FileSummary {
  const grades: RiskRating[] = ["PRIME", "MODERATE-LOW", "MODERATE"];
  const chains = [1, 0.9934, 0.962];
  return {
    rows: [412, 1287, 238][i % 3]!, chain: chains[i % 3]!, flagged: [0, 8, 9][i % 3]!,
    is_partial: i % 3 === 2, completeness: i % 3 === 2 ? "Pages 1–6 of 9 read; last 3 pages unreadable" : "All pages read",
    filename: name, info: { bank: ["HDFC Bank", "State Bank of India", "ICICI Bank"][i % 3]! },
    score: [82, 64, 51][i % 3]!, risk_rating: grades[i % 3]!,
  };
}

export function doneFile(id: string, name: string, i: number): FileTask {
  return { id, name, status: "done", progress: 100, message: "done", error: null, result: summary(name, i) };
}

export function seed(): MockDb {
  const tenant: MockTenant = {
    id: "t_demo", name: "Demo Lending Pvt Ltd", plan: "Growth", status: "active",
    max_files: 5, max_upload_mb: 25, created_at: daysAgo(120), retention_hours: 72, monthly_statement_quota: 2000,
  };
  const users: MockUser[] = [
    { id: "u_owner", email: "demo@impera.test", password: "demo1234", role: "owner", is_superuser: false, tenant_id: "t_demo", is_active: true, created_at: daysAgo(120), last_login_at: daysAgo(0, 2) },
    { id: "u_member", email: "member@impera.test", password: "demo1234", role: "member", is_superuser: false, tenant_id: "t_demo", is_active: true, created_at: daysAgo(60), last_login_at: daysAgo(3) },
    { id: "u_staff", email: "staff@impera.test", password: "demo1234", role: "owner", is_superuser: true, tenant_id: "t_demo", is_active: true, created_at: daysAgo(300), last_login_at: daysAgo(1) },
  ];
  const jobs: MockDb["jobs"] = [
    { id: "job_7Hq2", tenant_id: "t_demo", status: "done", created: daysAgo(1, 3), use_ocr: true, dpi: 300, bank: null, progress: 100,
      files: [doneFile("f1", "demo_traders_hdfc_apr-sep.pdf", 0)] },
    { id: "job_4Lm9", tenant_id: "t_demo", status: "done", created: daysAgo(2, 5), use_ocr: true, dpi: 300, bank: null, progress: 100,
      files: [doneFile("f1", "sharma_textiles_sbi_fy24.pdf", 1), doneFile("f2", "sharma_textiles_sbi_q1.pdf", 0)] },
    { id: "job_2Ka5", tenant_id: "t_demo", status: "done", created: daysAgo(5), use_ocr: false, dpi: 300, bank: "ICICI Bank", progress: 100,
      files: [doneFile("f1", "example_agro_icici_scan.pdf", 2)] },
    { id: "job_9Xr1", tenant_id: "t_demo", status: "running", created: new Date().toISOString(), use_ocr: true, dpi: 300, bank: null, progress: 0, startedAt: Date.now(),
      files: [
        { id: "f1", name: "sample_enterprises_axis.pdf", status: "queued", progress: 0, message: "waiting for OCR worker", error: null, result: null },
        { id: "f2", name: "sample_enterprises_kotak.pdf", status: "queued", progress: 0, message: "queued", error: null, result: null },
      ] },
  ];
  const keys: MockDb["keys"] = [
    { id: "k1", tenant_id: "t_demo", name: "LOS production", prefix: "icam_live_Ab12", scopes: ["jobs:read", "jobs:write"], created_at: daysAgo(40), created_by: "demo@impera.test", last_used_at: daysAgo(0, 1), revoked_at: null, requests_30d: 1842 },
    { id: "k2", tenant_id: "t_demo", name: "Staging test", prefix: "icam_live_Zx9P", scopes: ["jobs:read"], created_at: daysAgo(20), created_by: "demo@impera.test", last_used_at: null, revoked_at: null, requests_30d: 0 },
  ];
  const r = rng(7);
  const otherTenants: AdminTenant[] = [
    { id: "t_demo", name: tenant.name, plan: tenant.plan, status: "active", users: 3, statements_30d: 0, pages_30d: 0, created_at: tenant.created_at },
    ...["Example Finance Co-op Bank", "Sample Capital NBFC", "Test DSA Partners LLP", "Placeholder Microfin Ltd"].map((name, i) => ({
      id: `t_${i + 2}`, name, plan: ["Starter", "Growth", "Enterprise", "Starter"][i]!, status: (i === 3 ? "suspended" : "active") as AdminTenant["status"],
      users: 1 + Math.floor(r() * 12), statements_30d: Math.floor(r() * 900), pages_30d: Math.floor(r() * 9000), created_at: daysAgo(30 + i * 40),
    })),
  ];
  return { users, tenants: [tenant], jobs, keys, invites: [
    { id: "inv1", tenant_id: "t_demo", email: "analyst@impera.test", role: "member", created_at: daysAgo(1), expires_at: daysAgo(-6), token: "demo-invite-token" },
  ], otherTenants, seq: 100 };
}

export function members(db: MockDb, tenantId: string): Member[] {
  return db.users.filter((u) => u.tenant_id === tenantId && !u.is_superuser).map((u) => ({
    id: u.id, email: u.email, role: u.role, is_active: u.is_active, created_at: u.created_at, last_login_at: u.last_login_at,
  }));
}

export function usageSeries(days: number, seedN = 3) {
  const r = rng(seedN);
  const out = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000);
    const st = Math.floor(10 + r() * 40);
    const key = d.toISOString().slice(0, 10);
    out.push({ key, label: key, statements: st, pages: st * Math.floor(6 + r() * 10) });
  }
  return out;
}

export function camResult(file: FileSummary, i: number): CamResult {
  const months = ["2024-04", "2024-05", "2024-06", "2024-07", "2024-08", "2024-09"];
  const r = rng(11 + i);
  const monthly = months.map((m) => {
    const inflow = Math.round(1800000 + r() * 900000);
    const outflow = Math.round(inflow * (0.82 + r() * 0.2));
    return { month: m, inflow, outflow, net: inflow - outflow, closing_balance: Math.round(250000 + r() * 400000), abb: Math.round(300000 + r() * 250000) };
  });
  const score = file.score ?? 70;
  return {
    file,
    account: {
      account_holder: ["Demo Traders Pvt Ltd", "Sharma Textiles (Sample)", "Example Agro Industries"][i % 3]!,
      bank_name: file.info.bank, account_number_masked: `••••${4821 + i}`, facility_type: i % 2 ? "Cash Credit" : "Current Account",
      account_type: "Current", customer_persona: "MSME trader", analysis_period: "01 Apr 2024 – 30 Sep 2024", months_count: 6,
      data_sufficiency: file.is_partial ? "Partial" : "Sufficient",
    },
    score: {
      credit_score_index: score, risk_rating: file.risk_rating ?? "MODERATE", score_before_caps: i % 3 === 2 ? score + 9 : score,
      scorecard_breakdown: {
        cashflow_margin_score: 16, liquidity_abb_score: 11, debt_capacity_score: 12, emi_regularity_score: 9,
        facility_compliance_score: i % 2 ? 10 : null, bounce_behavior_score: i % 3 === 0 ? 10 : 5, transaction_risk_score: 8, income_concentration_score: 3,
      },
      max_points: { cashflow_margin_score: 20, liquidity_abb_score: 15, debt_capacity_score: 15, emi_regularity_score: 10, facility_compliance_score: 15, bounce_behavior_score: 10, transaction_risk_score: 10, income_concentration_score: 5 },
      hard_cap_rules_applied: i % 3 === 2 ? ["Partial statement: score capped at 55"] : [],
      strengths: ["Consistent monthly inflows", "No EMI bounces in 6 months"],
      red_flags: i % 3 === 0 ? [] : ["2 outward cheque bounces", "High cash share of inflows"],
      unscored_reasons: i % 2 ? [] : ["Facility compliance: no OD/CC limit found on a current account"],
    },
    metrics: {
      abb: 412500, monthly_eligible_income: 1950000, net_cash_flow: 286000, total_monthly_emi: 145000, total_monthly_debt_service: 162000,
      foir_percentage: 38.4, dscr: 1.76, dscr_display: "1.76×", outward_bounces: i % 3 === 0 ? 0 : 2, loan_emi_bounces_count: 0,
      cash_share_of_inflows_pct: 18.2, average_limit_utilization_pct: i % 2 ? 72.5 : null, gross_bank_inflows: 13240000, gross_debits: 12954000,
    },
    monthly,
    income: {
      eligible: [
        { category: "Business receipts", count: 214, amount: 9800000, monthly: 1633333 },
        { category: "UPI collections", count: 612, amount: 1900000, monthly: 316667 },
      ],
      excluded: [
        { category: "Self transfers", count: 12, amount: 1100000, reason: "Transfer between own accounts" },
        { category: "Loan disbursal", count: 1, amount: 440000, reason: "Borrowed funds are not income" },
      ],
    },
    debt: { loans: [
      { lender: "Sample Finance Ltd", monthly_emi: 85000, installments: 6, total_paid: 510000, last_paid: "2024-09-05", status: "Regular", linked_bounces: 0 },
      { lender: "Example Bank Business Loan", monthly_emi: 60000, installments: 6, total_paid: 360000, last_paid: "2024-09-10", status: "Regular", linked_bounces: 0 },
    ] },
    counterparties: {
      top_inward: [
        { name: "Demo Distributors", count: 48, total: 3200000, share_pct: 24.2 },
        { name: "Sample Retail Pvt Ltd", count: 31, total: 2100000, share_pct: 15.9 },
        { name: "Test Wholesale Co", count: 22, total: 1300000, share_pct: 9.8 },
      ],
      top_outward: [
        { name: "Example Suppliers", count: 40, total: 4100000, share_pct: 31.6 },
        { name: "Placeholder Logistics", count: 18, total: 900000, share_pct: 6.9 },
      ],
    },
    risk: {
      bounces: i % 3 === 0 ? [] : [
        { date: "2024-06-14", type: "Outward cheque return", amount: 45000, narration: "CHQ RTN INSUFF FUNDS 004512" },
        { date: "2024-08-02", type: "Outward cheque return", amount: 28000, narration: "CHQ RTN INSUFF FUNDS 004588" },
      ],
      structuring: [{ date: "2024-07-19", amount: 49000, confidence: 0.62 }],
      rapid_in_out: [{ credit_date: "2024-05-03", debit_date: "2024-05-03", amount: 500000, confidence: 0.81 }],
    },
    validation: {
      strategy: "running-balance", chain_mode: "strict", pass_rate: file.chain,
      flagged_rows: Array.from({ length: file.flagged }, (_, k) => ({ row: 40 + k * 17, issue: "Printed balance differs from computed balance" })),
    },
  };
}

export function transactions(total: number, flaggedRows: number[], offset: number, limit: number): Txn[] {
  const r = rng(99);
  const out: Txn[] = [];
  let bal = 325000;
  const cats = ["Business receipt", "Supplier payment", "UPI", "EMI", "Cash deposit", "Charges"];
  for (let i = 0; i < Math.min(total, offset + limit); i++) {
    const credit = r() > 0.5 ? Math.round(r() * 90000) : null;
    const debit = credit ? null : Math.round(r() * 70000);
    bal = bal + (credit ?? 0) - (debit ?? 0);
    if (i < offset) continue;
    const d = new Date(2024, 3, 1 + Math.floor(i / 3));
    const iso = d.toISOString().slice(0, 10);
    out.push({
      sno: i + 1, date: iso, value_date: iso, narration: credit ? `NEFT CR DEMO DISTRIBUTORS ${1000 + i}` : `IMPS DR EXAMPLE SUPPLIERS ${2000 + i}`,
      reference: `REF${100000 + i}`, debit, credit, balance: bal, category: cats[i % cats.length]!,
      counterparty: credit ? "Demo Distributors" : "Example Suppliers", status: flaggedRows.includes(i + 1) ? "CHECK" : "OK", page: 1 + Math.floor(i / 40),
    });
  }
  return out;
}

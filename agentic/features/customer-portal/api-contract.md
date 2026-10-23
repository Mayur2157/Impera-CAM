# API contract — portal and public API v1

> Status: approved (plan approval, 2026-10-16) · Last updated: 2026-10-23
> The single source of truth shared by the portal frontend (`frontend/`) and the FastAPI backend.
> A change here must be made in the backend and the frontend's `src/api/types.ts` together.

## Implementation status (2026-10-23)

| Area | Status |
|---|---|
| `POST /api/auth/register`, `/login`, `GET /me` | **Done**: `me` per contract; register requires `accept_terms` and makes the creator `owner`; login records `last_login_at` |
| `/api/v1/jobs*` (list with `offset` and `{items,total}`, job, result, transactions, download) | **Done**, for Bearer JWT and `X-API-Key` (scopes, revoke, suspension, per-key rate limit). The unversioned `/api/jobs*` stay for the legacy page |
| `GET /api/v1/usage` | **Done** |
| `GET /api/health` | Exists |
| API keys, org, members, invites, change-password, accept-invite, super-admin | Not started (portal phases 5–6) |

Changes made while implementing (2026-10-23):
- `score.unscored_reasons` is a map `{component_key: reason}`, not a list, so each scorecard bar can show why it was not scored.
- `metrics` also carries `income_metric_label` and `debt_ratio_label`. A business account's "FOIR" is a debt-service-to-revenue ratio, and the UI must label it as the CAM does.
- `usage` also returns `month_to_date: {statements, pages}`, for the quota bar whatever range is chosen.
- The holder's own account number is masked inside narrations too; some banks (HDFC) print it there.
- Results of files processed before 2026-10-23 have no analysis JSON: `…/result` and `…/transactions` answer 410 for them.

## Contract

```text
Base: {VITE_API_BASE_URL}. JSON unless noted. Portal auth: Bearer JWT.
Machine auth (customers' servers): header "X-API-Key: icam_live_…" on /api/v1/jobs* only.
Status values for jobs and files: "queued" | "running" | "done" | "error".

AUTH
POST /api/auth/register  {email, password(min 8), org_name, accept_terms: true}
     → 201 {access_token, token_type:"bearer"}         409 email exists
POST /api/auth/login     form-urlencoded username=<email>&password=…
     → {access_token, token_type}                       401 wrong; 429 too many
GET  /api/auth/me → {id, email, role:"owner"|"admin"|"member", is_superuser:boolean,
     tenant_id, org_name, org_status:"active"|"suspended", plan}
POST /api/auth/change-password {current_password, new_password} → 204
POST /api/auth/accept-invite {token, password} → {access_token, token_type}
GET  /api/auth/invite/{token} → {email, org_name, role, expires_at}   404 if invalid

STATEMENT JOBS  (portal and API keys)
POST /api/v1/jobs   multipart: files[] (PDF, ≤ plan.max_files per job, ≤ plan.max_upload_mb each),
     password?(PDF password), use_ocr?(bool, default true), dpi?(200|300|400, default 300),
     bank?(string, only if the PDF shows the bank as a logo)
     → 201 {job_id, files}
     400 not a PDF / wrong PDF password / too big;  429 too many files still processing;
     503 queue unavailable
GET  /api/v1/jobs?limit=20&offset=0 → {items:[JobSummary], total}
GET  /api/v1/jobs/{job_id} → Job
GET  /api/v1/jobs/{job_id}/files/{index}/result → CamResult        409 not ready; 410 expired
GET  /api/v1/jobs/{job_id}/files/{index}/transactions?offset=0&limit=100
     → {items:[Txn], total}
GET  /api/v1/jobs/{job_id}/files/{index}/download → .xlsx file (binary; use blob download)

Job = {id, status, created, use_ocr, dpi, bank, progress(0-100),
       files:[FileTask]}
JobSummary = Job without file results except FileSummary
FileTask = {id, name, status, progress, message ("waiting for OCR worker", "reading pages", …),
            error, result: FileSummary|null}
FileSummary = {rows, chain(0-1), flagged, is_partial, completeness, filename,
               info:{bank}, score?, risk_rating?}
CamResult = {
  file: FileSummary,
  account: {account_holder, bank_name, account_number_masked, facility_type, account_type,
            customer_persona, analysis_period, months_count, data_sufficiency},
  score: {credit_score_index(0-100), risk_rating, score_before_caps,
          scorecard_breakdown:{cashflow_margin_score, liquidity_abb_score, debt_capacity_score,
            emi_regularity_score, facility_compliance_score, bounce_behavior_score,
            transaction_risk_score, income_concentration_score}   // each number|null (null = not scored)
          max_points:{cashflow_margin_score:20, liquidity_abb_score:15, debt_capacity_score:15,
            emi_regularity_score:10, facility_compliance_score:15, bounce_behavior_score:10,
            transaction_risk_score:10, income_concentration_score:5},
          hard_cap_rules_applied:[string], strengths:[string], red_flags:[string],
          unscored_reasons:{<scorecard key>: string}},
  metrics: {abb, monthly_eligible_income, net_cash_flow, total_monthly_emi,
            total_monthly_debt_service, foir_percentage|null, dscr|null, dscr_display,
            outward_bounces, loan_emi_bounces_count, cash_share_of_inflows_pct,
            average_limit_utilization_pct|null, gross_bank_inflows, gross_debits,
            income_metric_label, debt_ratio_label},
  monthly: [{month:"2024-04", inflow, outflow, net, closing_balance, abb}],
  income: {eligible:[{category, count, amount, monthly}], excluded:[{category, count, amount, reason}]},
  debt: {loans:[{lender, monthly_emi, installments, total_paid, last_paid, status, linked_bounces}]},
  counterparties: {top_inward:[{name, count, total, share_pct}], top_outward:[…same]},
  risk: {bounces:[{date, type, amount, narration}], structuring:[{date, amount, confidence}],
         rapid_in_out:[{credit_date, debit_date, amount, confidence}]},
  validation: {strategy, chain_mode, pass_rate, flagged_rows:[{row, issue}]}
}
Txn = {sno, date, value_date, narration, reference, debit|null, credit|null, balance,
       category, counterparty, status:"OK"|"CHECK", page}

API KEYS  (owner/admin)
GET    /api/v1/api-keys → [{id, name, prefix:"icam_live_Ab12", scopes:["jobs:read","jobs:write"],
        created_at, created_by, last_used_at|null, revoked_at|null, requests_30d}]
POST   /api/v1/api-keys {name, scopes} → 201 {…key, secret:"icam_live_<40 chars>"}
       // secret is returned ONCE; never again
DELETE /api/v1/api-keys/{id} → 204 (revokes immediately)

USAGE  (all roles)
GET /api/v1/usage?from=YYYY-MM-DD&to=YYYY-MM-DD&group_by=day|api_key|user
    → {plan:{name, max_files_per_job, max_upload_mb, monthly_statement_quota|null},
       totals:{statements, pages}, month_to_date:{statements, pages},
       series:[{key, label, statements, pages}]}
    // day: every date in the range, zeros included; api_key: key "portal" / label "Portal"
    //      for jobs sent from the portal; range ≤ 366 days, default the last 30

ORGANISATION
GET   /api/v1/org → {id, name, plan, status, max_files, max_upload_mb, created_at,
                     retention_hours}
PATCH /api/v1/org {name} → org            (owner/admin)
GET   /api/v1/org/members → [{id, email, role, is_active, created_at, last_login_at}]
PATCH /api/v1/org/members/{id} {role?, is_active?} → member   (owner/admin; cannot demote owner)
DELETE /api/v1/org/members/{id} → 204
GET   /api/v1/org/invites → [{id, email, role, created_at, expires_at}]
POST  /api/v1/org/invites {email, role:"admin"|"member"} → 201 {id, invite_url, expires_at}
      // no email is sent in v1: show invite_url with a Copy button
DELETE /api/v1/org/invites/{id} → 204

SUPER-ADMIN  (is_superuser only)
GET   /api/v1/admin/overview → {tenants, active_tenants_30d, statements_30d, pages_30d,
                                queue:{cpu, ocr}, workers:{cpu, ocr}, ocr_device}
GET   /api/v1/admin/tenants?query=&status=&limit=50&offset=0
      → {items:[{id, name, plan, status, users, statements_30d, pages_30d, created_at}], total}
GET   /api/v1/admin/tenants/{id} → tenant + members + usage series (30 days) + api keys (no secrets)
PATCH /api/v1/admin/tenants/{id} {plan?, max_files?, max_upload_mb?,
      monthly_statement_quota?, status?:"active"|"suspended"} → tenant
POST  /api/v1/admin/api-keys/{id}/revoke → 204

PUBLIC
GET /api/health → {status, db, redis, queues:{cpu, ocr}, workers:{cpu, ocr}, ocr_device, ocr_warning}
```

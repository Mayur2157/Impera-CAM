# Lovable prompt pack — Impera CAM portal

> Status: approved (plan approval, 2026-10-16) · Last updated: 2026-10-16
> Written for: whoever builds the frontend in Lovable.

## How to use

1. Create a new Lovable project. Open **Project settings → Knowledge** and paste the
   **Lovable Knowledge** block, then the **API CONTRACT** block, below it.
2. Send **Prompt 1**. Check the result works in mock mode (log in as
   `demo@impera.test` / `demo1234`) before sending the next prompt.
3. Send Prompts 2 → 7 one at a time, checking each one. If Lovable drifts (adds
   Supabase, invents an endpoint), reply: "Follow the Knowledge: no Supabase; use only
   endpoints in the API CONTRACT."
4. Connect the project to GitHub, so the code can be integrated into this repository
   (see `phases.md`).

The backend endpoints marked new in `api-contract.md` don't exist yet. The frontend
works fully in mock mode until they're built.

### Lovable Knowledge (project instructions — paste once, before Prompt 1)

```text
PROJECT: Impera CAM — customer portal + developer console for a B2B SaaS that turns
Indian bank-statement PDFs into a verified Credit Appraisal Memo (CAM). Customers are
lenders (NBFCs, banks, co-operative banks, DSAs). They use the portal to upload
statements and read results, and they create API keys to call our REST API from their
own loan systems (like Google AI Studio keys for Gemini).

HARD TECH RULES
- React + Vite + TypeScript (strict) + Tailwind + shadcn/ui + lucide-react icons,
  React Router, TanStack Query, react-hook-form + zod, Recharts for charts.
- DO NOT use Supabase or any Lovable Cloud backend/auth/database. There is no
  Supabase. ALL data comes from our existing REST API (FastAPI) described in the
  API CONTRACT below. Never invent endpoints or fields outside the contract.
- One typed API client: src/lib/api/client.ts. Base URL from import.meta.env.VITE_API_BASE_URL.
  Every request goes through it. Types for every request/response live in src/lib/api/types.ts.
- MOCK MODE: when VITE_USE_MOCKS === "true", the client answers from an in-memory mock
  server (src/lib/api/mocks/) that implements EVERY contract endpoint with realistic
  but obviously fake Indian data (fake names like "Demo Traders Pvt Ltd", masked
  account numbers, INR amounts). Mocks simulate job progress over ~10 s, 401/403/429
  errors, and empty states. Default VITE_USE_MOCKS=true in the Lovable preview.
- Auth: portal users send "Authorization: Bearer <jwt>". Keep the token in memory and
  sessionStorage (not localStorage). On any 401: clear the token, go to /login with
  ?next=. On 403: show an inline "You don't have permission" state, never a blank page.
- Errors from the API are JSON {"detail": string} or, for validation (422),
  {"detail": [{"loc": [...], "msg": string}]}. Show the message to the user. On 429
  read the Retry-After header and say how long to wait.
- Money: Indian format with ₹ and lakh/crore grouping via Intl.NumberFormat("en-IN").
  Dates: "dd MMM yyyy". Times in the user's local zone. All figures use tabular numbers.
- Privacy (India DPDP Act): never put personal data in URLs, page titles, analytics or
  console logs. Show bank account numbers masked (••••1234). PAN masked (ABCDE••••F).
  The signup form has an unticked consent checkbox linking to /privacy and /terms.
- Quality floor on EVERY screen: loading skeleton, empty state with a next action,
  error state with retry, success state. Keyboard accessible, visible focus, labels on
  all inputs, aria-live for progress and toasts, WCAG 2.1 AA contrast, works from
  360 px wide to desktop. Respect prefers-reduced-motion.

DESIGN DIRECTION — "Ledger, modernised"
- Calm, trustworthy fintech. Feels like a precise accounts book, not a crypto dashboard.
- Palette tokens (CSS variables, light + dark):
  paper #fbfbf9 / dark #0f1419 (background), panel #ffffff / #161d24, ink #16202a /
  #e6edf3 (text), muted #5c6873 / #8b98a5, rule #dce0e4 / #2a333d (borders),
  primary (field blue) #2e4a6b / #7fa7d6, tie (verified green) #1f6f5c / #4cc39f,
  break (failed red) #a6402c / #ef7c63, warn amber #9a6700 / #e3b341.
- "tie" green means numerically verified; "break" red means failed verification —
  use them only for that meaning. Risk grades: PRIME / MODERATE-LOW = tie,
  MODERATE = warn, HIGH / VERY HIGH = break.
- Type: Inter for UI; a serif (Source Serif 4) only for big page headings;
  JetBrains Mono for keys, IDs, code. tabular-nums on every number.
- Radius 10px cards, 8px inputs. Hairline borders, very soft shadows. 8-pt spacing.
- Signature element: the "Balance check" badge — a pill showing the % of rows whose
  previous balance − debit + credit equals the printed balance (green at 100%, amber
  98–99.99%, red below).

ROLES (from GET /api/auth/me)
- owner/admin: everything in their organisation incl. API keys, members, settings.
- member: upload statements, view results, view usage. Cannot manage keys/members/settings.
- is_superuser = true (Impera staff): additionally sees the /admin console.
Hide what a role cannot do, and also handle 403 gracefully.

API CONTRACT: see the "API CONTRACT" document (pasted below / in Knowledge).
```

### API CONTRACT (paste into Lovable Knowledge too)

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
          unscored_reasons:[string]},
  metrics: {abb, monthly_eligible_income, net_cash_flow, total_monthly_emi,
            total_monthly_debt_service, foir_percentage|null, dscr|null, dscr_display,
            outward_bounces, loan_emi_bounces_count, cash_share_of_inflows_pct,
            average_limit_utilization_pct|null, gross_bank_inflows, gross_debits},
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
       totals:{statements, pages}, series:[{key, label, statements, pages}]}

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

### Prompt 1 — Foundation: design system, API client, mocks, auth, app shell

```text
Build the foundation of the Impera CAM portal following the Knowledge (tech rules,
design direction, API contract). Do not build feature pages yet beyond what's listed.

1. Design system: Tailwind theme + CSS variables for every palette token in light and
   dark mode (system default + toggle). Fonts Inter / Source Serif 4 / JetBrains Mono.
   Reusable components: Money (₹, en-IN), MaskedAccount, StatusPill (queued/running/
   done/error), BalanceCheckBadge (green 100%, amber ≥98%, red below), RiskGradeBadge,
   ScoreGauge (0–100 semicircle), EmptyState, ErrorState (with Retry), PageHeader,
   DataTable (sortable, paginated, keyboard accessible, collapses to cards < 640px),
   CopyButton, ConfirmDialog, Toasts with aria-live.
2. API layer: src/lib/api/client.ts (fetch wrapper: base URL, Bearer token, JSON/blob,
   error normalisation to {status, message, retryAfter}), src/lib/api/types.ts with a
   TypeScript type for EVERY contract shape, and TanStack Query hooks per endpoint.
3. Mock server (VITE_USE_MOCKS=true): implements every contract endpoint in memory with
   seeded fake data: 1 org "Demo Lending Pvt Ltd" (owner demo@impera.test / password
   "demo1234"), a member, a superuser staff@impera.test, 3 completed jobs, 1 running job
   whose progress advances over ~10 s, 2 API keys, 30 days of usage. Can be switched to
   return errors for testing (?mockError=429 etc.).
4. Auth pages: /login, /signup (org name, work email, password with strength meter,
   consent checkbox → /privacy, /terms), /invite/:token (accept invite: shows org + role,
   set password). Redirect to /app after login; preserve ?next=.
5. App shell for /app/*: left sidebar (Dashboard, Statements, API keys, Usage, Team,
   Settings, Docs; Admin shown only to superusers), top bar with org name, plan badge,
   user menu (Change password, Theme, Sign out). Collapsible on mobile. A banner when
   org_status is "suspended" (read-only). Route guards by role.
6. Public pages: / (landing: hero "Bank statements to a verified CAM in seconds",
   how it works in 3 steps, the balance-check proof explained, API code snippet,
   security/DPDP section, CTA), /pricing (plans display only, "Contact sales"),
   /privacy, /terms (placeholder legal text clearly marked DRAFT), 404 page.
```

### Prompt 2 — Statements: upload, live progress, history

```text
Build the Statements area using the contract (/api/v1/jobs*).

/app/statements/new — Upload:
- Drag-and-drop zone + file picker; PDF only; shows each file with size; enforce the
  plan's max files per job and max MB (from GET /api/v1/org) BEFORE upload with clear
  messages. Optional fields: PDF password (masked, with a note "never stored"),
  bank name (helper: only if the statement shows the bank as a logo), OCR toggle
  (default on), OCR quality select 200/300/400 dpi (300 recommended).
- Submit → POST multipart with upload progress bar; on 201 navigate to the job page.
  Map 400/429/503 to friendly inline errors.

/app/statements/:jobId — Job page:
- Header with created time, overall progress, status.
- One row/card per file: name, StatusPill, progress bar, live message
  ("waiting for OCR worker" shows a hint that scanned statements are queued for GPU OCR),
  and when done: rows, BalanceCheckBadge, flagged count, "Partial PDF" badge with the
  completeness text as tooltip, score + RiskGradeBadge, buttons "View CAM" and
  "Download Excel" (blob download, filename from result).
- Poll GET /api/v1/jobs/:id with backoff: 1 s, ×1.5 when nothing changes, max 3 s,
  reset on change; stop at done/error; pause when the tab is hidden.

/app/statements — History: DataTable of jobs (date, files, status, best balance check,
worst risk grade), search by file name client-side, pagination (limit/offset),
empty state with "Upload your first statement".
```

### Prompt 3 — CAM result view (the hero screen)

```text
Build /app/statements/:jobId/files/:index — the Credit Appraisal Memo for one statement,
from GET …/result and …/transactions. It must feel like a premium underwriting report.

Layout (tabs on desktop, stacked sections on mobile; sticky summary header):
- Summary header: account holder, bank, masked account, facility type, analysis period,
  data sufficiency; ScoreGauge with credit_score_index and RiskGradeBadge; "score before
  caps" when different; BalanceCheckBadge; Download Excel; Print/PDF (print stylesheet).
- Overview tab: KPI tiles (ABB, monthly eligible income, net cash flow, total monthly EMI,
  FOIR or DSCR — show dscr_display when DSCR is not meaningful, outward bounces, cash
  share of inflows, OD utilisation when present). Scorecard: 8 horizontal bars
  score/max_points; null = "Not scored" with the reason from unscored_reasons.
  Hard caps list (the binding one highlighted). Strengths (tie) and Red flags (break).
- Cash flow tab: Recharts monthly inflow vs outflow bars + closing balance/ABB line;
  table below with the same numbers.
- Income tab: eligible vs excluded inflows tables with reasons; donut by category.
- Debt tab: loans table (lender, EMI, instalments, total paid, last paid, status,
  linked bounces).
- Counterparties tab: top inward/outward with share bars.
- Risk tab: bounces, structuring alerts (confidence chips), rapid in-out.
- Transactions tab: server-paginated DataTable (date, narration, reference, debit, credit,
  balance, category, counterparty, status). CHECK rows highlighted in break colour with
  an explanation tooltip; filter "Only rows needing review"; category filter.
- Verification tab: strategy, chain mode, pass rate, flagged rows with issue text and a
  plain-English explanation of the balance check.
Every number uses Money/tabular nums. Handle 409 (still processing → link back to job)
and 410 (expired after retention → "resubmit the PDF").
```

### Prompt 4 — Developer console: API keys, docs, playground

```text
Build the developer experience, in the spirit of Google AI Studio's "Get API key".

/app/api-keys (owner/admin; members see a read-only explanation):
- Table: name, prefix (mono, e.g. icam_live_Ab12…), scopes chips, created by/at,
  last used (relative), requests in 30 days, status (Active/Revoked).
- "Create API key" dialog: name (required), scopes checkboxes (jobs:write = upload,
  jobs:read = status/results). On success show the secret ONCE in a modal: mono field,
  Copy button, warning "Store it now — you won't see it again", checkbox "I've copied it"
  required to close. Never keep the secret in state after closing.
- Revoke with ConfirmDialog typing the key name. Empty state explains what keys are for.

/app/docs — API documentation (static content, generated from the contract):
- Quickstart in 4 steps (create key → upload → poll → fetch result).
- Code tabs: cURL, Python (requests), Node (fetch), Java — upload with X-API-Key,
  polling loop with backoff, fetching CamResult, downloading xlsx.
- Reference for every /api/v1/jobs* endpoint: method, path, params, example request/
  response, error codes (400, 401, 403, 404, 409, 410, 429 + Retry-After, 503).
- Limits & retention section (values from GET /api/v1/org).
- Security best practices (keep keys server-side, rotate, revoke on leak).

/app/playground — "Try it": runs on the logged-in session (Bearer token) and never asks
the user to paste an API key secret. Upload a PDF, watch the raw JSON of each poll, then
show the CamResult JSON in a collapsible JSON viewer with copy, next to the equivalent
cURL command using a placeholder key.
```

### Prompt 5 — Dashboard, usage, team, settings

```text
Build:
/app (Dashboard): greeting + org; KPI tiles (statements this month, pages this month,
  vs plan quota with progress bar, average balance-check %, jobs in progress);
  "Recent statements" (5) with status and score; quick actions (Upload, Create API key,
  Read docs); system notice when /api/health reports no OCR worker
  ("Scanned statements may take longer right now").
/app/usage: date-range picker (presets 7/30/90 days), group by Day / API key / User;
  Recharts stacked bars (statements, pages), table, CSV export (client-side);
  plan card with limits and "Contact us to change plan".
/app/team (owner/admin): members table (email, role select, active toggle, last login,
  remove with confirm; owner row locked); "Invite member" dialog (email, role) → show the
  invite_url with Copy (no email is sent in v1) ; pending invites list with revoke.
/app/settings: organisation name (owner/admin), plan & limits read-only, data retention
  notice ("Uploads and workbooks are deleted after {retention_hours} hours"),
  your profile + change password, danger zone placeholder "Delete organisation — contact
  support" (no action).
```

### Prompt 6 — Impera staff super-admin console

```text
Build /admin/* visible and routable only when me.is_superuser is true (others → 404).
Distinct look: a thin amber top bar "Impera staff console".
/admin: overview tiles from GET /api/v1/admin/overview (tenants, active in 30 days,
  statements/pages 30 days, queue depth cpu/ocr, workers online, OCR device) with
  auto-refresh every 15 s; red alert when ocr workers = 0 and ocr queue > 0.
/admin/tenants: searchable, filterable (status) table with usage columns, pagination.
/admin/tenants/:id: profile, members, 30-day usage chart, API keys (revoke button),
  "Edit plan & limits" form (plan, max files/job, max MB, monthly quota) and
  Suspend/Reactivate with ConfirmDialog stating the impact (users read-only, API keys
  rejected). Show every action result as a toast. No impersonation feature.
```

### Prompt 7 — Polish and QA pass

```text
Do a full QA pass across every page in both themes and at 360px, 768px, 1280px:
- Every screen has loading skeleton, empty, error (with retry) and success states;
  test with mock errors (?mockError=500, 401, 403, 429).
- Keyboard-only walkthrough: focus order, visible focus, dialogs trap focus and return it,
  Escape closes, tables navigable. aria-live on job progress and toasts. Contrast AA.
- No personal data in URLs, titles or console.log; secrets never logged.
- Remove unused code, make sure no Supabase package or client exists, all API calls go
  through src/lib/api/client.ts, and switching VITE_USE_MOCKS=false + VITE_API_BASE_URL
  makes the app use the real backend without code changes.
- Add a README section: env vars, how to run with mocks, how to point at a backend.
```

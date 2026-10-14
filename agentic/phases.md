# Delivery Phases

> Status: draft · Last updated: 2026-10-14
> Phases 1–3 are reconstructed from the as-built code; there was no prior plan. Phase 4 is next, by product-owner decision (2026-10-14). Phases 5–6 are proposed and not yet approved for start.

## Phase status values

Use only: `not-started`, `in-progress`, `blocked`, `complete`.

## Phase 1 — Extraction engine

- **Objective:** template-free extraction of Indian bank statements into a verified transaction table.
- **Dependencies:** none.
- **Deliverables:**
  - `app/core/*`: classify, layout, OCR, columns, three row strategies, normalize, validate/reconstruct, customer, clean, annexure, completeness
  - `cli.py`
  - a 3-sheet workbook, since expanded in Phase 2
- **Verification:** manual runs over the 13 sample statements. The README records 1,825 rows, 12 at a 100% chain and 1 at 98.6%. Not re-run in this session.
- **Exit criteria:** every sample bank extracts with a chain ≥ 0.98, or with its failures flagged.
- **Status:** complete

## Phase 2 — Credit analysis layer (CAM)

- **Objective:** turn the verified transactions into an explainable underwriting profile.
- **Dependencies:** Phase 1.
- **Deliverables:**
  - `app/analysis/*`: 17 modules, the 8-component scorecard, hard caps and grades
  - the 11-sheet workbook (`app/output/excel.py`)
  - the account registry and linked accounts
- **Verification:** manual inspection of sample workbooks, plus `scratch/batch_process_all.py` stdout metrics.
- **Exit criteria:** every sample produces all 11 sheets with a score, a grade and reconciliation rows.
- **Notes:** known defects are listed in `memory.md` and carried into Phase 4.
- **Status:** complete

## Phase 3 — Multi-tenant web platform

- **Objective:** serve lender organisations as SaaS.
- **Dependencies:** Phases 1–2.
- **Deliverables:**
  - JWT auth and self-registration
  - MySQL models and Alembic migration 001
  - DB-backed jobs with a thread pool
  - tenant-scoped storage and registry
  - the usage meter
  - the static UI with login, history and download
  - Docker and compose
- **Verification:** none recorded.
- **Exit criteria:** a user can register, upload, poll and download; tenants can't see each other's jobs.
- **Notes:** the poll/list/download path probably fails on a detached session; it is the first task of Phase 4.
- **Status:** complete

## Phase 4 — Hardening

- **Objective:** make the existing product correct, testable and safe to keep developing, before adding anything new.
- **Dependencies:** Phase 3. The product-owner decision is in `memory.md` (2026-10-14).
- **Deliverables** (each one a separate reviewable change, `collaboration-workflow` H4):
  1. **Job API crash.** Make the `jobs.get` / `list_for_tenant` results usable after the session closes: eager-load `file_tasks`, or serialise inside the session. Order `file_tasks` by upload order, not uuid.
  2. **Regression suite.**
     - `tests/` with golden expectations per sample statement: rows, chain, mode, strategy, flagged, score, grade, FOIR/DSCR, bounce count. Free of personal data, keyed by file hash.
     - Unit tests for `normalize`, `validate` and the classifier rules.
     - API tests for auth, tenant isolation and the job lifecycle.
  3. **Personal data out of the repo.**
     - Move `Bank/`, `Croped Bank PDF's/`, generated `output/*.xlsx` and `data/account_registry.json` outside the project tree, or into a git-ignored fixtures location.
     - Extend `.gitignore` and add `.dockerignore`.
  4. **Scoring and validation defects** (consequential, so each needs a go-ahead and a decision entry in `memory.md`):
     - bounce double-counting
     - structuring score floor
     - OD utilisation averaging only negative days
     - OD in credit scored as 0× turnover
     - `RENT` substring match
     - swap-mode opening balance
     - hard-coded Balance Chain reconciliation
     - presence-only field "validation" relabelled or made real
     - the FOIR/DSCR band mismatch between `debt.py` and `profiler.py`
  5. **Dependencies.** Pin versions (lockfile), add `email-validator`, require `python-jose ≥ 3.4`, keep `bcrypt < 5` with passlib.
  6. **Housekeeping.**
     - Rewrite `README.md` for the SaaS edition, pointing at `agentic/`.
     - Fix or remove `verify_fix.py`.
     - Pick one schema path: Alembic only, or stamp after `create_all`.
- **Verification:**
  - `pytest` is green.
  - The sample-set run shows no chain/rows/flagged regression versus the pre-change baseline, or each difference is explained.
  - Grep the tracked tree for personal-data patterns and get no hits.
- **Exit criteria:** all six deliverables merged; the regression suite runs in one command; the job poll/download path works end to end against MySQL.
- **Status:** not-started

## Phase 5 — Security & DPDP compliance

- **Objective:** make the platform safe to expose to external lenders.
- **Dependencies:**
  - Phase 4
  - re-verifying the DPDP rule's freshness (due 2026-10-24)
  - the open question on processor vs fiduciary role (`prd.md`)
- **Deliverables:**
  - Refuse to start with the default JWT secret.
  - Restrict CORS.
  - A non-root MySQL user; don't publish 3306.
  - Login rate limiting and lockout.
  - Enforce roles, or remove them.
  - Purge output workbooks and orphaned uploads on a schedule.
  - Keep `usage` when a job is purged.
  - Tenant data erasure / export endpoints.
  - Registry retention policy.
  - Upload magic-byte check and streamed size limit.
  - Generic error messages to clients; structured logging without personal data.
- **Verification:** `security-review` over the diff, the DPDP checklist from `.agents/skills/dpdp-compliance/`, and API tests for each control.
- **Exit criteria:** no hard rule in `dpdp-compliance` or `rules.md` [H10]–[H14] is violated by the deployed configuration.
- **Status:** not-started

## Phase 6 — UI analysis display and accessibility

- **Objective:** show the CAM in the browser, and bring the UI to WCAG 2.1 AA.
- **Dependencies:** Phase 4 (stable analysis output).
- **Deliverables:**
  - A results view showing score, grade, binding caps, strengths and red flags from `result.financial_profile`.
  - Define `--accent`.
  - `aria-live` progress and errors; tab roles on auth.
  - Replace `innerHTML` and `alert()`.
  - Polling backoff.
  - Plan-aware upload limits in the copy.
- **Verification:** `frontend-standards` review and an accessibility audit.
- **Exit criteria:** every screen documents and implements its loading, empty, error and success states (`design.md`).
- **Status:** not-started

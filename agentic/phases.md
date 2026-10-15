# Delivery Phases

> Status: draft · Last updated: 2026-10-14
> Phases 1–3 are reconstructed from the as-built code; there was no prior plan. Phase 4 (SaaS scale-out) was requested and approved by the product owner on 2026-10-14, ahead of the remaining hardening. Phases 5–7 are proposed and not yet approved for start.

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

## Phase 4 — SaaS scale-out (100 concurrent users)

- **Objective:** serve 100 analysts at once from one machine (local now, a VM later), with durable queued processing and GPU OCR, without changing any CAM result.
- **Dependencies:** Phase 3. Product-owner decision of 2026-10-14 (`memory.md`); feature documents in `agentic/features/saas-scale/`.
- **Deliverables:**
  1. Celery + Redis queue: one task per file, `cpu` and `ocr` queues, redelivery on worker loss, time limits, purge and reaper on beat (`app/worker.py`, `app/tasks.py`).
  2. Correctness blockers: detached-session crash, registry insert race, streamed uploads, relative paths, upload order (`app/jobs.py`, `app/core/registry.py`, `app/api/routes.py`, migration 002).
  3. Security baseline: prod start guard, login/register rate limits, tenant active-file cap, MySQL app user, Redis without persistence, encrypted PDF passwords, `usage` kept on purge, outputs purged.
  4. Deployment: compose services `db`, `redis`, `migrate`, `api`, `worker-cpu`, `beat`, `worker-ocr` (gpu profile); `Dockerfile.gpu`; native Windows GPU worker documented.
  5. Dependencies: `requirements.lock`, `email-validator`, `python-jose ≥ 3.4`, `bcrypt < 5`, Celery and Redis.
  6. Tests and load test: `tests/` (API, queue, registry, baseline), `loadtest/locustfile.py`.
- **Verification:** `pytest tests`; `docker compose up` with `/api/health` green; worker kill mid-job; load test with 100 users (criteria in `agentic/features/saas-scale/prd.md`).
- **Exit criteria:** all of the above pass and are recorded in `HANDOVER.md`.
- **Notes:** everything verified 2026-10-15 except a manual browser run of the upload page (`agentic/features/saas-scale/phases.md` Step 4).
- **Status:** in-progress

## Phase 5 — Hardening (remaining)

- **Objective:** fix the known scoring and validation defects and finish the clean-up, now that a baseline guards every change.
- **Dependencies:** Phase 4 (baseline and test harness).
- **Deliverables** (each one a separate reviewable change, `collaboration-workflow` H4):
  1. **Scoring and validation defects** (consequential, so each needs a go-ahead and a decision entry in `memory.md`, and regenerates the baseline):
     - bounce double-counting
     - structuring score floor
     - OD utilisation averaging only negative days
     - OD in credit scored as 0× turnover
     - `RENT` substring match
     - swap-mode opening balance
     - hard-coded Balance Chain reconciliation
     - presence-only field "validation" relabelled or made real
     - the FOIR/DSCR band mismatch between `debt.py` and `profiler.py`
  2. **Unit tests** for `normalize`, `validate` and the classifier rules.
  3. **Housekeeping:** fix or remove `verify_fix.py`.
- **Verification:** `pytest` green; every baseline difference explained and approved.
- **Exit criteria:** all deliverables merged.
- **Status:** not-started

## Phase 6 — Security & DPDP compliance

- **Objective:** make the platform safe to expose to external lenders.
- **Dependencies:**
  - Phase 5
  - re-verifying the DPDP rule's freshness (due 2026-10-24)
  - the open question on processor vs fiduciary role (`prd.md`)
- **Deliverables** (start guard, CORS check, MySQL app user, rate limits, scheduled purge, `usage` retention, magic-byte check and streamed uploads were delivered in Phase 4):
  - Account lockout after repeated failed logins.
  - Enforce roles, or remove them.
  - Tenant data erasure / export endpoints.
  - Registry retention policy.
  - Generic error messages to clients; structured logging without personal data.
  - TLS termination and a reverse proxy on the VM.
- **Verification:** `security-review` over the diff, the DPDP checklist from `.agents/skills/dpdp-compliance/`, and API tests for each control.
- **Exit criteria:** no hard rule in `dpdp-compliance` or `rules.md` [H10]–[H14] is violated by the deployed configuration.
- **Status:** not-started

## Phase 7 — UI analysis display and accessibility

- **Objective:** show the CAM in the browser, and bring the UI to WCAG 2.1 AA.
- **Dependencies:** Phase 5 (stable analysis output).
- **Deliverables** (polling backoff and the progress `innerHTML` were done in Phase 4):
  - A results view showing score, grade, binding caps, strengths and red flags from `result.financial_profile`.
  - Define `--accent`.
  - `aria-live` progress and errors; tab roles on auth.
  - Replace the remaining `innerHTML` and `alert()` uses.
  - Plan-aware upload limits in the copy.
- **Verification:** `frontend-standards` review and an accessibility audit.
- **Exit criteria:** every screen documents and implements its loading, empty, error and success states (`design.md`).
- **Status:** not-started

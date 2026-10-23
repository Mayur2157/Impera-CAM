# Feature phases — Customer portal and developer API

> Status: approved (plan approval, 2026-10-16) · Last updated: 2026-10-16

## Step 1 — Prompt pack and contract

- **Deliverables:** `lovable-prompts.md`, `api-contract.md`, `prd.md`, this file.
- **Exit criteria:** every endpoint the prompts use is in the contract.
- **Status:** complete

## Step 2 — Frontend in Lovable (product owner)

- **Deliverables:** a Lovable project built from Prompts 1–7, connected to GitHub.
- **Exit criteria:** the app works end to end in mock mode; `package.json` has no Supabase dependency.
- **Status:** not-started

## Step 3 — Backend implements the contract

- **Dependencies:** consequential change, so it needs its own go-ahead.
- **Deliverables:**
  - migration 003: `api_keys`, `invites`, `tenants.status`/`monthly_statement_quota`, `users.last_login_at`, `usage.api_key_id`, owner role
  - `app/auth/principal.py`: JWT or `X-API-Key`, roles, superuser, suspension, per-key rate limit
  - `app/api/v1/`: jobs, api-keys, usage, org/members/invites, admin
  - full-result JSON written beside the xlsx by `app/tasks.py` and purged with it
  - CORS for the Lovable origins
- **Verification:** pytest per contract endpoint (shape, roles, tenant isolation, key revoke); existing baseline and load tests.
- **Status:** not-started

## Step 4 — Integrate the Lovable build

- **Deliverables:**
  - the Lovable code in `frontend/`
  - FastAPI serving `frontend/dist` at `/` (done 2026-10-23, with the local-mode change; Docker was removed, so there is no image stage)
  - the old `app/static` UI at `/legacy` until it's removed
- **Verification:** a browser walk-through with `VITE_USE_MOCKS=false`; smoke and load tests through `/api/v1`.
- **Status:** not-started

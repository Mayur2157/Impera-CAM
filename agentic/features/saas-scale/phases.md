# Feature phases — SaaS scale-out

> Status: approved (plan approval, 2026-10-14) · Last updated: 2026-10-14
> This is product Phase 4 in `agentic/phases.md`. Evidence for each step is in `HANDOVER.md`.

## Step 0 — Baseline and benchmark

- **Deliverables:** `tests/baseline/make_baseline.py`, `tests/baseline/extraction.json`; a GPU check of Paddle on the RTX 5070 Ti.
- **Exit criteria:** the baseline is deterministic (`--check` passes on a re-run); Paddle GPU `run_check()` passes.
- **Status:** complete

## Step 1 — Correctness blockers

- **Deliverables:** session-safe serialisation in `app/jobs.py`; registry upsert; streamed and validated uploads; relative paths (`app/storage.py`).
- **Exit criteria:** `tests/test_jobs_api.py` and `tests/test_platform.py` pass.
- **Status:** complete

## Step 2 — Durable queue and workers

- **Deliverables:** `app/worker.py`, `app/tasks.py`, `app/secretbox.py`, migration 002.
- **Exit criteria:** worker-path baseline identical (`tests/test_baseline.py`); a SIGKILLed worker loses no file.
- **Status:** complete

## Step 3 — Configuration, security, deployment

- **Deliverables:** new settings and prod guard; rate limits and tenant cap; `/api/health`; compose services; `Dockerfile`, `Dockerfile.gpu`; `requirements.lock`.
- **Exit criteria:** `docker compose up` healthy; migrations 001→002 on MySQL; image free of personal data.
- **Status:** complete

## Step 4 — Frontend

- **Deliverables:** polling backoff; server messages as text; queue and OCR-worker states visible.
- **Exit criteria:** the UI completes an upload against the stack.
- **Notes:** `app.js` passes `node --check`, and every API call it makes was exercised by the smoke and load tests. The page itself has not yet been driven in a browser; that manual check is what remains.
- **Status:** in-progress

## Step 5 — Tests, load test, docs

- **Deliverables:** `tests/`, `loadtest/locustfile.py`, README rewrite, `agentic/` updates.
- **Exit criteria:** the load test with 100 users meets the `prd.md` acceptance criteria.
- **Status:** complete

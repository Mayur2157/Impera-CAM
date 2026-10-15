# Feature PRD — SaaS scale-out (100 concurrent users)

> Status: approved (plan approval, 2026-10-14) · Last updated: 2026-10-14

## Problem

The platform processed statements inside the web process: `ThreadPoolExecutor(4)` shared the GIL with the API, files in a job ran one after another, and a restart lost every queued job. Job status, history and download crashed on a detached database session. It couldn't serve external lenders at any real concurrency.

## Target (decided with the product owner, 2026-10-14)

| Decision | Value |
|---|---|
| Load | 100 analysts signed in at once, working normally: about 100 statements in a busy 10 minutes |
| Turnaround | Results in 1–3 minutes; a short queue at peak is acceptable |
| Scanned statements | Frequent, so GPU OCR is a first-class queue |
| Hosting | Local machine now (Windows + Docker Desktop); one VM later, with no code changes |

## Requirements

- **FR-S1** Every uploaded file is an independent, durable task. It survives API and worker restarts, and a worker dying mid-file gives the task back.
- **FR-S2** Digital and scanned files use separate queues (`cpu`, `ocr`), so a scanned statement never holds a CPU worker and digital ones never wait behind the GPU.
- **FR-S3** The API is stateless and multi-process; uploads never block its event loop.
- **FR-S4** Fairness: a tenant's queued plus running files are capped (`BSX_TENANT_MAX_ACTIVE_FILES`, default 50), returning 429.
- **FR-S5** Login and registration are rate-limited per IP across all API processes.
- **FR-S6** PDF passwords are never stored. They travel encrypted inside the task message, in a Redis instance with persistence off.
- **FR-S7** Retention: uploads, workbooks and orphaned files are purged on a schedule. Billing (`usage`) rows survive the purge.
- **FR-S8** `/api/health` reports the database, Redis, queue depths and live workers per queue, including which OCR device the GPU worker sees.
- **FR-S9** `BSX_ENV=prod` refuses to start on a placeholder JWT secret, wildcard CORS, or MySQL root.

## Non-goals

- S3 or object storage. There is one machine, and paths are stored relative, so it can be added later.
- Horizontal API scaling across hosts.
- Billing UI, role enforcement, and DPDP erasure endpoints (Phase 5).
- Scoring changes. CAM results must stay identical to the pre-change baseline.

## Acceptance

- `pytest` is green, including `test_baseline.py`: all 13 sample statements identical through the worker path.
- The load test with 100 users shows 0 HTTP 5xx; p95 < 500 ms on non-upload endpoints and < 2 s on upload; median digital end-to-end < 3 min.
- A worker killed mid-file leaves no job stuck in `running`.

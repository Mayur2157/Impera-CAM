# Feature architecture — SaaS scale-out

> Status: approved (plan approval, 2026-10-14) · Last updated: 2026-10-14
> The system-wide architecture of record stays in `agentic/architecture.md`; this file covers what the feature added.

## Topology

```
Browser ──► api  (uvicorn --workers 4, stateless) ──► MySQL 8  (app user)
              │ tasks.dispatch(file_task_id, sealed_pw)
              ▼
            Redis 7  (broker · rate-limit counters · worker heartbeats; no persistence)
              │ queue "cpu"                          │ queue "ocr"
              ▼                                      ▼
      worker-cpu  (Celery prefork, -c 8)      worker-ocr  (Celery --pool solo, GPU)
      classify pages; scanned → re-queue      Windows laptop: native process
      on "ocr"; digital → pipeline.process    VM: docker compose --profile gpu
              │                                      │
              └──── ./data/uploads, ./output  (bind mounts; DB stores relative paths)
      beat: bsx.purge every 15 min · bsx.reap_stuck every 5 min
      migrate: one-shot `alembic upgrade head` before api/workers start
```

## Modules

| File | Role |
|---|---|
| `app/worker.py` | Celery app and config (`acks_late`, `reject_on_worker_lost`, prefetch 1, visibility timeout > OCR hard limit), beat schedule, worker heartbeats, `redis_client()` |
| `app/tasks.py` | `dispatch()` (queue + time limits), `process_file`, `purge`, `reap_stuck` |
| `app/jobs.py` | API-side job store. Serialises inside the session (fixes the detached-instance crash); `finalize()` locks the job row; purge and reaper logic |
| `app/storage.py` | Relative path helpers, so the API, containers and a native GPU worker can each mount the folders differently |
| `app/secretbox.py` | Fernet seal/unseal for PDF passwords, key derived from `BSX_JWT_SECRET` with a fixed context label |
| `app/ratelimit.py` | Redis fixed-window limiter as a FastAPI dependency (fails open if Redis is down) |
| `alembic/versions/002_saas_scale.py` | `file_tasks.position/started_at/finished_at`, index on `status`, `usage.job_id ON DELETE SET NULL` |

## Lifecycle of one file

1. `POST /api/jobs` streams each upload to `data/uploads/<tenant>/` (1 MB chunks, size cap, `%PDF-` magic check). It opens each PDF once, so a wrong password is a 400 immediately, then checks the tenant cap.
2. `jobs.create()` writes the Job and FileTasks (with `position`), then `dispatch(..., ocr=False)` for each file.
3. On the `cpu` queue: if `use_ocr` and any page classifies as scanned (`app/core/classify.classify_page`), the file is re-dispatched to `ocr` with the message "waiting for OCR worker". Otherwise it runs `app/core/pipeline.process()` unchanged.
4. The result (with the workbook path made relative), `status=done` and a `Usage` row are written in **one commit**, so a redelivered task can't meter twice. A task already `done` is skipped on redelivery.
5. `finalize()` locks the job row and sets `running`, `done` or `error` from its files.

## Decisions

| # | Decision | Why |
|---|---|---|
| S-AD1 | Celery + Redis, as the earlier code comment had planned | Durable, multi-process, per-queue routing and time limits; runs on Windows (solo pool) and Linux |
| S-AD2 | One task per file, not per job | Files of one upload run in parallel; one bad PDF fails alone |
| S-AD3 | Route by page classification at the start of the CPU task | Same test extraction already uses; no GPU is held for digital files |
| S-AD4 | Encrypted password in the task message, Redis persistence off | Workers are separate processes, so the in-memory dict can't reach them. Nothing touches disk (rules H10, clarified) |
| S-AD5 | Shared bind-mounted folders, relative paths in the DB | Single machine now; a native Windows GPU worker sees the same files; an S3 adapter can replace `storage.py` later |
| S-AD6 | Alembic is the only schema path; a `migrate` service runs first | Several API processes running `create_all` at once would race |
| S-AD7 | Compose MySQL on host port 3307 | The development machine already runs a MySQL on 3306 |

## Capacity

- **Measured (Step 0):** digital statements take 0.3–7 s each on one core (13 samples, 6,278 rows). Ten statements a minute is about 30 CPU-seconds per minute, so 8 CPU workers leave large headroom.
- **OCR (measured 2026-10-15, RTX 5070 Ti, PaddleOCR 3.7 PP-OCRv6 medium):**
  - 2.8 s per page warm, including extraction; a 35-page scan takes 98 s. That is about 21 pages a minute per GPU, with a 2.5 GB peak under the `auto_growth` allocator.
  - One GPU handles about 1.4 fifteen-page scans a minute. A scanned-heavy peak (4 scans/min) queues on `ocr` and drains afterwards.
  - Scale by adding GPU hosts running `worker-ocr` against the same Redis, MySQL and folders. A second process on the same GPU is possible memory-wise, but inference is serialised per process, so the gain is unmeasured.
- **MySQL connections:** 4 API processes × (10 + 10), plus 8 workers × (2 + 2), plus beat ≈ 120, under `max_connections=300`.

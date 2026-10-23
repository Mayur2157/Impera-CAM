# Handover

> Last updated: 2026-10-23 · model/version: claude-opus-5-5

## Completed

**Docker removed; everything runs locally (2026-10-23, product owner's request).**
- Deleted `Dockerfile`, `Dockerfile.gpu`, `docker-compose.yml` and `.dockerignore` (all recoverable from git).
- `python main.py` now needs no configuration. It applies the Alembic migrations, then serves the API, the portal build (`frontend/dist`) at `/` and the old page at `/legacy`.
- The defaults are a SQLite database (`data/impera_cam.db`, git-ignored, WAL mode) and `BSX_QUEUE=local`: jobs run on threads inside the API process (`BSX_LOCAL_WORKERS`, default 2, plus one GPU thread), with an in-memory store instead of Redis. A maintenance thread purges and reaps, and on start it fails files a previous run left unfinished.
- Celery, Redis and MySQL still work (`BSX_QUEUE=celery`); README "Running on a server". `BSX_ENV=prod` refuses SQLite and local mode.
- Fixed while testing: the empty `alembic/__init__.py` shadowed the real Alembic package (`from alembic import command` failed), so I deleted it. The Celery task wrapper is not thread-safe, so local threads now call a plain `tasks.run_file`, and a crash in a local thread marks the file failed instead of leaving it queued.

**Customer portal, Phase 1: backend core (2026-10-23).** The plan is a hand-built Vite + React SPA in `frontend/` (the Lovable build in `Frontend/` was deleted and is reference only, at `732ae3b`), plus the backend it needs, in 7 phases.
- `app/auth/principal.py`: Bearer JWT or `X-API-Key` (SHA-256 lookup, scopes, revoked → 401, suspended tenant → 403, per-key rate limit, `last_used_at`).
- `app/output/cam_json.py`: the full CAM as contract-shaped JSON, written beside the workbook (`pipeline.process(cam_json=True)`, which the worker uses) and purged with it. The account number is masked, including inside narrations; email, phone, address and PAN are never written.
- `/api/v1/jobs*` (list `{items,total}`, job, result, transactions, download) and `/api/v1/usage` (by day, user or API key, plus month-to-date and plan). Usage rows record `api_key_id`.
- `/api/auth`: register requires `accept_terms` and makes the creator `owner`; login records `last_login_at`; `/me` carries `is_superuser`, `org_status` and `plan`. The legacy page got a consent checkbox.
- The suspension check moved into the shared `submit_job`, so the legacy `/api/jobs` upload enforces it too.
- `api-contract.md` was updated: implementation status, plus three small additions (an `unscored_reasons` map, metric labels, usage `month_to_date`).

**Earlier (2026-10-14):** agentic documents; `.gitignore`/`.dockerignore` hardened; git initialised (`d2b5366`).

**SaaS scale-out (Phase 4):** see `agentic/features/saas-scale/`.
- **Queue:** Celery + Redis, one task per file, `cpu` and `ocr` queues, redelivery on worker loss, time limits, beat purge and reaper (`app/worker.py`, `app/tasks.py`).
- **API:** stateless, 4 processes, streamed and validated uploads, wrong PDF password rejected at upload, tenant active-file cap (429), login/register rate limits, `/api/health` with DB, Redis, queues and live workers (`app/api/routes.py`, `app/ratelimit.py`).
- **Fixes:**
  - detached-session crash in status/history/download
  - registry insert race (`app/core/registry.py`)
  - absolute paths in the DB (`app/storage.py`)
  - `usage` deleted with jobs
  - outputs never purged
  - `config.py` list default (the app couldn't import on Python 3.11+)
  - SQLAlchemy reserved name `Tenant.registry`
- **Security:** prod start guard, MySQL app user, Redis without persistence, PDF passwords Fernet-encrypted in the task message only (`app/secretbox.py`; rules H10 clarified).
- **OCR:** PaddleOCR 3.x greyscale crash fixed. The GPU allocator default changed `naive_best_fit` → `auto_growth`; the old one failed every multi-page scan with out-of-memory. Paddle GPU cu129 runs on the RTX 5070 Ti.
- **Deployment (removed 2026-10-23):** this was a Docker Compose stack (MySQL on 3307, Redis, migrate, api, workers, beat, GPU worker). `requirements.lock` remains.
- **Tests:** `tests/` (21 tests including worker-path baseline), `tests/baseline/` (hash-keyed, no personal data), `loadtest/locustfile.py`.
- **Docs:** README rewritten; `agentic/architecture.md`, `phases.md`, `memory.md` and `rules.md` (H8, H10, H21, H22) updated.

## In Progress

- Portal Phases 1–2 are uncommitted in the working tree. The deletion of the old `Frontend/` is **staged** (`git rm --cached`), so the new lowercase `frontend/` is tracked as new files (`core.ignorecase=true`).
- Portal Phase 2 (`frontend/`): Vite + React 19 + TypeScript + React Router 8 + TanStack Query + Tailwind 4, plus Radix for the menu and drawer. It has sign-in and sign-up (an unticked consent box, draft privacy notice and terms), the app shell (sidebar and mobile drawer, org and plan, suspended banner, theme), New analysis (drag-and-drop with plan-aware checks, XHR progress, cancel, OCR notice), Statements (paginated, cards on mobile) and the job page (polling 2→10 s, summaries, Excel download). Dashboard, analysis, usage, keys, team, settings and admin are "Coming soon" placeholders. Run it with `cd frontend && npm install && npm run dev` (port 5173, proxies `/api` to `:8000`).
- **Not yet done for Phase 2:** a real-browser walk-through at 375, 768 and 1440 px, keyboard-only, with an axe check (frontend H9/H12). No browser tool was available this session.
- Portal plan, phases 2–7: 2 frontend foundation (auth, shell, upload, jobs); 3 analysis dashboard and Excel download; 4 tenant dashboard and usage; 5 API keys, team and settings; 6 super-admin; 7 docs. FastAPI already serves `dist`, and there is no longer a Docker stage. The plan file is at `~/.claude/plans/i-want-to-make-splendid-gosling.md`.

## Next

0. Portal: do the browser walk-through of Phase 2, review and commit Phases 1–2, then start Phase 3 (the analysis dashboard; add Recharts in its own lazy chunk).
1. Run locally: `cd frontend && npm install && npm run build`, then `python main.py` → http://localhost:8000.
2. Review the diff and commit it (suggested: Docker removal + local mode; portal backend; portal frontend).
3. Get **real scanned statements**: accuracy is proven only on simulated scans.
4. Decide GPU capacity for scanned-heavy peaks: one GPU is about 21 pages/min (see Watchouts).
5. Phase 5: scoring defects, each guarded by the baseline.

## Watchouts

- **Local mode is one process.** Stopping or reloading `python main.py` fails the files still processing ("upload it again"). Threads share the GIL, so it is for development, not capacity; the server setup is celery mode.
- **Your old `.env` is unused.** Nothing loads `.env` now, and its `BSX_MYSQL_URL` points at the removed compose MySQL (3307). If those variables are set in your shell, the app follows them; unset `BSX_MYSQL_URL` and `BSX_QUEUE` to get the local defaults.
- **One GPU ≈ 21 scanned pages/min.** A burst of scans queues on `ocr` and drains afterwards. Add GPU hosts (`worker-ocr`) to shorten waits.
- **Celery mode only:** every process needs the same `BSX_JWT_SECRET`, or workers can't decrypt queued PDF passwords.
- **Crash redelivery takes up to 40 min** (`BSX_BROKER_VISIBILITY_SECONDS`). Normal stops are warm.
- Personal data sits in `Bank/`, `Croped Bank PDF's/`, `output/` and `data/account_registry.json` (ignored by git), and in `data/impera_cam.db`. Never copy it into docs, tests or logs.
- The DPDP rule's freshness is due 2026-10-24.
- Portal: files processed before 2026-10-23 have no analysis JSON, so `/result` answers 410 for them (resubmit).
- Portal: `/api/v1/usage` groups by `func.date()`. This is tested on SQLite only, not yet on MySQL.
- Portal: an API key keeps working if the member who created it is deactivated. Decide in Phase 5 (revoke their keys on removal?).
- Portal: `monthly_statement_quota` is displayed but not enforced at upload, as the PRD's "billing v1 = display only" says.
- Portal DPDP gaps: consent stores only `terms_accepted_at`; rule H6 also wants the notice version and method recorded (the notice is versioned `draft-2026-10-23` in `LegalPages.tsx`). The privacy notice is a DRAFT for legal review. The rights requests (access, erasure) have no product path yet.
- Portal: frontend dependencies are new majors (React Router 8, zod 4, TypeScript 6, Vite 8, ESLint 10). `@hookform/resolvers` is pinned to 5.x, because 6.0.0 has a conflicting optional peer (`effect`).
- Vite dev listens on `localhost` (IPv6 `::1`), not `127.0.0.1`.
- Pre-existing cosmetic warnings: naive `datetime.utcnow()` (the codebase's convention) and Celery's "clock drift" between UTC containers and the Windows host.

## Verification

2026-10-23 (Docker removal, local mode):
- `pytest tests` → `37 passed` (exit 0), including 6 local-mode tests (thread pool with 6 concurrent files, OCR hand-off, crash → failed, restart → failed, memory store, portal routes).
- `python main.py` with no `BSX_*` variables (a throwaway SQLite path): migrations 001→003 ran; health `db ok, workers cpu 1 / ocr 1, ocr_device gpu:0`. Portal at `/`, `/legacy` 200, unknown `/api/...` 404. An upload of 4 real statements returned in 0.1 s and processed 2 at a time with live progress, all done in 13 s: HDFC 253 rows / score 50, Kotak 251 / 38.3, SBI 117 / 63.3, Cosmos 704 / 13.8, all chain 1.0, xlsx 200, usage 4 statements / 41 pages.
- No scanned statement was run through the in-process GPU thread (no real scans in the samples).

2026-10-23 (portal Phase 1):
- `pytest tests` → `31 passed` (exit 0). That includes 9 new `/api/v1` tests and the worker-path baseline. The baseline digest now excludes the `cam_json` output path, as it already excluded `xlsx`; the stored baseline is unchanged.
- The real pipeline with `cam_json=True` on HDFC, Kotak OD and Cosmos produced valid JSON: monthly series, loans, bounces, labels, and the masked account number nowhere unmasked.

2026-10-23 (portal Phase 2, in `frontend/`):
- `npm run lint`, `npm run typecheck`, `npm test` (16 passed) and `npm run build` all pass. Pages are code-split; the initial JS is about 98 kB gzipped.
- Smoke test through the Vite proxy, with the real FastAPI app on SQLite and Celery eager (Docker was not running): sign-up, `/me`, usage and plan, uploading `Bank/HDFC.pdf` (253 rows, chain 1.0, score 50), job, result (masked account number), xlsx download 200, usage 1 statement / 10 pages, and 401 without a token.
- **Not run:** the browser UI walk-through, the responsive and keyboard checks, and the Docker stack with MySQL.

All run 2026-10-14/15 on this machine.

| Check | Command | Outcome |
|---|---|---|
| Baseline recorded | `python tests/baseline/make_baseline.py "Bank/*.pdf"` | 13 statements, 6,278 rows, all chain 1.0, 0.3–7 s each; re-run `--check` → `baseline OK` (deterministic) |
| CLI baseline after all changes | `... make_baseline.py "Bank/*.pdf" --check` | `baseline OK` |
| Test suite | `pytest tests` | `21 passed` (includes worker-path baseline over all 13 statements) |
| Stack | `docker compose up -d --build` | Migrations 001 → 002 on MySQL; health `db ok, redis ok, cpu 1` |
| Image hygiene | `find` inside `imperacam-api` | No PDF, xlsx or registry; runs as user `bsx` |
| Smoke | 4 real statements, one job | Done in 11.3 s (parallel); status, history and download 200 |
| Crash safety | SIGKILL `worker-cpu` mid-job, restart (visibility 60 s for the test) | 10/10 files `done`, none stuck |
| GPU | `paddle.utils.run_check()` | "PaddlePaddle works well on 1 GPU" (compute 12.0) |
| OCR accuracy (simulated scans) | `ocr_bench.py` | 35 pages → 1,009 rows, chain 1.0, 98 s (2.8 s/page); 8 pages → 226 rows, chain 1.0; 2-page layout → 4 rows, chain 0 |
| Scanned upload through the stack | Upload 8-page scan, native GPU worker | Routed cpu → ocr; 226 rows, chain 1.0, 25 s end-to-end; download 200 |
| **Load test** | `locust -u 100 -r 10 -t 15m --host http://192.168.0.168:8000` | **3,009 requests, 0 failures.** p95: history 9 ms, status 8 ms, upload 97 ms, download 13 ms, register 320 ms. 150 statements end-to-end: median 4.8 s, p95 14 s. All 169 files `done`, queues drained |
| Rules pack | `python .agents/scripts/validate.py` | `0 error(s), 0 warning(s)` |

The first load-test attempts against `http://localhost:8000` failed with connection resets. The cause was WSL's loopback relay, not the app: the API answered in 80 ms from inside its container throughout.

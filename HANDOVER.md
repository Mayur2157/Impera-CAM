# Handover

> Last updated: 2026-10-15 · model/version: claude-opus-5-5

## Completed

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
- **Deployment:** compose `db`, `redis`, `migrate`, `api`, `worker-cpu`, `beat`, `worker-ocr` (gpu profile); non-root `Dockerfile`, `Dockerfile.gpu`, `requirements.lock`; native Windows GPU worker documented. MySQL is on host port 3307 because 3306 is taken by another local MySQL. The API is published on IPv4 only.
- **Tests:** `tests/` (21 tests including worker-path baseline), `tests/baseline/` (hash-keyed, no personal data), `loadtest/locustfile.py`.
- **Docs:** README rewritten; `agentic/architecture.md`, `phases.md`, `memory.md` and `rules.md` (H8, H10, H21, H22) updated.

## In Progress

- Phase 4 Step 4: a manual browser run of the upload page. The API calls it makes are verified; the page itself hasn't been clicked through.
- Nothing is committed yet. All changes are in the working tree (`git status`).

## Next

1. Open `http://<lan-ip>:8000`, sign up, upload a statement, and download it. That closes Phase 4.
2. Review the diff and commit it (suggested: one commit for the queue and API, one for OCR fixes, one for docs).
3. Get **real scanned statements**: accuracy is proven only on simulated scans.
4. Decide GPU capacity for scanned-heavy peaks: one GPU is about 21 pages/min (see Watchouts).
5. Phase 5: scoring defects, each guarded by the baseline.

## Watchouts

- **Windows `localhost` can hang under load:** `wslrelay` (WSL localhost forwarding) stalls; Docker's forwarder via the LAN IP doesn't. Restart Docker Desktop if `localhost:8000` hangs. Linux VMs are unaffected.
- **One GPU ≈ 21 scanned pages/min.** A burst of scans queues on `ocr` and drains afterwards. Add GPU hosts (`worker-ocr`) to shorten waits.
- **The native GPU worker needs the same `BSX_JWT_SECRET` as the stack**, or it can't decrypt queued PDF passwords. Start it with the command in the README "Scanned statements" section; it isn't a Windows service, so it stops when its terminal closes.
- **Crash redelivery takes up to 40 min** (`BSX_BROKER_VISIBILITY_SECONDS`). Normal stops are warm.
- Personal data sits in `Bank/`, `Croped Bank PDF's/`, `output/` and `data/account_registry.json` (ignored by git and Docker). Never copy it into docs, tests or logs.
- The DPDP rule's freshness is due 2026-10-24.
- Pre-existing cosmetic warnings: naive `datetime.utcnow()` (the codebase's convention) and Celery's "clock drift" between UTC containers and the Windows host.

## Verification

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

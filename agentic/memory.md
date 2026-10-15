# Project Memory

> Last updated: 2026-10-14
> Durable product decisions and state. Session-level state belongs in `HANDOVER.md`.

## Approved decisions and rationale

| Date | Decision | Rationale | Source |
|---|---|---|---|
| 2026-10-14 | Impera CAM is **external multi-tenant SaaS for lenders** (NBFCs, banks, co-ops, DSAs) | Matches the tenant/plan/usage model already built | Product owner |
| 2026-10-14 | Next phase was Hardening; **superseded the same day** by the scale-out below, which absorbed hardening items #1 (job API crash), #2 (baseline + API tests), #3 (PII out of the repo) and #5 (dependencies) | The product owner asked for SaaS at 100 concurrent users | Product owner |
| 2026-10-14 | **SaaS scale-out (Phase 4):** 100 analysts signed in at once, normal use (about 100 statements per busy 10 min, results in 1–3 min); many scanned statements, so GPU OCR is first-class; local machine now, one VM later | Product-owner answers; feature docs in `agentic/features/saas-scale/` | Product owner, plan approval |
| 2026-10-14 | **Celery + Redis**, one task per file, `cpu` and `ocr` queues; the native Windows GPU worker locally, `worker-ocr` (Docker + nvidia) on the VM | Durable and multi-process; the extraction is pure-Python CPU work that threads can't parallelise | Plan approval (S-AD1–S-AD3) |
| 2026-10-14 | **rules H10 clarified:** a PDF password may travel Fernet-encrypted inside the task message, in a Redis with persistence off; nowhere else | Workers are separate processes; the in-memory dict could not reach them | Plan approval (S-AD4) |
| 2026-10-14 | Alembic is the only schema path (`migrate` service); `create_all` removed from the API | Several API processes would race on CREATE TABLE | Plan approval (S-AD6) |
| 2026-10-14 | Paddle GPU uses the **cu129** wheel (3.3.0) | The RTX 5070 Ti is Blackwell (compute 12.0); the README's cu126 instruction targeted the 40-series. Verified: `paddle.utils.run_check()` passes on the GPU | Measured this session |
| 2026-10-14 | `agentic/` is the source of record; `README.md` is the developer quick start | The old README predated auth, the DB and the analysis layer (rewritten 2026-10-14) | Plan approval |
| pre-2026-10 *(inferred)* | Balance chain as ground truth; bands from ink; balance-anchored rows; three scored strategies; Decimal core; OCR emits the same `Word` schema; deterministic rule-based scoring; per-tenant registry | See `architecture.md` AD-1 to AD-9 | Code and README |

model/version: not recorded for pre-existing decisions; this session ran on claude-opus-5-5.

## Current progress

- Phases 1–3 `complete`; **Phase 4 (SaaS scale-out) `in-progress`**; see `phases.md` and `HANDOVER.md` for what is verified.
- Baseline measured 2026-10-14 (`tests/baseline/extraction.json`): 13 statements, 6,278 rows, all at a 100% chain, 0.3–7 s each on one CPU core. None of the 13 samples has a scanned page.
- Git was initialised (initial commit `d2b5366`). No statements, workbooks or registry are tracked.

## Important context

- **Ports:** a MySQL already listens on 3306 on the development machine, so the compose MySQL is published on **127.0.0.1:3307**. Never point the app at the 3306 database without asking: it isn't ours.
- **Python:** system Python is 3.14; Paddle needs **3.12** (`.venv` is 3.12 and holds the GPU stack). The Docker images are 3.12.
- `.env` is read only by docker compose; native processes (the GPU worker, `python main.py`) read the OS environment.
- The native GPU worker must use the **same `BSX_JWT_SECRET`** as the stack, or it can't decrypt queued PDF passwords.
- Tenant plan defaults (10 files / 20 MB per job) override the global settings (25 / 40).
- PaddleX pins `PyYAML==6.0.2`; `requirements.lock` carries that pin so the API and GPU images agree.
- Analysis docstrings name the sample banks that drove each rule; the baseline (`tests/baseline/`) now guards them.

## Active risks

Ranked by impact. Items are marked *fixed* only when a test or measured run shows it.

1. **GPU OCR throughput is the capacity limit for scanned-heavy peaks.** Measured 2026-10-15 on the RTX 5070 Ti: 2.8 s per page warm (35-page scan in 98 s), so about 21 pages a minute per GPU. If 40% of a peak of 10 statements/min are 15-page scans, that's 60 pages/min, roughly 3× one GPU. The `ocr` queue absorbs the burst and drains after it. For shorter waits, add GPU hosts running `worker-ocr` against the same Redis/MySQL/folders (no code change).
2. **OCR accuracy is proven only on simulated scans.** Simulated 200 dpi rescans: 35 pages → 1,009 rows at a 100% chain (the digital original also has 1,009); 8 pages → 226 rows at 100%. A 2-page, 15-row layout read only 4 rows (chain 0). No genuine scanned statement is in the samples; get real ones before promising scanned accuracy.
3. **Windows-local only: `wslrelay` stalls loopback under load.** WSL's localhost relay also binds `127.0.0.1:8000`/`::1:8000` and stopped forwarding during a 100-user run, so `http://localhost:8000` hung while the API was idle and healthy. Docker's own forwarder (`0.0.0.0:8000`, reached via the LAN IP) was unaffected. Use the LAN IP for load tests; restart Docker Desktop (or set `localhostForwarding=false` in `%UserProfile%\.wslconfig`) if localhost hangs. Linux VMs have no such relay.
4. **Scoring defects that move the CAM score** (unchanged; now Phase 5, each guarded by the baseline):
   - Bounces may be counted twice: the reversed debit and the credit are both marked `bounce_side=OWN` (`classifier.py:744-749`, `returns.py:60-61`, `debt.py:192`).
   - Structuring always scores ≥ MEDIUM without trade wording; the LOW branch is unreachable (`fraud_aml.py:150-199`).
   - OD utilisation averages only negative-balance days; an OD in credit scores as 0× turnover (`health.py:173-176`, `profiler.py:330`).
   - `"RENT" in narr` matches CURRENT, PARENT, TORRENT (`eligible_income.py:117-119`).
   - One SALARY credit switches a business account to retail FOIR (`income.py:61`).
   - A payer named "… Capital" is treated as a capital infusion (`eligible_income.py:147`).
   - A cash deposit with SALE/BILL wording counts as revenue (`classifier.py:233-234`).
   - The circular-flow check excludes the wrong names (`fraud_aml.py:238`); the fallback uses non-existent categories (`debt.py:333`).
   - TAX_GST/EPFO/ESIC/PF are excluded from operating expenses. **A policy question, not a bug.**
5. **Validation the workbook overstates:** presence-only `validate_field_linkage` (`validate.py:111`); hard-coded Balance Chain reconciliation (`excel.py:1271, 1299`); "Operating Cash Coverage" duplicates DSCR (`excel.py:1253`); swap-mode opening balance (`pipeline.py:88-112`).
6. **Inconsistent policy constants:** FOIR bands 35/50 (`debt.py`) vs 30/45/55 (`profiler.py`); concentration 40% vs 35%; ÷30 vs ÷30.4.
7. **Remaining security gaps** (Phase 6): no account lockout; roles never enforced; self-registration; token in localStorage; raw exception text returned to clients; no TLS until a reverse proxy is added on the VM. Rate limits fail open while Redis is down.
8. **Crash recovery is slow by design:** a file whose worker was killed (not stopped) is redelivered only after `BSX_BROKER_VISIBILITY_SECONDS` (40 min), because a shorter timeout would re-run long OCR files. Normal stops are warm and lose nothing.
9. **DPDP:** no erasure or export endpoint; `account_registry` keeps personal data indefinitely (Phase 6; re-verify the DPDP rule, due 2026-10-24).
10. **Frontend:** `--accent` undefined; no `aria-live`; the remaining `innerHTML`/`alert()` uses (Phase 7).
11. **Operational:** `annexure.py:52-55` can raise `StopIteration`; `columns.py:329` `runs[ib-1]` wraps when `ib == 0`; `verify_fix.py` references workbooks that no longer exist.

*Fixed 2026-10-14 (verified by `tests/` and live runs):*
- job status/history/download crash (detached session)
- in-memory queue lost on restart
- serial files within a job
- registry insert race under parallel workers
- blocking uploads
- absolute paths in the DB
- output workbooks never purged; `usage` deleted with jobs
- placeholder secret / CORS `*` / MySQL root accepted in prod; MySQL port exposed
- unpinned deps (bcrypt 5 broke passlib; python-jose CVEs; email-validator missing)
- personal data in the repo and image
- `app/config.py` frozen dataclass with a list default (the app couldn't import on Python 3.11+)
- PaddleOCR 3.x rejecting greyscale input (`app/core/ocr.py`)
- every multi-page scanned statement failing with GPU out-of-memory: the `naive_best_fit` allocator default; now `auto_growth` (`app/core/ocr.py`)

## Unresolved noncritical questions

Mirrored from `prd.md` → Open questions: pricing/plans, target lender segment, data residency, DPDP role (processor vs fiduciary, which is **critical before Phase 6**), SLAs, role enforcement, and future LLM narrative. New: where real scanned statements for OCR accuracy work come from.

## Changes affecting future work

- Any change to scoring constants must update `rules.md` → Business rules of record, this file, and the baseline (`tests/baseline/make_baseline.py`) in the same change ([H4], [H8]).
- New long-running work is a Celery task, idempotent under redelivery ([H21], [H22]).
- Never enable Redis persistence while task messages can carry passwords ([H10]).
- Moving to the VM: copy `.env`, `docker compose --profile gpu up -d --build`, put a TLS reverse proxy in front of `:8000`, and set `BSX_ENV=prod` (the start guard will list anything still unsafe).
- If an LLM is ever introduced, `.agents/rules/ai/*` applies and AD-6 must be amended first.

---

**Never record here:** secrets, credentials, access tokens, API keys, connection strings, or personal data.

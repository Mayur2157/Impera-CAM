# Technical Architecture

> Status: draft · Last updated: 2026-10-14
> This is the architecture of record. Do not maintain a second copy at the repository root. `README.md` predates the SaaS edition and is out of date (see `memory.md`).

## System context

```
 Lender analyst (browser)                 Operator (shell)
        │  HTTPS, Bearer JWT                     │
        ▼                                        ▼
 ┌───────────────────────────── app (FastAPI, uvicorn :8000) ─────────────┐
 │  static UI  ─  /api/auth/*  ─  /api/jobs*  ─  /api/health               │      cli.py ──┐
 │                       │                                                 │               │
 │                 jobs.py ThreadPoolExecutor ──► core.pipeline.process() ◄┼───────────────┘
 │                                                   │        │            │
 │                                     analysis.profiler   output.excel    │
 └──────────────┬─────────────────────────────────────┬─────────┬─────────┘
                │ SQLAlchemy / PyMySQL                │         │
                ▼                                     ▼         ▼
            MySQL 8                           data/uploads/  output/<tenant>/*.xlsx
   tenants users jobs file_tasks              <tenant>/*.pdf
   account_registry usage
                                   optional: PaddleOCR (GPU) / Tesseract, in-process
```

There are no outbound network integrations: no LLM, no bureau, no email.

## Technology stack and rationale

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 (`Dockerfile`) | PDF/OCR ecosystem |
| PDF text | pdfplumber ≥ 0.11.4 | Word-level coordinates, which the geometry-based extraction needs |
| OCR | PaddleOCR ≥ 3.0 on `paddlepaddle-gpu==3.3.0` (cu126); Tesseract fallback | Paddle is the only engine whose amounts verified; Tesseract fails the chain (README) |
| Money | `decimal.Decimal` in `app/core` | Balance-chain equality at ₹0.02 needs exact arithmetic |
| Web | FastAPI ≥ 0.115, uvicorn | Async uploads, OpenAPI at `/docs` |
| DB | MySQL 8 via SQLAlchemy 2 + PyMySQL; Alembic | Multi-tenant persistence *(inferred: a hosting preference; no SQLite fallback)* |
| Auth | python-jose (HS256), passlib[bcrypt] | Stateless bearer tokens |
| Output | openpyxl ≥ 3.1.2 | The workbook is the deliverable |
| Frontend | Plain HTML/CSS/JS | No build step |
| Packaging | Docker (`python:3.12-slim`), docker-compose with `mysql:8.0` | Single-host deployment |

Every dependency is unpinned (`>=`) and there is no lockfile (`requirements.txt`). `email-validator` is required by `EmailStr` (`app/auth/schemas.py`) but not listed.

## Component and service boundaries

```
app/
  main.py            FastAPI app; create_all on startup; CORS; static mount
  config.py          frozen Settings from BSX_* env vars
  jobs.py            job lifecycle, thread pool, in-memory PDF passwords, purge
  api/routes.py      /api/health, /api/jobs*        api/auth_routes.py  /api/auth/*
  auth/              JWT + bcrypt helpers, get_current_user dependency, schemas
  db/                engine/session (base.py), ORM models (models.py)
  core/              EXTRACTION + VERIFICATION (deterministic, Decimal)
  analysis/          CREDIT ANALYSIS (deterministic, float)
  output/excel.py    11-sheet workbook writer
  static/            index.html, style.css, app.js
cli.py               shell batch runner (no tenant; uses the JSON registry)
alembic/             migration 001_initial_schema
```

**Dependency direction:** `api → jobs → core.pipeline → {core.*, analysis.profiler, output.excel}`. `analysis` depends only on the transaction dicts. `output.excel` depends on `analysis` and `core.validate`.

### Extraction pipeline (`app/core`)

```
PDF
 ├─ classify    per page: usable text layer or scanned?          classify.py:31
 ├─ layout      words with coordinates → visual lines             layout.py:6-29
 │              (scanned pages detour through ocr.py and come back as the same Word objects)
 ├─ columns     header (1- or 2-line) → whitespace corridors on   columns.py:173, 303
 │              transaction-bearing lines only → column bands
 ├─ clean       strip repeated chrome / footers / opening stubs   clean.py, extract.py:129
 ├─ rows        three strategies: balance-anchored, gap, date     rows.py:637, 656, 727
 ├─ validate    chain_score in asis|swap|rev|rev_swap picks the winner   validate.py:7; extract.py:329
 │              reconstruct() when score < 0.98; audit()          validate.py:72, 39; pipeline.py:90-97
 ├─ customer    header region only; IFSC_MAP bank resolution      customer.py:49-70
 ├─ complete    partial-PDF detection                             pipeline.py:24
 ├─ annexure    payer/payee hints from IMPS/NEFT tables           annexure.py:48, 77
 ├─ registry    linked accounts by shared email/phone/address     registry.py:160, 173
 ├─ analysis    generate_financial_profile                        analysis/profiler.py:113
 └─ excel       11 sheets                                         output/excel.py:56
```

Entry point: `process(pdf_path, out_dir, password, use_ocr, dpi, backend, progress, source_name, bank, tenant_id)` (`app/core/pipeline.py:71`). It returns a summary dict (`:144-166`) that is stored as `file_tasks.result_data`.

**Data shapes.**
- `Word(text, x0, x1, top, bottom, page)` and `Line(words)` are dataclasses (`layout.py:6, 12`).
- Rows and transactions are **plain dicts**. A transaction carries `txn_date`, `value_date`, `narration`, `reference`, `debit`, `credit`, `balance` (Decimal) and `page`, plus `_raw_lines`.
- Enrichment adds `party_hint` and `party_account`.
- The analysis layer adds `category`, `counterparty`, `counterparty_id`, `relationship` and `purpose`.

**Word fallback.** If exact header labels find nothing, extraction re-runs with `columns.WORD_FALLBACK` set. The workbook then reports "matched by words (unfamiliar layout — review)" (`extract.py:288-303`, `pipeline.py:125`).

### Credit analysis (`app/analysis`)

`profiler.generate_financial_profile(txns, info, meta, issues)` calls the modules in this order:

1. `health` (ABB, OD metrics), `account_type`
2. `classifier`: about 40 categories from regex rules plus post-passes for reversals, payroll, related parties, pass-through and personal credits; lender table in `narration_rules.LENDERS`
3. `eligible_income` → `income` → `expenses` → `debt` (EMIs, FOIR, DSCR, bounce↔loan linking)
4. `cashflow` → `channels` → `counterparties` → `risk` → `fraud_aml` → `business`
5. the scorecard

It returns `executive_summary` plus one dict per module and `annotated_transactions`. Weights, caps and grade bands are listed in `rules.md` → "Business rules of record".

## Data model and storage

MySQL tables (`app/db/models.py`; migration `alembic/versions/001_initial_schema.py`):

| Table | Key columns | Notes |
|---|---|---|
| `tenants` | id (uuid), name, plan (`free`/`starter`/`pro`), max_files=10, max_upload_mb=20 | cascades to users, jobs, registry |
| `users` | id, email (unique), hashed_password, is_active, is_superuser, tenant_id, role (`admin`/`member`) | roles not enforced anywhere |
| `jobs` | id (12-hex), tenant_id, user_id, status (`queued`/`running`/`done`/`error`), use_ocr, dpi, bank, created_at | cascades to file_tasks **and usage** |
| `file_tasks` | id (uuid4), job_id, name, path, status, progress, message, `result_data` JSON, error | `result_data` holds the full customer `info` (personal data) |
| `account_registry` | tenant_id, account_number (unique per tenant), customer_name, bank, email, phone, address | personal data, kept indefinitely |
| `usage` | tenant_id, user_id, job_id, pages, statements | billing meter; deleted when its job is purged |

**Files on disk.**
- Uploads: `{BSX_UPLOAD_DIR}/{tenant_id}/{uuid8}_{name}.pdf` (`routes.py:64-74`).
- Outputs: `{BSX_OUTPUT_DIR}/{tenant_id}/{stem}.xlsx` (`jobs.py:197`).
- CLI runs with no tenant: outputs go to the chosen directory, and the registry goes to the JSON file at `BSX_REGISTRY_PATH`.

**Schema management.**
- `create_all` runs at startup (`app/main.py:22`).
- The Docker CMD runs `alembic upgrade head`.
- A database created by `create_all` has no `alembic_version` stamp, so mixing the two paths clashes.

## API contracts

| Method | Path | Auth | Request → Response |
|---|---|---|---|
| GET | `/` | — | `index.html` |
| GET | `/api/health` | — | `{status, ocr_backend, ocr_device, gpu, cuda_compiled, ocr_warning, workers}` |
| POST | `/api/auth/register` | — | JSON `{email, password (≥8), org_name}` → 201 `{access_token, token_type}`; 409 if the email exists |
| POST | `/api/auth/login` | — | OAuth2 form `username`, `password` → `{access_token, token_type}`; 401 |
| GET | `/api/auth/me` | Bearer | `{id, email, tenant_id, role, org_name}` |
| POST | `/api/jobs` | Bearer | multipart `files[]`, `password?`, `use_ocr=true`, `dpi=300`, `bank?` → 201 `{job_id, files}` |
| GET | `/api/jobs?limit=50` | Bearer | `[job]`, tenant-scoped |
| GET | `/api/jobs/{id}` | Bearer | `{id, status, use_ocr, dpi, bank, created, progress, files:[{id, name, status, progress, message, result, error}]}`; 404 if the job is another tenant's |
| GET | `/api/jobs/{id}/download/{index}` | Bearer | xlsx; 404 / 409 not ready / 410 cleaned up |

`result` is the `process()` summary: `xlsx, filename, rows, chain, flagged, strategy, mode, reconstructed, pages, scanned_pages, is_partial, completeness, financial_profile (executive_summary), info, totals`.

**Known defect.** `jobs.get()` and `list_for_tenant()` close their session before returning (`jobs.py:75-98`). `job_to_dict()` and `download()` then lazy-load `job.file_tasks` on a detached instance, which should raise `DetachedInstanceError` (HTTP 500). This was found by reading the code and has not been reproduced. It is the first item in Phase 4.

## External integrations

None at runtime. OCR engines run in-process and are imported lazily (`app/core/ocr.py:140`). Paddle results are cached in a module global and serialised by `_INFER_LOCK`.

## Authentication and authorization

- **Tokens:** HS256 JWT with `sub` = user id and `exp` = now + `BSX_JWT_EXPIRE_HOURS` (24) (`app/auth/auth.py:40-46`). `get_current_user` rejects tokens for inactive or missing users (`auth.py:53-78`).
- **Registration:** self-service, creating a new tenant plus an `admin` user (`auth_routes.py:26`).
- **Authorization:** tenant isolation only (`routes.py:107, 119`). `role` and `is_superuser` are stored but never checked.
- **Gaps:**
  - The secret defaults to a public placeholder (`config.py:58`) and is not checked at startup.
  - There are no refresh tokens, no revocation, and no rate limiting or lockout.
  - The token is stored in `localStorage`.

## Security and privacy

Personal data processed: holder name, account number, PAN, address, email, mobile, and full transaction history. That brings in `.agents/rules/compliance/dpdp-compliance.md` (DPDP Act 2023 / Rules 2025). Its freshness entry is due 2026-10-24, so re-verify it before compliance work.

| Control | State |
|---|---|
| PDF passwords | Memory only, popped by the worker (`jobs.py:67-69, 167-168`) |
| Tenant isolation | Enforced on poll and download; uploads and outputs in tenant directories; registry tenant-scoped in MySQL |
| Upload validation | `.pdf` extension only; whole file read into memory before the size check (`routes.py:68-72`) |
| Retention | `purge()` runs only at the end of each job; it deletes jobs older than 6 h and their **uploads**. **Output xlsx files are never deleted.** Uploads of crashed jobs are never deleted (`jobs.py:130-157, 242`) |
| Erasure / rights | No endpoint. `account_registry` keeps personal data indefinitely |
| CORS | Default `*` with `allow_credentials=True` (`app/main.py:38-44`) |
| DB | Compose connects as MySQL root, port 3306 published (`docker-compose.yml`) |
| Repo hygiene | Real statements (`Bank/`, `Croped Bank PDF's/`), generated workbooks and `data/account_registry.json` are in the project tree. `.gitignore` covers `output/*`, `data/uploads/`, `.env` only. There is no `.dockerignore`, so `COPY . .` bakes them into the image |
| Error exposure | Raw exception text goes into `file_tasks.error` and is returned to the client (`jobs.py:228`) |

## Performance and scalability

- `ThreadPoolExecutor(BSX_WORKERS=4)` per process (`jobs.py:23`); the files in a job run in sequence (`:178`).
- OCR inference is serialised by a lock, so the GPU is effectively single-stream.
- The queue is in memory: a restart leaves jobs stuck in `queued`/`running` with no recovery.
- The intended scale path is Celery + Redis behind the same API (`jobs.py:9-10`). It is not built.
- The DB pool is size 10 with overflow 20 and `pool_pre_ping` (`app/db/base.py:14-21`).

## Observability

Almost none. There is a single `log.info` in `app/core/ocr.py:112`, no request logging, no metrics and no audit trail. Progress is reported through the `progress(pct, msg)` callback into `file_tasks.progress/message`. `/api/health` reports the OCR engine and device.

## Deployment and environments

| Path | Command | Notes |
|---|---|---|
| Local | `./run.sh` or `python main.py` | Creates `.venv`, serves `0.0.0.0:8000`. **Needs a reachable MySQL**, and `.env` is not loaded (no python-dotenv) |
| Docker | `docker compose up` | `db: mysql:8.0` (healthcheck, `mysql_data` volume) + `app` (build arg `OCR=1` adds paddleocr but not paddlepaddle); runs as root; CMD `alembic upgrade head && uvicorn app.main:app` |
| CLI | `python cli.py "<glob>" [--password] [--dpi] [--backend]` | Same engine, no DB needed for the registry (JSON) |

Environment variables (`app/config.py`):

| Var | Default |
|---|---|
| `BSX_UPLOAD_DIR` | `data/uploads` |
| `BSX_OUTPUT_DIR` | `output` |
| `BSX_MYSQL_URL` | `mysql+pymysql://root:…@localhost/impera_cam` |
| `BSX_REGISTRY_PATH` | `data/account_registry.json` |
| `BSX_JWT_SECRET` | placeholder — **must** be set |
| `BSX_JWT_EXPIRE_HOURS` | 24 |
| `BSX_MAX_UPLOAD_MB` | 40 |
| `BSX_MAX_FILES` | 25 |
| `BSX_WORKERS` | 4 |
| `BSX_RETENTION_SECONDS` | 21600 |
| `BSX_OCR_BACKEND` | paddle |
| `BSX_OCR_DEVICE` | gpu |
| `BSX_OCR_GPU_ID` | 0 |
| `BSX_ALLOWED_ORIGINS` | `*` |

## Testing strategy

**Current:** no automated tests. `tests/` does not exist, although the README mentions it. Verification has been manual: `cli.py` and `scratch/batch_process_all.py` over the sample statements, plus reading the workbooks. `verify_fix.py` points at workbook names that no longer exist.

**Target (Phase 4):**
1. **Golden-file regression.** For each sample statement, assert the row count, chain score, chain mode, strategy and flagged count, plus selected analysis outputs (score, grade, FOIR, bounce count). Expectations are stored without personal data, keyed by a file hash, not the holder.
2. **Unit tests** for `normalize.parse_amount` / `parse_date`, `validate.chain_score` / `reconstruct`, and the classifier rules.
3. **API tests** against a throwaway MySQL (or a SQLAlchemy URL override): auth, tenant isolation, and the job lifecycle. These would have caught the detached-session defect.

## Architectural decisions and consequences

| # | Decision | Consequence |
|---|---|---|
| AD-1 | The **balance chain is the ground truth**. All strategy choice and row trust route through `validate.chain_score` | Layout-agnostic correctness signal. A statement without running balances can't be verified |
| AD-2 | **Column bands come from ink (whitespace corridors), not header label positions**, measured on transaction lines only | Survives labels offset from their data and second tables on the page. Bands are pooled per document, not per page |
| AD-3 | **Balance-anchored rows**, with wrapped fragments split at the largest vertical gap | One rule covers HDFC, JPCB and Canara wrap styles |
| AD-4 | **Three competing strategies, scored**, rather than one tuned parser | Robust, at about 3× row-assembly cost |
| AD-5 | **Decimal in core, float in analysis and output** | Exact verification. Analysis tolerances are float (±0.5, ±1%, ±5%) |
| AD-6 | **Deterministic, rule-based classification and scoring; no LLM** | Explainable and reproducible scores. Rules need manual upkeep per bank and narration format |
| AD-7 | **The OCR path emits the same `Word` schema** as the digital path | Nothing downstream branches on scanned vs digital |
| AD-8 | **Per-tenant account registry** (MySQL), with a JSON fallback for the CLI | Related-party linking without cross-tenant leakage. The JSON file holds personal data on disk |
| AD-9 | **PDF passwords are never persisted** | Restart loses in-flight passwords, so those jobs fail |
| AD-10 | **In-process thread pool**, not a queue service | Simple single-host deployment. No restart recovery and no horizontal scale yet |

## Diagrams

See System context and Extraction pipeline above.

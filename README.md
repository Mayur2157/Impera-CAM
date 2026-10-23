# Impera CAM — Bank Statement Extractor (SaaS edition)

Turns Indian bank statement PDFs into an underwriting workbook: verified
transactions, account details and a scored Credit Appraisal Memo (CAM). No
template per bank, and multi-tenant, for lenders.

The design premise is that extracting rows is the easy half. The hard half is
**proving the rows are right**, and Indian statements hand you the proof for
free: every row prints a running balance. So the pipeline reconstructs the table,
then checks `previous balance − debit + credit == balance` on every row and
reports the pass rate. Rows that fail are highlighted rather than shipped
quietly.

Verified 2026-10-14 on 13 real statements from 13 banks: **6,278 rows, all 13 at
a 100% balance chain**, 0.3–7 s per statement on one CPU core
(`tests/baseline/extraction.json`).

Design and architecture of record live in [`agentic/`](agentic/): start with
`agentic/architecture.md` and `agentic/features/saas-scale/`.

---

## Quick start (local, no Docker)

Needs Python 3.12 (Paddle's GPU build requires it) and Node.js 20+ for the portal.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt -c requirements.lock

# the portal (React); build once, or see "Working on the portal" below
cd frontend
npm install
npm run build
cd ..

.\.venv\Scripts\python main.py
```

Open <http://localhost:8000>, create an account, upload PDFs, read results and
download workbooks. `python main.py` needs no configuration:

- the database is a SQLite file, `data/impera_cam.db`, brought up to date with
  Alembic on every start;
- jobs run on threads inside the API process (`BSX_QUEUE=local`): two digital
  statements at a time (`BSX_LOCAL_WORKERS`) plus one thread for the GPU;
- expired uploads and workbooks are purged on a background thread.

Interactive API docs are at `/docs`; `GET /api/health` shows the database and
the OCR device. The original single-page uploader is still at `/legacy`.

Stopping the server stops processing: files still waiting or running are marked
failed on the next start ("upload it again"), because the local queue lives in
memory. `--reload` restarts the process on every code change, with the same effect.

### Working on the portal

```powershell
.\.venv\Scripts\python main.py        # API on :8000
cd frontend; npm run dev                  # portal on http://localhost:5173, /api proxied to :8000
```

Before calling portal work done: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.

### Accounts

There are no built-in accounts. `/signup` creates an organisation and makes you
its **owner**. Until the team and admin screens exist, change roles in the
database (`sqlite3 data/impera_cam.db`, or any SQLite browser):

```sql
UPDATE users SET is_superuser = 1 WHERE email = 'you@example.com';          -- Impera staff
UPDATE users SET role = 'admin' WHERE email = 'colleague@example.com';      -- owner | admin | member
```

Sign out and in again afterwards.

---

## Scanned statements (GPU OCR)

Scanned pages are detected per page (a statement is often a scanned cover page
stapled to a digital table) and read with PaddleOCR on the GPU, which returns
the *same* `Word` objects the digital path returns. Nothing downstream knows the
difference. In local mode the GPU thread lives in the API process; install the
GPU build into the same virtual environment:

```powershell
# RTX 50-series (Blackwell) needs the CUDA 12.9 build; RTX 40-series and older can use cu126
.\.venv\Scripts\python -m pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu129/
.\.venv\Scripts\python -m pip install -r requirements-ocr.txt
```

`python main.py` prints the OCR device it found (`device=gpu:0`). Without a GPU,
set `BSX_OCR_DEVICE=cpu`.

Do not install CPU `paddlepaddle` next to `paddlepaddle-gpu` — it shadows the
GPU wheel. **On quality, plainly:** Tesseract (the CPU fallback) misreads
amounts badly enough that the balance chain collapses; use the GPU for
scanned work, and treat a low chain score as a signal to re-scan at higher
resolution.

---

## Running on a server (MySQL, Redis, Celery workers)

Local mode is one process. For many concurrent users, run the API and the
workers separately against MySQL and Redis:

```bash
export BSX_ENV=prod BSX_QUEUE=celery        BSX_MYSQL_URL=mysql+pymysql://impera:<pw>@<host>:3306/impera_cam        BSX_REDIS_URL=redis://<host>:6379/0 BSX_JWT_SECRET=<64 hex chars>        BSX_ALLOWED_ORIGINS=https://<your domain>
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
celery -A app.worker worker -Q cpu -c 8                     # digital statements
celery -A app.worker worker -Q ocr --pool=solo -n ocr@%h    # one per GPU
celery -A app.worker beat                                   # purge + stuck-file reaper
```

Every process needs the **same `BSX_JWT_SECRET`**: it also decrypts queued PDF
passwords. Keep Redis persistence off (`agentic/rules.md` H10). `BSX_ENV=prod`
refuses to start on SQLite, local mode, placeholder secrets or `*` origins.

Command line, same engine, no database or queue needed:

```bash
python cli.py "statements/*.pdf"
python cli.py "locked.pdf" --password hunter2
python cli.py "scans/*.pdf" --dpi 400 --backend paddle
```

---

## What comes out

An 11-sheet workbook: Financial_Profile (the CAM: score, grade, hard caps,
strengths, red flags), Income_Analysis, Monthly_Analysis, Transactions,
Customer_Info, Debt_Obligations, Counterparties, Risk_Anomaly_Flags,
Validation, PDF_Field_Validation, Calculation_Reconciliation. Dates are real
dates and money is real numbers; rows failing the balance check are shaded and
marked `CHECK`. Sheet-by-sheet detail: `agentic/design.md`.

---

## How it works

```
PDF
 ├─ classify   per page: real text layer, or scanned?
 ├─ layout     words with coordinates → visual lines      (identical schema
 │             scanned pages take the OCR detour here      for both paths)
 ├─ columns    find header (1- or 2-line) → whitespace
 │             corridors → column bands
 ├─ rows       three competing assembly strategies
 ├─ validate   balance chain scores them; best wins
 ├─ customer   account details from above the table only
 ├─ analysis   classification, income, debt, risk → 100-point CAM score
 └─ excel      11 sheets
```

**Bands come from ink, not from header positions.** Header labels rarely sit
over their data — Bandhan's `DEBITS` label is 40pt left of its right-aligned
values. So column boundaries are whitespace corridors measured on
transaction-bearing lines only. Measuring on all lines lets a footer disclaimer
or a second table on the same page destroy the geometry.

**Rows are anchored on the balance.** Every printed row carries exactly one
running balance, so balance-bearing lines map 1:1 onto transactions. Wrapped
lines are attached by splitting each fragment run at its largest vertical gap.
That one rule covers HDFC (narration spills *below* its amounts), JPCB (amounts
arrive four lines *after* the narration starts) and Canara (date vertically
centred inside a seven-line cell).

**The balance chain picks the strategy.** Balance-anchored, gap-clustered and
date-anchored assembly all run; whichever scores highest wins. The chain is also
tried debit/credit-swapped and reverse-chronological, which is how a statement
printing newest-first gets caught.

**Out-of-order statements are relinked.** One bank in the sample prints rows
sorted by transaction date while the running balance follows posting order. Each
row states the predecessor balance it requires (`prev = balance + debit −
credit`), so `validate.reconstruct()` rebuilds the true sequence. The rows it
cannot link uniquely are flagged, not guessed.

---

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | create an organisation + admin user; returns a JWT (rate limited) |
| `POST` | `/api/auth/login` | — | OAuth2 password form; returns a JWT (rate limited) |
| `GET` | `/api/auth/me` | Bearer | current user and organisation |
| `GET` | `/api/health` | — | database, Redis, queue depths, live workers, OCR device |
| `POST` | `/api/jobs` | Bearer | multipart upload (`files`, `password`, `use_ocr`, `dpi` 200/300/400, `bank`); returns a `job_id` immediately |
| `GET` | `/api/jobs` | Bearer | this organisation's recent jobs (summary results) |
| `GET` | `/api/jobs/{id}` | Bearer | status, per-file progress and full results |
| `GET` | `/api/jobs/{id}/download/{index}` | Bearer | the `.xlsx` for one file |

```bash
TOKEN=$(curl -s -d "username=you@lender.com&password=..." localhost:8000/api/auth/login | jq -r .access_token)
JOB=$(curl -s -H "Authorization: Bearer $TOKEN" -F "files=@stmt.pdf" localhost:8000/api/jobs | jq -r .job_id)
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/jobs/$JOB | jq
curl -sOJ -H "Authorization: Bearer $TOKEN" localhost:8000/api/jobs/$JOB/download/0
```

Errors worth knowing: `400` not a PDF / wrong PDF password / over the size
limit; `429` too many of your files still processing, or too many login
attempts; `503` the queue is down.

---

## Settings

All via environment variables (`app/config.py`); `.env.example` lists them.

| Variable | Default | |
|---|---|---|
| `BSX_ENV` | `dev` | `prod` refuses to start with a placeholder JWT secret, `*` CORS, MySQL root, SQLite or local mode |
| `BSX_MYSQL_URL` | `sqlite:///data/impera_cam.db` | SQLAlchemy URL |
| `BSX_QUEUE` | `local` | `local` = threads in the API process; `celery` = Redis + worker processes |
| `BSX_LOCAL_WORKERS` | 2 | digital statements processed at once in local mode |
| `BSX_REDIS_URL` | `redis://localhost:6379/0` | broker + counters (celery mode) |
| `BSX_JWT_SECRET` | placeholder | also keys the encryption of queued PDF passwords |
| `BSX_ALLOWED_ORIGINS` | `*` | comma-separated exact origins in prod |
| `BSX_TENANT_MAX_ACTIVE_FILES` | 50 | queued + running files per organisation |
| `BSX_LOGIN_PER_MINUTE` / `BSX_REGISTER_PER_HOUR` | 10 / 5 | per client IP |
| `BSX_RETENTION_SECONDS` | 21600 | jobs, uploads and workbooks older than this are purged |
| `BSX_TASK_CPU_*` / `BSX_TASK_OCR_*` | 600/720 s, 1800/2100 s | soft/hard time limit per file |
| `BSX_BROKER_VISIBILITY_SECONDS` | 2400 | after a worker crash, its file is redelivered after this |
| `BSX_DB_POOL_SIZE` / `BSX_DB_MAX_OVERFLOW` | 10 / 10 | per process |
| `BSX_OCR_BACKEND` / `BSX_OCR_DEVICE` / `BSX_OCR_GPU_ID` | paddle / gpu / 0 | OCR worker |
| `BSX_UPLOAD_DIR` / `BSX_OUTPUT_DIR` | `data/uploads` / `output` | shared by API and workers |

---

## Tests and load test

```bash
pip install -r requirements-dev.txt -c requirements.lock
pytest tests                                                 # API, queue, registry, baseline
python tests/baseline/make_baseline.py "Bank/*.pdf" --check  # CAM output unchanged?
locust -f loadtest/locustfile.py --headless -u 100 -r 10 -t 15m --host http://<lan-ip>:8000
```

The baseline test runs only where the sample statements exist locally; they
contain personal data and are never committed. For a load run from one
machine, raise `BSX_REGISTER_PER_HOUR` and `BSX_LOGIN_PER_MINUTE` first. Local
mode is one process; load-test the server setup (celery mode) for capacity figures.

---

## Adding a bank

Usually nothing to do. If a header uses a label not seen before, add its regex
to `SYNONYMS` in `app/core/columns.py`. To name a bank whose logo is an image,
add its IFSC prefix to `IFSC_MAP` in `app/core/customer.py`. Then run the
baseline check above.

---

## Verified layouts

Jalgaon Peoples Co-op, Dombivli Nagari Sahakari, Bharat Co-op, Bandhan, HDFC,
Kotak, SBI, Cosmos Co-op (savings and current), United Bank of India, Union
Bank, Bank of Baroda, Canara.

Between them these cover: separate debit/credit columns and a single amount
column with a Dr/Cr flag; `Cr`/`Dr` suffixes, parenthesised negatives and bare
minus signs; lakh grouping (`1,00,99,262.60`) and Western grouping in the same
document; dates split across two lines; reversed column order; overdraft
accounts printing negative balances; reverse-chronological order; rows whose
print order differs from posting order; and a second unrelated table on the same
page.

---

## Not built yet

See `agentic/phases.md`. In short: known scoring defects (Phase 5), account
lockout, role enforcement, data erasure and TLS (Phase 6), and showing the CAM
in the browser (Phase 7).

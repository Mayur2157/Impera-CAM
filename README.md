# Bank Statement Extractor

Turns Indian bank statement PDFs into Excel workbooks — transactions on one
sheet, account details on another — without a template per bank.

The design premise is that extracting rows is the easy half. The hard half is
**proving the rows are right**, and Indian statements hand you the proof for
free: every row prints a running balance. So the pipeline reconstructs the table,
then checks `previous balance − debit + credit == balance` on every row and
reports the pass rate. Rows that fail are highlighted rather than shipped
quietly.

Verified on 13 real statements from 13 different banks: **1,825 rows, 12 at a
100% balance chain, one at 98.6%.**

---

## Quick start

```bash
git clone <your remote> bank-statement-extractor
cd bank-statement-extractor
./run.sh                    # creates .venv, installs, serves on :8000
python main.py              # same server, once the venv is set up
```

Then open <http://localhost:8000>, drop PDFs, download workbooks.

Command line, same engine:

```bash
python cli.py "statements/*.pdf"
python cli.py "locked.pdf" --password hunter2
python cli.py "scans/*.pdf" --dpi 400 --backend paddle
```

Interactive API docs are at `/docs`.

---

## What comes out

**Transactions** — S.No, Txn Date, Value Date, Narration, Reference, Debit,
Credit, Balance, Type, Page, Status. Dates are real dates and money is real
numbers, so the sheet is ready to pivot. Rows failing the balance check are
shaded and marked `CHECK`.

**Customer_Info** — bank, customer name, account number, account type, customer
id, IFSC, MICR, branch, address, email, phone, PAN, statement period, plus
derived totals and opening/closing balance.

**Validation** — row assembly strategy chosen, chain orientation, pass rate,
count of flagged rows, and the specific rows that broke with their rupee
difference. This is the sheet you show a client to justify trusting the rest.

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
 └─ excel      Transactions / Customer_Info / Validation
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
credit`), so `validate.reconstruct()` rebuilds the true sequence — 128 of 144
rows into a chain that verifies at 100%. The rows it cannot link uniquely are
flagged, not guessed.

---

## Scanned statements

Scanned pages are detected per page (a statement is often a scanned cover page
stapled to a digital table) and routed through OCR, which returns the *same*
`Word` objects the digital path returns. Nothing downstream knows the
difference.

Install the GPU engine (Python 3.12, RTX 40-series, driver ≥ 550):

```bash
pip uninstall -y paddlepaddle paddlepaddle-gpu
pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
pip install -r requirements-ocr.txt
```

Do not install CPU `paddlepaddle` from PyPI — it shadows the GPU wheel. Confirm
with `GET /api/health`: `ocr_device` should be `gpu:0` and `cuda_compiled` true.
With none installed, scanned pages fall back to whatever text layer exists
rather than being dropped. Override with `BSX_OCR_DEVICE=cpu` if you must.

**On quality, plainly:** the tesseract fallback was tested on a 200 dpi rescan
of the United Bank statement. It found the table and read dates and narration,
but misread enough of the amount columns that the balance chain fell to 15% and
39 of 47 rows came back marked `CHECK`. That is the system behaving correctly —
it refused to present unverified numbers as clean — but it is not a usable
result. Use PaddleOCR for scanned work, and treat a low chain score as a signal
to re-scan at higher resolution rather than a reason to trust the output.

---

## Layout

```
main.py              entry point — python main.py  (serves on :8000)
app/
  main.py            FastAPI app, serves the API and the page
  config.py          settings, all overridable by environment variable
  jobs.py            in-memory job store + thread pool
  api/routes.py      POST /api/jobs, GET /api/jobs/{id}, download
  core/
    classify.py      digital vs scanned, per page
    layout.py        words and visual lines — the shared schema
    ocr.py           paddle / tesseract, emits the same Word objects
    columns.py       header detection and column bands
    rows.py          the three row-assembly strategies
    normalize.py     Indian money and date parsing, all Decimal
    validate.py      balance chain, audit, chain reconstruction
    customer.py      account details, IFSC-prefix bank resolution
    extract.py       orchestrates a document
    clean.py         footer / header chrome and opening-balance stubs
    pipeline.py      one PDF in, one workbook out
  output/excel.py    the workbook writer
  static/            index.html, style.css, app.js — no build step
cli.py               batch runs from a shell
tests/               parsing tests
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | liveness, active OCR engine, worker count |
| `POST` | `/api/jobs` | multipart upload; returns a `job_id` immediately |
| `GET` | `/api/jobs/{id}` | status, per-file progress and results |
| `GET` | `/api/jobs/{id}/download/{index}` | the `.xlsx` for one file |

```bash
JOB=$(curl -s -F "files=@stmt.pdf" localhost:8000/api/jobs | jq -r .job_id)
curl -s localhost:8000/api/jobs/$JOB | jq
curl -sO -J localhost:8000/api/jobs/$JOB/download/0
```

Settings via environment: `BSX_UPLOAD_DIR`, `BSX_OUTPUT_DIR` (defaults to
`output/` at the project root),
`BSX_MAX_UPLOAD_MB` (40), `BSX_MAX_FILES` (25), `BSX_WORKERS` (4),
`BSX_RETENTION_SECONDS` (6h), `BSX_OCR_BACKEND` (paddle), `BSX_OCR_DEVICE`
(gpu), `BSX_OCR_GPU_ID` (0).

---

## Adding a bank

Usually nothing to do. If a header uses a label not seen before, add its regex
to `SYNONYMS` in `app/core/columns.py`. To name a bank whose logo is an image,
add its IFSC prefix to `IFSC_MAP` in `app/core/customer.py`.

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

- Persistent job storage (jobs live in memory; restart clears them)
- Authentication — do not expose this on a public port as-is
- Category tagging and cashflow summaries on top of the extracted rows
- Bank name for issuers that print it only as a logo and carry no IFSC in the
  header (two of the thirteen); account number, customer and period still extract

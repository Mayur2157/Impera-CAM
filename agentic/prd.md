# Product Requirements Document

> Status: draft · Last updated: 2026-10-14
> Written retroactively from the as-built code (no prior kickoff). Statements marked *(inferred from code)* describe intent read from the implementation, not a stated decision. Items confirmed by the product owner are marked *(confirmed)*.

## Product vision

Impera CAM turns an Indian bank-statement PDF into an underwriting-ready Credit Appraisal Memo (CAM) workbook. It covers any bank and any layout, with no per-bank template. Every number it shows can be traced back to the statement's own printed running balance.

## Problem statement

Lenders appraise borrowers largely from bank statements. Each Indian bank (and many co-operative banks) prints a different layout: separate debit/credit columns or a single amount column with a Dr/Cr flag, lakh grouping, wrapped narrations, reverse-chronological order, scanned cover pages, and overdraft accounts printing negative balances. Analysts re-key or template-map these by hand, which is slow, error-prone and impossible to audit.

Extracting rows is the easy half. The hard half is **proving the rows are right**. Indian statements print a running balance on every row, which gives a free per-row proof: `previous balance − debit + credit == balance`.

## Target users and needs

*(confirmed)* External multi-tenant SaaS for lenders.

| User | Need |
|---|---|
| Credit analyst / underwriter at an NBFC, bank or co-operative bank | Upload statements, get a verified transaction table and a scored financial profile, and see which rows need a human |
| DSA / loan aggregator | Batch-process applicant statements quickly, without a template per bank |
| Tenant admin | Register the organisation, manage users within plan limits (roles exist but are not yet enforced) |

Current workaround: manual re-keying, per-bank templates in generic PDF tools, or opaque third-party analysers whose numbers can't be audited.

## Goals

1. Extract transactions from any Indian bank layout without bank-specific templates.
2. Make correctness visible: score every statement by balance-chain pass rate, and flag rather than hide rows that fail.
3. Produce an underwriting profile covering eligible income, debt service, FOIR/DSCR, ABB, OD utilisation, bounces, AML signals and concentration. The output is an explainable 100-point score with hard caps and a risk grade.
4. Serve many lender organisations from one deployment, with tenant isolation of data, files and cross-statement linking.

## Non-goals

- No credit *decision* or sanction. The product informs an underwriter; it does not approve loans.
- No LLM or generative model in the extraction or scoring path *(inferred from code: none present)*.
- No bank-account aggregation APIs (Account Aggregator / open banking). The input is PDF only.
- No editing or correction of rows in the UI. Corrections happen in the downloaded workbook.
- No CIBIL or bureau integration.

## Use cases and user stories

- As an analyst, I upload one or more statement PDFs (optionally password-protected) and download one workbook per statement.
- As an analyst, I see per statement the row count, the balance-check pass rate and the number of rows needing review, before I open the workbook.
- As an analyst, I can trust a 100%-chain statement's numbers and focus my review on rows marked `CHECK`.
- As an analyst, I get a scored CAM: score, grade, binding hard caps, strengths and red flags, each with its evidence sheet.
- As an analyst, I see when a statement is a partial excerpt (missing pages or a truncated period).
- As an analyst, I see accounts of other holders already processed by my organisation who share this holder's email, phone or address (related-party signal).
- As a tenant admin, I register my organisation and sign in. My data is invisible to other tenants.
- As an operator, I can run the same engine from a shell over a folder of PDFs (`cli.py`).

## Functional requirements

**FR-1 Ingest.**
- Accept PDF uploads, multipart, several per job (`app/api/routes.py:41`).
- Accept an optional PDF password, which is never persisted (`app/jobs.py:7`).
- Accept an optional user-supplied bank name, used only when the statement doesn't print it (`app/core/pipeline.py:105`).
- Enforce per-tenant file-count and size limits (`routes.py:53-58`).

**FR-2 Page classification.** Decide per page whether a page has a usable text layer or needs OCR (`app/core/classify.py:31`). Scanned pages use PaddleOCR (GPU) or Tesseract and yield the same `Word` objects as digital pages (`app/core/ocr.py`).

**FR-3 Table reconstruction.**
- Detect the header (single- or two-line) and derive column bands from whitespace corridors on transaction-bearing lines (`app/core/columns.py:173, 303`).
- Run three row-assembly strategies — balance-anchored, gap-clustered and date-anchored — and keep the one with the best balance-chain score (`app/core/extract.py:307-331`).

**FR-4 Normalisation.** Money is parsed to `Decimal`, handling Indian grouping, Cr/Dr suffixes, parentheses and minus signs. Dates are parsed to real dates (`app/core/normalize.py`).

**FR-5 Verification.**
- Score the balance chain in four orientations: as-is, debit/credit swapped, reversed, reversed-and-swapped (`app/core/validate.py:7`).
- Below 0.98, attempt chain reconstruction for print-order ≠ posting-order statements (`pipeline.py:90-95`).
- Flag rows that fail, not gaps already present in the PDF (`validate.py:39`).

**FR-6 Account details.** Extract bank, holder, account number/type, IFSC, MICR, branch, address, contact details, PAN, period and OD limit, from the region above the table only. The bank is resolved via an IFSC-prefix map (`app/core/customer.py`).

**FR-7 Completeness.** Detect partial PDFs from page footers and from the gap between the last transaction and the end of the period (`pipeline.py:24`).

**FR-8 Enrichment.**
- Attach payer/payee names from IMPS/NEFT/RTGS annexure tables (`app/core/annexure.py`).
- Link holders across statements within a tenant (`app/core/registry.py`).

**FR-9 Credit analysis.** Produce an 8-component, 100-point scorecard with hard caps and a risk grade (`app/analysis/profiler.py:113`). The components are cash-flow margin 20, liquidity/ABB 15, DSCR/FOIR 15, EMI regularity 10, OD/facility compliance 15, bounces 10, AML 10, concentration 5. Unmeasurable components are dropped and the rest rescaled (`profiler.py:626-632`).

**FR-10 Workbook.** Write 11 sheets: Financial_Profile, Income_Analysis, Monthly_Analysis, Transactions, Customer_Info, Debt_Obligations, Counterparties, Risk_Anomaly_Flags, Validation, PDF_Field_Validation, Calculation_Reconciliation (`app/output/excel.py:56`). Failing rows are shaded and marked `CHECK`.

**FR-11 Jobs.**
- Processing runs asynchronously, with per-file progress and status polling.
- Downloads are gated by tenant (`routes.py:101-140`).
- There is a job history per tenant (`routes.py:91`).

**FR-12 Accounts.**
- Self-service registration creates a tenant and an admin user.
- Email/password login returns a JWT (`app/api/auth_routes.py`).

**FR-13 CLI.** Batch extraction from a shell with the same engine (`cli.py`).

## Non-functional requirements

- **Accuracy:** a balance chain ≥ 0.98 is the threshold below which the engine attempts relinking (`pipeline.py:17`). The chain tolerance is ₹0.02 (`validate.py:4`).
- **Integrity:** money stays `Decimal` through extraction and verification. Unverified rows are never presented as clean.
- **Isolation:** every job, file, output and registry entry is scoped to a tenant.
- **Privacy:**
  - PDF passwords are held in memory only.
  - Personal data is subject to India's DPDP Act (see `.agents/rules/compliance/dpdp-compliance.md`).
  - Retention is currently 6 h for jobs and uploads (`app/config.py:67`), but output workbooks are not purged (see Risks).
- **Limits:** default 25 files / 40 MB globally, overridden per tenant (10 / 20 by default) (`config.py:62-63`, `app/db/models.py:44-45`).
- **Throughput:** 4 worker threads by default; the files within one job run in sequence (`app/jobs.py:23, 178`).
- **OCR:** GPU PaddleOCR is the supported quality path. The Tesseract fallback is not fit for amounts (README: 15% chain on a 200 dpi rescan).

## Success metrics

| Metric | Current evidence | Target |
|---|---|---|
| Statements at 100% balance chain | 12 of 13 sample statements (README; not re-run this session) | Maintain on every verified layout; no regression |
| Rows verified across the sample set | 1,825 rows (README) | Tracked per release via a regression suite (Phase 4) |
| Banks/layouts verified | 13 banks | TBD — product owner |
| Analyst time per statement | Not measured | TBD — product owner |

## Constraints and dependencies

- Python 3.12, FastAPI, SQLAlchemy 2 and Alembic on **MySQL 8** (required at startup), pdfplumber, openpyxl.
- Optional PaddleOCR GPU, which needs an RTX-class GPU with CUDA 12.6 wheels installed by hand.
- Deployment is a Docker image plus docker-compose. Docker is the only path that loads `.env`.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Real customer statements and a registry containing personal data sit inside the project tree, not git-ignored, and are baked into the Docker image | Phase 4: move out of the repo, `.gitignore` + `.dockerignore`, anonymised fixtures |
| No automated tests; scoring tuned by hand against sample PDFs | Phase 4: golden-file regression suite |
| Score inflation/deflation from known scoring defects (see `memory.md`) | Phase 4 fixes, each with a recorded decision |
| Weak production security defaults (JWT secret, CORS, MySQL root) | Phase 5 |
| DPDP obligations (retention, erasure, notice) not implemented | Phase 5, after re-verifying the DPDP rule's freshness |
| README describes an older product; agents and new developers are misled | Phase 4: rewrite README; `agentic/` is the source of record |

## Open questions

| Question | Critical? | Owner | Status |
|---|---|---|---|
| Pricing and plan model beyond `tenants.plan` (free/starter/pro) and the `usage` meter | No | Product owner | Open |
| Target lender segment (NBFC vs bank vs co-op vs DSA) and its scoring calibration | No | Product owner | Open |
| Data residency and hosting region | No | Product owner | Open |
| Under DPDP, is Impera a data processor for the lender, or a fiduciary? | No for documentation; **yes before Phase 5** | Product owner + counsel | Open |
| Required SLA and processing-time targets | No | Product owner | Open |
| Should roles (admin/member) and invitations be enforced, or is self-registration per organisation intended? | No | Product owner | Open |
| Will an LLM ever write CAM narrative text? (It would trigger `.agents/rules/ai/*`) | No | Product owner | Open |

## Acceptance criteria

For the current release (as-built):

- Every sample statement in `Bank/` produces a workbook with all 11 sheets.
- The chain pass rate is reported on the Validation sheet and in the API result.
- Failing rows are marked `CHECK`, never silently dropped.
- A user in tenant A can't list, poll or download tenant B's jobs (`routes.py:107, 119`).

## Release scope

The current version is 2.0.0 (`app/main.py:33`): extraction engine, credit analysis layer, and the multi-tenant web platform. Next, Phase 4 (Hardening), then Phase 5 (Security & DPDP). See `phases.md`.

# Project Memory

> Last updated: 2026-10-14
> Durable product decisions and state. Session-level state belongs in `HANDOVER.md`.

## Approved decisions and rationale

| Date | Decision | Rationale | Source |
|---|---|---|---|
| 2026-10-14 | Impera CAM is **external multi-tenant SaaS for lenders** (NBFCs, banks, co-ops, DSAs) | Matches the tenant/plan/usage model already built | Product owner, this session |
| 2026-10-14 | **Next phase is Hardening** (Phase 4), before new features or compliance work | No tests, a likely API crash, and scoring defects make further building risky | Product owner, this session |
| 2026-10-14 | `agentic/` written retroactively from the code is the source of record; `README.md` is secondary | The README predates auth, the DB and the analysis layer | Plan approval, this session |
| pre-2026-10 *(inferred)* | Balance chain as ground truth; bands from ink; balance-anchored rows; three scored strategies; Decimal core; OCR emits the same `Word` schema; deterministic rule-based scoring; per-tenant registry; passwords never persisted; in-process thread pool | See `architecture.md` AD-1 to AD-10 | Code and README |

model/version: not recorded for pre-existing decisions; this session ran on claude-opus-5-5.

## Current progress

- Phases 1–3 are `complete` as built. Phase 4 is `not-started`. See `phases.md`.
- The app version string is 2.0.0 (`app/main.py:33`).
- The README's verification claim (13 statements, 1,825 rows, 12 at a 100% chain) was **not re-run** this session.

## Important context

- **There is no git repository.** `D:\Company Projects\Impera CAM` is not under version control, so we can't tell what has been shared. Initialising git is a prerequisite for Phase 4 review workflow (ask first).
- **The README is stale.** It says there is no auth, no persistence and no analysis, and lists 3 sheets with an in-memory job store and a `tests/` folder. None of that is current.
- **MySQL is required to start the web app** (`create_all` in the lifespan). The CLI runs without it and uses the JSON registry.
- `.env` is loaded only by docker-compose. `python main.py` reads OS environment variables only.
- Tenant plan defaults (10 files / 20 MB) override the global settings (25 / 40) for every registered user.
- Analysis docstrings name the sample banks that drove each rule. Treat those comments as the test oracle until Phase 4 replaces them.

## Active risks

Ranked by impact. All were found by reading the code and **none has been reproduced** unless marked otherwise.

1. **Personal data inside the project tree:**
   - real statements in `Bank/` and `Croped Bank PDF's/`
   - generated workbooks in `output/`
   - holder identities in `data/account_registry.json`

   None are git-ignored except `output/*`. There is no `.dockerignore`, so all of it is copied into the Docker image. → Phase 4 #3.
2. **Job poll/list/download likely 500.** `jobs.get()` and `list_for_tenant()` close the session, then `job.file_tasks` lazy-loads on a detached instance (`app/jobs.py:75-98`, `routes.py:109, 122`). → Phase 4 #1.
3. **No automated tests.** Every change to the extraction or scoring rules is unguarded. → Phase 4 #2.
4. **Scoring defects that move the CAM score:**
   - Bounces may be counted twice: the reversed debit and the credit are both marked `bounce_side=OWN` (`classifier.py:744-749`, `returns.py:60-61`, `debt.py:192`). This can trigger cap 45.
   - Structuring always scores ≥ MEDIUM without trade wording. Cash points are a constant 30, and the LOW branch is unreachable (`fraud_aml.py:150-199`). A cash amount within 1% of a threshold → HIGH → C7 = 0, cap 65.
   - OD utilisation averages only negative-balance days (`health.py:174-176`). An OD that stays in credit gets turnover None, scored as 0× "sluggish" (`health.py:173`, `profiler.py:330`).
   - `"RENT" in narr` matches CURRENT, PARENT and TORRENT, and can block all rental income (`eligible_income.py:117-119`).
   - One SALARY credit switches a business account to retail FOIR and the salaried persona (`income.py:61`).
   - A payer named "… Capital" is treated as a capital infusion (`eligible_income.py:147`).
   - A cash deposit with SALE/BILL wording is counted as revenue, contradicting the cash-never-verified rule (`classifier.py:233-234`).
   - The circular-flow check excludes the wrong names and can flag lenders (`fraud_aml.py:238`).
   - The fallback uses non-existent category names (`debt.py:333`).
   - TAX_GST, along with EPFO/ESIC/PF, is excluded from operating expenses, which inflates DSCR. **This is a policy question, not a bug.**
5. **Validation the workbook overstates:**
   - `validate_field_linkage` checks presence only, so debit/credit can never FAIL (`validate.py:111`).
   - Balance Chain reconciliation hard-codes "100.00%" / "0 Breaks" (`excel.py:1271, 1299`).
   - "Operating Cash Coverage" duplicates the DSCR formula (`excel.py:1253`).
   - The opening balance is computed as-is even in swap mode, and `mode` isn't refreshed after `reconstruct()` (`pipeline.py:88-112`).
6. **Inconsistent policy constants:**
   - FOIR bands are 35/50 in `debt.py` but 30/45/55 in `profiler.py`; business bands are 30/50 vs 15/40.
   - Concentration MODERATE is 40% (`counterparties`) vs 35% (`business`).
   - Turnover months use ÷30 vs ÷30.4.
7. **Security defaults:**
   - placeholder JWT secret not enforced
   - CORS `*` with credentials
   - MySQL root with 3306 published
   - self-registration, with roles never enforced
   - token in localStorage
   - `python-jose` versions with known CVEs allowed
   - `passlib` + unpinned `bcrypt` (bcrypt 5 breaks passlib 1.7.4) → Phase 5 / Phase 4 #5
8. **Retention:**
   - output workbooks are never deleted
   - uploads of crashed jobs are never deleted
   - `usage` (billing) rows cascade-delete with purged jobs
   - no erasure endpoint; the registry keeps personal data indefinitely → Phase 5
9. **Operational:**
   - no restart recovery for queued or running jobs
   - `email-validator` missing from requirements
   - `create_all` vs Alembic stamp clash
   - `verify_fix.py` references workbooks that no longer exist
   - `annexure.py:52-55` can raise `StopIteration`
   - `columns.py:329` `runs[ib-1]` wraps when `ib == 0`
10. **Frontend:** `--accent` undefined (broken focus ring and colours on the auth UI); no `aria-live`; `innerHTML` with server text. → Phase 6

## Unresolved noncritical questions

These are mirrored from `prd.md` → Open questions: pricing/plans, target lender segment, data residency, DPDP role (processor vs fiduciary, which is **critical before Phase 5**), SLAs, role enforcement, and future LLM narrative.

## Changes affecting future work

- Any change to scoring constants must update `rules.md` → Business rules of record, plus this file ([H4]).
- Before Phase 5, re-verify `.agents/config/freshness.json` → `dpdp-compliance` (last verified 2026-07-26, due 2026-10-24).
- If an LLM is ever introduced (CAM narrative, classification), `.agents/rules/ai/ai-applications.md` and `accuracy-validation.md` apply to `app/core/**`, so the "no LLM" architectural decision AD-6 must be amended first.

---

**Never record here:** secrets, credentials, access tokens, API keys, connection strings, or personal data.

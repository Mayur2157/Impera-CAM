# Engineering Rules

> Status: draft · Last updated: 2026-10-14
> Project-specific rules. These sit above `.agents/rules/**` in the precedence hierarchy — see `.agents/PRIORITY.md`.
> Each entry is hard `[H<n>]` or soft `[S<n>]`, matching `.agents/CONVENTIONS.md`.

## Mandatory conventions

- **[H1]** The balance chain is the arbiter of extraction correctness. A change in `app/core/` that lowers any sample statement's chain score, or changes its winning strategy or mode, is a regression unless it is explicitly approved and recorded in `memory.md`.
- **[H2]** Never present an unverified row as clean. Rows failing the chain or the audit stay flagged `CHECK` on the Transactions sheet and are listed on the Validation sheet. Do not drop, "fix" or interpolate them silently.
- **[H3]** Money in `app/core/` is `decimal.Decimal` end to end. Convert to `float` only at an output boundary (`pipeline.py` return dict, `excel._f`). No float arithmetic in `normalize`, `validate`, `annexure` or `pipeline`.
- **[H4]** Scoring weights, hard caps, grade bands and analysis thresholds (see "Business rules of record") are credit policy, not implementation detail. Change them only with a dated decision in `memory.md` giving the old value, new value and reason, and update this file's table in the same change.
- **[H5]** Account details come from the region above the transaction table only (`customer.extract_customer(pdf, htop)`). Do not read holder fields from inside the table.
- **[H6]** Tenant isolation: every DB query on `jobs`, `file_tasks`, `account_registry` and `usage`, and every upload or output path, is scoped by `tenant_id`. A new endpoint returning job or file data checks `job.tenant_id == current_user.tenant_id`.
- **[H7]** The scanned (OCR) and digital paths emit the same `layout.Word` schema. Nothing downstream of `extract.collect()` may branch on whether a page was scanned.
- **[S1]** Supporting a new bank layout: first add a header regex to `SYNONYMS` (`app/core/columns.py:11-31`) or an IFSC prefix to `IFSC_MAP` (`app/core/customer.py:49-70`). Add bank-specific code paths only when a sample proves the generic path can't work, and name the bank in a comment.
- **[S2]** Thresholds are named module-level constants beside the code that uses them (as `MIN_SCORE`, `TOL`, `MIN_CONF` are). Promote to `Settings` only if an operator needs to tune it per deployment.
- **[S3]** Classification is regex- and rule-first, in `narration_rules.py` / `classifier.py`. Introducing ML or an LLM is a consequential change and brings in `.agents/rules/ai/*`.

## Coding and naming standards

- **[S4]** Follow `.agents/rules/backend/python-structure.md` and `fastapi-structure.md` for new code. The existing code is lightly typed and passes dicts around; don't refactor it to dataclasses as a side effect of an unrelated change (`minimal-change`).
- **[S5]** Use `from __future__ import annotations` and type hints on public functions in new or substantially edited modules.
- **[S6]** Comments explain *why*, usually by naming the bank or statement that forced the rule (for example "Bandhan's DEBITS label sits 40 pt left"). Keep that style.
- **[S7]** Configuration is read only through `app.config.settings`, with env vars prefixed `BSX_`.

## Testing requirements

- **[H8]** A change to `app/core/` or `app/analysis/` is verified by running the engine over the sample statements and comparing per-statement rows, chain score, mode and flagged count against the previous run. Once the Phase 4 regression suite exists, that suite is the check.
- **[H9]** Test fixtures and expected-value files contain no personal data: no names, account numbers, PAN, phone, email or addresses. Key fixtures by file hash or synthetic id.
- **[S8]** A bug fix in the analysis layer comes with a minimal synthetic-transaction test reproducing it.
- **[S9]** Run API tests against a disposable database, never the development database that holds real tenant data.

## Security requirements

- **[H10]** Never persist PDF passwords: not to disk, the DB or logs (`app/jobs.py:7`).
- **[H11]** Never log, print or write personal data or full narrations into application logs, docs, `agentic/`, `HANDOVER.md` or commit messages. The CLI's stdout financial summaries are allowed only in local runs by the operator.
- **[H12]** Never commit or bake into an image any real statement PDF, generated workbook, or the JSON account registry.
- **[H13]** Production deployments must set `BSX_JWT_SECRET` (≥32 random chars) and restrict `BSX_ALLOWED_ORIGINS`. The defaults in `app/config.py` are for local development only.
- **[H14]** Changes touching personal data, retention or deletion follow `.agents/rules/compliance/dpdp-compliance.md`. Run `.agents/scripts/check-freshness.sh` first and say so if the entry is overdue.

## Dependency and version constraints

- **[H15]** Do not install CPU `paddlepaddle` from PyPI alongside `paddlepaddle-gpu==3.3.0`, because it shadows the GPU wheel. Confirm with `GET /api/health` (`ocr_device: gpu:0`, `cuda_compiled: true`).
- **[S10]** Python 3.12. A new dependency is a consequential change (`collaboration-workflow`). Prefer pinning exact versions when adding one; Phase 4 pins the rest.
- **[S11]** `python-jose` must be ≥ 3.4.0 and `passlib` must be paired with a compatible `bcrypt` (< 5). Both are pinned in Phase 4.

## Verification tooling

| Tool | Invocation | When it runs | Reporting requirements |
|---|---|---|---|

No automated reviewer is configured. See `.agents/rules/core/code-verification.md`.

The manual verification commands:

```sh
python cli.py "Bank/*.pdf"                 # per-statement rows / chain / flagged, printed
python .agents/scripts/validate.py         # rules-pack integrity
python .agents/scripts/check-freshness.py  # before compliance work
```

## Documentation expectations

- **[H16]** `agentic/architecture.md` is the architecture of record. Do not create a root `ARCHITECTURE.md`. Update the relevant `agentic/` document in the same change as the code it describes.
- **[S12]** Keep `README.md` as the developer quick start and point it at `agentic/` for design and architecture. It is out of date until Phase 4 rewrites it.
- **[S13]** Session state goes in `HANDOVER.md` (`collaboration-workflow` H6), and durable decisions go in `agentic/memory.md`.

## Definition of done

A change is done when all of the following hold:

1. The diff has been read (`collaboration-workflow` H1).
2. [H8] verification has been run, with the exact command and the per-statement outcome recorded.
3. No statement regressed on chain score, rows or flagged count, or every regression is explained and approved.
4. Any change to a scoring rule is reflected in the table below and in `memory.md` ([H4]).
5. Affected `agentic/` documents, and `phases.md` status, are updated.
6. No personal data was added to any tracked file ([H9], [H11]).

## Forbidden practices

- **[H17]** Tuning a threshold to make one sample statement pass without checking all the others.
- **[H18]** Hard-coding a reconciliation or validation result in the workbook. Every reported figure must be computed. (This currently happens at `excel.py:1271, 1299` and is a Phase 4 fix.)
- **[H19]** Catching and discarding exceptions in `app/core/` or `app/analysis/` in a way that turns an extraction failure into an apparently clean result.
- **[H20]** Editing generated AI adapter files (`.claude/`, `.cursor/`, `.github/copilot-instructions.md`, `.windsurfrules`, `.clinerules`). Edit `.agents/` and run `.agents/scripts/sync.sh`.

## Approved exceptions to `.agents/rules/**`

| Rule ID | Exception | Reason | Approved by | Date |
|---|---|---|---|---|

None.

---

## Business rules of record

This is the current credit policy as implemented. Per [H4], change it only with a recorded decision. Source: `app/analysis/*`.

**Scorecard** (`profiler.py:1-13, 626-632`). Unmeasurable components are dropped and the rest rescaled to 100. The final score is clamped to 5–100 (`:646`).

| Component | Weight |
|---|---|
| C1 Cash-flow stability & margin | 20 |
| C2 Liquidity / ABB (non-OD) or credit turnover vs limit (OD) | 15 |
| C3 Debt capacity — FOIR (retail) / DSCR (business) | 15 |
| C4 EMI repayment regularity | 10 |
| C5 OD utilisation / facility compliance | 15 |
| C6 Bounce / return behaviour | 10 |
| C7 Transaction risk / AML | 10 |
| C8 Income stability & concentration | 5 |

**Risk grades** (`profiler.py:649-658`):

| Score | Grade |
|---|---|
| ≥ 80 | LOW (PRIME) |
| ≥ 65 | MODERATE-LOW |
| ≥ 50 | MODERATE |
| ≥ 35 | HIGH |
| < 35 | VERY HIGH / STRESSED |

**Hard caps.** The lowest triggered cap binds.

| Cap | Trigger |
|---|---|
| 35 | More than 5 negative-balance days on a non-OD account |
| 45 | Holder name missing |
| 45 | No meaningful income |
| 45 | DSCR not meaningful with deficit ≥10% of income |
| 45 | ≥2 EMI bounces |
| 45 | ≥2 outward bounces |
| 50 | FOIR or DSCR failing its lowest band |
| 55 | Deficit worse than 25% |
| 55 | OD utilisation above 92% |
| 60 | 1 outward bounce |
| 60 | Unclassified value above 15% |
| 60 | Cash ≥50% of inflows |
| 60 | Buffer under 0.5 months while in deficit |
| 60 | 1–5 negative days on a non-OD account |
| 65 | Any HIGH structuring alert |

**Key thresholds:**
- Data sufficiency: under 3 months VERY LIMITED, up to 5 LIMITED, up to 11 MODERATE, more STRONG (`profiler.py:668-675`).
- Months covered = days ÷ 30.4.
- Eligible income excludes all cash deposits, self/related transfers, loans, refunds, capital, pass-through and bank-funded inflows (`eligible_income.py:166-178`).
- Active loan = last paid within 45 days of the period end (`debt.py`).
- Structuring bands: ₹47–50k, ₹95k–1L, ₹4.75–5L, ₹9.5–10L; HIGH ≥55, MEDIUM ≥30 (`fraud_aml.py`).

Known inconsistencies in these rules (FOIR bands in `debt.py` vs `profiler.py`, concentration 40% vs 35%, and others) are listed in `memory.md` → Active risks.

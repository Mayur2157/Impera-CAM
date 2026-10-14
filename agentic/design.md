# Product Design

> Status: draft · Last updated: 2026-10-14
> Describes the as-built UI (`app/static/`) and the workbook, which is the product's main output surface. Gaps against `.agents/rules/frontend/frontend-standards.md` are listed under each screen and collected in Phase 6.

## Design principles

1. **Show what tied and what needs a human.** The balance-check rate and the "needs review" count are first-class results, not hidden diagnostics.
2. **Money reads like a ledger.** Tabular, lining numerals everywhere (`style.css:1-2, 28`). Real numbers and real dates in the workbook so analysts can pivot.
3. **Two-state signal.** Green "tie" (`--tie`) for verified, red "break" (`--break`) for failed. Nothing in between pretends to be verified.
4. **No build step.** Plain HTML, CSS and JS served by FastAPI (`app/main.py:48-53`).
5. **Explain the number.** Every score in the workbook has an evidence sheet and a reconciliation row (Calculation_Reconciliation).

## User journeys and flows

```
Visit /  ──► token in localStorage? ──no──► Auth panel ──sign in / register──┐
               │yes                                                          │
               ▼                                                             ▼
          App panel ◄────────────────────────────────────────────────────────┘
               │
   choose/drop PDFs ─► set options (password, bank, DPI, OCR) ─► Extract
               │
   POST /api/jobs ─► poll GET /api/jobs/{id} every 700 ms ─► results table
               │                                               │
               └──────────── Recent jobs (history) ◄───────────┴─► Download .xlsx
```

- Sign-out clears the token client-side only (`app.js:127`).
- A 401 from any call clears the token and returns the user to the auth panel (`app.js:27-31`).

## Information architecture

This is a single page (`app/static/index.html`) with two mutually exclusive panels:

- **Auth panel** (`#auth-panel`): product title, Sign in / Create account tabs.
- **App panel** (`#app-panel`):
  - masthead with the user badge, sign-out and the OCR engine line
  - Intake: dropzone, file queue, options fieldset, Extract button, error line
  - Results table
  - Recent jobs table

The **workbook** is the second surface: 11 sheets in reading order, listed under "Workbook surface" below.

## Screens and states

### Auth panel (`index.html:14-51`)

| State | Behaviour |
|---|---|
| Default | Sign in tab active; email and password fields with `autocomplete` hints |
| Register | Organisation, email, password (`minlength=8`) |
| Loading | No explicit loading state on submit — **gap** |
| Error | `.auth-error` paragraph un-hidden with the server message |
| Success | Token stored and app panel shown |

Gaps:
- The tabs are plain buttons with no `role="tab"` or `aria-selected`.
- Errors are not announced (no `role="alert"`).
- `--accent` is used for the active tab, the buttons and the focus outline (`style.css:315, 317, 339, 345, 395`) but **never defined**, so those elements lose their colour and focus ring.

### Intake (`index.html:77-114`)

| State | Behaviour |
|---|---|
| Empty | Dropzone prompt; Extract disabled |
| Files chosen | Queue list shown; Extract enabled |
| Drag-over | `.hot` class on the dropzone |
| Submitting | Button disabled, label changes |
| Error | `#error` line shown via `fail()` (`app.js:198`) |

Gaps:
- The copy says "Up to 25 files" (`index.html:81`), but tenant plans default to 10 files / 20 MB (`app/db/models.py:44-45`).
- There is no client-side size check.

### Results (`index.html:116-136`)

One row per file: Statement, Bank, Rows, Balance check, Needs review, Workbook.

| State | Behaviour |
|---|---|
| Running | Spinner plus progress message |
| Error | "failed" in red |
| Done | Figures plus Download button; a "Partial PDF" badge when `is_partial` |

Gaps:
- Progress is not in an `aria-live` region.
- The server message is inserted through `innerHTML` (`app.js:263`), which is an XSS surface.
- Download errors use `alert()` (`app.js:307`).
- Polling is a fixed 700 ms with no backoff (`app.js:206-225`).
- The analysis profile (score, grade, FOIR, red flags) is **not shown**. It exists only in the workbook.

### Recent jobs (`index.html:139-153`)

| State | Behaviour |
|---|---|
| Empty | "No jobs yet." |
| Loaded | Date, Files, Status pill, Actions (download) |
| Error | **Silently swallowed** (`app.js:317-320`) — gap |

## Interaction behavior

- **Dropzone:**
  - keyboard-operable: Enter/Space opens the picker (`app.js:160`)
  - click opens the picker
  - drag-and-drop replaces the queue
- **Options:**
  - The PDF password applies to every file in the job.
  - "Bank name" is used only when the statement prints the bank as a logo (`app/core/pipeline.py:105`).
  - DPI choices are 200/300/400.
  - The OCR checkbox defaults to on.
- **Download** uses fetch with the bearer token, then a blob URL (the token can't go in a plain link).

## Responsive behavior

Below `40rem`, both ledger tables collapse to stacked cards with `data-label` prefixes (`style.css:247-261`). Content width is capped at `62rem` (`style.css:30`).

## Accessibility

**Target:** WCAG 2.1 AA, per `frontend-standards`.

| Criterion | Status |
|---|---|
| Visible focus | Present on most controls (`style.css:70, 130`); broken where it depends on `--accent` |
| Labels | All inputs labelled; table headers use `scope` |
| Reduced motion | Honoured (`style.css:263-266`) |
| Status announcements (4.1.3) | **Missing**: no `aria-live` on progress or errors |
| Tabs pattern | **Missing** roles/states on the auth tabs |
| Colour contrast | Not measured; verify in Phase 6 |

## Visual direction

"Ledger" (`style.css:1-2`): cool paper, blue-black ink, a serif body with a sans-serif for UI chrome, and a two-state tie/break signal. Calm, document-like, closer to an accounts book than a dashboard.

## Design system

### Colors

| Token | Value | Use |
|---|---|---|
| `--paper` | `#fbfbf9` | page background |
| `--panel` | `#ffffff` | cards, tables |
| `--ink` | `#16202a` | body text |
| `--muted` | `#5c6873` | secondary text |
| `--rule` | `#dce0e4` | borders, rules |
| `--field` | `#2e4a6b` | inputs, links |
| `--tie` | `#1f6f5c` | verified / OK |
| `--break` | `#a6402c` | failed / CHECK |
| `--accent` | **undefined** | used by the auth UI — define it, or replace it with `--field` |

The status pills use hard-coded colours (`style.css:430-433`). Dark mode (`style.css:434`) only recolours those pills; the page tokens have no dark variant.

### Typography scale

- **Body:** `--serif` 17px / 1.6 (`style.css:27`).
- **UI chrome:** `--sans` at about .85–.88rem.
- **Masthead h1:** `clamp(2rem, 4.5vw, 2.9rem)`, weight 600.
- **Numerals:** `font-variant-numeric: tabular-nums lining-nums` globally.

### Spacing

rem-based, with no scale tokens. The common steps are .2, .5, .85, 1, 1.5, 2.75, 3 and 3.5rem.

### Radii

Not tokenised; set per component.

### Shadows

`--shadow: 0 1px 0 var(--rule)`, a hairline only.

### Icons

None. Text and a CSS spinner only.

### Components and variants

- dropzone (default / `.hot`)
- queue list
- options fieldset
- primary button `.go`
- auth tabs and buttons
- `.ledger` table
- status pills (`done`, `running`, `queued`, `error`)
- `.broke` failure text
- link button
- spinner

### Interactive states

Hover/focus are defined for buttons and inputs, and disabled for `.go`. There is no pressed state.

## Workbook surface (`app/output/excel.py:56`)

| # | Sheet | Purpose |
|---|---|---|
| 1 | Financial_Profile | Executive CAM: profile, scorecard, components, hard caps, strengths, red flags |
| 2 | Income_Analysis | Eligible vs excluded inflows; excluded debits with rationale |
| 3 | Monthly_Analysis | Per-month inflow/outflow, ABB, margins, operating net |
| 4 | Transactions | One row per transaction plus category, counterparty, relationship, purpose; `CHECK` rows shaded |
| 5 | Customer_Info | Header fields, linked accounts, derived totals, completeness |
| 6 | Debt_Obligations | Loans/EMIs, disbursals, recurring debits, related parties |
| 7 | Counterparties | Top inward/outward and channel mix |
| 8 | Risk_Anomaly_Flags | Bounces, penalties, structuring, rapid in-out |
| 9 | Validation | Strategy, chain mode, pass rate, flagged rows with ₹ difference |
| 10 | PDF_Field_Validation | Per-row field presence (see `memory.md`: presence-only, not a true comparison) |
| 11 | Calculation_Reconciliation | Formula, inputs and result for every headline ratio |

## Diagrams

See the journey diagram above. The pipeline diagram is in `architecture.md`.

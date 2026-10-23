# Feature PRD — Customer portal and developer API

> Status: approved (plan approval, 2026-10-16) · Last updated: 2026-10-16

## Problem

Impera CAM is sold to lenders as SaaS, but:
- The only interface is a single static upload page.
- Lenders can't integrate it into their own loan systems: there are no API keys.
- Organisations can't manage their own teams.
- Impera staff have no way to manage tenants.

## Users

| User | Needs |
|---|---|
| Lender org owner/admin | Manage the organisation, members and API keys; see usage against plan |
| Credit analyst (member) | Upload statements, follow progress, read the CAM, download the workbook |
| Lender's developer | Create a key, read the docs, call `/api/v1/jobs*` from their servers |
| Impera staff (superuser) | See every tenant and its usage; change plans and limits; suspend a tenant or revoke a key; see queue and worker health |

## Decisions (product owner, 2026-10-16)

- The frontend is built in **Lovable** from `lovable-prompts.md`, then integrated here. *Superseded 2026-10-23: hand-built Vite + React SPA in `frontend/` (product owner).*
- **Billing v1:** usage and plan display only; staff change plans. No payment gateway.
- **The super-admin console is included.**
- API keys work like Gemini/AI Studio keys: created in the portal, shown once, sent as `X-API-Key`.

## Requirements

- **FR-P1** Every portal feature in `lovable-prompts.md`, built against `api-contract.md` only.
- **FR-P2** API keys:
  - prefix plus a secret shown once
  - stored as a SHA-256 hash only
  - scoped (`jobs:read`, `jobs:write`)
  - revocable immediately
  - `last_used_at` and per-key usage recorded
  - rate limited per key
- **FR-P3** Roles enforced server-side: `owner`, `admin`, `member`, plus `is_superuser`. The UI hiding a control is never the only check.
- **FR-P4** The full CAM is available as JSON (`…/result`, `…/transactions`), purged with the workbook at retention. Account number and PAN are masked in the API.
- **FR-P5** A suspended tenant's users are read-only, and its keys are rejected.
- **FR-P6** DPDP: consent at signup; no personal data in URLs or logs; masking in the UI and API; retention stated in Settings.

## Non-goals (v1)

- Payments and invoices.
- Email sending (invites are copy-link).
- SSO.
- Webhooks: customers poll with backoff.
- Impersonation.
- Tenant self-deletion.

## Acceptance

- ~~The Lovable app runs fully in mock mode with no Supabase dependency.~~ Superseded 2026-10-23: the portal is tested against the real API (component tests mock `fetch`).
- With mocks off, every screen works against the backend, and pytest covers every new contract endpoint.
- The existing baseline, smoke and load tests still pass.

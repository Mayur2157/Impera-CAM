---
id: dpdp-compliance
title: DPDP Compliance (India)
scope: glob
globs: ["**/*.tsx", "**/*.jsx", "**/*.vue", "**/*.svelte", "**/*.html", "**/*.ts", "**/*.js", "**/*.py", "**/*.go", "**/*.java", "**/*.kt", "**/*.rb", "**/*.php", "**/*.sql"]
category: compliance
version: 2.0.0
updated: 2026-08-30
freshness: tracked
---

# DPDP Compliance (India)

Applies when a feature collects, stores, processes, or shares personal data, particularly for users in India. Full guide: `.agents/skills/dpdp-compliance/SKILL.md` and its `reference.md`.

Triggers: signup, login, profile, checkout, HR, CRM, support, analytics touching personal data; consent banners, privacy notices, deletion or export flows, retention policy; any question about DPDP or Indian data privacy.

## Freshness — read first

**[H1]** This material is a developer reference, not legal advice, and it goes stale. Before shipping compliance-sensitive functionality, making a compliance claim, or answering a legal question:

1. Check `.agents/config/freshness.json` → entry `dpdp-compliance`. If `last_verified` is older than its review interval, say so before relying on the content.
2. Verify the current text of the Act and Rules, **their commencement status**, and any regulator guidance against authoritative sources — MeitY, the Gazette of India, India Code. Commencement is staggered; a provision being in the text does not mean it is in force, and a provision not yet in force may have become so.
3. Route anything that is a legal representation to qualified counsel. An agent may never certify compliance.

**[H2]** Never state or imply that a product "is DPDP compliant". Describe what the implementation does and what remains open for legal review.

## Hard rules

- **[H3]** Collect only the personal data the stated purpose requires. Every collected field maps to a purpose.
- **[H4]** Consent is specific, informed, unambiguous, and given by affirmative action. No pre-ticked boxes, no bundled consent, no consent inferred from continued use.
- **[H5]** Withdrawing consent is as easy as giving it, and the withdrawal path is discoverable in the product, not only in a policy document.
- **[H6]** Every consent event is recorded with purpose, notice version, timestamp, and method. A consent you cannot evidence did not happen.
- **[H7]** A privacy notice accompanies collection, is available in plain language, and is versioned. Changing the notice creates a new version; it does not silently edit the old one.
- **[H8]** Personal data is encrypted in transit and at rest, with access controlled by role and logged.
- **[H9]** Retention is defined per data category and enforced by an actual mechanism — a scheduled job, not a paragraph in a policy.
- **[H10]** Deletion means deletion: primary store, replicas, caches, search indexes, exports, logs, and backups per the documented backup expiry. A soft-delete flag alone does not satisfy an erasure request.
- **[H11]** Data principal rights — access, correction, erasure, grievance, nomination — have working product paths, not just email addresses.
- **[H12]** Breach handling has a defined workflow: notify affected principals without delay, notify the Board within the statutory window, and keep a breach record. Verify the current window before relying on any figure in the reference.
- **[H13]** Never log, never put in analytics, and never send to a third party: authentication credentials, full payment data, government identifiers, health data, or children's data.
- **[H14]** Processing children's data requires verifiable parental consent and the restrictions that attach to it. Do not build a children-facing flow without reading the reference section in full.
- **[H15]** Every processor and sub-processor is under a written contract and appears in the vendor register before it receives data.
- **[H16]** Development, test, and demo environments never hold real personal data. Use synthetic or irreversibly anonymized data.

## Soft defaults

- **[S1]** Model consent as `consent_purposes` and `user_consents` tables — purpose-level, versioned, append-only.
- **[S2]** Keep a data inventory and a record of processing activities alongside the code, updated when a field is added.
- **[S3]** Run a lightweight impact assessment for a new processing purpose; use the template in the reference.
- **[S4]** Surface consent and privacy state in an internal admin view so support can answer questions without database access.
- **[S5]** Flag any gap you find for legal and product review rather than resolving it in code.

---
name: dpdp-compliance
description: Apply India's Digital Personal Data Protection Act 2023 and DPDP Rules 2025 to product decisions — consent, notices, retention, rights, breach handling, and security safeguards. Use when a feature touches personal data, or when asked about DPDP or Indian data privacy.
---

# DPDP Compliance (India)

Binding rules: `.agents/rules/compliance/dpdp-compliance.md`. Detailed guide: `reference.md` in this folder.

## Freshness gate — run this first, every time

**This material has a shelf life and the law is on a staggered commencement schedule.** Before relying on it:

1. Read `.agents/config/freshness.json`, entry `dpdp-compliance`. Compare `last_verified` against `review_interval_days`.
2. If it is past due, say so in your first response on the topic, in one line: what the reference is dated, and that current text and commencement status need verification.
3. Verify against authoritative sources before any shipping decision — MeitY, the Gazette of India, India Code. Check **commencement**, not just text: a provision printed in the Rules may not yet be in force, and one that was not in force at last verification may be now.
4. Anything that is a legal representation goes to counsel. You may describe what an implementation does. You may not certify that it complies.

Run `.agents/scripts/check-freshness.sh` if you have shell access.

## What this skill is for

Product and engineering decisions: what to collect, how to ask, what to store, how long, who can see it, how a user gets it back or gets it deleted, and what happens when something leaks. It is not a substitute for legal review and does not produce legal advice.

## Working order

1. **Map the data.** For the feature in front of you: every personal-data field, why it is collected, where it is stored, who can read it, what leaves the system. If you cannot produce this list, you cannot assess the feature.
2. **Test necessity.** Each field justifies itself against a stated purpose. A field that exists because the form template had it is a field to delete.
3. **Design the consent.** Purpose-level, affirmative, unbundled, withdrawable, and evidenced. Bad consent is not a UI problem — it invalidates the processing.
4. **Write the notice.** Plain language, versioned, delivered at collection. Structure in `reference.md` §7.
5. **Set retention.** Per category, with a mechanism that actually deletes. A policy without a job is a claim.
6. **Build the rights paths.** Access, correction, erasure, grievance, nomination — as product surfaces, not an inbox.
7. **Handle the security floor.** Encryption in transit and at rest, role-based access, access logging, log retention, backup expiry.
8. **Prepare for breach.** Workflow, principal notification, Board notification within the statutory window, breach record. Verify the window before relying on it.
9. **Record what remains open.** Gaps go to legal and product review, named and dated. Do not close them in code.

## Special cases that change everything

- **Children's data** — verifiable parental consent plus processing restrictions. Read `reference.md` §16–19 before building any of it.
- **Persons with a lawful guardian** — analogous consent path, §20.
- **Significant Data Fiduciary designation** — adds DPIA, audit, and officer obligations, §23.
- **Cross-border transfer** — §25.
- **Multi-tenant SaaS** — tenant isolation is a privacy control, not just an architecture choice, §33.

## Reference map

`reference.md` is long. Load the section you need: terminology §2 · consent §5–6 · notice §7 · minimisation §8 · security §12 · breach §13 · retention §14 · children §16–19 · rights §21–22 · DPIA §24 · schemas and checklists §28–40 · logging §51 · deletion workflow §43 · export §44.

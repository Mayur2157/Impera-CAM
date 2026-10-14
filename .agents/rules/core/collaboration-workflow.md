---
id: collaboration-workflow
title: Collaboration Workflow
scope: always
globs: []
category: core
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Collaboration Workflow

Governs **ongoing sessions**: how a change is proposed, made, checked, and handed off. It does not govern what the product is — that is `project-kickoff`.

Full procedure: `.agents/skills/collaboration-workflow/SKILL.md`.

## Change size, and what it requires

The v1 rule required an explanation before every implementation, which made "rename this variable" a planning exercise. Classify first:

| Class | Examples | Required before implementing |
|---|---|---|
| **Mechanical** | Copy edits, renames, formatting, adding a log line, a version bump, a one-line guard in one place | Nothing. Do it, then report what changed. |
| **Ordinary** | A new function, a bug fix inside one module, a small component, a test | One or two sentences on the approach, in the same message as the change. No separate approval turn. |
| **Consequential** | New dependency, schema or migration, auth/permissions, public API contract, data deletion, cross-module refactor, anything touching personal data or money | Approach, alternatives rejected, blast radius, planned verification — **and an explicit go-ahead before writing code.** |

When the class is ambiguous, treat it as the higher one.

## Hard rules

- **[H1]** Read the actual diff before claiming the work is done. A summary is not a diff.
- **[H2]** Never claim a check passed unless it was run. Record the exact command and its outcome. "Should pass" is not a result.
- **[H3]** Consequential changes require explicit user go-ahead before implementation.
- **[H4]** One coherent change per request. Split broad work into independently reviewable steps.
- **[H5]** Never write secrets, credentials, tokens, or personal data into any project document, memory file, handover, or decision record.
- **[H6]** End a substantive session with an updated `HANDOVER.md` carrying all five headings: Completed, In Progress, Next, Watchouts, Verification.
- **[H7]** Flag what you are unsure about. Do not present a guess with the same confidence as a verified fact.

## Soft defaults

- **[S1]** Maintain `HANDOVER.md`, `DECISIONS.md`, and `FLOW.md` at the repo's documentation root; create each only when the work needs it.
- **[S2]** Open a `FEATURE-<slug>.md` or `BUG-<slug>.md` record for non-trivial work.
- **[S3]** Comment only non-obvious intent, control flow, invariants, and assumptions. Never narrate syntax.
- **[S4]** Record the model/version on a material decision when the session exposes it; write `model/version: not recorded` rather than guessing.
- **[S5]** When resuming, read the handover, the active work record, and decisions before proposing edits, and reconcile them against current code.

## Interaction with other rules

**Document ownership when `agentic/` exists** (i.e. `project-kickoff` has run):

| Concern | Lives in | Not in |
|---|---|---|
| What we are building and why | `agentic/prd.md` | a root `REQUIREMENTS.md` |
| System architecture of record | `agentic/architecture.md` | a root `ARCHITECTURE.md` |
| Engineering rules for this project | `agentic/rules.md` | a root `CONSTRAINTS.md` |
| Phase status | `agentic/phases.md` | the handover |
| Durable decisions and rationale | `agentic/memory.md` | `DECISIONS.md` |
| Session state — done, in progress, next | `HANDOVER.md` | `agentic/memory.md` |
| Execution path for the active change | `FLOW.md` | `agentic/architecture.md` |
| Work record for one feature or bug | `FEATURE-*.md` / `BUG-*.md` | anywhere else |

When `agentic/` does not exist, `ARCHITECTURE.md` and `CONSTRAINTS.md` at the root are the fallback for the first two rows. Never maintain both copies.

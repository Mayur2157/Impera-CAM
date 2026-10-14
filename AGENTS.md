# Agent Instructions

This repository carries the **AI Rules & Skills pack v2**. Canonical content lives in `.agents/`. Platform adapters (`.cursor/`, `.claude/`, `.github/copilot-instructions.md`, `.windsurfrules`, `.clinerules`) are generated pointer files — never edit them.

## Read before working

1. **`.agents/PRIORITY.md`** — how conflicts resolve. This is the tiebreaker.
2. **`.agents/CONVENTIONS.md`** — what `[H<n>]` and `[S<n>]` mean.
3. **`agentic/`** — the approved project documents, if this project has been through kickoff. For a major feature, also `agentic/features/<feature-slug>/`.

**Hard rules `[H<n>]` are binding.** Violating one requires an explicit user override, stated aloud. **Soft defaults `[S<n>]` are starting points** — deviate when the situation calls for it and state the reason in one line.

<!-- ai-rules:start -->
## Agentic project documents

Before project work, read the applicable approved documents under `agentic/` and, for a major feature, `agentic/features/<feature-slug>/`.

Treat approved requirements and rules as authoritative. If a request conflicts with them, name the conflict and ask whether to amend the documents before proceeding. Keep `agentic/memory.md`, phase statuses, and affected documents synchronized with approved changes.

Never store secrets, credentials, tokens, or personal data in project documents or memory files.
<!-- ai-rules:end -->

## Rules

Always applied:

| Rule | Covers |
|---|---|
| `.agents/rules/core/rule-precedence.md` | Conflict resolution; hard/soft semantics |
| `.agents/rules/core/minimal-change.md` | Simplest solution that works; root cause over symptom |
| `.agents/rules/core/project-kickoff.md` | Planning gates before implementation |
| `.agents/rules/core/collaboration-workflow.md` | Change sizing, diff review, verification, handoffs |
| `.agents/rules/core/code-verification.md` | Verification tiers and when review runs |

Applied when files match:

| Rule | Applies to |
|---|---|
| `.agents/rules/frontend/frontend-standards.md` | Frontend source |
| `.agents/rules/frontend/ui-redesign.md` | Frontend source |
| `.agents/rules/backend/python-structure.md` | `**/*.py` |
| `.agents/rules/backend/fastapi-structure.md` | `**/api/**`, `**/routers/**`, `**/main.py` |
| `.agents/rules/ai/ai-applications.md` | `**/core/**`, `**/services/**`, `**/prompts/**`, `**/agents/**` |
| `.agents/rules/ai/accuracy-validation.md` | The above plus `**/api/**` |
| `.agents/rules/compliance/dpdp-compliance.md` | Anything touching personal data |

## Skills

Read the matching skill before specialized work.

| Skill | When |
|---|---|
| `.agents/skills/project-kickoff/` | New product or major feature, before planning |
| `.agents/skills/collaboration-workflow/` | Sessions, handoffs, decisions, verification |
| `.agents/skills/frontend-standards/` | UI, forms, components, accessibility, review |
| `.agents/skills/ui-redesign/` | Upgrading existing UI without changing the stack |
| `.agents/skills/python-ai-applications/` | Python LLM, RAG, agents, FastAPI |
| `.agents/skills/dpdp-compliance/` | Personal data, consent, privacy, India users |

## Configuration

- `.agents/config/defaults.md` — tunable technology defaults. **Everything in it is soft.** No model identifier is hardcoded anywhere else.
- `.agents/config/freshness.json` — staleness register for legal, vendor, and standards content. Run `.agents/scripts/check-freshness.sh` before relying on tracked material.

## Maintenance

```sh
.agents/scripts/sync.sh              # regenerate all AI IDE adapters from .agents/
.agents/scripts/validate.sh          # structural checks; run in CI
.agents/scripts/check-freshness.sh   # what needs re-verifying
```

Edit `.agents/`, run `.agents/scripts/sync.sh`, run `.agents/scripts/validate.sh`. Never edit a generated file.

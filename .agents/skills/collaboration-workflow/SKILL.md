---
name: collaboration-workflow
description: Maintain traceable documentation and review discipline across AI-assisted coding sessions. Use when starting or resuming work, planning a change, reviewing a diff, preparing verification, or closing a session with a handoff.
---

# Collaboration Workflow

This skill owns **session state** — what happened, what is in flight, what is next. It does not own product intent; that is `project-kickoff`. When `agentic/` exists, defer to it for requirements, architecture, and project rules.

Binding rules: `.agents/rules/core/collaboration-workflow.md`, including the change-size table and the document ownership table.

## The change loop

For each coherent change:

1. **Read** the relevant code and documents. Identify the affected flow and the constraints on it.
2. **Classify** the change as mechanical, ordinary, or consequential. Consequential changes stop here for go-ahead.
3. **State** the intended change and the planned verification — length proportional to class.
4. **Implement** the smallest coherent version.
5. **Inspect** the diff line by line: unintended changes, unsafe assumptions, missing checks.
6. **Verify** per `code-verification`. Record exact commands and outcomes.
7. **Record** what was established — work record, decisions, flow, handover. Facts only.

## Documents

Create only what the current work needs, in the repository's existing documentation location. Never invent system facts to fill a template.

### `HANDOVER.md` — always, at session close

```md
# Handover

## Completed
- ...

## In Progress
- ...

## Next
- ...

## Watchouts
- ...

## Verification
- `<command>`: <outcome>
```

Living and short. Rewrite it, do not append history to it.

### `DECISIONS.md` — on a material decision

```md
## YYYY-MM-DD - <decision>
- Context: ...
- Decision: ...
- Rationale and tradeoffs: ...
- Model/version: ...
```

When `agentic/memory.md` exists, durable product decisions go there and `DECISIONS.md` holds implementation-level choices. Do not write a decision twice.

### `FLOW.md` — when a change spans modules

Entry point, intermediate modules and functions, data and side effects, exit point, and which portion is being modified. A small Mermaid diagram when it makes a multi-module path clearer.

### `FEATURE-<slug>.md` / `BUG-<slug>.md` — non-trivial work

Scope or reproduction, approach and rejected alternatives, files touched, decisions, tests run with outcomes, unresolved items. Updated as work progresses, not written at the end.

### Conditional guardrails

- `TEST-CHECKLIST.md` — exact commands and observable expected outcomes for declaring the active work done.
- `ROLLBACK.md` — for risky or broad edits: restoration point, impacted files and services, reversal action, post-rollback checks.
- `ARCHITECTURE.md`, `CONSTRAINTS.md` — **only when `agentic/` does not exist.** Otherwise these live in `agentic/`.

## Resuming

Read the handover, the active work record, decisions, and the relevant flow before proposing edits. Reconcile them against the current code and say plainly which notes are stale. A handover that disagrees with the repository is a finding, not a nuisance.

## Closing

Update the five-section handover, record material decisions, attach verification evidence, and state the next smallest action. Actionable, not historical prose.

---
name: project-kickoff
description: Establish the approved planning foundation for a new software product or major feature before any implementation begins. Use when starting a new product, scoping a major feature, or when a codebase has no agentic/ documents and substantial work is about to start.
---

# Project Kickoff

This skill owns **decided intent** — what is being built, for whom, and under what constraints. It runs once per product (and once per major feature). Ongoing session mechanics belong to `collaboration-workflow`; do not duplicate them here.

Binding rules: `.agents/rules/core/project-kickoff.md`.

## Scope

| Situation | Location |
|---|---|
| New product | `agentic/` |
| Major feature on an existing product | `agentic/features/<feature-slug>/` |
| Small feature, bug fix, refactor | Neither — use `collaboration-workflow` |

A "major feature" changes the data model, adds a user-facing surface, introduces an integration, or takes more than a few sessions. If unsure, ask.

## Sequence

### 1. Orient before asking

Read the repository first: existing code, README, any `agentic/` documents, package manifests, migration history, deployed configuration. Never ask what the repository already answers. Say what you learned and what remains unknown.

### 2. Discovery

Ask one to three tightly related questions per turn, one decision per question. Cover, in roughly this order:

- Problem and who has it
- Users and their current workaround
- Scope boundary — what this explicitly does not do
- Critical constraints: platform, stack, deadline, budget, team, compliance
- Data: what personal data is involved, if any (triggers `dpdp-compliance`)
- Success: how anyone will know this worked
- Risks the user already suspects

Stop asking when nothing left is *critical*. Non-critical unknowns are recorded as `TBD` with an owner and do not block the gate.

### 3. Consolidated discovery brief

Present one brief covering everything learned, with every assumption listed explicitly and marked as an assumption. Ask for approval. **Create no files until this is approved.**

### 4. Documents, in order, each approved before the next

Use `assets/` as the structure. Each document is as short as it can be while still being decidable.

1. `prd.md` — what and why
2. `design.md` — how it looks and behaves
3. `architecture.md` — how it is built
4. `rules.md` — engineering constraints for this project
5. `phases.md` — delivery sequence with exit criteria
6. `memory.md` — approved decisions, current state, risks

Order matters: architecture that precedes requirements is a guess, and rules written after implementation are a rationalization.

### 5. Merge the agent block

Merge the managed block from `assets/AGENTS-block.md` into the project's root `AGENTS.md`. Replace only the content between the markers. Preserve everything else the project already had.

### 6. Gate check before code

All six documents approved, no critical `TBD` remaining, `phases.md` has a first phase with exit criteria. Then implementation may begin, and `collaboration-workflow` takes over.

## Maintaining the documents

- A request that conflicts with an approved document is a conflict, not an instruction. Name it, and ask whether to amend the document or approve a scoped exception.
- Keep `memory.md` and phase statuses synchronized as work lands. A phase status that lags the code is worse than none.
- Phase status values: `not-started`, `in-progress`, `blocked`, `complete`. Nothing else.

## Stop conditions

Reset if you notice: batched unrelated questions, code written before the gate, placeholder text used to clear a document, project instructions overwritten, or `rules.md` deferred.

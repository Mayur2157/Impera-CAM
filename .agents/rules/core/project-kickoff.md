---
id: project-kickoff
title: Project Kickoff
scope: always
globs: []
category: core
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Project Kickoff

Gates that keep a new product or major feature from being coded before it is understood. Full procedure and templates: `.agents/skills/project-kickoff/SKILL.md`.

## Hard rules — kickoff gates

- **[H1]** Create no `agentic/` planning files before the consolidated discovery brief is explicitly approved.
- **[H2]** Begin no implementation before `prd.md`, `design.md`, `architecture.md`, `rules.md`, `phases.md`, and `memory.md` are approved, in that order.
- **[H3]** Do not silently assume a critical fact. An unresolved critical `TBD` blocks the gate; a non-critical one is recorded and does not.
- **[H4]** If a request conflicts with an approved document, name the conflict and ask whether to amend the document or approve a scoped exception. Do not implement around it.
- **[H5]** Never write secrets, credentials, tokens, or personal data into any `agentic/` document.
- **[H6]** Preserve existing project instructions. When merging into an existing root `AGENTS.md`, replace only the managed `<!-- ai-rules:start -->` … `<!-- ai-rules:end -->` block.

## Soft defaults — discovery questioning

The v1 rule mandated exactly one question per turn, which turned a fifteen-unknown project into fifteen round trips.

- **[S1]** Ask **one decision per question** — never an "and" question. This is the part that matters.
- **[S2]** Send **one to three questions per turn**, grouped only when they are tightly related and the answers do not depend on each other. Send one alone when the answer will reshape what you ask next.
- **[S3]** Never batch more than three, and never batch across unrelated domains (do not ask about auth and brand color in the same turn).
- **[S4]** Inspect existing code and any `agentic/` documents before asking anything. Do not ask what the repository already answers.
- **[S5]** New product → `agentic/`. Major feature → `agentic/features/<feature-slug>/`.

## Stop conditions

Stop and reset if you catch yourself: writing code before the gate, filling a document with placeholder text to clear it, overwriting the project's own instructions, or deferring `rules.md` until after implementation.

## Interaction with other rules

The documents this rule requires are exempt from `minimal-change` [S3]. Write the shortest useful version; do not skip.

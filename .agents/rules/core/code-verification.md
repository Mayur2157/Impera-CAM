---
id: code-verification
title: Code Verification
scope: always
globs: []
category: core
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Code Verification

Every change gets checked before it is called done. This rule is written against **capabilities**, not a named vendor, so it stays correct in environments where a given review tool is absent.

## Verification tiers

Use the strongest tier available in the environment. Never skip the tier entirely because a stronger one is missing.

| Tier | What it is | Availability |
|---|---|---|
| 1 | Project checks — lint, typecheck, tests, build | Assume present unless proven otherwise |
| 2 | Self-review of the diff, line by line, against this pack's hard rules | Always |
| 3 | Automated review tool (external reviewer, static analysis, security scanner) | Only if configured — see below |

## Hard rules

- **[H1]** Run tier 1 and tier 2 before claiming a coherent unit of work is complete. Report the exact commands and their outcomes.
- **[H2]** Never present unverified work as verified. If checks could not be run, say which and why.
- **[H3]** When an automated reviewer returns findings, tell the user what was found **before** fixing anything. Never fix silently.
- **[H4]** Run dependency validation before adding a package or regenerating a lockfile: check the package's real name, maintenance status, license, and known advisories.
- **[H5]** Resolve or explicitly defer every finding from a review pass before starting the next unit of work. Deferred findings are recorded, not dropped.

## When automated review runs

The v1 rule fired after **any** file write, which meant a twenty-file change triggered twenty full reviews.

- **[S1]** Run automated review **once per coherent unit of work** — a completed feature, a completed fix, a completed refactor — not per file write.
- **[S2]** Run it before: committing, opening a PR, presenting work as complete, or starting a dependent unit of work.
- **[S3]** Run it immediately, mid-unit, for changes touching authentication, authorization, payments, personal data, file uploads, deserialization, or raw SQL — do not wait for the unit to close.
- **[S4]** Re-run after applying fixes from a previous pass, to confirm the fixes landed.
- **[S5]** Do not re-run on a unit that has not changed since the last clean pass.

## Tool adapters

Automated review is configured per project, not assumed. If the environment exposes a review tool (MCP server, CLI, CI check), record it in the project's `agentic/rules.md` under "Verification tooling" with: the tool name, the invocation, session/context requirements, and any required reporting format. If nothing is configured, tiers 1 and 2 stand alone and this section is inert — do not invent a tool call.

- **[S6]** When a tool returns a session or chat identifier, carry the exact value into every subsequent call for that session. Never generate or mutate it.
- **[S7]** When a tool returns a task list, complete it before re-running the tool.
- **[S8]** When a session used an automated reviewer, close with a short summary: issues found grouped by severity, what was fixed, and what the impact would have been unfixed.

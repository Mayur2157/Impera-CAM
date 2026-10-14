---
id: rule-precedence
title: Rule Precedence
scope: always
globs: []
category: core
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Rule Precedence

Load this before acting on any other rule. It is the tiebreaker, and it is short on purpose.

## Hard rules

- **[H1]** Resolve conflicts using the hierarchy in `.agents/PRIORITY.md`. Do not invent an ordering.
- **[H2]** Every normative statement in this pack is marked `[H<n>]` (hard) or `[S<n>]` (soft). Treat an unmarked statement as soft.
- **[H3]** Never silently violate a hard rule. If a hard rule blocks the requested work, say which rule, why it applies, and what the options are — then wait.
- **[H4]** Never silently follow a soft default that the situation contradicts. State the deviation in one line and continue.
- **[H5]** When two rules of equal strength conflict and the tie-breakers in `PRIORITY.md` do not settle it, stop and ask. Do not pick.
- **[H6]** Do not edit generated adapter files (`.cursor/`, `.claude/`, `.github/`, `.windsurfrules`, `.clinerules`). Edit `.agents/`, then run `.agents/scripts/sync.sh`.

## Soft defaults

- **[S1]** When citing a rule to the user, use its identifier (`frontend-standards H4`) rather than paraphrasing.
- **[S2]** If a rule seems wrong for the project rather than wrong for the task, say so once and offer to amend the rule instead of quietly working around it.

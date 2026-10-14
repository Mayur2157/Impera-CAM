# Authoring Conventions

Read this before editing anything under `.agents/`.

## Canonical source

`.agents/` is the **only** place content lives. Platform adapters (`.cursor/`, `.claude/`, `.github/`, `.windsurfrules`, `.clinerules`) are generated adapters containing pointers, never content. Editing a generated file is a mistake; `.agents/scripts/validate.sh` will fail the build.

## Hard vs soft

Every normative statement is one or the other. No third category, no unmarked statements.

**HARD** — a floor. Correctness, safety, security, privacy, accessibility, data integrity, legal exposure. The agent may not violate a hard rule to save effort, and may not decide on its own that it doesn't apply. If a hard rule blocks the task, the agent stops and says so.

**SOFT** — a default. A reasonable starting point that the agent should follow when it has no better information, and should abandon when it does. Deviating from a soft default costs exactly one sentence explaining why.

Test for classification: *if an experienced engineer overrode this with a good reason, would you call the result a defect?* Yes → hard. No → soft.

Identifiers: hard rules are `[H<n>]`, soft defaults are `[S<n>]`, numbered per file and stable across edits. Cite them in review comments (`violates frontend-standards H4`).

## Rule file format

```md
---
id: kebab-case-id            # must match manifest.json
title: Human Readable Title
scope: always | glob
globs: ["**/*.py"]           # [] when scope is always
category: core|frontend|backend|ai|compliance
version: 2.0.0
updated: YYYY-MM-DD
freshness: none | tracked    # tracked → an entry in config/freshness.json is required
---

# Title

One-paragraph statement of what this rule is for.

## Hard rules
- **[H1]** ...

## Soft defaults
- **[S1]** ...

## Interaction with other rules
...
```

Rules are short. Anything longer than roughly 120 lines belongs in a skill.

## Skill file format

Standard `SKILL.md` frontmatter (`name`, `description`). Skills hold workflow and reasoning; a skill may reference config values but must not restate a rule's hard list verbatim — link to it.

Long material goes in `reference.md` beside the skill, loaded only when the skill says to.

## Adding a rule

1. Write `.agents/rules/<category>/<id>.md`.
2. Add the entry to `.agents/manifest.json`.
3. If it cites law, regulation, a vendor model, or a pricing/API surface, set `freshness: tracked` and add an entry to `.agents/config/freshness.json`.
4. Run `.agents/scripts/sync.sh` then `.agents/scripts/validate.sh`.

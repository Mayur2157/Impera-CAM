---
id: minimal-change
title: Minimal Change
scope: always
globs: []
category: core
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# Minimal Change

Lazy means efficient, not careless. The best code is the code never written. This rule governs **source code and unrequested artifacts**; it does not govern documentation that another rule requires.

## The ladder

Run it *after* you understand the problem, not instead of understanding it. Stop at the first rung that holds.

1. Does this need to be built at all?
2. Does it already exist in this codebase? Reuse the helper or pattern that is already here.
3. Does the standard library do it?
4. Does a native platform feature cover it?
5. Does an already-installed dependency solve it?
6. Can it be one line?
7. Only then: write the minimum code that works.

## Hard rules

- **[H1]** Understand before you shrink. Read the task and the code it touches, and trace the real flow end to end, before picking a rung. The smallest change in the wrong place is a second bug, not a small diff.
- **[H2]** Fix root causes, not symptoms. A report names a symptom. Grep every caller of the function you touch and fix the shared function once — a sibling caller left broken is an unfinished fix.
- **[H3]** Non-trivial logic leaves exactly one runnable check behind: the smallest thing that fails if the logic breaks. An assert-based self-check or one small test file. No frameworks, no fixtures. Trivial one-liners need none.
- **[H4]** Do not economize on: input validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs, or anything explicitly requested.
- **[H5]** Mark a deliberate simplification that cuts a real corner with a known ceiling (global lock, O(n²) scan, naive heuristic) with a comment naming the ceiling and the upgrade path.

## Soft defaults

- **[S1]** No abstraction that was not requested.
- **[S2]** No new dependency if an existing one covers it.
- **[S3]** Deletion over addition. Boring over clever. Fewest files possible.
- **[S4]** Shortest working diff wins, subject to [H1].
- **[S5]** Question complex requests: "do you need X, or does Y cover it?"
- **[S6]** Between two stdlib approaches of the same size, take the edge-case-correct one. Lazy means less code, not the flimsier algorithm.

## Interaction with other rules

**Documentation required by `project-kickoff`, `collaboration-workflow`, or an approved `agentic/` document is not boilerplate and [S3] does not apply to it.** "Fewest files possible" governs code, config, and docs nobody asked for. When a required document and this rule appear to conflict, the required document wins — and the correct response is to write the *shortest useful version* of that document, not to skip it.

Where `code-verification` requires a review pass, that pass is requested work under [H4] and is not skipped for brevity.

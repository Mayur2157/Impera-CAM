---
name: frontend-standards
description: Build and review production frontend UI against a quality floor covering accessibility, states, validation, security, responsiveness, and performance. Use when building pages, forms, or components, or when reviewing UI before shipping.
---

# Frontend Standards

Binding rules: `.agents/rules/frontend/frontend-standards.md`. Full checklist: `reference.md` in this folder — load it when reviewing or when you need the detail.

## Decision order

Restated because it is the thing most often gotten wrong: correctness and data safety → accessibility → existing product consistency → task efficiency → responsive behavior → visual quality → novelty.

Aesthetic guidance from `ui-redesign` enters at level 6. It never outranks the first five.

## Build sequence

1. **Understand the task the screen serves.** What is the user trying to finish? Everything else follows from that.
2. **Check what exists.** Component library, tokens, established patterns. Compose before you create.
3. **Enumerate states before markup.** Loading, empty, error, success, plus partial and permission-denied where they apply. Design the error path with the happy path, not after it.
4. **Structure semantically.** Landmarks, headings in order, lists as lists, buttons as buttons, links as links. ARIA only for what HTML cannot express.
5. **Wire validation to the contract.** Client rules mirror the server's; the server remains the enforcement point.
6. **Handle the failure path.** Network failure, timeout, partial success, stale data, double submit.
7. **Verify.** Keyboard-only pass, three widths, reduced-motion, lint, typecheck, tests, production build.

## Review pass

When reviewing existing UI, walk `reference.md` in order and report findings by hard rule ID. A finding against a hard rule is a defect; a finding against a soft default is a suggestion, and should be labeled as one.

## Common failures worth checking first

- A spinner standing in for the entire state set
- Placeholder used as a label
- Focus ring removed by a reset
- Error text that says something went wrong without saying what or what next
- Client-only validation on a field the server also enforces differently
- Touch targets too small on the mobile breakpoint
- A modal that traps nothing, or traps everything and cannot be escaped

---
id: frontend-standards
title: Frontend Standards
scope: glob
globs: ["**/*.tsx", "**/*.jsx", "**/*.vue", "**/*.svelte", "**/*.html", "**/*.css", "**/*.scss", "**/*.astro"]
category: frontend
version: 2.0.0
updated: 2026-08-30
freshness: tracked
---

# Frontend Standards

The quality floor for shipped UI. Full checklist: `.agents/skills/frontend-standards/SKILL.md` and its `reference.md`.

## Decision order

When two UI considerations conflict, resolve in this order. This settles the v1 conflict between visual novelty and everything else:

1. **Correctness and data safety** — no destructive action without confirmation, no silent failure
2. **Accessibility** — a user who cannot use it is not served by how it looks
3. **Existing product consistency** — a novel pattern that breaks the rest of the app makes the product worse
4. **Task efficiency** — fewest steps to the user's goal
5. **Responsive behavior**
6. **Visual quality and craft**
7. **Novelty** — distinctiveness for its own sake, lowest

## Hard rules

- **[H1]** Every async path renders four states: loading, empty, error, success. A spinner alone is not the set.
- **[H2]** Every interactive element is reachable and operable by keyboard, with a visible focus indicator. Focus is never removed without an equivalent replacement.
- **[H3]** Every form control has a programmatically associated label. Placeholder text is not a label.
- **[H4]** Errors say what went wrong and what to do next, are associated with their field, and are announced to assistive technology.
- **[H5]** Client validation matches the server contract. Client validation is a convenience, never the enforcement point.
- **[H6]** Never render untrusted content as HTML. No `dangerouslySetInnerHTML` / `v-html` / `{@html}` on user-supplied or third-party data without sanitization at the boundary.
- **[H7]** No secrets, API keys, or privileged tokens in client code or bundles.
- **[H8]** Images carry meaningful `alt`; decorative images carry empty `alt`. No filename-as-alt.
- **[H9]** Verify behavior at mobile, tablet, and desktop widths before calling it done. No horizontal scroll on mobile; touch targets meet the minimum size.
- **[H10]** Respect `prefers-reduced-motion`. No animation that cannot be disabled.
- **[H11]** Lint, typecheck, tests, and a production build all pass before shipping.
- **[H12]** Meet the accessibility target in `.agents/config/defaults.md` for the surface being built — currently WCAG 2.2 AA.

## Soft defaults

- **[S1]** Compose from existing components before creating a new one.
- **[S2]** Semantic HTML before ARIA. ARIA is a patch, not a foundation.
- **[S3]** Design tokens over hardcoded values for color, spacing, radius, and type.
- **[S4]** Optimistic updates only where the failure path is designed.
- **[S5]** Test at the widths in `defaults.md` unless the product's analytics say otherwise.
- **[S6]** Keep bundle growth visible: state the cost when adding a dependency to the client bundle.

## Interaction with other rules

`ui-redesign` supplies aesthetic guidance. Every item there is soft and sits at level 6–7 of the decision order above. No aesthetic preference may override [H1]–[H12], and none may override established product consistency without the user asking for a visual overhaul.

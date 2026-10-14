---
id: ui-redesign
title: UI Redesign
scope: glob
globs: ["**/*.tsx", "**/*.jsx", "**/*.vue", "**/*.svelte", "**/*.html", "**/*.css", "**/*.scss", "**/*.astro"]
category: frontend
version: 2.0.0
updated: 2026-08-30
freshness: none
---

# UI Redesign

Raising the quality of existing UI without breaking it. Full procedure: `.agents/skills/ui-redesign/SKILL.md`.

Triggers: a request to redesign, polish, or improve look and feel; an audit for generic AI-generated design; missing interaction states.

## Hard rules

These are hard because violating them ships a defect, not a taste disagreement.

- **[H1]** Do not break existing functionality. Verify after each change.
- **[H2]** Work within the existing stack. Do not migrate framework, styling system, or component library as part of a visual pass.
- **[H3]** No placeholder content in shipped UI — no Lorem Ipsum, no `#` links, no fake avatars or invented testimonials, no dead buttons.
- **[H4]** Never remove a focus indicator, a label, a landmark, an `alt` attribute, or an ARIA relationship in pursuit of a cleaner look.
- **[H5]** Preserve contrast. A restyled surface still meets the contrast requirement in `frontend-standards` [H12].
- **[H6]** Every interactive element keeps its full state set: default, hover, focus-visible, active, disabled, loading.
- **[H7]** Prefer small reviewable improvements to a rewrite. Do not rewrite a working screen to change its appearance.

## Soft defaults — aesthetic guidance

**Every item below is a preference, not a requirement.** They exist to interrupt autopilot, not to ban patterns. Each is phrased as "do not reach for this by default" — if the pattern is the right answer for this product's information architecture, use it and say why in one line.

- **[S1]** Do not default to a left sidebar. Choose navigation from information architecture, screen complexity, and how the user actually moves through tasks. *A left sidebar is frequently the correct choice for a complex SaaS dashboard — this is a prompt to decide, not a prohibition.*
- **[S2]** Do not default to a three-column card grid. Ask whether the items are genuinely parallel and genuinely three.
- **[S3]** Do not default to one ubiquitous icon set or one ubiquitous UI font. Consistency within a product beats novelty; if the set already in use is working, keep it.
- **[S4]** Do not default to an FAQ accordion. Accordions are right when items are independent and scanned selectively, wrong when the content is read in sequence.
- **[S5]** Do not default to a hero of big-number + gradient accent. Lead with the most characteristic thing about the product.
- **[S6]** Spend boldness in one place. One signature element, everything around it quiet.
- **[S7]** Set an intentional type scale with deliberate weights and spacing rather than inheriting framework defaults.
- **[S8]** Prefer a consistent spacing scale to ad-hoc values.
- **[S9]** Avoid arbitrary `z-index` values; keep a named layer scale.
- **[S10]** Avoid `div` soup — use the element that carries the meaning.

## Interaction with other rules

Subordinate to `frontend-standards` in full. When a soft item here conflicts with product consistency, consistency wins unless the user has asked for a deliberate visual break.

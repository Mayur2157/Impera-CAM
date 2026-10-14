---
name: ui-redesign
description: Raise the visual and interaction quality of an existing website or app without breaking it or migrating its stack. Use when asked to redesign, polish, or modernize UI, or to audit an interface for generic AI-generated design patterns.
---

# UI Redesign

Binding rules: `.agents/rules/frontend/ui-redesign.md`. The hard rules there protect function and accessibility; everything aesthetic is soft.

## Before changing anything

Establish the constraint set:

- What is the existing stack, component library, and token system? You are working inside it.
- What patterns are already load-bearing across the product? Breaking one screen's convention breaks the product's learnability.
- Is this a polish pass or a deliberate visual overhaul? The answer changes how much consistency you may spend.
- What does the user actually dislike? "Make it better" is not a brief — get one concrete example.

## Audit order

1. **Function** — anything broken, dead, or placeholder. Fix these first; they are defects.
2. **Accessibility** — missing focus, labels, contrast, alt text, keyboard traps.
3. **States** — hover, focus-visible, active, disabled, loading, empty, error.
4. **Structure** — semantics, heading order, layer scale, spacing consistency.
5. **Craft** — typography, rhythm, alignment, density.
6. **Character** — the one thing that makes this product recognizably itself.

Most of the value is in 1–3. Skipping to 6 produces a prettier broken screen.

## On generic design

Current AI-generated UI clusters into recognizable defaults: warm cream background with high-contrast serif and terracotta accent; near-black with one acid accent; broadsheet hairline rules and dense columns. The same is true of layout habits — the three-card row, the left rail, the big-number hero.

None of these is bad. They are *unchosen*. When an axis is free, spend that freedom deliberately instead of landing on the default. When the brief pins a direction, follow the brief exactly.

Ground the choices in the subject: the product's own domain, vocabulary, and materials are where a distinctive direction comes from.

## Working method

Two passes. First, a compact plan: 4–6 named palette values, typefaces for display and body (and a utility face if data-dense), a layout concept, and the one signature element. Review that plan against the brief — if a part of it reads like what you would produce for any similar product, change it and say what you changed.

Then build to the plan. Small reviewable commits, verify function after each. Spend boldness in one place and keep everything around it quiet.

## Copy

Words are design material. Name things by what the user controls, not by how the system is built. Active voice; a control says what happens when it is used, and keeps the same name through the whole flow. Errors explain what went wrong and how to fix it. An empty state is an invitation to act, not an apology.

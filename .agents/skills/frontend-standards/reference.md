<!-- freshness: tracked · register entry `frontend-standards` in .agents/config/freshness.json -->

> Accessibility target and criteria references were last verified 2026-08-30 against the W3C WAI publications. Confirm the current WCAG version and applicable success criteria for the surface you are building before treating a specific criterion number as authoritative.

# Frontend Standards — Full Checklist

Walk this in order during a review. Report findings by rule ID: a hard-rule finding is a defect, a soft-default finding is a suggestion and must be labeled as one.

---

## 1. States

- [ ] **[H1]** Loading state exists and is not only a spinner — skeleton or progress where the wait is long
- [ ] **[H1]** Empty state explains what would be here and how to get it
- [ ] **[H1]** Error state distinguishes recoverable from terminal, and offers the recovery
- [ ] **[H1]** Success state confirms what happened, in the same vocabulary as the action
- [ ] Partial-success state where an operation can half-fail
- [ ] Permission-denied state distinct from empty
- [ ] Stale-data indication where data can go out of date behind the user

## 2. Keyboard and focus

- [ ] **[H2]** Every interactive element reachable by Tab, in a sensible order
- [ ] **[H2]** Visible focus indicator on every focusable element, with sufficient contrast against its background
- [ ] **[H2]** No focus removed without an equivalent replacement — `outline: none` alone is a defect
- [ ] Escape closes overlays; focus returns to the trigger
- [ ] Focus is trapped inside a modal while it is open, and only while it is open
- [ ] Skip link to main content on pages with substantial navigation
- [ ] Custom controls implement the expected key behavior for their role (arrows in a listbox, Enter/Space on a button)

## 3. Forms

- [ ] **[H3]** Every control has a programmatically associated label
- [ ] **[H3]** Placeholder is not doing a label's job
- [ ] **[H4]** Errors state what went wrong and what to do
- [ ] **[H4]** Errors are associated with their field and announced to assistive technology
- [ ] **[H5]** Client validation matches the server contract exactly — same rules, same limits
- [ ] Required fields marked in text, not by color or asterisk alone
- [ ] Autocomplete attributes on common personal fields
- [ ] Input type and mode appropriate on mobile
- [ ] Submit is disabled or guarded against double submission
- [ ] Field-level validation timing does not punish the user mid-typing

## 4. Security

- [ ] **[H6]** No untrusted content rendered as raw HTML without sanitization at the boundary
- [ ] **[H7]** No secrets, keys, or privileged tokens in client code, bundles, or source maps
- [ ] Sensitive values not written to `localStorage` where a shorter-lived store will do
- [ ] External links carrying `rel="noopener noreferrer"` where they open new contexts
- [ ] File upload constrains type and size on the client and relies on the server to enforce
- [ ] URLs from user data validated before use in `href` or `src`
- [ ] No sensitive data in query strings, which end up in logs and referrers

## 5. Content and semantics

- [ ] **[H8]** Meaningful `alt` on informative images; empty `alt` on decorative ones
- [ ] Headings form a correct outline with no skipped levels
- [ ] Landmarks present: header, nav, main, footer
- [ ] Lists marked up as lists; tables have headers and a caption or accessible name
- [ ] Buttons are buttons and links are links — a `div` with a click handler is a defect
- [ ] Page has a unique, descriptive title
- [ ] Language attribute set on the document

## 6. Responsive

- [ ] **[H9]** Verified at mobile, tablet, and desktop widths (see `defaults.md`)
- [ ] **[H9]** No horizontal scroll at the smallest supported width
- [ ] **[H9]** Touch targets meet the minimum size with adequate spacing
- [ ] Content reflows rather than being hidden as the viewport narrows
- [ ] Usable at 200% zoom
- [ ] Sticky elements do not eat the viewport on short screens
- [ ] Hover-only affordances have a touch equivalent

## 7. Motion and preferences

- [ ] **[H10]** `prefers-reduced-motion` respected — no unstoppable animation
- [ ] Auto-playing motion can be paused
- [ ] Transitions are fast enough not to delay a task
- [ ] Dark mode, if supported, maintains contrast rather than just inverting

## 8. Contrast and color

- [ ] **[H12]** Text contrast meets the target ratio for its size
- [ ] Non-text contrast met for controls, focus indicators, and meaningful graphics
- [ ] Color is never the only carrier of meaning — pair it with text, icon, or pattern
- [ ] Disabled states remain legible

## 9. Performance

- [ ] Images sized, formatted, and lazy-loaded below the fold
- [ ] No layout shift from late-loading images, fonts, or ads
- [ ] Fonts loaded with a sane fallback and no invisible-text flash
- [ ] Long lists virtualized rather than rendered whole
- [ ] Bundle cost of each added client dependency stated
- [ ] Network waterfall checked for sequential requests that could be parallel

## 10. Definition of done

- [ ] **[H11]** Lint passes
- [ ] **[H11]** Typecheck passes
- [ ] **[H11]** Tests pass
- [ ] **[H11]** Production build succeeds
- [ ] Keyboard-only pass completed by hand
- [ ] Three widths checked by hand
- [ ] No console errors or warnings introduced
- [ ] No placeholder content, dead links, or non-functional controls

---

## Review reporting format

```
[H3] LoginForm.tsx:42 — email input has no associated label; the placeholder is
     carrying the label's job. Screen reader announces "edit text, blank".
     Fix: <label for="email"> or aria-label.

[S3] Button.tsx:18 — hardcoded #3B82F6 instead of the primary token.
     Suggestion, not a defect.
```

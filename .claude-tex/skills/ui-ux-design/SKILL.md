---
name: ui-ux-design
description: Use for any UI/UX work — screen layout, typography, color, spacing, component states, forms, motion, accessibility, design tokens, or reviewing an implemented UI against design quality. Numbers-first design doctrine that works with any brand; brand specifics come from the company brain.
---

# UI/UX Design

Design is decisions with numbers, not taste. Every rule here has a value you can check; "looks nice" is not a review verdict. Brand personality (colors, fonts, tone) comes from the company brain — this skill is the craft underneath any brand.

## Spacing & layout

- **One spacing scale, 4px base**: 4, 8, 12, 16, 24, 32, 48, 64. Every margin/padding/gap is one of these — an 18px gap is a bug.
- Related items sit closer than unrelated ones (proximity IS grouping). Space between sections ≥ 2× the space within a section.
- Content max-width for reading surfaces: 640–760px; full-bleed only for dashboards/tables/canvas.
- Touch targets: **≥ 44×44px** (Apple HIG) / 48dp (Material). Desktop click targets ≥ 32px with ≥ 8px between destructive and safe actions.
- Align to a grid: 12-column for web pages, 8pt grid for apps. Nothing centers "by eye".

## Typography

- Max **2 typefaces** (one is usually right: UI + mono for code). Weights carry the hierarchy: 400 body, 500–600 headings/labels, 700 sparingly.
- Type scale with a fixed ratio (~1.25): e.g. 12, 14, 16, 20, 25, 31, 39. Body text **16px minimum** (14px only for dense data UI); never below 12px anywhere.
- Line height: **1.5** for body, **1.1–1.3** for headings. Line length **45–75 characters** — wider reads worse, cap it with max-width.
- Don't use color alone to differentiate text roles — pair with weight or size.
- Numbers in tables: tabular figures (`font-variant-numeric: tabular-nums`), right-aligned.

## Color

- Structure: **60/30/10** — 60% neutral surface, 30% secondary surfaces/borders, 10% brand/accent. If brand color covers half the screen, it stops meaning anything.
- Contrast is law (WCAG AA): **4.5:1** for body text, **3:1** for large text (≥ 24px / 19px bold) and for UI components/borders against adjacent colors. Verify with a checker, not eyes.
- Semantic colors are reserved: green = success, red = danger/error, amber = warning, blue = info. Never decorative red.
- Color never carries meaning alone — pair with icon/label (8% of men are color-blind).
- Dark mode: no pure black (#000) surfaces — use dark gray ramps (e.g. #121212 base, lighter = elevated); desaturate brand colors slightly; re-verify every contrast pair separately.

## Component states — a component isn't done at "default"

Every interactive component ships all of: **default · hover · focus-visible · active · disabled · loading**. Every data surface ships all of: **loading (skeleton, not spinner-only) · empty · error · partial/offline**.

- Focus: a visible ring (≥ 2px, ≥ 3:1 contrast) on EVERY focusable element. Removing outlines without replacement fails review.
- Empty states sell the feature: icon + one line of what belongs here + the primary action to create it. A blank white void is a design defect.
- Error states say what happened AND what to do next; never raw exception text.
- Disabled controls that users will wonder about get a tooltip/hint explaining why.

## Hierarchy & flow

- **One primary action per screen.** One filled button; everything else outline/ghost/link. Two filled buttons side-by-side = the design hasn't decided.
- Destructive actions: never the default button, never adjacent to the primary, confirm with the consequence named ("Delete 3 projects" not "Are you sure?").
- Scanning order: size → weight → color → position. If everything is bold, nothing is.
- Progressive disclosure: the 80% case on the surface; the 20% behind "Advanced". Settings pages with 40 visible toggles fail review.

## Forms

- Labels ABOVE fields (not placeholder-as-label — it vanishes on input). Placeholder = example format only.
- Validate on blur, re-validate on change after first error. Never on every keystroke of a pristine field; never only on submit for long forms.
- Error next to the field, red + icon + specific fix ("Password needs 8+ characters", not "Invalid input"). Keep the user's input on error — clearing a form is hostile.
- Mark OPTIONAL fields, not required ones (most fields should be required or removed).
- One column beats two: multi-column forms get skipped fields and worse completion.
- Right keyboard per input on mobile (`inputmode="email"`, `numeric`, `tel`); autocomplete attributes set.

## Motion

- Micro-interactions (hover, toggle): **100–200ms**. Panels/modals/drawers: **200–300ms**. Anything > 400ms feels broken.
- Ease-out for entering elements, ease-in for exiting, never linear for UI movement.
- Motion must mean something: direction matches spatial model (drawer from the edge it lives on), things don't animate just to exist.
- Respect `prefers-reduced-motion`: replace movement with opacity fades, keep durations but kill translation/scale.

## Accessibility gates (blocking, not optional)

1. Full keyboard path: every action reachable by Tab/Enter/Escape, in logical order, no traps.
2. Contrast pairs verified AA (see Color).
3. Images: alt text (or `alt=""` when purely decorative). Icon-only buttons: `aria-label`.
4. Native elements first (`button`, `a`, `select`, `dialog`); ARIA only when native can't do it — a `div onclick` fails review.
5. Zoom to 200%: no lost content, no horizontal scroll on text surfaces.
6. Announce async results (`aria-live="polite"` for toasts/updates).

## Design tokens & handoff

- Name by ROLE, not value: `color-surface`, `color-text-muted`, `color-danger`, `space-4`, `radius-md`, `font-size-body` — never `$blue-500` in component code.
- One tokens file (CSS variables / platform equivalent) both light and dark themes read from. Hardcoded hex in a component = review reject.
- Handoff = tokens + component states (all of them) + spacing annotations + interaction notes. A static happy-path mockup is half a handoff.

## Review checklist (the design gate, run in order)

1. Spacing: all values on the scale? Sections breathe more than their contents?
2. Type: scale respected, body ≥ 16px, line length ≤ 75ch?
3. Contrast: AA verified for text AND UI components, both themes?
4. States: all interactive + all data states present?
5. One primary action? Destructive separated + named?
6. Keyboard walk: complete the core flow mouse-free?
7. Mobile: targets ≥ 44px, right keyboards, no horizontal scroll?

## Done-gates

- **Screen design done** = every state designed (not just happy-path), tokens named, both themes, checklist above passes.
- **UI implementation done** = matches the spec at token level (not "close"), keyboard walk recorded, contrast re-verified in the BUILT UI (rendered colors drift from mockups).
- Never sign off from a screenshot alone — click it, tab it, zoom it.

# Authenticated Theme Revamp Guide

> Scope lock: only authenticated (inside-app) layouts inherit the new light theme. Landing/marketing pages remain on the current dark brand stack and must not pull in these overrides.

## 1. Theme Model & Tokens

- Treat the existing tokens as semantics. We **keep the same Tailwind token names** but remap them to light counterparts when `data-theme="light"` is active in `myApp/base.html`.
- Landing templates continue to resolve the legacy dark values.

| Token | Dark Hex (landing + dark mode) | Light Hex (authenticated default) | Intent |
|-------|-------------------------------|------------------------------------|--------|
| `ink-bg` | `#0A0A0F` | `#F7F8FB` | Base canvas/background |
| `ink-surface` | `#141420` | `#FFFFFF` | Cards, nav bars, modals |
| `electric-violet` | `#8B5CF6` | `#6D28D9` (or keep `#8B5CF6` if WCAG passes) | Primary accent |
| `cyan` | `#06B6D4` | `#0891B2` | Secondary accent/highlight |

### Tailwind Runtime Config (authenticated base)

- Define both palettes in `tailwind.config` and expose them via CSS variables:
  - `[data-theme="dark"] --color-ink-bg: #0A0A0F`, etc.
  - `[data-theme="light"] --color-ink-bg: #F7F8FB`, etc.
- Update utility classes (`bg-ink-bg`, `border-ink-surface`, etc.) to read from the CSS variables so the same markup works in both themes.

### Utility Alias Remaps

Introduce theme-aware aliases to eliminate hardcoded dark utilities:

| Legacy Utility | Replace With | Light Resolution | Dark Resolution |
|----------------|--------------|------------------|-----------------|
| `bg-white/5` | `.bg-overlay-weak` | `rgba(15, 23, 42, 0.05)` (`#0F172A` @ 5%) | `rgba(255, 255, 255, 0.05)` |
| `border-white/10` | `.border-default` | `#E5E7EB` (`zinc-200`) | `rgba(255, 255, 255, 0.1)` |
| `text-white/60` | `.text-muted` | `#64748B` (`slate-500/600`) | `rgba(255, 255, 255, 0.6)` |
| `text-white` | `.text-strong` | `#0F172A` (`slate-900`) | `#FFFFFF` |

Document these and migrate components to the aliases before theme launch.

## 2. Gradients & Effects

- Keep the primary gradient (`from-electric-violet to-cyan`) across both themes.
- On light:
  - Add `ring-1 ring-black/5` or `border-default` for CTAs so edges don’t disappear.
  - Replace colored outer glows with soft, neutral shadows (`shadow-[0_2px_16px_rgba(2,6,23,0.08)]`).
- Background patterns (e.g., violet dots) should drop to ~20% opacity or swap to `slate-200` dots.

## 3. State Colors (Light Theme)

| State | Background | Border | Text/Icon |
|-------|------------|--------|-----------|
| Success | `bg-green-50` | `border-green-200` | `text-green-700` |
| Warning | `bg-amber-50` | `border-amber-200` | `text-amber-700` |
| Error | `bg-rose-50` | `border-rose-200` | `text-rose-700` |
| Info | `bg-cyan-50` | `border-cyan-200` | `text-cyan-700` |

Avoid semi-transparent whites for these callouts in light mode.

## 4. Optional Theme Toggle (Strategy B)

- Add a sun/moon toggle within authenticated nav.
- Preference hierarchy:
  1. User choice (persist via localStorage or profile field).
  2. `prefers-color-scheme`.
  3. Default to light.
- Apply `data-theme="light|dark"` to `<body>` or `<html>` before Tailwind loads to avoid FOUC.
- No landing impact: those pages never set `data-theme` or include the toggle script.

## 5. Page-Level Adjustments (Authenticated Only)

- **Home (`home.html`)**
  - Board cards: `bg-ink-surface` resolves to white; add `border-default` + soft shadow.
  - Progress rails: keep gradient, add subtle ring for definition.
  - Replace glowing module halos with low-alpha shadows (`shadow-[0_6px_18px_rgba(109,40,217,0.18)]`).

- **Lesson Runner (`lesson_runner.html`)**
  - Sticky header: white background, `border-b border-default`.
  - Stage labels: `.text-muted` for inactive, violet for active.
  - Review cards: use tinted backgrounds from state table above.

- **Milestone Challenge (`milestone_challenge.html`)**
  - CTA buttons: gradient with `ring-1 ring-black/5`.
  - Pass/fail banners use state tints; ensure copy is `text-strong`.
  - Recording status badge switches from red glow to `bg-rose-500 text-white` chip.

- **Onboarding (`onboarding.html`)**
  - Option tiles: white surface + `border-default` by default, `border-electric-violet ring-2 ring-violet-200` on select.
  - Step dots: inactive `bg-slate-300`, active `bg-electric-violet`, completed `bg-green-500`.

- **AI Coach (`ai_chat.html`)**
  - Background becomes `bg-ink-bg` (`#F7F8FB`) with optional `bg-gradient-to-b from-white via-slate-50`.
  - Chat bubbles: gradient bubble retains, add `border-black/5`.
  - Error replies: `bg-rose-50 border-rose-200 text-rose-700`.

- **Districts (`district_detail.html`, `district_venue.html`)**
  - Cards: white with `border-default` and `hover:border-electric-violet`.
  - Ticket/XP stats: solid text, optional tinted pills (`bg-cyan-50`, `bg-violet-50`).

- **Profile (`profile.html`)**
  - Stat tiles: white surfaces, thin border, neutral shadow.
  - Labels shift to `.text-muted`; numbers keep accent colors.

### Lesson Runner Concept & Experience

- **Purpose**: `lesson_runner.html` delivers the core learning experience inside the app, walking the learner through each knowledge block without leaving the flow. It organizes content into sequential stages (Teach → Drill → Review → Checkpoint) and keeps progress visible at all times.
- **Structure**:
  - Sticky header surfaces module metadata (skill, outcome, time), streak/XP, and a stage rail that animates as the learner advances.
  - A card carousel renders one stage at a time; each card draws from `current_block` and `knowledge_blocks` so that server-provided data is hydrated into the UI.
  - The coach sheet (`#coachSheet`) slides up for additional guidance, reusing the same theme tokens to stay on-brand.
- **Data Flow**: `views.py` supplies module context, progress state, and user stats. Inline JavaScript (bottom of the template) handles stage transitions, character counts, saving drill responses, and toggling the coach sheet—no full page reload needed.
- **Theming Notes**: Use semantic tokens (`bg-ink-surface`, `text-text-strong`, `border-default`, `bg-overlay-weak`) so the entire flow adapts automatically between light and dark themes, while gradient CTAs and progress bars retain the violet→cyan brand signature.
- **Learner Journey**:
  1. **Teach** presents summaries/citations.
  2. **Drill** captures practice input with hints/templates.
  3. **Review** displays AI feedback in state-tinted cards (green/amber/cyan).
  4. **Checkpoint** confirms completion and unlocks the next block or milestone.
  - Ensure all interactive elements maintain visible focus states (`focus:ring` in violet) and gradient CTAs include a neutral ring (`ring-black/5` on light, `ring-white/20` on dark) for contrast.

## 6. Shared Component Rules

- **Top Nav (`base.html`) & Bottom Nav (`components/bottom_nav.html`)**
  - Surfaces: white with `border-default`.
  - Active tab indicator: 2px violet underline; remove glow.
  - Floating center CTA: gradient + `ring-2 ring-white` (dark) vs `ring-2 ring-black/5` (light).
  - Icons set `class="text-current"` so they follow theme color.

- **Auth & Forms**
  - Inputs: `bg-white`, `border-zinc-300`, focus `border-electric-violet focus:ring-2 focus:ring-violet-200`.
  - Placeholders: `.text-muted`.
  - Primary buttons: solid violet with accessible hover shade; secondary buttons: white with zinc border.

- **Flash Messages / Toasts**
  - Convert to state tint pattern; include leading icon with accent color.

- **Logo Assets**
  - Provide dark-on-light variant for authenticated nav.
  - If only light logo exists, wrap it in a pill (`bg-electric-violet/10 border border-electric-violet/20`) so it maintains contrast.

## 7. Migration Checklist

1. Define light and dark token variables in `myApp/base.html` runtime Tailwind config.
2. Create utility aliases (`overlay-weak`, `border-default`, `text-muted`, `text-strong`) and replace hardcoded dark utilities.
3. Audit authenticated templates for raw `bg-white/5`, `text-white`, etc., and swap to aliases.
4. Add neutral rings/borders to gradient CTAs.
5. Update cards from glassmorphism to solid white surfaces with subtle shadows.
6. Ensure logo variant renders correctly on white.
7. Revisit status chips and banners for contrast and readability.
8. (If toggle enabled) Implement persistence + data-theme loading script.

## 8. QA & Smoke Tests

- Verify each primary flow (Home, Lesson Runner, Milestone, Onboarding, AI Coach, Districts, Profile) in light mode:
  - No white text on white backgrounds.
  - Disabled states remain visible.
  - Hover/focus indicators are obvious and accessible.
  - SVG icons adopt current color (no invisible white icons).
  - Gradients remain legible with new rings/shadows.
- Confirm landing pages still load the original dark palette.
- Check contrast: headings ≥ 7:1 (slate-900), body copy ~5:1 (slate-700).
- Validate focus states meet accessibility (visible `ring` or border).
- Respect `prefers-reduced-motion` where animated glows previously lived.

## 9. Implementation Notes

- Tailwind is still delivered via CDN; keep the token config in `myApp/base.html`. Consider extracting the theme block into a partial if it grows complex.
- When adding new components, always use the semantic tokens/aliases (`bg-ink-surface`, `text-muted`, etc.) to inherit theme behavior automatically.
- Gradients should anchor on the established brand stops; if adding new stops, align with existing warm/cool palette for consistency.


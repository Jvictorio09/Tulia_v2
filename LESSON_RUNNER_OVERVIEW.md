# Lesson Runner Overview

This document summarizes the `lesson_runner` experience, how it currently works, and opportunities to extend or refine it. Use it as the baseline reference when iterating on the learning flow inside authenticated pages.

---

## 1. Purpose & Goals

- **Primary objective**: guide the learner through each module’s knowledge block in a single, focused flow.
- **Outcome**: deliver alternate states (Teach → Drill → Review → Checkpoint) that combine instruction, practice, feedback, and completion in one session.
- **Constraints**:
  - Must adapt to light/dark themes via tokenized classes.
  - Should minimize page reloads and preserve progress between sessions.
  - Needs to support optional A/B variants (coach sheet, hints) without divergent markup.

---

## 2. Template Entry Point

- File: `myApp/templates/myApp/lesson_runner.html`
- Django view: serves module context (`module`, `knowledge_blocks`, `current_block`), progress meta (`progress_data`), and user stats (XP, streak).
- Extends: `myApp/base.html`, inheriting the authenticated shell and theme configuration.

---

## 3. Layout & Structure

1. **Hidden data block**  
   `<div id="lessonData" data-block-id="..." data-module-code="..." ...>` seeds JS with IDs, module code, and block counts.

2. **Sticky progress header**  
   - Shows back button, skill/outcome/time metadata (when available), XP/streak stats, and stage rail.
   - Stage rail uses labeled dots/rings to indicate which phase is active (Teach, Drill, Review, Checkpoint).

3. **Card carousel (`#cardCarousel`)**  
   - Each stage is a `.card-slide` with `data-card="teach|drill|review|checkpoint"`.
   - Cards share markup pattern: heading + body + supporting elements.  
     - Teach: summary, citations.  
     - Drill: scenario/hints, textarea, hint toggle.  
     - Review: AI feedback in tinted blocks (keep using `bg-green-50`, `bg-amber-50`, etc.).  
     - Checkpoint: summary, CTA to next block/milestone.

4. **Coach sheet (`#coachSheet`)**  
   - Hidden bottom drawer that surfaces tips, backlog of tasks, or tools (Signal, 3×3, Radar).
   - Triggered via primary CTA and uses the same tokens for consistent theming.

5. **Modals/Tools**  
   - Imported partials (Signal Sentence, Message Builder, Style Radar) provide auxiliary helpers. Each tool now respects theme tokens.

---

## 4. Data & Script Flow

- Inline `<script>` at bottom orchestrates:
  - Stage transitions (e.g., toggling `hidden` on `.card-slide`).
  - Updating progress rail elements and compressed progress bar.
  - Handling drill textarea character counts and hint toggling.
  - Interacting with backend endpoints (fetch calls for saving drill responses, loading review feedback, etc.).
  - Positioning the player avatar on the board (if relevant modules require it).
- DOM dataset attributes supply the initial state (`data-block-id`, `data-total-blocks`, `data-module-code`), reducing hard-coded IDs.
- The script is theme-agnostic; styling relies on Tailwind classes defined in the HTML.

---

## 5. Theming Checklist

- Use semantic classes:
  - Surfaces: `bg-ink-surface`, `border-default`, `bg-overlay-weak`.
  - Text: `text-text-strong` for headings/body, `text-muted` for supporting copy.
  - Buttons: `bg-electric-violet`, `ring-1 ring-black/5` (light) or `ring-1 ring-white/20` (dark).
- Keep gradient CTAs (`from-electric-violet to-cyan`) for primary actions; add neutral rings so edges remain visible on white.
- Status feedback:
  - Success: `bg-green-50 border-green-200 text-green-700`.
  - Warning: `bg-amber-50 border-amber-200 text-amber-700`.
  - Info: `bg-cyan-50 border-cyan-200 text-cyan-700`.
- Ensure focus states use `focus:ring-2 focus:ring-brand` for accessibility.

---

## 6. North Star Experience — “Watch → Do → Explain → Transfer”

- Reframe the runner as a **multi-pass arc** that deepens mastery through repetition and escalating challenge.
- Core loop aligns to the eight-stage path below and repeats 2–3 times per knowledge block.  
- Each loop should last ~7–10 minutes; full modules span 45–60 minutes across multiple sittings with scheduled return passes.

### Loop Overview

| Stage | Purpose | Key Artifacts | Notes |
|-------|---------|---------------|-------|
| 0. Prime | Set intent, recall wins, pick focus behavior | Intention input, focus checkbox | New card |
| 1. Teach (Micro) | Deliver one concept (<300 words) | Copy, figure, example | Use existing concept tiles |
| 2. Diagnose | Identify stakes (A1), rate PIC (B1), label load (D1) | Structured prompts, sliders | Chain exercises in one pass |
| 3. Control-Shift | Choose lever (3P) + action | Lever selector, action input | Merge B2 + E1 logic |
| 4. Perform | Practice text & voice (w/ optional body drill) | Text area, recorder hook, C2 baseline | Adds 4a + 4b subcards |
| 5. Review | AI rubric + self-explain | Rubric scores, reflection prompt | Reuse tinted feedback blocks |
| 6. Transfer | Log next real moment (A2) | Scenario form, PIC sliders | Schedules follow-up |
| 7. Spacing | Return pass (micro loop) | Quick re-teach, voice, review | Triggered after delay |

---

## 7. Stage Breakdown & Content Mapping

### 0) Prime (New)
- **Goal**: lower emotional load, set intention, clarify success metric.
- **UI**: short intention input (1–2 lines), checkbox group for 3P focus (Preparation / Presence / Perspective), optional micro animation to acknowledge prior win.
- **Implementation**: new `prime` card type; data stored with `loop_index`, `focus_choice`.

### 1) Teach (Micro)
- **Goal**: single concept burst (e.g., “Stakes = Pressure + Visibility + Irreversibility”).
- **Constraints**: <300 words, one figure, one example. Sequence concept tiles to build narrative across loops.
- **Content feed**: reuse existing knowledge snippets; mark each tile with `concept_slug` for analytics.

### 2) Diagnose (Richer)
- **Goal**: chain A1 (stakes detector) → B1 (PIC rating) → D1 (load label) in one pass.
- **UI**: scenario prompt (pre-filled from Transfer or user entry), toggles for Pressure/Visibility/Irreversibility, PIC slider, load radio buttons.
- **Data**: persists as a single `diagnosis` payload containing all sub-results to reduce duplication.

### 3) Control-Shift (Action)
- **Goal**: pick one lever and define the action.
- **Mapping**: merges existing B2/E1 patterns; present lever cards (Preparation/Presence/Perspective) with quick descriptors, plus free-text “What action will you take?”
- **Persistence**: store `lever_choice`, `action_text`, `scenario_ref`.

### 4) Perform (Guided)
- **Structure**:
  - **4a Text Performance**: write a 90–120 word opening/outcome using the chosen lever.
  - **4b Voice Performance**: 30–45 second spoken version (upload or record when infra ready).
  - Optional **C2 Body Awareness drill**: pre/post self-report plus guided reset steps.
- **UI**: treat as stacked subcards within the stage; show timers or progress meters to emphasize time-boxing.
- **Data**: keep separate entries for text vs. voice attempts; include `body_reset_before`/`after` metrics if C2 triggered.

### 5) Review (AI + Self-Explain)
- **Goal**: provide rubric-based feedback and force reflection.
- **Components**:
  - AI rubric thresholds (clarity, audience relevance, control cues, etc.).
  - Self-explain prompt: “Why did this work? What tweak next?”
- **Visuals**: reuse tinted chips (`bg-green-50`, `bg-amber-50`, `bg-rose-50`) to highlight current rating.
- **Data**: store AI scores + user reflection for progress analytics.

### 6) Transfer (Next Moment)
- **Goal**: log or revisit the learner’s upcoming high-stakes moment (A2).
- **UI**: scenario name, date/time, PIC sliders, optional free text for context, lever selection for future focus.
- **Outcome**: sets a `return_pass_at` timestamp to schedule spacing.

### 7) Spacing (Return Pass)
- **Mechanic**: schedule short booster loops (2–3 cards) 24–72h later.
  - Micro re-teach tile (different example).
  - Perform (voice-only).
  - Review (lightweight rubric + quick reflection).
- **Trigger**: view layer shows a notification/CTA; no new page required.
- **Storage**: add `pass_type` (`main` vs `return`) and `scheduled_for` fields to existing progress models.

---

## 8. Coach Sheet as “Sidekick”

- **Stage-aware content**:
  - Diagnose: slide-in definitions, mini PIC explainer, quick reference diagrams.
  - Perform: C2 body reset timer, breath/countdown prompts.
  - Review: rubric explanations with exemplars (“What ‘clarity’ looks like”).
  - Transfer: one-tap templates for logging next moment (A2) with PIC sliders.
- **Implementation**: feed the coach sheet via `data-stage` attribute; no new UI chrome required.

---

## 9. Progression & Analytics

- **Progression model**:
  - Block mastery ≥ 80 unlocks harder loop variants (tighter time boxes, higher-stakes scenarios).
  - Loop mastery requires: one text + one voice performance, one lever action logged, one transfer entry scheduled.
  - Module pass = 2–3 loops completed over ≥2 days (spacing requirement).
- **Analytics to track & surface**:
  - PIC delta loop-to-loop (show trend if control ↑).
  - Load labeling accuracy (emotional vs cognitive).
  - Lever usage mix (which 3P choices dominate).
  - Physio self-report shift from C2 (tense → less tense).
- **UI surfacing**: add summary chips in header/toast (“Control ↑2”, “Lever mix: Presence 60%”).

---

## 10. Time Budget

- **Single loop**: ~7–10 minutes  
  Prime (1) → Teach (2) → Diagnose (2) → Control-Shift (1) → Perform (2–3) → Review (1) → Transfer (1)
- **Two loops in a sitting**: ~20 minutes.
- **Return pass**: 4–6 minutes.
- Emphasize “short bursts, repeated often” to raise total learning hours without fatigue.

---

## 11. Implementation Notes

- **Cards**: add new types (`prime`, `transfer`, `return-pass`) while reusing existing carousel infrastructure.
- **Routing**: adjust the sequence generator to enqueue additional cards per loop; support `pass_type` flag.
- **Persistence**: extend current payload schema with `loop_index`, `pass_type`, `lever_choice`, `return_pass_at`.
- **Webhooks**: reuse existing endpoints for exercises (A1, A2, B1, B2, C2, D1, E1); ensure data binder handles chained inputs.
- **Coach Sheet**: populate via stage-specific partials; rely on `data-stage` for content selection.
- **Theme**: unchanged—continue using current tokens so light/dark support comes “for free.”

---

## 12. Quick QA Checklist

- Can a learner run Loop 1 end-to-end without dead ends?
- Do A1 → B1 → D1 chain smoothly without duplicate scenario entry?
- Does C2 appear before voice attempts and record pre/post states?
- Does Transfer (A2) schedule a return pass automatically?
- Does the coach sheet swap content per stage?
- Are PIC deltas and lever usage surfaced in the header/toast?
- Are focus states and instructions accessible via keyboard/screen reader?

---

_Last updated: {{DATE}}_


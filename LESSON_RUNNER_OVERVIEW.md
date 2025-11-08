# Lesson Runner Overview

This document captures the current intent, structure, and next-phase direction of the `lesson_runner`. Use it as the single source of truth when shipping UI, content, or data changes to the multi-pass learning arc.

---

## 1. Intent & Experience Pillars

**Tulia’s promise** is calm focus, structured insight, and emotional safety. Our enhancement wraps that pedagogy in micro-dopamine loops and gentle-game delight.

| Layer | Tulia baseline | Guided enhancement |
| --- | --- | --- |
| Cognitive | Mastery through reflection | Mastery through play + tight feedback |
| Emotional | Compassionate, self-aware tone | “Gentle-game” energy (mascot praise, soft glow wins) |
| Behavioural | 10-minute focused loops | 10-minute missions / quests |

Guiding mantra: _Less app → more journey_. Every click should feel like forward momentum.

---

## 2. System Snapshot

- **Template**: `myApp/templates/myApp/lesson_runner.html`
- **View**: `lesson_runner()` wires module meta, progress payload, content tiles, coach guardrails.
- **JS Orchestration**: `LessonRunnerMachine` (inline class) sequences stages, submits payloads, hydrates the coach sidekick, and now tracks mission context (scenario, PIC, lever).
- **Shared components**: signal sentence, 3×3 builder, style radar. Each now receives state via `window.lessonRunnerContext` for smart prefills.

---

## 3. Mission Loop Overview

Reframe the legacy Teach → Drill → Review → Checkpoint into an eight-step “Mission Loop.” Each knowledge block runs 2–3 loops (`loop_index`), then unlocks a return pass (`pass_type = return`).

| Legacy exercise | Mission name | Emoji | Emotional beat |
| --- | --- | --- | --- |
| Prime | **Prime Intent** | 🪄 | Grounded curiosity |
| A1 Stakes Detector | **Spot the Heat** | 🔎 | Curious diagnosis |
| B1 PIC Rating | **Decode the Pressure** | 📊 | Clarity |
| B2 Control Shift | **Take the Lever** | ⚡ | Agency |
| C1–C2 Reset drills | **Reset Mode** | 🧘 | Calm confidence |
| Perform (text/voice) | **Perform Mission** | 🎙️ | Momentum |
| Review (AI + reflect) | **Insight Check** | 🌟 | Encouraged mastery |
| A2 / Transfer | **Next Mission** | 🎯 | Anticipation |
| Spacing return pass | **Booster Loop** | 🔁 | Consistency |

_Optional flavor tiles_: “Brain vs Heart Test” (Load lab), “Your Player Map” (Stakes map) surface as boosters inside Diagnose & Review.

---

## 4. Stage Blueprint

### 0 · Prime Intent 🪄
- Inputs: intention sentence, focus lever chip (Preparation / Presence / Perspective).
- Output: `focus_lever`, `intention_text`. Animates with soft glow & supportive copy “You’ve set your focus.”

### 1 · Spot the Heat 🔎
- UI: scenario textarea (prefilled from Transfer), quick binary chips (“Who’s in the room?”), PIC sliders appear after the story stub.
- Data: `scenario_text`, `pic.{pressure,visibility,irreversibility}`. Reward: tiny “Curiosity +5” gem sparkle.

### 2 · Decode the Pressure 📊
- UI: slider confirmations, short explanation cards (“Pressure = consequences if…”) pulled from coach sheet if needed.
- Data: `pic.control`, `load_label` (Emotional / Cognitive / Mixed). Emotion: clarity.

### 3 · Take the Lever ⚡
- UI: lever cards with micro illustration, CTA “What’s the move?” text input.
- Data: `lever_choice`, `action_plan`. Reward: progress ring tick + “Lever locked in.”

### 4 · Reset Mode 🧘 (optional wrapper)
- UI: quick body reset slider (“Tension → Ease”), 30-second breathing animation.
- Data: `body_reset_before`, `body_reset_after`.

### 5 · Perform Mission 🎙️
- Sub-stages: **Text Pass** (word counter, timer), **Voice Pass** (link upload placeholder).
- Data: `text`, `audio_ref`, `duration_ms`.
- Reward: confetti bursts + XP sound.

### 6 · Insight Check 🌟
- UI: AI rubric chips (Clarity, Audience, Control). Self-explain prompt: “What made that feel right?”
- Data: `scores`, `self_explain`, `accept_suggestions`.
- Reward: “Insight +1” gem & friendly mascot reaction.

### 7 · Next Mission 🎯
- UI: upcoming moment form (title, date/time), optional PIC sliders for preview, lever suggestion.
- Data: `next_moment`, `desired_outcome`, `return_pass_at` (calculated). Buttons schedule 24h / 48h / 72h boosters.

### Booster Loop 🔁
- Triggered by scheduler; includes micro re-teach tile, voice-only perform, insight check. Light UI with ambient background to reinforce quick-hit practice.

---

## 5. Visual & Interaction System (Calm × Duolingo × Notion)

- **Card surfaces**: white (`bg-ink-surface`) with generous rounding, soft shadows, thin borders for clarity.
- **Ambient animation**: breathing gradients, subtle particles on stage completion, confetti for major milestones.
- **Mascot**: Coach Tuli (friendly speech bubble avatar) positioned near the coach toggle; reacts with captions (“Nice catch!”, “Deep breath first…”).
- **Color rhythm**:
  - Awareness phases (Prime, Diagnose): calm purples/blues.
  - Action phases (Lever, Perform): vivid violets/cyans.
  - Reflection/mastery (Review, Transfer): warm greens/golds.
- **Sound design**: soft chimes for progression, airy tone for insight, no harsh error sounds (use “Try another angle” copy instead).
- **Layout**: buttons anchored low-center for thumb reach; single action per card.

---

## 6. Motivation & Progress Architecture

| Trigger | Immediate reward | Reinforcement |
| --- | --- | --- |
| Submit any stage | +XP toast, gentle sound, progress ring tick | Stage label lights up
| Complete loop | Badge card + quote + shareable summary | Unlocks next mission tile
| Return consecutive days | Streak flame + “Keep your calm streak alive” nudge | Calendar highlights streak
| Record reflection | “Insight +1” gem counter updates | Feeds personalised coach tips

Re-use Tulia scoring (50 pts per exercise) but surface it visibly: progress ring around mascot, XP meter in header.

---

## 7. Copy & Tone Guidelines

- Replace academic directives with conversational prompts.
- Examples:
  - Instruction → “Tap what makes this moment feel intense.”
  - Feedback → “Exactly — pressure + visibility = that board-meeting buzz.”
  - Reflection → “What made this choice feel right?”
- Always celebrate awareness: “Interesting! That tension is data we can use.”

---

## 8. Personalisation Hooks

- Store tone words (“tense”, “steady”, “amped”); surface them in future encouragement (“You called it tense last time—how does it feel now?”).
- Track lever mix; when one lever dominates, spawn a challenge mission (“Try Perspective this round?”).
- Pause/resume: display “Resume Loop 2 of 3” overlay with calming animation.

---

## 9. Accessibility & Flow

- One-handed mobile first: CTAs centred near bottom, 48px targets.
- Support keyboard navigation & screen readers (aria-live on rewards, descriptive labels).
- Provide voice entry option for reflections where feasible.
- Cache micro drills for offline continuity; resume handshake on reconnect.

---

## 10. Implementation Roadmap

1. **Storyboard mission cards** – map each legacy exercise to new copy, emoji, reward moment.
2. **Refresh copy deck** – align micro-copy with new tone.
3. **Mascot system** – create React-ish helper (or Django include) that swaps reactions via data attributes.
4. **Scoring + streak surface** – expose aggregated XP, insight gems, and streak to the header JSON.
5. **Animation primitives** – CSS utility classes for glow, confetti, ambient gradients.
6. **User testing** – A/B “reflective vs playful” tone with 10 users; watch for focus/comfort.
7. **Ship Module A** – deliver full mission loop with boosters; track KPIs (completion %, reflection depth, return rate).

---

## 11. QA Checklist

- Loop 1 runs end-to-end with mission framing and rewards firing.
- Scenario text carries into Diagnose, Lever, Transfer without duplicate typing.
- Booster scheduling writes `return_pass_at` and surfaces in header.
- Coach sheet swaps stage-aware content + mascot reactions.
- Progress ring, XP meter, and streak flame update correctly.
- Focus states, keyboard flows, and screen readers succeed across stages.

---

## 12. Creative Seed (Shareable Prompt)

Use this seed with designers, writers, or generative tools:

> **Context**: “Design a calm-yet-playful mission loop for an adult communication coach called Tulia. Learners complete 10-minute quests to master high-stakes conversations. Keep the tone compassionate, but reward awareness with gentle dopamine (soft chimes, Coach Tuli mascot, progress rings). Stage names: Prime Intent 🪄, Spot the Heat 🔎, Decode the Pressure 📊, Take the Lever ⚡, Reset Mode 🧘, Perform Mission 🎙️, Insight Check 🌟, Next Mission 🎯, Booster Loop 🔁. One action per screen, accessible controls, color rhythm (cool purples for awareness, vibrant violets for action, warm greens for mastery). No red error states—use encouraging re-frames. Surface XP, streaks, and ‘Insight +1’ gems after each reflection. Aim for Calm × Duolingo × Notion vibes.”

Include module-specific content (concept tile summaries, real user scenarios, AI rubric copy) when handing off to content or motion teams.

---

_Last updated: 2025-11-08_


# Module Exercise Circuits – Level 1 District

This document explains how learner exercises are assembled for every Level 1 module, how the circuit is triggered from the lesson page, and what still needs to be produced for the remaining modules. Use this as a blueprint when refining content or planning additional districts.

---

## 1. Shared Exercise Framework

- **Flow-driven** – Each module is defined by a flow JSON (see `myApp/content/moduleA/moduleA.flow.json`) that arranges a linear sequence of exercise templates. Templates are referenced by their `template_id` and keep their own rendering/validation rules inside the lesson engine.  
- **Context threading** – Exercises read/write shared context (`current_scenario_ref`, `last_lever_choice`, etc.) so later steps can react to earlier answers. Guards can insert additional drills when thresholds are met (e.g., extra breathing drill when stakes are high).  
- **Scoring model** – Every flow declares completion, accuracy, and reflection weights. Currently Module A awards 40/30/30 points respectively with an unlock threshold of 300 and an “excellence” band at 450. The lesson page should surface the module score so users understand progress.  
- **Focus-first UX** – The updated lesson page (`module_learn.html`) drives immersion: cinematic video panel, live transcript with font controls, and a focus mode that temporarily hides the AI coach sidebar so exercises feel like a continuation of the lesson.  
- **Exercise storage** – Seed packs (e.g., scenario banks, mantra presets) live under `myApp/content/moduleA/` and are versioned. The `SeedLoader` verifies deprecation windows to prevent stale assets in production.

---

## 2. Module A — Foundations of High-Stakes Communication

### Goal
Help learners recognise high-stakes moments, regulate their state, and build a personal “stakes map.” The circuit is segment-driven (A–F) and mirrors the knowledge blocks defined in `seed_moduleA_sample.py`.

### Exercise Timeline

| Segment | Exercise ID | Template | Purpose / Notes |
|---------|-------------|----------|-----------------|
| A1 | `ScenarioTaggerCard` | Identify pressure / visibility / irreversibility across seeded scenarios; repeats x3 to show variety. |
| A2 | `PersonalScenarioCapture` | Capture the learner’s own upcoming high-stakes moment (becomes `current_scenario_ref`). |
| B1 | `TernaryRatingCard` | Rate Pressure / Impact / Control for the saved scenario; requires scenario context. |
| B2 | `SingleSelectActionCard` | Choose a control-shift behaviour; allows custom entry and stores `last_lever_choice`. |
| C1 | `MantraSelectOrWrite` | Pick or craft a reframing mantra (character limit 120). |
| C2 | `GuidedBreathDrill` | 30 s breathing micro-drill; asks for pre/post tension rating. |
| D1 | `BinaryClassifierCard` | Decide if current friction is emotional vs. cognitive load. |
| D2 | `PickThreeKeyPoints` | Distill the message to three essentials; free-text enabled. |
| E1 | `LeverSelector3P` | Choose the most useful 3P lever (Preparation / Presence / Perspective). |
| E2 | `PresenceRitualQuickStart` | Guided 28 s ritual; logs intention word. |
| F1 | `StakesMapBuilder` | Synthesize into the learner’s stakes map (situation → pressure → lever → action). |
| F2 | `ReflectionRatingCard` | Capture usefulness rating plus a follow-up reflection prompt when < 2. |

### Dynamic Guards

- **`high_stakes_relief`** – When recent stakes score ≥ 4, re-inserts an extended breathing drill before load classification.  
- **`presence_followup`** – If the learner chose “presence” in E1, inserts a longer ritual before the stakes map to reinforce transfer.  
- **`force_personal_scenario`** – Safeguard ensuring a personal scenario exists; re-prompts A2 if the context is missing.

### Assets & Seed Packs

- Scenario bank (`scenarios.moduleA.json`)  
- Control-shift action lists (`actions_control_shift.json`)  
- PIC rating examples (`pic_sets.json`)  
- Load case studies (`load_examples.json`)  
- Reframe mantra presets (`reframe_mantras.json`)  
- 3P lever cards (`lever_cards.json`)  
- Stakes map templates (`stakes_map_presets.json`)

Keep these packs versioned and align `deprecated_after` so content invalidates gracefully.

---

## 3. Module B — Audience Dynamics & Influence (Planned)

Module B’s video centres on stakeholder mapping, question ladders, and reframing objections. The exercises should push learners to apply those tactics immediately. Suggested circuit:

1. **Stakeholder Map Builder** – Drag/drop influence/interest grid seeded from enterprise vs. internal personas.  
2. **Motivation Decoder** – Multi-select reflection to identify incentives + friction for top three stakeholders.  
3. **Objection Reframe Drill** – Audio script or text prompts where learners rewrite a tough objection; could reuse the `SingleSelectActionCard` with influence-specific options or implement a new `ObjectionReframeCard`.  
4. **Question Ladder Practice** – Timed prompt generating “open → probing → commitment” question sequences.  
5. **Allies & Detractors Plan** – Template to record specific allies, neutral parties, and detractors with mitigation tactics.  
6. **Influence Commitments** – Reflection rating + immediate next action scheduling (ties into Coach reminders).

> _Status_: flow JSON + seed packs still required. Track under `moduleB/` once scripted.

---

## 4. Module C — Adaptive Delivery & Flow (Planned)

Key focus is conversational agility. Proposed exercise flow:

1. **Reset Phrase Library** – Capture three personal reset phrases triggered by stress cues.  
2. **Rapid Summary Sprint** – Timed 90 s exercise summarising messy transcripts; auto-feedback can compare against key points from seed file.  
3. **Clarify & Confirm Drill** – Choose best clarifying questions for branching scenarios (similar to `ScenarioTaggerCard` but with dialogue).  
4. **Shared Goal Surfacing** – Learner writes or selects statements that align agendas; scoreboard tracks empathetic language usage.  
5. **Adaptive Pitch Playback** – Upload/self-record 45 s audio then self-assess with rubric (ties into existing recording components if available).  
6. **Flow Reflection** – What shift helped most? Log signal for AI coach to pick up.

> _Status_: requires new templates for timed summaries and audio capture, or adaptation of existing Q&A cards.

---

## 5. Module D — Integrated Playback & Spacing (Planned)

Capstone module—full rehearsal and spacing plan.

Suggested sequence:

1. **Moment Selection & Success Metrics** – Confirm the highest-stakes moment to rehearse, success definition, and time constraints.  
2. **Storyboard Planner** – Break rehearsal into opening / core argument / close, capturing both verbal and non-verbal focus points.  
3. **Playback Upload + Self-Grade** – Video/audio submission, self-score with rubric (clarity, presence, influence, adaptive responses).  
4. **AI Feedback Review** – Guided reflection on automated feedback (once coach integration is ready).  
5. **Spacing Schedule Builder** – Calendar-style selection for next three rehearsal slots plus accountability partner.  
6. **District Unlock Check** – Reflection rating; triggers venue unlock when ≥ milestone score.

> _Status_: needs higher-fidelity recording UI and calendar integration; can start with text commitments as interim.

---

## 6. Next Steps & Recommendations

1. **Author flows for Modules B–D** – Mirror Module A’s structure by adding `moduleB/`, `moduleC/`, `moduleD/` folders with scenario packs and `*.flow.json` files.  
2. **Template coverage gaps** – Some proposed exercises require new templates (e.g., timed summary, playback upload). Coordinate with the lesson engine team to scope these components.  
3. **Progress telemetry** – Ensure each exercise writes helpful metrics (`last_lever_choice`, `influence_plan_ready`, etc.) so guards can branch intelligently and AI Coach can reference the work.  
4. **QA scripts** – Update `seed_moduleA_sample.py` (or create sibling scripts) once flows are authoring-ready so local/test environments populate consistent content.  
5. **UX polish** – Continue validating the immersive lesson layout across devices; keep transcript controls, focus mode, and guard-triggered inserts accessible in reduced-motion mode.  

With this outline, content and engineering teams have a shared reference for how exercises chain together today (Module A) and what needs to be implemented for the remaining modules. Keep this document updated as new flows or templates land. 


# Guided Script Rollout – Level 1 Modules

**Summary**  
The legacy multi-template lesson runner (cards, carousels, scoring bands) is retired for Level 1. We now run every learning module through a guided-script flow: one prompt displayed at a time, paired with a single answer field. After each submission the UI swaps in the next prompt, creating a lightweight “AI-led script” feel instead of a deck of widgets.

**What changed**

- Removed module-level flow JSONs and seed packs (`myApp/content/moduleA/…`) that stitched template cards together. Backups live under `docs/legacy/moduleA/` for analytics reference.
- Replaced `module_learn.html` with a mobile-first prompt layout: centered stage, micro-header with progress, helper drawer, and a fixed answer bar.
- New backend endpoints (`POST /lesson/start`, `POST /lesson/answer`, `GET /lesson/resume`) manage the scripted session, store transcripts, and trigger module completion logic.
- Added models `LessonSession` and `LessonStepResponse` to persist simple transcripts instead of per-template metrics.
- Legacy endpoints (e.g., `lesson_prime_submit`, `lesson_card_submit`, etc.) now return HTTP 410 and are removed from the router.
- Analytics events continue to fire (`lesson_guided_start`, `lesson_guided_step_submitted`, `lesson_guided_complete`) so completion dashboards remain intact.

**What product should expect**

- Learners see one primary prompt at a time with a single input. No carousels, no stacked cards, no focus toggle buttons.
- Each session stores a compact transcript (field/value pairs) plus the derived summary for coach use.
- Module completion still locks/unlocks venues and awards XP through the existing progress pipeline.

**Next steps**

- Author the remaining module scripts (B–D) in `myApp/content/guided/` using the new step schema.
- Update coach copy or automations that referenced template IDs; they should now read the transcript rows instead.
- Coordinate QA for the `/lesson` endpoints, especially validation and resume flows, before porting additional modules.

Ping @product-team in #launch-room when ready to onboard the remaining modules.


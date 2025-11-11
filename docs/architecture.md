# SpeakProApp Architecture Overview

_Last updated: {{DATE}}_

## 1. Project Snapshot

- **Framework**: Django + Tailwind-based templates  
- **Apps**: `myApp` (core functionality), `myProject` (settings)  
- **Primary user flows**:
  - _Unauthenticated visitors_ → Marketing landing page
  - _Authenticated learners_ → Guided lesson environment, AI coach, amphitheatre simulations

---

## 2. Directory Outline

```
/manage.py
/myProject
    settings.py, urls.py, wsgi.py, asgi.py
/myApp
    __init__.py
    models.py
    views.py
    urls.py
    forms.py
    context_processors.py
    templates/
        landing/
            _hero.html
            _how_it_works.html
            _pricing.html
            _testimonials.html
            _faq.html
            _footer.html
            index.html
        myApp/
            … (authenticated dashboards, lessons, amphitheatre)
    content/
        ui.tokens.json
        guided/
            *.steps.json
```

---

## 3. Django App Responsibilities

| Component | Purpose |
| --- | --- |
| `views.py` | Landing page, auth flows, onboarding, module/district progression, amphitheatre sessions, AI endpoints. |
| `models.py` | User profile, levels/modules/knowledge blocks, quest/milestone tracking, analytics events, amphitheatre records. |
| `forms.py` | Custom user signup (`CustomUserCreationForm`). |
| `urls.py` | Maps routes like `/`, `/login`, `/home`, `/amphitheatre/...`, `/api/...`. |
| `context_processors.py` | Adds UI tokens & feature flags to templates. |
| `content/` | JSON configuration for UI and guided lesson scripts. |

---

## 4. Landing Page Structure

`landing/index.html` includes modular sections:

1. `_hero.html`
2. `_how_it_works.html`
3. `_pricing.html`
4. `_testimonials.html`
5. `_faq.html`
6. `_footer.html`

> `_offer_section.html` (Beta / Legacy cards) was removed. Restore and include if needed.

Each partial uses Tailwind utilities and includes gradients, shadows, and animation helpers inline.

### 4.1 `_hero.html`
- Gradient background with floating icons.
- SVG logo positioned top-left (“Speak ProApp” speech bubble).
- Headline: “From Anxiety to Impact”.
- Subheadline, paragraph, and CTA buttons (“Start Learning”, “Watch Demo”).
- Drop-shadows added for readability.

### 4.2 `_how_it_works.html`
- Title: “The SpeakProApp Method”.
- Subtitle: “A hands-on learning ecosystem…”.
- Four cards (Awareness, Audience, Style, Clarity) with updated copy + italicized quotes.
- Keyframe animations defined at bottom.

### 4.3 `_pricing.html`
- Badge: “Pricing”.
- Headline: “Simple, transparent pricing”.
- Two cards (Free vs Pro) with feature lists and CTAs.
- JSON-LD schema for SEO appended at bottom.

### 4.4 `_testimonials.html`
- Badge: “Testimonials”.
- H1: “From Boardrooms to Your Pocket”.
- H2: “Built on Two Decades of Real-World Coaching and Training”.
- Paragraph set:
  - “Tulia is the visionary behind SpeakProApp.”
  - “For more than 20 years…”
  - “Now, her proven methodology…”
- Three testimonial cards (Maya Chen, Andre Santos, Rina Patel). Company names normalized to “Airbus Defence & Space” (adjust as desired).
- Logos strip removed.

### 4.5 `_faq.html`
- Accordion using `<details>` with custom chevron rotation.
- “Do I need any special equipment?” rendered in neon yellow with drop-shadow.
- CTA “Watch Demo” retained at top of section.

### 4.6 `_footer.html`
- Gradient background with enlarged speech-bubble logo.
- Social icons, navigation columns, legal text.

---

## 5. Authentication & Onboarding

- `login_view`, `signup_view`, `logout_view` – standard auth flows.
- `onboarding` – 7-question intake storing persona, goals, comfort levels, etc. (sets `onboarding_completed`).
- `home` – decides between marketing landing page (anonymous) or dashboard (authenticated). Builds district/module cards, progress stats, quests, analytics events.

---

## 6. Curriculum & Guided Lessons

- **Models**: `Level`, `Module`, `KnowledgeBlock`, `UserProgress`, `ExerciseAttempt`, `DailyQuest`, etc.
- **Guided Flow**:
  - JSON definitions in `content/guided/*.steps.json` loaded via `load_guided_flow`.
  - Endpoints `lesson_start`, `lesson_answer`, `lesson_resume` orchestrate sessions, calling external webhooks (n8n) with fallbacks.
  - `serialize_guided_step`, `_ensure_guided_flow` manage step structure and validation.
- **Progress Tracking**:
  - `UserProgress` updates on module completion.
  - `_unlock_module_and_venues`, `_set_district_full_access`, `_user_has_venue_access` manage gating across districts and venues.

---

## 7. Amphitheatre Simulation

- `AmphitheatreSession`, `AmphitheatreExerciseRecord` store practice sessions/exercises.
- `build_session_plan`, `score_submission`, `build_philosopher_response` craft sessions and generate feedback microcopy.
- Routes: `amphitheatre_hub`, `amphitheatre_session`, `amphitheatre_history`, `amphitheatre_settings`.
- `amphitheatre_submit` saves reflections, updates XP, logs analytics events.
- `amphitheatre_transcribe` integrates with OpenAI Whisper & GPT for transcription and feedback.

---

## 8. AI Coach & Lesson Orchestration

- `ai_chat` renders the coach UI; header includes the speech-bubble logo.
- `ai_chat_send`, `ai_coach_respond` hit n8n webhooks if configured, otherwise return fallback responses.
- `ai_lesson_orchestrate` is a stub orchestrator returning next knowledge block or calling n8n.
- Analytics recorded via `AnalyticsEvent` for each interaction.

---

## 9. Gamification & Analytics

- `AnalyticsEvent` tracks logins, module progress, amphitheatre submissions, AI interactions, etc.
- Gamified components:
  - `DailyQuest` (complete a drill).
  - `MilestoneAttempt` (assessment tracking).
  - `VenueEntry` (ticket-based access).
  - `ExerciseAttempt` (XP/coin rewards).
- XP/Tickets/Coins updated in `submit_exercise`, `complete_venue`, `milestone_submit`.

---

## 10. External Integrations

| Integration | Usage | Configuration |
| --- | --- | --- |
| **n8n webhooks** | Guided lessons (`LESSON_EXERCISE_WEBHOOK_URL`), AI coach (`N8N_COACH_WEBHOOK`), milestone scoring (`N8N_MILESTONE_WEBHOOK`). | Django settings / environment variables. |
| **OpenAI** | Whisper transcription & GPT reflections (`OpenAI(api_key)`). | `OPENAI_API_KEY`. |
| **Requests** | HTTP calls to external services with timeout/fallback handling. | Network configuration & error logging. |

---

## 11. Pending / Removed Assets

- `_offer_section.html` (beta & legacy patron cards) was removed; reintroduce if marketing requires those CTAs.
- Numerous legacy lesson endpoints return `"Legacy lesson endpoint removed."` – keep or re-implement as needed.

---

## 12. Recommendations / Next Steps

1. **Offer Section** – Recreate `_offer_section.html` and include it before the FAQ if you need the beta + legacy offers on the landing page.
2. **Testimonials** – Decide whether to retain original employer names or standardized “Airbus Defence & Space.”
3. **Documentation** – Consider summarizing marketing layout / feature flags in the main README.
4. **Cleanup** – Remove or update legacy API endpoints.
5. **Deploy Config** – Ensure n8n and OpenAI environment variables are set in production.

---

## 13. Reference Snippets

### Include Offer Section (if reintroduced)

```django
{% include 'landing/_pricing.html' %}
{% include 'landing/_offer_section.html' %}
{% include 'landing/_faq.html' %}
```

### Tailwind Utility Patterns

- Gradient background: `bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900`
- Card panel: `bg-white rounded-3xl shadow-xl border border-gray-100`
- CTA button: `inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-3 font-semibold text-white`

---

## 14. Key Models & Data Flows

- `UserProfile` – Onboarding info, persona, streaks, progress metrics.
- `Level`, `Module`, `KnowledgeBlock` – Curriculum structure (Level 1 modules A–D).
- `LessonSession`, `LessonStepResponse`, `ExerciseSubmission` – Guided lesson infrastructure.
- `AmphitheatreSession`, `AmphitheatreExerciseRecord` – Simulation data.
- `DailyQuest`, `MilestoneAttempt`, `VenueEntry`, `ExerciseAttempt` – Gamification & rewards.
- `AnalyticsEvent` – Activity logging.
- `StakesMap`, `TelemetryEvent` – Additional analytics/telemetry (usage-dependent).

---

## 15. Useful Internal Helpers

- `load_guided_flow` / `serialize_guided_step` – JSON-driven lesson flows.
- `_ensure_amphitheatre_session` / `_build_amphitheatre_payload` – Create and hydrate amphitheatre sessions.
- `_call_exercise_webhook` / `_coerce_message_text` – External webhook interactions.
- `_unlock_module_and_venues` – Module completion gating for districts/venues.
- `_append_meta_history` – Persists recent actions in `UserProgress.meta`.

---

## 16. Glossary

- **Guided Flow**: Step-by-step lesson prompts defined via JSON.
- **Amphitheatre**: Simulation environment for high-stakes practice with Philosopher feedback.
- **Daily Quest**: Short gamified tasks (e.g., complete one drill).
- **Legacy Patron**: Proposed marketing offer for lifetime access.
- **Legacy Endpoints**: Older lesson APIs currently returning “Legacy lesson endpoint removed.”

---

_Document crafted via code review and template inspection. Update as the project evolves._


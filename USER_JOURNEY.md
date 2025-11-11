# Tulia User Journey Overview

This document describes the end-to-end experience a user has with Tulia, starting from their first visit to the public landing page and continuing through the full learning loop, milestone assessments, and district progression. It is intended to give product, engineering, design, and customer success stakeholders a detailed reference of the current flow implemented in the application.

---

## 1. Visitor Lands on the Marketing Site

- **Entry point**: Unauthenticated visitors who hit the root URL are routed to the marketing landing page rendered from `landing/index.html` via `myApp.views.home`.
- **Page sections**: The landing page assembles partial templates for hero, how-it-works, pricing, testimonials, FAQ, and footer content. It communicates core value props and prompts visitors to either sign up or log in.
- **Primary calls-to-action**:
  - `Get Started` / `Create Account` → redirects to `/signup/`.
  - `Log In` → redirects to `/login/`.
- **Secondary content**: Static marketing copy, feature highlights, and social proof remain accessible without authentication.

---

## 2. Account Creation & Authentication

### 2.1 Sign Up (`/signup/`)

- **Form**: Uses `CustomUserCreationForm`, collecting username, email, and password.
- **Validation & Creation**:
  - Standard Django validation ensures password requirements.
  - On success, the user is created and automatically logged in.
  - Event `user_signup` is logged via `AnalyticsEvent`, capturing the email and username.
- **Post-success redirect**: New users are sent to `/onboarding/` to complete the required questionnaire.

### 2.2 Log In (`/login/`)

- **Form**: Username + password.
- **Success**: Authenticates via Django `authenticate` and logs `user_login` analytics.
- **Redirect**: Authenticated users are taken to `/home/`. If onboarding is incomplete, they are immediately redirected to `/onboarding/`.

### 2.3 Log Out (`/logout/`)

- Ends the session and returns the visitor to the `/login/` page.

---

## 3. Mandatory Onboarding Flow (`/onboarding/`)

- **Eligibility**: Accessible only to authenticated users who have not yet completed onboarding.
- **Questionnaire**: Captures role, typical audience, main goal, comfort under pressure, time pressure profile, preferred practice time, and target daily practice minutes.
- **Persistence**: Answers populate `UserProfile` fields; `onboarding_completed` is set to `True`.
- **Database touchpoints**: `UserProfile` holds the persona data, XP totals, tickets, A/B variant, and unlock flags, providing the backbone for gating later content.
- **Analytics**: Emits `onboarding_complete`.
- **Completion**: Redirects back to `/home/`, which now renders the authenticated dashboard.

---

## 4. Authenticated Home Dashboard (`/home/`)

- **District-first layout**: Pulls `District` rows ordered by number and builds `district_cards` capturing name, blurb, status (`locked` / `available` / `in_progress` / `complete`), module summaries, and unlock hints.
- **Status logic**:
  - District 1 is previewable by default; additional districts become available once `UserProfile.district_full_access` marks them true.
  - Module availability uses `UserProgress.completed` to decide whether the next module is locked, in progress, or ready.
  - Venues and full-access flags are surfaced when Module A/B/C/D completions fire `module_unlocked_next`, `venue_unlocked`, and `district_full_access_granted` analytics.
- **Secondary widgets**: Daily Quest CTA, Milestone readiness state, AI Coach quick launch, and profile link live in the right rail / below the grid on smaller screens.
- **Analytics**: Still emits `home_view`, now with `event_data.view_mode = "districts"` to track adoption of the new dashboard.
- **Quick navigation**:
  - District overview → `/district/<number>/`
  - Venues list → `/district/<number>/venues/`
  - Learn flow → `/module/<code>/learn/`
  - Exercises → `/module/<code>/exercises/`
  - Milestone → `/milestone/<level_number>/`
  - AI Coach → `/ai-chat/`

---

## 5. Core Lesson Loop (Lesson Runner)

### 5.1 Learn Phase (`/module/<code>/learn/`)

- **Entry**: Accessed after selecting a module from a district card or overview page. Redirected here before exercises if the module hasn’t been started.
- **Surface**:
  - Lesson video player (HTML5 source configurable via `Module.lesson_video_url`).
  - Live transcript pane sourced from `Module.lesson_transcript` (scrollable, mobile tabbed when viewport is narrow).
  - AI Coach primer showing knowledge blocks, persona cues, and CTA to the dedicated coach screen.
- **State changes**:
  - First visit flips `UserProgress.started = True`, records `lesson_start`, and logs `module_learn_view`.
  - Knowledge blocks feed both the transcript context and the AI coach prompt seed.
- **Exits**: “Continue to Exercises” button routes to `/module/<code>/exercises/`. Button remains available even after completion for replay.

### 5.2 Exercise Phase (`/module/<code>/exercises/`)

- **Prerequisites**: Redirects back to the Learn phase if the module has not been started (enforces watch-first flow).
- **Session Initialization**:
  - Retrieves/creates `UserProgress` and `LessonSessionContext`.
  - Loads guided step definitions from `myApp/content/guided/*.steps.json` (prompt copy, input metadata, helper context).
  - Logs `module_exercises_view` every entry.
- **Context Provided to Template**:
  - `lesson_cards`: Ordered stack of exercise cards returned by the engine.
  - `flow_meta`: Flow name, version, and scoring weights.
  - `session_state`: Scenario refs, lever choices, stakes scores, cooldowns.
  - `progress_payload`: Loop index and pass type so the client can stay in sync.
  - `ui_tokens`: Optional UI theming tokens from `content/ui.tokens.json`.

### 5.3 Card Submission Endpoints

The lesson flow comprises multiple stage-specific API endpoints (`POST` JSON):

| Stage | Endpoint | Purpose | Notable Side Effects |
| --- | --- | --- | --- |
| Prime | `/api/lesson/prime/submit/` | Capture intention & focus lever | Sets initial lever choice, advances sequence |
| Teach | `/api/lesson/teach/submit/` | Confirm knowledge block readiness | Hashes block summary for validation |
| Diagnose | `/api/lesson/diagnose/submit/` | Evaluate pressure, visibility, irreversibility, control (PIC) | Updates PIC metrics, load label, and history |
| Control Shift | `/api/lesson/control-shift/submit/` | Commit to a lever and action plan | Locks lever choice and logs history |
| Perform (Text) | `/api/lesson/perform-text/submit/` | Text-based rehearsal | Validates word count and duration |
| Perform (Voice) | `/api/lesson/perform-voice/submit/` | Audio rehearsal submission | Accepts audio reference and duration |
| Review | `/api/lesson/review/submit/` | Reflection and acceptance of AI feedback | Computes PIC delta, triggers toast |
| Transfer | `/api/lesson/transfer/submit/` | Plan next real-world application | Generates transfer toast message |
| Spacing | `/api/lesson/spacing/schedule/` | Schedule booster/return pass | Sets `pass_type` to `return`, stores reminder |

- **Submission Handling**:
  - Each endpoint validates stage order via `_validate_stage` and loop index via `_validate_loop_index`.
  - `ExerciseSubmission` records include payload, scores, duration, and AB variant metadata.
  - `LessonSessionContext` is updated with latest session state for resuming.
  - `TelemetryEvent` captures granular card metrics.
  - `_compute_next_stage` advances the user through the sequence or rotates into a return pass. When the main pass finishes, `_finalize_module_completion` marks `UserProgress.completed`, raises `module_completed`, and unlocks the next module / venue cadence.

### 5.4 Return Passes

- Triggered when users schedule spacing via `lesson_spacing_schedule`.
- Switches progress `pass_type` to `return`, pushing the user into a modified sequence (`RETURN_SEQUENCE`).
- On completion of return stages, the main loop increments and resumes normal progression without re-triggering unlocks.

---

## 6. AI Coach & Support Features

### 6.1 AI Chat (`/ai-chat/`)

- Displays contextual coach interface, pre-populated with `UserProfile` data.
- Logs `ai_chat_view` when accessed.
- `POST /api/ai-chat/send/`:
  - Validates the message, logs `ai_chat_message`.
  - Attempts to call external n8n webhook (`N8N_COACH_WEBHOOK`) if configured.
  - Falls back to scripted encouragement responses on failure.

### 6.2 AI Lesson Orchestration (`POST /api/lesson/orchestrate/`)

- Intended for adaptive sequencing; currently returns mocked block progression if external orchestrator is unavailable.
- Updates `UserProgress.current_knowledge_block`, marks progress completion when appropriate, and logs `ai_lesson_request`.

### 6.3 Data Stores Involved

- **Knowledge Blocks**: Lesson orchestration relies on `KnowledgeBlock` entries tied to modules for titles, summaries, and drill seeds.
- **Exercise Attempts**: Lightweight drills and coach follow-ups create `ExerciseAttempt` rows, preserving score, correctness, and AI feedback references for later review.

---

## 7. Milestone Challenge

- **Access**: Available after completing all Level 1 modules.
- **View**: `GET /milestone/<level_number>/` presents the challenge overview and previous attempts.
- **Analytics**: `milestone_start` event logged upon entry.
- **Submission**: `POST /milestone/<level_number>/submit/` accepts audio URLs and transcripts.
  - Calls out to `N8N_MILESTONE_WEBHOOK` if configured for scoring; otherwise, uses fallback rubric.
  - Stores `MilestoneAttempt` with overall score, detailed rubric, pass/fail status, coaching note.
  - Rewards XP (100 if pass, 25 if fail) and tickets (3 on pass); flips `district_1_unlocked` on the first success.
  - Logs `milestone_complete` with score details.
- **Outcome**: Successful pass unlocks District 1 content and contributes to overall progression narrative.

---

## 8. District Map & Venue Experiences

### 8.1 District Overview (`/district/<number>/`)

- Always previewable; module CTA buttons are disabled if prerequisites are unmet or the district is still locked for full access.
- Renders hero video + transcript side-by-side on desktop (stacked/tabs on mobile) using the new `District.overview_video_url` and `overview_transcript` fields.
- Lists modules in-order with status chips, unlock hints, and buttons to `module/<code>/learn/` and `/exercises/`.
- Logs `district_view` with `event_data.mode = "overview"`; future iterations can add `district_overview_play`/`district_overview_transcript_view` for finer media analytics.

### 8.2 Venues Index (`/district/<number>/venues/`)

- Presents venue cards with lock/available badges. Availability derives from `UserVenueUnlock` rows or `UserProfile.district_full_access`.
- Shows ticket cost, XP/coin rewards, and provides disabled CTA states when locked.
- Logs `district_view` with `mode = "venues"`.

### 8.3 Module → Venue Unlock Cadence

- District 1 mapping:
  - Completing Module A unlocks **Greek Amphitheatre** (presence under friendly visibility).
  - Completing Module B unlocks **Roman Forum** (audience dynamics & influence).
  - Completing Module C unlocks **Medieval Market** (adaptability & conversational flow).
  - Completing Module D grants full access across the district (`district_full_access['1'] = True`) so every venue stays open.
- Unlocks emit `module_unlocked_next`, `venue_unlocked`, and `district_full_access_granted` analytics, enabling product telemetry and celebratory UI toasts.

### 8.4 Venue Detail (`/district/venue/<venue_id>/`)

- Enforces unlock gating (`UserVenueUnlock` or full access) before permitting entry; otherwise, displays requirement copy and redirects to the venues list.
- Validates ticket availability, creates/updates `VenueEntry`, and logs `venue_entered`.
- Renders ordered `VenueTaskSheet`s. Seed data includes single-task sheets with simple JSON payloads per venue.

### 8.5 Completing Venues

- `POST /district/venue/<venue_id>/complete/` stamps completion, awards XP/coins, and saves to `VenueEntry`.
- Emits `venue_completed` analytics and increments `UserProfile.total_xp`/`coins` to keep the economy consistent.

---

## 9. Supplemental Progression Systems

- **Daily Quests**: Encourage consistent practice by rewarding XP and coins for simple tasks (e.g., completing one drill per day).
- **Exercise Attempts** (`POST /api/exercise/submit/`):
  - Used for lightweight drills outside the main lesson runner.
  - Awards XP scaled by streak multiplier and coins based on XP.
  - Logs `exercise_complete`.
- **UserProfile Tracking**:
  - Captures cumulative XP, coins, tickets, streak multipliers, persona summaries, and unlock flags.
  - Serves as the backbone for gating content and personalizing the experience.

- **Economy & XP**: Venue completions, daily quests, and exercises all increment `UserProfile.total_xp`, `coins`, and `tickets`, which in turn unlock districts and fund venue entries.

---

## 10. Analytics Coverage

Throughout the journey, `AnalyticsEvent` entries provide instrumentation for critical milestones:

- `user_signup`, `user_login`, `home_view`, `onboarding_complete`
- `lesson_start`, `module_learn_view`, `module_exercises_view`, `ai_lesson_request`, `lesson_card_*` telemetry
- `district_view` (overview vs venues), `district_overview` media events, `district_full_access_granted`
- `module_unlocked_next`, `module_completed`, `venue_unlocked`
- `ai_chat_view`, `ai_chat_message`, `coach_question`
- `milestone_start`, `milestone_complete`
- `venue_entered`, `venue_completed`
- `exercise_complete`

These events enable tracking onboarding funnel, engagement with lessons, AI interactions, and progression across districts and venues.

---

## 11. End-State Summary

By completing modules, passing milestones, and exploring districts:

- Users evolve from onboarding personas to confident communicators with contextual practice plans.
- Core outcomes include mastery of module content, recorded rehearsals, reflective feedback loops, and real-world transfer plans.
- Progression unlocks deeper content (districts/venues), rewards (XP, coins, tickets), and expanded AI coaching support.

This journey ensures every user has a guided, data-informed path from their first impression on the landing page to ongoing, personalized mastery of high-stakes communication scenarios.


---

## 12. Data & Content Provisioning

- **Relational Backbone**:
  - `UserProfile` extends Django `User` with persona, XP, streak, currency, and unlock flags.
  - `Level` → `Module` → `KnowledgeBlock` establishes the curriculum hierarchy feeding lessons and AI orchestration.
  - `Lesson`, `UserProgress`, `LessonSessionContext`, and `ExerciseSubmission` capture lesson-loop state, ensuring resumable experiences and fine-grained analytics.
  - `District` → `Venue` → `VenueTaskSheet` define the post-milestone exploration layer, while `VenueEntry` logs user participation.
- **Seed Scripts & Fixtures**:
  - `/Users/julia/Downloads/Tulia_v2/seed_data.py` seeds core Level 1 structure (levels, modules, sample knowledge blocks, districts, venues) and should be run after migrations to bootstrap a fresh environment.
  - `/Users/julia/Downloads/Tulia_v2/seed_moduleA_sample.py` focuses on Module A content, inserting scenario seeds, lesson flows, and example tasks suitable for demos.
  - Lesson engine seed packs live in `myApp/content/moduleA/*.json`; these files drive the card stack generated in the lesson runner and can be edited manually for rapid iteration.
- **Manual Content Updates**:
  - Admins can create or edit `KnowledgeBlock`, `Lesson`, and `Venue` records through Django admin or custom management commands (`myApp/management/commands/add_venue_content.py`, `seed_data.py`).
  - JSON seed packs (`actions_control_shift.json`, `lever_cards.json`, etc.) can be updated directly to tweak card copy, options, and scoring without touching Python code.
  - For quick experiments, developers can insert new `ExerciseAttempt` or `ExerciseSubmission` rows via Django shell to simulate user runs and validate analytics dashboards.
- **Lifecycle Considerations**:
  - Always run migrations before seeding to ensure the schema matches expectations.
  - Re-seeding in a non-empty database may create duplicates; prefer management commands that `get_or_create` records, mirroring the logic in the provided scripts.
  - Large content updates (e.g., new modules) should include corresponding seed JSON, database entries, and adjustments to the lesson engine flow configuration to keep UI, AI coaching, and analytics aligned.

---

## 13. Key Model Definitions (Reference)

```7:52:myApp/models.py
class UserProfile(models.Model):
    """Extended user profile with persona and progress data"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # ...
```

```53:110:myApp/models.py
class Level(models.Model):
    """Learning levels (currently only Level 1)"""
    # ...
class Module(models.Model):
    """Modules within a level (A, B, C, D for Level 1)"""
    # ...
class Lesson(models.Model):
    """Lesson metadata (ultra-thin, AI orchestrates content)"""
    # ...
```

```112:220:myApp/models.py
class ExerciseAttempt(models.Model):
    """Legacy exercise attempts"""
    # ...
class MilestoneAttempt(models.Model):
    """Milestone assessment attempts"""
    # ...
class District(models.Model):
    """Districts (currently only District-1)"""
    # ...
class Venue(models.Model):
    """Venues within districts"""
    # ...
class VenueTaskSheet(models.Model):
    """Task sheets for venues (curated micro-exercises)"""
    # ...
class VenueEntry(models.Model):
    """User entries into venues"""
    # ...
```

```223:408:myApp/models.py
class DailyQuest(models.Model):
    """Daily quests for user engagement"""
    # ...
class UserProgress(models.Model):
    """Track user progress through modules and lessons"""
    # ...
class ExerciseSubmission(models.Model):
    """Stage submission records for lesson runner loops"""
    # ...
class AnalyticsEvent(models.Model):
    """Analytics event tracking"""
    # ...
class LessonSessionContext(models.Model):
    """Session context for module-specific lesson runs."""
    # ...
class StakesMap(models.Model):
    """Persistent stakes map artifact reused in later modules."""
    # ...
class TelemetryEvent(models.Model):
    """Fine-grained telemetry for learning analytics dashboards."""
    # ...
```


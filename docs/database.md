# SpeakProApp Database & Persistence Guide

_Last updated: {{DATE}}_

## 1. Stack & Connection Overview

- **Engine**: PostgreSQL (hosted; Railway connection string provided as default).
- **ORM**: Django ORM with `dj_database_url` for DSN parsing and SSL configuration.
- **Driver**: `psycopg2-binary` (pulled in via Django requirements).
- **Connection pooling**: Django persistent connections enabled via `conn_max_age=600` seconds.
- **Deployment**: Expects `DATABASE_URL` environment variable; falls back to the production Railway DSN for convenience.

```82:92:myProject/settings.py
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:FJeoqFpWuvzgFjFWmmYIgulciueykKUk@hopper.proxy.rlwy.net:31553/railway',
)

DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=DATABASE_URL.startswith(('postgres://', 'postgresql://')),
    )
}
```

### 1.1 Environment Expectations
- `.env` is loaded at startup; set `DATABASE_URL` there for local development.
- When running locally without overrides, the project will attempt to use the Railway DSN above—override it to avoid writing to production.
- SSL is automatically required when the URL uses the `postgres://`/`postgresql://` scheme.

### 1.2 Local Development Checklist
1. Export or set a safe `DATABASE_URL`, e.g. `postgresql://postgres:postgres@localhost:5432/speakpro`.
2. Run `python manage.py migrate` to prepare schema.
3. Optionally load seed data via `python seed_data.py --list` then `python seed_data.py <target>`.
4. Use `python manage.py createsuperuser` to bootstrap admin access.

---

## 2. Data Model Landscape

All persistent data lives in `myApp.models`. The models are grouped below by domain, with key relations and notable fields. Fields of type `JSONField` are stored as PostgreSQL `jsonb` columns, enabling flexible structures and partial indexing if needed.

### 2.1 Accounts & Persona

| Model | Purpose | Key Fields | Relationships |
| --- | --- | --- | --- |
| `User` (Django auth) | Core authentication identity. | `username`, `email`, `password`. | One-to-one with `UserProfile`. |
| `UserProfile` | Extends `User` with persona, onboarding, economy, and access flags. | Persona fields (`role`, `main_goal`, etc.), `ab_variant`, `district_full_access` (`JSONField`), currency balances (`coins`, `tickets`). | `user = OneToOneField(User)`.

```9:47:myApp/models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=200, blank=True)
    main_goal = models.CharField(max_length=200, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    district_full_access = models.JSONField(default=dict, blank=True)
    coins = models.IntegerField(default=0)
    tickets = models.IntegerField(default=0)
    ...
```

### 2.2 Curriculum Structure

| Model | Purpose | Highlights |
| --- | --- | --- |
| `Level` | Represents a learning level (e.g. Level 1). | `number` unique, `milestone_threshold` for pass score. |
| `Module` | Logical module within a level (A/B/C/D). | `lesson_video_url`, `xp_reward`, ordered by level & `order`. |
| `KnowledgeBlock` | RAG-friendly knowledge chunks. | `summary`, `tags`, `exercise_seeds`, `citations` (JSON). |
| `Lesson` | Thin metadata wrapper for module lessons. | `order`, `xp_reward`; tied to `Module`. |

### 2.3 Progress & Assessment

| Model | Purpose | Highlights |
| --- | --- | --- |
| `ExerciseAttempt` | Legacy per-exercise attempt log. | Stores `score`, `ai_feedback`, `user_response` (`JSON`). |
| `MilestoneAttempt` | Captures milestone submissions. | `audio_url`, `transcript`, `rubric_scores` (`JSON`), `pass_bool`. |
| `DailyQuest` | Tracks daily quest completion. | Unique per user+date+quest type; rewards XP/coins. |
| `UserProgress` | Current progress through modules/lessons. | Many JSON attributes for loops, checkpoints, `current_knowledge_block`; indexed for query speed. |
| `ExerciseSubmission` | Records granular lesson-run submissions. | `payload`, `scores`, `duration_ms`; indexes on user/module/stage. |

### 2.4 Districts, Venues & Economy

| Model | Purpose | Notes |
| --- | --- | --- |
| `District` | Top-level world map nodes. | Contains overview media metadata. |
| `Venue` | Practice venue within a district. | `ticket_cost`, `xp_reward`, `coin_reward`. |
| `VenueTaskSheet` | Predefined exercise bundles per venue. | Ordered list of exercises (JSON). |
| `VenueEntry` | User's visit/progress inside a venue. | Tracks tickets spent, rewards, timestamps. |
| `UserVenueUnlock` | Unlock state for venues. | `unique_together(user, venue)` ensures no duplicates. |

### 2.5 Guided Sessions & Artifacts

| Model | Purpose |
| --- | --- |
| `LessonSessionContext` | Stores state for module lessons (cooldowns, scenario refs). |
| `LessonSession` | UUID keyed session for guided scripts; tracks state machine, steps. |
| `LessonStepResponse` | Transcript rows per step (`value` JSON). |
| `StakesMap` | Persistent high-stakes scenario mapping per user/module. |

### 2.6 Amphitheatre Simulation

| Model | Purpose |
| --- | --- |
| `AmphitheatreSession` | Practice session container (visit number, plan, points). |
| `AmphitheatreExerciseRecord` | Per-exercise capture inside amphitheatre session; stores audio references, markers, reflections. |

### 2.7 Analytics & Telemetry

| Model | Purpose | Usage |
| --- | --- | --- |
| `AnalyticsEvent` | General product analytics (logins, milestones, chatbot interactions). | Created throughout views; `event_data` is JSON. |
| `TelemetryEvent` | Higher-volume event stream for dashboards. | Indexed by `module_code` and `name`. |

---

## 3. Data Flow by User Journey

### 3.1 Signup & Onboarding
1. **Signup** (`signup_view`): creates `User`, logs `user_signup` `AnalyticsEvent` with basic metadata.
2. **Onboarding** (`onboarding` view): populates persona fields on `UserProfile` (role, audience, goals, comfort levels) and sets `onboarding_completed=True`.
3. **Home dashboard** (`home`): ensures `UserProfile` exists, assigns A/B variant, loads districts/modules from relational tables, and builds context using `UserProgress`, `VenueEntry`, `MilestoneAttempt` queries.

### 3.2 Curriculum Progress
- **Lesson runs**: `lesson_start`, `lesson_answer`, and related endpoints read/write `LessonSession`, `LessonStepResponse`, and `ExerciseSubmission`. JSON payloads let the AI orchestrator persist flexible step data without schema migrations.
- **Module completion**: `_module_status_for_user` inspects `UserProgress` and `ExerciseSubmission` to decide status, updating XP/coins on success.
- **Milestones**: `milestone_submit` records `MilestoneAttempt`, stores transcripts/audio URL, and adjusts XP/coins.

### 3.3 District & Venue Unlocks
- `_unlock_module_and_venues` grants venue access via `UserVenueUnlock` entries, updates `UserProfile.district_full_access` for full unlocks, and increments tickets/coins.
- `VenueEntry` records track when a user starts/finishes a venue activity, storing rewards and timestamps for analytics.

### 3.4 Amphitheatre Sessions
- `amphitheatre_hub` creates/updates `AmphitheatreSession` rows.
- `amphitheatre_submit` appends `AmphitheatreExerciseRecord` items with audio references, reflections, and scoring metadata; XP/coin/ticket adjustments persist on `UserProfile`.
- `amphitheatre_history` reads back historical sessions for timeline rendering.

### 3.5 Analytics & Chatbot
- Every major action logs an `AnalyticsEvent` (`event_type`, `event_data`).
- The landing chatbot (`landing_chat_send`) captures each message (length, UA) as an `AnalyticsEvent` and relies on OpenAI for responses; no chat transcript is stored in Postgres beyond analytics breadcrumbs.

---

## 4. Seeding & Fixtures

- `seed_data.py` is a dispatcher that boots Django, then loads registered seed modules (currently `seed_moduleA_sample.main`).
- Seed scripts should live alongside `seed_data.py` and expose a `main()` entry point.
- Use `python seed_data.py module_a_sample` after migrations to populate Level 1 curriculum, districts, venues, and a sample superuser.

---

## 5. Maintenance & Best Practices

1. **Avoid Production Writes from Local**: Always override `DATABASE_URL` locally to prevent accidental writes to the Railway instance.
2. **Migration Discipline**: Model changes require `python manage.py makemigrations` followed by review of generated SQL.
3. **JSONField Usage**: Many models rely on JSON for flexible attributes. When querying large JSON blobs, prefer filtering on indexed columns (`user`, `module`, etc.) or add `GinIndex` if structured querying becomes necessary.
4. **Long-lived Connections**: With `conn_max_age=600`, Django keeps connections open; ensure your Postgres instance allows matching idle timeouts.
5. **Backups**: For Railway, enable automatic backups or schedule `pg_dump` jobs. Document credentials rotation alongside `DATABASE_URL` updates.
6. **Observability**: `AnalyticsEvent` is the lightweight audit trail; if you need immutable audit logs, consider a dedicated append-only table or streaming events to external analytics.
7. **Testing**: Use SQLite only if you understand JSON compat differences; the project assumes PostgreSQL semantics for JSONB and UUID handling.

---

## 6. Quick Reference

| Task | Command |
| --- | --- |
| Run migrations | `python manage.py migrate` |
| Create migration | `python manage.py makemigrations myApp` |
| Open Django shell | `python manage.py shell` |
| Dump data | `python manage.py dumpdata myApp > backup.json` |
| Load seed | `python seed_data.py module_a_sample` |

---

**Next Steps**
- Keep this document updated when models or environments change.
- Consider diagramming ER relationships for newcomers (e.g. with `django-extensions graph_models`).

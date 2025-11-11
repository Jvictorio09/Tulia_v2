# Lesson Runner Overview

Single-screen guided sessions have replaced the legacy multi-template deck. Every module now advances through one prompt at a time with a lightweight AI copilot. This document describes the current architecture, contracts, and UX guidelines for the Level 1 guided lesson experience.

---

## 1. Purpose & Experience Pillars

- **Focus first** – the learner sees one prompt, one input, one clear next action.
- **Calm momentum** – soft transitions, micro-headers, and progress breadcrumbs reinforce steady progress rather than high-pressure gamification.
- **AI-assisted** – each submission is routed through the external webhook to fetch the next prompt copy or micro-coaching.

---

## 2. System Map

- **Template**: `myApp/templates/myApp/module_guided.html` renders the prompt stage, helper drawer, answer bar, and toast surface.
- **Frontend runtime**: inline ES module orchestrates the state machine, validation, helper content, and safe-area layout.
- **Endpoints**:
  - `POST /lesson/start` → bootstrap a session.
  - `POST /lesson/answer` → persist the answer, relay it to the webhook, and return the next prompt.
  - `GET /lesson/resume` → reload a session after a refresh.
- **Guided content**: `myApp/content/guided/<module>.steps.json` lists ordered steps with metadata (title, body, helper, validation, icons).
- **Webhook**: `https://katalyst-crm.fly.dev/webhook/afe1a38e-ae3d-4d6c-b23a-14ac169aed7a` is the single integration point for copy hand-offs.

---

## 3. Prompt Flow & State Machine

Frontend and backend share the same lifecycle vocabulary:

1. `idle` – no session loaded.
2. `asking` – prompt visible and ready for input.
3. `waiting` – submission in-flight while the webhook processes.
4. `transitioning` – UI fades between prompts.
5. `completed` – transcript saved; recap card replaces the prompt.

The backend persists `waiting`, `transitioning`, `asking`, and `completed` so that resume calls mirror the real state.

---

## 4. UI Regions

- **Prompt Stage**: centered card with micro-header (step count, progress bar), headline/body copy, optional icon, and example list.
- **Helper Drawer**: lightbulb affordance that slides in static context tips (`helper.title`, `helper.bullets`).
- **Footer Answer Bar**: safe-area padded form with a single input, primary action icon (Font Awesome), inline validation with `fa-circle-info`, and spinner treatment during waits.
- **Toast Rail**: top-center stack for success/error notifications (webhook errors always surface here).

Transitions use subtle fade/translate CSS; “focus mode” overlays were removed.

---

## 5. API Contracts

### POST `/lesson/start`

**Request**
```json
{ "module": "A" }
```

**Response**
```json
{
  "session_id": "b5d3e3ae-b18c-4d96-95bc-770c2ac7f8ab",
  "module": "A",
  "state": "asking",
  "total_steps": 8,
  "step": {
    "step_id": "moment_snapshot",
    "prompt_title": "...",
    "prompt_body": "...",
    "input_type": "textarea",
    "validation": { "required": true, "min_length": 35 },
    "helper": { "title": "...", "bullets": ["...", "..."] },
    "progress": { "current": 1, "total": 8 }
  }
}
```

### POST `/lesson/answer`

**Request**
```json
{
  "session_id": "b5d3e3ae-b18c-4d96-95bc-770c2ac7f8ab",
  "step_id": "moment_snapshot",
  "field_name": "moment_snapshot",
  "value": "Presenting Q4 results…"
}
```

**Webhook payload (derived)**  
`{ "message": "Presenting Q4 results…", "timestamp": "...", "userId": "42", "sessionId": "b5d3e3ae-..." }`

**Response (happy path)**
```json
{
  "session_id": "b5d3e3ae-b18c-4d96-95bc-770c2ac7f8ab",
  "state": "asking",
  "next_step": {
    "step_id": "stakes_intensity",
    "prompt_title": "...",
    "prompt_body": "How intense does it feel right now?",
    "input_type": "select",
    "...": "..."
  }
}
```

**Response (final step)**
```json
{
  "completed": true,
  "state": "completed",
  "summary": {
    "steps_completed": 8,
    "fields": [
      { "step_id": "moment_snapshot", "field_name": "moment_snapshot", "value": "...", "recorded_at": "..." }
    ]
  }
}
```

Errors return `{ "ok": false, "error": { "code": "...", "message": "..." } }`. `code = webhook_failed` always pairs with a 502 and triggers the top toast.

### GET `/lesson/resume?session_id=<uuid>`

- Completed sessions return summary + `state = completed`.
- Active sessions return the current step, total count, and persisted state.

---

## 6. Step Definition Schema

Every entry in `<module>.steps.json` supports:

| Field | Purpose |
| --- | --- |
| `step_id` | Stable identifier used in transcripts. |
| `order` | Render ordering. |
| `field_name` | Storage key for transcripts. |
| `input_type` | `text`, `textarea`, `select`, `rating`, `confirm`, `complete`, etc. |
| `prompt_title` / `prompt_body` | Copy shown in the stage. |
| `examples` | Optional bulleted examples. |
| `validation` | Object containing `required`, `min_length`, `min_value`, etc. |
| `options` | Array for select inputs (`value`, `label`). |
| `helper` | Optional { `title`, `bullets` }. |
| `fa_icon` | Icon hint rendered beside the heading. |
| `progress` | `{ "current": n, "total": m }` for the micro-header bar. |

We only keep legacy seed packs that power helper bullets or examples; scoring seeds and guard rules were retired with the multi-template engine.

---

## 7. Data Capture & Storage

- `LessonSession` retains state (`asking`, `waiting`, `transitioning`, `completed`), current step, total steps, flow version, and a `context` dict.
- `LessonStepResponse` rows hold the minimal transcript (`session_id`, `step_id`, `field_name`, JSON value, timestamp).
- `session.context["answers"]` caches last known values; `webhook_trace` keeps the five most recent webhook request/response pairs for debugging.
- Analytics events:
  - `lesson_guided_start`
  - `lesson_guided_step_submitted`
  - `lesson_guided_complete`

---

## 8. Accessibility, Motion, & Mobile

- `aria-live="polite"` on the prompt container to announce new copy for screen readers.
- Keyboard-friendly focus order: helper toggle → prompt → input → submit.
- Inputs default to 48px tap targets; footer respects `env(safe-area-inset-bottom)` to avoid keyboard overlap.
- Transitions: 180–220 ms fade/translate, no motion on validation errors.

---

## 9. QA Checklist

- Start, answer, resume endpoints respond with the expected state values.
- Frontend state machine visits `idle → asking → waiting → transitioning → asking` for each step; `completed` only after the final response.
- Webhook failures show the top toast and keep the learner on the same prompt.
- Transcript rows persist with accurate timestamps and field names.
- Helper drawer closes and reopens without losing tip content.
- Mobile keyboards do not cover the answer bar; safe-area padding verified on iOS and Android.
- Validation copy uses the Font Awesome info icon and clears once the value is fixed.

---

## 10. Future Enhancements

- Allow the webhook to return structured helper additions (`helper_append`) as well as prompt copy.
- Expand module registry (`GUIDED_FLOW_FILES`) once Module B–D scripts are authored.
- Persist webhook latency metrics for observability.

---

_Last updated: 2025-11-11_


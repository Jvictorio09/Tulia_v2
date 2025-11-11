# Landing Chatbot Architecture

## Overview
- **Purpose**: Provide a concierge-style AI assistant on the unauthenticated landing page that answers questions about SpeakProApp’s beta, pricing, and communication offering.
- **Entry point**: Rendered for all visitors via `templates/landing/index.html` when `myApp.views.home` detects an anonymous request.
- **Key components**:
  - Floating launcher + panel UI (Tailwind + inline JS) in `templates/landing/index.html`.
  - Chat backend endpoint `landing_chat_send` in `myApp/views.py`.
  - URL mapping `path('landing-chat/send/', ...)` in `myApp/urls.py`.
  - OpenAI client helper `_get_openai_client()` sharing settings-driven credentials.

## Front-end Flow
| Step | File/Selector | Notes |
| --- | --- | --- |
| 1 | `#landing-chatbot` container | Fixed-position floating button, "Need help" callout, hidden panel. |
| 2 | `data-chatbot-toggle` button | Click opens panel by toggling `hidden` class and applying animation classes. |
| 3 | `data-chatbot-panel` div | Holds header, welcome copy, quick suggestion buttons, message list, and input form. |
| 4 | Scripts (wrapped in `{% block extra_scripts %}`) | Located at bottom of `landing/index.html`; executed because `base.html` exposes block. |
| 5 | Fetch request | `fetch(endpoint, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': ... } })` ensures cookies/CSRF included. |
| 6 | Message rendering | User messages styled gradient, bot replies styled indigo cards; pending reply shows bouncing dots. |

### Suggestions
- Quick-actions (e.g., "Beta access perks") prefill input and open the panel.
- ESC key closes panel; callout reappears after delay.

### Analytics Hook
- Each POST logs `landing_chat_message` in `AnalyticsEvent` (length + user agent) for landing usage tracking.

## Backend Flow
```
landing/index.html  ──fetch──▶  /landing-chat/send/
                           │
                     landing_chat_send (views.py)
                           │
               ┌───────────┴────────────┐
               │ _get_openai_client()   │
               │  • pulls settings.OPENAI_API_KEY
               │  • returns OpenAI client or None
               └───────────┬────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                     │
   OpenAI Responses API               Graceful fallback
         │                                     │
 JSON reply sent back             Varied copy using question context
```

### `landing_chat_send`
- Decorated with `@csrf_protect` and `@require_http_methods(["POST"])`.
- Parses JSON body, validates `message`.
- Logs analytics.
- Calls `_get_openai_client`:
  - Reads `OPENAI_API_KEY` from Django settings (environment fallback).
  - Returns configured `OpenAI` client if present.
- On success: sends prompt to `gpt-4.1-mini` via `client.responses.create` with a system persona describing SpeakProApp concierge duties.
- On errors (no key/network): builds varied fallback responses referencing the question so visitors still receive guidance.

### CSRF Handling
- Landing view `home` is decorated with `@ensure_csrf_cookie` ensuring anonymous visitors receive a CSRF token as soon as the page renders.
- Front-end fetch includes `credentials: 'same-origin'` and the cookie-derived token (Double Submit pattern).

## Files & Dependencies
| File | Responsibility |
| --- | --- |
| `templates/landing/index.html` | Complete chatbot markup, Tailwind classes, animations, JS logic. |
| `templates/myApp/base.html` | Provides `{% block extra_head %}` and `{% block extra_scripts %}` so landing page styles/scripts execute. |
| `myApp/urls.py` | `path('landing-chat/send/', views.landing_chat_send, name='landing_chat_send')`. |
| `myApp/views.py` | `home` (CSRF cookie), `_get_openai_client`, `landing_chat_send`. |
| `myApp/models.py` | `AnalyticsEvent` used for usage logging. |

## Extending
- **Copy updates**: Modify concierge system prompt or quick actions inside `landing_chat_send` or `landing/index.html`.
- **Conversation history**: Capture prior messages client-side and include them in the JSON payload before calling the endpoint.
- **Authentication awareness**: Extend `landing_chat_send` to check `request.user.is_authenticated` and tailor replies.
- **Analytics**: Additional context (e.g., page section) can be appended to `event_data`.

## Troubleshooting
- **Repeating fallback text**: Indicates CSRF failure or missing API key; inspect network tab (403 or 503). Availability of `OPENAI_API_KEY` is mandatory for live responses.
- **CSS/JS not executing**: Ensure extra blocks exist in `base.html` (already added) and that `landing/index.html` wraps assets inside those blocks.
- **CORS issues**: Both frontend and API share the same origin; credentials set to `same-origin`. Any domain change requires updated CSRF settings.

from functools import lru_cache
from copy import deepcopy
import base64
import io
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomUserCreationForm
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
import json
import random
import requests
from datetime import date, datetime, timedelta

from .models import (
    UserProfile, Level, Module, KnowledgeBlock, Lesson,
    ExerciseAttempt, MilestoneAttempt, District, Venue,
    VenueTaskSheet, VenueEntry, DailyQuest, UserProgress,
    AnalyticsEvent, ExerciseSubmission, LessonSessionContext,
    StakesMap, TelemetryEvent, UserVenueUnlock, LessonSession,
    LessonStepResponse, AmphitheatreSession, AmphitheatreExerciseRecord
)
from .amphitheatre import (
    build_session_plan,
    build_philosopher_response,
    score_submission,
    EXERCISE_TITLES,
    get_depth_tier,
)


@lru_cache(maxsize=1)
def get_ui_tokens():
    tokens_path = Path(settings.BASE_DIR) / "myApp" / "content" / "ui.tokens.json"
    if not tokens_path.exists():
        return {}
    with tokens_path.open("r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError:
            return {}
    return {
        "version": data.get("version"),
        "values": data.get("items") or data.get("tokens") or {},
    }


GUIDED_FLOW_FILES = {
    "A": "moduleA.steps.json",
    "B": "moduleB.steps.json",
    "C": "moduleC.steps.json",
    "D": "moduleD.steps.json",
}

DEFAULT_MODULE_WEBHOOKS = {
    "A": "https://katalyst-crm.fly.dev/webhook/afe1a38e-ae3d-4d6c-b23a-14ac169aed7a",
    "B": "https://speak-pro-app.fly.dev/webhook/afe1a38e-ae3d-4d6c-b23a-14ac169aed7a",
    "C": "https://speak-pro-app.fly.dev/webhook/d4908fce-e029-4c09-8267-027516b0e6cf",
    "D": "https://speak-pro-app.fly.dev/webhook/b3bf6992-16b8-4512-8982-7573211fbd63",
}

VENUE_SESSION_WEBHOOK_URL = getattr(
    settings,
    "VENUE_SESSION_WEBHOOK_URL",
    os.getenv(
        "VENUE_SESSION_WEBHOOK_URL",
        "https://speak-pro-app.fly.dev/webhook/d4908fce-e029-4c09-8267-027516b0e6cf",
    ),
)

SYSTEM_PROMPT = (
    "You are SpeakProApp's landing-page concierge. Be concise, friendly, and specific. "
    "Answer questions about: Beta access, Legacy Patron lifetime (€47), pricing, simulations, and how we help with high-stakes communication. "
    "If the user asks for account-specific or medical/legal advice, steer them to signup. "
    "Style: 1–3 short paragraphs max. Use bullet points when listing perks."
)


def _get_module_webhook(module_code: str) -> str:
    module_code = (module_code or "").upper()
    env_key = f"LESSON_EXERCISE_WEBHOOK_URL_{module_code}"
    override = getattr(settings, env_key, None) or os.getenv(env_key)
    if override:
        return override
    if module_code == "A":
        return getattr(
            settings,
            "LESSON_EXERCISE_WEBHOOK_URL",
            DEFAULT_MODULE_WEBHOOKS["A"],
        )
    return DEFAULT_MODULE_WEBHOOKS.get(module_code, DEFAULT_MODULE_WEBHOOKS["A"])


class WebhookError(Exception):
    """Raised when the external exercise webhook fails."""


def _coerce_message_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value)
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return str(value)


def _call_exercise_webhook(session, user, message: str) -> Tuple[Optional[str], Dict[str, Any], Dict[str, Any]]:
    module_code = ""
    if hasattr(session, "module") and session.module:
        module_code = session.module.code
    webhook_url = _get_module_webhook(module_code)

    if not webhook_url:
        return None, {}, {}

    request_payload = {
        "message": message,
        "timestamp": timezone.now().isoformat(),
        "userId": str(user.id),
        "sessionId": str(session.id),
    }

    try:
        response = requests.post(webhook_url, json=request_payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WebhookError(str(exc)) from exc

    try:
        response_payload = response.json()
    except ValueError as exc:
        raise WebhookError("Exercise webhook returned invalid JSON.") from exc

    output = response_payload.get("module1_test_response", {}).get("output")
    if not isinstance(output, str):
        output = None

    return output, response_payload, request_payload


@lru_cache(maxsize=8)
def load_guided_flow(module_code: str) -> dict:
    module_code = module_code.upper()
    flow_file = GUIDED_FLOW_FILES.get(module_code)
    if not flow_file:
        return {}
    flow_path = Path(settings.BASE_DIR) / "myApp" / "content" / "guided" / flow_file
    if not flow_path.exists():
        return {}
    with flow_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    steps = data.get("steps", [])
    steps = sorted(steps, key=lambda s: s.get("order", 0))
    index = {step["step_id"]: step for step in steps}
    return {
        "module_code": module_code,
        "version": data.get("version", "v1"),
        "steps": steps,
        "index": index,
    }


def serialize_guided_step(step: dict) -> dict:
    allowed_fields = {
        "step_id",
        "field_name",
        "input_type",
        "prompt_title",
        "prompt_body",
        "examples",
        "validation",
        "fa_icon",
        "helper",
        "progress",
        "options",
        "media",
    }
    return {key: value for key, value in step.items() if key in allowed_fields and value is not None}


def get_stage_sequence(progress):
    if progress.pass_type == 'return':
        return RETURN_SEQUENCE
    return MAIN_SEQUENCE


def build_progress_payload(progress):
    return {
        "loop_index": progress.loop_index,
        "pass_type": progress.pass_type,
        "stage_key": progress.stage_key,
        "sequence_version": progress.sequence_version,
        "lever_choice": progress.lever_choice,
        "pic_control": progress.pic_control,
        "return_at": progress.return_at.isoformat() if progress.return_at else None,
    }


def _json_error(message, status=400, code='bad_request'):
    return JsonResponse({
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        }
    }, status=status)


def _parse_request_json(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None, _json_error("Invalid JSON payload", status=400, code='invalid_json')
    return payload, None


DISTRICT_DEFAULT_UNLOCK = 1
DISTRICT_MODULE_VENUE_MAP = {
    1: {
        "A": "Greek Amphitheatre",
        "B": "Roman Forum",
        "C": "Medieval Market",
        "D": None,  # Module D grants full district access
    },
}


AMPHITHEATRE_HINTS = {
    "stakes_echoes": {
        "label": "Today leans clarity",
        "subtext": "We'll map the stakes with the Philosopher beside you.",
    },
    "voice_to_marble": {
        "label": "Today leans presence",
        "subtext": "A gentle voice warm-up sets the tone.",
    },
    "inner_listener": {
        "label": "Today leans awareness",
        "subtext": "Listen inward first; the room will notice.",
    },
    "control_in_motion": {
        "label": "Today leans agency",
        "subtext": "We'll choose the lever that widens control.",
    },
    "shorter_not_smaller": {
        "label": "Today leans precision",
        "subtext": "Compression without losing heart.",
    },
    "echo_of_truth": {
        "label": "Today leans congruence",
        "subtext": "Speak the quiet truth as an invitation.",
    },
}


def _amphitheatre_last_prompt_lookup(user):
    latest_completed = (
        AmphitheatreSession.objects.filter(user=user, status="completed")
        .order_by("-completed_at", "-created_at")
        .first()
    )
    lookup = {}
    if not latest_completed:
        return lookup
    for record in latest_completed.exercise_records.all():
        if record.prompt_id:
            lookup[record.exercise_id] = record.prompt_id
    return lookup


def _ensure_amphitheatre_session(user):
    existing = (
        AmphitheatreSession.objects.filter(user=user, status__in=["active", "draft"])
        .order_by("-created_at")
        .first()
    )
    if existing:
        return existing, False

    visit_number = AmphitheatreSession.objects.filter(user=user).count() + 1
    last_prompts = _amphitheatre_last_prompt_lookup(user)
    plan = build_session_plan(visit_number=visit_number, last_prompt_lookup=last_prompts)

    session = AmphitheatreSession.objects.create(
        user=user,
        visit_number=visit_number,
        depth_tier=get_depth_tier(visit_number),
        status="active",
        current_index=0,
        exercises_plan=plan,
        metadata={
            "version": "v1",
            "last_prompt_lookup": last_prompts,
        },
    )

    for slot in plan:
        AmphitheatreExerciseRecord.objects.create(
            session=session,
            exercise_id=slot["id"],
            prompt_id=slot["prompt"]["id"],
            sequence_index=slot["sequence_index"],
            microcopy={
                "title": slot["title"],
                "prompt": slot["prompt"],
            },
        )

    AnalyticsEvent.objects.create(
        user=user,
        event_type="amphitheatre_session_started",
        event_data={
            "visit_number": visit_number,
            "depth_tier": session.depth_tier,
            "exercise_ids": [slot["id"] for slot in plan],
        },
    )

    return session, True


def _build_amphitheatre_payload(session):
    plan = deepcopy(session.exercises_plan or [])
    records = {record.exercise_id: record for record in session.exercise_records.all()}

    exercises = []
    for slot in plan:
        record = records.get(slot["id"])
        slot_payload = deepcopy(slot)
        if record:
            slot_payload["state"] = record.state
            slot_payload["selections"] = record.selections or {}
            slot_payload["reflection_text"] = record.reflection_text or ""
            slot_payload["markers"] = record.markers or {}
            slot_payload["philosopher_response"] = record.philosopher_response or ""
            slot_payload["completed_at"] = (
                record.completed_at.isoformat() if record.completed_at else None
            )
            slot_payload["has_audio"] = record.has_audio
            slot_payload["microcopy"] = record.microcopy or {}
        else:
            slot_payload["state"] = "idle"
            slot_payload["selections"] = {}
            slot_payload["markers"] = {}
            slot_payload["reflection_text"] = ""
            slot_payload["philosopher_response"] = ""
            slot_payload["has_audio"] = False
            slot_payload["microcopy"] = {}
        exercises.append(slot_payload)

    return {
        "session_id": str(session.session_id),
        "status": session.status,
        "current_index": session.current_index,
        "visit_number": session.visit_number,
        "depth_tier": session.depth_tier,
        "score": {
            "completion": session.completion_points,
            "reflection": session.reflection_points,
            "total": session.total_points,
        },
        "exercises": exercises,
    }


def _amphitheatre_hint_for_plan(plan):
    if not plan:
        return {
            "label": "Your practice awaits",
            "subtext": "We'll choose a prompt as soon as you arrive.",
            "count": 0,
        }
    first_id = plan[0]["id"]
    hint = AMPHITHEATRE_HINTS.get(first_id, {})
    return {
        "label": hint.get("label", "Practice at the Amphitheatre"),
        "subtext": hint.get("subtext", "We'll keep it gentle and grounded."),
        "count": len(plan),
        "exercise_titles": [slot["title"] for slot in plan],
    }


def _amphitheatre_reflection_feed(user, limit=6):
    records = (
        AmphitheatreExerciseRecord.objects.filter(session__user=user, state="done")
        .order_by("-completed_at", "-updated_at")
        .select_related("session")[:limit]
    )
    feed = []
    for record in records:
        timestamp = record.completed_at or record.updated_at
        feed.append(
            {
                "exercise_id": record.exercise_id,
                "exercise_title": EXERCISE_TITLES.get(record.exercise_id, record.exercise_id),
                "reflection_text": record.reflection_text,
                "philosopher_response": record.philosopher_response,
                "has_audio": record.has_audio,
                "timestamp": timestamp,
                "session_visit": record.session.visit_number,
            }
        )
    return feed


def _get_level_for_district(district_number):
    try:
        return Level.objects.get(number=district_number)
    except Level.DoesNotExist:
        return None


def _get_module_progress(user, module):
    progress, _ = UserProgress.objects.get_or_create(user=user, module=module)
    return progress


def _module_prerequisites_complete(user, module):
    modules = Module.objects.filter(level=module.level).order_by('order')
    previous_modules = modules.filter(order__lt=module.order)
    for previous in previous_modules:
        if not UserProgress.objects.filter(user=user, module=previous, completed=True).exists():
            return False
    return True


def _module_status_for_user(user, module):
    progress = UserProgress.objects.filter(user=user, module=module).first()
    if progress and progress.completed:
        return "complete", progress
    if progress and progress.started:
        return "in_progress", progress
    if _module_prerequisites_complete(user, module):
        return "available", progress
    return "locked", progress


def _user_has_district_full_access(profile, district_number):
    flags = profile.district_full_access or {}
    return flags.get(str(district_number)) is True


def _set_district_full_access(profile, district_number):
    flags = profile.district_full_access or {}
    if flags.get(str(district_number)):
        return False
    flags[str(district_number)] = True
    profile.district_full_access = flags
    profile.save(update_fields=['district_full_access'])
    return True


def _unlock_module_and_venues(user, module):
    unlock_payload = {
        "module": module.code,
        "unlocks": [],
    }

    # Unlock the next module in sequence (implicitly via status, but surface for UI)
    next_module = Module.objects.filter(
        level=module.level,
        order__gt=module.order
    ).order_by('order').first()

    if next_module:
        unlock_payload["unlocks"].append({
            "type": "module",
            "code": next_module.code,
            "name": next_module.name,
        })
        AnalyticsEvent.objects.create(
            user=user,
            event_type='module_unlocked_next',
            event_data={'module': next_module.code}
        )

    district_number = module.level.number
    venue_map = DISTRICT_MODULE_VENUE_MAP.get(district_number, {})
    venue_name = venue_map.get(module.code.upper())

    if venue_name:
        venue = Venue.objects.filter(
            district__number=district_number,
            name__iexact=venue_name
        ).first()
        if venue:
            _, created = UserVenueUnlock.objects.get_or_create(user=user, venue=venue)
            if created:
                unlock_payload["unlocks"].append({
                    "type": "venue",
                    "venue_id": venue.id,
                    "name": venue.name,
                })
                AnalyticsEvent.objects.create(
                    user=user,
                    event_type='venue_unlocked',
                    event_data={'venue_id': venue.id, 'venue_name': venue.name}
                )

    # Module D grants free navigation inside the district (full access)
    if module.code.upper() == "D":
        profile = user.profile
        changed = _set_district_full_access(profile, district_number)
        if not profile.district_1_unlocked and district_number == 1:
            profile.district_1_unlocked = True
            profile.save(update_fields=['district_1_unlocked'])
            changed = True
        if changed:
            unlock_payload["unlocks"].append({
                "type": "district_full_access",
                "district": district_number,
            })
            AnalyticsEvent.objects.create(
                user=user,
                event_type='district_full_access_granted',
                event_data={'district': district_number}
            )

    return unlock_payload


def _finalize_module_completion(user, module, progress):
    if progress.completed:
        return None
    progress.completed = True
    progress.last_activity = timezone.now()
    progress.save(update_fields=['completed', 'last_activity'])

    AnalyticsEvent.objects.create(
        user=user,
        event_type='lesson_complete',
        event_data={'module': module.code}
    )

    AnalyticsEvent.objects.create(
        user=user,
        event_type='module_completed',
        event_data={'module': module.code}
    )

    unlock_payload = _unlock_module_and_venues(user, module)
    return unlock_payload


def _user_has_venue_access(user, venue):
    profile = user.profile
    if _user_has_district_full_access(profile, venue.district.number):
        return True
    return UserVenueUnlock.objects.filter(user=user, venue=venue).exists()


def _module_code_for_venue(venue):
    mapping = DISTRICT_MODULE_VENUE_MAP.get(venue.district.number, {})
    for module_code, venue_name in mapping.items():
        if venue_name and venue.name.lower() == venue_name.lower():
            return module_code
    return None


def _append_meta_history(progress, key, payload, limit=10):
    meta = progress.meta or {}
    history = meta.get(key, [])
    history.append(payload)
    meta[key] = history[-limit:]
    progress.meta = meta


def _get_module_and_block(user, module_code, block_id):
    level_1 = Level.objects.get(number=1)
    module = get_object_or_404(Module, level=level_1, code=module_code.upper())
    block = get_object_or_404(KnowledgeBlock, module=module, id=block_id)
    progress, _ = UserProgress.objects.get_or_create(user=user, module=module)
    if progress.current_knowledge_block_id != block.id:
        progress.current_knowledge_block = block
    return module, block, progress


def _stage_keys_for(progress):
    return [s["key"] for s in get_stage_sequence(progress)]


def _validate_stage(progress, stage_key):
    allowed = _stage_keys_for(progress)
    if stage_key not in allowed:
        return False, _json_error("Stage not allowed in current sequence.", code='invalid_stage')
    if progress.stage_key != stage_key:
        return False, _json_error("Stage out of order.", code='stage_out_of_order')
    return True, None


def _validate_loop_index(progress, loop_index):
    if loop_index != progress.loop_index:
        return False, _json_error("Loop index mismatch; reload to refresh state.", code='loop_conflict')
    return True, None


def _compute_next_stage(progress, completed_stage):
    order = _stage_keys_for(progress)
    idx = order.index(completed_stage)
    if idx + 1 < len(order):
        next_stage = order[idx + 1]
        progress.stage_key = next_stage
        return next_stage
    # Completed sequence
    if progress.pass_type == 'main':
        progress.loop_index += 1
    else:
        # Return pass completed; restore main loop
        progress.pass_type = 'main'
        progress.return_at = None
    progress.stage_key = order[0] if order else 'prime'
    return None


def _build_submission_response(progress, next_stage, toast=None, unlocks=None):
    payload = {
        "ok": True,
        "progress": build_progress_payload(progress),
        "next": {
            "stage_key": next_stage if next_stage else progress.stage_key,
        }
    }
    if toast:
        payload["toast"] = toast
    if unlocks:
        payload["unlocks"] = unlocks
    return JsonResponse(payload)


def _parse_client_ts(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except Exception:
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def _create_submission(user, module, block, progress, stage_key, payload, duration_ms=0, lever_choice=None, scores=None, client_ts=None):
    return ExerciseSubmission.objects.create(
        user=user,
        module=module,
        knowledge_block=block,
        loop_index=progress.loop_index,
        pass_type=progress.pass_type,
        stage_key=stage_key,
        lever_choice=lever_choice or '',
        payload=payload,
        scores=scores or {},
        duration_ms=duration_ms or 0,
        client_ts=client_ts,
    )


def _parse_hours(label):
    if not label:
        return 0
    if isinstance(label, (int, float)):
        return float(label)
    label = str(label).strip()
    if label.endswith('h'):
        try:
            return float(label[:-1])
        except ValueError:
            return 0
    try:
        return float(label)
    except ValueError:
        return 0


def login_view(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            AnalyticsEvent.objects.create(
                user=user,
                event_type='user_login',
                event_data={}
            )
            return redirect('home')
        else:
            return render(request, 'myApp/auth/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'myApp/auth/login.html')


def signup_view(request):
    """Signup view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Email is now saved in user.email (Django User model)
            login(request, user)
            AnalyticsEvent.objects.create(
                user=user,
                event_type='user_signup',
                event_data={
                    'email': user.email,  # Track email collection
                    'username': user.username
                }
            )
            return redirect('onboarding')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'myApp/auth/signup.html', {'form': form})


def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    """User profile page"""
    profile = request.user.profile
    context = {
        'profile': profile,
    }
    return render(request, 'myApp/profile.html', context)


@ensure_csrf_cookie
def home(request):
    """Home page - landing for unauthenticated, dashboard for authenticated"""
    if not request.user.is_authenticated:
        # Show landing page for unauthenticated users
        return render(request, 'landing/index.html')
    
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Assign A/B variant if not set
    if not profile.ab_variant:
        profile.ab_variant = random.choice(['A', 'B'])
        profile.save(update_fields=['ab_variant'])

    # Require onboarding before showing dashboard
    if not profile.onboarding_completed:
        return redirect('onboarding')

    districts = District.objects.all().order_by('number')
    district_cards = []
    resume_module = None

    user_venue_unlocks = UserVenueUnlock.objects.filter(user=request.user).select_related('venue')

    for district in districts:
        level = _get_level_for_district(district.number)
        module_qs = Module.objects.filter(level=level).order_by('order') if level else Module.objects.none()
        modules_data = []
        all_complete = bool(module_qs)
        any_started = False
        completed_count = 0
        total_modules = module_qs.count()

        for module in module_qs:
            status, progress = _module_status_for_user(request.user, module)
            if status == "in_progress" and resume_module is None:
                resume_module = {
                    'code': module.code,
                    'name': module.name,
                    'id': module.id,
                    'module': module,
                }
            if status != "complete":
                all_complete = False
            if status == "in_progress":
                any_started = True

            modules_data.append({
                'id': module.id,
                'code': module.code,
                'name': module.name,
                'description': module.description,
                'status': status,
                'progress': progress,
                'unlock_hint': DISTRICT_MODULE_VENUE_MAP.get(district.number, {}).get(module.code.upper()),
            })
            if status == "complete":
                completed_count += 1

        base_access = (
            district.number == DISTRICT_DEFAULT_UNLOCK
            or _user_has_district_full_access(profile, district.number)
            or (district.number == 1 and profile.district_1_unlocked)
        )

        if all_complete and module_qs:
            district_status = "complete"
        elif any_started:
            district_status = "in_progress"
        elif base_access:
            district_status = "available"
        else:
            district_status = "locked"

        primary_module = None
        for module in modules_data:
            if module['status'] == 'in_progress':
                primary_module = module
                break
        if not primary_module:
            for module in modules_data:
                if module['status'] == 'available':
                    primary_module = module
                    break
        if not primary_module and modules_data:
            primary_module = modules_data[0]

        venues = Venue.objects.filter(district=district).order_by('order')
        total_venues = venues.count()
        unlocked_venues = total_venues if _user_has_district_full_access(profile, district.number) else \
            user_venue_unlocks.filter(venue__district=district).count()
        locked_venues = max(total_venues - unlocked_venues, 0)

        district_cards.append({
            'district': district,
            'status': district_status,
            'modules': modules_data,
            'base_access': base_access,
            'all_complete': all_complete,
            'any_started': any_started,
            'total_modules': total_modules,
            'completed_modules': completed_count,
            'progress_percent': int(round((completed_count / total_modules) * 100)) if total_modules else 0,
            'primary_module': primary_module,
            'locked_venues': locked_venues if locked_venues > 0 else 0,
            'venue_names': list(venues.values_list('name', flat=True)),
        })

    # Get Level 1 for milestone and quest context (fallback friendly)
    level_1 = Level.objects.filter(number=1).first()

    all_modules_complete = False
    milestone_passed = False
    if level_1:
        level_modules = Module.objects.filter(level=level_1).order_by('order')
        progresses = UserProgress.objects.filter(user=request.user, module__in=level_modules)
        all_modules_complete = level_modules.exists() and progresses.filter(completed=True).count() == level_modules.count()
        milestone_passed = MilestoneAttempt.objects.filter(
            user=request.user,
            level=level_1,
            pass_bool=True
        ).exists()

    today = date.today()
    daily_quest, _ = DailyQuest.objects.get_or_create(
        user=request.user,
        date=today,
        quest_type='complete_drill',
        defaults={
            'description': 'Complete one drill',
            'xp_reward': 10,
            'coin_reward': 5
        }
    )

    context = {
        'profile': profile,
        'district_cards': district_cards,
        'resume_module': resume_module,
        'daily_quest': daily_quest,
        'milestone_passed': milestone_passed,
        'all_modules_complete': all_modules_complete,
        'variant': profile.ab_variant,
    }

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='home_view',
        event_data={
            'variant': profile.ab_variant,
            'view_mode': 'districts'
        }
    )

    return render(request, 'myApp/home.html', context)


@login_required
def onboarding(request):
    """Onboarding flow - 7 questions"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Process onboarding answers
        profile.role = request.POST.get('role', '')
        profile.typical_audience = request.POST.get('audience', '')
        profile.main_goal = request.POST.get('goal', '')
        profile.comfort_under_pressure = request.POST.get('comfort', '')
        profile.time_pressure_profile = request.POST.get('time_pressure', '')
        profile.preferred_practice_time = request.POST.get('practice_time', '')
        profile.daily_goal_minutes = int(request.POST.get('daily_goal', 15))
        profile.onboarding_completed = True
        profile.save()
        
        # Track analytics
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='onboarding_complete',
            event_data={}
        )
        
        return redirect('home')
    
    return render(request, 'myApp/onboarding.html')


@login_required
def district_overview(request, district_number):
    """District overview: hero video, transcript, module list"""
    district = get_object_or_404(District, number=district_number)
    profile = request.user.profile

    level = _get_level_for_district(district.number)
    modules = Module.objects.filter(level=level).order_by('order') if level else Module.objects.none()
    module_cards = []
    available_modules = []

    for module in modules:
        status, progress = _module_status_for_user(request.user, module)
        prerequisites_complete = _module_prerequisites_complete(request.user, module)
        module_cards.append({
            'id': module.id,
            'code': module.code,
            'name': module.name,
            'description': module.description,
            'status': status,
            'prerequisites_complete': prerequisites_complete,
            'progress': progress,
            'unlock_hint': DISTRICT_MODULE_VENUE_MAP.get(district.number, {}).get(module.code.upper()),
            'lesson_video_url': module.lesson_video_url,
        })
        if status in ("available", "in_progress"):
            available_modules.append(module.code)

    base_access = (
        district.number == DISTRICT_DEFAULT_UNLOCK
        or _user_has_district_full_access(profile, district.number)
        or (district.number == 1 and profile.district_1_unlocked)
    )

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='district_view',
        event_data={'district': district_number, 'mode': 'overview'}
    )

    context = {
        'profile': profile,
        'district': district,
        'module_cards': module_cards,
        'base_access': base_access,
        'available_modules': available_modules,
    }
    return render(request, 'myApp/district_overview.html', context)


@login_required
def district_venues(request, district_number):
    """List venues within a district with unlock states"""
    district = get_object_or_404(District, number=district_number)
    profile = request.user.profile
    venues = Venue.objects.filter(district=district).order_by('order')
    unlocked_ids = set(UserVenueUnlock.objects.filter(user=request.user, venue__district=district).values_list('venue_id', flat=True))
    full_access = _user_has_district_full_access(profile, district.number)

    venue_cards = []
    for venue in venues:
        unlocked = full_access or (venue.id in unlocked_ids)
        venue_cards.append({
            'venue': venue,
            'unlocked': unlocked,
            'status': 'available' if unlocked else 'locked',
        })

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='district_view',
        event_data={'district': district_number, 'mode': 'venues'}
    )

    context = {
        'district': district,
        'venue_cards': venue_cards,
        'full_access': full_access,
        'profile': profile,
    }
    return render(request, 'myApp/district_venues.html', context)


@login_required
def module_learn(request, module_code):
    """Module learning page: video, transcript, AI coach context"""
    profile = request.user.profile

    level = Level.objects.filter(number=1).first()
    module = get_object_or_404(Module, level=level, code=module_code.upper())

    status, progress = _module_status_for_user(request.user, module)
    if status == "locked":
        return redirect('district_overview', district_number=module.level.number)

    progress = _get_module_progress(request.user, module)
    if not progress.started:
        progress.started = True
        progress.last_activity = timezone.now()
        progress.save(update_fields=['started', 'last_activity'])
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='lesson_start',
            event_data={'module': module.code}
        )

    knowledge_blocks = module.knowledge_blocks.order_by('order')
    guided_flow = load_guided_flow(module.code)
    first_step = guided_flow["steps"][0] if guided_flow and guided_flow.get("steps") else None

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='module_learn_view',
        event_data={'module': module.code}
    )

    context = {
        'profile': profile,
        'module': module,
        'progress': progress,
        'knowledge_blocks': knowledge_blocks,
        'video_url': module.lesson_video_url,
        'transcript': module.lesson_transcript,
        'coach_context': {
            'module_code': module.code,
            'module_name': module.name,
            'knowledge_blocks': list(knowledge_blocks.values('title', 'summary')),
            'transcript_present': bool(module.lesson_transcript),
        },
        'guided_first_step': serialize_guided_step(first_step) if first_step else None,
        'guided_flow_meta': {
            'version': guided_flow.get('version'),
            'total_steps': len(guided_flow.get('steps', [])),
        } if guided_flow else {},
    }
    return render(request, 'myApp/module_learn.html', context)


@login_required
def module_guided(request, module_code):
    """Dedicated guided lesson page with single-prompt flow."""
    profile = request.user.profile

    level = Level.objects.filter(number=1).first()
    module = get_object_or_404(Module, level=level, code=module_code.upper())

    status, progress = _module_status_for_user(request.user, module)
    if status == "locked":
        return redirect('district_overview', district_number=module.level.number)

    progress = _get_module_progress(request.user, module)

    guided_flow = load_guided_flow(module.code)
    first_step = guided_flow["steps"][0] if guided_flow and guided_flow.get("steps") else None

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='lesson_guided_view',
        event_data={'module': module.code}
    )

    context = {
        'profile': profile,
        'module': module,
        'progress': progress,
        'guided_first_step': serialize_guided_step(first_step) if first_step else None,
        'guided_flow_meta': {
            'version': guided_flow.get('version'),
            'total_steps': len(guided_flow.get('steps', [])),
        } if guided_flow else {},
    }
    return render(request, 'myApp/module_guided.html', context)


def _ensure_guided_flow(module: Module) -> dict:
    flow = load_guided_flow(module.code)
    if not flow or not flow.get("steps"):
        raise ValueError(f"Guided script missing for module {module.code}")
    return flow


def _update_progress_started(user, module):
    progress = _get_module_progress(user, module)
    if not progress.started:
        progress.started = True
        progress.last_activity = timezone.now()
        progress.save(update_fields=['started', 'last_activity'])
        AnalyticsEvent.objects.create(
            user=user,
            event_type='lesson_guided_start',
            event_data={'module': module.code}
        )
    return progress


def _build_guided_summary(session: LessonSession):
    responses = session.responses.order_by('created_at')
    fields = [
        {
            "step_id": response.step_id,
            "field_name": response.field_name,
            "value": response.value.get("value", response.value),
            "recorded_at": response.created_at.isoformat(),
        }
        for response in responses
    ]
    return {
        "steps_completed": len(fields),
        "fields": fields,
    }


def _normalize_input(step, payload_value):
    input_type = (step.get("input_type") or "").lower()
    validation = step.get("validation") or {}

    if input_type in {"text", "textarea"}:
        value = (payload_value or "").strip()
        if validation.get("required") and not value:
            raise ValueError("This field is required.")
        min_length = validation.get("min_length")
        if min_length and len(value) < int(min_length):
            raise ValueError(f"Answer must be at least {min_length} characters.")
        return value

    if input_type == "select":
        value = (payload_value or "").strip()
        if validation.get("required") and not value:
            raise ValueError("Please choose an option.")
        options = step.get("options") or []
        allowed = {opt.get("value") for opt in options}
        if allowed and value not in allowed:
            raise ValueError("Selection not recognised.")
        return value

    if input_type == "rating":
        if payload_value in (None, ""):
            raise ValueError("Rating is required.")
        try:
            value = int(payload_value)
        except (TypeError, ValueError):
            raise ValueError("Rating must be a number.")
        min_value = validation.get("min_value")
        max_value = validation.get("max_value")
        if min_value is not None and value < int(min_value):
            raise ValueError(f"Rating must be ≥ {min_value}.")
        if max_value is not None and value > int(max_value):
            raise ValueError(f"Rating must be ≤ {max_value}.")
        return value

    if input_type in {"confirm", "continue"}:
        if payload_value in (True, "true", "True", "1", 1, None, ""):
            return True
        raise ValueError("Confirmation required.")

    if input_type == "complete":
        return True

    return payload_value


@login_required
@require_http_methods(["POST"])
def lesson_start(request):
    data, error = _parse_request_json(request)
    if error:
        return error
    module_code = (data.get("module") or "").upper()
    if not module_code:
        return _json_error("module is required.", code='missing_module')

    level_1 = Level.objects.get(number=1)
    module = get_object_or_404(Module, level=level_1, code=module_code)
    try:
        flow = _ensure_guided_flow(module)
    except ValueError as exc:
        return _json_error(str(exc), status=404, code='guided_unavailable')

    steps = flow["steps"]
    first_step = steps[0]

    progress = _update_progress_started(request.user, module)
    progress.last_activity = timezone.now()
    progress.save(update_fields=['last_activity'])

    session = LessonSession.objects.create(
        user=request.user,
        module=module,
        state="asking",
        current_step_id=first_step["step_id"],
        current_order=first_step.get("order", 1),
        total_steps=len(steps),
        flow_version=flow.get("version", "v1"),
        context={"answers": {}},
    )

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='lesson_guided_session_created',
        event_data={'module': module.code, 'session_id': str(session.id)}
    )

    return JsonResponse({
        "session_id": str(session.id),
        "module": module.code,
        "step": serialize_guided_step(first_step),
        "state": session.state,
        "total_steps": len(steps),
    })


@login_required
@require_http_methods(["POST"])
def lesson_answer(request):
    data, error = _parse_request_json(request)
    if error:
        return error
    session_id = data.get("session_id")
    step_id = data.get("step_id")
    field_name = data.get("field_name")
    value = data.get("value")

    if not session_id or not step_id or not field_name:
        return _json_error("session_id, step_id, and field_name are required.", code='missing_fields')

    session = get_object_or_404(LessonSession, id=session_id, user=request.user)
    module = session.module

    flow = load_guided_flow(module.code)
    if not flow:
        return _json_error("Guided script unavailable.", status=404, code='guided_unavailable')
    steps = flow["steps"]
    index = flow["index"]

    current_step = index.get(step_id)
    if not current_step:
        return _json_error("Unknown step_id.", code='unknown_step')

    if session.current_step_id != step_id:
        return _json_error("Step order mismatch; refresh to resume.", code='step_out_of_order')

    try:
        normalized_value = _normalize_input(current_step, value)
    except ValueError as exc:
        return _json_error(str(exc), code='validation_error')

    LessonStepResponse.objects.create(
        session=session,
        step_id=step_id,
        field_name=field_name,
        value={"value": normalized_value},
    )

    answers = session.context.get("answers", {})
    answers[field_name] = normalized_value
    session.context["answers"] = answers

    current_index = next((idx for idx, step in enumerate(steps) if step["step_id"] == step_id), None)
    next_step = steps[current_index + 1] if current_index is not None and current_index + 1 < len(steps) else None

    session.state = "waiting"
    session.save(update_fields=["context", "state", "updated_at"])

    webhook_output: Optional[str] = None
    webhook_payload: Dict[str, Any] = {}
    webhook_request: Dict[str, Any] = {}
    try:
        message_text = _coerce_message_text(normalized_value)
        webhook_output, webhook_payload, webhook_request = _call_exercise_webhook(session, request.user, message_text)
    except WebhookError:
        session.state = "asking"
        session.save(update_fields=["state", "updated_at"])
        return _json_error(
            "We hit a snag processing that answer. Try again in a moment.",
            status=502,
            code='webhook_failed',
        )

    if webhook_payload:
        trace = session.context.get("webhook_trace", [])
        trace.append(
            {
                "step_id": step_id,
                "field_name": field_name,
                "request": webhook_request,
                "response": {
                    "module1_test_response": webhook_payload.get("module1_test_response")
                },
                "recorded_at": timezone.now().isoformat(),
            }
        )
        session.context["webhook_trace"] = trace[-5:]
    if webhook_output is not None:
        session.context["last_webhook_output"] = webhook_output

    progress = _get_module_progress(request.user, module)
    progress.last_activity = timezone.now()
    progress.save(update_fields=['last_activity'])

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='lesson_guided_step_submitted',
        event_data={'module': module.code, 'session_id': str(session.id), 'step_id': step_id}
    )

    if not next_step:
        session.state = "completed"
        session.current_step_id = ""
        session.save(update_fields=['state', 'current_step_id', 'context', 'updated_at'])
        summary = _build_guided_summary(session)
        unlocks = _finalize_module_completion(request.user, module, progress)
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='lesson_guided_complete',
            event_data={'module': module.code, 'session_id': str(session.id)}
        )
        payload = {
            "completed": True,
            "summary": summary,
            "state": session.state,
        }
        if unlocks:
            payload["unlocks"] = unlocks
        return JsonResponse(payload)

    if next_step.get("input_type") == "complete":
        session.current_step_id = next_step["step_id"]
        session.current_order = next_step.get("order", session.current_order + 1)
        session.state = "transitioning"
        session.save(update_fields=['current_step_id', 'current_order', 'state', 'context', 'updated_at'])
        summary = _build_guided_summary(session)
        session.state = "completed"
        session.save(update_fields=['state', 'updated_at'])
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='lesson_guided_complete',
            event_data={'module': module.code, 'session_id': str(session.id)}
        )
        unlocks = _finalize_module_completion(request.user, module, progress)
        payload = {
            "completed": True,
            "completion_step": serialize_guided_step(next_step),
            "summary": summary,
            "state": session.state,
        }
        if webhook_output is not None:
            payload["completion_step"]["prompt_body"] = webhook_output
        if unlocks:
            payload["unlocks"] = unlocks
        return JsonResponse(payload)

    session.current_step_id = next_step["step_id"]
    session.current_order = next_step.get("order", session.current_order + 1)
    session.state = "transitioning"
    session.save(update_fields=['current_step_id', 'current_order', 'state', 'context', 'updated_at'])
    session.state = "asking"
    session.save(update_fields=['state', 'updated_at'])

    next_payload = serialize_guided_step(next_step)
    if webhook_output is not None:
        next_payload["prompt_body"] = webhook_output

    return JsonResponse({
        "next_step": next_payload,
        "session_id": str(session.id),
        "state": session.state,
    })


@login_required
@require_http_methods(["GET"])
def lesson_resume(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return _json_error("session_id is required.", code='missing_session')
    session = get_object_or_404(LessonSession, id=session_id, user=request.user)
    module = session.module
    flow = load_guided_flow(module.code)
    if not flow:
        return _json_error("Guided script unavailable.", status=404, code='guided_unavailable')
    index = flow["index"]

    if session.state == "completed":
        summary = _build_guided_summary(session)
        return JsonResponse({
            "completed": True,
            "summary": summary,
            "state": session.state,
        })

    current_step = index.get(session.current_step_id)
    if not current_step:
        return _json_error("Active step not found; restart session.", status=409, code='step_not_found')

    return JsonResponse({
        "session_id": str(session.id),
        "step": serialize_guided_step(current_step),
        "state": session.state,
        "total_steps": session.total_steps,
    })



@login_required
@require_http_methods(["POST"])
def lesson_teach_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    data, error = _parse_request_json(request)
    if error:
        return error
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'teach')
    if not valid:
        return error_resp
    tile_slug = data.get('tile_slug') or f"{module.code}-{block.order}"
    payload = {
        "tile_slug": tile_slug,
        "summary_hash": hash(block.summary),
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'teach',
        payload,
        client_ts=client_ts,
    )
    _append_meta_history(progress, 'teach', payload)
    next_stage = _compute_next_stage(progress, 'teach')
    progress.last_activity = timezone.now()
    progress.save()
    return _build_submission_response(progress, next_stage)


@login_required
@require_http_methods(["POST"])
def lesson_diagnose_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'diagnose')
    if not valid:
        return error_resp
    pic = data.get('pic') or {}
    try:
        pressure = int(pic.get('pressure', 0))
        visibility = int(pic.get('visibility', 0))
        irreversibility = int(pic.get('irreversibility', 0))
        control = int(pic.get('control', 0))
    except (TypeError, ValueError):
        return _json_error("PIC values must be integers.", code='invalid_pic')
    for value in (pressure, visibility, irreversibility, control):
        if value < 0 or value > 5:
            return _json_error("PIC values must be between 0 and 5.", code='invalid_pic')
    load_label = (data.get('load_label') or 'unknown').lower()
    load_options = {choice[0] for choice in UserProgress.LOAD_CHOICES}
    if load_label not in load_options:
        return _json_error("Invalid load label.", code='invalid_load')
    scenario_text = data.get('scenario_text', '').strip()
    previous_control = progress.pic_control
    payload = {
        "scenario_text": scenario_text,
        "pic": {
            "pressure": pressure,
            "visibility": visibility,
            "irreversibility": irreversibility,
            "control": control,
        },
        "load_label": load_label,
        "control_delta": control - previous_control,
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'diagnose',
        payload,
        client_ts=client_ts,
    )
    progress.pic_pressure = pressure
    progress.pic_visibility = visibility
    progress.pic_irreversibility = irreversibility
    progress.pic_control = control
    progress.load_label = load_label
    _append_meta_history(progress, 'diagnose', payload)
    next_stage = _compute_next_stage(progress, 'diagnose')
    progress.last_activity = timezone.now()
    progress.save()
    return _build_submission_response(progress, next_stage)


@login_required
@require_http_methods(["POST"])
def lesson_control_shift_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'control_shift')
    if not valid:
        return error_resp
    lever_choice = data.get('lever_choice')
    lever_options = {choice[0] for choice in UserProgress.LEVER_CHOICES}
    if lever_choice not in lever_options:
        return _json_error("Invalid lever choice.", code='invalid_lever')
    action_plan = (data.get('action_plan') or "").strip()
    payload = {
        "lever_choice": lever_choice,
        "action_plan": action_plan,
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'control_shift',
        payload,
        client_ts=client_ts,
        lever_choice=lever_choice,
    )
    progress.lever_choice = lever_choice
    _append_meta_history(progress, 'control_shift', payload)
    next_stage = _compute_next_stage(progress, 'control_shift')
    progress.last_activity = timezone.now()
    progress.save()
    return _build_submission_response(progress, next_stage)


@login_required
@require_http_methods(["POST"])
def lesson_perform_text_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    data, error = _parse_request_json(request)
    if error:
        return error
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'perform_text')
    if not valid:
        return error_resp
    text = (data.get('text') or "").strip()
    if not text:
        return _json_error("Text performance cannot be empty.", code='empty_text')
    word_count = data.get('word_count')
    if word_count is None:
        word_count = len(text.split())
    try:
        word_count = int(word_count)
    except (TypeError, ValueError):
        return _json_error("word_count must be numeric.", code='invalid_word_count')
    duration_ms = data.get('duration_ms', 0)
    try:
        duration_ms = int(duration_ms or 0)
    except (TypeError, ValueError):
        duration_ms = 0
    payload = {
        "text": text,
        "word_count": word_count,
        "duration_ms": duration_ms,
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'perform_text',
        payload,
        duration_ms=duration_ms,
        lever_choice=progress.lever_choice,
        client_ts=client_ts,
    )
    _append_meta_history(progress, 'perform_text', payload)
    next_stage = _compute_next_stage(progress, 'perform_text')
    progress.last_activity = timezone.now()
    progress.save()
    return _build_submission_response(progress, next_stage)


@login_required
@require_http_methods(["POST"])
def lesson_perform_voice_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'perform_voice')
    if not valid:
        return error_resp
    audio_ref = data.get('audio_ref')
    if not audio_ref:
        return _json_error("audio_ref is required.", code='missing_audio')
    duration_ms = data.get('duration_ms')
    try:
        duration_ms = int(duration_ms or 0)
    except (TypeError, ValueError):
        duration_ms = 0
    payload = {
        "audio_ref": audio_ref,
        "duration_ms": duration_ms,
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'perform_voice',
        payload,
        duration_ms=duration_ms,
        lever_choice=progress.lever_choice,
        client_ts=client_ts,
    )
    _append_meta_history(progress, 'perform_voice', payload)
    next_stage = _compute_next_stage(progress, 'perform_voice')
    progress.last_activity = timezone.now()
    progress.save()
    toast = None
    if not next_stage:
        toast = {
            "title": "Voice pass saved",
            "body": "Great work—check your review for feedback.",
        }
    return _build_submission_response(progress, next_stage, toast=toast)


@login_required
@require_http_methods(["POST"])
def lesson_review_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'review')
    if not valid:
        return error_resp
    self_explain = (data.get('self_explain') or "").strip()
    accept_suggestions = bool(data.get('accept_suggestions', False))
    scores = data.get('scores') or {}
    payload = {
        "self_explain": self_explain,
        "accept_suggestions": accept_suggestions,
        "scores": scores,
    }
    # Compute PIC delta using latest diagnose entry if available
    diagnose_history = progress.meta.get('diagnose', []) if progress.meta else []
    pic_delta = 0
    if diagnose_history:
        last_entry = diagnose_history[-1]
        pic_delta = last_entry.get('control_delta', 0)
        payload["pic_delta"] = pic_delta
    client_ts = _parse_client_ts(data.get('client_ts'))
    submission = _create_submission(
        request.user,
        module,
        block,
        progress,
        'review',
        payload,
        lever_choice=progress.lever_choice,
        scores=scores,
        client_ts=client_ts,
    )
    _append_meta_history(progress, 'review', payload)
    next_stage = _compute_next_stage(progress, 'review')
    progress.last_activity = timezone.now()
    progress.save()
    toast = {
        "title": "Review complete",
        "body": "AI feedback saved. PIC ΔControl: {:+d}".format(int(pic_delta)),
    }
    return _build_submission_response(progress, next_stage, toast=toast)


@login_required
@require_http_methods(["POST"])
def lesson_transfer_submit(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    try:
        loop_index = int(data.get('loop_index', progress.loop_index))
    except (TypeError, ValueError):
        return _json_error("loop_index must be an integer.", code='invalid_loop')
    valid, error_resp = _validate_loop_index(progress, loop_index)
    if not valid:
        return error_resp
    valid, error_resp = _validate_stage(progress, 'transfer')
    if not valid:
        return error_resp
    next_moment = data.get('next_moment') or {}
    desired_outcome = (data.get('desired_outcome') or "").strip()
    payload = {
        "next_moment": next_moment,
        "desired_outcome": desired_outcome,
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'transfer',
        payload,
        lever_choice=progress.lever_choice,
        client_ts=client_ts,
    )
    _append_meta_history(progress, 'transfer', payload)
    next_stage = _compute_next_stage(progress, 'transfer')
    progress.last_activity = timezone.now()
    progress.save()
    toast = {
        "title": "Transfer logged",
        "body": "Great—set a booster to revisit this in a day or two.",
    }
    unlock_payload = None
    if next_stage is None and progress.pass_type == 'main':
        unlock_payload = _finalize_module_completion(request.user, module, progress)
    return _build_submission_response(progress, next_stage, toast=toast, unlocks=unlock_payload)


@login_required
@require_http_methods(["POST"])
def lesson_spacing_schedule(request):
    return _json_error("Legacy lesson endpoint removed.", status=410, code='legacy_endpoint')
    module_code = data.get('module_code')
    block_id = data.get('block_id')
    if not module_code or not block_id:
        return _json_error("module_code and block_id are required.", code='missing_fields')
    module, block, progress = _get_module_and_block(request.user, module_code, block_id)
    base_label = data.get('base', '24h')
    jitter_label = data.get('jitter', '±6h')
    base_hours = _parse_hours(base_label)
    jitter_hours = 0
    if isinstance(jitter_label, str) and jitter_label.startswith('±'):
        jitter_hours = _parse_hours(jitter_label[1:])
    else:
        jitter_hours = _parse_hours(jitter_label)
    offset = random.uniform(-jitter_hours, jitter_hours) if jitter_hours else 0
    schedule_at = timezone.now() + timedelta(hours=base_hours + offset)
    progress.return_at = schedule_at
    progress.pass_type = 'return'
    progress.stage_key = RETURN_SEQUENCE[0]['key']
    progress.last_activity = timezone.now()
    _append_meta_history(progress, 'spacing', {
        "scheduled_for": schedule_at.isoformat(),
        "base": base_label,
        "jitter": jitter_label,
    })
    progress.save()
    payload = {
        "ok": True,
        "progress": build_progress_payload(progress),
        "next": {
            "stage_key": progress.stage_key,
        },
        "toast": {
            "title": "Booster scheduled",
            "body": schedule_at.strftime("Return pass due %b %d %H:%M"),
        }
    }
    return JsonResponse(payload)
@login_required
@require_http_methods(["POST"])
def ai_lesson_orchestrate(request):
    """AI webhook endpoint for lesson orchestration"""
    data = json.loads(request.body)
    user = request.user
    module_code = data.get('module')
    last_block_id = data.get('last_block')
    last_score = data.get('last_score', 0)
    confusion_flag = data.get('confusion_flag', False)
    
    # Get module
    level_1 = Level.objects.get(number=1)
    module = Module.objects.get(level=level_1, code=module_code.upper())
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=user,
        event_type='ai_lesson_request',
        event_data={'module': module_code, 'last_block': last_block_id}
    )
    
    # In production, this would call n8n webhook
    # For now, return a mock response
    try:
        # Try to call n8n (if configured)
        n8n_url = getattr(settings, 'N8N_LESSON_WEBHOOK', None)
        if n8n_url:
            response = requests.post(n8n_url, json={
                'user_id': user.id,
                'module': module_code,
                'last_block': last_block_id,
                'last_score': last_score,
                'confusion_flag': confusion_flag,
                'persona': user.profile.persona_summary
            }, timeout=5)
            if response.status_code == 200:
                return JsonResponse(response.json())
    except:
        pass
    
    # Fallback: return cached/mock block
    knowledge_block = KnowledgeBlock.objects.filter(module=module).first()
    if last_block_id:
        try:
            last_block = KnowledgeBlock.objects.get(id=last_block_id)
            next_block = KnowledgeBlock.objects.filter(
                module=module,
                order__gt=last_block.order
            ).first()
            if next_block:
                knowledge_block = next_block
        except:
            pass
    
    # Update user progress
    if knowledge_block:
        progress, _ = UserProgress.objects.get_or_create(
            user=user,
            module=module
        )
        progress.current_knowledge_block = knowledge_block
        progress.last_activity = timezone.now()
        
        # Check if this is the last block
        total_blocks = KnowledgeBlock.objects.filter(module=module).count()
        current_order = knowledge_block.order
        if current_order >= total_blocks - 1:
            progress.completed = True
        else:
            progress.completed = False
        
        progress.save()
    
    # Prepare response with all block data
    response_data = {
        'block_id': knowledge_block.id if knowledge_block else None,
        'title': knowledge_block.title if knowledge_block else 'No more blocks',
        'summary': knowledge_block.summary if knowledge_block else '',
        'citations': knowledge_block.citations if knowledge_block and knowledge_block.citations else []
    }
    
    # Include exercise_seeds (drill data and metadata)
    if knowledge_block and knowledge_block.exercise_seeds:
        response_data['exercise_seeds'] = knowledge_block.exercise_seeds
    else:
        response_data['exercise_seeds'] = []
    
    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def ai_coach_respond(request):
    """AI webhook endpoint for coach Q&A"""
    data = json.loads(request.body)
    question = data.get('question', '')
    module_code = data.get('module', '')
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='coach_question',
        event_data={'module': module_code, 'question_length': len(question)}
    )
    
    # In production, call n8n
    try:
        n8n_url = getattr(settings, 'N8N_COACH_WEBHOOK', None)
        if n8n_url:
            response = requests.post(n8n_url, json={
                'user_id': request.user.id,
                'question': question,
                'module': module_code,
                'persona': request.user.profile.persona_summary
            }, timeout=5)
            if response.status_code == 200:
                return JsonResponse(response.json())
    except:
        pass
    
    # Fallback response
    return JsonResponse({
        'answer': 'I\'m here to help you learn. Try asking about the current concept or request a simpler explanation.',
        'source_chips': [],
        'suggested_drill': None
    })


@login_required
def ai_chat(request):
    """AI Chat page - Coach interface"""
    profile = request.user.profile
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='ai_chat_view',
        event_data={}
    )
    
    context = {
        'profile': profile,
        'current_level': profile.current_level,
    }
    
    return render(request, 'myApp/ai_chat.html', context)


@login_required
@require_http_methods(["POST"])
def ai_chat_send(request):
    """Send message to AI coach"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
        
        # Track analytics
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='ai_chat_message',
            event_data={'message_length': len(message)}
        )
        
        # Call the existing ai_coach_respond logic
        # In production, this would call n8n webhook
        try:
            n8n_url = getattr(settings, 'N8N_COACH_WEBHOOK', None)
            if n8n_url:
                response = requests.post(n8n_url, json={
                    'user_id': request.user.id,
                    'question': message,
                    'module': '',
                    'persona': request.user.profile.persona_summary
                }, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('answer', 'I\'m here to help you learn!')
                    return JsonResponse({
                        'success': True,
                        'response': answer
                    })
        except Exception as e:
            # Fallback if n8n fails
            pass
        
        # Fallback response
        fallback_responses = [
            "I'm here to help you master high-stakes communication! What would you like to know?",
            "Great question! Let me help you understand this better. Can you tell me more about what you're working on?",
            "I'm your AI coach, ready to guide you. What specific aspect of communication would you like to improve?",
            "Let's work together to build your confidence. What's your main challenge right now?",
        ]
        
        return JsonResponse({
            'success': True,
            'response': random.choice(fallback_responses)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def milestone(request, level_number):
    """Milestone assessment page"""
    level = get_object_or_404(Level, number=level_number)
    profile = request.user.profile
    
    # Check if user has completed all modules
    level_1 = Level.objects.get(number=1)
    modules = Module.objects.filter(level=level_1)
    all_complete = all(
        UserProgress.objects.filter(user=request.user, module=m, completed=True).exists()
        for m in modules
    )
    
    if not all_complete:
        return redirect('home')
    
    # Get previous attempts
    previous_attempts = MilestoneAttempt.objects.filter(
        user=request.user,
        level=level
    ).order_by('-created_at')[:5]
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='milestone_start',
        event_data={'level': level_number}
    )
    
    context = {
        'level': level,
        'profile': profile,
        'previous_attempts': previous_attempts,
    }
    
    return render(request, 'myApp/milestone_challenge.html', context)


@login_required
@require_http_methods(["POST"])
def milestone_submit(request, level_number):
    """Submit milestone assessment"""
    level = get_object_or_404(Level, number=level_number)
    
    audio_url = request.POST.get('audio_url', '')
    transcript = request.POST.get('transcript', '')
    
    # In production, call n8n for scoring
    try:
        n8n_url = getattr(settings, 'N8N_MILESTONE_WEBHOOK', None)
        if n8n_url:
            response = requests.post(n8n_url, json={
                'user_id': request.user.id,
                'level': level_number,
                'audio_url': audio_url,
                'transcript': transcript,
                'persona': request.user.profile.persona_summary
            }, timeout=30)
            if response.status_code == 200:
                result = response.json()
                overall_score = result.get('overall_score', 0)
                rubric_scores = result.get('rubric_scores', {})
                pass_bool = overall_score >= level.milestone_threshold
                coaching_note = result.get('coaching_note', '')
            else:
                # Fallback scoring
                overall_score = 75.0
                rubric_scores = {'clarity': 75, 'structure': 80, 'presence': 70, 'influence': 65}
                pass_bool = overall_score >= level.milestone_threshold
                coaching_note = 'Great effort! Keep practicing.'
        else:
            # Fallback scoring
            overall_score = 75.0
            rubric_scores = {'clarity': 75, 'structure': 80, 'presence': 70, 'influence': 65}
            pass_bool = overall_score >= level.milestone_threshold
            coaching_note = 'Great effort! Keep practicing.'
    except:
        # Fallback scoring
        overall_score = 75.0
        rubric_scores = {'clarity': 75, 'structure': 80, 'presence': 70, 'influence': 65}
        pass_bool = overall_score >= level.milestone_threshold
        coaching_note = 'Great effort! Keep practicing.'
    
    # Create milestone attempt
    profile = request.user.profile
    attempt = MilestoneAttempt.objects.create(
        user=request.user,
        level=level,
        overall_score=overall_score,
        rubric_scores=rubric_scores,
        pass_bool=pass_bool,
        coaching_note=coaching_note
    )
    
    # Award XP and tickets
    if pass_bool:
        profile.total_xp += 100
        profile.tickets += 3
        if not profile.district_1_unlocked:
            profile.district_1_unlocked = True
    else:
        profile.total_xp += 25
    profile.save()
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='milestone_complete',
        event_data={
            'level': level_number,
            'score': overall_score,
            'passed': pass_bool
        }
    )
    
    return JsonResponse({
        'success': True,
        'overall_score': overall_score,
        'rubric_scores': rubric_scores,
        'pass_bool': pass_bool,
        'coaching_note': coaching_note,
        'xp_earned': 100 if pass_bool else 25,
        'tickets_awarded': 3 if pass_bool else 0,
        'district_unlocked': pass_bool and not profile.district_1_unlocked
    })


@login_required
def venue_detail(request, venue_id):
    """Venue detail with task sheets"""
    venue = get_object_or_404(Venue, id=venue_id)
    profile = request.user.profile
    is_amphitheatre = venue.name.lower() == "greek amphitheatre"

    if not _user_has_venue_access(request.user, venue):
        required_module = _module_code_for_venue(venue)
        if required_module:
            messages.info(request, f"Complete Module {required_module} to unlock {venue.name}.")
        else:
            messages.info(request, f"{venue.name} unlocks after completing this district's modules.")
        return redirect('district_venues', district_number=venue.district.number)
    
    # Check tickets for paid venues
    if not is_amphitheatre and profile.tickets < venue.ticket_cost:
        messages.info(request, "You need more tickets to enter this venue.")
        return redirect('district_venues', district_number=venue.district.number)
    
    # Get or create entry
    entry, created = VenueEntry.objects.get_or_create(
        user=request.user,
        venue=venue,
        completed=False,
        defaults={'tickets_spent': 0 if is_amphitheatre else venue.ticket_cost}
    )
    
    if created and not is_amphitheatre:
        profile.tickets -= venue.ticket_cost
        profile.save()
        
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='venue_entered',
            event_data={'venue_id': venue_id, 'venue_name': venue.name}
        )
    
    if is_amphitheatre:
        return redirect('amphitheatre_hub')
    
    task_sheets = VenueTaskSheet.objects.filter(venue=venue).order_by('order')
    
    context = {
        'venue': venue,
        'entry': entry,
        'task_sheets': task_sheets,
        'profile': profile,
    }
    
    template = 'myApp/district_venue.html'
    if venue.name.lower() == "greek amphitheatre":
        template = 'myApp/venue_greek_amphitheatre_welcome.html'
    return render(request, template, context)


@login_required
def venue_session(request, venue_id):
    """Dedicated guided session screen for a venue."""
    venue = get_object_or_404(Venue, id=venue_id)

    if not _user_has_venue_access(request.user, venue):
        messages.info(request, "Unlock this venue to start a guided session.")
        return redirect('venue_detail', venue_id=venue.id)

    initial_prompt = (
        f"Welcome to the {venue.name}. Take a breath, then share what moment you're preparing for."
    )

    return render(
        request,
        'myApp/venue_session.html',
        {
            'venue': venue,
            'initial_prompt': initial_prompt,
        },
    )


@login_required
@require_http_methods(["POST"])
def venue_session_feedback(request, venue_id):
    """Return a short AI reflection for a venue session transcript."""
    venue = get_object_or_404(Venue, id=venue_id)

    payload, error = _parse_request_json(request)
    if error:
        return error

    transcript = (payload.get("transcript") or "").strip()
    session_id = (payload.get("session_id") or "").strip()
    if not transcript:
        return _json_error("Transcript is required.", code="missing_transcript")

    message = ""

    if VENUE_SESSION_WEBHOOK_URL:
        try:
            webhook_response = requests.post(
                VENUE_SESSION_WEBHOOK_URL,
                json={
                    "venue_id": venue.id,
                    "venue_name": venue.name,
                    "user_id": request.user.id,
                    "transcript": transcript,
                    "session_id": session_id or None,
                },
                timeout=12,
            )
            webhook_response.raise_for_status()
            try:
                payload = webhook_response.json()
            except ValueError:
                payload = {"message": webhook_response.text}
            nested_response = (
                payload.get("greek_amphitheatre_response")
                or payload.get("greek_amphitheatre")
                or {}
            )
            if isinstance(nested_response, dict):
                output_block = nested_response.get("output") or {}
                if isinstance(output_block, dict) and output_block.get("text"):
                    message = str(output_block.get("text")).strip()
                elif isinstance(output_block, str):
                    message = output_block.strip()
            if not message:
                for key in ("message", "response", "reply", "text"):
                    if payload.get(key):
                        message = str(payload[key]).strip()
                        break
            if not message:
                message = webhook_response.text.strip()
            AnalyticsEvent.objects.create(
                user=request.user,
                event_type="venue_session_webhook_success",
                event_data={
                    "venue_id": venue.id,
                    "session_id": session_id or None,
                    "status_code": webhook_response.status_code,
                    "excerpt": message[:180],
                },
            )
        except requests.RequestException as exc:
            AnalyticsEvent.objects.create(
                user=request.user,
                event_type="venue_session_feedback_error",
                event_data={
                    "venue_id": venue.id,
                    "session_id": session_id or None,
                    "error": f"webhook: {exc}",
                },
            )

    if not message:
        client = _get_openai_client()
        if client:
            system_prompt = (
                "You are The Philosopher guiding a communication practice session. "
                "Offer a concise, encouraging response (maximum two sentences). "
                "Acknowledge what the speaker shared, then offer a gentle nudge toward presence or clarity. "
                "Keep it warm, judgement-free, and grounded."
            )
            user_prompt = (
                f"The practice is happening inside the {venue.name}. "
                f"The speaker just said: \"{transcript}\""
            )

            try:
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                message = (response.output_text or "").strip()
            except Exception as exc:
                AnalyticsEvent.objects.create(
                    user=request.user,
                    event_type="venue_session_feedback_error",
                    event_data={
                        "venue_id": venue.id,
                        "session_id": session_id or None,
                        "error": f"openai: {exc}",
                    },
                )

    if not message:
        if VENUE_SESSION_WEBHOOK_URL:
            message = "Philosopher: the webhook responded, but no message text was returned."
        else:
            message = "Philosopher: no reflection available yet. Try again in a moment."

    return JsonResponse({"ok": True, "message": message})


@login_required
def amphitheatre_hub(request):
    """Hub experience for the Greek Amphitheatre venue."""
    user = request.user
    profile = user.profile

    venue_obj = Venue.objects.filter(name__iexact="Greek Amphitheatre").first()

    sessions = (
        AmphitheatreSession.objects.filter(user=user)
        .order_by("-created_at")
        .prefetch_related("exercise_records")
    )
    visits = sessions.count()
    next_visit = visits + 1
    next_plan = build_session_plan(
        visit_number=next_visit,
        last_prompt_lookup=_amphitheatre_last_prompt_lookup(user),
    )
    hint = _amphitheatre_hint_for_plan(next_plan)
    active_exists = AmphitheatreSession.objects.filter(
        user=user, status__in=["active", "draft"]
    ).exists()

    last_session = sessions.first()
    last_practice = None
    if last_session:
        last_practice = last_session.completed_at or last_session.created_at

    total_points = sum(session.total_points for session in sessions)

    context = {
        "hub": {
            "visits": visits,
            "streak": profile.current_streak,
            "last_practice": last_practice,
            "total_points": total_points,
            "has_active_session": active_exists,
            "hint": hint,
        },
        "next_plan": next_plan,
        "recent_reflections": _amphitheatre_reflection_feed(user),
        "venue": venue_obj,
    }

    return render(request, "myApp/amphitheatre_hub.html", context)


@login_required
def amphitheatre_session(request):
    """Render or resume an Amphitheatre practice session."""
    session, created = _ensure_amphitheatre_session(request.user)
    payload = _build_amphitheatre_payload(session)

    context = {
        "session_payload": payload,
        "ui_tokens": get_ui_tokens(),
        "profile": request.user.profile,
        "session_created": created,
    }
    return render(request, "myApp/amphitheatre_session.html", context)


@login_required
def amphitheatre_history(request):
    """Timeline of Amphitheatre sessions with quick replays."""
    sessions = (
        AmphitheatreSession.objects.filter(user=request.user)
        .order_by("-created_at")
        .prefetch_related("exercise_records")
    )
    timeline = []
    for session in sessions:
        timestamp = session.completed_at or session.created_at
        exercises = []
        for record in session.exercise_records.order_by("sequence_index"):
            exercises.append(
                {
                    "title": EXERCISE_TITLES.get(record.exercise_id, record.exercise_id),
                    "reflection_text": record.reflection_text,
                    "philosopher_response": record.philosopher_response,
                    "has_audio": record.has_audio,
                    "markers": record.markers or {},
                    "audio": record.audio_reference,
                }
            )
        timeline.append(
            {
                "session_id": str(session.session_id),
                "visit_number": session.visit_number,
                "status": session.status,
                "timestamp": timestamp,
                "points": session.total_points,
                "exercises": exercises,
            }
        )

    return render(
        request,
        "myApp/amphitheatre_history.html",
        {
            "timeline": timeline,
        },
    )


@login_required
def amphitheatre_settings(request):
    """Settings panel for Amphitheatre-specific preferences."""
    settings_state = {
        "language": request.session.get("amphitheatre_language", "en"),
        "available_languages": [
            {"id": "en", "label": "English"},
            {"id": "en_es", "label": "English + Español"},
        ],
        "accessibility": {
            "reduced_motion": request.session.get("amphitheatre_reduced_motion", False),
        },
        "audio": {
            "last_device": request.session.get("amphitheatre_last_device"),
            "diagnostics_status": request.session.get("amphitheatre_audio_status", "unknown"),
        },
    }
    return render(
        request,
        "myApp/amphitheatre_settings.html",
        {
            "settings_state": settings_state,
        },
    )


@login_required
@require_http_methods(["GET"])
def amphitheatre_session_state(request, session_id):
    """Return JSON payload for a session (used by polling refresh)."""
    session = get_object_or_404(
        AmphitheatreSession,
        session_id=session_id,
        user=request.user,
    )
    payload = _build_amphitheatre_payload(session)
    return JsonResponse({"ok": True, "data": payload})


@login_required
@require_http_methods(["POST"])
def amphitheatre_submit(request):
    """Persist an Amphitheatre exercise submission."""
    payload, error = _parse_request_json(request)
    if error:
        return error

    session_id = payload.get("session_id")
    exercise_id = payload.get("exercise_id")
    if not session_id or not exercise_id:
        return _json_error("session_id and exercise_id are required.")

    session = get_object_or_404(
        AmphitheatreSession,
        session_id=session_id,
        user=request.user,
    )
    record = get_object_or_404(
        AmphitheatreExerciseRecord,
        session=session,
        exercise_id=exercise_id,
    )

    selections = payload.get("selections") or {}
    reflection_text = (payload.get("reflection_text") or "").strip()
    markers = payload.get("markers") or {}
    audio_reference = payload.get("audio_ref") or ""
    state = payload.get("state") or "done"
    now = timezone.now()

    previous_score = (record.microcopy or {}).get("score", {})
    new_score = score_submission(exercise_id, reflection_text, markers)
    completion_delta = new_score["completion"] - int(previous_score.get("completion", 0))
    reflection_delta = new_score["reflection"] - int(previous_score.get("reflection", 0))

    session.completion_points = max(
        0, int(session.completion_points or 0) + completion_delta
    )
    session.reflection_points = max(
        0, int(session.reflection_points or 0) + reflection_delta
    )
    session.current_index = max(session.current_index, record.sequence_index + 1)
    metadata = session.metadata or {}
    metadata.update(
        {
            "last_submission": {
                "exercise_id": exercise_id,
                "timestamp": now.isoformat(),
            }
        }
    )
    session.metadata = metadata

    record.selections = selections
    record.reflection_text = reflection_text
    record.markers = markers
    record.audio_reference = audio_reference
    record.state = "done" if state == "done" else state
    record.philosopher_response = build_philosopher_response(
        exercise_id, selections, reflection_text, markers
    )
    record.completed_at = now
    microcopy = record.microcopy or {}
    microcopy["score"] = new_score
    microcopy["last_submit_ts"] = now.isoformat()
    record.microcopy = microcopy

    record.save(
        update_fields=[
            "selections",
            "reflection_text",
            "markers",
            "audio_reference",
            "state",
            "philosopher_response",
            "completed_at",
            "microcopy",
            "updated_at",
        ]
    )

    session.save(
        update_fields=[
            "completion_points",
            "reflection_points",
            "current_index",
            "metadata",
            "updated_at",
        ]
    )

    all_done = not session.exercise_records.exclude(state="done").exists()
    if all_done:
        session.mark_completed()
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type="amphitheatre_session_completed",
            event_data={
                "session_id": str(session.session_id),
                "visit_number": session.visit_number,
                "total_points": session.total_points,
            },
        )

    xp_delta = max(completion_delta, 0) + max(reflection_delta, 0)
    if xp_delta:
        profile = request.user.profile
        profile.total_xp += xp_delta
        profile.last_activity_date = now.date()
        profile.save(update_fields=["total_xp", "last_activity_date"])

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type="amphitheatre_exercise_submitted",
        event_data={
            "session_id": str(session.session_id),
            "exercise_id": exercise_id,
            "state": record.state,
            "score_delta": {
                "completion": completion_delta,
                "reflection": reflection_delta,
            },
        },
    )

    payload = _build_amphitheatre_payload(session)

    return JsonResponse(
        {
            "ok": True,
            "data": {
                "session": payload,
                "exercise_id": exercise_id,
                "philosopher_response": record.philosopher_response,
                "score": {
                    "total": payload["score"]["total"],
                    "completion": payload["score"]["completion"],
                    "reflection": payload["score"]["reflection"],
                    "delta": {
                        "completion": completion_delta,
                        "reflection": reflection_delta,
                    },
                },
                "completed": all_done,
                "microcopy": record.microcopy or {},
            },
        }
    )


def _decode_audio_payload(data_uri: str) -> bytes:
    if not data_uri:
        return b""
    if "," in data_uri:
        _, data = data_uri.split(",", 1)
    else:
        data = data_uri
    padding = 4 - (len(data) % 4)
    if padding and padding != 4:
        data = f"{data}{'=' * padding}"
    return base64.b64decode(data)


def _get_openai_client():
    key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if not key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=key)


@require_POST
@csrf_protect
def landing_chat_send(request):
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    if not message:
        return JsonResponse({"success": False, "response": "Please type a question."}, status=400)

    try:
        AnalyticsEvent.objects.create(
            event_type="landing_chat_message",
            event_data={
                "length": len(message),
                "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:160],
            },
        )
    except Exception:
        pass

    client = _get_openai_client()

    convo = [{"role": "system", "content": SYSTEM_PROMPT}]
    if not isinstance(history, list):
        history = []
    for turn in history[-6:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            convo.append({"role": role, "content": content})
    convo.append({"role": "user", "content": message})

    if client is None:
        q = message.lower()
        if "beta" in q:
            hint = "You can explore everything free during Beta."
        elif any(key in q for key in ("legacy", "lifetime", "€47")):
            hint = "Legacy Patron is a one-time €47 lifetime access with new simulations first."
        elif "price" in q or "pricing" in q or "$" in q:
            hint = "Right now it's free for Beta, or €47 for lifetime Legacy Patron."
        elif "investor" in q or "pitch" in q:
            hint = "We provide high-pressure investor and exec simulations with feedback."
        else:
            hint = "Ask me about Beta, Legacy Patron, pricing, or our simulations."

        return JsonResponse({
            "success": True,
            "response": f"Got it about '{message}'. {hint} If you need a direct link, tap Legacy Patron or Start Free."}
        )

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=convo,
            temperature=0.4,
            top_p=0.9,
            max_tokens=220,
        )
        text = (res.choices[0].message.content or "").strip()
        if not text:
            raise ValueError("Empty completion")
        return JsonResponse({"success": True, "response": text})
    except Exception:
        return JsonResponse({
            "success": True,
            "response": (
                f"I'm having trouble reaching the assistant right now, but here's the quick take on '{message}': "
                "• Free Beta access today • Lifetime Legacy Patron for €47 • Simulations for investor pitches, media, and leadership. "
                "Share more context and I'll point you to the right simulation track."
            ),
        })


@login_required
@require_http_methods(["POST"])
def amphitheatre_transcribe(request):
    """Accept an audio clip, transcribe it, and store lightweight analysis."""
    payload, error = _parse_request_json(request)
    if error:
        return error

    audio_b64 = payload.get("audio_b64")
    transcript_text = (payload.get("transcript") or "").strip()
    session_id = payload.get("session_id")
    exercise_id = payload.get("exercise_id")
    if not session_id or not exercise_id:
        return _json_error("session_id and exercise_id are required.")
    if not audio_b64 and not transcript_text:
        return _json_error("Provide audio_b64 or transcript.", code="missing_payload")

    session = get_object_or_404(
        AmphitheatreSession,
        session_id=session_id,
        user=request.user,
    )
    record = get_object_or_404(
        AmphitheatreExerciseRecord,
        session=session,
        exercise_id=exercise_id,
    )

    client = _get_openai_client()
    if not client:
        return _json_error("OpenAI API key not configured.", status=503, code="config_missing")

    if audio_b64 and not transcript_text:
        audio_bytes = _decode_audio_payload(audio_b64)
        if not audio_bytes:
            return _json_error("Audio payload could not be decoded.", code="invalid_audio")

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "amphitheatre_clip.webm"

        try:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
            )
            transcript_text = (transcription or "").strip()
        except Exception as exc:
            return _json_error(f"Transcription failed: {exc}", status=502, code="transcription_failed")

    analysis_text = ""
    if transcript_text:
        try:
            analysis_response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are the Philosopher observing Amphitheatre practice. "
                            "Offer a calm, encouraging two-sentence note about the voice clip. "
                            "In the second sentence, reflect on delivery aspects the speaker can notice (pace, pauses, tone). "
                            "Keep it supportive and non-judgemental."
                        ),
                    },
                    {
                        "role": "user",
                        "content": transcript_text,
                    },
                ],
            )
            analysis_text = (analysis_response.output_text or "").strip()
        except Exception:
            analysis_text = ""

    microcopy = record.microcopy or {}
    microcopy.update(
        {
            "transcript": transcript_text,
            "analysis": analysis_text,
        }
    )
    record.microcopy = microcopy
    record.save(update_fields=["microcopy", "updated_at"])

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type="amphitheatre_transcription_saved",
        event_data={
            "session_id": str(session.session_id),
            "exercise_id": exercise_id,
            "has_analysis": bool(analysis_text),
        },
    )

    return JsonResponse(
        {
            "ok": True,
            "data": {
                "transcript": transcript_text,
                "analysis": analysis_text,
            },
        }
    )


@login_required
@require_http_methods(["POST"])
def submit_exercise(request):
    """Submit exercise attempt"""
    data = json.loads(request.body)
    exercise_type = data.get('type')
    score = float(data.get('score', 0))
    is_correct = data.get('is_correct', False)
    knowledge_block_id = data.get('knowledge_block_id')
    user_response = data.get('response', {})
    
    profile = request.user.profile
    knowledge_block = None
    if knowledge_block_id:
        knowledge_block = get_object_or_404(KnowledgeBlock, id=knowledge_block_id)
    
    # Calculate XP with streak multiplier
    base_xp = 5 if is_correct else 2
    xp_earned = int(base_xp * profile.get_streak_multiplier())
    
    # Create attempt
    attempt = ExerciseAttempt.objects.create(
        user=request.user,
        knowledge_block=knowledge_block,
        exercise_type=exercise_type,
        score=score,
        is_correct=is_correct,
        xp_earned=xp_earned,
        user_response=user_response
    )
    
    # Award XP and coins
    profile.total_xp += xp_earned
    profile.coins += xp_earned // 2
    profile.save()
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='exercise_complete',
        event_data={
            'type': exercise_type,
            'score': score,
            'xp_earned': xp_earned
        }
    )
    
    return JsonResponse({
        'success': True,
        'xp_earned': xp_earned,
        'coins_earned': xp_earned // 2,
        'total_xp': profile.total_xp,
        'total_coins': profile.coins
    })


@login_required
@require_http_methods(["POST"])
def complete_venue(request, venue_id):
    """Mark venue entry as completed and award rewards"""
    venue = get_object_or_404(Venue, id=venue_id)
    entry = VenueEntry.objects.filter(
        user=request.user,
        venue=venue,
        completed=False
    ).first()
    
    if not entry:
        return JsonResponse({'success': False, 'error': 'No active entry found'}, status=400)
    
    profile = request.user.profile
    entry.completed = True
    entry.completed_at = timezone.now()
    entry.xp_earned = venue.xp_reward
    entry.coins_earned = venue.coin_reward
    entry.save()
    
    # Award rewards
    profile.total_xp += venue.xp_reward
    profile.coins += venue.coin_reward
    profile.save()
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='venue_completed',
        event_data={'venue_id': venue_id, 'venue_name': venue.name}
    )
    
    return JsonResponse({
        'success': True,
        'xp_earned': venue.xp_reward,
        'coins_earned': venue.coin_reward,
        'total_xp': profile.total_xp,
        'total_coins': profile.coins
    })

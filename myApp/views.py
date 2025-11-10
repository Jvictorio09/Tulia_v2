from functools import lru_cache
from pathlib import Path
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomUserCreationForm
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
import json
import random
import requests
from datetime import date, datetime, timedelta

from .models import (
    UserProfile, Level, Module, KnowledgeBlock, Lesson,
    ExerciseAttempt, MilestoneAttempt, District, Venue,
    VenueTaskSheet, VenueEntry, DailyQuest, UserProgress,
    AnalyticsEvent, ExerciseSubmission, LessonSessionContext,
    StakesMap, TelemetryEvent, UserVenueUnlock
)
from .lesson_engine import LessonEngine, LessonContext, SeedLoader, SeedVersionError
from .lesson_engine.contracts_registry import build_default_registry


MODULE_A_SEED_PATHS = [
    "moduleA/scenarios.moduleA.json",
    "moduleA/pic_sets.json",
    "moduleA/actions_control_shift.json",
    "moduleA/reframe_mantras.json",
    "moduleA/load_examples.json",
    "moduleA/d2_keypoint_sets.json",
    "moduleA/lever_cards.json",
    "moduleA/stakes_map_presets.json",
]
MODULE_A_FLOW_PATH = "moduleA/moduleA.flow.json"


@lru_cache(maxsize=1)
def get_module_a_bundle():
    loader = SeedLoader()
    packs, flow = loader.resolve_module_seeds(
        "A",
        MODULE_A_SEED_PATHS,
        MODULE_A_FLOW_PATH,
    )
    return packs, flow


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
    }
    return render(request, 'myApp/module_learn.html', context)


@login_required
def lesson_runner(request, module_code):
    """Module A lesson runner using the new card engine."""
    profile = request.user.profile
    level_1 = Level.objects.get(number=1)
    module = get_object_or_404(Module, level=level_1, code=module_code.upper())

    status, _ = _module_status_for_user(request.user, module)
    if status == "locked":
        return redirect('district_overview', district_number=module.level.number)

    progress = _get_module_progress(request.user, module)
    if not progress.started:
        return redirect('module_learn', module_code=module.code)

    session_ctx, _ = LessonSessionContext.objects.get_or_create(
        user=request.user,
        module=module,
        defaults={
            'loop_index': progress.loop_index,
        },
    )

    try:
        seed_packs, flow = get_module_a_bundle()
    except SeedVersionError as exc:
        return render(
            request,
            'myApp/lesson_runner.html',
            {
                'module': module,
                'profile': profile,
                'seed_error': str(exc),
                'lesson_cards': [],
                'session_state': {},
                'flow_meta': {},
                'progress_payload': {},
                'ui_tokens': get_ui_tokens(),
            },
        )

    registry = build_default_registry()
    session_state = {
        "current_scenario_ref": session_ctx.current_scenario_ref,
        "last_lever_choice": session_ctx.last_lever_choice or progress.lever_choice,
        "last_stakes_score": float(session_ctx.last_stakes_score)
        if session_ctx.last_stakes_score is not None else None,
        "loop_index": session_ctx.loop_index or progress.loop_index,
        "cooldowns": session_ctx.cooldowns or {},
    }

    user_state = {
        "ab_variant": profile.ab_variant,
        "loop_index": progress.loop_index,
        "pass_type": progress.pass_type,
    }

    engine = LessonEngine(registry, seed_packs, flow)
    lesson_context = LessonContext(
        module_code=module.code,
        user_state=user_state,
        session_context=session_state,
    )
    cards = engine.build_session_stack(lesson_context)

    # Persist mutated session context
    session_ctx.cooldowns = lesson_context.session_context.get("cooldowns", {})
    session_ctx.loop_index = lesson_context.session_context.get("loop_index", progress.loop_index)
    session_ctx.save(update_fields=['cooldowns', 'loop_index', 'updated_at'])

    progress_payload = {
        "loop_index": progress.loop_index,
        "pass_type": progress.pass_type,
    }

    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='module_exercises_view',
        event_data={'module': module.code}
    )

    context = {
        'module': module,
        'profile': profile,
        'flow_meta': {
            'name': flow.name,
            'version': flow.version,
            'scoring': flow.scoring,
        },
        'lesson_cards': cards,
        'session_state': lesson_context.session_context,
        'progress_payload': progress_payload,
        'ui_tokens': get_ui_tokens(),
    }

    return render(request, 'myApp/lesson_runner.html', context)


def _compute_scores(scoring_conf, metrics):
    completion_weight = int(scoring_conf.get('completion', 40))
    accuracy_weight = int(scoring_conf.get('accuracy', 30))
    reflection_weight = int(scoring_conf.get('reflection', 30))

    completion_score = completion_weight if metrics.get('completion', True) else 0
    accuracy_score = 0
    accuracy_ratio = metrics.get('accuracy')
    if isinstance(accuracy_ratio, (int, float)):
        accuracy_score = int(max(0.0, min(1.0, float(accuracy_ratio))) * accuracy_weight)
    reflection_score = reflection_weight if metrics.get('reflection') else 0
    total_score = completion_score + accuracy_score + reflection_score
    return completion_score, accuracy_score, reflection_score, total_score


def _update_session_context_for_template(session_state, template_id, payload, exercise_id, card_key):
    completed = session_state.setdefault("completed_cards", [])
    if card_key and card_key not in completed:
        completed.append(card_key)
    if template_id == "PersonalScenarioCapture":
        scenario_ref = payload.get("scenario_ref") or f"scn_{uuid.uuid4().hex[:10]}"
        session_state["current_scenario_ref"] = scenario_ref
        scenarios = session_state.setdefault("scenarios", {})
        scenarios[scenario_ref] = {
            "text": payload.get("situation_text", ""),
            "pressure": payload.get("pressure"),
            "visibility": payload.get("visibility"),
            "irreversibility": payload.get("irreversibility"),
            "reflection": payload.get("reflection"),
        }
    elif template_id == "TernaryRatingCard":
        p = float(payload.get("P", 0) or 0)
        i = float(payload.get("I", 0) or 0)
        control = float(payload.get("C", 1) or 1)
        if control <= 0:
            control = 1
        stakes_score = round((p + i) / control, 2)
        session_state["last_stakes_score"] = stakes_score
    elif template_id == "LeverSelector3P":
        lever = payload.get("selected_lever")
        if lever:
            session_state["last_lever_choice"] = lever
    elif template_id == "StakesMapBuilder":
        session_state["last_stakes_map"] = {
            "pressure_points": payload.get("pressure_points", []),
            "trigger": payload.get("trigger"),
            "lever": payload.get("lever"),
            "action_step": payload.get("action_step"),
            "situation": payload.get("situation"),
        }
    return session_state


@login_required
@require_http_methods(["POST"])
def lesson_card_submit(request):
    data, error = _parse_request_json(request)
    if error:
        return error

    module_code = data.get("module_code")
    card = data.get("card") or {}
    payload = data.get("payload") or {}
    metrics = data.get("metrics") or {}
    if not module_code:
        return _json_error("module_code is required", code="missing_module")
    template_id = card.get("template_id")
    exercise_id = card.get("exercise_id")
    if not template_id or not exercise_id:
        return _json_error("template_id and exercise_id are required.", code="missing_card_meta")
    card_key = card.get("card_key") or f"{exercise_id}::0"

    level_1 = Level.objects.get(number=1)
    module = get_object_or_404(Module, level=level_1, code=module_code.upper())
    progress, _ = UserProgress.objects.get_or_create(user=request.user, module=module)
    session_ctx, _ = LessonSessionContext.objects.get_or_create(
        user=request.user,
        module=module,
        defaults={
            'loop_index': progress.loop_index,
        },
    )

    try:
        seed_packs, flow = get_module_a_bundle()
    except SeedVersionError as exc:
        return _json_error(str(exc), code="seed_version_error")

    registry = build_default_registry()

    session_state = {
        "current_scenario_ref": session_ctx.current_scenario_ref,
        "last_lever_choice": session_ctx.last_lever_choice or progress.lever_choice,
        "last_stakes_score": float(session_ctx.last_stakes_score)
        if session_ctx.last_stakes_score is not None else None,
        "loop_index": session_ctx.loop_index or progress.loop_index,
        "cooldowns": session_ctx.cooldowns or {},
    }
    session_state.update(session_ctx.data or {})

    payload["card_key"] = card_key

    session_state = _update_session_context_for_template(
        session_state,
        template_id,
        payload,
        exercise_id=exercise_id,
        card_key=card_key,
    )

    completion_score, accuracy_score, reflection_score, total_score = _compute_scores(flow.scoring, metrics)

    duration_ms = int(data.get("time_on_card") or 0)
    client_ts = _parse_client_ts(data.get("client_ts"))

    ExerciseSubmission.objects.create(
        user=request.user,
        module=module,
        knowledge_block=progress.current_knowledge_block,
        loop_index=session_state.get("loop_index", progress.loop_index),
        pass_type=progress.pass_type,
        stage_key=template_id.lower(),
        exercise_id=exercise_id,
        template_id=template_id,
        payload_version=flow.version,
        payload=payload,
        scores=metrics.get("scores") or {},
        completion_score=completion_score,
        accuracy_score=accuracy_score,
        reflection_score=reflection_score,
        total_score=total_score,
        duration_ms=duration_ms,
        ab_variant=request.user.profile.ab_variant,
        client_ts=client_ts,
    )

    if template_id == "StakesMapBuilder":
        map_payload = session_state.get("last_stakes_map", {})
        if map_payload:
            StakesMap.objects.create(
                user=request.user,
                module=module,
                scenario_ref=session_state.get("current_scenario_ref", ""),
                situation_text=map_payload.get("situation", ""),
                pressure_points=map_payload.get("pressure_points", []),
                trigger=map_payload.get("trigger", ""),
                lever=map_payload.get("lever", ""),
                action_step=map_payload.get("action_step", ""),
            )

    session_ctx.current_scenario_ref = session_state.get("current_scenario_ref", "") or ""
    session_ctx.last_lever_choice = session_state.get("last_lever_choice") or ""
    session_ctx.last_stakes_score = session_state.get("last_stakes_score")
    session_ctx.cooldowns = session_state.get("cooldowns", {})
    session_ctx.loop_index = session_state.get("loop_index", progress.loop_index)
    session_ctx.data = {k: v for k, v in session_state.items() if k not in {"current_scenario_ref", "last_lever_choice", "last_stakes_score", "cooldowns", "loop_index"}}
    session_ctx.save()

    progress.last_activity = timezone.now()
    progress.session_state = session_state
    progress.save(update_fields=['last_activity', 'session_state'])

    TelemetryEvent.objects.create(
        user=request.user,
        module_code=module.code,
        name=f"{template_id}.submitted",
        properties_json={
            "exercise_id": exercise_id,
            "metrics": metrics,
            "duration_ms": duration_ms,
        },
        ab_variant=request.user.profile.ab_variant,
    )

    user_state = {
        "ab_variant": request.user.profile.ab_variant,
        "loop_index": session_state.get("loop_index", progress.loop_index),
        "pass_type": progress.pass_type,
    }

    engine = LessonEngine(registry, seed_packs, flow)
    lesson_context = LessonContext(
        module_code=module.code,
        user_state=user_state,
        session_context=session_state,
    )
    cards = engine.build_session_stack(lesson_context)

    session_ctx.cooldowns = lesson_context.session_context.get("cooldowns", {})
    session_ctx.loop_index = lesson_context.session_context.get("loop_index", progress.loop_index)
    session_ctx.save(update_fields=['cooldowns', 'loop_index', 'updated_at'])

    return JsonResponse({
        "ok": True,
        "cards": cards,
        "session_state": lesson_context.session_context,
        "scores": {
            "completion": completion_score,
            "accuracy": accuracy_score,
            "reflection": reflection_score,
            "total": total_score,
        },
    })


@login_required
@require_http_methods(["POST"])
def lesson_prime_submit(request):
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
    valid, error_resp = _validate_stage(progress, 'prime')
    if not valid:
        return error_resp
    focus_lever = data.get('focus_lever')
    lever_options = {choice[0] for choice in UserProgress.LEVER_CHOICES}
    if focus_lever and focus_lever not in lever_options:
        return _json_error("Invalid focus lever.", code='invalid_lever')
    intention = (data.get('intention') or "").strip()
    payload = {
        "intention": intention,
        "focus_lever": focus_lever,
    }
    client_ts = _parse_client_ts(data.get('client_ts'))
    _create_submission(
        request.user,
        module,
        block,
        progress,
        'prime',
        payload,
        client_ts=client_ts,
        lever_choice=focus_lever,
    )
    if not progress.lever_choice and focus_lever:
        progress.lever_choice = focus_lever
    _append_meta_history(progress, 'prime', payload)
    next_stage = _compute_next_stage(progress, 'prime')
    progress.last_activity = timezone.now()
    progress.save()
    return _build_submission_response(progress, next_stage)


@login_required
@require_http_methods(["POST"])
def lesson_teach_submit(request):
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
    data, error = _parse_request_json(request)
    if error:
        return error
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

    if not _user_has_venue_access(request.user, venue):
        required_module = _module_code_for_venue(venue)
        if required_module:
            messages.info(request, f"Complete Module {required_module} to unlock {venue.name}.")
        else:
            messages.info(request, f"{venue.name} unlocks after completing this district's modules.")
        return redirect('district_venues', district_number=venue.district.number)
    
    # Check if user has enough tickets
    if profile.tickets < venue.ticket_cost:
        messages.info(request, "You need more tickets to enter this venue.")
        return redirect('district_venues', district_number=venue.district.number)
    
    # Get or create entry
    entry, created = VenueEntry.objects.get_or_create(
        user=request.user,
        venue=venue,
        completed=False,
        defaults={'tickets_spent': venue.ticket_cost}
    )
    
    if created:
        profile.tickets -= venue.ticket_cost
        profile.save()
        
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='venue_entered',
            event_data={'venue_id': venue_id, 'venue_name': venue.name}
        )
    
    task_sheets = VenueTaskSheet.objects.filter(venue=venue).order_by('order')
    
    context = {
        'venue': venue,
        'entry': entry,
        'task_sheets': task_sheets,
        'profile': profile,
    }
    
    return render(request, 'myApp/district_venue.html', context)


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

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
import json
import random
import requests
from datetime import date, timedelta

from .models import (
    UserProfile, Level, Module, KnowledgeBlock, Lesson,
    ExerciseAttempt, MilestoneAttempt, District, Venue,
    VenueTaskSheet, VenueEntry, DailyQuest, UserProgress, AnalyticsEvent
)


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
    
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        # Assign A/B variant if not set
        if not profile.ab_variant:
            profile.ab_variant = random.choice(['A', 'B'])
            profile.save()
        
        # Check if onboarding is needed
        if not profile.onboarding_completed:
            return redirect('onboarding')
        
        # Get user progress
        try:
            level_1 = Level.objects.get(number=1)
            modules = Module.objects.filter(level=level_1).order_by('order')
        except Level.DoesNotExist:
            # If Level 1 doesn't exist, show a message
            return render(request, 'myApp/home.html', {
                'profile': profile,
                'variant': profile.ab_variant,
                'error': 'Level 1 not configured. Please run migrations and seed data.'
            })
        progress_data = {}
        for module in modules:
            progress, _ = UserProgress.objects.get_or_create(
                user=request.user,
                module=module
            )
            progress_data[module.code] = progress
        
        # Check if all modules completed
        all_modules_complete = all(p.completed for p in progress_data.values())
        milestone_passed = MilestoneAttempt.objects.filter(
            user=request.user,
            level=level_1,
            pass_bool=True
        ).exists()
        
        # Get or create today's daily quest
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
        
        # Get district if unlocked
        district_1 = None
        if profile.district_1_unlocked:
            try:
                district_1 = District.objects.get(number=1)
            except District.DoesNotExist:
                pass
        
        context = {
            'profile': profile,
            'modules': modules,
            'progress_data': progress_data,
            'all_modules_complete': all_modules_complete,
            'milestone_passed': milestone_passed,
            'daily_quest': daily_quest,
            'district_1': district_1,
            'variant': profile.ab_variant,
        }
        
        # Track analytics
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='home_view',
            event_data={'variant': profile.ab_variant}
        )
        
        return render(request, 'myApp/home.html', context)
    else:
        return redirect('login')


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
def lesson_runner(request, module_code):
    """Main lesson runner with Teach/Drill/Review tabs"""
    profile = request.user.profile
    level_1 = Level.objects.get(number=1)
    module = get_object_or_404(Module, level=level_1, code=module_code.upper())
    
    # Get or create progress
    progress, _ = UserProgress.objects.get_or_create(
        user=request.user,
        module=module
    )
    
    if not progress.started:
        progress.started = True
        progress.last_activity = timezone.now()
        progress.save()
        
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='lesson_start',
            event_data={'module': module.code}
        )
    
    # Get current knowledge block (or first one)
    current_block = progress.current_knowledge_block
    if not current_block:
        current_block = KnowledgeBlock.objects.filter(module=module).first()
        if current_block:
            progress.current_knowledge_block = current_block
            progress.save()
    
    # Ensure citations is always a list (handle JSONField)
    if current_block and current_block.citations:
        if not isinstance(current_block.citations, list):
            current_block.citations = list(current_block.citations) if current_block.citations else []
    elif current_block:
        current_block.citations = []
    
    # Get all knowledge blocks for left rail
    knowledge_blocks = KnowledgeBlock.objects.filter(module=module).order_by('order')
    
    context = {
        'module': module,
        'progress': progress,
        'current_block': current_block,
        'knowledge_blocks': knowledge_blocks,
        'profile': profile,
    }
    
    return render(request, 'myApp/lesson_runner.html', context)


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
def district_map(request, district_number):
    """District map view"""
    try:
        district = District.objects.get(number=district_number)
    except District.DoesNotExist:
        # If district doesn't exist, redirect to home with message
        from django.contrib import messages
        messages.info(request, f'District {district_number} is not available yet. Please run: python manage.py seed_data')
        return redirect('home')
    
    profile = request.user.profile
    
    if district_number == 1 and not profile.district_1_unlocked:
        return redirect('home')
    
    venues = Venue.objects.filter(district=district).order_by('order')
    
    # Get user's venue entries
    venue_entries = {}
    for venue in venues:
        entry = VenueEntry.objects.filter(
            user=request.user,
            venue=venue,
            completed=False
        ).first()
        venue_entries[venue.id] = entry
    
    # Track analytics
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='district_view',
        event_data={'district': district_number}
    )
    
    context = {
        'district': district,
        'venues': venues,
        'venue_entries': venue_entries,
        'profile': profile,
    }
    
    return render(request, 'myApp/district_detail.html', context)


@login_required
def venue_detail(request, venue_id):
    """Venue detail with task sheets"""
    venue = get_object_or_404(Venue, id=venue_id)
    profile = request.user.profile
    
    # Check if user has enough tickets
    if profile.tickets < venue.ticket_cost:
        return redirect('district_map', district_number=venue.district.number)
    
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

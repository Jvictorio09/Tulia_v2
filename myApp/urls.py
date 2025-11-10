from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/signup/', views.signup_view, name='signup'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('module/<str:module_code>/learn/', views.module_learn, name='module_learn'),
    path('module/<str:module_code>/exercises/', views.lesson_runner, name='module_exercises'),
    path('milestone/<int:level_number>/', views.milestone, name='milestone'),
    path('milestone/<int:level_number>/submit/', views.milestone_submit, name='milestone_submit'),
    path('district/<int:district_number>/', views.district_overview, name='district_overview'),
    path('district/<int:district_number>/venues/', views.district_venues, name='district_venues'),
    path('district/venue/<int:venue_id>/', views.venue_detail, name='venue_detail'),
    
    # AI webhook endpoints
    path('ai/lesson/orchestrate/', views.ai_lesson_orchestrate, name='ai_lesson_orchestrate'),
    path('ai/coach/respond/', views.ai_coach_respond, name='ai_coach_respond'),
    
    # AI Chat
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('ai-chat/send/', views.ai_chat_send, name='ai_chat_send'),
    
    # Exercise submission
    path('api/exercise/submit/', views.submit_exercise, name='submit_exercise'),
    path('api/venue/<int:venue_id>/complete/', views.complete_venue, name='complete_venue'),
    
    # Lesson runner stage endpoints
    path('api/lessons/prime/submit/', views.lesson_prime_submit, name='lesson_prime_submit'),
    path('api/lessons/teach/submit/', views.lesson_teach_submit, name='lesson_teach_submit'),
    path('api/lessons/diagnose/submit/', views.lesson_diagnose_submit, name='lesson_diagnose_submit'),
    path('api/lessons/control-shift/submit/', views.lesson_control_shift_submit, name='lesson_control_shift_submit'),
    path('api/lessons/perform/text/submit/', views.lesson_perform_text_submit, name='lesson_perform_text_submit'),
    path('api/lessons/perform/voice/submit/', views.lesson_perform_voice_submit, name='lesson_perform_voice_submit'),
    path('api/lessons/review/submit/', views.lesson_review_submit, name='lesson_review_submit'),
    path('api/lessons/transfer/submit/', views.lesson_transfer_submit, name='lesson_transfer_submit'),
    path('api/lessons/card/submit/', views.lesson_card_submit, name='lesson_card_submit'),
    path('api/lessons/spacing/schedule/', views.lesson_spacing_schedule, name='lesson_spacing_schedule'),
]


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
    path('module/<str:module_code>/guided/', views.module_guided, name='module_guided'),
    path('milestone/<int:level_number>/', views.milestone, name='milestone'),
    path('milestone/<int:level_number>/submit/', views.milestone_submit, name='milestone_submit'),
    path('district/<int:district_number>/', views.district_overview, name='district_overview'),
    path('district/<int:district_number>/venues/', views.district_venues, name='district_venues'),
    path('district/venue/<int:venue_id>/', views.venue_detail, name='venue_detail'),
    path('district/venue/<int:venue_id>/session/', views.venue_session, name='venue_session'),
    path('amphitheatre/', views.amphitheatre_hub, name='amphitheatre_hub'),
    path('amphitheatre/session/', views.amphitheatre_session, name='amphitheatre_session'),
    path('amphitheatre/history/', views.amphitheatre_history, name='amphitheatre_history'),
    path('amphitheatre/settings/', views.amphitheatre_settings, name='amphitheatre_settings'),
    
    # AI webhook endpoints
    path('ai/lesson/orchestrate/', views.ai_lesson_orchestrate, name='ai_lesson_orchestrate'),
    path('ai/coach/respond/', views.ai_coach_respond, name='ai_coach_respond'),
    
    # AI Chat
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('ai-chat/send/', views.ai_chat_send, name='ai_chat_send'),
    
    # Exercise submission
    path('api/exercise/submit/', views.submit_exercise, name='submit_exercise'),
    path('api/venue/<int:venue_id>/complete/', views.complete_venue, name='complete_venue'),
    path('api/amphitheatre/session/<uuid:session_id>/', views.amphitheatre_session_state, name='amphitheatre_session_state'),
    path('api/amphitheatre/submit/', views.amphitheatre_submit, name='amphitheatre_submit'),
    path('api/amphitheatre/transcribe/', views.amphitheatre_transcribe, name='amphitheatre_transcribe'),
    path('api/venue/<int:venue_id>/session/feedback/', views.venue_session_feedback, name='venue_session_feedback'),
    
    # Guided lesson endpoints
    path('lesson/start/', views.lesson_start, name='lesson_start'),
    path('lesson/answer/', views.lesson_answer, name='lesson_answer'),
    path('lesson/resume/', views.lesson_resume, name='lesson_resume'),
    path('api/lesson/start/', views.lesson_start, name='lesson_start_legacy'),
    path('api/lesson/answer/', views.lesson_answer, name='lesson_answer_legacy'),
    path('api/lesson/resume/', views.lesson_resume, name='lesson_resume_legacy'),
]


from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/signup/', views.signup_view, name='signup'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('lesson/<str:module_code>/', views.lesson_runner, name='lesson_runner'),
    path('milestone/<int:level_number>/', views.milestone, name='milestone'),
    path('milestone/<int:level_number>/submit/', views.milestone_submit, name='milestone_submit'),
    path('district/<int:district_number>/', views.district_map, name='district_map'),
    path('venue/<int:venue_id>/', views.venue_detail, name='venue_detail'),
    
    # AI webhook endpoints
    path('ai/lesson/orchestrate/', views.ai_lesson_orchestrate, name='ai_lesson_orchestrate'),
    path('ai/coach/respond/', views.ai_coach_respond, name='ai_coach_respond'),
    
    # AI Chat
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('ai-chat/send/', views.ai_chat_send, name='ai_chat_send'),
    
    # Exercise submission
    path('api/exercise/submit/', views.submit_exercise, name='submit_exercise'),
    path('api/venue/<int:venue_id>/complete/', views.complete_venue, name='complete_venue'),
]


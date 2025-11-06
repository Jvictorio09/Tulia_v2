from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile, Level, Module, KnowledgeBlock, Lesson,
    ExerciseAttempt, MilestoneAttempt, District, Venue,
    VenueTaskSheet, VenueEntry, DailyQuest, UserProgress, AnalyticsEvent
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_level', 'total_xp', 'current_streak', 'coins', 'tickets', 'onboarding_completed']
    list_filter = ['onboarding_completed', 'district_1_unlocked', 'ab_variant']
    search_fields = ['user__username', 'user__email']


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'milestone_threshold']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'level', 'order', 'xp_reward']
    list_filter = ['level']
    ordering = ['level', 'order']


@admin.register(KnowledgeBlock)
class KnowledgeBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'order']
    list_filter = ['module']
    search_fields = ['title', 'summary']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'order', 'xp_reward']
    list_filter = ['module']
    ordering = ['module', 'order']


@admin.register(ExerciseAttempt)
class ExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'exercise_type', 'score', 'is_correct', 'xp_earned', 'created_at']
    list_filter = ['exercise_type', 'is_correct', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']


@admin.register(MilestoneAttempt)
class MilestoneAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'overall_score', 'pass_bool', 'created_at']
    list_filter = ['level', 'pass_bool', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['number', 'name']


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'district', 'ticket_cost', 'xp_reward', 'order']
    list_filter = ['district']
    ordering = ['district', 'order']


@admin.register(VenueTaskSheet)
class VenueTaskSheetAdmin(admin.ModelAdmin):
    list_display = ['title', 'venue', 'order']
    list_filter = ['venue']


@admin.register(VenueEntry)
class VenueEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'venue', 'tickets_spent', 'completed', 'entered_at']
    list_filter = ['completed', 'entered_at']
    search_fields = ['user__username']


@admin.register(DailyQuest)
class DailyQuestAdmin(admin.ModelAdmin):
    list_display = ['user', 'quest_type', 'date', 'completed']
    list_filter = ['quest_type', 'completed', 'date']
    search_fields = ['user__username']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'module', 'started', 'completed', 'last_activity']
    list_filter = ['started', 'completed']
    search_fields = ['user__username']


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'user', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['user__username', 'event_type']
    readonly_fields = ['created_at']

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import json


class UserProfile(models.Model):
    """Extended user profile with persona and progress data"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Onboarding persona data
    role = models.CharField(max_length=200, blank=True)
    typical_audience = models.CharField(max_length=200, blank=True)
    main_goal = models.CharField(max_length=200, blank=True)
    comfort_under_pressure = models.CharField(max_length=100, blank=True)
    time_pressure_profile = models.CharField(max_length=100, blank=True)
    preferred_practice_time = models.CharField(max_length=100, blank=True)
    daily_goal_minutes = models.IntegerField(default=15, validators=[MinValueValidator(1)])
    
    # Persona summary (AI-generated from onboarding)
    persona_summary = models.TextField(blank=True)
    
    # Progress tracking
    current_level = models.IntegerField(default=1)
    total_xp = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Economy
    coins = models.IntegerField(default=0)
    tickets = models.IntegerField(default=0)
    
    # A/B testing
    ab_variant = models.CharField(max_length=1, default='A', choices=[('A', 'Dashboard'), ('B', 'Map-first')])
    
    # Onboarding completion
    onboarding_completed = models.BooleanField(default=False)
    
    # District unlocks
    district_1_unlocked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_streak_multiplier(self):
        """Calculate XP multiplier based on streak (max 2.0)"""
        return min(1.0 + (self.current_streak * 0.1), 2.0)


class Level(models.Model):
    """Learning levels (currently only Level 1)"""
    number = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    milestone_threshold = models.FloatField(default=70.0)  # Minimum score to pass
    
    def __str__(self):
        return f"Level {self.number}: {self.name}"


class Module(models.Model):
    """Modules within a level (A, B, C, D for Level 1)"""
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='modules')
    code = models.CharField(max_length=10)  # A, B, C, D
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField()
    xp_reward = models.IntegerField(default=50)
    
    class Meta:
        unique_together = ['level', 'code']
        ordering = ['level', 'order']
    
    def __str__(self):
        return f"{self.level} - Module {self.code}: {self.name}"


class KnowledgeBlock(models.Model):
    """RAG fuel - knowledge chunks for AI teaching"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='knowledge_blocks')
    title = models.CharField(max_length=200)
    summary = models.TextField()  # ~120 words
    tags = models.JSONField(default=list)  # List of tags
    exercise_seeds = models.JSONField(default=list)  # Exercise templates
    citations = models.JSONField(default=list)  # Source references
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['module', 'order']
    
    def __str__(self):
        return f"{self.module.code} - {self.title}"


class Lesson(models.Model):
    """Lesson metadata (ultra-thin, AI orchestrates content)"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    name = models.CharField(max_length=200)
    order = models.IntegerField()
    xp_reward = models.IntegerField(default=10)
    
    class Meta:
        ordering = ['module', 'order']
    
    def __str__(self):
        return f"{self.module.code} - {self.name}"


class ExerciseAttempt(models.Model):
    """User attempts at exercises"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_attempts')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True)
    knowledge_block = models.ForeignKey(KnowledgeBlock, on_delete=models.CASCADE, null=True, blank=True)
    
    exercise_type = models.CharField(max_length=50)  # select, match, rewrite, speak, scenario
    score = models.FloatField(default=0.0)  # 0.0 to 1.0
    is_correct = models.BooleanField(default=False)
    xp_earned = models.IntegerField(default=0)
    ai_feedback = models.TextField(blank=True)
    concept_refs = models.JSONField(default=list)  # References to knowledge blocks
    
    # Response data
    user_response = models.JSONField(default=dict)  # Store user's answer
    correct_answer = models.JSONField(default=dict)  # Store correct answer
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.exercise_type} - {self.score:.0%}"


class MilestoneAttempt(models.Model):
    """Milestone assessment attempts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='milestone_attempts')
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='milestone_attempts')
    
    audio_url = models.URLField(blank=True)  # Signed URL to audio recording
    transcript = models.TextField(blank=True)
    
    overall_score = models.FloatField(default=0.0)  # 0.0 to 100.0
    rubric_scores = models.JSONField(default=dict)  # {clarity: 75, structure: 80, presence: 70, influence: 65}
    pass_bool = models.BooleanField(default=False)
    coaching_note = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.level} - {self.overall_score:.1f}%"


class District(models.Model):
    """Districts (currently only District-1)"""
    number = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unlock_requirement = models.TextField(blank=True)  # e.g., "Complete Level 1 + Milestone ≥70%"
    
    def __str__(self):
        return f"District {self.number}: {self.name}"


class Venue(models.Model):
    """Venues within districts"""
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='venues')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ticket_cost = models.IntegerField(default=1)
    xp_reward = models.IntegerField(default=20)
    coin_reward = models.IntegerField(default=10)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['district', 'order']
    
    def __str__(self):
        return f"{self.district} - {self.name}"


class VenueTaskSheet(models.Model):
    """Task sheets for venues (curated micro-exercises)"""
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='task_sheets')
    title = models.CharField(max_length=200)
    description = models.TextField()
    exercises = models.JSONField(default=list)  # List of exercise configurations
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['venue', 'order']
    
    def __str__(self):
        return f"{self.venue} - {self.title}"


class VenueEntry(models.Model):
    """User entries into venues"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='venue_entries')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='entries')
    task_sheet = models.ForeignKey(VenueTaskSheet, on_delete=models.CASCADE, null=True, blank=True)
    tickets_spent = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    xp_earned = models.IntegerField(default=0)
    coins_earned = models.IntegerField(default=0)
    
    entered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-entered_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.venue}"


class DailyQuest(models.Model):
    """Daily quests for user engagement"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_quests')
    quest_type = models.CharField(max_length=50, default='complete_drill')
    description = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    xp_reward = models.IntegerField(default=10)
    coin_reward = models.IntegerField(default=5)
    
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'date', 'quest_type']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.quest_type} - {self.date}"


class UserProgress(models.Model):
    """Track user progress through modules and lessons"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='user_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True)
    PASS_CHOICES = [
        ('main', 'Main'),
        ('return', 'Return'),
    ]
    LEVER_CHOICES = [
        ('preparation', 'Preparation'),
        ('presence', 'Presence'),
        ('perspective', 'Perspective'),
    ]
    LOAD_CHOICES = [
        ('emotional', 'Emotional'),
        ('cognitive', 'Cognitive'),
        ('mixed', 'Mixed'),
        ('unknown', 'Unknown'),
    ]
    stage_key = models.CharField(max_length=32, default='prime')
    loop_index = models.IntegerField(default=0)
    pass_type = models.CharField(max_length=8, choices=PASS_CHOICES, default='main')
    sequence_version = models.CharField(max_length=12, default='v1.0')
    lever_choice = models.CharField(max_length=16, choices=LEVER_CHOICES, blank=True)
    pic_pressure = models.SmallIntegerField(default=0)
    pic_visibility = models.SmallIntegerField(default=0)
    pic_irreversibility = models.SmallIntegerField(default=0)
    pic_control = models.SmallIntegerField(default=0)
    load_label = models.CharField(max_length=16, choices=LOAD_CHOICES, default='unknown')
    return_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    
    started = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    current_knowledge_block = models.ForeignKey(KnowledgeBlock, on_delete=models.SET_NULL, null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Track checkpoint progress
    checkpoints_passed = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'module']
        ordering = ['module__order']
        indexes = [
            models.Index(fields=['user', 'current_knowledge_block', 'loop_index', 'pass_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.module}"


class ExerciseSubmission(models.Model):
    """Stage submission records for lesson runner loops"""
    STAGE_CHOICES = [
        ('prime', 'Prime'),
        ('teach', 'Teach'),
        ('diagnose', 'Diagnose'),
        ('control_shift', 'Control Shift'),
        ('perform_text', 'Perform Text'),
        ('perform_voice', 'Perform Voice'),
        ('review', 'Review'),
        ('transfer', 'Transfer'),
    ]
    PASS_CHOICES = [
        ('main', 'Main'),
        ('return', 'Return'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_submissions')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lesson_submissions')
    knowledge_block = models.ForeignKey(KnowledgeBlock, on_delete=models.CASCADE, related_name='lesson_submissions')
    loop_index = models.IntegerField(default=0)
    pass_type = models.CharField(max_length=8, choices=PASS_CHOICES, default='main')
    stage_key = models.CharField(max_length=32, choices=STAGE_CHOICES)
    lever_choice = models.CharField(max_length=16, blank=True)
    payload = models.JSONField(default=dict)
    scores = models.JSONField(default=dict, blank=True)
    duration_ms = models.IntegerField(default=0)
    client_ts = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'module', 'knowledge_block', 'loop_index', 'stage_key']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.stage_key} - loop {self.loop_index}"


class AnalyticsEvent(models.Model):
    """Analytics event tracking"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics_events', null=True, blank=True)
    event_type = models.CharField(max_length=100)  # lesson_start, lesson_complete, coach_tab_click, etc.
    event_data = models.JSONField(default=dict)
    session_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"

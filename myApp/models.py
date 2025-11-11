from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import json
import uuid


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
    district_full_access = models.JSONField(default=dict, blank=True)
    
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
    lesson_video_url = models.URLField(blank=True)
    lesson_transcript = models.TextField(blank=True)
    lesson_duration = models.IntegerField(default=0)
    
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
    """Legacy exercise attempts"""
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
    overview_video_url = models.URLField(blank=True)
    overview_transcript = models.TextField(blank=True)
    overview_duration = models.IntegerField(default=0)
    
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


class UserVenueUnlock(models.Model):
    """Track module-driven venue unlocks per user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='venue_unlocks')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='user_unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'venue']
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} unlocked {self.venue}"


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
    session_state = models.JSONField(default=dict, blank=True)
    
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
    PASS_CHOICES = [
        ('main', 'Main'),
        ('return', 'Return'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_submissions')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lesson_submissions')
    knowledge_block = models.ForeignKey(KnowledgeBlock, on_delete=models.CASCADE, related_name='lesson_submissions', null=True, blank=True)
    loop_index = models.IntegerField(default=0)
    pass_type = models.CharField(max_length=8, choices=PASS_CHOICES, default='main')
    stage_key = models.CharField(max_length=64)
    lever_choice = models.CharField(max_length=16, blank=True)
    exercise_id = models.CharField(max_length=32, blank=True)
    template_id = models.CharField(max_length=64, blank=True)
    payload_version = models.CharField(max_length=12, default='v1')
    payload = models.JSONField(default=dict)
    scores = models.JSONField(default=dict, blank=True)
    completion_score = models.IntegerField(default=0)
    accuracy_score = models.IntegerField(default=0)
    reflection_score = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    ab_variant = models.CharField(max_length=12, blank=True)
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


class LessonSessionContext(models.Model):
    """Session context for module-specific lesson runs."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_sessions')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='session_contexts')
    current_scenario_ref = models.CharField(max_length=64, blank=True)
    last_lever_choice = models.CharField(max_length=16, blank=True)
    last_stakes_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    cooldowns = models.JSONField(default=dict, blank=True)
    loop_index = models.IntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'module']
    
    def __str__(self):
        return f"{self.user.username} - Session {self.module.code}"


class LessonSession(models.Model):
    """Guided script session state (one prompt at a time)."""

    STATE_CHOICES = [
        ("idle", "Idle"),
        ("asking", "Asking"),
        ("waiting", "Waiting"),
        ("transitioning", "Transitioning"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guided_sessions")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="guided_sessions")
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="asking")
    current_step_id = models.CharField(max_length=64, blank=True)
    current_order = models.IntegerField(default=0)
    total_steps = models.IntegerField(default=0)
    flow_version = models.CharField(max_length=32, blank=True)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "module", "state"]),
        ]

    def __str__(self):
        return f"{self.user.username} – Session {self.module.code} ({self.id})"


class LessonStepResponse(models.Model):
    """Transcript row for guided script sessions."""

    session = models.ForeignKey(LessonSession, on_delete=models.CASCADE, related_name="responses")
    step_id = models.CharField(max_length=64)
    field_name = models.CharField(max_length=128)
    value = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "step_id"]),
        ]

    def __str__(self):
        return f"{self.session_id}::{self.step_id}"


class StakesMap(models.Model):
    """Persistent stakes map artifact reused in later modules."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stakes_maps')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='stakes_maps')
    scenario_ref = models.CharField(max_length=64)
    situation_text = models.TextField(blank=True)
    pressure_points = models.JSONField(default=list)
    trigger = models.CharField(max_length=255)
    lever = models.CharField(max_length=32)
    action_step = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.scenario_ref} - {self.lever}"


class TelemetryEvent(models.Model):
    """Fine-grained telemetry for learning analytics dashboards."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telemetry_events', null=True, blank=True)
    module_code = models.CharField(max_length=8)
    name = models.CharField(max_length=80)
    properties_json = models.JSONField(default=dict, blank=True)
    ab_variant = models.CharField(max_length=12, blank=True)
    ts = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-ts']
        indexes = [
            models.Index(fields=['module_code', 'name', 'ts']),
        ]
    
    def __str__(self):
        return f"{self.module_code} - {self.name} @ {self.ts}"


class AmphitheatreSession(models.Model):
    """Guided venue practice sessions in the Greek Amphitheatre."""

    STATE_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='amphitheatre_sessions')
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    visit_number = models.IntegerField(default=1)
    depth_tier = models.CharField(max_length=16, default='alpha')
    status = models.CharField(max_length=16, choices=STATE_CHOICES, default="active")
    current_index = models.IntegerField(default=0)
    exercises_plan = models.JSONField(default=list)
    metadata = models.JSONField(default=dict, blank=True)
    completion_points = models.IntegerField(default=0)
    reflection_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['user', 'visit_number']),
        ]

    def __str__(self):
        return f"{self.user.username} – Amphitheatre visit {self.visit_number}"

    @property
    def total_points(self) -> int:
        return int(self.completion_points or 0) + int(self.reflection_points or 0)

    def mark_completed(self) -> bool:
        if self.status == "completed":
            return False
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])
        return True


class AmphitheatreExerciseRecord(models.Model):
    """Per-exercise artefacts captured inside an Amphitheatre session."""

    STATE_CHOICES = [
        ("idle", "Idle"),
        ("primed", "Primed"),
        ("capturing", "Capturing"),
        ("review", "Review"),
        ("reflected", "Reflected"),
        ("done", "Done"),
    ]

    session = models.ForeignKey(AmphitheatreSession, on_delete=models.CASCADE, related_name='exercise_records')
    exercise_id = models.CharField(max_length=40)
    prompt_id = models.CharField(max_length=64, blank=True)
    sequence_index = models.IntegerField(default=0)
    selections = models.JSONField(default=dict, blank=True)
    audio_reference = models.TextField(blank=True)
    reflection_text = models.TextField(blank=True)
    markers = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="idle")
    philosopher_response = models.TextField(blank=True)
    microcopy = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence_index']
        unique_together = ('session', 'exercise_id')
        indexes = [
            models.Index(fields=['session', 'state']),
            models.Index(fields=['session', 'sequence_index']),
        ]

    def __str__(self):
        return f"{self.session.user.username} – {self.exercise_id} #{self.sequence_index + 1}"

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_reference)

    def as_timeline_entry(self) -> dict:
        """Return a lightweight dict for history timelines."""
        return {
            "exercise_id": self.exercise_id,
            "prompt_id": self.prompt_id,
            "sequence_index": self.sequence_index,
            "reflection_text": self.reflection_text,
            "has_audio": self.has_audio,
            "philosopher_response": self.philosopher_response,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "markers": self.markers or {},
        }

# Tulia Onboarding Questions Documentation

## Overview
After signup, users complete a 7-question onboarding flow that helps personalize their learning experience. The answers are stored in the `UserProfile` model and used to create a personalized persona summary.

## Question Flow

### Question 1: Role
**Question:** "What's your role?"
**Help Text:** "Help us understand your professional context"
**Field:** `role` (CharField, max_length=200)
**Options:**
- Executive
- Manager
- Entrepreneur
- Professional
- Student
- Other

**Purpose:** Understands the user's professional context to tailor communication examples and scenarios.

---

### Question 2: Typical Audience
**Question:** "Who's your typical audience?"
**Help Text:** "Who do you usually present to or communicate with?"
**Field:** `typical_audience` (CharField, max_length=200)
**Options:**
- Board Members
- Team Members
- Clients
- Stakeholders
- General Public
- Mixed

**Purpose:** Identifies the primary audience type to customize lesson content and practice scenarios.

---

### Question 3: Main Goal
**Question:** "What's your main goal?"
**Help Text:** "What do you want to improve most?"
**Field:** `main_goal` (CharField, max_length=200)
**Options:**
- Build Confidence
- Improve Clarity
- Handle Pressure
- Engage Audience
- Persuade & Influence
- All of the Above

**Purpose:** Determines the primary learning objective to prioritize relevant modules and exercises.

---

### Question 4: Comfort Under Pressure
**Question:** "How do you feel under pressure?"
**Help Text:** "When the stakes are high, what happens?"
**Field:** `comfort_under_pressure` (CharField, max_length=100)
**Options:**
- I thrive
- I manage well
- I get nervous
- I struggle

**Purpose:** Assesses baseline anxiety/confidence level to adjust difficulty and provide appropriate support.

---

### Question 5: Time Pressure Profile
**Question:** "How do you handle time pressure?"
**Help Text:** "When you have limited time to prepare"
**Field:** `time_pressure_profile` (CharField, max_length=100)
**Options:**
- I prefer plenty of time
- I work well under deadline
- I thrive on last minute

**Purpose:** Understands preparation preferences to schedule practice recommendations and lesson pacing.

---

### Question 6: Preferred Practice Time
**Question:** "When do you prefer to practice?"
**Help Text:** "What time of day works best for you?"
**Field:** `preferred_practice_time` (CharField, max_length=100)
**Options:**
- Morning
- Afternoon
- Evening
- Flexible

**Purpose:** Identifies optimal practice times for personalized daily reminders and scheduling.

---

### Question 7: Daily Goal Minutes
**Question:** "How many minutes per day?"
**Help Text:** "How much time can you commit daily?"
**Field:** `daily_goal_minutes` (IntegerField, default=15, min=5, max=120)
**Input Type:** Number input (slider or text field)
**Default Value:** 15 minutes
**Validation:** Minimum 5 minutes, Maximum 120 minutes

**Purpose:** Sets realistic daily practice goals for progress tracking and streak maintenance.

---

## Data Storage

All onboarding responses are stored in the `UserProfile` model:

```python
class UserProfile(models.Model):
    role = models.CharField(max_length=200, blank=True)
    typical_audience = models.CharField(max_length=200, blank=True)
    main_goal = models.CharField(max_length=200, blank=True)
    comfort_under_pressure = models.CharField(max_length=100, blank=True)
    time_pressure_profile = models.CharField(max_length=100, blank=True)
    preferred_practice_time = models.CharField(max_length=100, blank=True)
    daily_goal_minutes = models.IntegerField(default=15, validators=[MinValueValidator(1)])
    persona_summary = models.TextField(blank=True)  # AI-generated from onboarding
    onboarding_completed = models.BooleanField(default=False)
```

## User Experience

- **Progress Indicator:** 7 dots at the top show current progress
- **Navigation:** Previous/Next buttons (Previous hidden on step 1)
- **Validation:** Users must select an option before proceeding
- **Completion:** Final step shows "Complete" button instead of "Next"
- **Duration Tracking:** Total time spent in onboarding is tracked

## Analytics

When onboarding is completed, an `AnalyticsEvent` is created:
- **Event Type:** `onboarding_complete`
- **Event Data:** Empty (can be extended to include duration, skipped questions, etc.)

## Future Enhancements

The `persona_summary` field is reserved for AI-generated persona summaries based on onboarding responses. This could be used to:
- Generate personalized lesson recommendations
- Customize AI Coach responses
- Tailor practice scenarios
- Provide targeted feedback

## Accessing Onboarding Data

```python
# In views or templates
profile = request.user.profile
role = profile.role
audience = profile.typical_audience
goal = profile.main_goal
comfort = profile.comfort_under_pressure
time_pressure = profile.time_pressure_profile
practice_time = profile.preferred_practice_time
daily_minutes = profile.daily_goal_minutes
```

## Notes

- All questions are required (except daily_goal_minutes which has a default)
- Users cannot skip questions
- Onboarding must be completed before accessing the main app
- Data is stored immediately upon form submission
- The onboarding flow is mobile-responsive


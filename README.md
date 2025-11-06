# Tulia v2 - Educational Communication Platform

A Django-based educational platform for teaching communication skills with AI-powered mentorship.

## Features

- **Onboarding**: 7-question persona profiling
- **Home Page**: A/B tested (Dashboard vs Map-first)
- **Lesson Runner**: Three-zone interface with AI Coach (Teach/Drill/Review)
- **Milestone Assessment**: Audio recording with rubric scoring
- **District-1**: Three venues (Amphitheater, Forum, Market Square) for practice
- **Economy System**: XP, Coins, Tickets with streak multipliers
- **Progress Tracking**: Module completion, knowledge blocks, checkpoints

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run migrations**:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Seed initial data** (Level 1, Modules A-D, District-1):
```bash
python manage.py seed_data
```

4. **Create superuser** (optional, for admin):
```bash
python manage.py createsuperuser
```

5. **Run development server**:
```bash
python manage.py runserver
```

6. **Access the app**:
- Home: http://localhost:8000/
- Admin: http://localhost:8000/admin/

## Configuration

### n8n Webhooks (Optional)

Set these environment variables to connect to n8n for AI orchestration:

```bash
N8N_LESSON_WEBHOOK=https://your-n8n-instance.com/webhook/lesson
N8N_COACH_WEBHOOK=https://your-n8n-instance.com/webhook/coach
N8N_MILESTONE_WEBHOOK=https://your-n8n-instance.com/webhook/milestone
```

If not set, the app will use fallback/mock responses.

### Feature Flags

Configure in `settings.py`:
- `ENABLE_DISTRICT_MAP`: Enable/disable district map
- `ENABLE_AB_TEST`: Enable/disable A/B testing
- `ENABLE_DAILY_QUESTS`: Enable/disable daily quests

## Project Structure

- `myApp/models.py`: Data models (UserProfile, Level, Module, KnowledgeBlock, etc.)
- `myApp/views.py`: View functions for all pages
- `myApp/templates/`: Django templates (using Tailwind CSS)
- `myApp/management/commands/seed_data.py`: Command to seed initial data

## Brand Styling

- **Colors**: Deep ink background (#0a0a0f), electric violet (#8b5cf6), cyan (#06b6d4)
- **Fonts**: Inter (body), Manrope (headings)
- **Effects**: Glass morphism, smooth transitions (200-250ms)

## User Flow

1. Sign up / Login
2. Complete onboarding (7 questions)
3. Start Module A (or any module)
4. Learn via Teach/Drill/Review tabs
5. Complete all modules (A-D)
6. Take Milestone assessment (≥70% to pass)
7. Unlock District-1 and explore venues

## Economy

- **XP**: 5-10 per exercise × streak multiplier (max 2.0)
- **Coins**: 1 per 2 XP
- **Tickets**: +1 per module complete, +3 for milestone pass
- **Streak**: Daily activity tracking with multiplier bonus

## Adding Content to District-1

District-1 unlocks after completing Level 1 (all modules A-D) and passing the Milestone (≥70%).

### Option 1: Via Django Admin (Easiest)
1. Go to `/admin/myApp/venuetasksheet/add/`
2. Select a venue (Greek Amphitheater, Roman Forum, or Medieval Market Square)
3. Add title, description, and exercises (JSON format)

### Option 2: Via Management Command
```bash
# Check current content
python manage.py add_venue_content

# Add content for specific venue
python manage.py add_venue_content --venue "Greek Amphitheater"
```

### Option 3: Via Python Shell
```python
python manage.py shell
>>> from myApp.models import Venue, VenueTaskSheet
>>> venue = Venue.objects.get(name="Greek Amphitheater")
>>> VenueTaskSheet.objects.create(
...     venue=venue,
...     title="Composure Practice",
...     description="Practice maintaining composure",
...     exercises=[
...         {
...             "title": "Handle Interruption",
...             "type": "scenario",
...             "description": "Practice responding calmly",
...             "prompt": "You're presenting. Someone interrupts..."
...         }
...     ]
... )
```

### Option 4: Via RAG (Advanced)
When n8n is configured, you can generate content dynamically:
```bash
python manage.py add_venue_content --use-rag
```

This would:
- Retrieve relevant Knowledge Blocks from Level 1 modules
- Use AI to generate venue-specific exercises
- Create VenueTaskSheet entries automatically

## RAG Architecture

**RAG is used for:**
- **Level 1 Knowledge Blocks**: These feed the AI Coach and lesson orchestration
- **AI Coach Q&A**: Answers questions using retrieved Knowledge Blocks
- **Lesson Orchestration**: Decides what to teach next based on user progress

**District-1 Content:**
- Can be **static** (manually created VenueTaskSheet entries)
- Can be **dynamic** (generated via RAG from Knowledge Blocks)
- Currently uses **static** approach (seed_data creates sample content)

## Next Steps

- Connect n8n webhooks for AI orchestration
- Add more Knowledge Blocks content for Modules A-D
- Configure RAG for dynamic District-1 content generation
- Add analytics dashboard
- Deploy to production

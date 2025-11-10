#!/usr/bin/env python
"""
Quick-start seeding script for Module A content scaffolding.

Usage:
    python seed_moduleA_sample.py

What this does:
    • Ensure Level 1 exists with the right milestone threshold
    • Ensure Module A is present and linked to Level 1 with the correct name/description
    • Create KnowledgeBlocks for sections A–F with accurate exercise seeds (A1–F2)
    • Create Lessons:
        - One "Mission Loop" lesson for smoke-tests
        - One lesson per section (A–F) to mirror the real flow
    • Create a default superuser (coach/coach123) for local testing

Idempotent: safe to run repeatedly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myProject.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from myApp.models import (  # noqa: E402
    KnowledgeBlock,
    Level,
    Lesson,
    Module,
    District,
    Venue,
    VenueTaskSheet,
)


# ---------- Constants that reflect the Module A spec ----------
LEVEL_NUMBER = 1
LEVEL_NAME = "Level 1"
LEVEL_DESC = (
    "Build high-stakes awareness and regulation habits: understand P/V/I, PIC, "
    "emotional vs cognitive load, 3P control levers, and create a Stakes Map."
)
# Per spec, Module A target unlock is ≥300 points across ~5–6 required activities.
LEVEL_MILESTONE = 300.0  # scoring threshold for unlock progression

MODULE_CODE = "A"
MODULE_NAME = "Module A — Foundations of High-Stakes Communication"
MODULE_DESC = (
    "Learn to analyze what makes moments high-stakes (Pressure · Visibility · Irreversibility), "
    "quantify with PIC, regulate with reframing + presence, diagnose load, select 3P levers, "
    "and build a personal Stakes Map."
)
MODULE_XP_REWARD = 100

# Knowledge Blocks (section titles and exercise seeds) derived from the document
KBLOCKS = [
    dict(
        order=1,
        title="A. Understanding High-Stakes (P · V · I)",
        summary=(
            "Recognize what makes a situation high-stakes by tagging Pressure, Visibility, "
            "and Irreversibility; capture your own upcoming moment."
        ),
        tags=["moduleA", "stakes", "PVI", "awareness"],
        exercise_seeds=["ScenarioTaggerCard:A1", "PersonalScenarioCapture:A2"],
        citations=[
            "Exercise A1 — Stakes Detector; Exercise A2 — My Next High-Stakes Moment"
        ],
    ),
    dict(
        order=2,
        title="B. PIC Formula & Control-Shift",
        summary=(
            "Rate Pressure, Impact, Control to compute a Stakes Score; choose one concrete "
            "action to increase control."
        ),
        tags=["moduleA", "PIC", "control", "agency"],
        exercise_seeds=["TernaryRatingCard:B1", "SingleSelectActionCard:B2"],
        citations=[
            "Exercise B1 — PIC Rating; Exercise B2 — Control-Shift Action"
        ],
    ),
    dict(
        order=3,
        title="C. Psychology of Pressure — Reframing & Body",
        summary=(
            "Shift inner language from anxiety to readiness and practice a 30–40s somatic "
            "reset to regulate before speaking."
        ),
        tags=["moduleA", "reframe", "somatic", "presence"],
        exercise_seeds=["MantraSelectOrWrite:C1", "GuidedBreathDrill:C2"],
        citations=[
            "Exercise C1 — Reframe Script; Exercise C2 — Body Awareness Micro-Drill"
        ],
    ),
    dict(
        order=4,
        title="D. Emotional vs Cognitive Load",
        summary=(
            "Diagnose whether difficulty is driven by emotion or by message complexity; "
            "practice simplifying to three essentials."
        ),
        tags=["moduleA", "diagnosis", "load", "clarity"],
        exercise_seeds=["BinaryClassifierCard:D1", "PickThreeKeyPoints:D2"],
        citations=[
            "Exercise D1 — Load Identification; Exercise D2 — Simplify to 3"
        ],
    ),
    dict(
        order=5,
        title="E. Control Levers (3P): Preparation · Presence · Perspective",
        summary=(
            "Select the most useful lever for your situation and rehearse a short presence "
            "ritual to activate on demand."
        ),
        tags=["moduleA", "3P", "preparation", "presence", "perspective"],
        exercise_seeds=["LeverSelector3P:E1", "PresenceRitualQuickStart:E2"],
        citations=[
            "Exercise E1 — Select Your Lever; Exercise E2 — Presence Micro-Drill"
        ],
    ),
    dict(
        order=6,
        title="F. Practical Application — Build Your Stakes Map",
        summary=(
            "Synthesize into a personal Stakes Map: situation → pressure point → trigger → "
            "lever → action; reflect on usefulness."
        ),
        tags=["moduleA", "stakes_map", "reflection", "application"],
        exercise_seeds=["StakesMapBuilder:F1", "ReflectionRatingCard:F2"],
        citations=[
            "Exercise F1 — Build Your Stakes Map; Exercise F2 — Progress Reflection"
        ],
    ),
]


DISTRICT_1_DATA = {
    "number": 1,
    "name": "District 1 – Foundations",
    "description": (
        "Start here to build practical regulation skills, situational awareness, and "
        "adaptive messaging before moving into higher-pressure districts."
    ),
    "overview_video_url": "https://cdn.tulia.dev/districts/1/overview.mp4",
    "overview_transcript": (
        "Welcome to District 1 – Foundations. This district is your launchpad for mastering "
        "high-stakes communication. You will learn to read the room, regulate your state, and "
        "convert pressure into presence.\n\n"
        "Each module includes a cinematic lesson with a live transcript, an embedded AI coach, "
        "and an exercise circuit that unlocks new venues around the district. Complete all four "
        "modules to earn full access to every space in District 1."
    ),
    "overview_duration": 480,
    "venues": [
        {
            "order": 1,
            "name": "Greek Amphitheatre",
            "description": "Practice presence and projection with a supportive audience.",
            "ticket_cost": 1,
            "xp_reward": 25,
            "coin_reward": 15,
        },
        {
            "order": 2,
            "name": "Roman Forum",
            "description": "Navigate influence dynamics when everyone has a stake.",
            "ticket_cost": 1,
            "xp_reward": 30,
            "coin_reward": 18,
        },
        {
            "order": 3,
            "name": "Medieval Market",
            "description": "Adapt quickly in noisy, fast-changing conversations.",
            "ticket_cost": 1,
            "xp_reward": 35,
            "coin_reward": 20,
        },
    ],
}


MODULES_DATA = [
    {
        "code": "A",
        "name": MODULE_NAME,
        "description": MODULE_DESC,
        "order": 1,
        "xp_reward": MODULE_XP_REWARD,
        "lesson_video_url": "https://cdn.tulia.dev/modules/A/lesson.mp4",
        "lesson_transcript": (
            "We begin by mapping the contours of high-stakes situations. Pressure, visibility, "
            "and irreversibility help you gauge the heat of any upcoming moment.\n\n"
            "Throughout this lesson we analyse real stories from executives who reframed fear "
            "into focus by understanding their PIC profile and choosing the right lever.\n\n"
            "Take notes on the scenarios that resonate with you—the exercises that follow will "
            "ask you to apply these ideas to your own upcoming moment."
        ),
        "lesson_duration": 540,
    },
    {
        "code": "B",
        "name": "Module B — Audience Dynamics & Influence",
        "description": (
            "Decode your stakeholders, anticipate resistance, and reshape your narrative to earn "
            "trust in the moments that matter."
        ),
        "order": 2,
        "xp_reward": 110,
        "lesson_video_url": "https://cdn.tulia.dev/modules/B/lesson.mp4",
        "lesson_transcript": (
            "Influence is contextual. In Module B we step into rooms where power, incentives, "
            "and history collide. You will see how subtle tactical shifts change the outcome.\n\n"
            "Pay close attention to the framing cues, mirroring patterns, and question ladders "
            "demonstrated in the live scenarios. These moves will be available inside the AI coach.\n\n"
            "By the end you will have a checklist to quickly calibrate any audience before you speak."
        ),
        "lesson_duration": 600,
    },
    {
        "code": "C",
        "name": "Module C — Adaptive Delivery & Flow",
        "description": (
            "Build conversational agility so you can pivot, respond, and keep momentum even when "
            "meetings swerve off-script."
        ),
        "order": 3,
        "xp_reward": 110,
        "lesson_video_url": "https://cdn.tulia.dev/modules/C/lesson.mp4",
        "lesson_transcript": (
            "This module takes you inside fast-paced negotiations and Q&A sessions. Watch how the "
            "speaker applies rapid summarising, clarifying, and redirecting techniques to stay in flow.\n\n"
            "You will learn three reset phrases, a concise scaffolding for responses, and how to surface "
            "shared goals when conversations drift.\n\n"
            "Capture your own adaptive phrases as you listen—they will feed the exercises immediately after."
        ),
        "lesson_duration": 570,
    },
    {
        "code": "D",
        "name": "Module D — Integrated Playback & Stakes Map",
        "description": (
            "Synthesize everything: rehearse hard moments end-to-end, gather feedback, and commit to a "
            "spacing plan that keeps skills refreshed."
        ),
        "order": 4,
        "xp_reward": 120,
        "lesson_video_url": "https://cdn.tulia.dev/modules/D/lesson.mp4",
        "lesson_transcript": (
            "We close the district by putting you on stage. You will watch a full rehearsal breakdown, "
            "see how to interpret AI feedback, and design your own spacing boosters.\n\n"
            "Focus on the review rubric and the deliberate practice loop—it unlocks free exploration across "
            "District 1 once you complete the exercises.\n\n"
            "Leave this module with a clear commitment: when will you revisit, who will you rehearse with, "
            "and what stakes map will you refresh first?"
        ),
        "lesson_duration": 620,
    },
]


VENUE_TASK_SHEETS = {
    "Greek Amphitheatre": [
        {
            "order": 1,
            "title": "Presence Warmup",
            "description": "Guided breath and intention-setting before stepping on stage.",
            "exercises": [
                {"type": "breath_control", "duration_sec": 90},
                {"type": "intention_statement", "prompt": "Who are you speaking for?"},
            ],
        },
    ],
    "Roman Forum": [
        {
            "order": 1,
            "title": "Influence Drill",
            "description": "Role-play stakeholder objections and reframe responses.",
            "exercises": [
                {"type": "objection_handling", "rounds": 3},
                {"type": "reframing", "prompt": "Restate their benefit in one line."},
            ],
        },
    ],
    "Medieval Market": [
        {
            "order": 1,
            "title": "Agility Circuit",
            "description": "Practice rapid summaries and adaptive language amid fast changes.",
            "exercises": [
                {"type": "rapid_summary", "count": 3},
                {"type": "bridge_phrase", "prompt": "Use: 'What I’m hearing is…'"},
            ],
        },
    ],
}


def seed_level_and_modules() -> Module:
    """Create/align Level 1 and all District 1 modules, returning Module A."""
    level, _ = Level.objects.get_or_create(
        number=LEVEL_NUMBER,
        defaults=dict(
            name=LEVEL_NAME,
            description=LEVEL_DESC,
            milestone_threshold=LEVEL_MILESTONE,
        ),
    )
    # If Level exists but threshold/desc changed, update minimally
    updates = {}
    if level.description != LEVEL_DESC:
        updates["description"] = LEVEL_DESC
    if getattr(level, "milestone_threshold", None) != LEVEL_MILESTONE:
        updates["milestone_threshold"] = LEVEL_MILESTONE
    if updates:
        for k, v in updates.items():
            setattr(level, k, v)
        level.save(update_fields=list(updates.keys()))

    module_lookup: dict[str, Module] = {}

    for payload in MODULES_DATA:
        defaults = dict(
            name=payload["name"],
            description=payload["description"],
            order=payload["order"],
            xp_reward=payload["xp_reward"],
            lesson_video_url=payload["lesson_video_url"],
            lesson_transcript=payload["lesson_transcript"],
            lesson_duration=payload["lesson_duration"],
        )
        module, created = Module.objects.get_or_create(
            level=level,
            code=payload["code"],
            defaults=defaults,
        )
        if not created:
            updates = {}
            for field, value in defaults.items():
                if getattr(module, field) != value:
                    updates[field] = value
            if updates:
                for field, value in updates.items():
                    setattr(module, field, value)
                module.save(update_fields=list(updates.keys()))
        module_lookup[payload["code"]] = module

    return module_lookup["A"]


def seed_knowledge_blocks(module: Module) -> list[KnowledgeBlock]:
    """Create/align KnowledgeBlocks for A–F with correct exercise seeds."""
    blocks = []
    for kb in KBLOCKS:
        block, created = KnowledgeBlock.objects.get_or_create(
            module=module,
            order=kb["order"],
            defaults=dict(
                title=kb["title"],
                summary=kb["summary"],
                tags=kb["tags"],
                exercise_seeds=kb["exercise_seeds"],
                citations=kb["citations"],
            ),
        )
        if not created:
            # Update drift without clobbering stable fields
            kb_updates = {}
            if block.title != kb["title"]:
                kb_updates["title"] = kb["title"]
            if block.summary != kb["summary"]:
                kb_updates["summary"] = kb["summary"]
            if list(block.tags or []) != kb["tags"]:
                kb_updates["tags"] = kb["tags"]
            if list(block.exercise_seeds or []) != kb["exercise_seeds"]:
                kb_updates["exercise_seeds"] = kb["exercise_seeds"]
            if list(block.citations or []) != kb["citations"]:
                kb_updates["citations"] = kb["citations"]
            if kb_updates:
                for k, v in kb_updates.items():
                    setattr(block, k, v)
                block.save(update_fields=list(kb_updates.keys()))
        blocks.append(block)
    return blocks


def seed_district() -> District:
    """Ensure District 1 exists with media metadata populated."""
    data = DISTRICT_1_DATA
    district, _ = District.objects.get_or_create(
        number=data["number"],
        defaults=dict(
            name=data["name"],
            description=data["description"],
            unlock_requirement="Complete Level 1 milestone",
            overview_video_url=data["overview_video_url"],
            overview_transcript=data["overview_transcript"],
            overview_duration=data["overview_duration"],
        ),
    )
    updates = {}
    for field in ["name", "description", "overview_video_url", "overview_transcript", "overview_duration"]:
        if getattr(district, field) != data[field]:
            updates[field] = data[field]
    if updates:
        for key, value in updates.items():
            setattr(district, key, value)
        district.save(update_fields=list(updates.keys()))
    return district


def seed_venues(district: District) -> None:
    """Ensure venues and task sheets exist for District 1."""
    for payload in DISTRICT_1_DATA["venues"]:
        venue, _ = Venue.objects.get_or_create(
            district=district,
            name=payload["name"],
            defaults=dict(
                description=payload["description"],
                ticket_cost=payload["ticket_cost"],
                xp_reward=payload["xp_reward"],
                coin_reward=payload["coin_reward"],
                order=payload["order"],
            ),
        )
        updates = {}
        for field in ["description", "ticket_cost", "xp_reward", "coin_reward", "order"]:
            if getattr(venue, field) != payload[field]:
                updates[field] = payload[field]
        if updates:
            for key, value in updates.items():
                setattr(venue, key, value)
            venue.save(update_fields=list(updates.keys()))

        sheets = VENUE_TASK_SHEETS.get(venue.name, [])
        for sheet in sheets:
            task_sheet, _ = VenueTaskSheet.objects.get_or_create(
                venue=venue,
                order=sheet["order"],
                defaults=dict(
                    title=sheet["title"],
                    description=sheet["description"],
                    exercises=sheet["exercises"],
                ),
            )
            ts_updates = {}
            for field in ["title", "description", "exercises"]:
                if getattr(task_sheet, field) != sheet[field]:
                    ts_updates[field] = sheet[field]
            if ts_updates:
                for key, value in ts_updates.items():
                    setattr(task_sheet, key, value)
                task_sheet.save(update_fields=list(ts_updates.keys()))


def seed_lessons(module: Module, blocks: list[KnowledgeBlock]) -> list[Lesson]:
    """
    Create lessons:
      • #1 Mission Loop (quick smoke run)
      • #2–#7 per-section lessons mirroring A–F
    """
    lessons = []

    # Mission Loop lesson for quick testing
    mission, _ = Lesson.objects.get_or_create(
        module=module,
        order=1,
        defaults=dict(
            name="Module A · Mission Loop (Smoke Test)",
            xp_reward=50,
        ),
    )
    lessons.append(mission)

    # Per-section lessons
    # Offset by +1 because order=1 is the Mission Loop
    for idx, block in enumerate(blocks, start=2):
        lesson, _ = Lesson.objects.get_or_create(
            module=module,
            order=idx,
            defaults=dict(
                name=f"Module A · {block.title}",
                xp_reward=50,
            ),
        )
        lessons.append(lesson)
    return lessons


def ensure_superuser() -> None:
    """Create a default superuser for quick testing (optional)."""
    User = get_user_model()
    if not User.objects.filter(username="coach").exists():
        User.objects.create_superuser(
            username="coach",
            email="coach@example.com",
            password="coach123",
        )


def main() -> None:
    module = seed_level_and_modules()
    district = seed_district()
    seed_venues(district)
    blocks = seed_knowledge_blocks(module)
    lessons = seed_lessons(module, blocks)
    ensure_superuser()

    print("✅ District 1 scaffolding aligned with spec")
    print(f" • District: {district.number} – {district.name}")
    print(f"   - Venues: {Venue.objects.filter(district=district).count()} with task sheets")
    print(f" • Level: {module.level.number} – {module.level.name}")
    print(f" • Level milestone threshold: {module.level.milestone_threshold}")
    print(f" • Module: {module.code} – {module.name}")
    other_modules = Module.objects.filter(level=module.level).exclude(code="A").order_by("order")
    for mod in other_modules:
        print(f"   - Module {mod.code} ready ({mod.lesson_video_url or 'no video'})")
    print(f" • KnowledgeBlocks: {len(blocks)} (A–F)")
    for b in blocks:
        print(f"   - #{b.order}: {b.title}  → seeds: {', '.join(b.exercise_seeds)}")
    print(f" • Lessons: {len(lessons)} (1 Mission Loop + {len(blocks)} section lessons)")
    print(" • Superuser: coach / coach123 (created if missing)")
    print("\nRun `python manage.py runserver` and open /module/A/learn/ to explore the flow.")


if __name__ == "__main__":
    main()

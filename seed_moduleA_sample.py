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


def seed_level_and_module() -> Module:
    """Create/align Level 1 and Module A."""
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

    module, created = Module.objects.get_or_create(
        level=level,
        code=MODULE_CODE,
        defaults=dict(
            name=MODULE_NAME,
            description=MODULE_DESC,
            order=1,
            xp_reward=MODULE_XP_REWARD,
        ),
    )
    if not created:
        m_updates = {}
        if module.name != MODULE_NAME:
            m_updates["name"] = MODULE_NAME
        if module.description != MODULE_DESC:
            m_updates["description"] = MODULE_DESC
        if getattr(module, "xp_reward", None) != MODULE_XP_REWARD:
            m_updates["xp_reward"] = MODULE_XP_REWARD
        if m_updates:
            for k, v in m_updates.items():
                setattr(module, k, v)
            module.save(update_fields=list(m_updates.keys()))
    return module


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
    module = seed_level_and_module()
    blocks = seed_knowledge_blocks(module)
    lessons = seed_lessons(module, blocks)
    ensure_superuser()

    print("✅ Module A seed aligned with spec")
    print(f" • Level: {module.level.number} – {module.level.name}")
    print(f" • Level milestone threshold: {module.level.milestone_threshold}")
    print(f" • Module: {module.code} – {module.name}")
    print(f" • KnowledgeBlocks: {len(blocks)} (A–F)")
    for b in blocks:
        print(f"   - #{b.order}: {b.title}  → seeds: {', '.join(b.exercise_seeds)}")
    print(f" • Lessons: {len(lessons)} (1 Mission Loop + {len(blocks)} section lessons)")
    print(" • Superuser: coach / coach123 (created if missing)")
    print("\nRun `python manage.py runserver` and open /lesson/A to explore the flow.")


if __name__ == "__main__":
    main()

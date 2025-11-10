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
    "overview_video_url": "https://res.cloudinary.com/dcuswyfur/video/upload/v1762789570/SpeakProApp_-_Mastering_High-Stakes_Communication_sohlyo.mp4",
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
        "lesson_video_url": "https://res.cloudinary.com/dcuswyfur/video/upload/v1762789570/1._LEVEL_1_Module_A__Foundations_of_High-Stakes_Communication_svcioe.mp4",
        "lesson_transcript": """0:00 All right, let's get into it.
0:01 Today, we are tackling those make or break moments.
0:05 You know the ones, the huge client pitch, that incredibly tough conversation you've been putting off, or the presentation that could literally define your career.
0:12 We're talking about mastering high stakes communication.
0:16 So picture this, you've been there, right?
0:18 In the car, on your run, in the shower, you're genius.
0:21 You've got the perfect comeback, the killer data point, the flawless argument.
0:25 But then you're in the room, the pressure hits and poof.
0:28 It's all gone.
0:29 Your brain just kind of goes offline.
0:30 It's a real thing.
0:32 When we're stressed, our working memory basically tanks.
0:35 So what do we do about it?
0:37 Well, here's a hint.
0:38 The answer is not memorising your lines better.
0:41 See, a script is brittle.
0:43 It shatters the second someone throws you a curveball question.
0:46 What you actually need is an internal guide, something to orient you when things get chaotic.
0:51 Forget the script.
0:52 What you need is a compass.
0:54 And that's what we're building today.
0:56 The whole game is about making a fundamental shift, moving away from that knee jerk, often disastrous reaction and into a more thoughtful intentional response.
1:06 This compass, it's the framework that helps you make that shift every single time.
1:11 So here it is, your communication compass.
1:14 It's built around four cardinal directions, four dimensions you have to keep in balance to stay on your feet when the pressure's on.
1:21 We've got awareness, audience, style, and clarity.
1:25 Let's break down how they all work together, starting with that vertical axis.
1:29 OK, so think of this axis as your personal anchor.
1:33 It's all about what's happening inside of you, and how that translates to the message you're actually putting out into the world.
1:40 It's the direct line from your internal state to your external impact.
1:44 And this slide just lays it all out, doesn't it?
1:47 On the left, that's the reaction zone.
1:49 That's what some psychologists call an amygdala hijack where your emotions basically take the steering wheel from your logical brain, but on the right, that's our goal.
1:59 That's a conscious response.
2:00 You're calm, you're observant, and you're coherent, which brings us to the south point of our compass, awareness.
2:07 This is the bedrock.
2:08 It's simply about taking a microsecond, just a beat, to check in with yourself.
2:12 OK, what's going on with me right now?
2:14 Am I feeling defensive?
2:16 Is my heart racing?
2:18 Just noticing it is the first and most important step to managing it.
2:22 Because when you're grounded in that self-awareness, you can point yourself toward clarity.
2:26 That's our North Star.
2:27 And listen, clarity is not about dumbing things down.
2:30 It's actually the opposite.
2:32 It's about doing the hard work of structuring your thoughts so your audience doesn't have to struggle to understand you.
2:38 And here's a super practical tool to get that clarity.
2:41 It's the 3 by 3 framework.
2:43 It's simple.
2:44 First, what is the one single thing, the absolute core truth you need your audience to remember?
2:50 Got it? OK.
2:51 Second, what are the three pillars, the key pieces of data, the stories, the evidence that hold up that idea?
2:59 And third, what do you want them to do now?
3:02 It's like a pyramid for your message and it is rock solid.
3:05 OK, so we've got ourselves grounded with that vertical axis.
3:09 Now, let's pivot to the horizontal axis.
3:12 This one is all about the dance, the dance between you and everyone else in the room.
3:16 It's how you connect with people without completely losing who you are.
3:20 Over on the west point we have style.
3:22 This is your unique flavour, your authentic energy.
3:25 This is not about putting on some kind of professional persona.
3:29 It's about understanding your natural way of being.
3:31 Are you a direct to the point person?
3:33 Are you more analytical or maybe warm and relational?
3:36 Knowing your default is the key.
3:38 And directly opposite your style, on the east, is the audience, and this is so, so important.
3:45 The best communicators I know, they're not just broadcasting a message at people.
3:49 No way.
3:50 They're creating meaning with people.
3:53 That means you have to read the room, understand what the other person cares about, and adapt to what they truly need to hear.
4:00 This chart here is a fantastic little cheat sheet for this.
4:03 You can see a driver, they just want the bottom line, but an analytical person, they're going to need the data.
4:08 An amiable person values harmony while an expressive is motivated by recognition.
4:12 Now here's the really interesting part.
4:14 Look at what happens under pressure.
4:16 Our biggest strengths flip and become our weaknesses.
4:19 That decisive driver, they become abrupt.
4:21 The harmony-seeking amiable, they vanish to avoid conflict.
4:25 Being aware of this in yourself and others is a total game changer.
4:29 I absolutely love this quote because it just nails the entire challenge of this horizontal axis.
4:36 Style is how authenticity meets context.
4:39 It's not about being a chameleon and changing who you are.
4:42 It's about being flexible enough to adapt how you express your authentic self to fit the situation you're in.
4:50 So let's pull all of these threads together.
4:52 You've got these four points on the compass, your inner awareness, your outer clarity, your authentic style, and your connection to the audience.
4:59 These aren't separate skills you just check off a list.
5:02 They're a living breathing system you use to navigate in real time.
5:06 And when you get all four of those points working in harmony, that's when you achieve this state, conscious communication.
5:14 You are present, you're perceptive of others, you're authentic to yourself, and you're crystal clear in your message.
5:22 This is the goal.
5:23 This is what it feels like to be on compass.
5:26 OK, but how do you use this in the real world, right? In the heat of the moment.
5:31 Well, think of it as a quick pre-flight checklist.
5:34 Before you walk into that meeting or unmute yourself on that call, just ask yourself two simple questions.
5:39 First, am I grounded before I speak?
5:41 That covers your whole vertical axis.
5:43 And second, am I balancing my own authenticity with empathy for them?
5:48 That's your horizontal axis.
5:50 That's it.
5:51 And please remember this.
5:53 The point of the compass isn't to become a perfect flawless communicator.
5:57 That's not real.
5:58 This is about being present.
6:00 It's about having the awareness to notice when you've drifted off course and then having the tool to gently guide yourself back to centre.
6:07 So, I'll leave you with a final thought to take with you.
6:11 As you look at these four directions, that inner awareness, the outer clarity, your authentic style, and our connection to the audience, just ask yourself, which one of those is calling out for a little more of your attention right now?
6:24 Thanks so much for tuning in.""",
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
        "lesson_video_url": "https://res.cloudinary.com/dcuswyfur/video/upload/v1762789563/2._LEVEL_1_Module_B__Audience_Psychology_Dynamics_Knowledge_Base_fgnxjh.mp4",
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
        "lesson_video_url": "https://res.cloudinary.com/dcuswyfur/video/upload/v1762789568/3._LEVEL_1_Module_C__Personal_Style_Awareness_Knowledge_Base_xdtbiz.mp4",
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
        "lesson_video_url": "https://res.cloudinary.com/dcuswyfur/video/upload/v1762789564/4._LEVEL_1_Module_D__Clarity_Message_Design_Basics_Knowledge_Base_jts6kd.mp4",
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

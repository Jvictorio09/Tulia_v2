"""
Domain logic for the Greek Amphitheatre venue experience.

This module packages prompt pools, shared component definitions, and helper
utilities that orchestrate session planning and reflective feedback.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

EXERCISE_ORDER = [
    "stakes_echoes",
    "voice_to_marble",
    "inner_listener",
    "control_in_motion",
    "shorter_not_smaller",
    "echo_of_truth",
]

TAG_PICKER_OPTIONS = [
    {
        "id": "pressure",
        "label": "Pressure",
        "hint": "Is a clock, deadline, or expectation squeezing the moment?",
    },
    {
        "id": "visibility",
        "label": "Visibility",
        "hint": "Are eyes, scrutiny, or visibility amplifying nerves?",
    },
    {
        "id": "irreversibility",
        "label": "Irreversibility",
        "hint": "Does the outcome feel permanent or hard to repair?",
    },
]

LEVER_OPTIONS = [
    {
        "id": "preparation",
        "label": "Preparation",
        "micro_priming": "Picture the one question you want to be ready for. Meet it with a steady breath in.",
    },
    {
        "id": "presence",
        "label": "Presence",
        "micro_priming": "Locate your feet, soften your jaw, and let the exhale guide your tone to ground level.",
    },
    {
        "id": "perspective",
        "label": "Perspective",
        "micro_priming": "Zoom out: what is the generous assumption you can lend this moment?",
    },
]


def get_depth_tier(visit_number: int) -> str:
    if visit_number <= 3:
        return "alpha"
    if visit_number <= 7:
        return "beta"
    return "gamma"


def exercises_for_visit(visit_number: int) -> List[str]:
    """Return the ordered exercise ids for a visit number."""
    if visit_number <= 2:
        return ["stakes_echoes"]
    if visit_number <= 4:
        return ["voice_to_marble", "inner_listener"]
    if visit_number <= 6:
        return ["control_in_motion", "shorter_not_smaller"]
    # Beyond visit 6, rotate through all exercises with gentle variety
    start_index = (visit_number - 1) % len(EXERCISE_ORDER)
    length = 2 if visit_number < 12 else 3
    chosen = []
    for offset in range(length):
        chosen.append(EXERCISE_ORDER[(start_index + offset) % len(EXERCISE_ORDER)])
    return chosen


@dataclass
class Prompt:
    id: str
    headline: str
    scenario: str
    why_it_matters: str
    rotating_prompt: Optional[str] = None


PROMPT_POOLS: Dict[str, Dict[str, List[Prompt]]] = {
    "stakes_echoes": {
        "alpha": [
            Prompt(
                id="stakes-alpha-1",
                headline="Warm boardroom, unexpected agenda",
                scenario="Your director adds a surprise ask: explain how the pivot protects client trust in one minute.",
                why_it_matters="Naming the true load reveals the lever you can reach for in seconds.",
                rotating_prompt="As the room leans in, what feels tightest: time, attention, or consequence?",
            ),
            Prompt(
                id="stakes-alpha-2",
                headline="All hands update",
                scenario="You have 45 seconds to unlock your team’s focus before demo handoffs begin.",
                why_it_matters="Seeing the stakes clarifies how you can soften them for both sides.",
                rotating_prompt="Where is your nervous system bracing itself?",
            ),
        ],
        "beta": [
            Prompt(
                id="stakes-beta-1",
                headline="Investor follow-up",
                scenario="A follow-up call with a lead investor needs your clearest ask after a shaky pilot.",
                why_it_matters="Pressure multiplies when we treat visibility as judgement rather than partnership.",
                rotating_prompt="If one lever eased, which part would breathe again?",
            ),
            Prompt(
                id="stakes-beta-2",
                headline="High-stakes facilitation",
                scenario="You’re moderating a tense cross-functional retro with two execs observing silently.",
                why_it_matters="Identifying the load invites an intentional response instead of a reactive one.",
                rotating_prompt="What unseen expectation could be fuelling the tension?",
            ),
        ],
        "gamma": [
            Prompt(
                id="stakes-gamma-1",
                headline="Public debrief",
                scenario="A public council meeting asks you to justify a delayed rollout with empathy and clarity.",
                why_it_matters="When irreversible threads loom, naming them aloud returns agency to your voice.",
                rotating_prompt="Which lever could convert scrutiny into alignment?",
            ),
            Prompt(
                id="stakes-gamma-2",
                headline="Media spotlight",
                scenario="A quick press briefing needs a three-sentence answer on a sensitive change org question.",
                why_it_matters="Clarity under lights protects trust long after the clip circulates.",
                rotating_prompt="What belief about yourself might lighten the lens?",
            ),
        ],
    },
    "voice_to_marble": {
        "alpha": [
            Prompt(
                id="voice-alpha-1",
                headline="Stone steps rehearsal",
                scenario="The Philosopher asks: tell this marble stage why your idea matters to the people listening.",
                why_it_matters="Your vocal presence convinces the marble before it reaches the ears.",
                rotating_prompt="Let the first word land with a soft exhale.",
            ),
            Prompt(
                id="voice-alpha-2",
                headline="The empty amphitheatre",
                scenario="With seats yet to fill, rehearse the opening line that grounds your message.",
                why_it_matters="The marble catches the timbre of confident breath before any audience arrives.",
                rotating_prompt="Can you let your tone arrive one beat before your words?",
            ),
        ],
        "beta": [
            Prompt(
                id="voice-beta-1",
                headline="Midday echo test",
                scenario="A second take focuses on pace: invite curiosity without rushing the silence.",
                why_it_matters="Presence is felt when pauses are offered as gifts, not apologies.",
                rotating_prompt="Trust the quiet—it’s part of the phrase.",
            ),
            Prompt(
                id="voice-beta-2",
                headline="Evening resonance",
                scenario="You’re practicing the close of your pitch as the amphitheatre lights dim.",
                why_it_matters="Energy shifts when the cadence balances warmth and conviction.",
                rotating_prompt="Let the final word taper like a lantern dimming slowly.",
            ),
        ],
        "gamma": [
            Prompt(
                id="voice-gamma-1",
                headline="Dawn declaration",
                scenario="Before sunrise, declare the future story you’re inviting stakeholders into.",
                why_it_matters="Your voice can anchor possibility even before there’s proof.",
                rotating_prompt="Shape the message as if the marble could remember it tomorrow.",
            ),
            Prompt(
                id="voice-gamma-2",
                headline="Night watch reflection",
                scenario="After a long day, speak directly to someone who doubted you.",
                why_it_matters="Articulating quiet conviction builds emotional resonance.",
                rotating_prompt="Let compassion soften any sharp edges in the tone.",
            ),
        ],
    },
    "inner_listener": {
        "alpha": [
            Prompt(
                id="inner-alpha-1",
                headline="Notice the whisper",
                scenario="Name the internal message that keeps tapping your shoulder in high-stakes rooms.",
                why_it_matters="Hearing the whisper reduces the volume of the critic.",
                rotating_prompt="Where in your body do you feel it first?",
            ),
            Prompt(
                id="inner-alpha-2",
                headline="Mapping the cue",
                scenario="Recall the last time your intuition tugged you toward clarity.",
                why_it_matters="Inner awareness is a lantern for porous attention.",
                rotating_prompt="What did it ask you to notice?",
            ),
        ],
        "beta": [
            Prompt(
                id="inner-beta-1",
                headline="Balancing dual voices",
                scenario="Two inner voices walk with you: the confident strategist and the cautious protector.",
                why_it_matters="Letting both speak invites a third voice—wise synthesis.",
                rotating_prompt="What bridge sentence could help them collaborate?",
            ),
            Prompt(
                id="inner-beta-2",
                headline="Listening in motion",
                scenario="Track how your inner narrator shifts during a challenging conversation.",
                why_it_matters="Documenting the shift creates data for self-trust.",
                rotating_prompt="Where did it speed up or slow down?",
            ),
        ],
        "gamma": [
            Prompt(
                id="inner-gamma-1",
                headline="The future mentor",
                scenario="Imagine future-you standing beside you, offering a single grounding cue.",
                why_it_matters="Borrowed wisdom today becomes embodied intuition tomorrow.",
                rotating_prompt="What sentence lands with compassionate firmness?",
            ),
            Prompt(
                id="inner-gamma-2",
                headline="From tension to tether",
                scenario="Transform the nervous narrative you feel before speaking into a supportive script.",
                why_it_matters="Rewriting it in real time turns threat into tether.",
                rotating_prompt="Which word changes the entire tone?",
            ),
        ],
    },
    "control_in_motion": {
        "alpha": [
            Prompt(
                id="control-alpha-1",
                headline="Choose your lever",
                scenario="Pick Preparation, Presence, or Perspective for the next 30 seconds.",
                why_it_matters="Conscious choice dissolves the myth of zero control.",
                rotating_prompt="Name the cue that tells you this lever matters now.",
            )
        ],
        "beta": [
            Prompt(
                id="control-beta-1",
                headline="Lever in the wild",
                scenario="Recall a live moment this week where the chosen lever softened the stakes.",
                why_it_matters="Tying breath to story helps you repeat it under pressure.",
                rotating_prompt="How did your body confirm you were on track?",
            )
        ],
        "gamma": [
            Prompt(
                id="control-gamma-1",
                headline="Pass the lever along",
                scenario="Teach someone else how to spot and pull your chosen lever.",
                why_it_matters="Instruction locks the lesson into muscle memory.",
                rotating_prompt="What invitation keeps the lever gentle, not rigid?",
            )
        ],
    },
    "shorter_not_smaller": {
        "alpha": [
            Prompt(
                id="short-alpha-1",
                headline="Full take → sentence → three words",
                scenario="Articulate the idea, refine to a sentence, then chisel it to three words.",
                why_it_matters="Compression sharpens both clarity and confidence.",
                rotating_prompt="Feel the shift each time you compress.",
            )
        ],
        "beta": [
            Prompt(
                id="short-beta-1",
                headline="Moments of compression",
                scenario="Start with the full story, then keep the emotional contour in the condensed versions.",
                why_it_matters="Depth isn’t lost when intention stays intact.",
                rotating_prompt="Which detail is essence rather than ornament?",
            )
        ],
        "gamma": [
            Prompt(
                id="short-gamma-1",
                headline="Compression for influence",
                scenario="Refine a persuasive case: full arc, one-line promise, three-word torch.",
                why_it_matters="Being brief without shrinking the idea is an advanced craft.",
                rotating_prompt="Let the three words feel like a vow.",
            )
        ],
    },
    "echo_of_truth": {
        "alpha": [
            Prompt(
                id="echo-alpha-1",
                headline="Voice the truth",
                scenario="Name the truth you want your stakeholders to feel after you leave the room.",
                why_it_matters="Stating truth gently is persuasive without force.",
                rotating_prompt="What is the warmth you want the listener to keep?",
            )
        ],
        "beta": [
            Prompt(
                id="echo-beta-1",
                headline="Truth in motion",
                scenario="Share the line that still rings true after the meeting is over.",
                why_it_matters="Echoes happen when authenticity outlasts performance.",
                rotating_prompt="How can you soften the edges without losing power?",
            )
        ],
        "gamma": [
            Prompt(
                id="echo-gamma-1",
                headline="Offer the truth as invitation",
                scenario="Voice the quiet conviction you want the room to adopt with you.",
                why_it_matters="Congruence invites others to mirror your calm clarity.",
                rotating_prompt="What promise sits behind the words?",
            )
        ],
    },
}


def pick_prompt(exercise_id: str, tier: str, exclude: Optional[str] = None) -> Prompt:
    pool = PROMPT_POOLS.get(exercise_id, {})
    tier_prompts = pool.get(tier) or pool.get("beta") or []
    if not tier_prompts:
        raise ValueError(f"No prompt pool configured for exercise '{exercise_id}' tier '{tier}'")
    candidates = [prompt for prompt in tier_prompts if prompt.id != exclude] or tier_prompts
    return random.choice(candidates)


def build_exercise_payload(exercise_id: str, tier: str, visit_number: int, sequence_index: int, recent_prompt_id: Optional[str] = None) -> Dict:
    prompt = pick_prompt(exercise_id, tier, exclude=recent_prompt_id)
    base = {
        "id": exercise_id,
        "title": EXERCISE_TITLES[exercise_id],
        "sequence_index": sequence_index,
        "prompt": {
            "id": prompt.id,
            "headline": prompt.headline,
            "scenario": prompt.scenario,
            "why_it_matters": prompt.why_it_matters,
            "rotating_prompt": prompt.rotating_prompt,
        },
        "tier": tier,
        "visit_number": visit_number,
    }

    base.update(EXERCISE_COMPONENTS[exercise_id])
    return base


def build_session_plan(visit_number: int, last_prompt_lookup: Optional[Dict[str, str]] = None) -> List[Dict]:
    tier = get_depth_tier(visit_number)
    sequence = exercises_for_visit(visit_number)
    last_prompt_lookup = last_prompt_lookup or {}
    plan = []
    for index, exercise_id in enumerate(sequence):
        plan.append(
            build_exercise_payload(
                exercise_id=exercise_id,
                tier=tier,
                visit_number=visit_number,
                sequence_index=index,
                recent_prompt_id=last_prompt_lookup.get(exercise_id),
            )
        )
    return plan


def score_submission(exercise_id: str, reflection_text: str, markers: Optional[Dict]) -> Dict[str, int]:
    """Return lightweight scoring data."""
    markers = markers or {}
    completion = 1
    reflection_bonus = 1 if reflection_text.strip() else 0
    if exercise_id in {"voice_to_marble", "shorter_not_smaller", "echo_of_truth", "control_in_motion"}:
        # Reward completion slightly higher when voice is used
        if markers.get("duration_sec"):
            completion += 1
    return {
        "completion": completion,
        "reflection": reflection_bonus,
    }


def build_philosopher_response(exercise_id: str, selections: Dict, reflection_text: str, markers: Optional[Dict]) -> str:
    reflection_text = (reflection_text or "").strip()
    markers = markers or {}
    selections = selections or {}

    if exercise_id == "stakes_echoes":
        picked = [label for label, flag in selections.items() if flag]
        if not picked:
            return "Perhaps start with the lever that already feels within reach."
        blend = ", ".join(word.capitalize() for word in picked)
        return f"{blend} sound present. Name one small action to widen your sense of control."

    if exercise_id == "voice_to_marble":
        duration = markers.get("duration_sec")
        pauses = markers.get("pause_count")
        if duration:
            return f"I heard {duration:.0f} seconds of grounded intent. Your pauses ({pauses or 'steady'}) helped the marble breathe with you."
        return "Let the first breath arrive before the words—you deserve the gentlest entry."

    if exercise_id == "inner_listener":
        if reflection_text:
            return "Awareness is a lantern—trust that this wording will guide you mid-conversation."
        return "Give the inner narrator a line tonight; it will meet you again tomorrow."

    if exercise_id == "control_in_motion":
        lever = selections.get("lever")
        lever_label = next((item["label"] for item in LEVER_OPTIONS if item["id"] == lever), None)
        if lever_label:
            return f"Your breath steadied your tone through {lever_label.lower()}. Notice where it lands in your body now."
        return "Name the lever aloud—it becomes sturdier once spoken."

    if exercise_id == "shorter_not_smaller":
        three_words = selections.get("phase_c")
        if three_words:
            return f"{three_words.title()} is a powerful torch. Carry it into the next room."
        return "Compression chisels meaning. Keep the essence; the marble remembers tone more than length."

    if exercise_id == "echo_of_truth":
        if reflection_text:
            return "A quiet truth is stronger when you acknowledge how it felt to speak it."
        return "Offer the truth gently, and it will echo back as support."

    return "Your practice is compounding—stay with the breath and let the rest soften."


EXERCISE_TITLES = {
    "stakes_echoes": "Spot the Stakes Echoes",
    "voice_to_marble": "Voice to the Marble",
    "inner_listener": "The Inner Listener",
    "control_in_motion": "Control in Motion",
    "shorter_not_smaller": "Shorter, Not Smaller",
    "echo_of_truth": "The Echo of Truth",
}


EXERCISE_COMPONENTS = {
    "stakes_echoes": {
        "components": [
            {
                "type": "tag_picker",
                "options": TAG_PICKER_OPTIONS,
                "label": "Which elements are quietly raising the stakes?",
                "microcopy": "Long-press to remember why each tag matters.",
                "max_select": 3,
            },
            {
                "type": "reflection_field",
                "mode": "text_or_voice",
                "label": "If one lever softened, what would shift?",
                "placeholder": "Take two lines or speak it softly.",
            },
        ],
        "score_bar": {
            "completion_label": "+ completion",
            "reflection_label": "+ reflection",
        },
    },
    "voice_to_marble": {
        "components": [
            {
                "type": "recorder_tile",
                "max_duration_sec": 30,
                "allow_waveform": True,
                "retake_limit": 1,
                "primary_label": "Hold to speak",
            },
            {
                "type": "system_notes",
                "fields": [
                    {"id": "duration", "label": "Duration", "kind": "duration"},
                    {"id": "pause_count", "label": "Pauses sensed", "kind": "count"},
                    {"id": "energy_level", "label": "Energy", "kind": "band"},
                ],
            },
            {
                "type": "reflection_field",
                "mode": "text_optional",
                "label": "What did you notice as you voiced it?",
                "placeholder": "A sentence on what felt steady.",
            },
        ],
    },
    "inner_listener": {
        "components": [
            {
                "type": "prompt_card_inline",
                "label": "What is the inner whisper sharing today?",
            },
            {
                "type": "reflection_field",
                "mode": "text_or_voice",
                "label": "Let the whisper speak without judgement.",
                "placeholder": "Two lines or a short note to self.",
            },
        ],
    },
    "control_in_motion": {
        "components": [
            {
                "type": "lever_picker",
                "options": LEVER_OPTIONS,
                "label": "Which lever will you lean on?",
            },
            {
                "type": "recorder_tile",
                "max_duration_sec": 30,
                "allow_waveform": True,
                "retake_limit": 1,
                "primary_label": "Speak your micro-priming",
            },
            {
                "type": "reflection_field",
                "mode": "text_optional",
                "label": "What shifted as you spoke?",
                "placeholder": "Note the body signal that softened.",
            },
        ],
    },
    "shorter_not_smaller": {
        "components": [
            {
                "type": "multi_phase_compression",
                "phases": [
                    {
                        "id": "phase_a",
                        "kind": "record",
                        "label": "Phase A · Say it in full",
                        "max_duration_sec": 30,
                    },
                    {
                        "id": "phase_b",
                        "kind": "sentence",
                        "label": "Phase B · Distill to one sentence",
                        "max_chars": 160,
                    },
                    {
                        "id": "phase_c",
                        "kind": "three_words",
                        "label": "Phase C · Three-word echo",
                        "max_chars": 32,
                    },
                ],
            },
        ],
    },
    "echo_of_truth": {
        "components": [
            {
                "type": "recorder_tile",
                "max_duration_sec": 25,
                "allow_waveform": True,
                "retake_limit": 1,
                "primary_label": "Speak the truth",
            },
            {
                "type": "reflection_field",
                "mode": "text_optional",
                "label": "How did it feel to speak it?",
                "placeholder": "Name the sensation or emotion.",
            },
        ],
    },
}


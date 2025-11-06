#!/usr/bin/env python
"""
Seed initial data for Tulia v2 (Educational Pillar · Level 1 + District 1)
Run: python seed_data.py
Idempotent and safe to rerun.
"""
import os
import sys
import django

# -- Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myProject.settings")
django.setup()

from django.db import transaction
from myApp.models import (
    Level, Module, KnowledgeBlock, District, Venue, VenueTaskSheet
)

def _flow(skill, outcome, time_estimate, steps):
    """
    Helper to wrap lesson flow data.
    steps: list of dicts with keys like:
      kind: "teach" | "drill" | "review" | "checkpoint"
      title, copy (teach text) | prompt (drill) | rules (review) | question/options/correct (checkpoint)
      scenario, template, constraints, hint, cta_label
    """
    return {
        "type": "lesson_flow",
        "skill": skill,
        "outcome": outcome,
        "time_estimate": time_estimate,
        "steps": steps,
    }

@transaction.atomic
def seed_data():
    print("🌱 Seeding Level 1, Modules A–D with stage-based flows, and District-1...")

    # ---------- LEVEL 1 ----------
    level_1, created = Level.objects.get_or_create(
        number=1,
        defaults=dict(
            name="Level 1 — Awareness & Foundations",
            description=(
                "Build core high-stakes communication foundations: "
                "know the pressure dynamics, understand your audience, "
                "recognize your style, and design clear messages."
            ),
            milestone_threshold=70.0,
        ),
    )
    print("✅ Created Level 1" if created else "ℹ️  Level 1 already exists")

    # ---------- MODULES (A–D) ----------
    modules = [
        dict(
            code="A",
            name="Foundations of High-Stakes Communication",
            order=1,
            xp_reward=60,
            description=(
                "What makes a moment 'high-stakes': time pressure, audience power, "
                "and emotional charge. Principles for staying intentional."
            ),
            kbs=[
                dict(
                    title="The High-Stakes Equation",
                    summary=(
                        "High-stakes moments intensify when time pressure, audience power, "
                        "and emotional charge rise together. Separate event from identity; act intentionally."
                    ),
                    tags=["foundations", "pressure", "mindset"],
                    citations=["Module A — Foundations"],
                    flow=_flow(
                        "Understand high-stakes dynamics",
                        "Spot pressure triggers and stay intentional",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Pressure Has Parts",
                                scenario="Any high-stakes setting",
                                copy=(
                                    "Stakes spike when time is short, the audience has power, "
                                    "and emotions run hot. Naming these parts reduces threat and restores choice."
                                ),
                                chips=["Time", "Power", "Emotion"],
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="Identify the Trigger",
                                question="Which trio best describes a high-stakes spike?",
                                options=[
                                    "Long time • low power • calm room",
                                    "Short time • high power • emotional charge",
                                    "Long time • high power • no emotion"
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="From Autopilot to Intentional",
                    summary=(
                        "In pressure, slow down to speed up. Anchor a Signal Sentence: topic + tension + takeaway. "
                        "Example: 'Our churn is climbing (tension) in SMB; we'll ship 3 retention fixes (takeaway) "
                        "to stop it this quarter (topic).'"
                    ),
                    tags=["foundations", "ritual", "presence", "signal-sentence"],
                    citations=["Module A — Foundations", "Signal Sentence"],
                    flow=_flow(
                        "Signal Sentence",
                        "Say the core in 1 line under pressure",
                        "3 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Your Anchor: The Signal",
                                scenario="Board review • Q2 losses",
                                copy="Signal = topic + tension + takeaway. Say it before details.",
                                chips=["Topic", "Tension", "Takeaway"],
                                cta_label="Try it (30s)",
                            ),
                            dict(
                                kind="drill",
                                title="Write One Signal Sentence",
                                scenario="Board review • Q2 losses",
                                prompt="Write one sentence that names the tension and ends with an action.",
                                template=["[Topic]", "[Tension]", "[Takeaway]"],
                                constraints="Max 140 characters • 1 sentence",
                                hint="Start with the problem; end with the action.",
                                cta_label="Check",
                            ),
                            dict(
                                kind="review",
                                title="Guiding Feedback",
                                rules={
                                    "keep": "You named the tension clearly.",
                                    "tweak": "Add a concrete action or timeframe.",
                                    "next": "Rewrite with a measurable takeaway."
                                },
                                cta_label="Next"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="Golden Principle of Clarity Under Pressure",
                    summary=(
                        "Signal = topic + tension + takeaway. When stakes rise, your signal sentence becomes your anchor."
                    ),
                    tags=["foundations", "clarity", "signal-sentence"],
                    citations=["Module A — Foundations", "Signal Sentence"],
                    flow=_flow(
                        "Signal Sentence",
                        "Anchor clarity before speaking",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Slow Down to Speed Up",
                                scenario="Investor Q&A",
                                copy="Before you answer, say the one-line signal. It orients you and the room.",
                                chips=["One line", "Before details"],
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="Spot the Real Signal",
                                question="Which is a true signal sentence?",
                                options=[
                                    "Let me explain our whole roadmap today.",
                                    "We’re losing SMB customers; we’ll ship 3 retention fixes this quarter.",
                                    "Churn is a problem and maybe we should do something."
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
            ],
        ),
        dict(
            code="B",
            name="Audience Psychology & Dynamics",
            order=2,
            xp_reward=60,
            description=(
                "Decode motives, assumptions, and perceptions. Adapt your message to what your audience values and fears."
            ),
            kbs=[
                dict(
                    title="MAP Card (Motives · Assumptions · Perceptions)",
                    summary=(
                        "Draft a MAP before you speak: what they want (motives), believe (assumptions), and perceive. "
                        "Then tailor hook and examples."
                    ),
                    tags=["audience", "map", "empathy"],
                    citations=["Module B — Audience Psychology", "MAP"],
                    flow=_flow(
                        "MAP Card",
                        "Read your audience in 30 seconds",
                        "3 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Quick MAP Scan",
                                scenario="Town hall • skeptical executives",
                                copy="Jot 3 lines: Motives, Assumptions, Perceptions. Use it to craft your hook.",
                                chips=["Motives", "Assumptions", "Perceptions"],
                                cta_label="Try it (30s)"
                            ),
                            dict(
                                kind="drill",
                                title="Make a MAP",
                                scenario="Town hall • skeptical executives",
                                prompt="Fill your MAP: one honest insight per line.",
                                template=["Motives:", "Assumptions:", "Perceptions:"],
                                constraints="3 lines • one insight each",
                                cta_label="Check"
                            ),
                            dict(
                                kind="review",
                                title="Does Your Hook Match?",
                                rules={
                                    "keep": "Your motive read is useful.",
                                    "tweak": "Make one assumption testable.",
                                    "next": "Draft a 2-sentence hook using your MAP."
                                },
                                cta_label="Next"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="Power & Risk Calibration",
                    summary=(
                        "Power shifts tone. Execs want crisp options; teams want safety and context. Match framing to power."
                    ),
                    tags=["audience", "power-dynamics", "framing"],
                    citations=["Module B — Audience Psychology"],
                    flow=_flow(
                        "Power Calibration",
                        "Frame messages for high-power vs low-power audiences",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Frame to Power",
                                scenario="Executive steering",
                                copy="High power: options and risks. Low power: safety, context, next step.",
                                chips=["Options", "Risk", "Safety"],
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="Pick the Best Framing",
                                question="For a high-power group, which opener fits best?",
                                options=[
                                    "“We’ll explore feelings first.”",
                                    "“Three options with risk/return tradeoffs.”",
                                    "“Let’s take as much time as we need.”"
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="Reading the Room",
                    summary=(
                        "Watch micro-signals: pace, posture, gaze. If confusion rises, add a concrete example and check alignment."
                    ),
                    tags=["audience", "signals", "adaptation"],
                    citations=["Module B — Audience Psychology"],
                    flow=_flow(
                        "Read the Room",
                        "Adapt in real time to audience signals",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Micro-Signals to Track",
                                scenario="Quarterly review",
                                copy="Leaning back? Frowns? Slower blinks? Add context and ask a check question.",
                                chips=["Pace", "Posture", "Gaze"],
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="When Confusion Shows Up…",
                                question="Best next move when faces look puzzled?",
                                options=[
                                    "Talk faster to cover more.",
                                    "Add a concrete example and ask a quick check question.",
                                    "Ignore it and finish."
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
            ],
        ),
        dict(
            code="C",
            name="Personal Style Awareness",
            order=3,
            xp_reward=60,
            description="Know your default style (assertive × responsive) and flex without losing authenticity.",
            kbs=[
                dict(
                    title="Style Radar Snapshot",
                    summary=(
                        "Map yourself on assertiveness × responsiveness. Under pressure, tilt toward what the audience needs."
                    ),
                    tags=["style", "self-awareness", "adaptability"],
                    citations=["Module C — Personal Style", "Style Radar"],
                    flow=_flow(
                        "Style Radar",
                        "Know your default and flex to audience needs",
                        "3 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Find Your Default",
                                scenario="Client pitch • analytical audience",
                                copy="If you’re high-assertive, add patience/questions. If high-responsive, tighten and decide.",
                                chips=["Assertive", "Responsive"],
                                cta_label="Try it (30s)"
                            ),
                            dict(
                                kind="drill",
                                title="Plan a Micro-Adjustment",
                                scenario="Client pitch • analytical audience",
                                prompt="Complete the 3 lines.",
                                template=["My default:", "Audience needs:", "Adjustment:"],
                                constraints="3 short lines",
                                cta_label="Check"
                            ),
                            dict(
                                kind="review",
                                title="Tiny Flex = Big Fit",
                                rules={
                                    "keep": "You identified your default accurately.",
                                    "tweak": "Make the adjustment observable (pace/wording).",
                                    "next": "Try it on your next sentence."
                                },
                                cta_label="Next"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="Stress Behaviors & Micro-Adjustments",
                    summary=(
                        "Stress triggers speed/volume/defense. Counter with slower pace, shorter sentences, reflective phrases."
                    ),
                    tags=["style", "stress", "language"],
                    citations=["Module C — Personal Style"],
                    flow=_flow(
                        "Stress Management",
                        "Stay composed under pressure",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Name the Trigger, Pick the Counter",
                                scenario="Tense stakeholder call",
                                copy="If you speed up, breathe and break sentences. If defensive, reflect first: “Let me clarify that.”",
                                chips=["Breathe", "Shorten", "Reflect"],
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="Pick the Best Counter",
                                question="You notice your pace rising. Best counter?",
                                options=[
                                    "Talk faster to finish.",
                                    "Breathe, slow down, shorten the next sentence.",
                                    "Raise volume to assert control."
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="Authenticity Without Over-Disclosure",
                    summary=(
                        "Use selective vulnerability: acknowledge briefly, then pivot to structure and next steps."
                    ),
                    tags=["style", "authenticity", "ethos"],
                    citations=["Module C — Personal Style"],
                    flow=_flow(
                        "Selective Vulnerability",
                        "Show authenticity without oversharing",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Acknowledge → Pivot",
                                scenario="Team update",
                                copy="One line of honesty, then structure. “This matters to me—here’s how we’ll proceed.”",
                                chips=["Acknowledge", "Pivot"],
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="Which Line Lands Best?",
                                question="Pick the authentic line that still leads.",
                                options=[
                                    "“I’m overwhelmed; I don’t know.”",
                                    "“This matters to me—here’s how we’ll proceed.”",
                                    "“Everything is perfect; no worries.”",
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
            ],
        ),
        dict(
            code="D",
            name="Clarity & Message Design Basics",
            order=4,
            xp_reward=60,
            description="Craft signal sentences and structure messages using the 3×3 builder (signal → three pillars → CTA).",
            kbs=[
                dict(
                    title="Signal Sentence",
                    summary="One-liner: topic + tension + takeaway. It guides your talk and audience attention.",
                    tags=["clarity", "signal-sentence"],
                    citations=["Module D — Clarity & Message Design", "Signal Sentence"],
                    flow=_flow(
                        "Signal Sentence",
                        "Anchor your message in one line",
                        "3 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Say the Core First",
                                scenario="Team stand-up",
                                copy="Name topic, tension, and takeaway in one sentence before details.",
                                chips=["Topic", "Tension", "Takeaway"],
                                cta_label="Try it (30s)"
                            ),
                            dict(
                                kind="drill",
                                title="Write Your Signal",
                                scenario="Team stand-up",
                                prompt="Write one sentence with topic + tension + takeaway.",
                                constraints="≤140 chars • 1 sentence",
                                cta_label="Check"
                            ),
                            dict(
                                kind="review",
                                title="Sharper in One Edit",
                                rules={
                                    "keep": "Your topic is clear.",
                                    "tweak": "Make the takeaway actionable.",
                                    "next": "Add timeframe or measure."
                                },
                                cta_label="Next"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="3×3 Message Builder",
                    summary=(
                        "3×3: Signal → 3 pillars → CTA. Use concrete nouns/verbs."
                    ),
                    tags=["clarity", "structure", "3x3"],
                    citations=["Module D — Clarity & Message Design", "3×3"],
                    flow=_flow(
                        "3×3 Builder",
                        "Structure any message in 3 pillars + CTA",
                        "4 cards • ~3 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Frame Your 3×3",
                                scenario="Executive pitch • budget approval",
                                copy="State the signal, then 3 short pillars, then a clear CTA matching readiness.",
                                chips=["Signal", "Pillars", "CTA"],
                                cta_label="Try it (45s)"
                            ),
                            dict(
                                kind="drill",
                                title="Draft the 3 Pillars",
                                scenario="Executive pitch • budget approval",
                                prompt="Fill your 3 pillars; keep them concrete.",
                                template=["Pillar 1:", "Pillar 2:", "Pillar 3:"],
                                constraints="≤6 words per pillar",
                                hint="Use measurable nouns/verbs.",
                                cta_label="Check"
                            ),
                            dict(
                                kind="review",
                                title="Make Pillars Measurable",
                                rules={
                                    "keep": "Two pillars are crisp.",
                                    "tweak": "Make the vague pillar measurable.",
                                    "next": "Add a CTA that fits execs."
                                },
                                cta_label="Next"
                            ),
                            dict(
                                kind="checkpoint",
                                title="Best CTA for a Skeptical Exec?",
                                question="Pick the CTA that matches power and readiness.",
                                options=[
                                    "“Let’s brainstorm sometime.”",
                                    "“Approve the 3 fixes by Friday.”",
                                    "“We’ll see what happens.”"
                                ],
                                correct=1,
                                reward="+10 XP",
                                cta_label="Continue"
                            ),
                        ]
                    ),
                ),
                dict(
                    title="Say Less, Mean More",
                    summary="Trim redundancies; prefer concrete words; break long sentences. Clarity raises trust.",
                    tags=["clarity", "editing", "brevity"],
                    citations=["Module D — Clarity & Message Design"],
                    flow=_flow(
                        "Brevity",
                        "Cut clutter, keep the core",
                        "2 cards • ~2 mins",
                        steps=[
                            dict(
                                kind="teach",
                                title="Tighten the Line",
                                scenario="Email status",
                                copy="Cut filler. Replace “implement a solution” with “Ship 3 fixes by Friday.”",
                                chips=["Cut filler", "Concrete verbs"],
                                cta_label="Try it (30s)"
                            ),
                            dict(
                                kind="drill",
                                title="Halve the Words",
                                scenario="Email status",
                                prompt="Rewrite the sentence using ~50% fewer words.",
                                constraints="One sentence • fewer words",
                                cta_label="Check"
                            ),
                        ]
                    ),
                ),
            ],
        ),
    ]

    # Create/update Modules and KnowledgeBlocks with flows
    for m in modules:
        module, m_created = Module.objects.get_or_create(
            level=level_1,
            code=m["code"],
            defaults=dict(
                name=m["name"],
                order=m["order"],
                xp_reward=m["xp_reward"],
                description=m["description"],
            ),
        )
        print(f"✅ Created Module {m['code']}" if m_created else f"ℹ️  Module {m['code']} exists")

        for idx, kb in enumerate(m["kbs"]):
            kb_defaults = dict(
                module=module,
                summary=kb["summary"],
                tags=kb["tags"],
                citations=kb["citations"],
                order=idx,
                exercise_seeds=[kb["flow"]],  # the new stage-based flow lives here
            )
            obj, created_kb = KnowledgeBlock.objects.get_or_create(
                module=module, title=kb["title"], defaults=kb_defaults
            )
            if not created_kb:
                # refresh data to keep content in sync with docs
                obj.summary = kb["summary"]
                obj.tags = kb["tags"]
                obj.citations = kb["citations"]
                obj.order = idx
                obj.exercise_seeds = [kb["flow"]]
                obj.save()
        print(f"   ↳ Seeded {len(m['kbs'])} knowledge blocks with flows for Module {m['code']}")

    # ---------- DISTRICT 1 ----------
    district_1, d_created = District.objects.get_or_create(
        number=1,
        defaults=dict(
            name="District 1 — Foundations in Action",
            description=(
                "A tasteful 2D board where you apply Level-1 skills in short, "
                "guided scenarios. Spend tickets to enter venues."
            ),
            unlock_requirement="Complete Level 1 modules + pass Milestone ≥ 70%",
        ),
    )
    print("✅ Created District-1" if d_created else "ℹ️  District-1 already exists")

    venues = [
        dict(
            name="Greek Amphitheater",
            description="Public debate · composure under challenge",
            ticket_cost=1, xp_reward=25, coin_reward=12, order=1,
            tasks=[
                dict(
                    title="Handle Interruption with Poise",
                    description="Respond calmly to a pointed interruption; stabilize the room.",
                    exercises=[
                        dict(
                            title="Interruption Response",
                            type="scenario",
                            description="You’re mid-pitch; a senior exec cuts in with a sharp question.",
                            prompt="“Q2 losses undermine your plan.” Reply in 3 lines: acknowledge, signal, next step."
                        ),
                        dict(
                            title="30-Second Re-Center",
                            type="speak",
                            description="Re-state your signal sentence under pressure.",
                            prompt="Deliver a 30-sec signal sentence that regains attention."
                        ),
                    ],
                ),
            ],
        ),
        dict(
            name="Roman Forum",
            description="Present case to a powerful audience · empathy & framing",
            ticket_cost=1, xp_reward=25, coin_reward=12, order=2,
            tasks=[
                dict(
                    title="Read the Room & Reframe",
                    description="Detect confusion and adjust framing for a high-power audience.",
                    exercises=[
                        dict(
                            title="MAP to Hook",
                            type="scenario",
                            description="Convert a MAP into a two-sentence opening for power.",
                            prompt="They value risk control. Draft a hook that signals prudence + options."
                        ),
                        dict(
                            title="Objection Loop",
                            type="scenario",
                            description="Address a skeptical senator-type persona.",
                            prompt="“Show me numbers, not stories.” 3 lines: pillar, data point, next step."
                        ),
                    ],
                ),
            ],
        ),
        dict(
            name="Medieval Market Square",
            description="Convince merchants in noise · presence & clarity",
            ticket_cost=1, xp_reward=25, coin_reward=12, order=3,
            tasks=[
                dict(
                    title="Command Attention in Noise",
                    description="Project presence, simplify language, and hold the crowd.",
                    exercises=[
                        dict(
                            title="One-Minute Street Pitch",
                            type="speak",
                            description="High-energy delivery with clean structure.",
                            prompt="Pitch in 60s using the 3×3 builder (signal → 3 pillars → CTA)."
                        ),
                        dict(
                            title="Brevity Drill",
                            type="scenario",
                            description="Cut clutter; keep the core.",
                            prompt="Rewrite this 4-sentence pitch into one signal + one pillar."
                        ),
                    ],
                ),
            ],
        ),
    ]

    for v in venues:
        venue, v_created = Venue.objects.get_or_create(
            district=district_1,
            name=v["name"],
            defaults=dict(
                description=v["description"],
                ticket_cost=v["ticket_cost"],
                xp_reward=v["xp_reward"],
                coin_reward=v["coin_reward"],
                order=v["order"],
            ),
        )
        if not v_created:
            venue.description = v["description"]
            venue.ticket_cost = v["ticket_cost"]
            venue.xp_reward = v["xp_reward"]
            venue.coin_reward = v["coin_reward"]
            venue.order = v["order"]
            venue.save()
        print(f"  ✅ {('Created' if v_created else 'Updated')} venue: {v['name']}")

        for idx, t in enumerate(v["tasks"]):
            sheet, created_ts = VenueTaskSheet.objects.get_or_create(
                venue=venue,
                title=t["title"],
                defaults=dict(
                    description=t["description"],
                    exercises=t["exercises"],
                    order=idx,
                ),
            )
            if not created_ts:
                sheet.description = t["description"]
                sheet.exercises = t["exercises"]
                sheet.order = idx
                sheet.save()
            print(f"     ↳ {'Created' if created_ts else 'Updated'} task sheet: {t['title']}")

    print("\n🎉 Seeding complete.")

if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"\n❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

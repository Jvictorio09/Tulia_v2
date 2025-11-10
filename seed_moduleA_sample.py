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
        """0:00 All right, let's get into it.
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
6:24 Thanks so much for tuning in."""
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
        "lesson_transcript": """0:00: All right, let's just jump right in.
0:01: We have all been there, right?
0:03: The big job interview, that huge presentation, or maybe that really tough conversation
you've been putting off, you know, those moments where it feels like every single word carries a
tonne of weight.
0:13: Today we're going to break down exactly how you can turn that high pressure anxiety into
high performance poise.
0:20: Man, does this hit close to home?
0:22: It's that awful feeling when all your brilliant, perfectly rehearsed thoughts just vanish the
second you open your mouth.
0:29: But listen, this is not a personal failure.
0:32: It's a completely universal human response to pressure.
0:36: And trust me, it's a response you can absolutely learn to manage and even master.
0:41: So what is it that flips the switch?
0:43: What turns a totally normal chat into a nail-biting high stakes moment?
0:48: It's not just about what you're talking about.
0:50: It's about a very specific mix of factors that our brains are just hardwired to freak out
about.
0:56: Yeah, it really boils down to these three things hitting you all at once.
1:00: First, you've got pressure, that ticking clock, that feeling of this has to happen now.
1:06: Then there's visibility.
1:07: You are totally aware that you're being watched, maybe judged or evaluated.
1:11: And finally, the big one, irreversibility.
1:14: The knowledge that once the words are out, that's it.
1:17: You can't just hit undo.
1:18: When those three things come together, that's when even the most confident person
starts to feel the heat.
1:23: OK, so to figure out how to handle this, we first need to peek under the hood and see
what's actually happening inside our heads.
1:30: You know, why do our palms get sweaty?
1:31: Why does our mind just go completely blank?
1:34: Well, it all comes down to some very old and very powerful brain wiring.
1:40: Let's talk about a little part of your brain called the amygdala.
1:43: Think of it as your ancient internal threat detector.
1:46: Now, here's the crazy part.
1:47: When it senses a high stakes situation, it doesn't see a performance review, it sees a lion
in the grass.

1:54: I mean, I remember giving a toast at a My friend's wedding, a totally safe, happy place,
but my amygdala fired up like I was about to be attacked.
2:01: It floods your system with adrenaline, your heart starts pounding, your focus narrows,
which is great if you need to run for your life, but absolutely terrible for delivering a thoughtful,
coherent message.
2:11: And this leads to this massive internal conflict, this mental tug of war we all feel.
2:17: See, you're dealing with two types of mental effort at the same time.
2:20: You've got the emotional load, that's all the energy you're spending just trying to manage
your own anxiety and fear.
2:26: Then there's the cognitive load, the actual brainpower you need to think, recall facts, and
speak clearly.
2:32: The problem is, as your emotional load skyrockets, it literally steals all the bandwidth from
your cognitive load.
2:38: Your brain basically runs out of RAM.
2:41: OK, so we get the problem.
2:42: Our brains can definitely work against us when the pressure is on.
2:45: But what if I told you there was a simple formula, a way to diagnose the situation and
more importantly, a way to take back command?
2:53: Well, there is.
2:54: Let's get into it.
2:55: So this is the PI formula, and honestly, it's an incredibly powerful little tool.
3:00: It helps you break down any situation into three key parts.
3:03: P is for pressure.
3:04: How intense is this?
3:06: I is for impact.
3:07: What are the real consequences here?
3:09: And C, the most important one is for control.
3:12: What parts of this can I actually influence?
3:15: You see, stress peaks when pressure and impact feel huge, but your sense of control
feels tiny.
3:20: The secret isn't to get rid of the pressure, it's to radically increase your sense of control.
3:25: And this right here, this is the whole game.
3:28: Seriously, if you remember one thing, make it this.
3:31: Forget trying to make the pressure magically disappear.
3:33: That's usually impossible anyway.
3:35: The entire strategy is about shifting your focus to the things you can control.
3:39: That feeling that you're in the driver's seat, it's one of the most reliable ways to stay
composed and perform at your best.
3:45: So, how do we do that?
3:47: How do we actually increase that feeling of control?
3:51: Well, it comes down to 3 very practical, very actionable levers you can pull before, during,
and after any high stakes moment.
4:00: Think of this as your complete control toolkit.
4:03: Preparation is everything you do beforehand to build a rock solid foundation.

4:08: Presence is how you manage yourself when you're in the heat of the moment, and
perspective, well, that's how you process the whole thing afterwards, so you're even stronger
next time.
4:16: Let's dive into that first lever, preparation.
4:20: This is your proactive defence.
4:22: Way before you ever walk into that room, get crystal clear on what you want to say and
what you want to happen.
4:27: And don't just think about it, rehearse it.
4:30: Maybe even try to practise under conditions that feel a little bit like the real thing.
4:34: And this is crucial.
4:36: Anticipate the curveballs.
4:37: What questions are they going to ask?
4:39: What objections might pop up?
4:41: Brainstorming answers now means you won't get caught flat-footed later.
4:45: All right, now for presence.
4:46: This is what you do during the moment.
4:49: The simplest, most powerful tool you have is your own breath.
4:52: Seriously, slow, deep breathing helps calm that amygdala response we talked about
earlier.
4:58: And please, don't be afraid of silence.
5:00: A deliberate pause, that's not a sign of weakness or that you forgot your words.
5:04: No, it's a powerful signal to everyone in the room that you are in complete control.
5:09: And finally, we have perspective.
5:11: The moment's over.
5:13: Now, the temptation is to either pop the champagne or more likely beat yourself up over
every little mistake.
5:19: A much better approach is to reflect on it, but without judgement.
5:22: Ask yourself, what went well, what would I do a little differently next time.
5:26: This changes everything.
5:27: It transforms every high stakes moment from some past failed test of your worth into just
a valuable piece of data for your own growth.
5:35: OK, so we've covered the why, the what, and the how.
5:38: We've got the theory, the formula, and the tools.
5:41: Now, let's talk about putting this to work in your own life, starting today.
5:45: This is your homework.
5:47: It's an exercise I call a stakes map.
5:49: It's simple.
5:50: First, identify your personal pressure points.
5:52: Is it talking to senior execs?
5:54: Is it a tight deadline?
5:55: Second, recognise your specific triggers.
5:58: What's the one thing that really makes you tense up?
6:00: Is it a tough question, an interruption?

6:02: And third, based on that, you're going to pick which control lever, preparation, presence,
or perspective, you're going to consciously practise.
6:10: See, this turns a vague feeling of dread into a concrete plan of action.
6:14: Because here's the one thing we all know for sure.
6:17: Another high stakes moment is coming.
6:20: It's just an inevitable and frankly necessary part of growing in your career and in your life.
6:25: But now you have a framework, you have the tools.
6:28: So the question isn't if it will happen, but how you will choose to step into that moment
and take control.""",
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
            """0:00: All right, let's just jump right in.
0:01: You know that feeling, right?
0:03: You're in a huge meeting, maybe giving a big presentation.
0:06: You've got this amazing idea, you lay it all out, and then nothing, just
crickets.
0:11: That silence is just awful.
0:13: Well, today, we're going to dig into the psychology behind why that
happens, and more importantly, how you can make sure that when you
speak, people actually listen.
0:22: You know, this quote, it really nails it.
0:25: We tend to think of communication as something we just send out,
you know, like we're a radio tower broadcasting a signal, but that's not it at
all.
0:33: It's a two-way street.
0:34: It's really about what gets created in the other person's mind.

0:37: And once you get that, I mean really get it, that simple little shift in
perspective.
0:42: Well, it changes everything.
0:44: It's the key to all the stuff we're about to get into.
0:47: OK, so first things first.
0:49: Let's talk about the core problem here.
0:51: Why are best ideas sometimes just vanish into thin air?
0:55: I like to call it the two rooms problem.
0:58: And man, is it frustrating.
0:59: I mean, you've been there, right?
1:01: You're talking, you're explaining everything perfectly, point by logical
point, but you can just see it in their eyes.
1:07: You're not connecting.
1:09: That feeling of disconnect, that's the dragon we're here to slay today.
1:13: And it happens for a really simple reason.
1:15: You're in one room and your audience, they're in a completely
different one.
1:20: See, we all get ready for the physical room.
1:22: We make sure our slides look amazing.

1:23: We've got our notes all lined up, but that's not where the magic
happens.
1:27: The real communication, the stuff that matters, it happens in the
mental room.
1:32: In that room, well, it's invisible.
1:34: It's filled with all the stuff you can't see.
1:36: The private goals, their secret fears, their assumptions about you
and your topic.
1:40: To really master communication, you've got to learn how to open the
door and walk into that room.
1:45: So the big question is, how do you even find your way around in that
mental room?
1:51: Well, the first tool in our toolbox is learning to spot the patterns, the
predictable ways people think and listen.
1:58: Now look, obviously everyone is different, but we all kind of have
these default settings, these go to communication styles, and the goal here
isn't to stick people in boxes, not at all.
2:09: It's just to get good at spotting these tendencies, so you can adjust
what you're saying, you know, in real time.
2:15: That's how you make your message actually hit home.

2:18: This is all based on something called the Soys model, and it's super
useful.
2:22: It basically says you can find 4 key types in pretty much any group.
2:26: You've got your get it done drivers, your show me the numbers
analyticals, your let's all get along amiables, and your dream big
expressives.
2:33: So let's figure out how to speak to each one of them.
2:36: OK, the driver, picture this.
2:39: The person in the meeting who keeps glancing at their watch.
2:41: Yeah, that's them.
2:43: For them, time is money and they have zero patience for a long
rambling story.
2:48: So you don't start with the backstory, you get straight to the point.
2:51: You lead with the punch line.
2:52: Here's the deal, we can cut costs by 15% and we can have it done
by the end of the quarter.
2:56: Boom, that's what they need to hear.
2:59: Next up, the analytical.
3:00: This is the person whose hand is always up asking, but how does
that work?

3:05: or why are we doing it this way?
3:06: And look, they're not trying to be annoying.
3:08: Their brain is just wired to need proof.
3:11: They need to see the logic to trust you.
3:13: So give them the data, show them the spreadsheet, walk them
through your thought process step by step.
3:18: They have to believe in the how before they'll ever buy into the what.
3:21: Then you've got the amiable.
3:23: They're listening with their heart.
3:24: While you're talking numbers and deadlines, they're quietly
wondering, but what about the team?
3:29: How is this going to affect people?
3:31: So you have to speak to that.
3:32: You have to show them you care.
3:34: Say something like, look, I get it.
3:36: This is a huge change, and my number one priority is making sure
we all get through this together as a team.
3:41: And finally, the expressive.
3:44: Ah, these are the visionaries.

3:46: They're the ones leaning forward in their chair, their eyes lighting up
when you talk about what's possible.
3:51: Don't you dare start with the nitty gritty details, you'll lose them
instantly.
3:53: You've got to paint them a picture of the future.
3:56: Get them excited about the grand vision, and I promise you they will
be your loudest cheerleaders.
4:00: All right, so just being able to spot those four styles, that's a massive
step forward.
4:05: Huge.
4:06: But if you want to really connect, we've got to go deeper.
4:10: We need to get past what they do and get into why they do it, right
into the mind itself.
4:15: And for that, there's a great tool called the MAP framework.
4:20: So MAP, it stands for motives, assumptions, and perceptions.
4:24: And think of it like this.
4:26: This isn't about their external actions.
4:28: This is about their internal operating system, the software that's
running in the background and driving everything they do.
4:35: It's basically a map to how they see the world.

4:38: And here's the kicker.
4:39: These three things are always running, like filters on a camera.
4:43: Their motives are constantly asking, Is this person with me or against
me?
4:46: Their assumptions, man, they can shut down your idea before you
even finish your first sentence, and their perceptions of you, your tone, your
body language, that stuff often speaks way louder than your actual words.
4:57: If you don't get these three things aligned, it doesn't matter how great
your logic is, your message is going to fall flat every time.
5:03: OK, so we have these great theories, right?
5:05: The 4 styles, the matte framework, all sounds good.
5:08: But how do you actually use this stuff in the real world, you know,
when you're live in the moment with a room full of people staring back at
you.
5:15: Well, it really comes down to building a few key micros skills.
5:19: You're not staring anyone down, you're just scanning, making quick
real eye contact with different people.
5:24: You learn to watch for that sudden stillness, you know, when
everyone just freezes, that means something.
5:29: It could be tension or it be intense focus.

5:32: You notice who's writing things down.
5:34: That's a great sign.
5:35: And you start to just sense the energy.
5:37: Is the room buzzing or people leaning forward, or can you feel the
tension, see the crossed arms, that gut feeling you have, that's not just a
feeling, that's real data.
5:46: I love this quote from Nancy Doherty, because it just perfectly sums
up the whole mindset shift we're talking about.
5:52: Look, your job isn't to be the hero on stage.
5:55: Your job is to make the audience the hero of their own story.
5:58: You're the guide who gives them the tool, the insight, the clarity they
need to go slay their own dragon.
6:04: Your success isn't about how well you presented, it's about how
much they accomplished after you presented.
6:10: All right, let's pull all these threads together now because the
absolute top tier skill, the real mastery level of communication, is finding
that perfect balance between two things, empathy and authority.
6:24: See, if you're all empathy and no authority, people might like you, but
they'll see you as wishy-washy, maybe even weak.

6:30: But if you're all authority and no empathy, well, you get people who
do what you say, but only because they have to.
6:36: You get compliance, but you don't get commitment.
6:39: Their bodies are in the room, but their hearts and minds are checked
out.
6:42: So what's the secret?
6:43: Here's a simple formula to get that balance just right.
6:46: Connect first, then deliver, then engage.
6:50: And what's wild is that neuroscience actually proves this works.
6:54: Our brains are hardwired to trust people more when we feel warmth
and connection before we see their competence.
7:00: So you always, always start by connecting.
7:03: Show them you're on their side.
7:04: Then you deliver your core message with confidence and authority,
and to finish, you bring them in, you engage them, you make them part of
the solution.
7:12: And that really brings us back to the core idea I want to leave you
with.
7:15: It's so easy to focus on what we're going to say, to perfect our script,
but that's only half the job.

7:21: The real work, the true mastery is in deeply, truly understanding who
you're talking to, because when you can do that, you'll stop just talking at
people and you'll finally, finally be heard."""
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
            """0:00: Hey everyone, and welcome.
0:01: Today we're gonna dive into one of the most powerful and honestly most invisible tools
you have in your professional life, your personal communication style.
0:10: We've all got one, right?
0:11: But really understanding it, especially when the pressure is on, well, that can be the game
changer between having real influence and just not landing your message.
0:21: You know, the management guru Peter Drucker really hit the nail on the head with this
one.
0:26: Before you can even think about managing a team or a project or some high stakes
conversation, you've got to be able to manage yourself, and that whole journey, it starts right
here with self knowledge.
0:38: It's the bedrock for everything we're about to talk about.
0:41: Think about it like this, your communication style is kind of like an energy or a rhythm that
you bring into a room.
0:48: Long before people have fully processed the actual words you're saying, they're already
responding to your tone, your pace, your whole presence.
0:55: This trace you leave behind, that's what shapes how they see your credibility and your
competence.
1:01: Yeah, so this is the real question, isn't it?
1:04: You might feel totally clear and confident when things are calm, but what about when
you're in a tough negotiation or you're thrown into a surprise presentation or you have to give
some really difficult feedback?
1:16: That's when our best intentions can just get lost and our impact is not at all what we
hoped for.
1:22: So when the stakes get high, our brains look for the easy way out.
1:26: They fall back on our deepest, most ingrained habits.
1:29: And without awareness, these default settings can be the exact opposite of what the
situation actually needs.
1:35: This gap, you know, between who we want to be and how we actually show up, that's
what we call the pressure shadow.
1:42: OK, so to get a handle on our habits, we can use a really simple but powerful model of
four core communication styles.
1:49: Now, listen, this is not about putting you in a box, it's about recognizing your dominant
patterns, your natural voice, so you can learn to use it and more importantly, flex from it on
purpose.

2:00: All right, let's break this down real quick.
2:02: Do you see yourself anywhere here?
2:04: The commanding style, that's all about drive and clarity, the analytical, precise, structured,
the relational style is fantastic at building trust, and the expressive, they inspire with pure
energy.
2:17: Each one has these incredible strengths, but also a very unique blind spot that really only
shows up under pressure, which one kind of feels like your home base.
2:27: And this is absolutely crucial.
2:29: There is no best style.
2:31: The most influential people out there don't have one perfect style.
2:35: They know how to adapt their approach to the moment.
2:37: It's really about adding more tools to your tool kit, not throwing out the one you already
have.
2:42: The real goal here is flexibility.
2:45: So let's go a little deeper into that pressure shadow thing I mentioned.
2:48: This is what happens when our greatest strengths, once you put them under stress, get
exaggerated and turn into, well, distortions.
2:55: Our best qualities can literally become our worst liabilities if we're not paying attention.
3:01: You can see it happen right here for a commanding style that natural confidence can just
flip a switch and become overbearing dominance, shutting other people down.
3:10: And for the analytical style, that gift for thorough analysis can turn into a crippling analysis
paralysis where no decision ever gets made.
3:19: And here's the other side of that coin, that wonderful empathy from a relational style.
3:24: Under stress, it can turn into a kind of conflict avoidant compliance, and the expressive's
infectious enthusiasm can just become a whirlwind of unfocused ideas, a total distraction from
what needs to get done.
3:36: Just seeing your pattern is the first step to getting a handle on it.
3:40: Now for those of you who want to go even deeper, the style metrics is a fantastic tool.
3:44: It basically maps these styles on two axes, how assertive you are and how responsive
you are.
3:50: This helps us see communication not as some fixed thing, but as a dynamic behavior.
3:55: You can consciously choose to dial your assertiveness up or dial your responsiveness
down, depending on what's needed.
4:00: Another classic model is the Jahari window.
4:03: What it shows is that a huge part of our impact, what it calls our blind area, is totally
visible to other people, but not to us.
4:11: And the only way to shrink that blind spot is simple, though, you know, not always easy,
it's actively asking for feedback so we can start to see ourselves the way others do, which
brings us to the number one question people always ask.
4:23: If I'm changing my style to fit a situation, am I being inauthentic?
4:28: Am I being fake?
4:29: And that is a fantastic question.
4:32: The answer, if you approach it the right way, is a definite no.
4:36: I just love this definition.

4:37: See, authenticity isn't about being rigidly the same person in every single context.
4:42: That's not authenticity, that's just inflexibility.
4:46: True authenticity is about keeping the integrity between your core values and your
actions, right there in that specific situation.
4:54: So here's the guiding principle to hold on to your core values, your integrity, those are
non-negotiable.
5:00: They stay fixed, but how you express them, that can and it absolutely should flex.
5:06: You can be direct without being disrespectful.
5:08: You can be empathetic without giving up on accountability.
5:11: OK, so we've gone from awareness to understanding.
5:14: Now let's get to the good stuff, action.
5:16: How do we actually turn all this insight into a real tangible skill?
5:20: Well, it comes down to a pretty simple practical framework.
5:24: Here's your plan.
5:25: First, know where your style is a huge asset and just lean into it, amplify those strengths.
5:30: Second, you've got to intentionally practice the behaviors that balance out your blind
spots.
5:34: So if you're a commanding type, practice pausing and asking a question.
5:37: If you're relational, practice stating your own need directly.
5:40: And finally, rehearse, visualize or even role play those tough situations to build a muscle
memory for a more balanced response.
5:47: When it comes right down to it, this whole journey is about moving from unconscious
habit to conscious choice.
5:53: Because every single time you speak, you leave a signature.
5:56: It tells people who you are, what you care about, and what it's like to be in the room with
you.
6:01: You have all the power to decide what that signature looks like.
6:04: So I'll leave you with this to think about.
6:06: Your style is your signature.
6:08: After you've left the room, after the call has ended, what story is it going to tell about you?
6:13: Thanks for tuning in."""
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
            """0:00: All right, let's talk about a huge challenge we all face.
0:04: Why is it that sometimes our most important ideas, the ones we've worked on for weeks,
just fall completely flat?
0:10: Today we're gonna break down how a super simple framework can make sure you're
heard, understood, and actually remembered every single time.
0:18: You know that feeling, right?
0:19: You're in a big meeting, you've got your brilliant idea all lined up and you start talking, but
you can just see the eyes glazing over.
0:26: You're sending out a signal, but it feels like no one's receiving it.
0:30: So what is going on here?
0:32: Well, the main villain in this story is something the linguist Steven Pinker calls the curse of
knowledge.
0:38: It's this weird paradox, the more of an expert you become, The harder it is to remember
what it was like not to know all that stuff.
0:46: Your own expertise, the very thing that makes you credible can actually become your
biggest communication roadblock.
0:52: So let's look at when this curse gets even more powerful.
0:55: It turns out that pressure is a massive trigger for communication breakdown.
0:59: You know, the more conversation matters, the harder it seems to be to just say things
clearly.
1:04: And there's some real brain science behind this.
1:07: When we're stressed out, our working memory.
1:09: Think of it as your brain's available RAM, it literally shrinks.
1:12: This is why we start to ramble, why we overexplain, and why we talk in circles.
1:17: We create this cognitive drag for our audience.
1:19: We're trying so, so hard to be clear, but we just end up creating a ton of confusion.
1:24: And that stress leads to these 4 classic clarity killers.
1:28: Any of these sound familiar?
1:29: You've got data dumping where you just throw every fact you know at someone instead of
the 3 that really matter.
1:34: There's ambiguity, using jargon, and just assuming everyone gets it, over politeness
where you water down your message so much it loses its punch, and finally, an unstructured
flow, which is basically a stream of consciousness with no clear beginning, middle, or end.
1:48: OK, so that's the problem, and it's a big one, but the good news is there's a science to
solving it.

1:54: If we want to design messages that actually stick, we've got to understand how the
human brain is wired to listen and process information in the first place.
2:03: First things first, our brains have a hard limit.
2:06: Way back in the 50s, a psychologist named George Miller discovered what he called the
magical number 7, plus or minus 2.
2:12: Basically, our working memory can only handle about 5 to 9 chunks of information at a
time.
2:17: So if you throw 10 points at someone, their brain is literally physically incapable of
catching them all.
2:22: And we have to be fast.
2:24: Research shows that a listener's focus pretty much falls off a cliff after about 90 seconds if
you don't change something up, like ask a question, pause, or show them something new.
2:33: We're working with a really short attention span here, so precision is everything.
2:38: So what does all this science boil down to?
2:40: It's actually super simple.
2:42: Given our brain's limits, the absolute best strategy is to build your entire message around
just three core ideas, not 7, not 53, it is the magic number for making things stick.
2:55: And this idea leads us to a really powerful repeatable system I want to show you, the 3 by
3 message framework.
3:01: It's designed to take the messy, confusing art of communication and turn it into a simple
science.
3:06: Just look at how simple and effective this is.
3:09: You start with phase one, your core idea.
3:12: Ask yourself what is the one single thing they must remember?
3:15: Then phase two, your three supporting points.
3:18: Why should they believe me?
3:20: And finally, phase 3, a crystal clear call to action.
3:23: What do I want them to do next?
3:26: It's a perfect road map for any message.
3:29: The easiest way to visualize it is as a pyramid.
3:31: You've got that single sharp point at the top, that's your core idea, and it's all held up by a
super stable foundation of your three supporting pillars.
3:41: It's logical, it's strong, and it's incredibly easy for a listener's brain to follow along.
3:46: Now, let's zoom in on the very tip of that pyramid because it's the most critical part of this
whole thing.
3:52: We call it the signal sentence, and it might just be the most powerful 20 or so words you'll
say in your entire presentation.
3:59: A really great signal sentence has three essential ingredients.
4:02: It starts with the topic what are we talking about?
4:05: Then it introduces tension.
4:07: Why does this matter right now?
4:08: And it lands with the takeaway.
4:10: What's the key benefit or conclusion you want them to walk away with?
4:14: Here's a perfect example in action.

4:16: Today I'll show you how our new workflow, boom, that's your topic, saves time and
reduces errors, there's your tension and keeps our clients happier, and that's the takeaway.
4:26: In one clean sentence, you've set the stage for the entire conversation.
4:30: OK, this brings us to our final and maybe the most important principle of all.
4:34: Real mastery in communication isn't about adding more stuff, it's about having the
discipline to take away everything that isn't absolutely essential.
4:42: I mean, just look at the difference here.
4:45: The before is drowning in corporate jargon.
4:47: The after, it's direct, it's memorable, it's powerful, it says the exact same thing, but it lands
with way more confidence and credibility.
4:56: Being brief actually builds trust.
4:58: So you can almost think of clarity as a simple equation.
5:01: It's relevance plus rhythm.
5:04: Relevance means you filter everything and only share what your audience truly needs to
know.
5:09: And rhythm is all about delivering those ideas in a cadence, a beat that's easy for the
brain to follow.
5:15: So what do you think is the single most powerful and most underused tool we have for
creating that rhythm?
5:20: It's silence.
5:22: A strategic pause isn't awkward, it's not a sign you've lost your place, it's punctuation.
5:26: It's a nonverbal cue that tells your listeners's brain, hey, pay attention, this part is
important.
5:31: Stop and process what you just heard.
5:33: It is an active tool for creating clarity.
5:36: In fact, studies have shown that a pause of about 2 seconds after you make a key point
dramatically improves how much people understand and remember, it gives the idea space to
land.
5:47: And that's really what this all comes down to.
5:49: This isn't about dumbing down your complex ideas.
5:52: Clarity isn't about removing all the details.
5:54: It's about providing a clear path, a direction for your listener to follow.
5:58: It's about you doing the hard work of thinking, so they don't have to.
6:02: So my question for you is, what direction will you provide next time you speak?"""
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

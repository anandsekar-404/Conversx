"""
ConversX - Communication Practice Scenarios & Daily Challenges.
Provides curated scenarios for all practice modes and deterministic daily challenge selection.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional


PRACTICE_MODES = [
    {
        "id": "casual",
        "name": "Casual Conversation",
        "description": "Practice everyday social speaking, small talk, and informal introductions.",
        "icon": "chat",
        "color": "#06b6d4",
    },
    {
        "id": "interview",
        "name": "Interview Practice",
        "description": "Master behavioral and technical job interview questions with structured responses.",
        "icon": "briefcase",
        "color": "#6366f1",
    },
    {
        "id": "presentation",
        "name": "Presentation Practice",
        "description": "Deliver engaging project pitches, technical explanations, and clear overviews.",
        "icon": "presentation",
        "color": "#8b5cf6",
    },
    {
        "id": "professional",
        "name": "Professional Communication",
        "description": "Handle workplace discussions, polite disagreements, and professional requests.",
        "icon": "user-check",
        "color": "#10b981",
    },
    {
        "id": "challenge",
        "name": "Daily Challenge",
        "description": "Complete today's targeted communication prompt to build your daily streak.",
        "icon": "award",
        "color": "#f59e0b",
    },
]

SCENARIOS: List[Dict[str, Any]] = [
    # A. Casual Conversation
    {
        "id": "cas_01",
        "mode": "casual",
        "title": "Meeting a New Person",
        "prompt": "You are at a community tech meetup and see someone standing alone by the refreshment table. Introduce yourself and start a friendly conversation.",
        "guidance": "Mention your name, ask an open-ended question about what brought them to the event, and keep a warm, approachable tone.",
        "target_word_count": (25, 80),
    },
    {
        "id": "cas_02",
        "mode": "casual",
        "title": "Talking with a Classmate / Colleague",
        "prompt": "A teammate seemed stressed about an upcoming deadline during yesterday's meeting. Check in on them casually and offer friendly support.",
        "guidance": "Acknowledge the workload with empathy, avoid prying, and make your offer of assistance clear and low-pressure.",
        "target_word_count": (30, 90),
    },
    {
        "id": "cas_03",
        "mode": "casual",
        "title": "Introducing Yourself at an Event",
        "prompt": "Give a quick 30-second casual introduction of who you are, what you enjoy working on, and one fun hobby or interest.",
        "guidance": "Keep it concise, energetic, and authentic without sounding like a formal resume reading.",
        "target_word_count": (35, 100),
    },
    {
        "id": "cas_04",
        "mode": "casual",
        "title": "Asking for Help Nicely",
        "prompt": "You are struggling to understand a project requirement. Ask a peer if they have five minutes to help point you in the right direction.",
        "guidance": "Be specific about what you are stuck on and show that you value their time.",
        "target_word_count": (25, 75),
    },
    {
        "id": "cas_05",
        "mode": "casual",
        "title": "Making Small Talk",
        "prompt": "You are sharing an elevator or waiting in a coffee line with a speaker from the conference. Make pleasant small talk about the morning keynote.",
        "guidance": "Reference a specific memorable highlight from the talk and ask for their perspective.",
        "target_word_count": (20, 70),
    },
    {
        "id": "cas_06",
        "mode": "casual",
        "title": "Starting a Conversation in a New Group",
        "prompt": "You joined a study group or committee for the first time. Greet the members and ask what topic they are currently discussing.",
        "guidance": "Express enthusiasm about joining and invite someone to brief you on the current topic.",
        "target_word_count": (25, 80),
    },

    # B. Interview Practice
    {
        "id": "int_01",
        "mode": "interview",
        "title": "Tell Me About Yourself",
        "prompt": "Interview Question: 'Can you walk me through your background and tell me a bit about yourself?'",
        "guidance": "Use the Present-Past-Future framework: where you are today, key past achievements, and why this role excites you next.",
        "target_word_count": (50, 150),
    },
    {
        "id": "int_02",
        "mode": "interview",
        "title": "What Are Your Strengths?",
        "prompt": "Interview Question: 'What do you consider your greatest professional strength, and how has it helped your team?'",
        "guidance": "Name one clear strength, give a concrete mini-example demonstrating it, and explain the positive impact on the team.",
        "target_word_count": (45, 130),
    },
    {
        "id": "int_03",
        "mode": "interview",
        "title": "Why Should We Hire You?",
        "prompt": "Interview Question: 'We have several strong candidates for this position. Why should we choose you?'",
        "guidance": "Focus on your unique combination of skills, genuine passion for their mission, and track record of delivering outcomes.",
        "target_word_count": (50, 140),
    },
    {
        "id": "int_04",
        "mode": "interview",
        "title": "Explain a Challenging Project",
        "prompt": "Interview Question: 'Tell me about a project that was difficult or did not go according to plan. How did you handle it?'",
        "guidance": "Use the STAR method (Situation, Task, Action, Result). Focus heavily on the actions you took and the lesson learned.",
        "target_word_count": (60, 160),
    },
    {
        "id": "int_05",
        "mode": "interview",
        "title": "What is Your Biggest Weakness?",
        "prompt": "Interview Question: 'What is an area of growth or a weakness you are actively working to improve?'",
        "guidance": "Pick a genuine professional skill, acknowledge it honestly, and describe the specific steps you are taking to overcome it.",
        "target_word_count": (45, 130),
    },
    {
        "id": "int_06",
        "mode": "interview",
        "title": "Where Do You See Yourself in Five Years?",
        "prompt": "Interview Question: 'Where do you see yourself professionally five years from now?'",
        "guidance": "Highlight realistic career growth, continuous skill mastery, and increasing leadership or technical contribution.",
        "target_word_count": (45, 120),
    },

    # C. Presentation Practice
    {
        "id": "pre_01",
        "mode": "presentation",
        "title": "Explain a Technical Topic Simply",
        "prompt": "Present an overview of an API (Application Programming Interface) or Cloud Computing as if speaking to a high school student.",
        "guidance": "Use an relatable analogy (e.g., restaurant menu/waiter for an API), avoid dense jargon, and verify clarity.",
        "target_word_count": (50, 150),
    },
    {
        "id": "pre_02",
        "mode": "presentation",
        "title": "Present Your Project Elevator Pitch",
        "prompt": "Give a 60-second elevator pitch for ConversX or your favorite software application to potential investors.",
        "guidance": "State the problem, present your unique solution, highlight key benefits, and close with a memorable vision.",
        "target_word_count": (50, 140),
    },
    {
        "id": "pre_03",
        "mode": "presentation",
        "title": "1-Minute Introduction to a Keynote",
        "prompt": "You are introducing a distinguished guest speaker at an engineering seminar. Deliver a compelling 1-minute welcome speech.",
        "guidance": "Acknowledge the speaker's accomplishments, set anticipation for the topic, and invite a warm round of applause.",
        "target_word_count": (40, 120),
    },
    {
        "id": "pre_04",
        "mode": "presentation",
        "title": "Explain Cybersecurity to Non-Technical Users",
        "prompt": "Explain why two-factor authentication (2FA) and strong passwords matter to someone who is unfamiliar with computer security.",
        "guidance": "Use clear analogies (e.g., double lock on a front door), emphasize personal safety, and offer a simple recommendation.",
        "target_word_count": (50, 140),
    },

    # D. Professional Communication
    {
        "id": "pro_01",
        "mode": "professional",
        "title": "Asking a Professor / Manager for Permission",
        "prompt": "Request permission from your manager or professor to attend a 2-day professional development workshop during work hours.",
        "guidance": "Explain how attending benefits your team or coursework, propose a plan to cover your responsibilities, and be polite.",
        "target_word_count": (45, 130),
    },
    {
        "id": "pro_02",
        "mode": "professional",
        "title": "Writing a Professional Request",
        "prompt": "Ask a cross-functional partner for access to project documentation that is blocking your work.",
        "guidance": "Be polite, specify the exact documents needed, explain why it's needed now, and provide a clear timeline.",
        "target_word_count": (35, 110),
    },
    {
        "id": "pro_03",
        "mode": "professional",
        "title": "Handling Disagreement Respectfully",
        "prompt": "A colleague proposed a technical architecture that you believe will not scale under high traffic. Express your disagreement constructively.",
        "guidance": "Validate their effort, present data or technical reasoning without personal attacks, and propose an alternative to evaluate together.",
        "target_word_count": (50, 140),
    },
    {
        "id": "pro_04",
        "mode": "professional",
        "title": "Asking for Clarification on Vague Feedback",
        "prompt": "You received feedback saying 'This report needs to be better'. Write a polite response asking for specific actionable guidance.",
        "guidance": "Thank them for the feedback, avoid defensiveness, and request specific examples or sections they would like revised.",
        "target_word_count": (35, 110),
    },
    {
        "id": "pro_05",
        "mode": "professional",
        "title": "Delivering Constructive Feedback to a Peer",
        "prompt": "A peer's code submission frequently lacks unit tests, creating delays in review. Provide helpful feedback encouraging better test coverage.",
        "guidance": "Focus on the shared goal of team speed and code quality, mention specific test patterns that help, and offer to collaborate.",
        "target_word_count": (45, 130),
    },
]

DAILY_CHALLENGES: List[Dict[str, Any]] = [
    {
        "id": "dc_01",
        "title": "The 30-Second Project Summary",
        "prompt": "Explain what your primary project does and who it helps in 30 to 50 words without using any filler words.",
        "focus": "Clarity & Filler Control",
        "tip": "State the problem in sentence one, and your solution in sentence two.",
        "target_word_count": (30, 60),
    },
    {
        "id": "dc_02",
        "title": "Zero-Filler Self Introduction",
        "prompt": "Introduce yourself to a potential employer or client without using 'like', 'um', 'actually', or 'basically'.",
        "focus": "Confidence & Filler Control",
        "tip": "Pause silently between thoughts instead of saying 'um' or 'like'.",
        "target_word_count": (35, 75),
    },
    {
        "id": "dc_03",
        "title": "Teach a Concept to a Beginner",
        "prompt": "Explain what an algorithm is in plain English to someone who has never coded before.",
        "focus": "Clarity & Vocabulary",
        "tip": "Compare an algorithm to a step-by-step recipe for baking a cake.",
        "target_word_count": (40, 90),
    },
    {
        "id": "dc_04",
        "title": "Respectful Disagreement",
        "prompt": "Disagree with a decision to cancel remote work Fridays, while staying 100% professional and collaborative.",
        "focus": "Professionalism & Respectfulness",
        "tip": "Highlight productivity data and suggest a trial period rather than expressing frustration.",
        "target_word_count": (45, 110),
    },
    {
        "id": "dc_05",
        "title": "Crisp Executive Summary",
        "prompt": "Summarize a successful feature launch in three sentences: Problem, Solution, and Measurable Outcome.",
        "focus": "Structure & Professionalism",
        "tip": "Use action verbs like 'delivered', 'reduced', or 'optimized'.",
        "target_word_count": (35, 80),
    },
]


def get_all_scenarios(mode: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all scenarios, optionally filtered by practice mode."""
    if not mode or mode == "all":
        return list(SCENARIOS)
    return [s for s in SCENARIOS if s["mode"] == mode]


def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Lookup a scenario by its unique identifier."""
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return dict(s)
    for c in DAILY_CHALLENGES:
        if c["id"] == scenario_id:
            return {**c, "mode": "challenge"}
    return None


def get_today_challenge() -> Dict[str, Any]:
    """Deterministically select today's challenge based on day-of-year."""
    day_of_year = datetime.datetime.now(datetime.timezone.utc).timetuple().tm_yday
    idx = day_of_year % len(DAILY_CHALLENGES)
    challenge = dict(DAILY_CHALLENGES[idx])
    challenge["mode"] = "challenge"
    challenge["date"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return challenge

/**
 * ConversX Practice Scenarios & Daily Challenges (Client-Side Module).
 */

export const PRACTICE_MODES = [
  {
    id: 'casual',
    name: 'Casual Conversation',
    description: 'Practice everyday social speaking, small talk, and informal introductions.',
    icon: '💬',
    color: '#06b6d4'
  },
  {
    id: 'interview',
    name: 'Interview Practice',
    description: 'Master behavioral and technical job interview questions with structured responses.',
    icon: '💼',
    color: '#6366f1'
  },
  {
    id: 'presentation',
    name: 'Presentation Practice',
    description: 'Deliver engaging project pitches, technical explanations, and clear overviews.',
    icon: '📊',
    color: '#8b5cf6'
  },
  {
    id: 'professional',
    name: 'Professional Communication',
    description: 'Handle workplace discussions, polite disagreements, and professional requests.',
    icon: '👔',
    color: '#10b981'
  },
  {
    id: 'challenge',
    name: 'Daily Challenge',
    description: "Complete today's targeted communication prompt to build your daily streak.",
    icon: '🏆',
    color: '#f59e0b'
  }
];

export const SCENARIOS = [
  // Casual
  {
    id: 'cas_01',
    mode: 'casual',
    title: 'Meeting a New Person',
    prompt: 'You are at a community meetup and see someone standing alone by the refreshment table. Introduce yourself and start a friendly conversation.',
    guidance: 'Mention your name, ask an open-ended question about what brought them to the event, and keep a warm, approachable tone.',
    targetWordCount: [25, 80]
  },
  {
    id: 'cas_02',
    mode: 'casual',
    title: 'Talking with a Classmate / Colleague',
    prompt: "A teammate seemed stressed about an upcoming deadline during yesterday's meeting. Check in on them casually and offer friendly support.",
    guidance: 'Acknowledge the workload with empathy, avoid prying, and make your offer of assistance clear and low-pressure.',
    targetWordCount: [30, 90]
  },
  {
    id: 'cas_03',
    mode: 'casual',
    title: 'Introducing Yourself at an Event',
    prompt: 'Give a quick 30-second casual introduction of who you are, what you enjoy working on, and one fun hobby or interest.',
    guidance: 'Keep it concise, energetic, and authentic without sounding like a formal resume reading.',
    targetWordCount: [35, 100]
  },
  {
    id: 'cas_04',
    mode: 'casual',
    title: 'Asking for Help Nicely',
    prompt: 'You are struggling to understand a project requirement. Ask a peer if they have five minutes to help point you in the right direction.',
    guidance: 'Be specific about what you are stuck on and show that you value their time.',
    targetWordCount: [25, 75]
  },
  {
    id: 'cas_05',
    mode: 'casual',
    title: 'Making Small Talk',
    prompt: 'You are waiting in a coffee line with a speaker from the conference. Make pleasant small talk about the morning keynote.',
    guidance: 'Reference a specific memorable highlight from the talk and ask for their perspective.',
    targetWordCount: [20, 70]
  },
  {
    id: 'cas_06',
    mode: 'casual',
    title: 'Starting a Conversation in a New Group',
    prompt: 'You joined a study group or committee for the first time. Greet the members and ask what topic they are currently discussing.',
    guidance: 'Express enthusiasm about joining and invite someone to brief you on the current topic.',
    targetWordCount: [25, 80]
  },

  // Interview
  {
    id: 'int_01',
    mode: 'interview',
    title: 'Tell Me About Yourself',
    prompt: "Interview Question: 'Can you walk me through your background and tell me a bit about yourself?'",
    guidance: 'Use the Present-Past-Future framework: where you are today, key past achievements, and why this role excites you next.',
    targetWordCount: [50, 150]
  },
  {
    id: 'int_02',
    mode: 'interview',
    title: 'What Are Your Strengths?',
    prompt: "Interview Question: 'What do you consider your greatest professional strength, and how has it helped your team?'",
    guidance: 'Name one clear strength, give a concrete mini-example demonstrating it, and explain the positive impact on the team.',
    targetWordCount: [45, 130]
  },
  {
    id: 'int_03',
    mode: 'interview',
    title: 'Why Should We Hire You?',
    prompt: "Interview Question: 'We have several strong candidates for this position. Why should we choose you?'",
    guidance: 'Focus on your unique combination of skills, genuine passion for their mission, and track record of delivering outcomes.',
    targetWordCount: [50, 140]
  },
  {
    id: 'int_04',
    mode: 'interview',
    title: 'Explain a Challenging Project',
    prompt: "Interview Question: 'Tell me about a project that was difficult or did not go according to plan. How did you handle it?'",
    guidance: 'Use the STAR method (Situation, Task, Action, Result). Focus heavily on the actions you took and the lesson learned.',
    targetWordCount: [60, 160]
  },
  {
    id: 'int_05',
    mode: 'interview',
    title: 'What is Your Biggest Weakness?',
    prompt: "Interview Question: 'What is an area of growth or a weakness you are actively working to improve?'",
    guidance: 'Pick a genuine professional skill, acknowledge it honestly, and describe the specific steps you are taking to overcome it.',
    targetWordCount: [45, 130]
  },
  {
    id: 'int_06',
    mode: 'interview',
    title: 'Where Do You See Yourself in Five Years?',
    prompt: "Interview Question: 'Where do you see yourself professionally five years from now?'",
    guidance: 'Highlight realistic career growth, continuous skill mastery, and increasing leadership or technical contribution.',
    targetWordCount: [45, 120]
  },

  // Presentation
  {
    id: 'pre_01',
    mode: 'presentation',
    title: 'Explain a Technical Topic Simply',
    prompt: 'Present an overview of an API (Application Programming Interface) or Cloud Computing as if speaking to a high school student.',
    guidance: 'Use an relatable analogy (e.g., restaurant menu/waiter for an API), avoid dense jargon, and verify clarity.',
    targetWordCount: [50, 150]
  },
  {
    id: 'pre_02',
    mode: 'presentation',
    title: 'Elevator Pitch for Your Project',
    prompt: 'Give a 60-second elevator pitch for ConversX or your favorite software application to potential investors.',
    guidance: 'State the problem, present your unique solution, highlight key benefits, and close with a memorable vision.',
    targetWordCount: [50, 140]
  },
  {
    id: 'pre_03',
    mode: 'presentation',
    title: '1-Minute Introduction to a Keynote',
    prompt: 'You are introducing a distinguished guest speaker at an engineering seminar. Deliver a compelling 1-minute welcome speech.',
    guidance: "Acknowledge the speaker's accomplishments, set anticipation for the topic, and invite a warm round of applause.",
    targetWordCount: [40, 120]
  },
  {
    id: 'pre_04',
    mode: 'presentation',
    title: 'Explain Cybersecurity to Non-Technical Users',
    prompt: 'Explain why two-factor authentication (2FA) and strong passwords matter to someone who is unfamiliar with computer security.',
    guidance: 'Use clear analogies (e.g., double lock on a front door), emphasize personal safety, and offer a simple recommendation.',
    targetWordCount: [50, 140]
  },

  // Professional
  {
    id: 'pro_01',
    mode: 'professional',
    title: 'Asking for Permission / Approval',
    prompt: 'Request permission from your manager or professor to attend a 2-day professional development workshop during work hours.',
    guidance: 'Explain how attending benefits your team or coursework, propose a plan to cover your responsibilities, and be polite.',
    targetWordCount: [45, 130]
  },
  {
    id: 'pro_02',
    mode: 'professional',
    title: 'Writing a Professional Request',
    prompt: 'Ask a cross-functional partner for access to project documentation that is blocking your work.',
    guidance: "Be polite, specify the exact documents needed, explain why it's needed now, and provide a clear timeline.",
    targetWordCount: [35, 110]
  },
  {
    id: 'pro_03',
    mode: 'professional',
    title: 'Handling Disagreement Respectfully',
    prompt: 'A colleague proposed an architecture that you believe will not scale under high traffic. Express your disagreement constructively.',
    guidance: 'Validate their effort, present data or technical reasoning without personal attacks, and propose an alternative to evaluate together.',
    targetWordCount: [50, 140]
  },
  {
    id: 'pro_04',
    mode: 'professional',
    title: 'Asking for Clarification on Vague Feedback',
    prompt: "You received feedback saying 'This report needs to be better'. Write a polite response asking for specific actionable guidance.",
    guidance: 'Thank them for the feedback, avoid defensiveness, and request specific examples or sections they would like revised.',
    targetWordCount: [35, 110]
  },
  {
    id: 'pro_05',
    mode: 'professional',
    title: 'Delivering Constructive Feedback to a Peer',
    prompt: "A peer's code submission frequently lacks unit tests, creating delays in review. Provide helpful feedback encouraging better test coverage.",
    guidance: 'Focus on the shared goal of team speed and code quality, mention specific test patterns that help, and offer to collaborate.',
    targetWordCount: [45, 130]
  }
];

export const DAILY_CHALLENGES = [
  {
    id: 'dc_01',
    title: 'The 30-Second Project Summary',
    prompt: 'Explain what your primary project does and who it helps in 30 to 50 words without using any filler words.',
    focus: 'Clarity & Filler Control',
    tip: 'State the problem in sentence one, and your solution in sentence two.',
    targetWordCount: [30, 60]
  },
  {
    id: 'dc_02',
    title: 'Zero-Filler Self Introduction',
    prompt: "Introduce yourself to a potential employer or client without using 'like', 'um', 'actually', or 'basically'.",
    focus: 'Confidence & Filler Control',
    tip: "Pause silently between thoughts instead of saying 'um' or 'like'.",
    targetWordCount: [35, 75]
  },
  {
    id: 'dc_03',
    title: 'Teach a Concept to a Beginner',
    prompt: 'Explain what an algorithm is in plain English to someone who has never coded before.',
    focus: 'Clarity & Vocabulary',
    tip: 'Compare an algorithm to a step-by-step recipe for baking a cake.',
    targetWordCount: [40, 90]
  },
  {
    id: 'dc_04',
    title: 'Respectful Disagreement',
    prompt: 'Disagree with a decision to cancel remote work Fridays, while staying 100% professional and collaborative.',
    focus: 'Professionalism & Respectfulness',
    tip: 'Highlight productivity data and suggest a trial period rather than expressing frustration.',
    targetWordCount: [45, 110]
  },
  {
    id: 'dc_05',
    title: 'Crisp Executive Summary',
    prompt: 'Summarize a successful feature launch in three sentences: Problem, Solution, and Measurable Outcome.',
    focus: 'Structure & Professionalism',
    tip: "Use action verbs like 'delivered', 'reduced', or 'optimized'.",
    targetWordCount: [35, 80]
  }
];

export function getTodayChallenge() {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 1000 / 60 / 60 / 24);
  const idx = dayOfYear % DAILY_CHALLENGES.length;
  return { ...DAILY_CHALLENGES[idx], mode: 'challenge' };
}

export function getScenariosByMode(mode) {
  if (!mode || mode === 'all') return SCENARIOS;
  return SCENARIOS.filter(s => s.mode === mode);
}

export function getScenarioById(id) {
  const found = SCENARIOS.find(s => s.id === id);
  if (found) return found;
  const challenge = DAILY_CHALLENGES.find(c => c.id === id);
  if (challenge) return { ...challenge, mode: 'challenge' };
  return null;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    PRACTICE_MODES,
    SCENARIOS,
    DAILY_CHALLENGES,
    getTodayChallenge,
    getScenariosByMode,
    getScenarioById
  };
}

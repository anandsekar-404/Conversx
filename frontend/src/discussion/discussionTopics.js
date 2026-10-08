/**
 * ConversX Live Group Discussion Topics.
 * Curated topics for 3 to 8 participants.
 */

export const DISCUSSION_TOPICS = [
  {
    id: 'disc_01',
    title: 'Should artificial intelligence replace certain human analytical jobs?',
    category: 'Technology & Ethics',
    difficulty: 'Intermediate',
    expectedDurationSeconds: 900, // 15 mins
    minParticipants: 3,
    maxParticipants: 8,
    guidance: 'Explore productivity vs. workforce displacement. Focus on balanced reasoning and synthesizing peer counterpoints.',
    coachingCues: [
      "Acknowledge the previous speaker's premise before stating your counter-view.",
      "Cite practical domain examples rather than purely theoretical outcomes.",
      "Invite input from participants who haven't spoken recently."
    ]
  },
  {
    id: 'disc_02',
    title: 'Remote Work vs. In-Office: Which model drives sustainable team culture?',
    category: 'Workplace & Culture',
    difficulty: 'Beginner',
    expectedDurationSeconds: 900,
    minParticipants: 3,
    maxParticipants: 8,
    guidance: 'Discuss autonomy, async collaboration, informal mentorship, and cross-functional silos.',
    coachingCues: [
      "Ask clarifying questions to uncover underlying assumptions.",
      "Summarize the group's consensus before pivoting to a new angle.",
      "Use measured, collaborative phrasing to introduce trade-offs."
    ]
  },
  {
    id: 'disc_03',
    title: 'Rapid Product Velocity vs. Deep Engineering Quality in High-Growth Tech',
    category: 'Engineering Leadership',
    difficulty: 'Advanced',
    expectedDurationSeconds: 900,
    minParticipants: 3,
    maxParticipants: 8,
    guidance: 'Debate tech debt vs. time-to-market. Practice executive persuasion and risk posture framing.',
    coachingCues: [
      "State your core recommendation within the first 15 seconds.",
      "Frame trade-offs quantitatively when possible.",
      "Respectfully challenge technical assumptions using evidence."
    ]
  },
  {
    id: 'disc_04',
    title: 'Corporate Climate Action: Voluntary Pledges vs. Mandatory Regulatory Caps',
    category: 'Policy & Economics',
    difficulty: 'Advanced',
    expectedDurationSeconds: 900,
    minParticipants: 3,
    maxParticipants: 8,
    guidance: 'Examine compliance incentives, global competitive fairness, and market mechanisms.',
    coachingCues: [
      "Bridge opposing economic perspectives with constructive synthesis.",
      "Avoid dismissive filler phrases when peers express opposing views.",
      "Keep speaking turns concise (under 45 seconds) to maintain dialogue rhythm."
    ]
  },
  {
    id: 'disc_05',
    title: 'Balancing User Privacy with Data-Driven Personalization in Consumer Products',
    category: 'Product & Privacy',
    difficulty: 'Intermediate',
    expectedDurationSeconds: 900,
    minParticipants: 3,
    maxParticipants: 8,
    guidance: 'Analyze explicit user consent vs. frictionless recommendation algorithms.',
    coachingCues: [
      "Affirm valid security concerns before proposing product solutions.",
      "Check for mutual alignment before progressing to action items.",
      "Use precise lexicon rather than vague technical generalities."
    ]
  }
];

export function getAllTopics() {
  return [...DISCUSSION_TOPICS];
}

export function getTopicById(topicId) {
  return DISCUSSION_TOPICS.find(t => t.id === topicId) || DISCUSSION_TOPICS[0];
}

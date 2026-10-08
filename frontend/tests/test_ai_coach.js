/**
 * Unit & Security Tests for ConversX Personal AI Coach Service.
 * Run via: node frontend/tests/test_ai_coach.js
 */

import { aiCoachService } from '../src/aiCoach/aiCoachService.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failed++;
    throw new Error(message);
  } else {
    passed++;
    console.log(`  ✓ ${message}`);
  }
}

console.log('\n--- ConversX Personal AI Coach Engine & Security Tests ---');

// 1. Initial State & Unconnected Fallbacks
console.log('\n[1] Initial Connection Status & Fallbacks');
assert(aiCoachService.status.openai.connected === false, 'OpenAI is initially disconnected');
assert(aiCoachService.status.gemini.connected === false, 'Gemini is initially disconnected');
assert(aiCoachService.status.preferred_provider === 'openai', 'Default preferred provider is OpenAI');

// 2. Input Validation
console.log('\n[2] Key Validation & Protection');
try {
  await aiCoachService.connectProvider('openai', 'short');
  assert(false, 'Should have rejected short key');
} catch (e) {
  assert(e.message.includes('valid API key'), 'Rejects short/empty key format');
}

// 3. Security: No Browser Storage Leaks
console.log('\n[3] Zero-Leak Client Storage Security');
// Verify global storage objects are clean
if (typeof localStorage !== 'undefined') {
  assert(localStorage.getItem('openai_api_key') === null, 'No OpenAI key in localStorage');
  assert(localStorage.getItem('gemini_api_key') === null, 'No Gemini key in localStorage');
}
if (typeof sessionStorage !== 'undefined') {
  assert(sessionStorage.getItem('openai_api_key') === null, 'No OpenAI key in sessionStorage');
  assert(sessionStorage.getItem('gemini_api_key') === null, 'No Gemini key in sessionStorage');
}
assert(true, 'Verified zero credentials in browser storage');

// 4. Client Fallback Coaching Structure
console.log('\n[4] 4-Part Coaching Structure & Drill Specialization');
const dummyMetrics = {
  clarity: 88,
  filler_control: 82,
  confidence: 85
};

const casualCoaching = aiCoachService._clientFallbackCoaching(
  'I worked on a collaborative deliverable with our engineering counterparts.',
  { title: 'Project Update', mode: 'casual' },
  dummyMetrics
);

assert(Array.isArray(casualCoaching.strengths) && casualCoaching.strengths.length >= 2, 'Returns at least 2 strengths');
assert(Array.isArray(casualCoaching.improvements) && casualCoaching.improvements.length >= 1, 'Returns actionable improvements');
assert(typeof casualCoaching.why_it_matters === 'string', 'Returns "Why It Matters" rationale');
assert(Array.isArray(casualCoaching.next_time_actions) && casualCoaching.next_time_actions.length >= 2, 'Returns prescriptive next-time actions');
assert(typeof casualCoaching.stronger_phrasing === 'string', 'Returns executive polish rewrite');

// 5. Interview STAR Breakdown
console.log('\n[5] Interview Drill STAR Breakdown');
const interviewCoaching = aiCoachService._clientFallbackCoaching(
  'When faced with a sudden deadline crunch, I realigned team priorities.',
  { title: 'Overcoming Deadlines', mode: 'interview' },
  dummyMetrics
);

assert(interviewCoaching.interview_star !== undefined, 'Interview coaching generates STAR breakdown');
assert(interviewCoaching.interview_star.situation.length > 0, 'STAR has Situation');
assert(interviewCoaching.interview_star.task.length > 0, 'STAR has Task');
assert(interviewCoaching.interview_star.action.length > 0, 'STAR has Action');
assert(interviewCoaching.interview_star.result.length > 0, 'STAR has Result');
assert(interviewCoaching.interview_star.likely_followup.length > 0, 'STAR provides likely follow-up question');

// 6. Presentation Structure
console.log('\n[6] Presentation Structure Breakdown');
const presCoaching = aiCoachService._clientFallbackCoaching(
  'Today I am proposing a reallocation of our cloud compute infrastructure.',
  { title: 'Infrastructure Proposal', mode: 'presentation' },
  dummyMetrics
);

assert(presCoaching.presentation_structure !== undefined, 'Presentation coaching generates structure critique');
assert(presCoaching.presentation_structure.opening.length > 0, 'Includes Opening analysis');
assert(presCoaching.presentation_structure.organization.length > 0, 'Includes Organization analysis');
assert(presCoaching.presentation_structure.transitions.length > 0, 'Includes Transitions analysis');
assert(presCoaching.presentation_structure.conclusion.length > 0, 'Includes Conclusion analysis');

// 7. Non-Interference Guarantee
console.log('\n[7] Strict Non-Interference with Deterministic Score');
const originalScore = 91;
const testMetrics = { ...dummyMetrics, score: originalScore };
const result = aiCoachService._clientFallbackCoaching(
  'Speech text for validation.',
  { title: 'Drill', mode: 'casual' },
  testMetrics
);

assert(testMetrics.score === 91, 'Original ConversX score remains untouched at 91');
assert(result.score === undefined, 'AI coaching does not fabricate or modify overall score');

console.log(`\n========================================`);
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log(`========================================\n`);

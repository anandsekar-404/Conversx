/**
 * Unit Tests for ConversX Communication Practice Engine.
 * Run via: node frontend/tests/test_practice.js
 */

import {
  analyzePracticeResponse,
  DEFAULT_FILLER_WORDS
} from '../src/practice/responseAnalyzer.js';
import {
  getTodayChallenge,
  getScenariosByMode,
  getScenarioById
} from '../src/practice/scenarios.js';
import { sessionManager } from '../src/practice/sessionManager.js';
import { progressTracker } from '../src/practice/progressTracker.js';

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

console.log('\n--- ConversX Practice & Coaching Engine Tests ---');

// 1. Scenarios & Daily Challenge
console.log('\n[1] Practice Modes & Scenarios');
const casualScenarios = getScenariosByMode('casual');
assert(casualScenarios.length >= 6, `Casual mode has ${casualScenarios.length} scenarios (expected >= 6)`);
const interviewScenarios = getScenariosByMode('interview');
assert(interviewScenarios.length >= 6, `Interview mode has ${interviewScenarios.length} scenarios (expected >= 6)`);
const todayChallenge = getTodayChallenge();
assert(todayChallenge && todayChallenge.title, `Today's challenge returned: "${todayChallenge.title}"`);
const single = getScenarioById('int_01');
assert(single && single.title === 'Tell Me About Yourself', 'Lookup scenario by ID works');

// 2. Clear Professional Response
console.log('\n[2] High-Quality Structured Response');
const clearText = 'Good morning. I am writing to propose a revised timeline for our project launch. Because our core deliverables need thorough verification, I recommend we schedule the deployment for next Tuesday. In summary, this guarantees stability for our clients.';
const clearRes = analyzePracticeResponse(clearText, 'pro_03');
assert(clearRes.overallScore >= 85, `High quality score: ${clearRes.overallScore} >= 85`);
assert(clearRes.dimensionScores.clarity >= 80, `Clarity >= 80: got ${clearRes.dimensionScores.clarity}`);
assert(clearRes.dimensionScores.grammar >= 90, `Grammar >= 90: got ${clearRes.dimensionScores.grammar}`);
assert(clearRes.dimensionScores.filler_control === 100, `Filler control 100: got ${clearRes.dimensionScores.filler_control}`);
assert(clearRes.dimensionScores.structure >= 80, `Structure >= 80: got ${clearRes.dimensionScores.structure}`);
assert(clearRes.positiveFeedback.length >= 2, 'Positive feedback highlights strengths');

// 3. Filler Word Detection
console.log('\n[3] Filler Word Detection');
const fillerText = 'I actually think this project is basically very useful and like it can help students.';
const fillerRes = analyzePracticeResponse(fillerText);
assert(fillerRes.detectedFillers.length >= 2, `Detected multiple filler words (${fillerRes.detectedFillers.length})`);
assert(fillerRes.dimensionScores.filler_control < 80, `Filler control penalized: ${fillerRes.dimensionScores.filler_control}`);
assert(fillerRes.improvementFeedback.some(f => f.includes('filler word')), 'Coaching feedback explicitly mentions filler words');

// 4. Grammar Cues Detection
console.log('\n[4] Grammar Issues Detection');
const grammarText = 'She has a apple and they is going to the the store.';
const grammarRes = analyzePracticeResponse(grammarText);
assert(grammarRes.detectedGrammarIssues.length >= 2, `Grammar issues detected: ${grammarRes.detectedGrammarIssues.length}`);
assert(grammarRes.dimensionScores.grammar < 80, `Grammar score penalized: ${grammarRes.dimensionScores.grammar}`);

// 5. Wordiness & Clarity
console.log('\n[5] Wordiness & Sentence Complexity');
const wordyText = 'Due to the fact that we are working in close proximity to the team, in order to finish each and every task on time we must hurry.';
const wordyRes = analyzePracticeResponse(wordyText);
assert(wordyRes.detectedWordiness.length >= 2, `Wordy phrases caught: ${wordyRes.detectedWordiness.length}`);
assert(wordyRes.dimensionScores.clarity < 90, `Clarity penalized: ${wordyRes.dimensionScores.clarity}`);

// 6. Confidence & Hedging
console.log('\n[6] Confidence & Hedging');
const hedgeText = "I think maybe I'm not sure but I guess we could try this solution.";
const hedgeRes = analyzePracticeResponse(hedgeText);
assert(hedgeRes.detectedHedges.length >= 2, `Hedges detected: ${hedgeRes.detectedHedges.length}`);
assert(hedgeRes.dimensionScores.confidence <= 65, `Confidence penalized: ${hedgeRes.dimensionScores.confidence}`);

// 7. Say It Better Deterministic Transformation
console.log('\n[7] Say It Better Transformation');
const sib = fillerRes.sayItBetter;
assert(sib.suggestedText !== fillerText, 'Suggested text is modified');
assert(sib.improvementsMade.length >= 1, `Improvements noted: ${sib.improvementsMade.join('; ')}`);
assert(!sib.suggestedText.includes('actually'), 'Filler "actually" removed in suggestion');
assert(!sib.suggestedText.includes('basically'), 'Filler "basically" removed in suggestion');

// 8. Retry & Session Manager Loop
console.log('\n[8] Retry & Attempt Progression');
sessionManager.startSession('int_01', 'interview');
const att1 = sessionManager.recordAttempt(fillerRes);
assert(att1.attemptNumber === 1, 'First attempt is #1');
assert(sessionManager.getAttemptCount() === 1, 'Attempt count is 1');

// Second attempt with improved response
const att2 = sessionManager.recordAttempt(clearRes);
assert(att2.attemptNumber === 2, 'Second attempt is #2');
assert(sessionManager.getAttemptCount() === 2, 'Attempt count is 2');
const delta = sessionManager.getScoreDelta();
assert(delta > 0, `Score progression delta is positive: +${delta} points`);

// 9. Progress Tracking
console.log('\n[9] Progress Tracking & History');
const record = progressTracker.saveSession({
  scenarioId: 'int_01',
  practiceType: 'interview',
  attemptNumber: 2,
  score: att2.score,
  dimensionScores: att2.dimensionScores
});
assert(record.score === att2.score, 'Session saved with score');
const overview = progressTracker.getOverview();
assert(overview.overallScore === att2.score, 'Overview reflects latest score');
assert(overview.currentStreakDays >= 1, 'Active streak calculated');

// 10. Strict Determinism
console.log('\n[10] Strict Determinism');
const run1 = analyzePracticeResponse('Tell me about your background in technology.', 'int_01');
const run2 = analyzePracticeResponse('Tell me about your background in technology.', 'int_01');
assert(JSON.stringify(run1) === JSON.stringify(run2), 'Identical input produces 100% identical practice analysis JSON');

console.log(`\n========================================`);
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log(`========================================\n`);

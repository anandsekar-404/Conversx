/**
 * Frontend JavaScript Moderation Engine Unit Tests.
 * Conforms to Master Prompt Section 16 & Section 18.
 * Run via: node frontend/tests/test_moderation.js
 */

import { normalizeText } from '../src/moderation/normalizeText.js';
import { matchWords } from '../src/moderation/matchWords.js';
import { matchPhrases } from '../src/moderation/matchPhrases.js';
import { calculateSeverity } from '../src/moderation/calculateSeverity.js';
import { DEFAULT_SEED_RULES, getSuggestionForCategory } from '../src/moderation/loadRules.js';
import { analyzeCommunication } from '../src/moderation/analyzeCommunication.js';

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

console.log('\n--- ConversX JavaScript Moderation Engine Tests ---');

// 1. Normalization
console.log('\n[1] Normalization');
const norm1 = normalizeText('You are!!!   USELESS!!!');
assert(norm1.normalizedText === 'you are useless', `Normalization handles caps & punctuation: "${norm1.normalizedText}"`);
const norm2 = normalizeText('Stúpíd idéà');
assert(norm2.normalizedText.includes('stupid') && norm2.normalizedText.includes('idea'), `Accents stripped: "${norm2.normalizedText}"`);

// 2. Safe Messages
console.log('\n[2] Safe Messages');
const safeTexts = [
  'Can you explain this again?',
  'I disagree with your idea.',
  'Could we try another approach?',
  'Here is the project timeline for Q3 deliverables.'
];
for (const text of safeTexts) {
  const res = analyzeCommunication(text, DEFAULT_SEED_RULES);
  assert(res.status === 'safe', `"${text}" -> status safe`);
  assert(res.score === 100, `"${text}" -> score 100`);
  assert(res.matchedCount === 0, `"${text}" -> 0 matches`);
}

// 3. False Positive Prevention
console.log('\n[3] False Positive Prevention (Token Boundaries)');
const falsePositives = [
  'We studied classic literature in our seminar.',
  'She was passionate about her classroom assignment.',
  'The therapist assisted our department yesterday.',
  'Please review the attached project document.'
];
for (const text of falsePositives) {
  const res = analyzeCommunication(text, DEFAULT_SEED_RULES);
  assert(res.status === 'safe', `False-positive safe: "${text}"`);
  assert(res.matchedCount === 0, `No substrings wrongly flagged in "${text}"`);
}

// 4. Bad-Word Detection
console.log('\n[4] Bad-Word Detection');
const bwRes = analyzeCommunication('You are useless.', DEFAULT_SEED_RULES);
assert(bwRes.matchedCount >= 1, 'Catches "useless"');
assert(bwRes.matchedRules.some(r => r.match === 'useless'), 'Identifies match word');
assert(bwRes.severity >= 2, 'Severity is warning or higher');

// 5. Harassment Phrase Matching
console.log('\n[5] Harassment Phrase Detection');
const hpRes = analyzeCommunication('You are useless. Your idea is stupid.', DEFAULT_SEED_RULES);
assert(hpRes.matchedCount >= 2, 'Catches multiple rules in message');
assert(hpRes.status === 'warning' || hpRes.status === 'harmful', 'Harmful status assigned');
assert(hpRes.categories.includes('insult') || hpRes.categories.includes('personal_attack'), 'Categories identified');

// 6. Threat Severity
console.log('\n[6] Severe Threat Detection');
const threatRes = analyzeCommunication('I will hurt you if you disagree.', DEFAULT_SEED_RULES);
assert(threatRes.severity >= 3, `Severity >= 3: got ${threatRes.severity}`);
assert(threatRes.categories.includes('threat'), 'Threat category mapped');
assert(threatRes.dimensions.aggressiveness > 60, 'Aggressiveness index elevated');

// 7. Say It Better Constructive Suggestions
console.log('\n[7] Say It Better Suggestions');
assert(hpRes.suggestion !== null, 'Suggestion returned for harmful message');
assert(typeof hpRes.suggestion.suggestion === 'string', 'Constructive guidance present');
assert(typeof hpRes.suggestion.example === 'string' && hpRes.suggestion.example.length > 5, 'Concrete example provided');

// 8. Determinism
console.log('\n[8] Strict Determinism');
const runA = analyzeCommunication('You are useless and incompetent.', DEFAULT_SEED_RULES);
const runB = analyzeCommunication('You are useless and incompetent.', DEFAULT_SEED_RULES);
assert(JSON.stringify(runA) === JSON.stringify(runB), 'Repeated execution produces 100% identical JSON result');

console.log(`\n========================================`);
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log(`========================================\n`);

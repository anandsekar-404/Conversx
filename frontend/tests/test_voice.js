/**
 * ConversX - Phase 5 Voice Communication Coach Automated Tests.
 * Run with Node.js: node frontend/tests/test_voice.js
 */

import {
  countWords,
  calculateWpm,
  classifyPace,
  calculateFillerMetrics,
  analyzePauses,
  calculateSpeakingMetrics,
  PACE_OPTIMAL_MIN,
  PACE_OPTIMAL_MAX
} from '../src/voice/speakingMetrics.js';

import {
  calculatePaceScore,
  calculateFillerControlScore,
  calculateFlowScore,
  calculateDeliveryScore,
  analyzeVoiceResponse,
  DELIVERY_DISCLAIMER
} from '../src/voice/voiceAnalyzer.js';

import { VoiceRecordingSession } from '../src/voice/recordingSession.js';
import { progressTracker } from '../src/practice/progressTracker.js';

let passedCount = 0;
let failedCount = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passedCount++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failedCount++;
  }
}

async function runVoiceTests() {
  console.log('\n--- ConversX Phase 5 Voice Communication Coach Tests ---\n');

  // [1] Speaking Metrics
  console.log('[1] Speaking Metrics: Words & WPM');
  const text60 = "This is a clean test sentence used for verifying words per minute accurately. " +
                 "This is a clean test sentence used for verifying words per minute accurately. " +
                 "This is a clean test sentence used for verifying words per minute accurately. " +
                 "This is a clean test sentence used for verifying words per minute accurately. " +
                 "This is a clean test sentence used for verifying words per minute accurately.";
  const words = countWords(text60);
  assert(words === 65, `countWords returns 65 (got ${words})`);

  const wpm120 = calculateWpm(60, 30);
  assert(wpm120 === 120, `calculateWpm(60 words, 30s) = 120 WPM (got ${wpm120})`);

  const wpmZero = calculateWpm(0, 30);
  assert(wpmZero === 0, `calculateWpm(0 words) = 0`);

  // [2] Pace Classification
  console.log('\n[2] Pace Classification');
  assert(classifyPace(80).category === 'very_slow', '80 WPM is very_slow');
  assert(classifyPace(110).category === 'slow', '110 WPM is slow');
  assert(classifyPace(135).category === 'optimal', '135 WPM is optimal (120–160 WPM)');
  assert(classifyPace(170).category === 'fast', '170 WPM is fast');
  assert(classifyPace(200).category === 'very_fast', '200 WPM is very_fast');
  assert(classifyPace(0).category === 'none', '0 WPM is none');

  // [3] Filler Word Tracking
  console.log('\n[3] Filler Word Tracking & Rates');
  const speechWithFillers = "Hello um my name is Alex and actually I basically think we should launch today.";
  const fillerRes = calculateFillerMetrics(speechWithFillers);
  assert(fillerRes.fillerCount === 3, `Detected 3 filler words (got ${fillerRes.fillerCount})`);
  assert(fillerRes.fillerRate > 15, `Filler rate calculated > 15% (got ${fillerRes.fillerRate}%)`);
  assert(fillerRes.detectedFillers.some(f => f.filler === 'um'), 'Identified filler "um"');
  assert(fillerRes.detectedFillers.some(f => f.filler === 'basically'), 'Identified filler "basically"');

  // [4] Pause Timing Analysis
  console.log('\n[4] Pause Timing Analysis');
  const emptyEvents = [];
  const noPauseRes = analyzePauses(emptyEvents);
  assert(noPauseRes.available === false, 'analyzePauses returns available: false when no timestamps');

  const chunkEvents = [
    { startTime: 1000, endTime: 3000, text: 'Hello team' },
    { startTime: 4200, endTime: 6000, text: 'Today we discuss the release' }, // 1.2s pause
    { startTime: 8500, endTime: 11000, text: 'Let us begin' }                  // 2.5s long pause
  ];
  const pauseRes = analyzePauses(chunkEvents);
  assert(pauseRes.available === true, 'Pause analysis available with real timestamps');
  assert(pauseRes.pauseCount === 2, `Detected 2 pauses (got ${pauseRes.pauseCount})`);
  assert(pauseRes.longPauseCount === 1, `Detected 1 long pause (got ${pauseRes.longPauseCount})`);
  assert(pauseRes.averagePauseDuration > 1.0, `Average pause duration calculated (> 1.0s)`);

  // [5] Speaking Delivery Scoring Formula
  console.log('\n[5] Speaking Delivery Scoring (0–100)');
  // Optimal sample: 70 words, 30s = 140 WPM, 0 fillers
  const optimalMetrics = calculateSpeakingMetrics(
    "Good morning everyone. Today we are presenting our new data architecture which simplifies event processing. " +
    "Our team has tested every single component and we saw a thirty percent reduction in server memory footprint.",
    15
  );
  const optimalDelivery = calculateDeliveryScore(optimalMetrics);
  assert(optimalDelivery.deliveryScore >= 85, `Optimal delivery score >= 85 (got ${optimalDelivery.deliveryScore})`);
  assert(optimalDelivery.deliveryDimensions.pace >= 90, `Pace dimension high (got ${optimalDelivery.deliveryDimensions.pace})`);
  assert(optimalDelivery.deliveryFeedback.strengths.length > 0, 'Strengths provided in feedback');

  // Rushed & high filler sample
  const rushedMetrics = calculateSpeakingMetrics(
    "Um like basically actually I think sort of like you know we really need to hurry up and um like fix everything because uh you know.",
    10
  );
  const rushedDelivery = calculateDeliveryScore(rushedMetrics);
  assert(rushedDelivery.deliveryScore <= 75, `Rushed delivery score penalized (got ${rushedDelivery.deliveryScore})`);
  assert(rushedDelivery.deliveryDimensions.fillerControl <= 50, `Filler control penalized (got ${rushedDelivery.deliveryDimensions.fillerControl})`);
  assert(rushedDelivery.deliveryFeedback.improvements.length > 0, 'Actionable improvements provided');

  // Empty transcript sample
  const emptyDelivery = calculateDeliveryScore({ wpm: 0, wordCount: 0, durationSeconds: 5, fillerRate: 0 });
  assert(emptyDelivery.deliveryScore === 0, 'Empty speech receives 0 delivery score');

  // [6] Full Voice Response Analysis (Communication + Delivery + Moderation)
  console.log('\n[6] Full Voice Response Integration');
  const fullTranscript = "Good morning. I am excited to introduce our new open platform that empowers students to learn communication skills.";
  const fullAnalysis = await analyzeVoiceResponse(fullTranscript, 12, 'int_01');
  assert(fullAnalysis.communicationScore > 80, `Communication score evaluated (got ${fullAnalysis.communicationScore})`);
  assert(fullAnalysis.deliveryScore > 80, `Delivery score evaluated (got ${fullAnalysis.deliveryScore})`);
  assert(fullAnalysis.moderationStatus === 'safe', 'Moderation status safe');
  assert(fullAnalysis.disclaimer.includes('ConversX does not claim'), 'Disclaimer present');
  assert(typeof fullAnalysis.sayItBetter === 'object', 'Say It Better returned');

  // [7] Voice Session & Side-by-Side Retry Comparison
  console.log('\n[7] Voice Session & Side-by-Side Comparison');
  const session = new VoiceRecordingSession({ scenarioId: 'int_01', mode: 'interview' });

  // Simulate Attempt 1 (nervous attempt with fillers & fast pace)
  const attempt1 = await session.analyzeCurrentResponse("Um basically I think like our team did good stuff you know right.");
  assert(attempt1.attemptNumber === 1, 'First attempt is #1');
  assert(session.attemptsHistory.length === 1, 'History has 1 attempt');

  // Prepare retry
  session.prepareRetry();
  assert(session.currentAttemptNumber === 2, 'Next attempt is #2');

  // Simulate Attempt 2 (improved, confident response)
  const attempt2 = await session.analyzeCurrentResponse("Our team engineered a distributed pipeline that delivered thirty percent lower latency.");
  assert(attempt2.attemptNumber === 2, 'Second attempt is #2');
  assert(attempt2.comparison !== null, 'Side-by-side comparison generated');

  const comp = attempt2.comparison;
  assert(comp.previousAttemptNumber === 1, 'Previous attempt was 1');
  assert(comp.currentAttemptNumber === 2, 'Current attempt was 2');

  const commMetric = comp.metrics.find(m => m.name === 'Communication Score');
  assert(commMetric && commMetric.delta > 0, `Communication score delta positive (+${commMetric.delta})`);

  const fillerMetric = comp.metrics.find(m => m.name === 'Filler Words');
  assert(fillerMetric && fillerMetric.improved, 'Filler words improved in attempt 2');

  // [8] Progress Hub Voice Metrics
  console.log('\n[8] Progress Hub Voice Tracking');
  const overview = progressTracker.getOverview();
  assert(overview.voiceProgress.voiceSessionsCount >= 2, `Voice sessions tracked (got ${overview.voiceProgress.voiceSessionsCount})`);
  assert(overview.voiceProgress.averageDeliveryScore > 0, `Average delivery score tracked (${overview.voiceProgress.averageDeliveryScore})`);
  assert(overview.voiceProgress.bestDeliveryScore >= overview.voiceProgress.averageDeliveryScore, 'Best delivery >= average');

  // [9] Strict Determinism
  console.log('\n[9] Strict Determinism Verification');
  const sample = "Clear communication builds alignment across engineering and product teams.";
  const resA = await analyzeVoiceResponse(sample, 10);
  const resB = await analyzeVoiceResponse(sample, 10);
  assert(JSON.stringify(resA) === JSON.stringify(resB), '100% identical JSON outputs for identical inputs');

  // Summary
  console.log('\n========================================');
  console.log(`Summary: ${passedCount} passed, ${failedCount} failed.`);
  console.log('========================================\n');

  if (failedCount > 0) {
    process.exit(1);
  }
}

runVoiceTests().catch(err => {
  console.error('Test execution error:', err);
  process.exit(1);
});

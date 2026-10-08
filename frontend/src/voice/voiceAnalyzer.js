/**
 * ConversX - Speaking Delivery Analyzer & Coaching Engine.
 * Calculates deterministic Speaking Delivery Score (0-100) across:
 * - Pace (35%)
 * - Filler Control (35%)
 * - Flow & Pause Control (30%)
 * 
 * Pairs speaking delivery with the existing 8-dimension Communication Score.
 * 
 * DISCLAIMER: ConversX evaluates delivery deterministically based on measurable
 * tempo, filler frequency, and pause distribution. ConversX does not claim to detect
 * emotions, psychological state, or vocal tone.
 */

import { calculateSpeakingMetrics } from './speakingMetrics.js';
import { analyzePracticeResponse } from '../practice/responseAnalyzer.js';

export const DELIVERY_WEIGHTS = {
  pace: 0.35,
  fillerControl: 0.35,
  flowControl: 0.30
};

export const DELIVERY_DISCLAIMER = "ConversX evaluates delivery using deterministic pace, filler frequency, and speech continuity. ConversX does not claim to detect emotions, vocal tone, or psychological confidence.";

/**
 * Calculates deterministic Pace Score (0-100).
 */
export function calculatePaceScore(wpm, wordCount) {
  if (wordCount === 0 || wpm <= 0) return 0;
  if (wpm >= 125 && wpm <= 155) return 100; // Optimal conversational sweet spot
  if ((wpm >= 115 && wpm < 125) || (wpm > 155 && wpm <= 165)) return 90;
  if ((wpm >= 100 && wpm < 115) || (wpm > 165 && wpm <= 180)) return 75;
  if ((wpm >= 80 && wpm < 100) || (wpm > 180 && wpm <= 200)) return 60;
  return 40; // Too slow (<80) or rushed (>200)
}

/**
 * Calculates deterministic Filler Control Score (0-100).
 */
export function calculateFillerControlScore(fillerRate, wordCount) {
  if (wordCount === 0) return 0;
  if (fillerRate === 0) return 100;
  if (fillerRate <= 1.5) return 92;
  if (fillerRate <= 3.0) return 82;
  if (fillerRate <= 5.0) return 70;
  if (fillerRate <= 8.0) return 50;
  return 35;
}

/**
 * Calculates deterministic Flow & Continuity Score (0-100).
 */
export function calculateFlowScore(pauseAnalysis, wordCount, durationSeconds) {
  if (wordCount === 0 || durationSeconds <= 0) return 0;

  let score = 85; // Baseline healthy conversational flow

  if (pauseAnalysis && pauseAnalysis.available) {
    // Reward natural breathing pauses (1-3 natural pauses per 30s)
    const pausesPer30s = (pauseAnalysis.pauseCount / Math.max(15, durationSeconds)) * 30;
    if (pausesPer30s >= 0.8 && pausesPer30s <= 3.5) {
      score += 15;
    } else if (pausesPer30s < 0.5 && durationSeconds > 30) {
      // Very few pauses in a long monologue - slight rush
      score -= 10;
    }

    // Penalize long awkward dead silences (>2.0s)
    if (pauseAnalysis.longPauseCount > 0) {
      score -= Math.min(30, pauseAnalysis.longPauseCount * 12);
    }
  } else {
    // Fallback: evaluate word-to-duration density
    const avgWordsPerSec = wordCount / durationSeconds;
    if (avgWordsPerSec >= 2.0 && avgWordsPerSec <= 2.8) {
      score = 90;
    } else if (avgWordsPerSec > 3.3 || avgWordsPerSec < 1.4) {
      score = 75;
    }
  }

  return Math.max(20, Math.min(100, Math.round(score)));
}

/**
 * Calculates overall Speaking Delivery Score (0-100) and delivery dimensions.
 */
export function calculateDeliveryScore(metrics) {
  const { wpm, wordCount, durationSeconds, fillerRate, pauseAnalysis } = metrics;

  if (wordCount === 0) {
    return {
      deliveryScore: 0,
      deliveryDimensions: {
        pace: 0,
        fillerControl: 0,
        flowControl: 0
      },
      deliveryFeedback: {
        strengths: [],
        improvements: ['No audible speech captured. Please try speaking into the microphone again.'],
        tip: 'Ensure your microphone is properly connected and permission is granted.'
      }
    };
  }

  const paceScore = calculatePaceScore(wpm, wordCount);
  const fillerScore = calculateFillerControlScore(fillerRate, wordCount);
  const flowScore = calculateFlowScore(pauseAnalysis, wordCount, durationSeconds);

  const rawDelivery = (
    paceScore * DELIVERY_WEIGHTS.pace +
    fillerScore * DELIVERY_WEIGHTS.fillerControl +
    flowScore * DELIVERY_WEIGHTS.flowControl
  );
  const deliveryScore = Math.max(0, Math.min(100, Math.round(rawDelivery)));

  // Build targeted delivery feedback
  const strengths = [];
  const improvements = [];

  if (paceScore >= 90) {
    strengths.push(`Excellent pacing (${wpm} WPM). You spoke within the optimal conversational range (120–160 WPM).`);
  } else if (wpm > 165) {
    improvements.push(`Your pace was brisk at ${wpm} WPM. Slowing down slightly allows the listener to absorb key concepts.`);
  } else if (wpm < 115) {
    improvements.push(`Your pace was deliberate at ${wpm} WPM. Aiming for 125–150 WPM will create more forward momentum.`);
  }

  if (fillerScore >= 90) {
    strengths.push(`Outstanding vocal composure: filler rate was only ${fillerRate}%.`);
  } else if (fillerRate > 4.0) {
    improvements.push(`Filler words represented ${fillerRate}% of your speech (${metrics.fillerCount} total). Practice replacing 'um' or 'like' with silent pauses.`);
  }

  if (flowScore >= 85) {
    strengths.push("Steady speech continuity with natural conversational rhythm.");
  } else if (pauseAnalysis?.longPauseCount > 1) {
    improvements.push(`${pauseAnalysis.longPauseCount} extended pauses detected. Keeping brief pauses under 1.5 seconds maintains listener engagement.`);
  }

  let deliveryTip = "When transitioning between points, take a silent 1-second pause rather than using a verbal filler.";
  if (wpm > 170) {
    deliveryTip = "Consciously breathe between thoughts to steady your cadence and emphasize critical points.";
  } else if (wpm < 110) {
    deliveryTip = "Connect ideas with clear transition phrases ('First', 'Additionally', 'In conclusion') to keep speech moving.";
  }

  return {
    deliveryScore,
    deliveryDimensions: {
      pace: paceScore,
      fillerControl: fillerScore,
      flowControl: flowScore
    },
    deliveryFeedback: {
      strengths,
      improvements,
      tip: deliveryTip
    }
  };
}

/**
 * Complete Voice Response Analysis.
 * Seamlessly integrates Speaking Delivery with the existing PracticeEngine Communication Score.
 */
export async function analyzeVoiceResponse(transcript, durationSeconds, scenarioId = null, speechEvents = []) {
  // 1. Calculate deterministic speaking metrics
  const speakingMetrics = calculateSpeakingMetrics(transcript, durationSeconds, speechEvents);

  // 2. Run existing deterministic PracticeEngine text analysis (all 8 dimensions + moderation)
  const communicationAnalysis = await analyzePracticeResponse(transcript, scenarioId);

  // 3. Calculate deterministic speaking delivery score
  const deliveryResult = calculateDeliveryScore(speakingMetrics);

  return {
    scenarioId,
    transcript: transcript.trim(),
    speakingMetrics,
    deliveryScore: deliveryResult.deliveryScore,
    deliveryDimensions: deliveryResult.deliveryDimensions,
    deliveryFeedback: deliveryResult.deliveryFeedback,
    // Existing Phase 4 Communication Score & dimensions
    communicationScore: communicationAnalysis.overallScore,
    communicationDimensionScores: communicationAnalysis.dimensionScores,
    positiveFeedback: communicationAnalysis.positiveFeedback,
    improvementFeedback: communicationAnalysis.improvementFeedback,
    coachingTip: communicationAnalysis.coachingTip,
    sayItBetter: communicationAnalysis.sayItBetter,
    moderationStatus: communicationAnalysis.moderationStatus,
    disclaimer: DELIVERY_DISCLAIMER
  };
}

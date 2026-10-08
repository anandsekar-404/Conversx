/**
 * ConversX - Deterministic Speaking Metrics Engine.
 * Calculates duration, word count, words per minute (WPM),
 * filler count & rate, pace classification, and pause timing.
 * 
 * Strict deterministic logic - no fabricated measurements.
 */

import { DEFAULT_FILLER_WORDS } from '../practice/responseAnalyzer.js';

export const PACE_OPTIMAL_MIN = 120;
export const PACE_OPTIMAL_MAX = 160;

/**
 * Clean and count words in a transcript.
 */
export function countWords(text) {
  if (!text || typeof text !== 'string') return 0;
  const cleaned = text.trim();
  if (!cleaned) return 0;
  const words = cleaned.split(/\s+/).filter(w => w.length > 0);
  return words.length;
}

/**
 * Calculates Words Per Minute (WPM).
 */
export function calculateWpm(wordCount, durationSeconds) {
  if (!wordCount || wordCount <= 0 || !durationSeconds || durationSeconds <= 0) {
    return 0;
  }
  const minutes = durationSeconds / 60;
  const wpm = wordCount / minutes;
  return Math.round(wpm * 10) / 10;
}

/**
 * Classifies pace based on standard speech science ranges:
 * - Optimal / Conversational: 120-160 WPM
 * - Deliberate / Slow: < 120 WPM
 * - Fast / Rushed: > 160 WPM
 */
export function classifyPace(wpm) {
  if (wpm <= 0) return { category: 'none', label: 'No Speech Detected', description: 'No measurable speaking pace.' };
  if (wpm < 100) return { category: 'very_slow', label: 'Very Slow', description: 'Significantly below standard conversational tempo (<100 WPM).' };
  if (wpm < PACE_OPTIMAL_MIN) return { category: 'slow', label: 'Deliberate / Slow', description: 'Below typical conversational pace (100–119 WPM).' };
  if (wpm <= PACE_OPTIMAL_MAX) return { category: 'optimal', label: 'Optimal / Conversational', description: 'Clear, engaging conversational sweet spot (120–160 WPM).' };
  if (wpm <= 185) return { category: 'fast', label: 'Brisk / Fast', description: 'Somewhat rapid pace (161–185 WPM); ensure listeners can follow.' };
  return { category: 'very_fast', label: 'Rushed', description: 'Very rapid tempo (>185 WPM); key ideas may be missed.' };
}

/**
 * Detects filler words and calculates filler rate.
 */
export function calculateFillerMetrics(transcript, customFillerList = null) {
  const fillers = customFillerList || DEFAULT_FILLER_WORDS;
  if (!transcript || typeof transcript !== 'string') {
    return { fillerCount: 0, fillerRate: 0, detectedFillers: [] };
  }

  const normalized = transcript.toLowerCase();
  const detected = [];
  let totalCount = 0;

  for (const filler of fillers) {
    const escaped = filler.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`\\b${escaped}\\b`, 'gi');
    const matches = normalized.match(regex);
    if (matches && matches.length > 0) {
      detected.push({ filler, count: matches.length });
      totalCount += matches.length;
    }
  }

  const wordCount = countWords(transcript);
  const fillerRate = wordCount > 0 ? Math.round((totalCount / wordCount) * 1000) / 10 : 0;

  return {
    fillerCount: totalCount,
    fillerRate, // e.g. 3.2%
    detectedFillers: detected
  };
}

/**
 * Analyzes pause timings from timestamped speech chunks.
 * Only returns measurements if real timestamps are provided.
 */
export function analyzePauses(speechEvents = []) {
  if (!Array.isArray(speechEvents) || speechEvents.length < 2) {
    return {
      available: false,
      pauseCount: 0,
      longPauseCount: 0,
      averagePauseDuration: 0,
      totalPauseDuration: 0,
      note: 'Pause timing not available from browser recognition.'
    };
  }

  const pauses = [];
  let longPauseCount = 0;

  for (let i = 1; i < speechEvents.length; i++) {
    const prev = speechEvents[i - 1];
    const curr = speechEvents[i];
    if (prev && curr && typeof prev.endTime === 'number' && typeof curr.startTime === 'number') {
      const gapSeconds = (curr.startTime - prev.endTime) / 1000;
      if (gapSeconds >= 0.8) { // Pause threshold: >= 800ms
        pauses.push(gapSeconds);
        if (gapSeconds >= 2.0) { // Long pause: >= 2.0s
          longPauseCount++;
        }
      }
    }
  }

  if (pauses.length === 0) {
    return {
      available: true,
      pauseCount: 0,
      longPauseCount: 0,
      averagePauseDuration: 0,
      totalPauseDuration: 0,
      note: 'Speech was continuous with minimal silence gaps.'
    };
  }

  const total = pauses.reduce((acc, p) => acc + p, 0);
  const avg = Math.round((total / pauses.length) * 10) / 10;

  return {
    available: true,
    pauseCount: pauses.length,
    longPauseCount,
    averagePauseDuration: avg,
    totalPauseDuration: Math.round(total * 10) / 10,
    note: `${pauses.length} natural pause(s) detected.`
  };
}

/**
 * Primary speaking metrics calculation.
 */
export function calculateSpeakingMetrics(transcript, durationSeconds, speechEvents = [], customFillerList = null) {
  const wordCount = countWords(transcript);
  const cleanDuration = Math.max(0.1, Number(durationSeconds) || 0);
  const wpm = calculateWpm(wordCount, cleanDuration);
  const pace = classifyPace(wpm);
  const fillerMetrics = calculateFillerMetrics(transcript, customFillerList);
  const pauseMetrics = analyzePauses(speechEvents);

  return {
    wordCount,
    durationSeconds: Math.round(cleanDuration * 10) / 10,
    wpm,
    paceClassification: pace,
    fillerCount: fillerMetrics.fillerCount,
    fillerRate: fillerMetrics.fillerRate,
    detectedFillers: fillerMetrics.detectedFillers,
    pauseAnalysis: pauseMetrics
  };
}

/**
 * ConversX Practice & Coaching Engine Entrypoint.
 */

import { PRACTICE_MODES, SCENARIOS, DAILY_CHALLENGES, getTodayChallenge, getScenariosByMode, getScenarioById } from './scenarios.js';
import { analyzePracticeResponse, DEFAULT_FILLER_WORDS } from './responseAnalyzer.js';
import { sessionManager } from './sessionManager.js';
import { progressTracker } from './progressTracker.js';

export {
  PRACTICE_MODES,
  SCENARIOS,
  DAILY_CHALLENGES,
  DEFAULT_FILLER_WORDS,
  getTodayChallenge,
  getScenariosByMode,
  getScenarioById,
  analyzePracticeResponse,
  sessionManager,
  progressTracker
};

if (typeof window !== 'undefined') {
  window.PracticeEngine = {
    PRACTICE_MODES,
    SCENARIOS,
    DAILY_CHALLENGES,
    DEFAULT_FILLER_WORDS,
    getTodayChallenge,
    getScenariosByMode,
    getScenarioById,
    analyzePracticeResponse,
    sessionManager,
    progressTracker
  };
}

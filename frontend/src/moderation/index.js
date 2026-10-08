/**
 * ConversX Moderation Engine Entry Point.
 */

import { normalizeText } from './normalizeText.js';
import { matchWords } from './matchWords.js';
import { matchPhrases } from './matchPhrases.js';
import { calculateSeverity, SEVERITY_LEVELS } from './calculateSeverity.js';
import { loadRules, getCachedRules, getSuggestionForCategory, DEFAULT_SEED_RULES } from './loadRules.js';
import { analyzeCommunication } from './analyzeCommunication.js';

export {
  normalizeText,
  matchWords,
  matchPhrases,
  calculateSeverity,
  SEVERITY_LEVELS,
  loadRules,
  getCachedRules,
  getSuggestionForCategory,
  DEFAULT_SEED_RULES,
  analyzeCommunication
};

if (typeof window !== 'undefined') {
  window.ModerationEngine = {
    normalizeText,
    matchWords,
    matchPhrases,
    calculateSeverity,
    SEVERITY_LEVELS,
    loadRules,
    getCachedRules,
    getSuggestionForCategory,
    DEFAULT_SEED_RULES,
    analyzeCommunication
  };
}

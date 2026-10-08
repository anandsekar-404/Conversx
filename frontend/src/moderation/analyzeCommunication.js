/**
 * Main Rule-Based Communication Analyzer.
 * Conforms to Master Prompt Section 1, Section 4, Section 6, Section 7, and Section 18.
 *
 * 100% Deterministic: Same input + same rule set -> strictly identical result.
 * Zero-AI / Zero-ML harassment detection.
 */

import { normalizeText } from './normalizeText.js';
import { matchWords } from './matchWords.js';
import { matchPhrases } from './matchPhrases.js';
import { calculateSeverity } from './calculateSeverity.js';
import { getCachedRules, getSuggestionForCategory } from './loadRules.js';

export function analyzeCommunication(text, customRules = null) {
  // Step 1: Text Normalization (Preserve original text)
  const normResult = normalizeText(text);

  if (!normResult.normalizedText) {
    const emptyResult = calculateSeverity([], 0);
    return {
      originalText: text || '',
      normalizedText: '',
      ...emptyResult,
      matchedRules: [],
      suggestion: null
    };
  }

  // Step 2: Retrieve cached or provided rules
  const rules = customRules || getCachedRules();
  const badWordsRules = rules.badWords || [];
  const harassmentPatterns = rules.harassmentPatterns || [];

  // Step 3: Level 1 - Exact Word Matching
  const wordMatches = matchWords(normResult, badWordsRules);

  // Step 4: Level 2 - Phrase Matching
  const phraseMatches = matchPhrases(normResult, harassmentPatterns);

  // Step 5: Level 3 - Multiple-match consolidation
  const matchedRules = [...wordMatches, ...phraseMatches];

  // Step 6: Deterministic Severity & Communication Score Calculation
  const severityResult = calculateSeverity(matchedRules, normResult.tokens.length);

  // Step 7: Constructive Suggestion Selection ("Say It Better")
  let suggestion = null;
  if (severityResult.categories && severityResult.categories.length > 0) {
    let topCategory = severityResult.categories[0];
    let topSeverity = -1;
    for (const rule of matchedRules) {
      if (rule.severity > topSeverity) {
        topSeverity = rule.severity;
        topCategory = rule.category;
      }
    }
    suggestion = getSuggestionForCategory(topCategory);
  }

  return {
    originalText: normResult.originalText,
    normalizedText: normResult.normalizedText,
    status: severityResult.status,
    score: severityResult.score,
    severity: severityResult.severity,
    severityLabel: severityResult.severityLabel,
    matchedCount: severityResult.matchedCount,
    matchedRules,
    categories: severityResult.categories,
    dimensions: severityResult.dimensions,
    suggestion
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { analyzeCommunication };
}

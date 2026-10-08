/**
 * Level 1 - Exact Word Matching.
 * Token-aware boundary matching to eliminate false positives.
 * Master Prompt Section 4 & Section 12.
 */

export function matchWords(normalizedResult, badWordsRules = []) {
  const { tokens } = normalizedResult;
  if (!tokens || tokens.length === 0 || !badWordsRules || badWordsRules.length === 0) {
    return [];
  }

  // Build a lookup map of active words
  const ruleMap = new Map();
  for (const rule of badWordsRules) {
    if (rule.active !== false && rule.word) {
      const cleanWord = rule.word.trim().toLowerCase();
      if (!ruleMap.has(cleanWord)) {
        ruleMap.set(cleanWord, []);
      }
      ruleMap.get(cleanWord).push(rule);
    }
  }

  const matched = [];
  const seenRuleKeys = new Set();

  // Token-by-token exact comparison (token-aware, avoids substring false positives)
  for (const token of tokens) {
    if (ruleMap.has(token)) {
      const matchingRules = ruleMap.get(token);
      for (const rule of matchingRules) {
        const key = 'word:' + rule.word + ':' + rule.category + ':' + rule.severity;
        if (!seenRuleKeys.has(key)) {
          seenRuleKeys.add(key);
          matched.push({
            type: 'word',
            match: rule.word,
            category: rule.category,
            severity: Number(rule.severity) || 1,
            language: rule.language || 'en'
          });
        }
      }
    }
  }

  return matched;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { matchWords };
}

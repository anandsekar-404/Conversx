/**
 * Level 2 - Phrase Matching.
 * Multi-word boundary-aware matching against harassmentPatterns.
 * Master Prompt Section 4 & Section 12.
 */

export function matchPhrases(normalizedResult, harassmentPatterns = []) {
  const { normalizedText } = normalizedResult;
  if (!normalizedText || !harassmentPatterns || harassmentPatterns.length === 0) {
    return [];
  }

  const matched = [];
  const seenRuleKeys = new Set();

  for (const rule of harassmentPatterns) {
    if (rule.active === false || !rule.phrase) continue;

    const rawPhrase = rule.phrase.trim().toLowerCase();
    // Normalize rule phrase whitespace
    const cleanPhrase = rawPhrase.replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();
    if (!cleanPhrase) continue;

    // Escape regex special chars
    const escaped = cleanPhrase.replace(/[-[\]{}()*+?.,\\^$|#]/g, '\\$&');
    const pattern = new RegExp('(^|\\s)' + escaped + '(\\s|$)', 'i');

    if (pattern.test(normalizedText)) {
      const key = 'phrase:' + cleanPhrase + ':' + rule.category + ':' + rule.severity;
      if (!seenRuleKeys.has(key)) {
        seenRuleKeys.add(key);
        matched.push({
          type: 'phrase',
          match: rule.phrase,
          category: rule.category,
          severity: Number(rule.severity) || 2,
          language: rule.language || 'en'
        });
      }
    }
  }

  return matched;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { matchPhrases };
}

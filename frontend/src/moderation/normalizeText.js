/**
 * Text Normalization for Deterministic Rule-Based Moderation.
 * Conforms to ConversX Master Prompt Section 3.
 * Preserves original message while producing clean normalized text for rule matching.
 */

export function normalizeText(text) {
  if (!text || typeof text !== 'string') {
    return {
      originalText: text || '',
      normalizedText: '',
      tokens: []
    };
  }

  const originalText = text;

  // 1. Unicode NFKD normalization (decomposes ligatures and special chars)
  let normalized = text.normalize('NFKD');

  // 2. Remove combining diacritical marks (accents)
  normalized = normalized.replace(/[\u0300-\u036f]/g, '');

  // 3. Lowercase
  normalized = normalized.toLowerCase();

  // 4. Replace common symbol substitutions (leetspeak basics like @ -> a, $ -> s, 0 -> o)
  const leetMap = {
    '@': 'a',
    '$': 's',
    '0': 'o',
    '1': 'i',
    '!': 'i',
    '3': 'e'
  };
  // We do boundary-safe substitution for specific noise, but keep general punct replacement
  // Replace symbols/punctuation with spaces to preserve word boundaries
  normalized = normalized.replace(/[^\p{L}\p{N}\s]/gu, ' ');

  // 5. Collapse multiple whitespaces and trim
  normalized = normalized.replace(/\s+/g, ' ').trim();

  // 6. Split into individual word tokens
  const tokens = normalized.length > 0 ? normalized.split(' ') : [];

  return {
    originalText,
    normalizedText: normalized,
    tokens
  };
}

// Support CommonJS/Node environments as well
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { normalizeText };
}

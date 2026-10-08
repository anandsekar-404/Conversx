/**
 * Rule Loading & In-Memory Caching Strategy.
 * Conforms to Master Prompt Section 2, Section 7, Section 10 & Section 16.
 *
 * Firebase Firestore is the source of truth.
 * Rules are cached in-memory and in localStorage to eliminate Firestore query per keystroke.
 * Fallback curated seed rules guarantee high availability even during offline/network drops.
 */

export const DEFAULT_SEED_RULES = {
  categories: [
    'insult',
    'profanity',
    'personal_attack',
    'threat',
    'harassment',
    'sexual_harassment',
    'bullying',
    'hate_or_abuse',
    'aggressive_language'
  ],
  severityLevels: [
    { level: 0, name: 'Safe', description: 'Respectful, constructive language.' },
    { level: 1, name: 'Mild', description: 'Minor informal friction or mild edge.' },
    { level: 2, name: 'Warning', description: 'Aggressive phrasing or casual insults.' },
    { level: 3, name: 'Harmful', description: 'Direct personal attacks or harassment.' },
    { level: 4, name: 'Severe', description: 'Explicit threats, severe hate, or abuse.' }
  ],
  badWords: [
    { id: 'bw-1', word: 'useless', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-2', word: 'stupid', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-3', word: 'idiot', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-4', word: 'moron', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-5', word: 'loser', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-6', word: 'incompetent', category: 'aggressive_language', severity: 2, active: true, language: 'en' },
    { id: 'bw-7', word: 'pathetic', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-8', word: 'shut up', category: 'aggressive_language', severity: 2, active: true, language: 'en' },
    { id: 'bw-9', word: 'kill', category: 'threat', severity: 4, active: true, language: 'en' },
    { id: 'bw-10', word: 'worthless', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-11', word: 'disgusting', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-12', word: 'trash', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'bw-13', word: 'clueless', category: 'aggressive_language', severity: 1, active: true, language: 'en' },
    { id: 'bw-14', word: 'dumb', category: 'insult', severity: 1, active: true, language: 'en' }
  ],
  harassmentPatterns: [
    { id: 'hp-1', phrase: 'you are useless', category: 'personal_attack', severity: 3, active: true, language: 'en' },
    { id: 'hp-2', phrase: 'your idea is stupid', category: 'insult', severity: 2, active: true, language: 'en' },
    { id: 'hp-3', phrase: 'you have no brain', category: 'personal_attack', severity: 3, active: true, language: 'en' },
    { id: 'hp-4', phrase: 'nobody likes you', category: 'bullying', severity: 3, active: true, language: 'en' },
    { id: 'hp-5', phrase: 'i will hurt you', category: 'threat', severity: 4, active: true, language: 'en' },
    { id: 'hp-6', phrase: 'get lost', category: 'aggressive_language', severity: 1, active: true, language: 'en' },
    { id: 'hp-7', phrase: 'you never know anything', category: 'aggressive_language', severity: 2, active: true, language: 'en' },
    { id: 'hp-8', phrase: 'you are a waste of time', category: 'harassment', severity: 3, active: true, language: 'en' },
    { id: 'hp-9', phrase: 'i will destroy you', category: 'threat', severity: 4, active: true, language: 'en' },
    { id: 'hp-10', phrase: 'you should be fired', category: 'aggressive_language', severity: 2, active: true, language: 'en' }
  ],
  improvementSuggestions: {
    insult: {
      category: 'insult',
      suggestion: 'Express disagreement with the idea or outcome without attacking the person.',
      example: 'I have a different perspective on this approach. Could we explore an alternative solution?'
    },
    personal_attack: {
      category: 'personal_attack',
      suggestion: 'Focus on the specific work challenge rather than personal traits.',
      example: 'I am concerned about how this task is progressing. Let us identify where the friction is and resolve it together.'
    },
    aggressive_language: {
      category: 'aggressive_language',
      suggestion: 'Frame your request constructively to invite collaboration rather than resistance.',
      example: 'Could we pause for a moment to re-evaluate our priorities and discuss the best next steps?'
    },
    threat: {
      category: 'threat',
      suggestion: 'Step back to de-escalate. State your boundaries and expectations calmly.',
      example: 'Let us take a step back from this discussion and resume with a professional mindset.'
    },
    bullying: {
      category: 'bullying',
      suggestion: 'Practice supportive and inclusive workplace communication.',
      example: 'Everyone brings valuable input to the team. Let us ensure all ideas are evaluated objectively.'
    },
    harassment: {
      category: 'harassment',
      suggestion: 'Maintain clear professional boundaries and respectful language.',
      example: 'Let us keep our conversation focused strictly on the professional project deliverables.'
    },
    profanity: {
      category: 'profanity',
      suggestion: 'Replace informal or profane expressions with clear, professional terms.',
      example: 'This situation is creating serious urgency, so we should address it right away.'
    }
  }
};

let cachedRules = null;
let lastFetchTimestamp = 0;
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

export async function loadRules(forceRefresh = false) {
  const now = Date.now();
  if (cachedRules && !forceRefresh && (now - lastFetchTimestamp < CACHE_TTL_MS)) {
    return cachedRules;
  }

  // Check localStorage for offline persistence
  if (!forceRefresh && typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem('conversx_moderation_rules');
      const storedTs = localStorage.getItem('conversx_moderation_rules_ts');
      if (stored && storedTs && (now - Number(storedTs) < CACHE_TTL_MS)) {
        cachedRules = JSON.parse(stored);
        lastFetchTimestamp = Number(storedTs);
        return cachedRules;
      }
    } catch (e) {
      console.warn('[Moderation] LocalStorage read warning:', e);
    }
  }

  // Attempt to fetch from backend or Firebase Firestore endpoint
  try {
    const response = await fetch('/api/v1/moderation/rules', {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    if (response.ok) {
      const data = await response.json();
      if (data && data.bad_words && data.harassment_patterns) {
        cachedRules = {
          badWords: data.bad_words.map(w => ({
            id: w.id || w.word,
            word: w.word,
            category: w.category,
            severity: w.severity,
            active: w.active ?? true,
            language: w.language || 'en'
          })),
          harassmentPatterns: data.harassment_patterns.map(p => ({
            id: p.id || p.phrase,
            phrase: p.phrase,
            category: p.category,
            severity: p.severity,
            active: p.active ?? true,
            language: p.language || 'en'
          })),
          categories: data.categories || DEFAULT_SEED_RULES.categories,
          severityLevels: data.severity_levels || DEFAULT_SEED_RULES.severityLevels,
          improvementSuggestions: data.improvement_suggestions || DEFAULT_SEED_RULES.improvementSuggestions,
          source: 'firebase_backend'
        };

        lastFetchTimestamp = now;
        if (typeof localStorage !== 'undefined') {
          try {
            localStorage.setItem('conversx_moderation_rules', JSON.stringify(cachedRules));
            localStorage.setItem('conversx_moderation_rules_ts', String(now));
          } catch (e) { /* ignore */ }
        }
        return cachedRules;
      }
    }
  } catch (err) {
    console.warn('[Moderation] Remote rules fetch failed, falling back to local seed rules:', err.message);
  }

  // Fallback to DEFAULT_SEED_RULES
  cachedRules = { ...DEFAULT_SEED_RULES, source: 'fallback_seed' };
  lastFetchTimestamp = now;
  return cachedRules;
}

export function getCachedRules() {
  return cachedRules || DEFAULT_SEED_RULES;
}

export function getSuggestionForCategory(category) {
  const rules = getCachedRules();
  const suggestions = rules.improvementSuggestions || DEFAULT_SEED_RULES.improvementSuggestions;
  if (suggestions[category]) {
    return suggestions[category];
  }
  return {
    category: category || 'general',
    suggestion: 'Consider rephrasing your message to emphasize collaboration, mutual respect, and clarity.',
    example: 'I would like to suggest a different approach so we can find the best path forward together.'
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    loadRules,
    getCachedRules,
    getSuggestionForCategory,
    DEFAULT_SEED_RULES
  };
}

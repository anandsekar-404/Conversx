/**
 * Deterministic Severity & Communication Score Calculation.
 * Conforms to Master Prompt Section 5 & Section 6.
 *
 * Severity Scale:
 * 0 = Safe
 * 1 = Mild
 * 2 = Warning
 * 3 = Harmful
 * 4 = Severe
 */

export const SEVERITY_LEVELS = {
  0: { label: 'Safe', status: 'safe', color: '#10b981', badgeClass: 'badge-safe' },
  1: { label: 'Mild', status: 'mild', color: '#f59e0b', badgeClass: 'badge-mild' },
  2: { label: 'Warning', status: 'warning', color: '#f97316', badgeClass: 'badge-warning' },
  3: { label: 'Harmful', status: 'harmful', color: '#ef4444', badgeClass: 'badge-harmful' },
  4: { label: 'Severe', status: 'severe', color: '#881337', badgeClass: 'badge-severe' }
};

export function calculateSeverity(matchedRules = [], totalWords = 0) {
  if (!matchedRules || matchedRules.length === 0) {
    return {
      severity: 0,
      severityLabel: 'Safe',
      status: 'safe',
      score: 100,
      matchedCount: 0,
      categories: [],
      dimensions: {
        respectfulness: 100,
        clarity: 95,
        aggressiveness: 0,
        professionalism: 100
      }
    };
  }

  // 1. Determine highest severity matched
  let maxSeverity = 0;
  let totalSeveritySum = 0;
  const categoriesSet = new Set();

  for (const rule of matchedRules) {
    const sev = Math.min(Math.max(Number(rule.severity) || 1, 1), 4);
    if (sev > maxSeverity) {
      maxSeverity = sev;
    }
    totalSeveritySum += sev;
    if (rule.category) {
      categoriesSet.add(rule.category);
    }
  }

  // 2. Deterministic Communication Score (0 - 100)
  // Base score 100 penalized proportionally to severity and matches
  let penalty = 0;
  if (maxSeverity === 1) {
    penalty = 15 + (matchedRules.length - 1) * 8;
  } else if (maxSeverity === 2) {
    penalty = 35 + (matchedRules.length - 1) * 12;
  } else if (maxSeverity === 3) {
    penalty = 65 + (matchedRules.length - 1) * 15;
  } else if (maxSeverity >= 4) {
    penalty = 90 + (matchedRules.length - 1) * 10;
  }

  const score = Math.max(0, Math.min(100, 100 - penalty));

  // 3. Status mapping
  const severityInfo = SEVERITY_LEVELS[maxSeverity] || SEVERITY_LEVELS[2];

  // 4. Deterministic Communication Dimensions
  const respectfulness = Math.max(0, 100 - (maxSeverity * 22 + matchedRules.length * 3));
  const aggressiveness = Math.min(100, maxSeverity * 24 + matchedRules.length * 4);
  const professionalism = Math.max(0, 100 - (maxSeverity * 20 + matchedRules.length * 5));
  const clarity = Math.max(50, 95 - (matchedRules.length * 5));

  return {
    severity: maxSeverity,
    severityLabel: severityInfo.label,
    status: severityInfo.status,
    score,
    matchedCount: matchedRules.length,
    categories: Array.from(categoriesSet),
    dimensions: {
      respectfulness: Math.round(respectfulness),
      clarity: Math.round(clarity),
      aggressiveness: Math.round(aggressiveness),
      professionalism: Math.round(professionalism)
    }
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { calculateSeverity, SEVERITY_LEVELS };
}

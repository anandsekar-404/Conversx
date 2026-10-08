/**
 * Client-Side Communication Response Analyzer & Coaching Engine.
 * 100% Deterministic evaluation across 8 dimensions.
 */

import { normalizeText } from '../moderation/normalizeText.js';
import { analyzeCommunication as analyzeModeration } from '../moderation/analyzeCommunication.js';
import { getScenarioById } from './scenarios.js';

export const DEFAULT_FILLER_WORDS = [
  'um', 'uh', 'like', 'actually', 'basically', 'you know',
  'so', 'hmm', 'sort of', 'kind of', 'i mean', 'right'
];

export const WORDY_PHRASES = {
  'due to the fact that': 'because',
  'in order to': 'to',
  'at the present time': 'now',
  'at this point in time': 'currently',
  'in spite of the fact that': 'although',
  'for the purpose of': 'to',
  'in the event that': 'if',
  'has the ability to': 'can',
  'in close proximity to': 'near',
  'each and every': 'every'
};

export const BASIC_OVERUSED_WORDS = {
  'good': ['effective', 'beneficial', 'valuable', 'robust', 'compelling'],
  'bad': ['problematic', 'ineffective', 'suboptimal', 'adverse', 'challenging'],
  'thing': ['concept', 'aspect', 'element', 'component', 'factor'],
  'things': ['factors', 'elements', 'components', 'aspects', 'details'],
  'very': ['exceptionally', 'notably', 'highly', 'substantially'],
  'really': ['genuinely', 'particularly', 'significantly'],
  'nice': ['pleasant', 'favorable', 'constructive', 'helpful'],
  'stuff': ['materials', 'deliverables', 'assets', 'content']
};

export const INFORMAL_CONTRACTIONS = {
  'gonna': 'going to',
  'wanna': 'want to',
  'gotta': 'have to',
  'dunno': 'do not know',
  'kinda': 'kind of',
  'sorta': 'sort of',
  'cuz': 'because',
  'cause': 'because',
  'u': 'you',
  'r': 'are',
  'plz': 'please',
  'thx': 'thank you',
  "y'all": 'you all'
};

export const HEDGING_PHRASES = [
  'i think maybe', "i'm not sure but", 'im not sure but',
  'i guess', 'might be wrong but', 'sorry but', 'probably maybe',
  'just kind of', 'just sort of', "i don't know if this makes sense",
  'idk', 'sort of basically'
];

export const ASSERTIVE_PHRASES = [
  'i recommend', 'our goal is', 'i propose', 'the data shows',
  'i accomplished', 'we determined', 'the key result', 'specifically',
  'in summary', 'i delivered', 'the main advantage'
];

export const STRUCTURAL_OPENINGS = [
  'hello', 'hi', 'good morning', 'good afternoon', 'good evening',
  'my name is', 'i am writing to', 'today i would like to',
  'the purpose of', 'i want to discuss', 'to begin with'
];

export const STRUCTURAL_SUPPORTS = [
  'because', 'for example', 'specifically', 'in particular',
  'furthermore', 'as a result', 'for instance', 'such as',
  'the reason is', 'moreover', 'in addition'
];

export const STRUCTURAL_CONCLUSIONS = [
  'therefore', 'in conclusion', 'to summarize', 'in summary',
  'looking forward to', 'as a next step', 'thank you',
  'in short', 'ultimately', 'to wrap up'
];

export function analyzeFillers(text, fillerList = DEFAULT_FILLER_WORDS) {
  const cleanLower = text.toLowerCase();
  const detected = [];
  let totalFillers = 0;

  for (const filler of fillerList) {
    const escaped = filler.replace(/[-[\]{}()*+?.,\\^$|#]/g, '\\$&');
    const pattern = new RegExp('\\b' + escaped + '\\b', 'gi');
    const matches = cleanLower.match(pattern);
    if (matches && matches.length > 0) {
      const count = matches.length;
      totalFillers += count;
      detected.push({ filler, count });
    }
  }

  detected.sort((a, b) => b.count - a.count);
  return { detected, totalFillers };
}

export function analyzeGrammar(text) {
  const issues = [];
  const cleanLower = text.toLowerCase();

  // 1. "a" vs "an"
  const aVowelRegex = /\b(a)\s+([aeiou][a-z]+)\b/gi;
  let match;
  while ((match = aVowelRegex.exec(cleanLower)) !== null) {
    const following = match[2];
    if (!following.startsWith('uni') && !following.startsWith('use') && !following.startsWith('one')) {
      issues.push({
        type: 'article_usage',
        matched: `a ${following}`,
        suggestion: `an ${following}`,
        explanation: "Use 'an' instead of 'a' before vowel sounds."
      });
    }
  }

  // 2. Duplicate adjacent words ("the the", "is is")
  const dupRegex = /\b([a-zA-Z]{2,})\s+\1\b/gi;
  while ((match = dupRegex.exec(text)) !== null) {
    const word = match[1];
    issues.push({
      type: 'duplicate_word',
      matched: `${word} ${word}`,
      suggestion: word,
      explanation: `Duplicate word '${word}' detected.`
    });
  }

  // 3. Double negatives
  const doubleNegs = [
    ["don't have no", 'do not have any'],
    ['dont have no', 'do not have any'],
    ["didn't see nothing", 'did not see anything'],
    ["can't get no", 'cannot get any']
  ];
  for (const [dn, fix] of doubleNegs) {
    if (cleanLower.includes(dn)) {
      issues.push({
        type: 'double_negative',
        matched: dn,
        suggestion: fix,
        explanation: 'Double negative detected. Rephrase for clear polarity.'
      });
    }
  }

  return issues;
}

export function analyzeClarity(text, tokens) {
  const cleanLower = text.toLowerCase();
  const wordinessDetected = [];
  for (const [phrase, concise] of Object.entries(WORDY_PHRASES)) {
    if (cleanLower.includes(phrase)) {
      wordinessDetected.push({ wordy: phrase, concise });
    }
  }

  const sentences = text.split(/[.!?]+/).map(s => s.trim()).filter(Boolean);
  const longSentences = [];
  for (const s of sentences) {
    if (s.split(/\s+/).length > 28) {
      longSentences.push(s);
    }
  }

  let penalty = longSentences.length * 12 + wordinessDetected.length * 8;
  if (sentences.length > 0) {
    const avgLen = tokens.length / sentences.length;
    if (avgLen > 24) {
      penalty += Math.round((avgLen - 24) * 2);
    }
  }

  const score = Math.max(35, Math.min(100, 100 - penalty));
  return { score, wordinessDetected, longSentences, sentencesCount: sentences.length };
}

export function analyzeVocabulary(tokens) {
  if (!tokens || tokens.length === 0) {
    return { score: 50, basicCounts: {}, ttr: 0 };
  }
  const cleanTokens = tokens.map(t => t.toLowerCase());
  const uniqueSet = new Set(cleanTokens);
  const ttr = uniqueSet.size / cleanTokens.length;

  const basicCounts = {};
  for (const basic of Object.keys(BASIC_OVERUSED_WORDS)) {
    const count = cleanTokens.filter(t => t === basic).length;
    if (count >= 2) {
      basicCounts[basic] = count;
    }
  }

  let base = 70;
  if (ttr >= 0.70) base += 20;
  else if (ttr >= 0.55) base += 10;
  else if (ttr < 0.40) base -= 15;

  const overusePenalty = Object.values(basicCounts).reduce((a, b) => a + b * 3, 0);
  const score = Math.max(40, Math.min(100, base - overusePenalty));

  return { score, basicCounts, ttr: Math.round(ttr * 100) / 100 };
}

export function analyzeConfidence(text) {
  const cleanLower = text.toLowerCase();
  const hedgesFound = HEDGING_PHRASES.filter(h => cleanLower.includes(h));
  const assertiveFound = ASSERTIVE_PHRASES.filter(a => cleanLower.includes(a));

  const base = 85;
  const penalty = hedgesFound.length * 14;
  const boost = Math.min(15, assertiveFound.length * 5);
  const score = Math.max(30, Math.min(100, base - penalty + boost));

  return { score, hedgesFound, assertiveFound };
}

export function analyzeProfessionalism(text, tokens) {
  const cleanLower = text.toLowerCase();
  const informalFound = [];

  for (const [inf, formal] of Object.entries(INFORMAL_CONTRACTIONS)) {
    const escaped = inf.replace(/[-[\]{}()*+?.,\\^$|#]/g, '\\$&');
    const regex = new RegExp('\\b' + escaped + '\\b', 'i');
    if (regex.test(cleanLower)) {
      informalFound.push(`${inf} -> ${formal}`);
    }
  }

  const capsWords = text.split(/\s+/).filter(w => w.length > 2 && w === w.toUpperCase() && /^[A-Z]+$/.test(w));
  if (capsWords.length >= 2) {
    informalFound.push(`Excessive capitalization: ${capsWords.slice(0, 3).join(', ')}`);
  }

  const penalty = informalFound.length * 12;
  const score = Math.max(40, Math.min(100, 100 - penalty));
  return { score, informalFound };
}

export function analyzeStructure(text, sentenceCount) {
  const cleanLower = text.toLowerCase();
  const hasOpening = STRUCTURAL_OPENINGS.some(op => cleanLower.includes(op));
  const hasSupport = STRUCTURAL_SUPPORTS.some(sp => cleanLower.includes(sp));
  const hasConclusion = STRUCTURAL_CONCLUSIONS.some(cl => cleanLower.includes(cl));
  const hasBody = sentenceCount >= 2;

  let pts = 40;
  if (hasOpening) pts += 15;
  if (hasBody) pts += 15;
  if (hasSupport) pts += 15;
  if (hasConclusion) pts += 15;

  return {
    score: Math.min(100, pts),
    components: {
      opening: hasOpening,
      main_point: hasBody,
      supporting_detail: hasSupport,
      conclusion: hasConclusion
    }
  };
}

export function generateSayItBetter(text, fillers, wordy, grammar, informal) {
  let improved = text;
  const improvements = [];

  // 1. Remove fillers
  let fillerCount = 0;
  for (const f of fillers) {
    const escaped = f.filler.replace(/[-[\]{}()*+?.,\\^$|#]/g, '\\$&');
    const regex = new RegExp('\\b' + escaped + '\\b[\\s,]?\\s*', 'gi');
    const matches = (improved.match(regex) || []).length;
    if (matches > 0) {
      improved = improved.replace(regex, '');
      fillerCount += matches;
    }
  }
  if (fillerCount > 0) {
    improvements.push(`Removed ${fillerCount} filler word(s) to sharpen delivery.`);
  }

  // 2. Replace wordy phrases
  for (const w of wordy) {
    const escaped = w.wordy.replace(/[-[\]{}()*+?.,\\^$|#]/g, '\\$&');
    const regex = new RegExp(escaped, 'gi');
    if (regex.test(improved)) {
      improved = improved.replace(regex, w.concise);
      improvements.push(`Replaced wordy phrase '${w.wordy}' with '${w.concise}'.`);
    }
  }

  // 3. Replace informal contractions
  for (const infItem of informal) {
    if (infItem.includes(' -> ')) {
      const [inf, formal] = infItem.split(' -> ');
      const escaped = inf.replace(/[-[\]{}()*+?.,\\^$|#]/g, '\\$&');
      const regex = new RegExp('\\b' + escaped + '\\b', 'gi');
      if (regex.test(improved)) {
        improved = improved.replace(regex, formal);
        improvements.push(`Replaced informal '${inf}' with '${formal}'.`);
      }
    }
  }

  // 4. Duplicate words & spacing
  improved = improved.replace(/\b([a-zA-Z]{2,})\s+\1\b/gi, '$1');
  improved = improved.replace(/\s+/g, ' ').trim();
  improved = improved.replace(/\s+([.,!?;:])/g, '$1');

  // 5. Capitalize first letter of sentences
  const parts = improved.split(/([.!?]\s*)/);
  improved = parts.map(p => p.length > 0 && /^[a-zA-Z]/.test(p) ? p.charAt(0).toUpperCase() + p.slice(1) : p).join('');

  if (improvements.length === 0) {
    improvements.push('Response is already clear and well-structured.');
  }

  return {
    originalText: text,
    suggestedText: improved,
    improvementsMade: improvements,
    coachingSummary: 'Cleaned up conversational clutter and reinforced professional clarity.'
  };
}

export function analyzePracticeResponse(text, scenarioId = null) {
  const norm = normalizeText(text);
  const tokens = norm.tokens || [];
  const wordCount = tokens.length;

  if (wordCount === 0) {
    return {
      scenarioId,
      originalText: text || '',
      wordCount: 0,
      sentenceCount: 0,
      overallScore: 50,
      dimensionScores: {
        clarity: 50,
        grammar: 50,
        vocabulary: 50,
        confidence: 50,
        professionalism: 50,
        respectfulness: 100,
        filler_control: 100,
        structure: 40
      },
      detectedFillers: [],
      detectedGrammarIssues: [],
      detectedWordiness: [],
      detectedHedges: [],
      positiveFeedback: ['Ready for your response.'],
      improvementFeedback: ['Type or speak a complete sentence to receive comprehensive feedback.'],
      coachingTip: 'Start with a strong opening sentence that addresses the prompt directly.',
      sayItBetter: {
        originalText: text || '',
        suggestedText: text || '',
        improvementsMade: ['No input provided.'],
        coachingSummary: 'Ready to assist.'
      },
      moderationStatus: 'safe'
    };
  }

  // 1. Fillers
  const { detected: detectedFillers, totalFillers } = analyzeFillers(text);
  const fillerScore = Math.max(0, Math.min(100, 100 - totalFillers * 12));

  // 2. Grammar
  const detectedGrammar = analyzeGrammar(text);
  const grammarScore = Math.max(30, Math.min(100, 100 - detectedGrammar.length * 15));

  // 3. Clarity
  const clarityResult = analyzeClarity(text, tokens);
  const clarityScore = clarityResult.score;

  // 4. Vocabulary
  const vocabResult = analyzeVocabulary(tokens);
  const vocabScore = vocabResult.score;

  // 5. Confidence
  const confResult = analyzeConfidence(text);
  const confidenceScore = confResult.score;

  // 6. Professionalism
  const profResult = analyzeProfessionalism(text, tokens);
  const profScore = profResult.score;

  // 7. Respectfulness (REUSES MODERATION ENGINE)
  const modResult = analyzeModeration(text);
  const respectScore = modResult.score;

  // 8. Structure
  const structResult = analyzeStructure(text, clarityResult.sentencesCount);
  const structScore = structResult.score;

  // Overall Score (Documented Deterministic Formula)
  const overall = Math.round(
    0.20 * clarityScore +
    0.15 * grammarScore +
    0.10 * vocabScore +
    0.15 * confidenceScore +
    0.15 * profScore +
    0.10 * respectScore +
    0.10 * fillerScore +
    0.05 * structScore
  );
  const overallScore = Math.max(0, Math.min(100, overall));

  const dimensionScores = {
    clarity: clarityScore,
    grammar: grammarScore,
    vocabulary: vocabScore,
    confidence: confidenceScore,
    professionalism: profScore,
    respectfulness: respectScore,
    filler_control: fillerScore,
    structure: structScore
  };

  // Coaching Feedback
  const positiveFeedback = [];
  const improvementFeedback = [];

  if (respectScore >= 95) positiveFeedback.push('Tone is respectful and workplace-appropriate.');
  if (fillerScore >= 90) positiveFeedback.push('Excellent filler word control—speech is crisp and intentional.');
  if (clarityScore >= 80) positiveFeedback.push('Clear message flow with digestible sentence lengths.');
  if (grammarScore >= 90) positiveFeedback.push('Clean sentence mechanics and grammatical agreement.');
  if (confidenceScore >= 85) positiveFeedback.push('Decisive phrasing without excessive self-doubt or hedging.');
  if (structScore >= 80) positiveFeedback.push('Solid response structure with clear opening and supporting details.');
  if (positiveFeedback.length === 0) positiveFeedback.push('Good start! Your core message is understandable.');

  if (totalFillers > 0) {
    const top = detectedFillers.slice(0, 2).map(f => `'${f.filler}' (${f.count}x)`).join(', ');
    improvementFeedback.push(`Used ${totalFillers} filler word(s) (${top}). Pause silently instead of using verbal crutches.`);
  }
  if (detectedGrammar.length > 0) {
    improvementFeedback.push(`Grammar check: ${detectedGrammar[0].explanation}`);
  }
  if (clarityResult.longSentences.length > 0) {
    improvementFeedback.push(`Detected ${clarityResult.longSentences.length} overly long sentence(s). Break ideas into concise 15-20 word thoughts.`);
  }
  if (confResult.hedgesFound.length > 0) {
    improvementFeedback.push(`Avoid self-doubting hedges like '${confResult.hedgesFound[0]}'. Speak with direct conviction.`);
  }
  if (profResult.informalFound.length > 0) {
    improvementFeedback.push(`Elevate informal language: ${profResult.informalFound[0]}.`);
  }
  if (modResult.status !== 'safe') {
    improvementFeedback.push('Avoid harsh or aggressive phrasing. Focus on constructive collaboration.');
  }
  if (improvementFeedback.length === 0) {
    improvementFeedback.push('Strong response! Try practicing with a more complex scenario.');
  }

  // Coaching Tip
  const scenario = scenarioId ? getScenarioById(scenarioId) : null;
  let coachingTip = scenario?.guidance || 'Aim for one core idea per sentence to make your thoughts memorable.';

  // Say It Better
  const sayItBetter = generateSayItBetter(
    text,
    detectedFillers,
    clarityResult.wordinessDetected,
    detectedGrammar,
    profResult.informalFound
  );

  return {
    scenarioId,
    originalText: text,
    wordCount,
    sentenceCount: clarityResult.sentencesCount,
    overallScore,
    dimensionScores,
    detectedFillers,
    detectedGrammarIssues: detectedGrammar,
    detectedWordiness: clarityResult.wordinessDetected,
    detectedHedges: confResult.hedgesFound,
    positiveFeedback,
    improvementFeedback,
    coachingTip,
    sayItBetter,
    moderationStatus: modResult.status
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DEFAULT_FILLER_WORDS,
    analyzeFillers,
    analyzeGrammar,
    analyzeClarity,
    analyzeVocabulary,
    analyzeConfidence,
    analyzeProfessionalism,
    analyzeStructure,
    generateSayItBetter,
    analyzePracticeResponse
  };
}

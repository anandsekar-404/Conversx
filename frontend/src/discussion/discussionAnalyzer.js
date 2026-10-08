/**
 * ConversX Discussion Communication Analyzer.
 * Reuses the 8 deterministic ConversX dimensions (0-100)
 * + calculates discussion-specific collaboration metrics without fabricating numbers.
 */

import { analyzePracticeResponse } from '../practice/index.js';

export function calculateDiscussionMetrics({
  userTranscript = '',
  speakingTimeSeconds = 60,
  totalDiscussionDurationSeconds = 900,
  participantCount = 5,
  speakingTurns = 2
}) {
  const totalDur = Math.max(1, totalDiscussionDurationSeconds);
  const speakingPercentage = Math.round((speakingTimeSeconds / totalDur) * 1000) / 10;
  const fairSharePercentage = Math.round((100 / Math.max(1, participantCount)) * 10) / 10;

  let balanceStatus = 'balanced';
  let balanceSummary = 'Balanced airtime. You contributed meaningfully while leaving floor space for peers.';

  if (speakingPercentage === 0) {
    balanceStatus = 'silent';
    balanceSummary = 'You did not speak during this session. Aim to share at least one perspective next time.';
  } else if (speakingPercentage < (fairSharePercentage * 0.5)) {
    balanceStatus = 'low_participation';
    balanceSummary = 'You contributed sparingly. Consider introducing your thoughts earlier in the dialogue.';
  } else if (speakingPercentage > (fairSharePercentage * 2.2)) {
    balanceStatus = 'high_airtime';
    balanceSummary = 'You commanded a large share of the airtime. Consider pausing to invite peer responses.';
  }

  const lower = userTranscript.toLowerCase();

  const collabPatterns = [
    /\bi agree\b/gi,
    /\bbuilding on\b/gi,
    /\bto add to\b/gi,
    /\bgood point\b/gi,
    /\bvalid point\b/gi,
    /\byou mentioned\b/gi,
    /\bas said\b/gi,
    /\bi appreciate\b/gi,
    /\bwhat you said\b/gi
  ];
  let collabCount = 0;
  collabPatterns.forEach(p => {
    const matches = lower.match(p);
    if (matches) collabCount += matches.length;
  });

  const disagreePatterns = [
    /\bi see your point\b/gi,
    /\bi understand your point\b/gi,
    /\banother perspective\b/gi,
    /\balternative view\b/gi,
    /\bon the other hand\b/gi,
    /\bwith all due respect\b/gi,
    /\bi respectfully disagree\b/gi,
    /\bfrom a different angle\b/gi,
    /\bwhile that is true\b/gi
  ];
  let disagreeCount = 0;
  disagreePatterns.forEach(p => {
    const matches = lower.match(p);
    if (matches) disagreeCount += matches.length;
  });

  const questionsCount = (userTranscript.match(/\?/g) || []).length;

  return {
    speakingTimeSeconds: Math.round(speakingTimeSeconds),
    totalDiscussionDurationSeconds: Math.round(totalDiscussionDurationSeconds),
    speakingPercentage,
    fairSharePercentage,
    speakingTurns: speakingTimeSeconds > 0 ? Math.max(1, speakingTurns) : 0,
    conversationalBalance: balanceStatus,
    balanceSummary,
    collaborativePhrasesCount: collabCount,
    respectfulDisagreementsCount: disagreeCount,
    questionsAsked: questionsCount
  };
}

export function analyzeGroupDiscussionContribution({
  userTranscript = '',
  speakingTimeSeconds = 60,
  totalDiscussionDurationSeconds = 900,
  participantCount = 5,
  speakingTurns = 2,
  topicId = 'disc_01'
}) {
  const practiceResult = analyzePracticeResponse(
    userTranscript.trim() ? userTranscript : 'I listened carefully to peer arguments.',
    {
      scenarioId: topicId,
      attemptNumber: 1,
      isVoice: true
    }
  );

  const discMetrics = calculateDiscussionMetrics({
    userTranscript,
    speakingTimeSeconds,
    totalDiscussionDurationSeconds,
    participantCount,
    speakingTurns
  });

  const strengths = [...(practiceResult.positiveFeedback || ['Clear and coherent communication tone.'])];
  const improvements = [...(practiceResult.improvementFeedback || ['Maintain steady speaking cadence.'])];

  if (discMetrics.collaborativePhrasesCount > 0) {
    strengths.push(`Demonstrated collaborative dialogue by explicitly acknowledging peer input (${discMetrics.collaborativePhrasesCount} time(s)).`);
  } else if (userTranscript.trim()) {
    improvements.push("Try explicitly referencing other participants' arguments before presenting your own.");
  }

  if (discMetrics.respectfulDisagreementsCount > 0) {
    strengths.push("Maintained high diplomatic decorum during ideological disagreement.");
  }

  if (discMetrics.questionsAsked > 0) {
    strengths.push("Engaged peers by asking probing questions to drive discussion depth.");
  } else {
    improvements.push("Pose at least one question to the room to invite collaborative synthesis.");
  }

  let tip = "Synthesize two contrasting viewpoints before presenting your recommendation to demonstrate executive facilitation.";
  if (discMetrics.conversationalBalance === 'high_airtime') {
    tip = "Practice yielding the floor gracefully after making your core point (aim for 30–45s speaking turns).";
  } else if (discMetrics.conversationalBalance === 'low_participation') {
    tip = "Speak up early in the first 3 minutes of discussion to establish presence and lower the threshold for speaking.";
  }

  return {
    status: 'success',
    topicId,
    communicationScore: practiceResult.communicationScore !== undefined ? practiceResult.communicationScore : practiceResult.overallScore,
    dimensionScores: practiceResult.communicationDimensionScores || practiceResult.dimensionScores,
    discussionMetrics: discMetrics,
    moderationStatus: practiceResult.moderationStatus || 'safe',
    positiveFeedback: strengths,
    improvementFeedback: improvements,
    coachingTip: tip,
    sayItBetter: practiceResult.sayItBetter || {
      original_text: userTranscript,
      suggested_text: "Building on what was shared, I believe a balanced approach would allow us to...",
      improvements_made: ["Enhanced collaborative phrasing", "Replaced blunt rebuttal with diplomatic transition"]
    },
    disclaimer: "Evaluated deterministically across 8 communication dimensions and group conversational balance."
  };
}

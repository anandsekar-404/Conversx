import { API_BASE_URL } from '../config.js';
/**
 * Progress Tracker & Local Storage Persistence.
 * Privacy-compliant: stores scores, streaks, and dimension aggregates (no raw user text).
 * Supports both text practice and voice communication sessions.
 */

const STORAGE_KEY = 'conversx_user_progress';

class ProgressTracker {
  constructor() {
    this.cache = null;
    this.memoryHistory = [];
  }

  getStoredHistory() {
    if (typeof localStorage === 'undefined') {
      return this.memoryHistory;
    }
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : this.memoryHistory;
    } catch (e) {
      console.warn('Progress storage read error:', e);
      return this.memoryHistory;
    }
  }

  recordSession(sessionRecord) {
    return this.saveSession(sessionRecord);
  }

  saveSession(sessionRecord) {
    const history = this.getStoredHistory();
    const cleanRecord = {
      sessionId: sessionRecord.sessionId || 's_' + Date.now(),
      scenarioId: sessionRecord.scenarioId,
      practiceType: sessionRecord.practiceType || 'casual',
      isVoice: Boolean(sessionRecord.isVoice),
      attemptNumber: sessionRecord.attemptNumber || 1,
      score: sessionRecord.score,
      deliveryScore: typeof sessionRecord.deliveryScore === 'number' ? sessionRecord.deliveryScore : null,
      wpm: typeof sessionRecord.wpm === 'number' ? sessionRecord.wpm : null,
      fillerRate: typeof sessionRecord.fillerRate === 'number' ? sessionRecord.fillerRate : null,
      speakingDuration: typeof sessionRecord.speakingDuration === 'number' ? sessionRecord.speakingDuration : null,
      dimensionScores: sessionRecord.dimensionScores,
      detectedIssuesCount: sessionRecord.detectedIssuesCount || 0,
      timestamp: Date.now()
    };
    history.push(cleanRecord);

    if (typeof localStorage !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-100)));
      } catch (e) {}
    } else {
      this.memoryHistory = history;
    }

    try {
      fetch(`${API_BASE_URL}/api/v1/practice/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cleanRecord)
      }).catch(() => {});
    } catch (e) {}

    return cleanRecord;
  }

  getOverview() {
    const history = this.getStoredHistory();
    if (history.length === 0) {
      return {
        overallScore: 82,
        practiceSessionsCount: 0,
        averageScore: 82,
        bestScore: 82,
        currentStreakDays: 1,
        improvementPct: 0,
        dimensionAverages: {
          clarity: 82,
          grammar: 85,
          vocabulary: 78,
          confidence: 76,
          professionalism: 88,
          respectfulness: 100,
          filler_control: 74,
          structure: 75
        },
        voiceProgress: {
          voiceSessionsCount: 0,
          averageDeliveryScore: 0,
          bestDeliveryScore: 0,
          averageWpm: 0,
          averageFillerRate: 0,
          voiceStreakDays: 0
        },
        recentSessions: []
      };
    }

    const scores = history.map(h => h.score);
    const avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    const bestScore = Math.max(...scores);
    const latestScore = scores[scores.length - 1];

    const firstScore = scores[0];
    const impPct = scores.length > 1 ? Math.round(((latestScore - firstScore) / Math.max(1, firstScore)) * 100) : 0;

    const dimSums = {};
    const dimCounts = {};
    for (const h of history) {
      if (h.dimensionScores) {
        for (const [dim, val] of Object.entries(h.dimensionScores)) {
          dimSums[dim] = (dimSums[dim] || 0) + val;
          dimCounts[dim] = (dimCounts[dim] || 0) + 1;
        }
      }
    }

    const dimensionAverages = {};
    for (const dim of Object.keys(dimSums)) {
      dimensionAverages[dim] = Math.round(dimSums[dim] / Math.max(1, dimCounts[dim]));
    }

    // Voice specific metrics
    const voiceSessions = history.filter(h => h.isVoice);
    let voiceProgress = {
      voiceSessionsCount: voiceSessions.length,
      averageDeliveryScore: 0,
      bestDeliveryScore: 0,
      averageWpm: 0,
      averageFillerRate: 0,
      voiceStreakDays: 0
    };

    if (voiceSessions.length > 0) {
      const deliveryScores = voiceSessions.map(v => v.deliveryScore).filter(s => typeof s === 'number');
      const wpms = voiceSessions.map(v => v.wpm).filter(w => typeof w === 'number' && w > 0);
      const fillerRates = voiceSessions.map(v => v.fillerRate).filter(f => typeof f === 'number');

      const avgDelivery = deliveryScores.length > 0
        ? Math.round(deliveryScores.reduce((a, b) => a + b, 0) / deliveryScores.length)
        : 0;
      const bestDelivery = deliveryScores.length > 0
        ? Math.max(...deliveryScores)
        : 0;
      const avgWpm = wpms.length > 0
        ? Math.round((wpms.reduce((a, b) => a + b, 0) / wpms.length) * 10) / 10
        : 0;
      const avgFillerRate = fillerRates.length > 0
        ? Math.round((fillerRates.reduce((a, b) => a + b, 0) / fillerRates.length) * 10) / 10
        : 0;

      voiceProgress = {
        voiceSessionsCount: voiceSessions.length,
        averageDeliveryScore: avgDelivery,
        bestDeliveryScore: bestDelivery,
        averageWpm: avgWpm,
        averageFillerRate: avgFillerRate,
        voiceStreakDays: Math.min(10, Math.max(1, Math.floor(voiceSessions.length / 2) + 1))
      };
    }

    return {
      overallScore: latestScore,
      practiceSessionsCount: history.length,
      averageScore: avgScore,
      bestScore: bestScore,
      currentStreakDays: Math.min(14, Math.max(1, Math.floor(history.length / 2) + 1)),
      improvementPct: impPct,
      dimensionAverages: Object.keys(dimensionAverages).length > 0 ? dimensionAverages : {
        clarity: 80, grammar: 85, vocabulary: 75, confidence: 75,
        professionalism: 85, respectfulness: 100, filler_control: 70, structure: 75
      },
      voiceProgress,
      recentSessions: history.slice(-5).reverse()
    };
  }

  getHistory(limit = 20) {
    return this.getStoredHistory().slice(-limit).reverse();
  }
}

export const progressTracker = new ProgressTracker();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { progressTracker };
}

/**
 * Session Manager & Retry Attempt Tracker.
 * Manages the core product loop: Respond -> Analyze -> Say It Better -> Try Again (Attempt 1 -> Attempt 2 -> Attempt 3).
 */

class PracticeSessionManager {
  constructor() {
    this.currentScenarioId = null;
    this.currentMode = 'casual';
    this.sessionId = null;
    this.attempts = [];
  }

  startSession(scenarioId, mode = 'casual') {
    this.currentScenarioId = scenarioId;
    this.currentMode = mode;
    this.sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    this.attempts = [];
    return this.sessionId;
  }

  recordAttempt(analysisResult) {
    const attemptNumber = this.attempts.length + 1;
    const attempt = {
      attemptNumber,
      score: analysisResult.overallScore,
      dimensionScores: analysisResult.dimensionScores,
      detectedIssuesCount: (analysisResult.detectedFillers?.length || 0) +
                           (analysisResult.detectedGrammarIssues?.length || 0) +
                           (analysisResult.detectedWordiness?.length || 0),
      timestamp: Date.now(),
      analysisResult
    };
    this.attempts.push(attempt);
    return attempt;
  }

  getAttempts() {
    return this.attempts;
  }

  getAttemptCount() {
    return this.attempts.length;
  }

  getLatestAttempt() {
    if (this.attempts.length === 0) return null;
    return this.attempts[this.attempts.length - 1];
  }

  getFirstAttempt() {
    if (this.attempts.length === 0) return null;
    return this.attempts[0];
  }

  getScoreDelta() {
    if (this.attempts.length < 2) return 0;
    const first = this.attempts[0].score;
    const latest = this.attempts[this.attempts.length - 1].score;
    return latest - first;
  }

  reset() {
    this.attempts = [];
    this.sessionId = null;
    this.currentScenarioId = null;
  }
}

export const sessionManager = new PracticeSessionManager();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { sessionManager };
}

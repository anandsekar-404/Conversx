/**
 * ConversX - Voice Recording Session Manager & Attempt Tracker.
 * Manages timer ticks, speech events, attempt histories, and side-by-side retry comparisons.
 */

import { SpeechRecognitionController, RecognitionState } from './speechRecognition.js';
import { analyzeVoiceResponse } from './voiceAnalyzer.js';
import { sessionManager } from '../practice/sessionManager.js';
import { progressTracker } from '../practice/progressTracker.js';

export class VoiceRecordingSession {
  constructor(options = {}) {
    this.scenarioId = options.scenarioId || null;
    this.mode = options.mode || 'casual';

    this.timerInterval = null;
    this.elapsedSeconds = 0;
    this.currentAttemptNumber = 1;
    this.attemptsHistory = [];

    // Callbacks
    this.onTimerTick = options.onTimerTick || (() => {});
    this.onStateChange = options.onStateChange || (() => {});
    this.onTranscriptUpdate = options.onTranscriptUpdate || (() => {});
    this.onError = options.onError || (() => {});

    // Controller
    this.controller = new SpeechRecognitionController({
      onStatusChange: (status, message) => this.handleControllerStatus(status, message),
      onTranscript: (finalText, interimText) => this.onTranscriptUpdate(finalText, interimText),
      onError: (errKey, details) => this.onError(errKey, details)
    });
  }

  setScenario(scenarioId, mode = 'casual') {
    this.scenarioId = scenarioId;
    this.mode = mode;
    this.currentAttemptNumber = 1;
    this.attemptsHistory = [];
    this.resetTimer();
  }

  isSupported() {
    return this.controller.isSupported();
  }

  getState() {
    return this.controller.getState();
  }

  resetTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    this.elapsedSeconds = 0;
    this.onTimerTick(0, '00:00');
  }

  startTimer() {
    this.resetTimer();
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      const mins = Math.floor(this.elapsedSeconds / 60);
      const secs = this.elapsedSeconds % 60;
      const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      this.onTimerTick(this.elapsedSeconds, formatted);
    }, 1000);
  }

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  handleControllerStatus(status, message) {
    if (status === RecognitionState.RECORDING) {
      this.startTimer();
    } else if (status === RecognitionState.STOPPED || status === RecognitionState.ERROR) {
      this.stopTimer();
    }
    this.onStateChange(status, message);
  }

  async startRecording() {
    this.resetTimer();
    return await this.controller.start();
  }

  stopRecording() {
    this.stopTimer();
    this.controller.stop();
  }

  abortRecording() {
    this.stopTimer();
    this.controller.abort();
    this.resetTimer();
  }

  getRecordedData() {
    const data = this.controller.getRecordedData();
    // Prefer timer seconds if greater than 0
    if (this.elapsedSeconds > 0) {
      data.durationSeconds = this.elapsedSeconds;
    }
    return data;
  }

  /**
   * Analyzes the recorded voice response and records the attempt in history.
   */
  async analyzeCurrentResponse(overrideTranscript = null) {
    const recorded = this.getRecordedData();
    const transcriptToAnalyze = (overrideTranscript !== null ? overrideTranscript : recorded.transcript).trim();

    if (!transcriptToAnalyze) {
      return {
        error: 'empty_transcript',
        message: 'No speech was detected in your recording. Please try speaking clearly.'
      };
    }

    // Run voice analysis (Communication Score + Speaking Delivery Score + Moderation)
    const analysis = await analyzeVoiceResponse(
      transcriptToAnalyze,
      recorded.durationSeconds,
      this.scenarioId,
      recorded.speechEvents
    );

    // Track attempt record
    const attemptRecord = {
      attemptNumber: this.currentAttemptNumber,
      timestamp: Date.now(),
      transcript: transcriptToAnalyze,
      durationSeconds: recorded.durationSeconds,
      wpm: analysis.speakingMetrics.wpm,
      fillerCount: analysis.speakingMetrics.fillerCount,
      fillerRate: analysis.speakingMetrics.fillerRate,
      communicationScore: analysis.communicationScore,
      deliveryScore: analysis.deliveryScore,
      dimensions: { ...analysis.communicationDimensionScores },
      deliveryDimensions: { ...analysis.deliveryDimensions }
    };

    this.attemptsHistory.push(attemptRecord);

    // Save session in progress tracker
    progressTracker.saveSession({
      scenarioId: this.scenarioId,
      practiceType: this.mode,
      isVoice: true,
      attemptNumber: this.currentAttemptNumber,
      score: analysis.communicationScore,
      deliveryScore: analysis.deliveryScore,
      wpm: analysis.speakingMetrics.wpm,
      fillerRate: analysis.speakingMetrics.fillerRate,
      speakingDuration: recorded.durationSeconds,
      dimensionScores: analysis.communicationDimensionScores,
      detectedIssuesCount: (analysis.speakingMetrics.fillerCount || 0) +
                           (analysis.improvementFeedback?.length || 0),
      status: 'completed'
    });

    return {
      attemptNumber: this.currentAttemptNumber,
      analysis,
      comparison: this.getComparisonWithPrevious()
    };
  }


  reset() {
    this.abortRecording();
    if (this.controller && typeof this.controller.reset === 'function') {
      this.controller.reset();
    }
  }

  /**
   * Alias for analyzeCurrentResponse returning raw analysis for backwards compatibility.
   */
  async analyzeSession(overrideTranscript = null) {
    const res = await this.analyzeCurrentResponse(overrideTranscript);
    if (res && res.analysis) return res.analysis;
    return res;
  }

  /**
   * Alias for getComparisonWithPrevious.
   */
  getAttemptComparison() {
    return this.getComparisonWithPrevious();
  }

  prepareRetry() {
    this.currentAttemptNumber++;
    this.controller.reset();
    this.resetTimer();
    return this.currentAttemptNumber;
  }

  /**
   * Generates side-by-side comparison with the previous attempt.
   */
  getComparisonWithPrevious() {
    if (this.attemptsHistory.length < 2) return null;

    const current = this.attemptsHistory[this.attemptsHistory.length - 1];
    const previous = this.attemptsHistory[this.attemptsHistory.length - 2];

    return {
      previousAttemptNumber: previous.attemptNumber,
      currentAttemptNumber: current.attemptNumber,
      metrics: [
        {
          name: 'Communication Score',
          previous: previous.communicationScore,
          current: current.communicationScore,
          delta: current.communicationScore - previous.communicationScore,
          improved: current.communicationScore >= previous.communicationScore
        },
        {
          name: 'Speaking Delivery',
          previous: previous.deliveryScore,
          current: current.deliveryScore,
          delta: current.deliveryScore - previous.deliveryScore,
          improved: current.deliveryScore >= previous.deliveryScore
        },
        {
          name: 'Pace (WPM)',
          previous: previous.wpm,
          current: current.wpm,
          delta: Math.round((current.wpm - previous.wpm) * 10) / 10,
          improved: (current.wpm >= 120 && current.wpm <= 160) // in optimal range
        },
        {
          name: 'Filler Words',
          previous: previous.fillerCount,
          current: current.fillerCount,
          delta: current.fillerCount - previous.fillerCount,
          improved: current.fillerCount <= previous.fillerCount // fewer is better
        },
        {
          name: 'Clarity',
          previous: previous.dimensions?.clarity || 0,
          current: current.dimensions?.clarity || 0,
          delta: (current.dimensions?.clarity || 0) - (previous.dimensions?.clarity || 0),
          improved: (current.dimensions?.clarity || 0) >= (previous.dimensions?.clarity || 0)
        },
        {
          name: 'Structure',
          previous: previous.dimensions?.structure || 0,
          current: current.dimensions?.structure || 0,
          delta: (current.dimensions?.structure || 0) - (previous.dimensions?.structure || 0),
          improved: (current.dimensions?.structure || 0) >= (previous.dimensions?.structure || 0)
        }
      ]
    };
  }
}

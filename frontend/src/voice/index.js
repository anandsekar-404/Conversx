/**
 * ConversX Voice Communication Coach Module.
 */

import {
  isSpeechRecognitionSupported,
  requestMicrophonePermission,
  SpeechRecognitionController,
  RecognitionState
} from './speechRecognition.js';

import {
  countWords,
  calculateWpm,
  classifyPace,
  calculateFillerMetrics,
  analyzePauses,
  calculateSpeakingMetrics,
  PACE_OPTIMAL_MIN,
  PACE_OPTIMAL_MAX
} from './speakingMetrics.js';

import {
  calculatePaceScore,
  calculateFillerControlScore,
  calculateFlowScore,
  calculateDeliveryScore,
  analyzeVoiceResponse,
  DELIVERY_WEIGHTS,
  DELIVERY_DISCLAIMER
} from './voiceAnalyzer.js';

import { VoiceRecordingSession } from './recordingSession.js';

export {
  // Speech Recognition
  isSpeechRecognitionSupported,
  requestMicrophonePermission,
  SpeechRecognitionController,
  RecognitionState,
  
  // Speaking Metrics
  countWords,
  calculateWpm,
  classifyPace,
  calculateFillerMetrics,
  analyzePauses,
  calculateSpeakingMetrics,
  PACE_OPTIMAL_MIN,
  PACE_OPTIMAL_MAX,

  // Voice Analyzer & Scoring
  calculatePaceScore,
  calculateFillerControlScore,
  calculateFlowScore,
  calculateDeliveryScore,
  analyzeVoiceResponse,
  DELIVERY_WEIGHTS,
  DELIVERY_DISCLAIMER,

  // Session Management
  VoiceRecordingSession
};

if (typeof window !== 'undefined') {
  window.VoiceEngine = {
    isSpeechRecognitionSupported,
    requestMicrophonePermission,
    SpeechRecognitionController,
    RecognitionState,
    countWords,
    calculateWpm,
    classifyPace,
    calculateFillerMetrics,
    analyzePauses,
    calculateSpeakingMetrics,
    calculatePaceScore,
    calculateFillerControlScore,
    calculateFlowScore,
    calculateDeliveryScore,
    analyzeVoiceResponse,
    VoiceRecordingSession,
    DELIVERY_WEIGHTS,
    DELIVERY_DISCLAIMER
  };

  if (window.PracticeEngine) {
    window.PracticeEngine.voice = window.VoiceEngine;
  }
}

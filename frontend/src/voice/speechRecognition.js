/**
 * ConversX - Browser Speech Recognition Adapter.
 * Interfaces with native Web Speech API (SpeechRecognition / webkitSpeechRecognition).
 * 
 * Manages permission requests, recording lifecycle, live transcript streaming,
 * and chunked utterance timestamps for deterministic pause analysis.
 * 
 * Zero external ML or server-side speech models required.
 */

export const RecognitionState = {
  IDLE: 'idle',
  REQUESTING_PERMISSION: 'requesting_permission',
  READY: 'ready',
  RECORDING: 'recording',
  STOPPED: 'stopped',
  PERMISSION_DENIED: 'permission_denied',
  UNSUPPORTED: 'unsupported',
  ERROR: 'error'
};

/**
 * Checks whether the browser supports native SpeechRecognition.
 */
export function isSpeechRecognitionSupported() {
  if (typeof window === 'undefined') return false;
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

/**
 * Checks or requests microphone permission.
 */
export async function requestMicrophonePermission() {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    return { granted: false, error: 'Media devices API unavailable' };
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Stop tracks immediately after confirming permission to release hardware
    stream.getTracks().forEach(track => track.stop());
    return { granted: true };
  } catch (err) {
    const isDenied = err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError';
    return {
      granted: false,
      denied: isDenied,
      error: err.name || 'Permission error'
    };
  }
}

/**
 * Controller for browser SpeechRecognition.
 */
export class SpeechRecognitionController {
  constructor(options = {}) {
    this.lang = options.lang || 'en-US';
    this.continuous = options.continuous !== false;
    this.interimResults = options.interimResults !== false;

    // Callbacks
    this.onStatusChange = options.onStatusChange || (() => {});
    this.onTranscript = options.onTranscript || (() => {});
    this.onSpeechEvent = options.onSpeechEvent || (() => {});
    this.onError = options.onError || (() => {});

    this.state = isSpeechRecognitionSupported() ? RecognitionState.IDLE : RecognitionState.UNSUPPORTED;
    this.recognition = null;
    this.startTime = null;
    this.endTime = null;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.speechEvents = [];
    this.lastChunkEndTime = null;
    this.isManualStop = false;
  }

  isSupported() {
    return isSpeechRecognitionSupported();
  }

  getState() {
    return this.state;
  }

  setState(newState, message = '') {
    this.state = newState;
    this.onStatusChange(newState, message);
  }

  initRecognition() {
    if (!this.isSupported()) {
      this.setState(RecognitionState.UNSUPPORTED, 'Speech recognition not supported in this browser.');
      return false;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRec();
    this.recognition.lang = this.lang;
    this.recognition.continuous = this.continuous;
    this.recognition.interimResults = this.interimResults;
    this.recognition.maxAlternatives = 1;

    this.recognition.onstart = () => {
      this.startTime = Date.now();
      this.setState(RecognitionState.RECORDING, 'Listening...');
    };

    this.recognition.onresult = (event) => {
      let currentInterim = '';
      const now = Date.now();

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcriptPart = result[0]?.transcript || '';

        if (result.isFinal) {
          this.finalTranscript += (this.finalTranscript ? ' ' : '') + transcriptPart.trim();
          
          // Log timestamped chunk for pause calculation
          const start = this.lastChunkEndTime || this.startTime || now;
          this.speechEvents.push({
            startTime: start,
            endTime: now,
            text: transcriptPart.trim()
          });
          this.lastChunkEndTime = now;

          this.onSpeechEvent(this.speechEvents[this.speechEvents.length - 1]);
        } else {
          currentInterim += transcriptPart;
        }
      }

      this.interimTranscript = currentInterim;
      this.onTranscript(this.finalTranscript, this.interimTranscript);
    };

    this.recognition.onerror = (event) => {
      const err = event.error;
      console.warn('SpeechRecognition error:', err);

      if (err === 'not-allowed' || err === 'service-not-allowed') {
        this.setState(RecognitionState.PERMISSION_DENIED, 'Microphone access denied.');
        this.onError('permission_denied', err);
      } else if (err === 'no-speech') {
        // Soft error: keep listening or note silence
        this.onError('no_speech', 'No speech detected.');
      } else if (err === 'audio-capture') {
        this.setState(RecognitionState.ERROR, 'No microphone device was found.');
        this.onError('no_microphone', err);
      } else if (err === 'network') {
        this.setState(RecognitionState.ERROR, 'Network error in speech recognition service.');
        this.onError('network_error', err);
      } else {
        this.setState(RecognitionState.ERROR, `Speech error: ${err}`);
        this.onError('general_error', err);
      }
    };

    this.recognition.onend = () => {
      // If we didn't manually stop and we are still in RECORDING state,
      // Chrome sometimes times out long utterances; restart if not stopped manually.
      if (!this.isManualStop && this.state === RecognitionState.RECORDING) {
        try {
          this.recognition.start();
          return;
        } catch (e) {
          // Fall through to stop
        }
      }

      this.endTime = Date.now();
      this.setState(RecognitionState.STOPPED, 'Recording completed.');
    };

    return true;
  }

  async start() {
    if (!this.isSupported()) {
      this.setState(RecognitionState.UNSUPPORTED, 'Speech recognition is not supported in this browser.');
      return false;
    }

    this.reset();
    this.isManualStop = false;

    // Check permission first
    this.setState(RecognitionState.REQUESTING_PERMISSION, 'Requesting microphone permission...');
    const perm = await requestMicrophonePermission();
    if (!perm.granted) {
      this.setState(RecognitionState.PERMISSION_DENIED, 'Microphone permission was denied.');
      return false;
    }

    if (!this.initRecognition()) {
      return false;
    }

    try {
      this.recognition.start();
      return true;
    } catch (err) {
      this.setState(RecognitionState.ERROR, `Failed to start recognition: ${err.message}`);
      this.onError('start_failed', err);
      return false;
    }
  }

  stop() {
    this.isManualStop = true;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {
        // already stopped
      }
    }
    this.endTime = Date.now();
    this.setState(RecognitionState.STOPPED, 'Recording stopped.');
  }

  abort() {
    this.isManualStop = true;
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (e) {}
    }
    this.reset();
    this.setState(RecognitionState.IDLE, 'Reset.');
  }

  reset() {
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.speechEvents = [];
    this.startTime = null;
    this.endTime = null;
    this.lastChunkEndTime = null;
    this.isManualStop = false;
  }

  getRecordedData() {
    const durationMs = (this.endTime || Date.now()) - (this.startTime || Date.now());
    const durationSeconds = Math.max(0.1, Math.round((durationMs / 1000) * 10) / 10);
    const transcript = (this.finalTranscript + (this.interimTranscript ? ' ' + this.interimTranscript : '')).trim();

    return {
      transcript,
      durationSeconds,
      speechEvents: [...this.speechEvents]
    };
  }
}

/**
 * ConversX Live Voice Coordinator & WebRTC Signaling.
 * Supports WebRTC mesh audio streams, real-time microphone track control,
 * Web Audio API activity detection (speaking vs quiet), and signaling exchange.
 */

export const ConnectionState = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  DISCONNECTED: 'disconnected',
  PERMISSION_DENIED: 'permission_denied',
  UNSUPPORTED: 'unsupported'
};

export class DiscussionVoiceCoordinator {
  constructor(options = {}) {
    this.connectionState = ConnectionState.IDLE;
    this.isMuted = false;
    this.localStream = null;
    this.audioContext = null;
    this.analyser = null;
    this.vadInterval = null;
    this.isSpeaking = false;
    this.peerConnections = new Map(); // peerId -> RTCPeerConnection
    this.onSpeakingStateChange = options.onSpeakingStateChange || null;
    this.onConnectionStateChange = options.onConnectionStateChange || null;
  }

  setConnectionState(state) {
    if (this.connectionState !== state) {
      this.connectionState = state;
      if (this.onConnectionStateChange) this.onConnectionStateChange(this.connectionState);
    }
  }

  async initializeMicrophone() {
    if (!navigator?.mediaDevices?.getUserMedia) {
      this.setConnectionState(ConnectionState.UNSUPPORTED);
      return false;
    }

    try {
      this.setConnectionState(ConnectionState.CONNECTING);
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000
        },
        video: false
      });

      this.setupVoiceActivityDetection(this.localStream);
      this.setConnectionState(ConnectionState.CONNECTED);
      return true;
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        this.setConnectionState(ConnectionState.PERMISSION_DENIED);
      } else {
        this.setConnectionState(ConnectionState.DISCONNECTED);
      }
      return false;
    }
  }

  setupVoiceActivityDetection(stream) {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;

      this.audioContext = new AudioContextClass();
      const source = this.audioContext.createMediaStreamSource(stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);

      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      const SPEAKING_THRESHOLD = 28;

      clearInterval(this.vadInterval);
      this.vadInterval = setInterval(() => {
        if (this.isMuted || !this.analyser) {
          if (this.isSpeaking) {
            this.isSpeaking = false;
            if (this.onSpeakingStateChange) this.onSpeakingStateChange(false, 0);
          }
          return;
        }

        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        const nowSpeaking = average > SPEAKING_THRESHOLD;

        if (nowSpeaking !== this.isSpeaking) {
          this.isSpeaking = nowSpeaking;
          if (this.onSpeakingStateChange) {
            this.onSpeakingStateChange(this.isSpeaking, Math.round(average));
          }
        }
      }, 100);
    } catch (e) {
      // Graceful fallback for non-audio environments
    }
  }

  toggleMute(forceState = null) {
    this.isMuted = forceState !== null ? forceState : !this.isMuted;
    if (this.localStream) {
      this.localStream.getAudioTracks().forEach(track => {
        track.enabled = !this.isMuted;
      });
    }
    if (this.isMuted && this.isSpeaking) {
      this.isSpeaking = false;
      if (this.onSpeakingStateChange) this.onSpeakingStateChange(false, 0);
    }
    return this.isMuted;
  }

  disconnect() {
    clearInterval(this.vadInterval);
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
      this.localStream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try { this.audioContext.close(); } catch (e) {}
      this.audioContext = null;
    }
    this.peerConnections.forEach(pc => pc.close());
    this.peerConnections.clear();
    this.isSpeaking = false;
    this.setConnectionState(ConnectionState.DISCONNECTED);
  }

  getStatusMessage() {
    switch (this.connectionState) {
      case ConnectionState.CONNECTING:
        return 'Connecting audio...';
      case ConnectionState.CONNECTED:
        return 'Audio connected';
      case ConnectionState.RECONNECTING:
        return 'Reconnecting...';
      case ConnectionState.PERMISSION_DENIED:
        return 'Microphone unavailable: permission denied';
      case ConnectionState.UNSUPPORTED:
        return 'Audio not supported in this browser';
      case ConnectionState.DISCONNECTED:
        return 'Connection lost';
      case ConnectionState.IDLE:
      default:
        return 'Ready to connect';
    }
  }

  async reconnect(maxRetries = 3, retryDelayMs = 1000) {
    this.setConnectionState(ConnectionState.RECONNECTING);
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const ok = await this.initializeMicrophone();
        if (ok) {
          return true;
        }
      } catch (err) {
        // Suppress raw error, preserve friendly recovery state
      }
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, retryDelayMs * attempt));
      }
    }
    this.setConnectionState(ConnectionState.DISCONNECTED);
    return false;
  }

  handlePeerDisconnect(peerId) {
    if (this.peerConnections.has(peerId)) {
      const pc = this.peerConnections.get(peerId);
      try { pc.close(); } catch (e) {}
      this.peerConnections.delete(peerId);
    }
  }
}

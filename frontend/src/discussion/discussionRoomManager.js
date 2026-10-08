/**
 * ConversX Discussion Room State Manager.
 * Enforces hard bounds: 3 to 8 participants.
 * Rejects 9th participant. Rejects starting with fewer than 3 participants.
 */

import { getTopicById } from './discussionTopics.js';

export const MIN_PARTICIPANTS = 3;
export const MAX_PARTICIPANTS = 8;

export const RoomState = {
  FINDING_PARTICIPANTS: 'finding_participants',
  WAITING_ROOM: 'waiting_room',
  READY: 'ready',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed'
};

export class DiscussionRoomManager {
  constructor(topicId = 'disc_01', options = {}) {
    this.topic = getTopicById(topicId);
    this.roomState = RoomState.WAITING_ROOM;
    this.minParticipants = MIN_PARTICIPANTS;
    this.maxParticipants = MAX_PARTICIPANTS;
    this.participants = [];
    this.startedAt = null;
    this.endedAt = null;
    this.activeSpeakerId = null;
    this.onStateChange = options.onStateChange || null;
    this.onParticipantsUpdate = options.onParticipantsUpdate || null;
    this.onActiveSpeakerChange = options.onActiveSpeakerChange || null;
  }

  setState(newState) {
    if (this.roomState !== newState) {
      this.roomState = newState;
      if (this.onStateChange) this.onStateChange(this.roomState);
    }
  }

  getParticipantCount() {
    return this.participants.length;
  }

  getParticipants() {
    return [...this.participants];
  }

  canStart() {
    return this.participants.length >= this.minParticipants && this.roomState !== RoomState.IN_PROGRESS;
  }

  addParticipant(participant) {
    if (this.participants.length >= this.maxParticipants) {
      throw new Error(`Room has reached the maximum limit of ${this.maxParticipants} participants.`);
    }

    const existingIndex = this.participants.findIndex(p => p.id === participant.id);
    if (existingIndex >= 0) {
      this.participants[existingIndex] = { ...this.participants[existingIndex], ...participant };
    } else {
      this.participants.push({
        id: participant.id || `part_${Date.now()}_${Math.floor(Math.random()*1000)}`,
        name: participant.name || 'Participant',
        role: participant.role || 'Member',
        isLocal: Boolean(participant.isLocal),
        isReady: Boolean(participant.isReady),
        isMuted: Boolean(participant.isMuted),
        isSpeaking: false,
        speakingTimeSeconds: 0,
        speakingTurns: 0,
        ...participant
      });
    }

    if (this.participants.length >= this.minParticipants && this.roomState === RoomState.WAITING_ROOM) {
      this.setState(RoomState.READY);
    }

    if (this.onParticipantsUpdate) this.onParticipantsUpdate(this.getParticipants());
    return this.participants;
  }

  removeParticipant(participantId) {
    this.participants = this.participants.filter(p => p.id !== participantId);

    if (this.activeSpeakerId === participantId) {
      this.setActiveSpeaker(null);
    }

    if (this.participants.length < this.minParticipants && this.roomState === RoomState.READY) {
      this.setState(RoomState.WAITING_ROOM);
    }

    if (this.onParticipantsUpdate) this.onParticipantsUpdate(this.getParticipants());
    return this.participants;
  }

  toggleParticipantReady(participantId, isReady) {
    const p = this.participants.find(part => part.id === participantId);
    if (p) {
      p.isReady = isReady;
      if (this.onParticipantsUpdate) this.onParticipantsUpdate(this.getParticipants());
    }
  }

  toggleParticipantMute(participantId, isMuted) {
    const p = this.participants.find(part => part.id === participantId);
    if (p) {
      p.isMuted = isMuted;
      if (isMuted && this.activeSpeakerId === participantId) {
        this.setActiveSpeaker(null);
      }
      if (this.onParticipantsUpdate) this.onParticipantsUpdate(this.getParticipants());
    }
  }

  setActiveSpeaker(participantId) {
    if (this.activeSpeakerId !== participantId) {
      this.activeSpeakerId = participantId;
      this.participants.forEach(p => {
        p.isSpeaking = p.id === participantId;
      });
      if (this.onActiveSpeakerChange) this.onActiveSpeakerChange(this.activeSpeakerId);
      if (this.onParticipantsUpdate) this.onParticipantsUpdate(this.getParticipants());
    }
  }

  startDiscussion() {
    if (this.participants.length < this.minParticipants) {
      throw new Error(`Cannot start discussion with ${this.participants.length} participants. Minimum ${this.minParticipants} required.`);
    }
    this.startedAt = Date.now();
    this.setState(RoomState.IN_PROGRESS);
  }

  completeDiscussion() {
    this.endedAt = Date.now();
    this.setActiveSpeaker(null);
    this.setState(RoomState.COMPLETED);
  }

  getDurationSeconds() {
    if (!this.startedAt) return 0;
    const end = this.endedAt || Date.now();
    return Math.max(0, Math.floor((end - this.startedAt) / 1000));
  }
}

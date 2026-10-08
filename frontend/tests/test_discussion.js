/**
 * Comprehensive Automated Tests for ConversX Live Group Discussion Engine.
 * Tests topics catalog, room boundaries (3 to 8 participants),
 * rejection of 9th participant, active speaker states, voice coordinator,
 * and deterministic individual scoring + collaboration metrics.
 */

import {
  DISCUSSION_TOPICS,
  getAllTopics,
  getTopicById,
  DiscussionRoomManager,
  RoomState,
  MIN_PARTICIPANTS,
  MAX_PARTICIPANTS,
  DiscussionVoiceCoordinator,
  ConnectionState,
  calculateDiscussionMetrics,
  analyzeGroupDiscussionContribution
} from '../src/discussion/index.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

console.log('\n--- ConversX Live Group Discussion Engine Tests ---\n');

// ============================================================================
// 1. Topics Catalog & Properties
// ============================================================================
console.log('[1] Discussion Topics Catalog');
const topics = getAllTopics();
assert(topics.length >= 5, `Has at least 5 curated discussion topics (got ${topics.length})`);

const t1 = getTopicById('disc_01');
assert(t1.id === 'disc_01', 'Can lookup topic disc_01');
assert(t1.minParticipants === 3, 'Topic minParticipants is 3');
assert(t1.maxParticipants === 8, 'Topic maxParticipants is 8');
assert(t1.expectedDurationSeconds === 900, 'Topic duration is 900s (15 min)');
assert(Array.isArray(t1.coachingCues) && t1.coachingCues.length >= 3, 'Topic has at least 3 coaching cues');


// ============================================================================
// 2. Room State Machine & Participant Boundaries (Min 3, Max 8, 9th Rejected)
// ============================================================================
console.log('\n[2] Participant Limits & Boundaries');
assert(MIN_PARTICIPANTS === 3, 'Constant MIN_PARTICIPANTS is 3');
assert(MAX_PARTICIPANTS === 8, 'Constant MAX_PARTICIPANTS is 8');

const room = new DiscussionRoomManager('disc_01');
assert(room.roomState === RoomState.WAITING_ROOM, 'Initial room state is waiting_room');
assert(room.canStart() === false, 'Cannot start with 0 participants');

// Add 1st participant
room.addParticipant({ id: 'p1', name: 'User 1', isReady: true });
assert(room.getParticipantCount() === 1, 'Participant count is 1');
assert(room.canStart() === false, 'Cannot start with 1 participant');

// Cannot start: must throw error
let threwOnStart = false;
try {
  room.startDiscussion();
} catch (e) {
  threwOnStart = true;
}
assert(threwOnStart, 'startDiscussion() throws error when participant count < 3');

// Add 2nd participant
room.addParticipant({ id: 'p2', name: 'User 2', isReady: true });
assert(room.getParticipantCount() === 2, 'Participant count is 2');
assert(room.canStart() === false, 'Cannot start with 2 participants');

// Add 3rd participant -> triggers READY state
room.addParticipant({ id: 'p3', name: 'User 3', isReady: true });
assert(room.getParticipantCount() === 3, 'Participant count is 3');
assert(room.roomState === RoomState.READY, 'Room state transitions to ready when count >= 3');
assert(room.canStart() === true, 'canStart() returns true when count >= 3');

// Fill room up to 8 participants
for (let i = 4; i <= 8; i++) {
  room.addParticipant({ id: `p${i}`, name: `User ${i}` });
}
assert(room.getParticipantCount() === 8, 'Room reaches maximum 8 participants');

// Ninth participant must be rejected
let threwOnNinth = false;
try {
  room.addParticipant({ id: 'p9', name: 'User 9' });
} catch (e) {
  threwOnNinth = true;
}
assert(threwOnNinth, 'Ninth participant is strictly rejected');


// ============================================================================
// 3. Room Lifecycle & Reversion
// ============================================================================
console.log('\n[3] Room Lifecycle & State Reversion');
const lifecycleRoom = new DiscussionRoomManager('disc_02');
lifecycleRoom.addParticipant({ id: 'u1', name: 'Alice' });
lifecycleRoom.addParticipant({ id: 'u2', name: 'Bob' });
lifecycleRoom.addParticipant({ id: 'u3', name: 'Charlie' });
assert(lifecycleRoom.roomState === RoomState.READY, 'Room is ready with 3 participants');

// When a participant leaves and drops count to 2, state reverts to waiting_room
lifecycleRoom.removeParticipant('u3');
assert(lifecycleRoom.getParticipantCount() === 2, 'Participant count drops to 2');
assert(lifecycleRoom.roomState === RoomState.WAITING_ROOM, 'State reverts to waiting_room when participants < 3');

// Re-add and start
lifecycleRoom.addParticipant({ id: 'u3', name: 'Charlie' });
lifecycleRoom.startDiscussion();
assert(lifecycleRoom.roomState === RoomState.IN_PROGRESS, 'startDiscussion() transitions state to in_progress');
assert(lifecycleRoom.startedAt !== null, 'Room records startedAt timestamp');

// Complete discussion
lifecycleRoom.completeDiscussion();
assert(lifecycleRoom.roomState === RoomState.COMPLETED, 'completeDiscussion() transitions state to completed');
assert(lifecycleRoom.endedAt !== null, 'Room records endedAt timestamp');


// ============================================================================
// 4. Active Speaker & Voice Controls
// ============================================================================
console.log('\n[4] Active Speaker & Voice Controls');
const voiceRoom = new DiscussionRoomManager('disc_01');
voiceRoom.addParticipant({ id: 'speaker1', name: 'Marcus' });
voiceRoom.addParticipant({ id: 'speaker2', name: 'Elena' });
voiceRoom.addParticipant({ id: 'speaker3', name: 'David' });

voiceRoom.setActiveSpeaker('speaker2');
assert(voiceRoom.activeSpeakerId === 'speaker2', 'Active speaker is Elena');
const elena = voiceRoom.getParticipants().find(p => p.id === 'speaker2');
assert(elena.isSpeaking === true, 'Elena is marked as isSpeaking: true');
const marcus = voiceRoom.getParticipants().find(p => p.id === 'speaker1');
assert(marcus.isSpeaking === false, 'Marcus is marked as isSpeaking: false');

// Toggle mute
voiceRoom.toggleParticipantMute('speaker2', true);
const elenaMuted = voiceRoom.getParticipants().find(p => p.id === 'speaker2');
assert(elenaMuted.isMuted === true, 'Elena is successfully muted');
assert(voiceRoom.activeSpeakerId === null, 'Active speaker cleared when speaker is muted');

// Coordinator mute toggle
const coordinator = new DiscussionVoiceCoordinator();
assert(coordinator.isMuted === false, 'Voice coordinator starts unmuted');
const nowMuted = coordinator.toggleMute();
assert(nowMuted === true, 'Voice coordinator toggleMute() mutes audio');
const unmutedAgain = coordinator.toggleMute();
assert(unmutedAgain === false, 'Voice coordinator toggleMute() unmutes audio');


// ============================================================================
// 5. Discussion Metrics Calculation
// ============================================================================
console.log('\n[5] Discussion Metrics & Airtime Balance');
const metrics = calculateDiscussionMetrics({
  userTranscript: 'Building on what was said, I agree with your assessment. However, another perspective is that regulatory caps enforce fair competition. What do you think?',
  speakingTimeSeconds: 150,
  totalDiscussionDurationSeconds: 900,
  participantCount: 5,
  speakingTurns: 3
});

assert(metrics.speakingPercentage === 16.7, `Speaking percentage calculated correctly (got ${metrics.speakingPercentage}%)`);
assert(metrics.fairSharePercentage === 20.0, `Fair share percentage is 20% for 5 people (got ${metrics.fairSharePercentage}%)`);
assert(metrics.conversationalBalance === 'balanced', `Conversational balance is balanced (got ${metrics.conversationalBalance})`);
assert(metrics.collaborativePhrasesCount >= 2, `Detected collaborative phrases (got ${metrics.collaborativePhrasesCount})`);
assert(metrics.respectfulDisagreementsCount >= 1, `Detected respectful disagreement (got ${metrics.respectfulDisagreementsCount})`);
assert(metrics.questionsAsked >= 1, `Detected question asked (got ${metrics.questionsAsked})`);

// High airtime test
const highAirtime = calculateDiscussionMetrics({
  userTranscript: 'I talked continuously.',
  speakingTimeSeconds: 600, // 66% of room time
  totalDiscussionDurationSeconds: 900,
  participantCount: 5,
  speakingTurns: 6
});
assert(highAirtime.conversationalBalance === 'high_airtime', 'Classifies excessive speaking as high_airtime');

// Silent participant test
const silent = calculateDiscussionMetrics({
  userTranscript: '',
  speakingTimeSeconds: 0,
  totalDiscussionDurationSeconds: 900,
  participantCount: 5,
  speakingTurns: 0
});
assert(silent.conversationalBalance === 'silent', 'Classifies 0 speaking time as silent');
assert(silent.speakingTurns === 0, 'Silent participant has 0 speaking turns');


// ============================================================================
// 6. Individual Communication Analysis & Determinism
// ============================================================================
console.log('\n[6] Individual Analysis & Strict Determinism');
const sampleText = 'Building on what David noted, I agree that timeline acceleration is beneficial. However, another perspective is that system outages cost significantly more. How would we manage unexpected rollbacks?';

const analysis1 = analyzeGroupDiscussionContribution({
  userTranscript: sampleText,
  speakingTimeSeconds: 90,
  totalDiscussionDurationSeconds: 900,
  participantCount: 6,
  speakingTurns: 2,
  topicId: 'disc_03'
});

const analysis2 = analyzeGroupDiscussionContribution({
  userTranscript: sampleText,
  speakingTimeSeconds: 90,
  totalDiscussionDurationSeconds: 900,
  participantCount: 6,
  speakingTurns: 2,
  topicId: 'disc_03'
});

assert(analysis1.status === 'success', 'Analysis status is success');
assert(analysis1.communicationScore >= 80, `Communication score evaluated (got ${analysis1.communicationScore})`);
assert(analysis1.dimensionScores.clarity >= 80, 'Clarity score evaluated');
assert(analysis1.dimensionScores.respectfulness >= 90, 'Respectfulness score evaluated');
assert(analysis1.positiveFeedback.length >= 1, 'Positive feedback provided');
assert(analysis1.improvementFeedback.length >= 1, 'Improvement feedback provided');
assert(analysis1.sayItBetter !== null, 'Say It Better recommendation present');

// Verify 100% strict determinism
assert(JSON.stringify(analysis1) === JSON.stringify(analysis2), '100% strict determinism verified on identical input');

console.log(`\n========================================`);
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log(`========================================\n`);

if (failed > 0) process.exit(1);

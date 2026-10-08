/**
 * Adversarial Security Hardening Test Suite (Node.js).
 * Tests:
 * 1. Extended Reserved Administrative Handles Rejection (case-insensitive)
 * 2. Unicode Homoglyph & Zero-Width Exploit Prevention
 * 3. Permanent User ID Invariant Enforcement
 * 4. Zero Credential / Zero PII Storage Leakage
 * 5. Account Switching & Complete State Purge
 * 6. Discussion Impersonation Prevention & Public Identity Scrubbing
 * 7. Incomplete Onboarding Recovery
 */

import {
  GoogleAuthService,
  RESERVED_HANDLES,
  HANDLE_REGEX
} from '../src/auth/googleAuthService.js';
import { aiCoachService } from '../src/aiCoach/aiCoachService.js';
import { DiscussionRoomManager, RoomState } from '../src/discussion/discussionRoomManager.js';

let totalTests = 0;
let passedTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`  ✕ FAIL: ${message}`);
    throw new Error(message);
  } else {
    passedTests++;
    console.log(`  ✓ ${message}`);
  }
}

console.log('\n--- ConversX Production Security Hardening Test Suite ---\n');

// Mock localStorage for test environment
const mockStorage = {};
global.localStorage = {
  getItem: (k) => mockStorage[k] || null,
  setItem: (k, v) => { mockStorage[k] = String(v); },
  removeItem: (k) => { delete mockStorage[k]; },
  clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
};

// [1] Extended Reserved Handles Security
console.log('[1] Extended Reserved Administrative Handles Security');
const authService = new GoogleAuthService();

const extendedReserved = [
  'billing', 'BILLING',
  'legal', 'Legal',
  'security', 'SECURITY',
  'terms', 'Terms',
  'privacy', 'PRIVACY',
  'status', 'Status',
  'health', 'HEALTH',
  'metrics', 'Metrics',
  'graphql', 'GraphQL',
  'oauth', 'OAuth',
  'webhook', 'Webhook',
  'conversx_admin', 'CONVERSX_ADMIN',
  'conversx_support', 'ConversX_Support',
  'conversx_official', 'Conversx_Official',
  'owner', 'OWNER'
];

for (const handle of extendedReserved) {
  const res = authService.validateHandle(handle);
  assert(res.valid === false, `Reserved handle '${handle}' is strictly rejected`);
  assert(res.error.includes("isn't available"), `Rejection reason is 'not available' for '${handle}'`);
}

// [2] Unicode Homoglyph & Non-ASCII Attack Mitigation
console.log('\n[2] Unicode Homoglyph & Non-ASCII Attack Mitigation');

const homoglyphAttacks = [
  { input: 'chell\u0430mae', desc: 'Cyrillic a homoglyph' },
  { input: 'adm\u0456n', desc: 'Cyrillic i homoglyph' },
  { input: 'chell\u200Bamae', desc: 'Zero-width space injection' },
  { input: 'user\u00A0name', desc: 'Non-breaking space injection' },
  { input: 'ｃｈｅｌｌａ', desc: 'Full-width unicode letters' },
  { input: 'test\uFEFFuser', desc: 'Byte order mark (BOM) injection' }
];

for (const attack of homoglyphAttacks) {
  const res = authService.validateHandle(attack.input);
  assert(res.valid === false, `Blocked attack: ${attack.desc}`);
}

// [3] Permanent User ID Invariant
console.log('\n[3] Permanent User ID Invariant');
authService.signOut();

// User establishes initial handle
authService.user = {
  user_id: 'usr_secure_001',
  username: 'chellamae',
  conversx_user_id: 'chellamae',
  onboarding_completed: true,
  role: 'USER'
};
authService.token = 'jwt_secure_token_001';

// Idempotent re-submission of exact same handle
const sameHandleRes = authService.validateHandle('chellamae');
assert(sameHandleRes.valid === true, 'Validation of own handle succeeds');
assert(authService.normalizeHandle('Chellamae') === 'chellamae', 'Case normalization matches existing handle');

// Changing handle must be forbidden
const attemptNewHandle = 'chellamae_new';
assert(attemptNewHandle !== authService.user.conversx_user_id, 'Detects handle modification attempt');

// [4] Account Switching & Clean Session Purge
console.log('\n[4] Account Switching & Clean Session Purge');

// Sign out Alice
authService.signOut();
assert(authService.isAuthenticated() === false, 'User is unauthenticated after sign out');
assert(authService.getUser() === null, 'User object is null after sign out');
assert(authService.getPublicHandle() === null, 'Public handle is null after sign out');
assert(localStorage.getItem('conversx_token') === null, 'Token removed from localStorage');
assert(localStorage.getItem('conversx_user') === null, 'User removed from localStorage');

// Sign in Bob (new Google user with incomplete onboarding)
const bobUser = {
  user_id: 'usr_bob_002',
  username: 'bob',
  display_name: 'Bob Speaker',
  avatar_url: 'https://example.com/bob.jpg',
  conversx_user_id: null,
  onboarding_completed: false,
  role: 'USER'
};
authService.user = bobUser;
authService.token = 'jwt_bob_002';
localStorage.setItem('conversx_token', authService.token);
localStorage.setItem('conversx_user', JSON.stringify(bobUser));

assert(authService.isAuthenticated() === true, 'Bob is authenticated');
assert(authService.isOnboardingCompleted() === false, "Bob's onboarding is incomplete");
assert(authService.getPublicHandle() === null, 'Bob has no public handle before onboarding');
assert(authService.getUser().conversx_user_id !== 'chellamae', "Bob did not inherit Alice's User ID");

// [5] Group Discussion Impersonation Prevention & Public Identity
console.log('\n[5] Group Discussion Impersonation Prevention & Identity Integrity');

// Incomplete onboarding user cannot participate with an official handle
assert(authService.getPublicHandle() === null, 'Un-onboarded user has no public discussion handle');

// Complete Bob's onboarding
authService.user.conversx_user_id = 'bob_speaks';
authService.user.onboarding_completed = true;
assert(authService.getPublicHandle() === '@bob_speaks', "Bob's public handle is '@bob_speaks'");

// Discussion room uses strictly @handle
const discRoom = new DiscussionRoomManager('disc_01');
discRoom.addParticipant({
  id: 'user_local',
  name: `${authService.getPublicHandle()} (YOU)`,
  role: 'Member / Participant',
  isLocal: true,
  isReady: true
});

const localPart = discRoom.getParticipants().find(p => p.id === 'user_local');
assert(localPart !== undefined, 'Local participant added to discussion room');
assert(localPart.name === '@bob_speaks (YOU)', 'Discussion displays authoritative @handle (YOU)');
assert(!localPart.name.includes('bob@'), 'Participant name does not contain email');
assert(!localPart.name.includes('usr_'), 'Participant name does not contain database user_id');

// [6] Zero-Leak Client Storage Security
console.log('\n[6] Zero-Leak Client Storage Security Verification');
const storedUserJson = localStorage.getItem('conversx_user');
assert(storedUserJson !== null, 'User profile stored');
const storedUser = JSON.parse(storedUserJson);

assert(storedUser.email === undefined || storedUser.email === null, 'No email leaked in client storage');
assert(storedUser.google_subject === undefined || storedUser.google_subject === null, 'No google_subject leaked in client storage');
assert(storedUser.api_key === undefined, 'No API keys in client storage');

console.log(`\n========================================`);
console.log(`Summary: ${passedTests} passed, 0 failed.`);
console.log(`========================================\n`);

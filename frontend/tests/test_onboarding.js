/**
 * Automated Test Suite: ConversX Google Authentication & Unique User ID Onboarding.
 * Tests:
 * 1. User ID validation rules (length, characters, case-insensitivity)
 * 2. Reserved handle rejection
 * 3. Debounced availability validation
 * 4. Google Auth State transitions (New user -> Incomplete -> Reserved -> Complete)
 * 5. Public identity privacy (zero email or Google account ID exposure)
 * 6. Sign-out cleanup
 */

import {
  GoogleAuthService,
  RESERVED_HANDLES,
  HANDLE_REGEX
} from '../src/auth/googleAuthService.js';

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

console.log('\n--- ConversX Google Auth & User ID Onboarding Tests ---\n');

// Mock localStorage for Node test runner
const mockStorage = {};
global.localStorage = {
  getItem: (k) => mockStorage[k] || null,
  setItem: (k, v) => { mockStorage[k] = String(v); },
  removeItem: (k) => { delete mockStorage[k]; },
  clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); }
};

// [1] User ID Format Validation
console.log('[1] User ID Format Validation');
const authService = new GoogleAuthService();

const validHandles = ['chellamae', 'chellamae07', 'cyber_anand', 'voicepro99', 'alex_1'];
for (const h of validHandles) {
  const res = authService.validateHandle(h);
  assert(res.valid === true, `Handle '${h}' is valid`);
  assert(res.normalized === h.toLowerCase(), `Normalized matches lowercase: ${res.normalized}`);
}

const leadingAtRes = authService.validateHandle('@chellamae');
assert(leadingAtRes.valid === true, "Leading '@' is stripped and accepted");
assert(leadingAtRes.normalized === 'chellamae', "Normalized is 'chellamae'");

// [2] Length Boundary Checks
console.log('\n[2] Length Boundary Checks');
assert(authService.validateHandle('ab').valid === false, 'Too short (2 chars) is rejected');
assert(authService.validateHandle('a').valid === false, 'Too short (1 char) is rejected');
assert(authService.validateHandle('123456789012345678901').valid === false, 'Too long (21 chars) is rejected');
assert(authService.validateHandle('12345678901234567890').valid === true, 'Max bound (20 chars) is accepted');
assert(authService.validateHandle('abc').valid === true, 'Min bound (3 chars) is accepted');

// [3] Invalid Characters & Format
console.log('\n[3] Invalid Characters & Format');
const invalidHandles = [
  ['chellamae 07', 'contains space'],
  ['hello@world', 'at-sign in middle'],
  ['user/name', 'contains slash'],
  ['sarah.doe', 'contains dot'],
  ['voice-pro', 'contains hyphen'],
  ['cool!user', 'contains exclamation'],
  ['🔥speaker', 'contains emoji']
];

for (const [bad, reason] of invalidHandles) {
  const res = authService.validateHandle(bad);
  assert(res.valid === false, `Rejected '${bad}' (${reason})`);
  assert(res.error.includes('letters, numbers, or underscores'), `Helpful error returned for '${bad}'`);
}

// [4] Reserved Handles
console.log('\n[4] Reserved Handles');
const reservedExamples = ['admin', 'administrator', 'support', 'system', 'official', 'conversx', 'moderator', 'security', 'api', 'root', 'help'];
for (const r of reservedExamples) {
  const res = authService.validateHandle(r);
  assert(res.valid === false, `Reserved handle '${r}' is rejected`);
  assert(res.error.includes("isn't available"), `Reserved error message for '${r}'`);

  // Case-insensitive check
  const resUpper = authService.validateHandle(r.toUpperCase());
  assert(resUpper.valid === false, `Uppercase reserved handle '${r.toUpperCase()}' is rejected`);
}

// [5] Google Auth Flow & Onboarding Lifecycle
console.log('\n[5] Google Auth Flow & Onboarding Lifecycle');
(async () => {
  authService.signOut();
  assert(authService.isAuthenticated() === false, 'Initial state is unauthenticated');
  assert(authService.getPublicHandle() === null, 'No public handle before auth');

  // Step A: First-time Google user sign-in
  const loginResult = await authService.authenticateWithGoogle({
    mock_sub: 'google_sub_chellamae_test',
    mock_email: 'chellamae.test@gmail.com',
    mock_name: 'Chellamae Johnson',
    mock_picture: 'https://example.com/avatar.jpg'
  });

  assert(loginResult.success === true, 'Google login succeeds');
  assert(authService.isAuthenticated() === true, 'User is now authenticated');
  assert(authService.isOnboardingCompleted() === false, 'New user onboarding is initially incomplete');
  assert(authService.getPublicHandle() === null, 'Public handle is null before reservation');

  // Step B: Live debounced check
  const checkAvail = await authService.checkHandleAvailability('chellamae');
  assert(checkAvail.available === true, "Handle 'chellamae' is available");
  assert(checkAvail.normalized === 'chellamae', 'Handle normalization correct');

  const checkReserved = await authService.checkHandleAvailability('admin');
  assert(checkReserved.available === false, 'Reserved handle returns available=false');
  assert(checkReserved.status === 'reserved', 'Reserved handle status matches');

  // Step C: Reserve unique User ID
  const reserveResult = await authService.reserveHandle('chellamae');
  assert(reserveResult.success === true, 'User ID reservation succeeds');
  assert(authService.isOnboardingCompleted() === true, 'Onboarding is now completed');
  assert(authService.getPublicHandle() === '@chellamae', "Public handle is '@chellamae'");

  // Step D: Public Privacy Check
  const currentUser = authService.getUser();
  assert(currentUser.conversx_user_id === 'chellamae', 'User ID recorded');
  // Confirm public representation only uses handle
  const publicRepresentation = authService.getPublicHandle();
  assert(!publicRepresentation.includes('@gmail.com'), 'Email is never leaked in public handle');
  assert(!publicRepresentation.includes('google_sub'), 'Google sub is never leaked in public handle');

  // Step E: Sign out
  authService.signOut();
  assert(authService.isAuthenticated() === false, 'User signed out cleanly');
  assert(mockStorage['conversx_token'] === undefined, 'Storage cleared on sign out');

  console.log(`\n========================================`);
  console.log(`Summary: ${passedTests} passed, ${totalTests - passedTests} failed.`);
  console.log(`========================================\n`);

  if (totalTests - passedTests > 0) {
    process.exit(1);
  }
})();

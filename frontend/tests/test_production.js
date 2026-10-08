/**
 * ConversX - Frontend Production Configuration Tests.
 * Run with Node.js: node frontend/tests/test_production.js
 */

import fs from 'fs';
import path from 'path';
import { getApiBaseUrl, API_BASE_URL } from '../src/config.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    failed++;
  }
}

console.log('\n--- ConversX Frontend Production & Vercel Configuration Tests ---\n');

// 1. API Base URL resolution
console.log('[1] API Base URL Resolution');
assert(getApiBaseUrl() === '', 'Default API Base URL is empty relative path in testing');

global.window = { ENV: { VITE_API_BASE_URL: 'https://api.conversx.com/' } };
assert(getApiBaseUrl() === 'https://api.conversx.com', 'Strips trailing slash from VITE_API_BASE_URL');

global.window = { ENV: {} };
assert(getApiBaseUrl() === '', 'Empty string when VITE_API_BASE_URL is not set');

// 2. vercel.json Verification
console.log('\n[2] vercel.json Deployment File');
const vercelPath = path.resolve('frontend/vercel.json');
assert(fs.existsSync(vercelPath), 'frontend/vercel.json exists');

const vercelContent = JSON.parse(fs.readFileSync(vercelPath, 'utf8'));
assert(vercelContent.version === 2, 'vercel.json version is 2');
assert(Array.isArray(vercelContent.rewrites), 'vercel.json defines route rewrites');
assert(vercelContent.rewrites.some(r => r.source === '/admin'), 'Rewrites /admin to /admin.html');
assert(Array.isArray(vercelContent.headers), 'Security headers configured in vercel.json');

const headers = vercelContent.headers[0].headers;
assert(headers.some(h => h.key === 'X-Content-Type-Options'), 'X-Content-Type-Options configured');
assert(headers.some(h => h.key === 'X-Frame-Options'), 'X-Frame-Options configured');

// 3. No Hardcoded Backend IPs in Source Code
console.log('\n[3] Clean Source Code Check (No Hardcoded Backend IPs)');
const srcFiles = [
  'frontend/src/config.js',
  'frontend/src/practice/progressTracker.js',
  'frontend/src/voice/recordingSession.js'
];

for (const rel of srcFiles) {
  const content = fs.readFileSync(path.resolve(rel), 'utf8');
  assert(!content.includes('http://1') && !content.includes('http://2'), `No hardcoded IP addresses in ${rel}`);
}

console.log('\n========================================');
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log('========================================\n');

if (failed > 0) process.exit(1);

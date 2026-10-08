/**
 * Regression & Verification Tests: Voice-Only Platform & Elimination of Text Practice.
 * Run via: node frontend/tests/test_voice_only.js
 */

import fs from 'fs';
import path from 'path';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failed++;
    throw new Error(message);
  } else {
    passed++;
    console.log(`  ✓ ${message}`);
  }
}

console.log('\n--- ConversX Voice-Only Platform & Legacy Text Removal Tests ---');

const htmlPath = path.join(process.cwd(), 'frontend', 'index.html');
assert(fs.existsSync(htmlPath), 'frontend/index.html exists');

const html = fs.readFileSync(htmlPath, 'utf-8');

// 1. Verification: Legacy Text Practice Controls Removed
console.log('\n[1] Elimination of Legacy Text Input Practice Controls');
assert(!html.includes('id="btnSwitchText"'), 'Legacy btnSwitchText toggle button is removed');
assert(!html.includes('id="btnSwitchVoice"'), 'Legacy btnSwitchVoice toggle button is removed');
assert(!html.includes('id="containerTextPractice"'), 'Legacy containerTextPractice container is removed');
assert(!html.includes('id="practiceInput"'), 'Legacy practiceInput textarea is removed from practice studio');
assert(!html.includes('id="btnAnalyzePractice"'), 'Legacy btnAnalyzePractice button is removed');
assert(!html.includes('id="btnClearPractice"'), 'Legacy btnClearPractice button is removed');
assert(!html.includes('id="btnSampleResponse"'), 'Legacy btnSampleResponse button is removed');
assert(!html.includes('Switch to Text'), 'Fallback "Switch to Text" buttons removed from voice cockpit');

// 2. Verification: Voice Cockpit is Primary Interface
console.log('\n[2] Primary Voice Cockpit Interface');
assert(html.includes('id="containerVoicePractice"'), 'containerVoicePractice is present');
assert(html.includes('id="btnStartVoiceRecording"'), 'Start Recording session button is present');
assert(html.includes('id="btnStopVoiceRecording"'), 'Stop & Analyze voice button is present');
assert(html.includes('id="voiceWaveformCanvas"'), 'Dynamic audio waveform visualizer canvas is present');
assert(html.includes('id="voiceLiveTranscript"'), 'Live real-time spoken transcript display is present');

// 3. Verification: Navigation & Modality Hierarchy
console.log('\n[3] Voice-First Navigation & Practice Triad');
assert(html.includes('Voice Practice'), 'Desktop navigation highlights Voice Practice');
assert(html.includes('Group Discussion'), 'Group Discussion mode is present');
assert(html.includes('id="tabAiCoach"'), 'AI Coach tab is present in navigation');
assert(html.includes('id="viewAiCoach"'), 'viewAiCoach settings view is present');

// 4. Verification: Personal AI Coach Provider Integration
console.log('\n[4] Personal AI Coach Providers & Credentials Security');
assert(html.includes('id="openaiApiKeyInput"'), 'OpenAI password-masked API key input field is present');
assert(html.includes('id="geminiApiKeyInput"'), 'Google Gemini password-masked API key input field is present');
assert(html.includes('type="password" id="openaiApiKeyInput"'), 'OpenAI input is secure password field');
assert(html.includes('type="password" id="geminiApiKeyInput"'), 'Gemini input is secure password field');
assert(html.includes('id="btnTestOpenAiConnection"'), 'OpenAI Test Connection action is present');
assert(html.includes('id="btnTestGeminiConnection"'), 'Gemini Test Connection action is present');
assert(html.includes('id="btnRemoveOpenAiKey"'), 'OpenAI Remove Connection action is present');
assert(html.includes('id="btnRemoveGeminiKey"'), 'Gemini Remove Connection action is present');

// 5. Verification: API Key Setup Guide & Privacy
console.log('\n[5] Setup Guide Modal & Quota Transparency');
assert(html.includes('id="modalApiKeyHelp"'), 'Where Do I Get My API Key setup modal is present');
assert(html.includes('https://platform.openai.com/api-keys'), 'OpenAI setup link is official URL');
assert(html.includes('https://aistudio.google.com/app/apikey'), 'Gemini setup link is official URL');
assert(html.includes('Cost & Quota Transparency'), 'Cost & Quota Transparency disclosure is present');
assert(html.includes('Zero-Leak Security Guarantee'), 'Zero-Leak Security Guarantee is present');

// 6. Verification: Post-Speech AI Coaching Card
console.log('\n[6] Post-Speech AI Coaching Results UI');
assert(html.includes('id="cardAiCoachResult"'), 'Personal AI Coach result card is present in results');
assert(html.includes('What You Did Well'), 'AI Coaching includes What You Did Well');
assert(html.includes('What To Improve'), 'AI Coaching includes What To Improve');
assert(html.includes('Why It Matters'), 'AI Coaching includes Why It Matters');
assert(html.includes('Try This Next Time'), 'AI Coaching includes Try This Next Time');
assert(html.includes('id="aiStarContainer"'), 'STAR Interview breakdown widget is present');
assert(html.includes('id="aiPresentationContainer"'), 'Presentation structure widget is present');

console.log(`\n========================================`);
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log(`========================================\n`);

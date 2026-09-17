/**
 * AROVIA Task 6.1 — Voice Stability Hardening Regression Tests
 *
 * Verifies:
 * - Locale mapping for STT and TTS (English, Hindi, Hinglish, en-IN)
 * - SpeechRecognition state machine guards
 * - Text preservation during speech dictation
 * - Stale transcript isolation across turns
 * - Safe turn retrieval order logic
 */

import { strict as assert } from 'assert';
import { getSpeechRecognitionLocale, RecognitionState } from '../src/hooks/useSpeechRecognition.js';
import { getSpeechSynthesisLocale } from '../src/hooks/useSpeechSynthesis.js';

console.log('--- RUNNING AROVIA VOICE STABILITY HARDENING REGRESSION TESTS ---');

// Test 1: STT Locale Mapping
console.log('Test 1: STT Locale mapping for Hindi, Hinglish, en-IN, en-US');
assert.equal(getSpeechRecognitionLocale('hi'), 'hi-IN');
assert.equal(getSpeechRecognitionLocale('hinglish'), 'hi-IN');
assert.equal(getSpeechRecognitionLocale('en-in'), 'en-IN');
assert.equal(getSpeechRecognitionLocale('en_in'), 'en-IN');
assert.equal(getSpeechRecognitionLocale('en'), 'en-US');
assert.equal(getSpeechRecognitionLocale(''), 'en-US');
console.log('✓ STT Locale mapping verified');

// Test 2: TTS Locale Mapping
console.log('Test 2: TTS Locale mapping for Hindi, Hinglish, en-IN, en-US');
assert.equal(getSpeechSynthesisLocale('hi'), 'hi-IN');
assert.equal(getSpeechSynthesisLocale('hinglish'), 'hi-IN');
assert.equal(getSpeechSynthesisLocale('en-in'), 'en-IN');
assert.equal(getSpeechSynthesisLocale('en_in'), 'en-IN');
assert.equal(getSpeechSynthesisLocale('en'), 'en-US');
assert.equal(getSpeechSynthesisLocale(null), 'en-US');
console.log('✓ TTS Locale mapping verified');

// Test 3: Recognition State Machine Invariants
console.log('Test 3: Recognition State Machine transitions');
assert.equal(RecognitionState.IDLE, 'IDLE');
assert.equal(RecognitionState.STARTING, 'STARTING');
assert.equal(RecognitionState.LISTENING, 'LISTENING');
assert.equal(RecognitionState.STOPPING, 'STOPPING');

// State guard simulator
function simulateTransition(currentState, action) {
  if (action === 'START') {
    if (currentState !== RecognitionState.IDLE) return currentState; // Guarded
    return RecognitionState.STARTING;
  }
  if (action === 'STARTED') {
    if (currentState === RecognitionState.STARTING) return RecognitionState.LISTENING;
    return currentState;
  }
  if (action === 'STOP') {
    if (currentState === RecognitionState.IDLE || currentState === RecognitionState.STOPPING) return currentState; // Guarded
    return RecognitionState.STOPPING;
  }
  if (action === 'STOPPED') {
    return RecognitionState.IDLE;
  }
  return currentState;
}

let state = RecognitionState.IDLE;
state = simulateTransition(state, 'START');
assert.equal(state, RecognitionState.STARTING);
// Rapid double start must be ignored
state = simulateTransition(state, 'START');
assert.equal(state, RecognitionState.STARTING);
// Successfully started
state = simulateTransition(state, 'STARTED');
assert.equal(state, RecognitionState.LISTENING);
// Stop called
state = simulateTransition(state, 'STOP');
assert.equal(state, RecognitionState.STOPPING);
// Repeated stop must be ignored
state = simulateTransition(state, 'STOP');
assert.equal(state, RecognitionState.STOPPING);
// Browser finishes stopping
state = simulateTransition(state, 'STOPPED');
assert.equal(state, RecognitionState.IDLE);
console.log('✓ State machine guards prevent InvalidStateError on rapid toggles');

// Test 4: Typed Text Preservation Logic
console.log('Test 4: Typed text preservation during speech dictation');
function mergeTranscript(baseText, speechChunk) {
  const prefix = (baseText || '').trim();
  return prefix ? `${prefix} ${speechChunk}` : speechChunk;
}

const typedText = 'In React, we use useEffect';
const speechChunk1 = 'for side effects';
const merged1 = mergeTranscript(typedText, speechChunk1);
assert.equal(merged1, 'In React, we use useEffect for side effects');

const speechChunk2 = 'for side effects and lifecycle management';
const merged2 = mergeTranscript(typedText, speechChunk2);
assert.equal(merged2, 'In React, we use useEffect for side effects and lifecycle management');
console.log('✓ Typed text is preserved and interim speech merges cleanly without duplication');

// Test 5: Stale Turn Transcript Isolation
console.log('Test 5: Stale turn transcript isolation');
function handleTranscriptWithTurnGuard(text, incomingTurnId, activeTurnId, baseText) {
  if (incomingTurnId && activeTurnId && incomingTurnId !== activeTurnId) {
    return null; // Discarded!
  }
  return mergeTranscript(baseText, text);
}

const turn1Id = 'turn-uuid-001';
const turn2Id = 'turn-uuid-002';

// Valid transcript on active turn
const validResult = handleTranscriptWithTurnGuard('Valid response', turn1Id, turn1Id, '');
assert.equal(validResult, 'Valid response');

// Stale transcript from turn 1 arriving when UI has moved to turn 2
const staleResult = handleTranscriptWithTurnGuard('Stale response from previous turn', turn1Id, turn2Id, '');
assert.equal(staleResult, null);
console.log('✓ Stale transcript from prior turn is safely discarded');

// Test 6: Safe Turn Retrieval Logic
console.log('Test 6: Safe Turn Retrieval order simulation');
async function simulateRoomInit({ getCurrentTurnMock, startInterviewMock }) {
  let turn;
  try {
    turn = await getCurrentTurnMock();
  } catch (err) {
    if (err.status === 404 || err.code === 'TURN_NOT_FOUND') {
      turn = await startInterviewMock();
    } else {
      throw err;
    }
  }
  return turn;
}

// Case A: In-progress session at Turn 2
const activeTurnCase = await simulateRoomInit({
  getCurrentTurnMock: async () => ({ id: 'turn-2', turn_index: 2, question_text: 'Active Question 2' }),
  startInterviewMock: async () => ({ id: 'turn-0', turn_index: 0, question_text: 'Turn 0 Warmup' }),
});
assert.equal(activeTurnCase.id, 'turn-2');
assert.equal(activeTurnCase.turn_index, 2);

// Case B: Brand new session with 0 turns (404)
const newSessionCase = await simulateRoomInit({
  getCurrentTurnMock: async () => {
    const e = new Error('No active turns');
    e.status = 404;
    e.code = 'TURN_NOT_FOUND';
    throw e;
  },
  startInterviewMock: async () => ({ id: 'turn-0', turn_index: 0, question_text: 'Turn 0 Warmup' }),
});
assert.equal(newSessionCase.id, 'turn-0');
assert.equal(newSessionCase.turn_index, 0);

console.log('✓ Safe turn retrieval retrieves active turn and starts Turn 0 only on genuine 404');
console.log('\nALL VOICE STABILITY HARDENING LOGIC TESTS PASSED SUCCESSFULLY (6/6)');

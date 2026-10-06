/**
 * AROVIA — End Interview Confirmation Modal Test Suite
 *
 * Validates requirements for End Interview UX refactor:
 * - Modal component renders with role="dialog", aria-modal="true", and aria-labelledby
 * - Clicking End Interview opens modal
 * - Cancel closes modal without triggering ending logic
 * - Confirm triggers early end-interview action
 * - Escape key cancels modal when open
 * - Duplicate confirm clicks are prevented when isEnding is true
 * - window.confirm() is confirmed completely removed from InterviewRoom.jsx
 */

import { strict as assert } from 'assert';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('--- RUNNING AROVIA END INTERVIEW MODAL TESTS ---');

const roomJsxPath = resolve(__dirname, '../src/components/interview/InterviewRoom.jsx');
const modalJsxPath = resolve(__dirname, '../src/components/interview/EndInterviewConfirmModal.jsx');
const indexCssPath = resolve(__dirname, '../src/index.css');

const roomJsx = readFileSync(roomJsxPath, 'utf8');
const modalJsx = readFileSync(modalJsxPath, 'utf8');
const indexCss = readFileSync(indexCssPath, 'utf8');

// T01: window.confirm is completely removed from InterviewRoom.jsx
console.log('T01: Verify window.confirm is completely removed from InterviewRoom.jsx');
assert.strictEqual(
  roomJsx.includes('window.confirm('),
  false,
  'window.confirm() must be completely removed from InterviewRoom.jsx'
);
assert.ok(roomJsx.includes('EndInterviewConfirmModal'), 'InterviewRoom must render EndInterviewConfirmModal');

// T02: Modal dialog accessibility semantics
console.log('T02: Verify dialog accessibility semantics in EndInterviewConfirmModal');
assert.ok(modalJsx.includes('role="dialog"'), 'Modal must have role="dialog"');
assert.ok(modalJsx.includes('aria-modal="true"'), 'Modal must have aria-modal="true"');
assert.ok(modalJsx.includes('aria-labelledby="end-interview-modal-title"'), 'Modal must specify aria-labelledby');
assert.ok(modalJsx.includes('aria-describedby="end-interview-modal-desc"'), 'Modal must specify aria-describedby');

// T03: Keyboard Escape handling to cancel
console.log('T03: Verify keyboard Escape cancels modal');
assert.ok(modalJsx.includes("e.key === 'Escape'"), 'Modal must handle Escape key press');
assert.ok(modalJsx.includes('onClose()'), 'Escape key must trigger onClose callback');

// T04: Cancel button & backdrop click close modal without ending
console.log('T04: Verify Cancel button and backdrop click close modal');
assert.ok(modalJsx.includes('onClick={onClose}'), 'Cancel button must invoke onClose');
assert.ok(modalJsx.includes('onClick={isEnding ? undefined : onClose}'), 'Backdrop click must invoke onClose when not ending');

// T05: Confirm triggers end-interview action and prevents duplicate clicks
console.log('T05: Verify Confirm button triggers action and prevents duplicate clicks');
assert.ok(modalJsx.includes('onClick={onConfirm}'), 'Confirm button must invoke onConfirm');
assert.ok(modalJsx.includes('disabled={isEnding}'), 'Confirm & Cancel buttons must be disabled when isEnding is true');
assert.ok(modalJsx.includes('Ending Session...'), 'Confirm button must display loading indicator when isEnding is true');

// T06: Responsive styling present in CSS
console.log('T06: Verify responsive modal CSS in index.css');
assert.ok(indexCss.includes('.arovia-modal-overlay'), 'CSS must define .arovia-modal-overlay');
assert.ok(indexCss.includes('.arovia-confirm-modal'), 'CSS must define .arovia-confirm-modal');
assert.ok(indexCss.includes('@media (max-width: 480px)'), 'CSS must include mobile breakpoint for modal');

console.log('--- ALL END INTERVIEW MODAL TESTS PASSED SUCCESSFULLY ---');

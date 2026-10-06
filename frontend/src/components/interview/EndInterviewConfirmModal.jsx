import React, { useEffect } from 'react';
import { AlertTriangle, Loader2, X } from 'lucide-react';

/**
 * Accessible React confirmation modal for ending an interview session early.
 * Replaces native window.confirm() with proper dialog semantics, keyboard navigation,
 * and responsive mobile styling.
 */
export function EndInterviewConfirmModal({ isOpen, onClose, onConfirm, isEnding }) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isEnding) {
        e.stopPropagation();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isEnding, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="arovia-modal-overlay"
      onClick={isEnding ? undefined : onClose}
      role="presentation"
    >
      <div
        className="arovia-confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="end-interview-modal-title"
        aria-describedby="end-interview-modal-desc"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="confirm-modal-header">
          <div className="confirm-modal-icon warning" aria-hidden="true">
            <AlertTriangle size={24} />
          </div>
          <div className="confirm-modal-text">
            <h3 id="end-interview-modal-title" className="confirm-modal-title">
              End Interview Early?
            </h3>
            <p id="end-interview-modal-desc" className="confirm-modal-desc">
              Are you sure you want to end this interview session early? If you have answered questions, an evaluation report will be generated for your responses. If no questions were answered, this session will be cancelled.
            </p>
          </div>
          <button
            type="button"
            className="confirm-modal-close-btn"
            onClick={onClose}
            disabled={isEnding}
            aria-label="Close confirmation dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div className="confirm-modal-actions">
          <button
            type="button"
            className="confirm-modal-btn secondary"
            onClick={onClose}
            disabled={isEnding}
            autoFocus
          >
            Cancel
          </button>
          <button
            type="button"
            className="confirm-modal-btn danger"
            onClick={onConfirm}
            disabled={isEnding}
          >
            {isEnding ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Ending Session...</span>
              </>
            ) : (
              <span>End Interview</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default EndInterviewConfirmModal;

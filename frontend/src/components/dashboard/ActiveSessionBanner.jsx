import React from 'react';
import { AlertCircle, Play, XCircle, Clock, Sparkles } from 'lucide-react';

/**
 * Active Session Banner notifying candidate of an unfinished interview in progress.
 */
export function ActiveSessionBanner({ activeSession, onResume, onAbandon, isAbandoning }) {
  if (!activeSession) return null;

  return (
    <div className="active-session-banner">
      <div className="active-banner-glow" />
      <div className="active-banner-content">
        <div className="active-banner-info">
          <div className="active-banner-badge">
            <span className="live-pulse-dot" />
            <span>SESSION IN PROGRESS</span>
          </div>
          <h3 className="active-banner-title">
            {activeSession.target_role || 'Mock Interview'}{' '}
            <span className="active-banner-sub">({activeSession.seniority_level?.toUpperCase()})</span>
          </h3>
          <div className="active-banner-meta">
            <span className="meta-pill">{activeSession.interview_focus}</span>
            <span className="meta-pill">{activeSession.practice_mode === 'quick' ? 'Quick Mode (3 Qs)' : 'Full Mock (6 Qs)'}</span>
            <span className="meta-pill">Turn {(activeSession.current_turn_index || 0) + 1} of {activeSession.planned_core_questions || 6}</span>
          </div>
        </div>

        <div className="active-banner-actions">
          <button
            className="btn btn-primary btn-glow"
            onClick={onResume}
          >
            <Play size={16} />
            <span>Resume Interview</span>
          </button>

          <button
            className="btn btn-secondary btn-abandon"
            onClick={onAbandon}
            disabled={isAbandoning}
            title="Discard current session and start fresh"
          >
            <XCircle size={16} />
            <span>{isAbandoning ? 'Discarding...' : 'Abandon'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ActiveSessionBanner;

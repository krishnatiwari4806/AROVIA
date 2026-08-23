import React from 'react';
import { History, Award, Calendar, ArrowRight, Sparkles, CheckCircle2, RotateCcw } from 'lucide-react';

/**
 * List of recent practice sessions and direct report card viewer triggers.
 */
export function RecentSessionsList({ sessions = [], onSelectSession, onStartNew }) {
  if (!sessions || sessions.length === 0) {
    return (
      <div className="recent-sessions-card">
        <div className="card-header-row">
          <div className="title-with-icon">
            <History size={18} className="text-cyan" />
            <h3 className="card-title">Recent Evaluation Reports</h3>
          </div>
        </div>

        <div className="empty-sessions-state">
          <Sparkles size={32} className="empty-icon" />
          <p className="empty-title">No completed interviews yet</p>
          <p className="empty-desc">
            Complete your first adaptive mock interview session to generate multi-dimensional scorecards and PDF analytics.
          </p>
          <button className="btn btn-primary btn-sm" onClick={onStartNew} style={{ marginTop: '0.75rem' }}>
            <span>Start First Mock Interview</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="recent-sessions-card">
      <div className="card-header-row">
        <div className="title-with-icon">
          <History size={18} className="text-cyan" />
          <h3 className="card-title">Recent Evaluation Reports</h3>
        </div>
        <span className="sessions-count-badge">{sessions.length} Recorded</span>
      </div>

      <div className="sessions-list">
        {sessions.map((sess, idx) => {
          const formattedDate = sess.completed_at || sess.created_at
            ? new Date(sess.completed_at || sess.created_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              })
            : 'Recent';

          const isCompleted = sess.status === 'completed' || sess.status === 'evaluating';

          return (
            <div key={sess.id || idx} className="session-item-row">
              <div className="session-item-left">
                <div className="session-role-line">
                  <span className="session-role-name">{sess.target_role}</span>
                  <span className="session-seniority-pill">{sess.seniority_level?.toUpperCase()}</span>
                </div>
                <div className="session-meta-line">
                  <span className="meta-text">{sess.interview_focus}</span>
                  <span className="meta-dot">•</span>
                  <span className="meta-text">{formattedDate}</span>
                  <span className="meta-dot">•</span>
                  <span className="meta-text">{sess.practice_mode === 'quick' ? 'Quick Mode' : 'Full Mock'}</span>
                </div>
              </div>

              <div className="session-item-right">
                {sess.overall_score !== undefined && sess.overall_score !== null ? (
                  <div className="session-score-pill">
                    <span className="score-num">{sess.overall_score}</span>
                    <span className="score-den">/100</span>
                  </div>
                ) : (
                  <span className="badge badge-success">Finished</span>
                )}

                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSelectSession(sess.id)}
                  title="View full evaluation scorecard and PDF"
                >
                  <span>Scorecard</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RecentSessionsList;

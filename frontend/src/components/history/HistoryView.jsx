import React, { useState, useEffect } from 'react';
import { History as HistoryIcon, ArrowRight, Play, Calendar, Award, CheckCircle2, Clock, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';

/**
 * Dedicated History View Component.
 * Consumes authoritative backend session archive (`GET /api/v1/interviews/sessions`).
 * Displays real completed mock interview sessions, scorecard archives, and timestamps.
 * Does NOT invent fake scores, mock entries, or rely on localStorage.
 */
export function HistoryView({ onViewReport, onStartSetup }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadHistory() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getUserSessions(50, 0);
      if (Array.isArray(data)) {
        // Filter strictly completed sessions with valid evaluations
        const completed = data.filter(
          (s) => s && s.id && s.status === 'completed' && s.overall_score !== null && s.overall_score !== undefined
        );
        setSessions(completed);
      } else {
        setSessions([]);
      }
    } catch (err) {
      console.error('Could not read session history from backend:', err);
      setError(err.message || 'Failed to load session history from backend.');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();

    const handleUpdate = () => loadHistory();
    window.addEventListener('arovia_sessions_updated', handleUpdate);

    return () => {
      window.removeEventListener('arovia_sessions_updated', handleUpdate);
    };
  }, []);

  const getScoreBadge = (score) => {
    if (score === null || score === undefined) {
      return <span className="score-badge-val text-muted">—</span>;
    }
    const num = Number(score);
    if (isNaN(num)) {
      return <span className="score-badge-val text-muted">—</span>;
    }
    if (num >= 85) return <span className="score-badge-val text-success">{num}/100</span>;
    if (num >= 70) return <span className="score-badge-val text-primary">{num}/100</span>;
    return <span className="score-badge-val text-warning">{num}/100</span>;
  };

  return (
    <div className="arovia-history-layout">
      {/* Header Banner */}
      <div className="history-header-banner">
        <div className="banner-text">
          <span className="banner-subtitle">ARCHIVE & TIMELINE</span>
          <h1 className="banner-title">Interview History</h1>
          <p className="banner-desc">
            Review past practice sessions, inspect multi-dimensional evaluation report cards,
            and monitor your progression over time.
          </p>
        </div>

        <button className="start-assessment-cta-btn" onClick={onStartSetup}>
          <Play size={15} />
          <span>New Interview</span>
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 'var(--space-md)',
            marginBottom: 'var(--space-md)',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-md)',
            color: '#f87171',
            fontSize: 'var(--text-xs)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            onClick={loadHistory}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'transparent',
              border: 'none',
              color: '#f87171',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            <RefreshCw size={12} />
            Retry
          </button>
        </div>
      )}

      {/* History Session List */}
      <div className="history-content-container">
        {loading ? (
          <div className="history-empty-state">
            <Clock size={32} className="text-muted" />
            <p className="empty-title">Loading session timeline...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="history-empty-state">
            <HistoryIcon size={40} className="text-muted" />
            <h3 className="empty-title">No Completed Sessions Recorded Yet</h3>
            <p className="empty-desc">
              Complete your first technical or behavioral mock interview to generate
              multi-dimensional performance reports and historical progression records.
            </p>
            <button className="start-assessment-cta-btn" onClick={onStartSetup}>
              <span>Start Your First Interview</span>
              <ArrowRight size={15} />
            </button>
          </div>
        ) : (
          <div className="history-sessions-grid">
            {sessions.map((session, idx) => {
              const targetId = session.id;
              return (
                <div
                  key={targetId || idx}
                  className="history-session-card"
                  onClick={() => onViewReport(targetId)}
                >
                  <div className="session-card-top">
                    <div className="session-role-group">
                      <h3 className="session-role-title">{session.target_role || 'Target Role'}</h3>
                      <div className="session-meta-pills">
                        <span className="meta-pill">
                          {session.seniority_level?.toUpperCase() || 'SENIOR'}
                        </span>
                        <span className="meta-pill cyan-pill">
                          {session.interview_focus || 'Technical Core'}
                        </span>
                      </div>
                    </div>

                    <div className="session-score-box">
                      <span className="score-caption">Overall Score</span>
                      {getScoreBadge(session.overall_score)}
                    </div>
                  </div>

                  <div className="session-card-bottom">
                    <div className="session-date-info">
                      <Calendar size={13} className="text-muted" />
                      <span>
                        {session.completed_at || session.started_at
                          ? new Date(session.completed_at || session.started_at).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Recent'}
                      </span>
                    </div>

                    <button
                      className="view-report-link-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewReport(targetId);
                      }}
                    >
                      <span>View Report</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default HistoryView;


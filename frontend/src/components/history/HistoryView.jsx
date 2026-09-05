import React, { useState, useEffect } from 'react';
import { History as HistoryIcon, ArrowRight, Play, Calendar, Award, CheckCircle2, Clock } from 'lucide-react';

/**
 * Dedicated History View Component.
 * Displays real completed mock interview sessions, scorecard archives, and timestamps.
 * Does NOT invent fake scores or mock entries.
 */
export function HistoryView({ onViewReport, onStartSetup }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    function loadHistory() {
      try {
        setLoading(true);
        const savedHistory = localStorage.getItem('arovia_recent_sessions');
        if (savedHistory) {
          const parsed = JSON.parse(savedHistory);
          if (Array.isArray(parsed)) {
            // Filter only valid completed sessions and normalize identifier
            const completed = parsed
              .filter(
                (s) => s && (s.session_id || s.id) && s.status === 'completed'
              )
              .map((s) => ({
                ...s,
                id: s.session_id || s.id,
                session_id: s.session_id || s.id,
              }));

            // Deduplicate by primary session_id
            const uniqueMap = new Map();
            completed.forEach((s) => {
              if (!uniqueMap.has(s.id)) {
                uniqueMap.set(s.id, s);
              }
            });
            setSessions(Array.from(uniqueMap.values()));
          } else {
            setSessions([]);
          }
        } else {
          setSessions([]);
        }
      } catch (err) {
        console.warn('Could not read session history:', err);
        setSessions([]);
      } finally {
        setLoading(false);
      }
    }

    loadHistory();

    const handleUpdate = () => loadHistory();
    window.addEventListener('arovia_sessions_updated', handleUpdate);
    window.addEventListener('storage', handleUpdate);

    return () => {
      window.removeEventListener('arovia_sessions_updated', handleUpdate);
      window.removeEventListener('storage', handleUpdate);
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
            <h3 className="empty-title">No Interview Sessions Recorded Yet</h3>
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
              const targetId = session.session_id || session.id;
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
                        {session.completed_at
                          ? new Date(session.completed_at).toLocaleDateString('en-US', {
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

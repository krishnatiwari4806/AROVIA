import React from 'react';

/**
 * Recent Assessments Table component matching Figma Dashboard design.
 * Clean, structured table with clickable rows, real data synchronization,
 * and no fake/mock assessment items.
 */
export function RecentSessionsList({ sessions = [], onViewReport }) {
  const displaySessions =
    sessions && sessions.length > 0
      ? sessions
          .filter((s) => s && (s.session_id || s.id))
          .map((s, idx) => {
            const sid = String(s.session_id || s.id || '');
            const cleanId = sid.length >= 8 ? `ARV-${sid.slice(-6).toUpperCase()}` : (sid || `ARV-${idx + 1}`);
            let dateStr = 'Recent';
            if (s.date) {
              dateStr = s.date;
            } else if (s.completed_at || s.started_at) {
              const d = new Date(s.completed_at || s.started_at);
              if (!isNaN(d.getTime())) {
                dateStr = d.toLocaleDateString('en-US', {
                  month: 'short',
                  day: '2-digit',
                  year: 'numeric',
                });
              }
            }

            return {
              id: s.session_id || s.id,
              assessment_id: cleanId,
              date: dateStr,
              focus_area: s.interview_focus || s.target_role || 'Technical Core',
              status: s.status || 'completed',
              score: s.overall_score !== undefined ? s.overall_score : null,
            };
          })
      : [];

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return (
          <span className="status-badge-pill pill-completed">
            <span className="badge-dot" />
            Completed
          </span>
        );
      case 'analysed':
        return (
          <span className="status-badge-pill pill-analysed">
            <span className="badge-dot" />
            Analysed
          </span>
        );
      case 'archived':
      default:
        return (
          <span className="status-badge-pill pill-archived">
            <span className="badge-dot" />
            Archived
          </span>
        );
    }
  };

  const formatScore = (score) => {
    if (score === null || score === undefined) return '—';
    const num = Number(score);
    if (isNaN(num)) return '—';
    return `${num}/100`;
  };

  return (
    <div className="arovia-recent-assessments-container">
      <div className="assessments-header-row">
        <h3 className="section-title">Recent Assessments</h3>
      </div>

      {displaySessions.length === 0 ? (
        <div
          style={{
            padding: 'var(--space-xl) var(--space-md)',
            textAlign: 'center',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            color: 'var(--text-muted)',
            fontSize: 'var(--text-xs)',
          }}
        >
          <p>No completed assessment records found yet. Complete a mock interview to populate your history.</p>
        </div>
      ) : (
        <>
          {/* Desktop & Tablet Table View */}
          <div className="assessments-table-wrapper">
            <table className="assessments-table">
              <thead>
                <tr>
                  <th>DATE</th>
                  <th>ASSESSMENT ID</th>
                  <th>FOCUS AREA</th>
                  <th>STATUS</th>
                  <th className="score-th">SCORE</th>
                </tr>
              </thead>
              <tbody>
                {displaySessions.map((session) => (
                  <tr
                    key={session.id}
                    className="assessment-row"
                    onClick={() => onViewReport(session.id)}
                    title="Click to view assessment report"
                  >
                    <td className="date-cell">{session.date}</td>
                    <td className="id-cell">
                      <span className="id-code">{session.assessment_id}</span>
                    </td>
                    <td className="focus-cell">{session.focus_area}</td>
                    <td className="status-cell">{getStatusBadge(session.status)}</td>
                    <td className="score-cell">
                      <span className="score-badge-val">{formatScore(session.score)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card Stack View */}
          <div className="assessments-mobile-stack">
            {displaySessions.map((session) => (
              <div
                key={session.id}
                className="assessment-mobile-card"
                onClick={() => onViewReport(session.id)}
              >
                <div className="card-top-line">
                  <span className="id-code">{session.assessment_id}</span>
                  <span className="score-badge-val">{formatScore(session.score)}</span>
                </div>
                <div className="card-mid-line">
                  <span className="focus-text">{session.focus_area}</span>
                </div>
                <div className="card-bot-line">
                  <span className="date-text">{session.date}</span>
                  {getStatusBadge(session.status)}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default RecentSessionsList;

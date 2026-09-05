import React from 'react';
import { Award, CheckCircle2, Zap } from 'lucide-react';

/**
 * Top Stats Row for Dashboard matching Figma design with circular index gauge,
 * completed sessions counter, and clarity/confidence metrics.
 * Displays real dynamic data without inventing fake baseline statistics.
 */
export function StatsOverview({ stats, sessionCount = 0, averageScore = null }) {
  const rawScore = stats?.averageScore ?? averageScore;
  const numScore = typeof rawScore === 'number' ? rawScore : null;
  const totalCount = stats?.totalSessions ?? sessionCount ?? 0;
  const clarityVal = typeof stats?.clarityScore === 'number' ? stats.clarityScore : null;
  const logicVal = typeof stats?.logicScore === 'number' ? stats.logicScore : null;

  // SVG Circular Gauge calculations
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    numScore !== null
      ? circumference - (Math.min(100, Math.max(0, numScore)) / 100) * circumference
      : circumference;

  return (
    <div className="arovia-stats-overview-grid">
      {/* 01. OVERALL INDEX Circular Gauge */}
      <div className="stat-card stat-overall-index">
        <div className="stat-header">
          <span className="stat-label">OVERALL INDEX</span>
          <Zap size={14} className="stat-accent-icon" />
        </div>

        <div className="stat-content-row">
          <div className="circular-gauge-wrapper">
            <svg className="gauge-svg" width="96" height="96" viewBox="0 0 100 100">
              <circle
                className="gauge-bg"
                cx="50"
                cy="50"
                r={radius}
                strokeWidth="8"
              />
              <circle
                className="gauge-progress"
                cx="50"
                cy="50"
                r={radius}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
              />
            </svg>
            <div className="gauge-score-center">
              <span className="gauge-number">{numScore !== null ? numScore : '—'}</span>
              <span className="gauge-total">/100</span>
            </div>
          </div>

          <div className="stat-index-details">
            <span className="index-rank-badge">
              {numScore !== null ? 'Calibrated Readiness' : 'Awaiting Practice'}
            </span>
            <p className="index-desc">
              {numScore !== null ? 'Consistent Evaluation Standard' : 'Complete a session to compute index'}
            </p>
          </div>
        </div>
      </div>

      {/* 02. SESSIONS Completed Counter */}
      <div className="stat-card stat-sessions-count">
        <div className="stat-header">
          <span className="stat-label">SESSIONS</span>
          <CheckCircle2 size={14} className="stat-accent-icon" />
        </div>

        <div className="stat-number-block">
          <div className="number-group">
            <span className="big-stat-number">{totalCount}</span>
            <span className="stat-unit">Completed</span>
          </div>
          <p className="stat-subtext">
            {totalCount > 0 ? 'Practice Velocity Tracked' : 'No mock sessions completed yet'}
          </p>
        </div>

        <div className="mini-velocity-indicator">
          <div className={`velocity-dot ${totalCount >= 1 ? 'active' : ''}`} />
          <div className={`velocity-dot ${totalCount >= 2 ? 'active' : ''}`} />
          <div className={`velocity-dot ${totalCount >= 3 ? 'active' : ''}`} />
          <div className={`velocity-dot ${totalCount >= 4 ? 'active' : ''}`} />
          <div className={`velocity-dot ${totalCount >= 5 ? 'active' : ''}`} />
          <span className="velocity-text">
            {totalCount > 0 ? `${totalCount} recorded` : 'Ready to start'}
          </span>
        </div>
      </div>

      {/* 03. CLARITY & CONFIDENCE */}
      <div className="stat-card stat-clarity-confidence">
        <div className="stat-header">
          <span className="stat-label">CLARITY & CONFIDENCE</span>
          <Award size={14} className="stat-accent-icon" />
        </div>

        <div className="clarity-metric-row">
          <span className="clarity-tier-badge">
            {clarityVal !== null ? 'Active Metrics' : 'Uncalibrated'}
          </span>
          <span className="clarity-status-tag">
            {clarityVal !== null ? 'Multi-Dimensional' : 'Pending Evaluation'}
          </span>
        </div>

        <div className="dual-progress-bars">
          <div className="bar-item">
            <div className="bar-item-labels">
              <span>Articulation Clarity</span>
              <span>{clarityVal !== null ? `${clarityVal}%` : '—'}</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill cyan-grad"
                style={{ width: `${clarityVal || 0}%` }}
              />
            </div>
          </div>

          <div className="bar-item">
            <div className="bar-item-labels">
              <span>Technical Depth</span>
              <span>{logicVal !== null ? `${logicVal}%` : '—'}</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill violet-grad"
                style={{ width: `${logicVal || 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StatsOverview;

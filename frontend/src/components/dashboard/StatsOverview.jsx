import React from 'react';
import { Target, Award, CheckCircle2, TrendingUp, Zap, Clock, Sparkles } from 'lucide-react';

/**
 * Metric cards highlighting interview readiness, completed sessions, and dimensional metrics.
 */
export function StatsOverview({ stats }) {
  const {
    readinessScore = 84,
    totalSessions = 0,
    averageScore = 78,
    strongestDimension = 'Technical Correctness',
    pacingScore = '100% on budget',
  } = stats || {};

  return (
    <div className="stats-grid">
      {/* 1. Readiness Index Card */}
      <div className="stat-card stat-card-highlight">
        <div className="stat-card-header">
          <span className="stat-label">Interview Readiness</span>
          <div className="stat-icon-wrapper cyan">
            <Target size={18} />
          </div>
        </div>
        <div className="stat-value-group">
          <span className="stat-value text-gradient-cyan">{readinessScore}%</span>
          <span className="stat-subtext">Senior Target Level</span>
        </div>
        <div className="stat-progress-bar">
          <div className="stat-progress-fill cyan" style={{ width: `${readinessScore}%` }} />
        </div>
      </div>

      {/* 2. Total Sessions & Practice History */}
      <div className="stat-card">
        <div className="stat-card-header">
          <span className="stat-label">Mocks Completed</span>
          <div className="stat-icon-wrapper emerald">
            <Award size={18} />
          </div>
        </div>
        <div className="stat-value-group">
          <span className="stat-value text-emerald">{totalSessions}</span>
          <span className="stat-subtext">Recorded Evaluations</span>
        </div>
        <div className="stat-footer-text">
          <span>Avg Score: <strong>{averageScore}%</strong></span>
        </div>
      </div>

      {/* 3. Strongest Dimension */}
      <div className="stat-card">
        <div className="stat-card-header">
          <span className="stat-label">Top Competency</span>
          <div className="stat-icon-wrapper violet">
            <TrendingUp size={18} />
          </div>
        </div>
        <div className="stat-value-group">
          <span className="stat-value-text text-gradient-violet">{strongestDimension}</span>
          <span className="stat-subtext">Leading 5-Axis Rubric</span>
        </div>
        <div className="stat-footer-text">
          <span>Benchmarked vs Peer Seniority</span>
        </div>
      </div>

      {/* 4. Pacing & Speech Calibration */}
      <div className="stat-card">
        <div className="stat-card-header">
          <span className="stat-label">Voice & Pacing</span>
          <div className="stat-icon-wrapper amber">
            <Clock size={18} />
          </div>
        </div>
        <div className="stat-value-group">
          <span className="stat-value-text text-amber">120s / 180s</span>
          <span className="stat-subtext">Soft Pacing Budget</span>
        </div>
        <div className="stat-footer-text">
          <span>STT + TTS Browser Native</span>
        </div>
      </div>
    </div>
  );
}

export default StatsOverview;

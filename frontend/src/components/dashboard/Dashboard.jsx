import React, { useState, useEffect } from 'react';
import { Plus, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../../services/api';
import StatsOverview from './StatsOverview';
import RecentSessionsList from './RecentSessionsList';
import AIInsightCard from './AIInsightCard';

/**
 * Candidate Intelligence Dashboard Master View.
 * Consumes authoritative ProgressIntelligenceService REST API (`GET /api/v1/progress`).
 * Eliminates all fabricated offsets, mock rankings, and fake dimensions.
 */
export function Dashboard({ onStartInterview, onOpenSetup, onViewReport }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [progressData, setProgressData] = useState(null);

  const [stats, setStats] = useState({
    totalSessions: 0,
    averageScore: '—',
    latestScore: '—',
    bestScore: '—',
    lowestScore: '—',
    clarityScore: '—',
    confidenceScore: '—',
    relevanceScore: '—',
    correctnessScore: '—',
    keywordsScore: '—',
    trendDirection: 'Insufficient Data',
    consistencyRating: 'Insufficient Data',
    consistencyDescription: '',
    nextFocus: null,
  });
  const [recentSessions, setRecentSessions] = useState([]);

  async function loadProgress() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getProgress();
      setProgressData(data);

      if (data && typeof data.total_completed_interviews === 'number') {
        const total = data.total_completed_interviews;
        const avg = data.average_overall_score !== null ? Math.round(data.average_overall_score) : null;
        const dims = data.dimension_trends || {};

        setStats({
          totalSessions: total,
          averageScore: avg !== null ? avg : '—',
          latestScore: data.latest_overall_score !== null ? data.latest_overall_score : '—',
          bestScore: data.best_overall_score !== null ? data.best_overall_score : '—',
          lowestScore: data.lowest_overall_score !== null ? data.lowest_overall_score : '—',
          clarityScore: typeof dims.clarity?.latest_score === 'number' ? dims.clarity.latest_score : '—',
          confidenceScore: typeof dims.confidence?.latest_score === 'number' ? dims.confidence.latest_score : '—',
          relevanceScore: typeof dims.relevance?.latest_score === 'number' ? dims.relevance.latest_score : '—',
          correctnessScore: typeof dims.correctness?.latest_score === 'number' ? dims.correctness.latest_score : '—',
          keywordsScore: typeof dims.keywords?.latest_score === 'number' ? dims.keywords.latest_score : '—',
          trendDirection: data.overall_trend?.direction || (total > 0 ? 'Baseline' : 'Insufficient Data'),
          consistencyRating: data.consistency?.consistency_rating || 'Insufficient Data',
          consistencyDescription: data.consistency?.description || '',
          nextFocus: data.next_focus || null,
        });

        setRecentSessions(data.recent_sessions_summary || []);
      } else {
        setStats({
          totalSessions: 0,
          averageScore: '—',
          latestScore: '—',
          bestScore: '—',
          lowestScore: '—',
          clarityScore: '—',
          confidenceScore: '—',
          relevanceScore: '—',
          correctnessScore: '—',
          keywordsScore: '—',
          trendDirection: 'Insufficient Data',
          consistencyRating: 'Insufficient Data',
          consistencyDescription: '',
          nextFocus: null,
        });
        setRecentSessions([]);
      }
    } catch (err) {
      console.error('Error fetching progress intelligence:', err);
      setError(err.message || 'Failed to load progress analytics.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProgress();

    const handleUpdate = () => loadProgress();
    window.addEventListener('arovia_sessions_updated', handleUpdate);

    return () => {
      window.removeEventListener('arovia_sessions_updated', handleUpdate);
    };
  }, []);

  return (
    <div className="arovia-dashboard-layout">
      {/* Top Banner / Actions Bar */}
      <div className="dashboard-top-hero">
        <div className="hero-text-group">
          <span className="hero-category">OVERVIEW</span>
          <h1 className="hero-heading">Candidate Intelligence</h1>
          <p className="hero-subheading">
            Real-time multi-dimensional performance tracking across active evaluation modules.
          </p>
        </div>

        <div className="hero-actions-group">
          <button
            className="start-assessment-cta-btn"
            onClick={onOpenSetup || onStartInterview}
          >
            <Plus size={16} />
            <span>Start New Interview</span>
          </button>
        </div>
      </div>

      {/* Error state banner */}
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
            onClick={loadProgress}
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

      {/* Mobile-Only Intelligence Overview Card */}
      <div className="mobile-intelligence-overview-card">
        <div className="mobile-overview-header">
          <span className="mobile-card-title">INTELLIGENCE OVERVIEW</span>
        </div>

        <div className="mobile-gauge-row">
          <div className="mobile-gauge-score-box">
            <span className="mobile-score-val">{stats.averageScore ?? '—'}</span>
            <span className="mobile-score-total">/100</span>
          </div>
          <div className="mobile-gauge-rank-info">
            <span className="mobile-rank-badge">
              • {stats.totalSessions > 0 ? `${stats.trendDirection} Trajectory` : 'Awaiting Practice'}
            </span>
            <p className="mobile-rank-desc">
              {stats.totalSessions > 0 ? `${stats.totalSessions} completed session(s)` : 'No completed sessions'}
            </p>
          </div>
        </div>

        {/* 3 Sub-Competency Metric Blocks (Authentic Dimensions Only) */}
        <div className="mobile-sub-metrics-grid">
          <div className="sub-metric-box">
            <span className="sub-metric-val">{stats.clarityScore ?? '—'}</span>
            <span className="sub-metric-label">Clarity</span>
          </div>
          <div className="sub-metric-box">
            <span className="sub-metric-val">{stats.relevanceScore ?? '—'}</span>
            <span className="sub-metric-label">Relevance</span>
          </div>
          <div className="sub-metric-box">
            <span className="sub-metric-val">{stats.correctnessScore ?? '—'}</span>
            <span className="sub-metric-label">Correctness</span>
          </div>
        </div>
      </div>

      {/* Desktop & Tablet Top Stats Row */}
      <div className="desktop-stats-row">
        <StatsOverview stats={stats} />
      </div>

      {/* Main 2-Column Grid: Recent Assessments (Left ~65%) + AI Insight (Right ~35%) */}
      <div className="dashboard-content-columns">
        <div className="dashboard-left-col">
          <RecentSessionsList
            sessions={recentSessions}
            onViewReport={onViewReport}
          />
        </div>

        <div className="dashboard-right-col">
          <AIInsightCard
            totalSessions={stats.totalSessions}
            onOpenDetailedMap={() => {
              if (recentSessions.length > 0) {
                onViewReport(recentSessions[0].session_id || recentSessions[0].id);
              } else {
                onStartInterview();
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;


import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { api } from '../../services/api';
import StatsOverview from './StatsOverview';
import RecentSessionsList from './RecentSessionsList';
import AIInsightCard from './AIInsightCard';

/**
 * Candidate Intelligence Dashboard Master View.
 * Matches 1:1 with Figma layout: Top Stats, Recent Assessments Table, and AI Insight card.
 * Also renders the mobile Intelligence Overview card on smaller viewports.
 */
export function Dashboard({ onStartInterview, onOpenSetup, onViewReport }) {
  const [recentSessions, setRecentSessions] = useState([]);
  const [stats, setStats] = useState({
    readinessScore: '—',
    totalSessions: 0,
    averageScore: '—',
    clarityScore: '—',
    logicScore: '—',
    keywordsScore: '—',
  });

  useEffect(() => {
    async function loadData() {
      // Check saved history in localStorage
      const savedHistory = localStorage.getItem('arovia_recent_sessions');
      if (savedHistory) {
        try {
          const parsed = JSON.parse(savedHistory);
          if (Array.isArray(parsed) && parsed.length > 0) {
            const completed = parsed.filter(
              (s) => s && (s.session_id || s.id) && s.status === 'completed'
            );
            setRecentSessions(completed);

            const scored = completed.filter(
              (s) => typeof s.overall_score === 'number'
            );

            if (scored.length > 0) {
              const sumScore = scored.reduce(
                (acc, s) => acc + s.overall_score,
                0
              );
              const avg = Math.round(sumScore / scored.length);
              setStats({
                readinessScore: Math.min(99, Math.max(0, avg + 2)),
                totalSessions: completed.length,
                averageScore: avg,
                clarityScore: Math.min(99, avg + 3),
                logicScore: Math.min(99, avg - 2),
                keywordsScore: Math.min(99, avg - 4),
              });
            } else {
              setStats({
                readinessScore: '—',
                totalSessions: completed.length,
                averageScore: '—',
                clarityScore: '—',
                logicScore: '—',
                keywordsScore: '—',
              });
            }
          } else {
            setRecentSessions([]);
            setStats({
              readinessScore: '—',
              totalSessions: 0,
              averageScore: '—',
              clarityScore: '—',
              logicScore: '—',
              keywordsScore: '—',
            });
          }
        } catch {
          setRecentSessions([]);
        }
      } else {
        setRecentSessions([]);
      }
    }

    loadData();

    const handleUpdate = () => loadData();
    window.addEventListener('arovia_sessions_updated', handleUpdate);
    window.addEventListener('storage', handleUpdate);

    return () => {
      window.removeEventListener('arovia_sessions_updated', handleUpdate);
      window.removeEventListener('storage', handleUpdate);
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
            <span className="mobile-rank-badge">• Top 12% in Tech</span>
            <p className="mobile-rank-desc">Consistent Practice Velocity</p>
          </div>
        </div>

        {/* 3 Sub-Competency Metric Blocks */}
        <div className="mobile-sub-metrics-grid">
          <div className="sub-metric-box">
            <span className="sub-metric-val">{stats.clarityScore ?? '—'}</span>
            <span className="sub-metric-label">Clarity</span>
          </div>
          <div className="sub-metric-box">
            <span className="sub-metric-val">{stats.logicScore ?? '—'}</span>
            <span className="sub-metric-label">Logic</span>
          </div>
          <div className="sub-metric-box">
            <span className="sub-metric-val">{stats.keywordsScore ?? '—'}</span>
            <span className="sub-metric-label">Keywords</span>
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
            stats={stats}
            onOpenDetailedMap={() => {
              if (recentSessions.length > 0) {
                onViewReport(recentSessions[0].id);
              } else {
                onViewReport('mock-1');
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

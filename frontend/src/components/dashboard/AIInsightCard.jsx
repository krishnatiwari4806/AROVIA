import React, { useState, useEffect } from 'react';
import { Sparkles, ArrowUpRight, Target, ShieldCheck, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../../services/api';

/**
 * Grounded AI Insight Card for AROVIA Candidate Intelligence Dashboard.
 * Consumes authoritative REST API endpoint (`GET /api/v1/progress/insight`).
 * Grounded exclusively in verified session scores, dimension trends, and recurring patterns.
 * Completely eliminates fabricated percentiles, fake readiness, and synthetic quotes.
 */
export function AIInsightCard({ onOpenDetailedMap, totalSessions = 0 }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadInsight() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getProgressInsight();
      setInsight(data);
    } catch (err) {
      console.error('Failed to load grounded progress insight:', err);
      setError(err.message || 'Failed to generate progress insight.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadInsight();

    const handleUpdate = () => loadInsight();
    window.addEventListener('arovia_sessions_updated', handleUpdate);

    return () => {
      window.removeEventListener('arovia_sessions_updated', handleUpdate);
    };
  }, []);

  const isZeroState =
    !insight ||
    insight.source_type === 'zero_state' ||
    (totalSessions === 0 && (!insight || insight.source_type === 'zero_state'));

  return (
    <div className="arovia-ai-insight-card">
      <div className="insight-card-header">
        <div className="header-title-box">
          <Sparkles size={16} className="insight-sparkle-icon" />
          <span className="insight-title">AI PROGRESS INSIGHT</span>
        </div>
        <span className="live-engine-tag">
          {insight?.source_type === 'ai_grounded'
            ? 'GROUNDED MENTOR'
            : insight?.source_type === 'zero_state'
            ? 'BASELINE'
            : 'PROGRESS ENGINE'}
        </span>
      </div>

      <div className="insight-body">
        {loading ? (
          <div
            style={{
              padding: 'var(--space-lg) 0',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-sm)',
            }}
          >
            <div
              style={{
                height: '18px',
                width: '75%',
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '4px',
                animation: 'pulse 1.5s infinite ease-in-out',
              }}
            />
            <div
              style={{
                height: '42px',
                width: '100%',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '4px',
                animation: 'pulse 1.5s infinite ease-in-out',
              }}
            />
            <div
              style={{
                height: '60px',
                width: '100%',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '4px',
                animation: 'pulse 1.5s infinite ease-in-out',
              }}
            />
          </div>
        ) : error ? (
          <div
            style={{
              padding: 'var(--space-md) 0',
              color: '#f87171',
              fontSize: 'var(--text-xs)',
              lineHeight: '1.5',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: 'var(--space-xs)' }}>
              <AlertCircle size={15} />
              <span style={{ fontWeight: 600 }}>Insight Unavailable</span>
            </div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>{error}</p>
            <button
              onClick={loadInsight}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 8px',
                color: 'var(--text-primary)',
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={12} /> Retry
            </button>
          </div>
        ) : isZeroState ? (
          <div
            style={{
              padding: 'var(--space-sm) 0',
              color: 'var(--text-muted)',
              fontSize: 'var(--text-sm)',
              lineHeight: '1.5',
            }}
          >
            <h4
              className="insight-headline"
              style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-xs)' }}
            >
              {insight?.headline || 'Awaiting Assessment History'}
            </h4>
            <p className="insight-paragraph">
              {insight?.summary ||
                'Personalized insights and targeted practice recommendations will appear here based on your completed interview performance.'}
            </p>
            {insight?.recommended_action && (
              <div className="competency-delta-box">
                <div className="delta-label-row">
                  <span className="delta-label">GETTING STARTED</span>
                  <span className="delta-value">
                    <Target size={14} className="delta-trend-icon" />
                    First Step
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)',
                    marginTop: 'var(--space-xs)',
                    lineHeight: '1.4',
                  }}
                >
                  {insight.recommended_action}
                </p>
              </div>
            )}
          </div>
        ) : (
          <>
            <h4 className="insight-headline">{insight.headline}</h4>
            <p className="insight-paragraph">{insight.summary}</p>

            {insight.key_observation && (
              <div className="competency-delta-box" style={{ marginBottom: 'var(--space-sm)' }}>
                <div className="delta-label-row">
                  <span className="delta-label">KEY OBSERVATION</span>
                  <span className="delta-value" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    <ShieldCheck size={13} style={{ color: 'var(--accent-cyan)' }} />
                    {insight.source_type === 'ai_grounded' ? 'Verified Evidence' : 'Deterministic Analytics'}
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-primary)',
                    marginTop: '4px',
                    lineHeight: '1.4',
                  }}
                >
                  {insight.key_observation}
                </p>
                {insight.evidence && (
                  <p
                    style={{
                      fontSize: '10px',
                      color: 'var(--text-muted)',
                      marginTop: '4px',
                      fontStyle: 'italic',
                    }}
                  >
                    Evidence: {insight.evidence}
                  </p>
                )}
              </div>
            )}

            {insight.recommended_action && (
              <div className="competency-delta-box">
                <div className="delta-label-row">
                  <span className="delta-label">RECOMMENDED ACTION</span>
                  <span className="delta-value">
                    <Target size={14} className="delta-trend-icon" />
                    Practice Priority
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)',
                    marginTop: 'var(--space-xs)',
                    lineHeight: '1.4',
                  }}
                >
                  {insight.recommended_action}
                </p>
              </div>
            )}
          </>
        )}
      </div>

      <div className="insight-card-footer">
        <button className="view-competency-map-btn" onClick={onOpenDetailedMap}>
          <span>{totalSessions > 0 ? 'VIEW ASSESSMENT REPORT' : 'START FIRST INTERVIEW'}</span>
          <ArrowUpRight size={14} />
        </button>
      </div>
    </div>
  );
}

export default AIInsightCard;

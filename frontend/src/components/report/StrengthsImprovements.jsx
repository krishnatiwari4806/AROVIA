import React from 'react';
import { CheckCircle2, TrendingUp, Lightbulb } from 'lucide-react';

/**
 * Demonstrated Strengths vs Growth Areas matching Figma Performance Report.
 * Renders real multi-dimensional evaluation results without fallback mock data.
 */
export function StrengthsImprovements({ topStrengths = [], topImprovements = [] }) {
  const safeStrengths = Array.isArray(topStrengths) ? topStrengths : [];
  const safeImprovements = Array.isArray(topImprovements) ? topImprovements : [];

  return (
    <div className="arovia-strengths-growth-grid">
      {/* Demonstrated Strengths Card */}
      <div className="report-card-column strengths-column">
        <div className="column-header">
          <div className="title-box">
            <CheckCircle2 size={16} className="text-accent-cyan" />
            <h4 className="column-title">Demonstrated Strengths</h4>
          </div>
          <span className="count-tag">
            {safeStrengths.length} {safeStrengths.length === 1 ? 'competency' : 'competencies'}
          </span>
        </div>

        <div className="insights-card-list">
          {safeStrengths.length === 0 ? (
            <div
              className="empty-insights-box"
              style={{
                padding: 'var(--space-lg) var(--space-md)',
                color: 'var(--text-muted)',
                fontSize: 'var(--text-xs)',
                textAlign: 'center',
              }}
            >
              No strengths identified yet.
            </div>
          ) : (
            safeStrengths.map((item, idx) => (
              <div key={idx} className="insight-card-item strength-item">
                <h5 className="item-title">{item.title || 'Strength Identified'}</h5>
                <p className="item-desc">{item.description || 'Demonstrated domain competency during interview.'}</p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Growth Areas Card */}
      <div className="report-card-column growth-column">
        <div className="column-header">
          <div className="title-box">
            <TrendingUp size={16} className="text-accent-violet" />
            <h4 className="column-title">Growth Areas</h4>
          </div>
          <span className="count-tag">
            {safeImprovements.length} {safeImprovements.length === 1 ? 'recommendation' : 'recommendations'}
          </span>
        </div>

        <div className="insights-card-list">
          {safeImprovements.length === 0 ? (
            <div
              className="empty-insights-box"
              style={{
                padding: 'var(--space-lg) var(--space-md)',
                color: 'var(--text-muted)',
                fontSize: 'var(--text-xs)',
                textAlign: 'center',
              }}
            >
              No improvement areas identified yet.
            </div>
          ) : (
            safeImprovements.map((item, idx) => (
              <div key={idx} className="insight-card-item growth-item">
                <h5 className="item-title">{item.title || 'Growth Opportunity'}</h5>
                <p className="item-desc">{item.description || 'Identified competency growth gap.'}</p>
                {item.actionable_recommendation && (
                  <div
                    className="item-recommendation-box"
                    style={{
                      marginTop: 'var(--space-xs)',
                      paddingTop: 'var(--space-xs)',
                      borderTop: '1px dashed var(--border)',
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 'var(--space-2xs)',
                    }}
                  >
                    <Lightbulb size={13} className="text-accent-violet" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <strong style={{ color: 'var(--text-primary)' }}>Actionable Study Advice: </strong>
                      <span>{item.actionable_recommendation}</span>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default StrengthsImprovements;

import React from 'react';
import { Sparkles, TrendingUp, Compass, ArrowUpRight } from 'lucide-react';

/**
 * AI Insight Card matching Figma Dashboard right-column component.
 * Displays behavioral AI analytics, competency delta, and evaluation quotes.
 */
export function AIInsightCard({ onOpenDetailedMap, stats }) {
  return (
    <div className="arovia-ai-insight-card">
      <div className="insight-card-header">
        <div className="header-title-box">
          <Sparkles size={16} className="insight-sparkle-icon" />
          <span className="insight-title">AI INSIGHT</span>
        </div>
        <span className="live-engine-tag">AROVIA CORE</span>
      </div>

      <div className="insight-body">
        <h4 className="insight-headline">Spontaneous Conflict Resolution</h4>
        <p className="insight-paragraph">
          Analysis indicates strong structural reasoning during crisis scenarios,
          with high-fidelity problem decomposition. Focus on dynamic de-escalation
          techniques when faced with unscripted stakeholder pushback in executive settings.
        </p>

        {/* Competency Delta Gauge */}
        <div className="competency-delta-box">
          <div className="delta-label-row">
            <span className="delta-label">COMPETENCY DELTA</span>
            <span className="delta-value">
              <TrendingUp size={14} className="delta-trend-icon" />
              +1.2%
            </span>
          </div>
          <div className="delta-bar-track">
            <div className="delta-bar-fill" style={{ width: '78%' }} />
          </div>
        </div>

        {/* Behavioral Engine Quote */}
        <div className="behavioral-quote-box">
          <p className="quote-text">
            &ldquo;Candidate demonstrates exceptional poise under pressure.
            Introducing deliberate ambiguity in upcoming scenarios will rigorously
            test real-time adaptability.&rdquo;
          </p>
          <span className="quote-author">— AROVIA BEHAVIORAL ENGINE</span>
        </div>
      </div>

      <div className="insight-card-footer">
        <button
          className="view-competency-map-btn"
          onClick={onOpenDetailedMap}
        >
          <span>VIEW DETAILED COMPETENCY MAP</span>
          <ArrowUpRight size={14} />
        </button>
      </div>
    </div>
  );
}

export default AIInsightCard;

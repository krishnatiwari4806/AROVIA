import React from "react";
import { ArrowUpRight, CheckCircle2, Compass, Lightbulb, Target } from "lucide-react";

/**
 * Technical Strengths and Prioritized Actionable Growth Recommendations.
 */
export default function StrengthsImprovements({ topStrengths = [], topImprovements = [] }) {
  return (
    <div className="insights-grid">
      {/* Key Technical Strengths Card */}
      <div className="insight-column strengths-card">
        <div className="insight-column-header">
          <div className="insight-title-group">
            <div className="insight-icon-pill strengths-icon">
              <CheckCircle2 size={18} />
            </div>
            <div>
              <h3 className="insight-title">Demonstrated Strengths</h3>
              <p className="insight-subtitle">Evidence-backed engineering competencies</p>
            </div>
          </div>
          <span className="count-pill strengths-count">{topStrengths.length}</span>
        </div>

        <div className="insight-list">
          {topStrengths.length === 0 ? (
            <p className="empty-insight">No specific strengths recorded.</p>
          ) : (
            topStrengths.map((item, idx) => (
              <div key={`strength-${idx}`} className="insight-item-box strength-item">
                <div className="item-header-row">
                  <span className="item-title">{item.title}</span>
                  {item.evidence_turn_index !== undefined && item.evidence_turn_index !== null && (
                    <span className="turn-evidence-tag">
                      Turn {item.evidence_turn_index + 1}
                    </span>
                  )}
                </div>
                <p className="item-description">{item.description}</p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Prioritized Actionable Improvements Card */}
      <div className="insight-column improvements-card">
        <div className="insight-column-header">
          <div className="insight-title-group">
            <div className="insight-icon-pill improvements-icon">
              <Compass size={18} />
            </div>
            <div>
              <h3 className="insight-title">Prioritized Growth Areas</h3>
              <p className="insight-subtitle">Actionable recommendations & study topics</p>
            </div>
          </div>
          <span className="count-pill improvements-count">{topImprovements.length}</span>
        </div>

        <div className="insight-list">
          {topImprovements.length === 0 ? (
            <p className="empty-insight">No specific growth areas identified.</p>
          ) : (
            topImprovements.map((item, idx) => (
              <div key={`improvement-${idx}`} className="insight-item-box improvement-item">
                <div className="item-header-row">
                  <span className="item-title">{item.title}</span>
                  {item.evidence_turn_index !== undefined && item.evidence_turn_index !== null && (
                    <span className="turn-evidence-tag warning">
                      Turn {item.evidence_turn_index + 1}
                    </span>
                  )}
                </div>
                <p className="item-description">{item.description}</p>

                {item.actionable_recommendation && (
                  <div className="recommendation-callout">
                    <div className="rec-header">
                      <Lightbulb size={14} className="rec-icon" />
                      <span className="rec-title">Actionable Recommendation</span>
                    </div>
                    <p className="rec-text">{item.actionable_recommendation}</p>
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

import React from "react";
import { DIMENSION_METADATA } from "../../utils/competencyRubric";

/**
 * Single and Grouped Horizontal Metric Progress Bars for 5 Evaluation Dimensions.
 */
export function MetricBarItem({ dimensionKey, score = 0 }) {
  const meta = DIMENSION_METADATA[dimensionKey] || {
    label: dimensionKey,
    short: dimensionKey,
    description: "",
    color: "#3b82f6",
  };

  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));

  // Color mapping based on score threshold
  const getProgressColor = (val) => {
    if (val >= 85) return "#10b981"; // Emerald
    if (val >= 70) return "#3b82f6"; // Blue
    if (val >= 50) return "#f59e0b"; // Amber
    return "#f43f5e"; // Rose
  };

  const barColor = getProgressColor(clampedScore);

  return (
    <div className="metric-bar-item">
      <div className="metric-bar-header">
        <div className="metric-title-group">
          <span className="metric-dot" style={{ backgroundColor: meta.color }} />
          <span className="metric-label">{meta.label}</span>
        </div>
        <span className="metric-score-badge" style={{ color: barColor }}>
          {clampedScore}%
        </span>
      </div>

      <div className="metric-track">
        <div
          className="metric-fill"
          style={{
            width: `${clampedScore}%`,
            backgroundColor: barColor,
          }}
        />
      </div>

      <p className="metric-description">{meta.description}</p>
    </div>
  );
}

export default function MetricBarList({ dimensionScores = {} }) {
  const dimensions = ["relevance", "correctness", "keywords", "clarity", "confidence"];

  return (
    <div className="metric-bar-list-card">
      <div className="card-header-simple">
        <h3 className="card-title">Dimensional Score Breakdown</h3>
        <p className="card-subtitle">Granular performance analysis across all 5 evaluation pillars.</p>
      </div>

      <div className="metric-bars-container">
        {dimensions.map((dim) => (
          <MetricBarItem
            key={dim}
            dimensionKey={dim}
            score={dimensionScores[dim] || 0}
          />
        ))}
      </div>
    </div>
  );
}

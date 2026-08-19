import React from "react";
import { DIMENSION_METADATA, getSeniorityBenchmark } from "../../utils/competencyRubric";

/**
 * Pure SVG Multi-Axis Radar Chart Component.
 *
 * @param {Object} props
 * @param {Object} props.dimensionScores - { relevance, correctness, keywords, clarity, confidence }
 * @param {string} props.seniorityLevel - Candidate seniority level ('junior' | 'mid' | 'senior')
 * @param {number} [props.size=320] - SVG viewport dimension
 */
export default function RadarChart({ dimensionScores = {}, seniorityLevel = "mid", size = 320 }) {
  const dimensions = ["relevance", "correctness", "keywords", "clarity", "confidence"];
  const numAxes = dimensions.length;

  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.36; // Max radius with padding for labels

  const benchmarkScore = getSeniorityBenchmark(seniorityLevel);

  // Helper to compute (x, y) for an axis index and score
  const getCoordinates = (axisIndex, score) => {
    const angle = -Math.PI / 2 + (axisIndex * 2 * Math.PI) / numAxes;
    const r = (Math.max(0, Math.min(100, score || 0)) / 100) * radius;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  // Helper for label positioning slightly outside max radius
  const getLabelCoordinates = (axisIndex) => {
    const angle = -Math.PI / 2 + (axisIndex * 2 * Math.PI) / numAxes;
    const r = radius + 26;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  // Concentric grid rings (20%, 40%, 60%, 80%, 100%)
  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];

  // Build candidate polygon points
  const candidatePoints = dimensions
    .map((dim, idx) => {
      const score = dimensionScores[dim] || 50;
      const { x, y } = getCoordinates(idx, score);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  // Build benchmark polygon points
  const benchmarkPoints = dimensions
    .map((_, idx) => {
      const { x, y } = getCoordinates(idx, benchmarkScore);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="radar-chart-card">
      <div className="radar-header">
        <h3 className="card-title">Multi-Dimensional Competency Radar</h3>
        <p className="card-subtitle">
          5-dimension balance compared against the {seniorityLevel} benchmark threshold ({benchmarkScore}%).
        </p>
      </div>

      <div className="radar-svg-wrapper">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="radar-svg"
          aria-label="Multi-dimensional competency radar chart"
        >
          <defs>
            {/* Candidate Polygon Glow Gradient */}
            <radialGradient id="candidateGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.15" />
            </radialGradient>
          </defs>

          {/* Grid Rings */}
          {gridLevels.map((level, lvlIdx) => {
            const ringPoints = dimensions
              .map((_, idx) => {
                const { x, y } = getCoordinates(idx, level * 100);
                return `${x.toFixed(1)},${y.toFixed(1)}`;
              })
              .join(" ");
            return (
              <polygon
                key={`grid-ring-${lvlIdx}`}
                points={ringPoints}
                fill="none"
                stroke="rgba(255, 255, 255, 0.08)"
                strokeWidth="1"
              />
            );
          })}

          {/* Axis Radial Lines */}
          {dimensions.map((_, idx) => {
            const { x, y } = getCoordinates(idx, 100);
            return (
              <line
                key={`axis-line-${idx}`}
                x1={cx}
                y1={cy}
                x2={x}
                y2={y}
                stroke="rgba(255, 255, 255, 0.12)"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
            );
          })}

          {/* Target Seniority Benchmark Polygon */}
          <polygon
            points={benchmarkPoints}
            fill="none"
            stroke="#818cf8"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            className="benchmark-polygon"
          />

          {/* Candidate Score Polygon */}
          <polygon
            points={candidatePoints}
            fill="url(#candidateGradient)"
            stroke="#10b981"
            strokeWidth="2.5"
            className="candidate-polygon"
          />

          {/* Candidate Vertex Dots */}
          {dimensions.map((dim, idx) => {
            const score = dimensionScores[dim] || 50;
            const { x, y } = getCoordinates(idx, score);
            const meta = DIMENSION_METADATA[dim] || {};
            return (
              <g key={`vertex-${dim}`}>
                <circle
                  cx={x}
                  cy={y}
                  r="4.5"
                  fill="#0f172a"
                  stroke={meta.color || "#10b981"}
                  strokeWidth="2.5"
                />
              </g>
            );
          })}

          {/* Axis Labels */}
          {dimensions.map((dim, idx) => {
            const { x, y } = getLabelCoordinates(idx);
            const meta = DIMENSION_METADATA[dim] || {};
            const score = dimensionScores[dim] || 0;
            return (
              <text
                key={`label-${dim}`}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="central"
                className="radar-label"
              >
                <tspan x={x} dy="-0.4em" className="radar-label-title" fill="#e2e8f0">
                  {meta.short || dim}
                </tspan>
                <tspan x={x} dy="1.2em" className="radar-label-score" fill={meta.color || "#38bdf8"}>
                  {score}%
                </tspan>
              </text>
            );
          })}
        </svg>
      </div>

      {/* Chart Legend */}
      <div className="radar-legend">
        <div className="legend-item">
          <span className="legend-indicator candidate" />
          <span className="legend-text">Candidate Score</span>
        </div>
        <div className="legend-item">
          <span className="legend-indicator benchmark" />
          <span className="legend-text">{seniorityLevel.toUpperCase()} Target ({benchmarkScore}%)</span>
        </div>
      </div>
    </div>
  );
}

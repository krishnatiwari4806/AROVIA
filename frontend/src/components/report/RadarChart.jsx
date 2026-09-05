import React from 'react';
import { DIMENSION_METADATA, getSeniorityBenchmark } from '../../utils/competencyRubric';

/**
 * Pure SVG Multi-Axis Radar Chart matching Figma Performance Report.
 * Uses official Cyan -> Blue -> Violet gradients, translucent fill, and sleek axis labels.
 * Renders real dimension scores without fake fallback numbers.
 */
export function RadarChart({ dimensionScores = {}, seniorityLevel = 'senior', size = 300 }) {
  const dimensions = ['relevance', 'correctness', 'keywords', 'clarity', 'confidence'];
  const numAxes = dimensions.length;

  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.35;

  const benchmarkScore = getSeniorityBenchmark(seniorityLevel);
  const hasData = dimensions.some((dim) => typeof dimensionScores?.[dim] === 'number');

  const getCoordinates = (axisIndex, score) => {
    const angle = -Math.PI / 2 + (axisIndex * 2 * Math.PI) / numAxes;
    const r = (Math.max(0, Math.min(100, score || 0)) / 100) * radius;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  const getLabelCoordinates = (axisIndex) => {
    const angle = -Math.PI / 2 + (axisIndex * 2 * Math.PI) / numAxes;
    const r = radius + 24;
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  };

  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  const candidatePoints = dimensions
    .map((dim, idx) => {
      const score = typeof dimensionScores?.[dim] === 'number' ? dimensionScores[dim] : 0;
      const { x, y } = getCoordinates(idx, score);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const benchmarkPoints = dimensions
    .map((_, idx) => {
      const { x, y } = getCoordinates(idx, benchmarkScore);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="arovia-radar-card">
      <div className="radar-header">
        <h4 className="radar-title">Dimension Mapping</h4>
        <span className="radar-tag">RADAR PROJECTION</span>
      </div>

      <div className="radar-svg-container">
        <svg viewBox={`0 0 ${size} ${size}`} className="radar-chart-svg">
          <defs>
            <radialGradient id="aroviaRadarFill" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.45" />
              <stop offset="60%" stopColor="#5B8CFF" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.15" />
            </radialGradient>
          </defs>

          {/* Concentric Rings */}
          {gridLevels.map((lvl, idx) => {
            const points = dimensions
              .map((_, aIdx) => {
                const { x, y } = getCoordinates(aIdx, lvl * 100);
                return `${x.toFixed(1)},${y.toFixed(1)}`;
              })
              .join(' ');
            return (
              <polygon
                key={idx}
                points={points}
                fill="none"
                stroke="rgba(42, 48, 64, 0.8)"
                strokeWidth="1"
              />
            );
          })}

          {/* Radial Spokes */}
          {dimensions.map((_, idx) => {
            const { x, y } = getCoordinates(idx, 100);
            return (
              <line
                key={idx}
                x1={cx}
                y1={cy}
                x2={x}
                y2={y}
                stroke="rgba(42, 48, 64, 0.8)"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
            );
          })}

          {/* Target Benchmark Outline */}
          <polygon
            points={benchmarkPoints}
            fill="none"
            stroke="#8B5CF6"
            strokeWidth="1.2"
            strokeDasharray="3 3"
          />

          {/* Candidate Polygon (rendered only if real dimension scores exist) */}
          {hasData && (
            <polygon
              points={candidatePoints}
              fill="url(#aroviaRadarFill)"
              stroke="#22D3EE"
              strokeWidth="2"
            />
          )}

          {/* Vertex Nodes */}
          {dimensions.map((dim, idx) => {
            const score = typeof dimensionScores?.[dim] === 'number' ? dimensionScores[dim] : 0;
            const { x, y } = getCoordinates(idx, score);
            return (
              <circle
                key={dim}
                cx={x}
                cy={y}
                r="3.5"
                fill="#0B0D12"
                stroke="#22D3EE"
                strokeWidth="2"
              />
            );
          })}

          {/* Axis Labels */}
          {dimensions.map((dim, idx) => {
            const { x, y } = getLabelCoordinates(idx);
            const hasVal = typeof dimensionScores?.[dim] === 'number';
            const labelName = dim.toUpperCase();

            return (
              <text
                key={`label-${dim}`}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="central"
                className="radar-axis-text"
              >
                <tspan x={x} dy="-0.3em" fill="#9CA3AF" fontSize="9" fontWeight="600">
                  {labelName}
                </tspan>
                <tspan x={x} dy="1.1em" fill="#22D3EE" fontSize="10" fontWeight="700">
                  {hasVal ? `${dimensionScores[dim]}%` : '—'}
                </tspan>
              </text>
            );
          })}
        </svg>
      </div>

      <div className="radar-legend-row">
        <div className="legend-entry">
          <span className="legend-dot cyan" />
          <span>Candidate</span>
        </div>
        <div className="legend-entry">
          <span className="legend-dot violet" />
          <span>{seniorityLevel.toUpperCase()} Target ({benchmarkScore}%)</span>
        </div>
      </div>
    </div>
  );
}

export default RadarChart;

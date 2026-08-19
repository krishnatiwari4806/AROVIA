import React from 'react';

/**
 * Audio wave animation visualizer for AI speaking / candidate recording states.
 */
export function AudioVisualizer({ active = false, label = '' }) {
  if (!active) return null;

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.5rem' }}>
      <div className="visualizer-wave">
        <div className="wave-bar" />
        <div className="wave-bar" />
        <div className="wave-bar" />
        <div className="wave-bar" />
        <div className="wave-bar" />
      </div>
      {label && <span style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 600 }}>{label}</span>}
    </div>
  );
}

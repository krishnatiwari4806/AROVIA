import React from 'react';

/**
 * Audio wave equalizer visualizer underneath the 3D crystal core.
 */
export function AudioVisualizer({ isSpeaking = false, isListening = false }) {
  const isActive = isSpeaking || isListening;

  return (
    <div className={`arovia-waveform-container ${isActive ? 'active' : 'idle'}`}>
      <div className="waveform-bar" style={{ animationDelay: '0.0s' }} />
      <div className="waveform-bar" style={{ animationDelay: '0.2s' }} />
      <div className="waveform-bar" style={{ animationDelay: '0.4s' }} />
      <div className="waveform-bar" style={{ animationDelay: '0.1s' }} />
      <div className="waveform-bar" style={{ animationDelay: '0.3s' }} />
      <div className="waveform-bar" style={{ animationDelay: '0.5s' }} />
      <div className="waveform-bar" style={{ animationDelay: '0.25s' }} />
    </div>
  );
}

export default AudioVisualizer;

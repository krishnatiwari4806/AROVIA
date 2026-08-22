import React from 'react';
import { Sparkles, Play, Upload, ShieldCheck, Zap, Bot } from 'lucide-react';

/**
 * Candidate Dashboard Hero component with luxury-tech aesthetic.
 */
export function DashboardHero({ onQuickStart, onOpenUpload, hasActiveSession, onResumeActive }) {
  return (
    <div className="dashboard-hero-card">
      <div className="hero-gradient-overlay" />
      
      <div className="hero-content">
        <div className="hero-badge-row">
          <div className="hero-platform-badge">
            <Bot size={14} className="badge-icon-cyan" />
            <span>AI-Powered Adaptive Mock Engine</span>
          </div>
          <div className="hero-cost-badge">
            <Zap size={14} className="badge-icon-emerald" />
            <span>100% Free • Browser Native</span>
          </div>
        </div>

        <h1 className="hero-heading">
          Master Your Next <span className="text-gradient-cyan">Technical & Behavioral</span> Interview
        </h1>

        <p className="hero-description">
          Simulate realistic, multi-turn AI interviews calibrated to your exact target role, seniority tier, and resume background. Receive multi-dimensional scoring and actionable improvement roadmaps.
        </p>

        <div className="hero-action-row">
          {hasActiveSession ? (
            <button className="btn btn-primary btn-lg btn-glow" onClick={onResumeActive}>
              <Play size={18} />
              <span>Resume Active Session</span>
            </button>
          ) : (
            <button className="btn btn-primary btn-lg btn-glow" onClick={onQuickStart}>
              <Sparkles size={18} />
              <span>Launch Mock Interview</span>
            </button>
          )}

          <button className="btn btn-secondary btn-lg" onClick={onOpenUpload}>
            <Upload size={18} />
            <span>Upload / Update Resume</span>
          </button>
        </div>

        <div className="hero-features-list">
          <div className="feature-chip">
            <ShieldCheck size={14} className="chip-icon" />
            <span>5-Dimension Rubric Scoring</span>
          </div>
          <div className="feature-chip">
            <ShieldCheck size={14} className="chip-icon" />
            <span>Dynamic Gemini Probing</span>
          </div>
          <div className="feature-chip">
            <ShieldCheck size={14} className="chip-icon" />
            <span>Instant PDF Export</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardHero;

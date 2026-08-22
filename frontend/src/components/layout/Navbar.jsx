import React from 'react';
import { Terminal, Sparkles, Play, BarChart3, LayoutDashboard } from 'lucide-react';

/**
 * Top navigation bar with dark luxury-tech branding and status.
 */
export function Navbar({ currentView, onNavigate, hasActiveSession, onResumeActive }) {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="logo-brand" onClick={() => onNavigate('dashboard')} role="button" tabIndex={0} style={{ cursor: 'pointer' }}>
          <div className="logo-icon-box">
            <Terminal size={20} className="logo-icon" />
          </div>
          <div className="logo-text-group">
            <span className="logo-name">AROVIA</span>
            <span className="logo-subtext">AI INTERVIEW ENGINE</span>
          </div>
        </div>

        <nav className="navbar-nav">
          <button
            className={`nav-link ${currentView === 'dashboard' ? 'active' : ''}`}
            onClick={() => onNavigate('dashboard')}
          >
            <LayoutDashboard size={16} />
            <span>Dashboard</span>
          </button>

          <button
            className={`nav-link ${currentView === 'interview' ? 'active' : ''}`}
            onClick={() => {
              if (hasActiveSession && onResumeActive) {
                onResumeActive();
              } else {
                onNavigate('dashboard');
              }
            }}
          >
            <Play size={16} />
            <span>{hasActiveSession ? 'Active Session' : 'Practice Room'}</span>
            {hasActiveSession && <span className="nav-live-dot" title="Active session in progress" />}
          </button>
        </nav>

        <div className="navbar-actions">
          <div className="system-status-badge">
            <span className="status-indicator-dot" />
            <span className="status-text">Gemini 2.0 Calibrated</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;

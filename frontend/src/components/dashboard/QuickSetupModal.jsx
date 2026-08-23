import React, { useState } from 'react';
import { X, Sparkles, Sliders, Briefcase, Zap, FileText, AlertCircle, ArrowRight } from 'lucide-react';
import { api } from '../../services/api';

/**
 * Quick Setup / Calibration Modal for launching a mock interview session.
 */
export function QuickSetupModal({ initialPreset, onClose, onSessionCreated }) {
  const [targetRole, setTargetRole] = useState(initialPreset?.title || 'Fullstack Engineer');
  const [seniorityLevel, setSeniorityLevel] = useState('mid');
  const [interviewFocus, setInterviewFocus] = useState('Technical Core');
  const [practiceMode, setPracticeMode] = useState('full');
  const [customJobDesc, setCustomJobDesc] = useState('');
  const [focusSkillsText, setFocusSkillsText] = useState(
    initialPreset?.default_skills ? initialPreset.default_skills.join(', ') : 'React, Python, System Architecture'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!targetRole.trim()) {
      setError('Please provide a target role title.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const focusSkills = focusSkillsText
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const payload = {
        target_role: targetRole.trim(),
        seniority_level: seniorityLevel,
        interview_focus: interviewFocus,
        practice_mode: practiceMode,
        custom_job_desc: customJobDesc.trim() || undefined,
        focus_skills: focusSkills.length > 0 ? focusSkills : undefined,
      };

      const session = await api.createSession(payload);
      if (onSessionCreated) {
        onSessionCreated(session);
      }
    } catch (err) {
      setError(err.message || 'Failed to initialize interview session.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-box">
              <Sliders size={20} className="text-cyan" />
            </div>
            <div>
              <h3 className="modal-title">Calibrate Interview Parameters</h3>
              <p className="modal-subtitle">Configure AI question generation scope and difficulty</p>
            </div>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="badge badge-danger alert-badge" style={{ margin: '1rem 1.5rem 0' }}>
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-body">
          {/* Target Role */}
          <div className="form-group">
            <label className="form-label">Target Role Title</label>
            <input
              type="text"
              className="form-input"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              placeholder="e.g. Senior Backend Engineer, Frontend Architect"
              required
            />
          </div>

          {/* Seniority Level */}
          <div className="form-group">
            <label className="form-label">Seniority Tier</label>
            <div className="segment-control">
              {[
                { id: 'junior', label: 'Junior / Entry' },
                { id: 'mid', label: 'Mid-Level' },
                { id: 'senior', label: 'Senior / Staff' },
              ].map((tier) => (
                <button
                  type="button"
                  key={tier.id}
                  className={`segment-btn ${seniorityLevel === tier.id ? 'active' : ''}`}
                  onClick={() => setSeniorityLevel(tier.id)}
                >
                  {tier.label}
                </button>
              ))}
            </div>
          </div>

          {/* Interview Focus Dimension */}
          <div className="form-group">
            <label className="form-label">Primary Interview Focus</label>
            <div className="segment-control">
              {[
                { id: 'Technical Core', label: 'Technical Core' },
                { id: 'System Design', label: 'System Design' },
                { id: 'Behavioral', label: 'Behavioral' },
              ].map((focus) => (
                <button
                  type="button"
                  key={focus.id}
                  className={`segment-btn ${interviewFocus === focus.id ? 'active' : ''}`}
                  onClick={() => setInterviewFocus(focus.id)}
                >
                  {focus.label}
                </button>
              ))}
            </div>
          </div>

          {/* Practice Mode */}
          <div className="form-group">
            <label className="form-label">Pacing Mode</label>
            <div className="mode-selection-grid">
              <div
                className={`mode-card ${practiceMode === 'full' ? 'active' : ''}`}
                onClick={() => setPracticeMode('full')}
              >
                <div className="mode-card-header">
                  <span className="mode-title">Full Mock Interview</span>
                  <span className="mode-pill">Standard</span>
                </div>
                <p className="mode-desc">6 core questions with adaptive follow-ups (~20 mins). Full multi-dimensional evaluation.</p>
              </div>

              <div
                className={`mode-card ${practiceMode === 'quick' ? 'active' : ''}`}
                onClick={() => setPracticeMode('quick')}
              >
                <div className="mode-card-header">
                  <span className="mode-title">Quick Practice</span>
                  <span className="mode-pill">Fast</span>
                </div>
                <p className="mode-desc">3 core questions with rapid feedback (~10 mins). Ideal for focused drilling.</p>
              </div>
            </div>
          </div>

          {/* Priority Technologies / Skills */}
          <div className="form-group">
            <label className="form-label">Priority Technologies & Keywords (Comma-separated)</label>
            <input
              type="text"
              className="form-input"
              value={focusSkillsText}
              onChange={(e) => setFocusSkillsText(e.target.value)}
              placeholder="e.g. React, PostgreSQL, Docker, Kafka, Distributed Caching"
            />
          </div>

          {/* Optional Job Description */}
          <div className="form-group">
            <label className="form-label">Job Description / Requirements (Optional)</label>
            <textarea
              className="form-textarea"
              rows={3}
              value={customJobDesc}
              onChange={(e) => setCustomJobDesc(e.target.value)}
              placeholder="Paste target job listing requirements or specific company focus topics here..."
            />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-glow" disabled={loading}>
              {loading ? (
                <>
                  <Sparkles size={16} className="spin" />
                  <span>Synthesizing Session...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Start Interview Room</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default QuickSetupModal;

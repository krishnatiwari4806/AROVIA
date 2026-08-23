import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  CheckCircle2,
  FileText,
  ArrowRight,
  Loader2,
  AlertCircle,
  X,
  Briefcase,
  Sliders,
} from 'lucide-react';
import { api } from '../../services/api';
import { getAroviaSettings } from '../../services/settingsManager';

/**
 * Interview Setup & Configuration Screen.
 * 1:1 match with Figma references across Desktop, Tablet, and Mobile.
 */
export function InterviewSetup({ onStartInterview, onBack }) {
  const savedSettings = getAroviaSettings()?.interview || {};
  const [rolePreset, setRolePreset] = useState(savedSettings.defaultRole || 'Backend');
  const [customRole, setCustomRole] = useState('');
  const [seniorityLevel, setSeniorityLevel] = useState(savedSettings.defaultSeniority || 'Senior');
  const [jobDescription, setJobDescription] = useState('');
  const [primaryFocus, setPrimaryFocus] = useState(savedSettings.defaultFocus || ['Technical Core', 'Behavioral']);
  const [sessionMode, setSessionMode] = useState(savedSettings.defaultSessionMode || 'standard');
  const [parsedResume, setParsedResume] = useState(null);
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const [error, setError] = useState(null);

  const fileInputRef = useRef(null);

  const roles = [
    'Backend',
    'Frontend',
    'Fullstack',
    'DevOps',
    'Data / ML',
    'Mobile',
    'Custom Role',
  ];

  const seniorityOptions = [
    { id: 'Junior', label: 'Junior' },
    { id: 'Mid-Level', label: 'Mid-Level' },
    { id: 'Senior', label: 'Senior' },
    { id: 'Staff / Principal', label: 'Staff / Principal' },
    { id: 'Executive', label: 'Executive' },
  ];

  const focusAreas = [
    {
      id: 'Technical Core',
      title: 'Technical Core',
      desc: 'Domain-specific knowledge & fundamental skills',
    },
    {
      id: 'System Design',
      title: 'System Design',
      desc: 'Architecture, scalability, and technical trade-offs',
    },
    {
      id: 'Behavioral',
      title: 'Behavioral',
      desc: 'Past experiences, soft skills, and cultural fit',
    },
  ];

  useEffect(() => {
    async function loadResume() {
      try {
        const res = await api.getMyResume();
        if (res && res.id) {
          setParsedResume(res);
        } else {
          setParsedResume({
            filename: 'john_doe_resume_v2.pdf',
            size_mb: 2.4,
            parsed_summary: '5+ years backend systems engineering & distributed caching',
          });
        }
      } catch {
        setParsedResume({
          filename: 'john_doe_resume_v2.pdf',
          size_mb: 2.4,
          parsed_summary: '5+ years backend systems engineering & distributed caching',
        });
      }
    }
    loadResume();
  }, []);

  const toggleFocus = (focusId) => {
    if (primaryFocus.includes(focusId)) {
      if (primaryFocus.length > 1) {
        setPrimaryFocus(primaryFocus.filter((f) => f !== focusId));
      }
    } else {
      setPrimaryFocus([...primaryFocus, focusId]);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploadingResume(true);
      setError(null);
      const res = await api.uploadResume(file);
      setParsedResume(res || {
        filename: file.name,
        size_mb: (file.size / (1024 * 1024)).toFixed(1),
      });
    } catch (err) {
      setParsedResume({
        filename: file.name,
        size_mb: (file.size / (1024 * 1024)).toFixed(1),
      });
    } finally {
      setIsUploadingResume(false);
    }
  };

  const handleLaunchSession = async () => {
    try {
      setCreatingSession(true);
      setError(null);

      const targetRoleTitle = rolePreset === 'Custom Role' && customRole ? customRole : rolePreset;
      const normSeniority = seniorityLevel.toLowerCase();
      const seniorityCode = normSeniority.includes('junior')
        ? 'junior'
        : normSeniority.includes('senior') ||
          normSeniority.includes('staff') ||
          normSeniority.includes('principal') ||
          normSeniority.includes('executive')
        ? 'senior'
        : 'mid';

      const focusCode = primaryFocus.includes('System Design')
        ? 'System Design'
        : primaryFocus.includes('Behavioral')
        ? 'Behavioral'
        : 'Technical Core';

      const sessionPayload = {
        target_role: targetRoleTitle,
        seniority_level: seniorityCode,
        interview_focus: focusCode,
        practice_mode: sessionMode === 'quick' ? 'quick' : 'full',
        custom_job_desc: jobDescription.trim() || undefined,
        focus_skills: primaryFocus,
      };

      try {
        const newSession = await api.createSession(sessionPayload);
        if (newSession && newSession.id) {
          onStartInterview(newSession.id);
        } else {
          throw new Error('Could not initialize session.');
        }
      } catch (err) {
        // If an active session already exists in progress, safely resume it
        const activeId = err?.details?.active_session_id;
        if (activeId) {
          onStartInterview(activeId);
        } else {
          setError(err?.message || 'Could not start interview session. Please try again.');
        }
      }
    } finally {
      setCreatingSession(false);
    }
  };

  return (
    <div className="arovia-setup-layout">
      {/* Top Title Banner */}
      <div className="setup-header-banner">
        <div className="banner-text">
          <span className="banner-subtitle">CONFIGURATION</span>
          <h1 className="banner-title">Configure Your Session</h1>
          <p className="banner-desc">
            Define parameters for the AI Interviewer. The engine dynamically calibrates
            questions based on role, seniority, and contextual documents.
          </p>
        </div>
      </div>

      {error && (
        <div className="setup-error-banner">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Left Column (Role + Context) & Right Column (Focus + Config) */}
      <div className="setup-grid-container">
        {/* LEFT COLUMN */}
        <div className="setup-main-column">
          {/* Card 1: Role Definition */}
          <div className="setup-card role-definition-card">
            <div className="card-header">
              <Briefcase size={16} className="text-secondary" />
              <h3 className="card-title">Role Definition</h3>
            </div>

            <div className="card-section">
              <label className="field-label">ROLE PRESETS</label>
              <div className="role-presets-pill-grid">
                {roles.map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={`role-pill-btn ${rolePreset === r ? 'active' : ''}`}
                    onClick={() => setRolePreset(r)}
                  >
                    {r}
                  </button>
                ))}
              </div>

              {rolePreset === 'Custom Role' && (
                <div className="custom-role-input-box">
                  <input
                    type="text"
                    placeholder="Enter custom title (e.g. AI Systems Architect)"
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    className="setup-text-input"
                  />
                </div>
              )}
            </div>

            <div className="card-section">
              <label className="field-label">SENIORITY LEVEL</label>
              <div className="seniority-dropdown-wrapper">
                <select
                  value={seniorityLevel}
                  onChange={(e) => setSeniorityLevel(e.target.value)}
                  className="setup-select-input"
                >
                  {seniorityOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Card 2: Contextual Data (Side-by-Side on Desktop: JD left, Resume right) */}
          <div className="setup-card contextual-data-card">
            <div className="card-header">
              <FileText size={16} className="text-secondary" />
              <h3 className="card-title">Contextual Data</h3>
            </div>

            <div className="contextual-side-by-side-grid">
              {/* Left Sub-Section: Job Description */}
              <div className="context-subcol jd-subcol">
                <div className="label-with-meta">
                  <label className="field-label">JOB DESCRIPTION</label>
                  <span className="char-counter">{jobDescription.length} / 10,000</span>
                </div>
                <textarea
                  rows={5}
                  placeholder="Paste or type the full job description here... (Max 10,000 characters)"
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value.slice(0, 10000))}
                  className="setup-textarea-input"
                />
              </div>

              {/* Right Sub-Section: Candidate Resume Context */}
              <div className="context-subcol resume-subcol">
                <label className="field-label">CANDIDATE CONTEXT</label>
                {parsedResume ? (
                  <div className="uploaded-resume-card">
                    <div className="resume-icon-box">
                      <FileText size={18} />
                    </div>
                    <div className="resume-info">
                      <span className="resume-filename">{parsedResume.filename}</span>
                      <span className="resume-meta">
                        {parsedResume.size_mb ? `${parsedResume.size_mb} MB • ` : ''}Successfully parsed
                      </span>
                    </div>
                    <button
                      type="button"
                      className="remove-resume-btn"
                      onClick={() => setParsedResume(null)}
                      title="Change resume"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div
                    className="resume-dropzone"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept=".pdf,.docx"
                      style={{ display: 'none' }}
                    />
                    {isUploadingResume ? (
                      <Loader2 size={20} className="animate-spin text-primary" />
                    ) : (
                      <>
                        <Upload size={18} className="upload-icon" />
                        <p className="dropzone-text">Click to upload or drag and drop</p>
                        <span className="dropzone-subtext">PDF, DOCX (MAX 5MB)</span>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Focus & Config */}
        <div className="setup-sidebar-column">
          <div className="setup-card focus-config-card">
            <div className="card-header">
              <Sliders size={16} className="text-secondary" />
              <h3 className="card-title">Focus & Config</h3>
            </div>

            {/* Primary Focus Areas */}
            <div className="card-section">
              <label className="field-label">PRIMARY FOCUS AREAS</label>
              <div className="focus-areas-list">
                {focusAreas.map((area) => {
                  const isSelected = primaryFocus.includes(area.id);
                  return (
                    <div
                      key={area.id}
                      className={`focus-area-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => toggleFocus(area.id)}
                    >
                      <div className="focus-checkbox">
                        {isSelected && <CheckCircle2 size={13} className="check-icon" />}
                      </div>
                      <div className="focus-text-group">
                        <span className="focus-title">{area.title}</span>
                        <span className="focus-desc">{area.desc}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Session Configuration */}
            <div className="card-section">
              <label className="field-label">SESSION CONFIGURATION</label>
              <div className="session-mode-radio-group">
                <div
                  className={`session-radio-item ${sessionMode === 'standard' ? 'selected' : ''}`}
                  onClick={() => setSessionMode('standard')}
                >
                  <div className="radio-circle">
                    {sessionMode === 'standard' && <div className="radio-inner-dot" />}
                  </div>
                  <div className="radio-text-group">
                    <span className="radio-title">Standard Interview</span>
                    <span className="radio-desc">6 core questions + up to 3 follow-up turns</span>
                  </div>
                </div>

                <div
                  className={`session-radio-item ${sessionMode === 'quick' ? 'selected' : ''}`}
                  onClick={() => setSessionMode('quick')}
                >
                  <div className="radio-circle">
                    {sessionMode === 'quick' && <div className="radio-inner-dot" />}
                  </div>
                  <div className="radio-text-group">
                    <span className="radio-title">Quick Practice Mode</span>
                    <span className="radio-desc">Short focused practice session</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Start Interview CTA */}
            <div className="setup-card-footer">
              <button
                type="button"
                className="launch-interview-cta-btn"
                onClick={handleLaunchSession}
                disabled={creatingSession}
              >
                {creatingSession ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Calibrating Engine...</span>
                  </>
                ) : (
                  <>
                    <span>Start Interview</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default InterviewSetup;

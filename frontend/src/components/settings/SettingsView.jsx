import React, { useState, useEffect } from 'react';
import {
  User,
  Sliders,
  Volume2,
  Sparkles,
  Palette,
  Bell,
  Shield,
  Eye,
  Info,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  Download,
  Trash2,
  LogOut,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import {
  getAroviaSettings,
  saveAroviaSettings,
  DEFAULT_SETTINGS,
} from '../../services/settingsManager';
import { useSpeechSynthesis } from '../../hooks/useSpeechSynthesis';
import { AroviaLogo } from '../common/AroviaLogo';

/**
 * Production-Quality Settings System for AROVIA.
 * Provides granular preferences for interview defaults, language/voice calibration,
 * accessibility tokens, visual appearance, notifications, and data management.
 */
export function SettingsView({ onReplayIntro, onNavigate }) {
  const [activeTab, setActiveTab] = useState('interview');
  const [settings, setSettings] = useState(() => getAroviaSettings());
  const [saveBanner, setSaveBanner] = useState(false);
  const [clearedNotice, setClearedNotice] = useState(false);
  const [exportedNotice, setExportedNotice] = useState(false);
  const [profileData, setProfileData] = useState(null);

  const { speak, isSpeaking, availableVoices } = useSpeechSynthesis();

  // Load profile context for Account section
  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem('arovia_candidate_profile');
      if (savedProfile) {
        setProfileData(JSON.parse(savedProfile));
      }
    } catch {
      // ignore
    }
  }, []);

  const updateSectionSetting = (section, key, value) => {
    const updated = {
      ...settings,
      [section]: {
        ...settings[section],
        [key]: value,
      },
    };
    setSettings(updated);
    saveAroviaSettings(updated);

    setSaveBanner(true);
    setTimeout(() => setSaveBanner(false), 2000);
  };

  const handleTestVoice = () => {
    const text = 'Welcome to AROVIA. I am your AI technical interviewer, calibrated to evaluate your responses.';
    speak(text, null, {
      voiceURI: settings.languageVoice.voiceURI,
      rate: settings.languageVoice.voiceSpeed,
      volume: settings.languageVoice.voiceVolume,
      language: settings.languageVoice.language,
    });
  };

  const handleResetDefaults = () => {
    if (window.confirm('Reset all settings to AROVIA default parameters?')) {
      setSettings(DEFAULT_SETTINGS);
      saveAroviaSettings(DEFAULT_SETTINGS);
      setSaveBanner(true);
      setTimeout(() => setSaveBanner(false), 2000);
    }
  };

  const handleExportData = () => {
    try {
      const exportObject = {
        exportedAt: new Date().toISOString(),
        application: 'AROVIA AI Interview Intelligence',
        settings: settings,
        profile: profileData || {},
        sessions: JSON.parse(localStorage.getItem('arovia_recent_sessions') || '[]'),
      };

      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportObject, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `arovia_candidate_data_${Date.now()}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();

      setExportedNotice(true);
      setTimeout(() => setExportedNotice(false), 3000);
    } catch (err) {
      console.warn('Data export error:', err);
    }
  };

  const handleClearCache = () => {
    if (
      window.confirm(
        'Are you sure you want to clear your local practice session history and cached reports? This cannot be undone.'
      )
    ) {
      try {
        localStorage.removeItem('arovia_recent_sessions');
        sessionStorage.removeItem('arovia_intro_seen');
        setClearedNotice(true);
        setTimeout(() => setClearedNotice(false), 3000);
      } catch (err) {
        console.warn('Clear error:', err);
      }
    }
  };

  const handleLogout = () => {
    if (window.confirm('Sign out of your current AROVIA session?')) {
      localStorage.removeItem('arovia_token');
      window.location.reload();
    }
  };

  const navSections = [
    { id: 'account', label: 'Account & Security', icon: User },
    { id: 'interview', label: 'Interview Defaults', icon: Sliders },
    { id: 'languageVoice', label: 'Language & Voice', icon: Volume2 },
    { id: 'ai', label: 'AI Calibration', icon: Sparkles },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy & Data', icon: Shield },
    { id: 'accessibility', label: 'Accessibility', icon: Eye },
    { id: 'about', label: 'About AROVIA', icon: Info },
  ];

  const languages = [
    { code: 'en-US', label: 'English (United States)' },
    { code: 'en-GB', label: 'English (United Kingdom)' },
    { code: 'en-IN', label: 'English (India)' },
    { code: 'es-ES', label: 'Español (Spain)' },
    { code: 'fr-FR', label: 'Français (France)' },
    { code: 'de-DE', label: 'Deutsch (Germany)' },
    { code: 'ja-JP', label: '日本語 (Japan)' },
    { code: 'hi-IN', label: 'हिन्दी (Hindi)' },
  ];

  const roles = ['Backend', 'Frontend', 'Fullstack', 'DevOps', 'Data / ML', 'Mobile'];
  const seniorityLevels = ['Junior', 'Mid-Level', 'Senior', 'Staff / Principal', 'Executive'];

  return (
    <div className="arovia-settings-layout">
      {/* Header Banner */}
      <div className="settings-header-banner">
        <div className="banner-text">
          <span className="banner-subtitle">PREFERENCES & CALIBRATION</span>
          <h1 className="banner-title">System Settings</h1>
          <p className="banner-desc">
            Configure default interview parameters, speech synthesis engines, accessibility options, and data privacy.
          </p>
        </div>

        <div className="settings-banner-actions">
          {saveBanner && (
            <span className="save-indicator-badge">
              <CheckCircle2 size={13} />
              Saved
            </span>
          )}
          <button type="button" className="reset-defaults-btn" onClick={handleResetDefaults}>
            <RotateCcw size={13} />
            <span>Reset Defaults</span>
          </button>
        </div>
      </div>

      {/* Main Settings Navigation & Content Layout */}
      <div className="settings-master-grid">
        {/* Left Section Navigation Rail */}
        <aside className="settings-nav-rail">
          {navSections.map((sec) => {
            const Icon = sec.icon;
            const isActive = activeTab === sec.id;
            return (
              <button
                key={sec.id}
                type="button"
                className={`settings-rail-btn ${isActive ? 'active' : ''}`}
                onClick={() => setActiveTab(sec.id)}
              >
                <Icon size={16} className="rail-btn-icon" />
                <span className="rail-btn-label">{sec.label}</span>
                {isActive && <ChevronRight size={14} className="active-arrow" />}
              </button>
            );
          })}
        </aside>

        {/* Right Active Settings Pane */}
        <main className="settings-pane-content">
          {/* 1. ACCOUNT SECTION */}
          {activeTab === 'account' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Account Credentials & Access</h3>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Candidate Account</span>
                    <span className="setting-desc">
                      {profileData?.email || 'Not configured'} • {profileData?.full_name || 'Candidate'}
                    </span>
                  </div>
                  <span className="setting-status-pill text-cyan">Active Tier</span>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Profile Information</span>
                    <span className="setting-desc">
                      Update your display name, contact info, and online links.
                    </span>
                  </div>
                  <button
                    type="button"
                    className="settings-action-btn"
                    onClick={() => onNavigate?.('profile')}
                  >
                    <span>Edit Profile</span>
                  </button>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Session Authentication</span>
                    <span className="setting-desc">
                      End your active browser session and clear stored tokens.
                    </span>
                  </div>
                  <button
                    type="button"
                    className="settings-action-btn danger-btn"
                    onClick={handleLogout}
                  >
                    <LogOut size={14} />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 2. INTERVIEW PREFERENCES SECTION */}
          {activeTab === 'interview' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Interview Setup Defaults</h3>
                </div>

                {/* Default Role */}
                <div className="setting-row-stacked">
                  <span className="setting-label">DEFAULT TARGET ROLE</span>
                  <p className="setting-desc">Pre-selected role when configuring a new interview session.</p>
                  <div className="setting-pills-row">
                    {roles.map((r) => (
                      <button
                        key={r}
                        type="button"
                        className={`pill-option-btn ${
                          settings.interview.defaultRole === r ? 'active' : ''
                        }`}
                        onClick={() => updateSectionSetting('interview', 'defaultRole', r)}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Default Seniority */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Default Seniority Calibration</span>
                    <span className="setting-desc">Sets baseline question difficulty level.</span>
                  </div>
                  <select
                    className="setting-select-control"
                    value={settings.interview.defaultSeniority}
                    onChange={(e) =>
                      updateSectionSetting('interview', 'defaultSeniority', e.target.value)
                    }
                  >
                    {seniorityLevels.map((lvl) => (
                      <option key={lvl} value={lvl}>
                        {lvl}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Default Session Mode */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Default Session Mode</span>
                    <span className="setting-desc">
                      Standard mode (6 questions) or Quick Practice (3 questions).
                    </span>
                  </div>
                  <div className="segmented-control">
                    <button
                      type="button"
                      className={`segment-btn ${
                        settings.interview.defaultSessionMode === 'standard' ? 'active' : ''
                      }`}
                      onClick={() =>
                        updateSectionSetting('interview', 'defaultSessionMode', 'standard')
                      }
                    >
                      Standard (6Q)
                    </button>
                    <button
                      type="button"
                      className={`segment-btn ${
                        settings.interview.defaultSessionMode === 'quick' ? 'active' : ''
                      }`}
                      onClick={() =>
                        updateSectionSetting('interview', 'defaultSessionMode', 'quick')
                      }
                    >
                      Quick (3Q)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 3. LANGUAGE & VOICE SECTION */}
          {activeTab === 'languageVoice' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Speech Synthesis (TTS) & Recognition (STT)</h3>
                </div>

                {/* Preferred Language */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Speech Recognition Language</span>
                    <span className="setting-desc">
                      Used for browser speech recognition during live interview turns.
                    </span>
                  </div>
                  <select
                    className="setting-select-control"
                    value={settings.languageVoice.language}
                    onChange={(e) =>
                      updateSectionSetting('languageVoice', 'language', e.target.value)
                    }
                  >
                    {languages.map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* AI Voice Selection */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">AI Interviewer Voice</span>
                    <span className="setting-desc">
                      Select synthesized voice from available browser acoustic models.
                    </span>
                  </div>
                  <select
                    className="setting-select-control"
                    value={settings.languageVoice.voiceURI}
                    onChange={(e) =>
                      updateSectionSetting('languageVoice', 'voiceURI', e.target.value)
                    }
                  >
                    <option value="">System Default (Natural English)</option>
                    {availableVoices.map((v, i) => (
                      <option key={v.voiceURI || i} value={v.voiceURI || v.name}>
                        {v.name} ({v.lang})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Voice Speed Slider */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Voice Cadence / Speed</span>
                    <span className="setting-desc">
                      Playback speech rate ({settings.languageVoice.voiceSpeed}x).
                    </span>
                  </div>
                  <div className="slider-control-group">
                    <input
                      type="range"
                      min="0.75"
                      max="1.5"
                      step="0.05"
                      value={settings.languageVoice.voiceSpeed}
                      onChange={(e) =>
                        updateSectionSetting(
                          'languageVoice',
                          'voiceSpeed',
                          parseFloat(e.target.value)
                        )
                      }
                      className="setting-range-slider"
                    />
                    <span className="slider-value-badge">
                      {settings.languageVoice.voiceSpeed}x
                    </span>
                  </div>
                </div>

                {/* Voice Volume Slider */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Voice Volume</span>
                    <span className="setting-desc">
                      Audio output level ({Math.round(settings.languageVoice.voiceVolume * 100)}%).
                    </span>
                  </div>
                  <div className="slider-control-group">
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={settings.languageVoice.voiceVolume}
                      onChange={(e) =>
                        updateSectionSetting(
                          'languageVoice',
                          'voiceVolume',
                          parseFloat(e.target.value)
                        )
                      }
                      className="setting-range-slider"
                    />
                    <span className="slider-value-badge">
                      {Math.round(settings.languageVoice.voiceVolume * 100)}%
                    </span>
                  </div>
                </div>

                {/* Auto Play Toggle */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Auto-play AI Questions</span>
                    <span className="setting-desc">
                      Automatically speak each AI question aloud when the turn begins.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.languageVoice.autoPlayQuestions}
                      onChange={(e) =>
                        updateSectionSetting('languageVoice', 'autoPlayQuestions', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                {/* Speech Dictation / STT Toggle */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Microphone Dictation (STT)</span>
                    <span className="setting-desc">
                      Enable real-time voice transcription into the answer textarea.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.languageVoice.sttEnabled}
                      onChange={(e) =>
                        updateSectionSetting('languageVoice', 'sttEnabled', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                {/* Test Voice CTA */}
                <div className="setting-row-footer">
                  <button
                    type="button"
                    className="settings-action-btn primary-btn"
                    onClick={handleTestVoice}
                    disabled={isSpeaking}
                  >
                    <Volume2 size={14} />
                    <span>{isSpeaking ? 'Speaking...' : 'Test Audio & Voice'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 4. AI CALIBRATION & BEHAVIOR SECTION */}
          {activeTab === 'ai' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">AI Evaluation Calibration</h3>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Evaluation Engine</span>
                    <span className="setting-desc">
                      Google Gemini 2.0 Flash with Native JSON Schema Enforcement.
                    </span>
                  </div>
                  <span className="setting-status-pill text-cyan">Calibrated Standard</span>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Adaptive Probing Loops</span>
                    <span className="setting-desc">
                      Generate dynamic follow-up probing questions on brief answers.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.ai.adaptiveProbing}
                      onChange={(e) =>
                        updateSectionSetting('ai', 'adaptiveProbing', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Scorecard Feedback Depth</span>
                    <span className="setting-desc">
                      Format depth for generated strength/weakness evaluations.
                    </span>
                  </div>
                  <div className="segmented-control">
                    <button
                      type="button"
                      className={`segment-btn ${
                        settings.ai.feedbackDetail === 'comprehensive' ? 'active' : ''
                      }`}
                      onClick={() => updateSectionSetting('ai', 'feedbackDetail', 'comprehensive')}
                    >
                      5-Dimensional
                    </button>
                    <button
                      type="button"
                      className={`segment-btn ${
                        settings.ai.feedbackDetail === 'concise' ? 'active' : ''
                      }`}
                      onClick={() => updateSectionSetting('ai', 'feedbackDetail', 'concise')}
                    >
                      Brief Summary
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 5. APPEARANCE SECTION */}
          {activeTab === 'appearance' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Visual Appearance & Motion</h3>
                </div>

                {/* Theme selection */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Interface Theme</span>
                    <span className="setting-desc">
                      AROVIA Figma dark luxury-tech token palette.
                    </span>
                  </div>
                  <div className="segmented-control">
                    <button
                      type="button"
                      className={`segment-btn ${
                        settings.appearance.theme === 'dark' ? 'active' : ''
                      }`}
                      onClick={() => updateSectionSetting('appearance', 'theme', 'dark')}
                    >
                      Dark Matte
                    </button>
                    <button
                      type="button"
                      className={`segment-btn ${
                        settings.appearance.theme === 'system' ? 'active' : ''
                      }`}
                      onClick={() => updateSectionSetting('appearance', 'theme', 'system')}
                    >
                      System
                    </button>
                  </div>
                </div>

                {/* Reduce motion */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Reduce Motion</span>
                    <span className="setting-desc">
                      Minimize floating and 3D geometric animation cycles.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.appearance.reduceMotion}
                      onChange={(e) =>
                        updateSectionSetting('appearance', 'reduceMotion', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                {/* 3D Intro Flow Replay */}
                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">AROVIA 3D Intro Experience</span>
                    <span className="setting-desc">
                      Replay the 5–6s futuristic 3D logo opening sequence.
                    </span>
                  </div>
                  <button
                    type="button"
                    className="settings-action-btn"
                    onClick={onReplayIntro}
                  >
                    <Sparkles size={14} />
                    <span>Replay 3D Intro</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 6. NOTIFICATIONS SECTION */}
          {activeTab === 'notifications' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Notification Preferences</h3>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Practice Velocity Reminders</span>
                    <span className="setting-desc">
                      Prompt periodic mock interviews to maintain technical readiness.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.notifications.sessionReminders}
                      onChange={(e) =>
                        updateSectionSetting('notifications', 'sessionReminders', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Report Evaluation Alerts</span>
                    <span className="setting-desc">
                      Notification banner when multi-dimensional report synthesis concludes.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.notifications.reportReadyAlerts}
                      onChange={(e) =>
                        updateSectionSetting('notifications', 'reportReadyAlerts', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Milestone Progression Updates</span>
                    <span className="setting-desc">
                      Notify on score index advancement and competency growth.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.notifications.progressMilestones}
                      onChange={(e) =>
                        updateSectionSetting('notifications', 'progressMilestones', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* 7. PRIVACY & DATA SECTION */}
          {activeTab === 'privacy' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Data Privacy & Local Storage</h3>
                </div>

                {clearedNotice && (
                  <div className="profile-alert success-alert">
                    <CheckCircle2 size={15} />
                    <span>Local session cache and report history cleared.</span>
                  </div>
                )}

                {exportedNotice && (
                  <div className="profile-alert success-alert">
                    <CheckCircle2 size={15} />
                    <span>Candidate data exported to JSON file.</span>
                  </div>
                )}

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Save Practice Session History</span>
                    <span className="setting-desc">
                      Retain past evaluation scorecards in local storage for timeline analytics.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.privacy.saveSessionHistory}
                      onChange={(e) =>
                        updateSectionSetting('privacy', 'saveSessionHistory', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Download My Data</span>
                    <span className="setting-desc">
                      Export your profile, preferences, and interview history to a JSON file.
                    </span>
                  </div>
                  <button
                    type="button"
                    className="settings-action-btn"
                    onClick={handleExportData}
                  >
                    <Download size={14} />
                    <span>Export JSON</span>
                  </button>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Clear Practice Cache & History</span>
                    <span className="setting-desc">
                      Permanently wipe all locally saved interview sessions and cached scorecards.
                    </span>
                  </div>
                  <button
                    type="button"
                    className="settings-action-btn danger-btn"
                    onClick={handleClearCache}
                  >
                    <Trash2 size={14} />
                    <span>Clear Cache</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 8. ACCESSIBILITY SECTION */}
          {activeTab === 'accessibility' && (
            <div className="settings-card-group">
              <div className="settings-card">
                <div className="card-header-simple">
                  <h3 className="card-title">Accessibility & Interaction</h3>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">High Contrast Mode</span>
                    <span className="setting-desc">
                      Enhance border contrast and typography clarity for low-visibility environments.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.accessibility.highContrast}
                      onChange={(e) =>
                        updateSectionSetting('accessibility', 'highContrast', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>

                <div className="setting-row">
                  <div className="setting-info">
                    <span className="setting-label">Larger Typography</span>
                    <span className="setting-desc">
                      Scale question prompts and text labels up by +2px across the interface.
                    </span>
                  </div>
                  <label className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={settings.accessibility.largerText}
                      onChange={(e) =>
                        updateSectionSetting('accessibility', 'largerText', e.target.checked)
                      }
                    />
                    <span className="toggle-switch-slider" />
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* 9. ABOUT AROVIA SECTION */}
          {activeTab === 'about' && (
            <div className="settings-card-group">
              <div className="settings-card about-card">
                <div className="about-brand-center">
                  <AroviaLogo variant="full" size={48} />
                </div>

                <div className="about-details-list">
                  <div className="about-detail-row">
                    <span className="about-label">Platform Version</span>
                    <span className="about-val">v1.2.0 (Build 2026.08)</span>
                  </div>
                  <div className="about-detail-row">
                    <span className="about-label">Evaluation Engine</span>
                    <span className="about-val text-cyan">Google Gemini 2.0 Flash</span>
                  </div>
                  <div className="about-detail-row">
                    <span className="about-label">Speech Protocol</span>
                    <span className="about-val">Web Speech API (Zero Latency)</span>
                  </div>
                  <div className="about-detail-row">
                    <span className="about-label">Architecture</span>
                    <span className="about-val">FastAPI + React + PostgreSQL</span>
                  </div>
                </div>

                <div className="about-footer-links">
                  <button
                    type="button"
                    className="about-link-btn"
                    onClick={() => onNavigate?.('help')}
                  >
                    <span>Help & Support Guide</span>
                    <ExternalLink size={13} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default SettingsView;

import React, { useState, useEffect } from 'react';
import {
  User,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  Globe,
  Link2,
  FileText,
  CheckCircle2,
  Edit3,
  Save,
  X,
  Loader2,
  AlertCircle,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { api } from '../../services/api';

/**
 * Full-Featured Candidate Profile Component.
 * Supports complete in-place editing, field validation, API/LocalStorage persistence,
 * and clear separation of Personal Information from Parsed Resume Context.
 */
export function ProfileView({ onStartSetup }) {
  const defaultProfile = {
    full_name: '',
    email: '',
    phone: '',
    location: '',
    target_role: '',
    experience_level: 'senior',
    bio: '',
    linkedin_url: '',
    github_url: '',
  };

  const [profile, setProfile] = useState(defaultProfile);
  const [initialProfile, setInitialProfile] = useState(defaultProfile);
  const [resume, setResume] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Load profile from API and LocalStorage on mount
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);

        // 1. Try to load user profile from backend
        let fetchedUser = null;
        try {
          fetchedUser = await api.getProfile();
        } catch {
          // Unauthenticated / guest session
        }

        // 2. Check local persistence
        let savedLocal = null;
        try {
          const localStr = localStorage.getItem('arovia_candidate_profile');
          if (localStr) {
            savedLocal = JSON.parse(localStr);
          }
        } catch {
          // ignore
        }

        // Merge saved data prioritising local user customizations
        const merged = {
          ...defaultProfile,
          ...(fetchedUser ? {
            full_name: fetchedUser.full_name || defaultProfile.full_name,
            email: fetchedUser.email || defaultProfile.email,
            target_role: fetchedUser.target_role || defaultProfile.target_role,
            experience_level: fetchedUser.experience_level || defaultProfile.experience_level,
            bio: fetchedUser.bio || defaultProfile.bio,
          } : {}),
          ...(savedLocal || {}),
        };

        setProfile(merged);
        setInitialProfile(merged);

        // 3. Load resume context separately
        try {
          const res = await api.getMyResume();
          if (res && res.id) {
            setResume(res);
          } else {
            setResume(null);
          }
        } catch {
          setResume(null);
        }
      } catch (err) {
        console.warn('Profile load warning:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // Field validation rules
  const validate = (dataToValidate = profile) => {
    const newErrors = {};

    // Name validation
    if (!dataToValidate.full_name || !dataToValidate.full_name.trim()) {
      newErrors.full_name = 'Full name is required.';
    } else if (dataToValidate.full_name.trim().length < 2) {
      newErrors.full_name = 'Name must be at least 2 characters.';
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!dataToValidate.email || !dataToValidate.email.trim()) {
      newErrors.email = 'Email address is required.';
    } else if (!emailRegex.test(dataToValidate.email.trim())) {
      newErrors.email = 'Please enter a valid email address.';
    }

    // Phone validation (if provided)
    if (dataToValidate.phone && dataToValidate.phone.trim()) {
      const cleaned = dataToValidate.phone.replace(/[\s\(\)\-\.]/g, '');
      if (cleaned.length < 7 || !/^[\+]?[0-9]+$/.test(cleaned)) {
        newErrors.phone = 'Please enter a valid phone number (min 7 digits).';
      }
    }

    // LinkedIn URL validation (if provided)
    if (dataToValidate.linkedin_url && dataToValidate.linkedin_url.trim()) {
      const val = dataToValidate.linkedin_url.trim();
      if (!val.startsWith('http://') && !val.startsWith('https://') && !val.includes('linkedin.com')) {
        newErrors.linkedin_url = 'Please enter a valid LinkedIn URL.';
      }
    }

    // GitHub URL validation (if provided)
    if (dataToValidate.github_url && dataToValidate.github_url.trim()) {
      const val = dataToValidate.github_url.trim();
      if (!val.startsWith('http://') && !val.startsWith('https://') && !val.includes('github.com')) {
        newErrors.github_url = 'Please enter a valid GitHub URL.';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field, value) => {
    const updated = { ...profile, [field]: value };
    setProfile(updated);

    // Clear inline error on change
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  const handleStartEdit = () => {
    setIsEditing(true);
    setSuccessMessage(null);
    setErrorMessage(null);
    setErrors({});
  };

  const handleCancel = () => {
    setProfile(initialProfile);
    setErrors({});
    setIsEditing(false);
    setErrorMessage(null);
  };

  const handleSave = async (e) => {
    e?.preventDefault();

    if (!validate(profile)) {
      setErrorMessage('Please resolve the validation errors before saving.');
      return;
    }

    try {
      setSaving(true);
      setErrorMessage(null);

      // 1. Try to sync to backend if authenticated
      try {
        await api.updateProfile({
          full_name: profile.full_name.trim(),
          target_role: profile.target_role.trim(),
          experience_level: profile.experience_level,
          bio: profile.bio?.trim() || null,
        });
      } catch (backendErr) {
        // Backend update may fail if unauthenticated; continue to local persistence
        console.info('Backend profile sync note:', backendErr?.message);
      }

      // 2. Persist locally for seamless refresh & reload retention
      localStorage.setItem('arovia_candidate_profile', JSON.stringify(profile));
      setInitialProfile(profile);
      setIsEditing(false);
      setSuccessMessage('Profile updated successfully.');

      setTimeout(() => {
        setSuccessMessage(null);
      }, 4000);
    } catch (err) {
      setErrorMessage(err?.message || 'Could not save profile changes.');
    } finally {
      setSaving(false);
    }
  };

  const getInitials = (name) => {
    if (!name) return 'AR';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  if (loading) {
    return (
      <div className="profile-loading-container">
        <Loader2 size={36} className="animate-spin text-primary" />
        <p className="loading-text">Loading candidate profile & credentials...</p>
      </div>
    );
  }

  return (
    <div className="arovia-profile-layout">
      {/* Top Banner & Actions */}
      <div className="profile-header-banner">
        <div className="banner-text">
          <span className="banner-subtitle">CANDIDATE IDENTITY & CAREER METRICS</span>
          <h1 className="banner-title">Candidate Profile</h1>
          <p className="banner-desc">
            Manage your personal contact information, target seniority level, and contextual resume record.
          </p>
        </div>

        <div className="profile-header-actions">
          {isEditing ? (
            <div className="edit-actions-group">
              <button
                type="button"
                className="profile-btn secondary-btn"
                onClick={handleCancel}
                disabled={saving}
              >
                <X size={15} />
                <span>Cancel</span>
              </button>

              <button
                type="button"
                className="profile-btn primary-save-btn"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save size={15} />
                    <span>Save Changes</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="view-actions-group">
              <button
                type="button"
                className="profile-btn edit-trigger-btn"
                onClick={handleStartEdit}
              >
                <Edit3 size={15} />
                <span>Edit Profile</span>
              </button>

              <button
                type="button"
                className="profile-btn new-session-btn"
                onClick={onStartSetup}
              >
                <Sparkles size={15} />
                <span>New Interview</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Notifications / Alerts */}
      {successMessage && (
        <div className="profile-alert success-alert">
          <CheckCircle2 size={16} />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="profile-alert error-alert">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Hero Header Card */}
      <div className="profile-card profile-hero-card">
        <div className="hero-avatar-wrapper">
          <div className="profile-avatar-large">
            <span>{getInitials(profile.full_name)}</span>
          </div>
        </div>

        <div className="hero-details-wrapper">
          <div className="hero-title-row">
            <h2 className="hero-candidate-name">{profile.full_name}</h2>
            <span className="hero-tier-badge">PREMIUM EVALUATION TIER</span>
          </div>

          <div className="hero-meta-badges-row">
            <span className="hero-meta-badge">
              <Briefcase size={13} />
              {profile.target_role || 'Target Role Not Specified'}
            </span>
            <span className="hero-meta-badge">
              <MapPin size={13} />
              {profile.location || 'Location Not Specified'}
            </span>
            <span className="hero-meta-badge">
              <Mail size={13} />
              {profile.email}
            </span>
          </div>

          <p className="hero-bio-quote">
            &ldquo;{profile.bio || 'No professional bio provided yet. Click Edit Profile to add your summary.'}&rdquo;
          </p>
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div className="profile-sections-grid">
        {/* LEFT COLUMN: Personal, Professional & Links */}
        <div className="profile-main-column">
          {/* Card 1: Personal & Contact Information */}
          <div className="profile-card section-card">
            <div className="card-header-simple">
              <div className="title-with-icon">
                <User size={17} className="text-secondary" />
                <h3 className="card-title">Personal Information</h3>
              </div>
            </div>

            <div className="fields-form-grid">
              {/* Full Name */}
              <div className="form-field-group">
                <label className="field-label">FULL NAME *</label>
                {isEditing ? (
                  <>
                    <input
                      type="text"
                      className={`profile-text-input ${errors.full_name ? 'error' : ''}`}
                      value={profile.full_name}
                      onChange={(e) => handleInputChange('full_name', e.target.value)}
                      placeholder="Enter your full name"
                    />
                    {errors.full_name && <span className="field-error-text">{errors.full_name}</span>}
                  </>
                ) : (
                  <div className="static-field-value">{profile.full_name}</div>
                )}
              </div>

              {/* Email Address */}
              <div className="form-field-group">
                <label className="field-label">EMAIL ADDRESS *</label>
                {isEditing ? (
                  <>
                    <input
                      type="email"
                      className={`profile-text-input ${errors.email ? 'error' : ''}`}
                      value={profile.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      placeholder="e.g. alex.thorne@example.com"
                    />
                    {errors.email && <span className="field-error-text">{errors.email}</span>}
                  </>
                ) : (
                  <div className="static-field-value">{profile.email}</div>
                )}
              </div>

              {/* Phone Number */}
              <div className="form-field-group">
                <label className="field-label">PHONE NUMBER</label>
                {isEditing ? (
                  <>
                    <input
                      type="tel"
                      className={`profile-text-input ${errors.phone ? 'error' : ''}`}
                      value={profile.phone}
                      onChange={(e) => handleInputChange('phone', e.target.value)}
                      placeholder="e.g. +1 (555) 234-5678"
                    />
                    {errors.phone && <span className="field-error-text">{errors.phone}</span>}
                  </>
                ) : (
                  <div className="static-field-value">{profile.phone || 'Not provided'}</div>
                )}
              </div>

              {/* Location */}
              <div className="form-field-group">
                <label className="field-label">LOCATION</label>
                {isEditing ? (
                  <input
                    type="text"
                    className="profile-text-input"
                    value={profile.location}
                    onChange={(e) => handleInputChange('location', e.target.value)}
                    placeholder="e.g. San Francisco, CA"
                  />
                ) : (
                  <div className="static-field-value">{profile.location || 'Not provided'}</div>
                )}
              </div>
            </div>
          </div>

          {/* Card 2: Professional Details */}
          <div className="profile-card section-card">
            <div className="card-header-simple">
              <div className="title-with-icon">
                <Briefcase size={17} className="text-secondary" />
                <h3 className="card-title">Professional Information</h3>
              </div>
            </div>

            <div className="fields-form-grid">
              {/* Target Role */}
              <div className="form-field-group">
                <label className="field-label">CURRENT / TARGET ROLE</label>
                {isEditing ? (
                  <input
                    type="text"
                    className="profile-text-input"
                    value={profile.target_role}
                    onChange={(e) => handleInputChange('target_role', e.target.value)}
                    placeholder="e.g. Senior Systems Engineer"
                  />
                ) : (
                  <div className="static-field-value">{profile.target_role || 'Not specified'}</div>
                )}
              </div>

              {/* Seniority Track */}
              <div className="form-field-group">
                <label className="field-label">SENIORITY CALIBRATION</label>
                {isEditing ? (
                  <select
                    className="profile-select-input"
                    value={profile.experience_level}
                    onChange={(e) => handleInputChange('experience_level', e.target.value)}
                  >
                    <option value="junior">Junior (0-2 years)</option>
                    <option value="mid">Mid-Level (3-5 years)</option>
                    <option value="senior">Senior (5-8 years)</option>
                    <option value="lead">Staff / Principal (8+ years)</option>
                  </select>
                ) : (
                  <div className="static-field-value capitalize">
                    {profile.experience_level === 'lead'
                      ? 'Staff / Principal (8+ years)'
                      : `${profile.experience_level || 'senior'} Level`}
                  </div>
                )}
              </div>

              {/* Bio / About */}
              <div className="form-field-group full-width">
                <label className="field-label">SHORT BIO / PROFESSIONAL SUMMARY</label>
                {isEditing ? (
                  <textarea
                    rows={4}
                    className="profile-textarea-input"
                    value={profile.bio}
                    onChange={(e) => handleInputChange('bio', e.target.value)}
                    placeholder="Summarize your engineering background, key frameworks, and core domain strengths..."
                  />
                ) : (
                  <div className="static-field-value bio-block">
                    {profile.bio || 'No professional bio provided yet.'}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Card 3: Online Profiles & Portfolios */}
          <div className="profile-card section-card">
            <div className="card-header-simple">
              <div className="title-with-icon">
                <Globe size={17} className="text-secondary" />
                <h3 className="card-title">Profiles & Social Links</h3>
              </div>
            </div>

            <div className="fields-form-grid">
              {/* LinkedIn */}
              <div className="form-field-group">
                <label className="field-label">
                  <Link2 size={12} className="inline-icon" /> LINKEDIN PROFILE
                </label>
                {isEditing ? (
                  <>
                    <input
                      type="url"
                      className={`profile-text-input ${errors.linkedin_url ? 'error' : ''}`}
                      value={profile.linkedin_url}
                      onChange={(e) => handleInputChange('linkedin_url', e.target.value)}
                      placeholder="https://linkedin.com/in/username"
                    />
                    {errors.linkedin_url && (
                      <span className="field-error-text">{errors.linkedin_url}</span>
                    )}
                  </>
                ) : profile.linkedin_url ? (
                  <a
                    href={profile.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="link-field-value"
                  >
                    <span>{profile.linkedin_url}</span>
                    <ExternalLink size={12} />
                  </a>
                ) : (
                  <div className="static-field-value text-muted">Not linked</div>
                )}
              </div>

              {/* GitHub */}
              <div className="form-field-group">
                <label className="field-label">
                  <Link2 size={12} className="inline-icon" /> GITHUB PROFILE
                </label>
                {isEditing ? (
                  <>
                    <input
                      type="url"
                      className={`profile-text-input ${errors.github_url ? 'error' : ''}`}
                      value={profile.github_url}
                      onChange={(e) => handleInputChange('github_url', e.target.value)}
                      placeholder="https://github.com/username"
                    />
                    {errors.github_url && (
                      <span className="field-error-text">{errors.github_url}</span>
                    )}
                  </>
                ) : profile.github_url ? (
                  <a
                    href={profile.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="link-field-value"
                  >
                    <span>{profile.github_url}</span>
                    <ExternalLink size={12} />
                  </a>
                ) : (
                  <div className="static-field-value text-muted">Not linked</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Contextual Resume Record (Independent) */}
        <div className="profile-side-column">
          <div className="profile-card resume-context-card">
            <div className="card-header-simple">
              <div className="title-with-icon">
                <FileText size={17} className="text-secondary" />
                <h3 className="card-title">Resume / Context</h3>
              </div>
              <span className="context-badge">AI Grounding Record</span>
            </div>

            <p className="resume-context-helper">
              Parsed from your uploaded resume. This data is used by the AI engine to generate
              personalized, experience-grounded interview questions.
            </p>

            {resume ? (
              <div className="resume-parsed-content">
                <div className="resume-file-info-badge">
                  <FileText size={22} className="text-primary" />
                  <div className="file-text-meta">
                    <span className="file-name">{resume.filename}</span>
                    <span className="file-status">
                      {resume.size_mb ? `${resume.size_mb} MB • ` : ''}Active Ingestion Ready
                    </span>
                  </div>
                </div>

                {resume.skills && resume.skills.length > 0 && (
                  <div className="skills-tags-section">
                    <label className="field-label">EXTRACTED TECHNICAL SKILLS</label>
                    <div className="skills-pill-grid">
                      {resume.skills.map((skill, i) => (
                        <span key={i} className="skill-pill">
                          <CheckCircle2 size={11} className="text-success" />
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {resume.summary && (
                  <div className="resume-summary-box">
                    <label className="field-label">EXPERIENCE SUMMARY</label>
                    <p className="summary-text-block">{resume.summary}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="no-resume-prompt">
                <FileText size={32} className="text-muted" />
                <p className="prompt-title">No Resume Uploaded Yet</p>
                <p className="prompt-desc">
                  Upload your resume during session setup to ground AI interview questions in your
                  real-world engineering track.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileView;

import React, { useState } from 'react';
import { FileText, Upload, CheckCircle2, AlertCircle, Trash2, Sparkles, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';

/**
 * Resume and Career Profile Status Widget.
 */
export function ResumeProfileCard({ resume, onResumeUpdated }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (5MB) & type
    if (file.size > 5 * 1024 * 1024) {
      setError('File exceeds 5MB limit. Please upload a smaller PDF/DOCX resume.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setSuccess(null);

      const response = await api.uploadResume(file);
      setSuccess('Resume successfully parsed and calibrated!');
      if (onResumeUpdated) {
        onResumeUpdated(response.resume);
      }
    } catch (err) {
      setError(err.message || 'Failed to upload and parse resume.');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteResume = async () => {
    try {
      setUploading(true);
      await api.deleteResume();
      if (onResumeUpdated) onResumeUpdated(null);
      setSuccess('Resume removed.');
    } catch (err) {
      setError(err.message || 'Failed to delete resume.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="resume-card">
      <div className="resume-card-header">
        <div className="resume-icon-box">
          <FileText size={20} className="text-cyan" />
        </div>
        <div>
          <h3 className="resume-title">Candidate Profile & Resume</h3>
          <p className="resume-subtitle">Calibrates AI interviewer questioning to your actual projects & background</p>
        </div>
      </div>

      {error && (
        <div className="badge badge-danger alert-badge">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="badge badge-success alert-badge">
          <CheckCircle2 size={14} />
          <span>{success}</span>
        </div>
      )}

      {resume ? (
        <div className="resume-details">
          <div className="resume-status-row">
            <div className="resume-file-info">
              <CheckCircle2 size={16} className="text-emerald" />
              <span className="file-name">{resume.filename || 'Active Resume (.pdf)'}</span>
            </div>
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleDeleteResume}
              disabled={uploading}
              title="Remove resume"
            >
              <Trash2 size={14} />
              <span>Remove</span>
            </button>
          </div>

          {resume.extracted_skills && resume.extracted_skills.length > 0 && (
            <div className="resume-skills-block">
              <span className="block-label">Extracted Core Competencies:</span>
              <div className="skills-cloud">
                {resume.extracted_skills.slice(0, 8).map((skill, idx) => (
                  <span key={idx} className="extracted-skill-pill">
                    {skill}
                  </span>
                ))}
                {resume.extracted_skills.length > 8 && (
                  <span className="extracted-skill-more">
                    +{resume.extracted_skills.length - 8} more
                  </span>
                )}
              </div>
            </div>
          )}

          <div className="resume-reupload-row">
            <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
              <RefreshCw size={14} />
              <span>{uploading ? 'Processing...' : 'Upload Updated Version'}</span>
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={handleFileUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>
      ) : (
        <div className="resume-upload-dropzone">
          <Upload size={32} className="dropzone-icon" />
          <p className="dropzone-prompt">
            <strong>Click to upload</strong> or drag & drop candidate resume
          </p>
          <span className="dropzone-hint">PDF or DOCX format (Max 5MB)</span>

          <label className="btn btn-primary btn-sm dropzone-btn" style={{ cursor: 'pointer', marginTop: '0.75rem' }}>
            <Sparkles size={14} />
            <span>{uploading ? 'Parsing with Gemini...' : 'Choose Resume Document'}</span>
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
          </label>
        </div>
      )}
    </div>
  );
}

export default ResumeProfileCard;

import React, { useEffect, useState, useCallback } from 'react';
import {
  ArrowLeft,
  Loader2,
  RotateCcw,
  Sparkles,
  Printer,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import RadarChart from './RadarChart';
import StrengthsImprovements from './StrengthsImprovements';
import TurnAccordion from './TurnAccordion';
import PDFExportButton from './PDFExportButton';

/**
 * 1:1 Performance Report Card matching Figma specifications across Desktop, Tablet, and Mobile.
 * Restrained analytical layout with 50/50 grids and clean progress styling.
 * Consumes real backend evaluation data without fallback fake scores or mock personas.
 */
export function ReportCard({ sessionId, onRetake, onBack, onOpenCoach }) {
  const [loading, setLoading] = useState(true);
  const [evaluationData, setEvaluationData] = useState(null);
  const [error, setError] = useState(null);

  const getCandidateName = () => {
    try {
      const savedProfile = localStorage.getItem('arovia_candidate_profile');
      if (savedProfile) {
        const parsed = JSON.parse(savedProfile);
        if (parsed?.full_name && parsed.full_name.trim()) {
          return parsed.full_name.trim();
        }
      }
    } catch {
      // ignore
    }
    return 'Candidate';
  };

  const loadReport = useCallback(async () => {
    if (!sessionId) {
      setLoading(false);
      setError('No session identifier was provided.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await api.getSessionEvaluation(sessionId);

      if (!data) {
        throw new Error('Empty evaluation response received from the server.');
      }

      setEvaluationData(data);

      // Update local session history entry with real scores and data
      try {
        const raw = localStorage.getItem('arovia_recent_sessions');
        const list = raw ? JSON.parse(raw) : [];
        const index = list.findIndex(
          (item) => item && (item.session_id || item.id) === sessionId
        );
        const updatedEntry = {
          id: sessionId,
          session_id: sessionId,
          target_role: data.target_role || 'Technical Interview Session',
          seniority_level: data.seniority_level || 'senior',
          interview_focus: data.interview_focus || 'Technical Core',
          practice_mode: data.practice_mode || 'standard',
          overall_score:
            data.overall_score !== undefined ? data.overall_score : null,
          completed_at: data.completed_at || new Date().toISOString(),
          status: 'completed',
        };
        let newList;
        if (index >= 0) {
          newList = [...list];
          newList[index] = { ...newList[index], ...updatedEntry };
        } else {
          newList = [updatedEntry, ...list].slice(0, 20);
        }
        localStorage.setItem('arovia_recent_sessions', JSON.stringify(newList));
        window.dispatchEvent(new CustomEvent('arovia_sessions_updated'));
      } catch {
        // ignore
      }
    } catch (err) {
      console.error('Failed to load session evaluation:', err);
      setEvaluationData(null);
      setError(err?.message || 'The evaluation could not be loaded from the server.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  if (loading) {
    return (
      <div className="report-loading-container">
        <Loader2 size={36} className="animate-spin text-primary" />
        <h3 className="loading-title">Synthesizing Performance Evaluation...</h3>
        <p className="loading-subtext">Calibrating 5 dimensions & benchmark gap analysis.</p>
      </div>
    );
  }

  if (error || !evaluationData) {
    return (
      <div className="arovia-report-page-layout">
        <div
          className="report-error-card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '380px',
            textAlign: 'center',
            padding: 'var(--space-2xl) var(--space-lg)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            margin: 'var(--space-2xl) auto',
            maxWidth: '560px',
          }}
        >
          <AlertCircle
            size={42}
            className="text-warning"
            style={{ marginBottom: 'var(--space-md)' }}
          />
          <h2
            style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: 'var(--space-xs)',
            }}
          >
            Unable to load evaluation
          </h2>
          <p
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)',
              marginBottom: 'var(--space-xl)',
              maxWidth: '420px',
              lineHeight: 1.6,
            }}
          >
            {error || 'The evaluation could not be loaded from the server.'}
          </p>
          <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
            <button
              type="button"
              className="footer-btn secondary"
              onClick={onBack}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-xs)' }}
            >
              <ArrowLeft size={15} />
              <span>Back to Dashboard</span>
            </button>
            <button
              type="button"
              className="footer-btn primary-cta"
              onClick={loadReport}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-xs)' }}
            >
              <RotateCcw size={15} />
              <span>Retry</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const candidateName = getCandidateName();
  const score = evaluationData.overall_score ?? 0;
  const dimensions = evaluationData.dimension_scores || {};
  const targetRole = evaluationData.target_role || 'Technical Assessment';
  const seniorityLevel = evaluationData.seniority_level || 'senior';
  const completedAt = evaluationData.completed_at || evaluationData.started_at;
  const executiveSummary = evaluationData.executive_summary || 'Evaluation summary generated.';
  const topStrengths = Array.isArray(evaluationData.top_strengths) ? evaluationData.top_strengths : [];
  const topImprovements = Array.isArray(evaluationData.top_improvements) ? evaluationData.top_improvements : [];
  const turnsEvaluation = Array.isArray(evaluationData.turns_evaluation) ? evaluationData.turns_evaluation : [];

  const getVerdict = (val) => {
    if (val >= 85) return { title: 'Expert', badge: 'HIGHLY RECOMMENDED' };
    if (val >= 70) return { title: 'Proficient', badge: 'RECOMMENDED' };
    if (val >= 55) return { title: 'Developing', badge: 'CALIBRATION REQUIRED' };
    return { title: 'Needs Improvement', badge: 'ADDITIONAL PRACTICE NEEDED' };
  };
  const verdict = getVerdict(score);

  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;

  return (
    <div className="arovia-report-page-layout">
      {/* Top Action Nav Bar */}
      <div className="report-action-header">
        <div className="action-header-left">
          <span className="report-eyebrow">INTERVIEW PERFORMANCE REPORT</span>
          <h1 className="report-title">{candidateName}</h1>
          <div className="report-meta-tags">
            <span className="meta-pill">{targetRole}</span>
            <span className="meta-pill">
              {completedAt
                ? new Date(completedAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })
                : 'Recent'}
            </span>
            <span className="verified-badge">
              <CheckCircle2 size={13} className="text-secondary" />
              Verified by AROVIA Intelligence
            </span>
          </div>
        </div>

        <div className="action-header-right">
          {onOpenCoach && (
            <button
              type="button"
              className="footer-btn primary-cta"
              style={{ padding: '8px 16px', fontSize: '13px' }}
              onClick={() => onOpenCoach(sessionId)}
            >
              <Sparkles size={15} />
              <span>Debrief with AI Coach</span>
            </button>
          )}
          <PDFExportButton
            targetRole={targetRole}
            sessionId={sessionId}
            containerId="arovia-printable-report"
          />
        </div>
      </div>

      {/* Main Printable / Visible Report Container */}
      <div id="arovia-printable-report" className="report-document-body">
        {/* ROW 1: Score Dial (Left) & Executive Summary (Right) */}
        <div className="report-hero-grid">
          {/* Circular Score Gauge Card */}
          <div className="report-card score-dial-card">
            <div className="circular-score-wrapper">
              <svg className="report-gauge-svg" width="110" height="110" viewBox="0 0 110 110">
                <circle
                  className="gauge-track"
                  cx="55"
                  cy="55"
                  r={radius}
                  strokeWidth="8"
                />
                <circle
                  className="gauge-fill-ring"
                  cx="55"
                  cy="55"
                  r={radius}
                  strokeWidth="8"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="gauge-score-value">
                <span className="score-num">{score}</span>
                <span className="score-den">/100</span>
              </div>
            </div>

            <div className="score-verdict-box">
              <h3 className="verdict-title">{verdict.title}</h3>
              <span className="verdict-badge">{verdict.badge}</span>
            </div>
          </div>

          {/* Executive Summary Card */}
          <div className="report-card executive-summary-card">
            <div className="card-header-line">
              <Sparkles size={16} className="text-secondary" />
              <h3 className="card-title">Executive Summary</h3>
            </div>
            <p className="summary-paragraph">{executiveSummary}</p>
          </div>
        </div>

        {/* ROW 2: Performance Dimensions (50%) & Radar Chart (50%) */}
        <div className="report-analytics-grid">
          {/* Performance Dimensions Progress Bars */}
          <div className="report-card dimensions-bars-card">
            <div className="card-header-line">
              <h4 className="card-title">Performance Dimensions</h4>
            </div>

            <div className="dimension-bar-items-list">
              {Object.keys(dimensions).length > 0 ? (
                Object.entries(dimensions).map(([key, val]) => (
                  <div key={key} className="dimension-row-item">
                    <div className="dimension-label-row">
                      <span className="dimension-name">
                        {key.charAt(0).toUpperCase() + key.slice(1)}
                      </span>
                      <span className="dimension-score-pct">{val}/100</span>
                    </div>
                    <div className="dimension-track">
                      <div
                        className="dimension-fill"
                        style={{ width: `${Math.max(0, Math.min(100, val))}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <p className="no-data-text">Dimensions being calibrated.</p>
              )}
            </div>
          </div>

          {/* Radar Chart */}
          <div className="report-card radar-mapping-card">
            <RadarChart
              dimensionScores={dimensions}
              seniorityLevel={seniorityLevel}
              size={280}
            />
          </div>
        </div>

        {/* ROW 3: Strengths & Growth Areas (50/50 Split) */}
        <StrengthsImprovements
          topStrengths={topStrengths}
          topImprovements={topImprovements}
        />

        {/* ROW 4: Turn-by-Turn Detailed Review */}
        <TurnAccordion turnsEvaluation={turnsEvaluation} />
      </div>

      {/* Footer Navigation Action Bar */}
      <div className="report-footer-actions">
        <button type="button" className="footer-btn secondary" onClick={onBack}>
          <ArrowLeft size={15} />
          <span>Back to Dashboard</span>
        </button>

        {onOpenCoach && (
          <button
            type="button"
            className="footer-btn primary-cta"
            onClick={() => onOpenCoach(sessionId)}
          >
            <Sparkles size={15} />
            <span>Debrief with AI Coach</span>
          </button>
        )}

        <button type="button" className="footer-btn secondary" onClick={() => window.print()}>
          <Printer size={15} />
          <span>Print</span>
        </button>

        <PDFExportButton
          targetRole={targetRole}
          sessionId={sessionId}
          containerId="arovia-printable-report"
        />

        <button type="button" className="footer-btn secondary" onClick={onRetake}>
          <RotateCcw size={15} />
          <span>Start New Interview</span>
        </button>
      </div>
    </div>
  );
}

export default ReportCard;

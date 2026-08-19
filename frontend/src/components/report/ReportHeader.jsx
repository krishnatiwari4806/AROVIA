import React from "react";
import { Award, Briefcase, Calendar, Clock, Sparkles } from "lucide-react";
import { getCompetencyTier } from "../../utils/competencyRubric";

/**
 * Report Card Header with Overall Score Radial Gauge, Competency Badge & Executive Summary.
 */
export default function ReportHeader({ evaluationData }) {
  if (!evaluationData) return null;

  const {
    target_role,
    seniority_level,
    interview_focus,
    practice_mode,
    overall_score = 0,
    executive_summary,
    completed_at,
  } = evaluationData;

  const tier = getCompetencyTier(overall_score);

  const formattedDate = completed_at
    ? new Date(completed_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : new Date().toLocaleDateString();

  // Radial Score Ring Calculation
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (overall_score / 100) * circumference;

  return (
    <div className="report-header-card">
      <div className="report-header-top">
        <div className="report-title-section">
          <div className="report-badge-row">
            <span className="platform-tag">AROVIA Evaluation Report</span>
            <span
              className="tier-badge"
              style={{
                backgroundColor: tier.bgAlpha,
                borderColor: tier.borderAlpha,
                color: tier.color,
              }}
            >
              <Sparkles size={14} className="badge-icon" />
              {tier.title}
            </span>
          </div>

          <h1 className="report-candidate-role">
            {target_role}{" "}
            <span className="seniority-pill">({seniority_level?.toUpperCase()})</span>
          </h1>

          <div className="report-meta-grid">
            <div className="meta-item">
              <Briefcase size={15} className="meta-icon" />
              <span>{interview_focus} Focus</span>
            </div>
            <div className="meta-item">
              <Clock size={15} className="meta-icon" />
              <span>{practice_mode === "quick" ? "Quick Practice (3 Qs)" : "Full Mock (6 Qs)"}</span>
            </div>
            <div className="meta-item">
              <Calendar size={15} className="meta-icon" />
              <span>{formattedDate}</span>
            </div>
          </div>
        </div>

        {/* Overall Score Radial Ring Gauge */}
        <div className="overall-score-gauge-box">
          <div className="radial-score-wrapper">
            <svg viewBox="0 0 120 120" className="radial-score-svg">
              <circle
                cx="60"
                cy="60"
                r={radius}
                className="radial-bg-ring"
                strokeWidth="10"
              />
              <circle
                cx="60"
                cy="60"
                r={radius}
                className="radial-fill-ring"
                stroke={tier.color}
                strokeWidth="10"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
              />
            </svg>
            <div className="radial-score-center">
              <span className="score-number" style={{ color: tier.color }}>
                {overall_score}
              </span>
              <span className="score-max">/ 100</span>
            </div>
          </div>
          <span className="score-caption">Composite Score</span>
        </div>
      </div>

      {/* Executive Summary Callout */}
      {executive_summary && (
        <div className="executive-summary-banner">
          <div className="summary-banner-header">
            <Award size={18} className="summary-icon" />
            <span className="summary-title">Executive Performance Summary</span>
          </div>
          <p className="summary-text">{executive_summary}</p>
        </div>
      )}
    </div>
  );
}

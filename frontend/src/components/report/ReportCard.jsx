import React, { useEffect, useState } from "react";
import { AlertCircle, ArrowLeft, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { api } from "../../services/api";
import MetricBarList from "./MetricBar";
import PDFExportButton from "./PDFExportButton";
import RadarChart from "./RadarChart";
import ReportHeader from "./ReportHeader";
import StrengthsImprovements from "./StrengthsImprovements";
import TurnAccordion from "./TurnAccordion";

/**
 * Master Performance Report Card Container Component.
 *
 * @param {Object} props
 * @param {string} props.sessionId - Interview Session ID
 * @param {Function} [props.onRetake] - Callback to start a new interview
 * @param {Function} [props.onBack] - Callback to navigate back
 */
export default function ReportCard({ sessionId, onRetake, onBack }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [evaluationData, setEvaluationData] = useState(null);

  const fetchEvaluation = async () => {
    if (!sessionId) {
      setError("No session ID provided.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // First try to fetch existing or trigger evaluation
      const data = await api.getSessionEvaluation(sessionId);
      setEvaluationData(data);
    } catch (err) {
      console.error("Failed to load interview evaluation report:", err);
      setError(err.message || "Failed to load evaluation scorecard. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvaluation();
  }, [sessionId]);

  // Loading State
  if (loading) {
    return (
      <div className="card loading-card" style={{ minHeight: "450px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1rem" }}>
        <Loader2 size={42} className="spinner-icon" style={{ color: "var(--accent-primary)" }} />
        <div style={{ textAlign: "center" }}>
          <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "#fff", marginBottom: "0.25rem" }}>
            Synthesizing Multi-Dimensional Evaluation...
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Analyzing candidate responses, scoring 5 dimensions, and benchmarking ideal answers.
          </p>
        </div>
      </div>
    );
  }

  // Error State
  if (error || !evaluationData) {
    return (
      <div className="card error-card" style={{ minHeight: "350px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1rem", borderColor: "rgba(239, 68, 68, 0.4)" }}>
        <AlertCircle size={40} style={{ color: "var(--danger)" }} />
        <div style={{ textAlign: "center" }}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#fff", marginBottom: "0.25rem" }}>
            Evaluation Report Unavailable
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", maxWidth: "450px" }}>
            {error || "Unable to retrieve evaluation scorecard."}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
          <button onClick={fetchEvaluation} className="btn btn-primary">
            <RotateCcw size={16} />
            <span>Retry Evaluation</span>
          </button>
          {onBack && (
            <button onClick={onBack} className="btn btn-secondary">
              <ArrowLeft size={16} />
              <span>Back</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  const {
    target_role,
    seniority_level,
    dimension_scores = {},
    top_strengths = [],
    top_improvements = [],
    turns_evaluation = [],
  } = evaluationData;

  return (
    <div className="report-container">
      {/* Top Action Bar */}
      <div className="report-action-bar">
        <div className="action-btn-group">
          {onBack && (
            <button onClick={onBack} className="btn btn-secondary" title="Return to interview">
              <ArrowLeft size={16} />
              <span>Back</span>
            </button>
          )}
          {onRetake && (
            <button onClick={onRetake} className="btn btn-secondary" title="Start a fresh practice interview">
              <RotateCcw size={16} />
              <span>Start New Interview</span>
            </button>
          )}
        </div>

        {/* PDF Download and Print Buttons */}
        <PDFExportButton
          targetRole={target_role}
          sessionId={sessionId}
          containerId="report-card-container"
        />
      </div>

      {/* Printable / Capturable Report Card Body */}
      <div id="report-card-container" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {/* 1. Header & Overall Scorecard */}
        <ReportHeader evaluationData={evaluationData} />

        {/* 2. Visual Analytics Grid: Radar Chart + Metric Progress Bars */}
        <div className="analytics-grid">
          <RadarChart
            dimensionScores={dimension_scores}
            seniorityLevel={seniority_level}
            size={340}
          />
          <MetricBarList dimensionScores={dimension_scores} />
        </div>

        {/* 3. Strengths & Prioritized Actionable Improvements */}
        <StrengthsImprovements
          topStrengths={top_strengths}
          topImprovements={top_improvements}
        />

        {/* 4. Turn-by-Turn Q&A Detailed Breakdown */}
        <TurnAccordion turnsEvaluation={turns_evaluation} />
      </div>

      {/* Bottom Footer Actions */}
      <div className="report-action-bar" style={{ marginTop: "1rem", paddingTop: "1.5rem", borderTop: "1px solid var(--border-subtle)" }}>
        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          AROVIA Candidate Assessment & Self-Practice Engine • Zero Cost Platform
        </span>

        <PDFExportButton
          targetRole={target_role}
          sessionId={sessionId}
          containerId="report-card-container"
        />
      </div>
    </div>
  );
}

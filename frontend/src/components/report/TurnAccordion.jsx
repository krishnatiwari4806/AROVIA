import React, { useState } from "react";
import { Check, ChevronDown, ChevronUp, Clock, HelpCircle, MessageSquare, Mic, Sparkles, X } from "lucide-react";

/**
 * Collapsible Turn-by-Turn Question & Answer Breakdown Component.
 */
export function TurnCard({ turn, defaultExpanded = false }) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!turn) return null;

  const {
    turn_index = 0,
    question_type = "core",
    question_text = "",
    candidate_answer = "",
    ideal_answer = "",
    turn_duration_sec,
    turn_score = 0,
    relevance_score = 0,
    correctness_score = 0,
    keywords_score = 0,
    clarity_score = 0,
    confidence_score = 0,
    covered_concepts = [],
    missed_concepts = [],
    ideal_answer_comparison = "",
    turn_feedback = "",
  } = turn;

  const isFollowUp = question_type === "follow_up" || turn.is_follow_up;

  // Filler stats from evaluation data if present
  const fillerStats = turn.evaluation_data?.filler_word_stats || null;

  const getScoreColor = (val) => {
    if (val >= 85) return "#10b981";
    if (val >= 70) return "#3b82f6";
    if (val >= 50) return "#f59e0b";
    return "#f43f5e";
  };

  return (
    <div className={`turn-accordion-card ${isExpanded ? "expanded" : ""}`}>
      {/* Accordion Header */}
      <div
        className="turn-accordion-header"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
      >
        <div className="turn-header-left">
          <span className={`turn-index-pill ${isFollowUp ? "followup" : ""}`}>
            {isFollowUp ? `Turn ${turn_index + 1}: Follow-up` : `Turn ${turn_index + 1}: Core`}
          </span>
          <span className="turn-question-preview">{question_text}</span>
        </div>

        <div className="turn-header-right">
          <span className="turn-score-badge" style={{ color: getScoreColor(turn_score) }}>
            {turn_score}%
          </span>
          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>

      {/* Expanded Accordion Body */}
      {isExpanded && (
        <div className="turn-accordion-body">
          {/* Side-by-Side Q&A Comparison */}
          <div className="qa-comparison-grid">
            <div className="qa-box candidate-box">
              <div className="qa-box-header">
                <MessageSquare size={14} />
                <span>Your Transcribed Answer</span>
              </div>
              <p className="qa-box-content">
                {candidate_answer || "No response recorded."}
              </p>
            </div>

            <div className="qa-box ideal-box">
              <div className="qa-box-header">
                <Sparkles size={14} />
                <span>Senior Benchmark Ideal Answer</span>
              </div>
              <p className="qa-box-content">
                {ideal_answer || "Benchmark answer synthesized for senior standard."}
              </p>
            </div>
          </div>

          {/* Benchmark Gap Analysis Diff */}
          {ideal_answer_comparison && (
            <div className="turn-feedback-takeaway">
              <strong>Benchmark Gap Analysis: </strong>
              {ideal_answer_comparison}
            </div>
          )}

          {/* Concept Matrix */}
          <div className="concept-matrix-section">
            {covered_concepts && covered_concepts.length > 0 && (
              <div className="concept-group">
                <span className="concept-group-label">Covered Concepts:</span>
                <div className="concept-pills">
                  {covered_concepts.map((c, i) => (
                    <span key={`covered-${i}`} className="concept-pill covered">
                      <Check size={12} style={{ display: "inline", marginRight: "4px" }} />
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {missed_concepts && missed_concepts.length > 0 && (
              <div className="concept-group">
                <span className="concept-group-label">Missed Gaps:</span>
                <div className="concept-pills">
                  {missed_concepts.map((m, i) => (
                    <span key={`missed-${i}`} className="concept-pill missed">
                      <X size={12} style={{ display: "inline", marginRight: "4px" }} />
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Mini Turn Dimensions Grid */}
          <div className="turn-mini-dimensions-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.5rem" }}>
            <div className="mini-dim-card" style={{ background: "rgba(15, 23, 42, 0.4)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Relevance</span>
              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getScoreColor(relevance_score), fontFamily: "var(--font-mono)" }}>{relevance_score}%</span>
            </div>
            <div className="mini-dim-card" style={{ background: "rgba(15, 23, 42, 0.4)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Correctness</span>
              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getScoreColor(correctness_score), fontFamily: "var(--font-mono)" }}>{correctness_score}%</span>
            </div>
            <div className="mini-dim-card" style={{ background: "rgba(15, 23, 42, 0.4)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Keywords</span>
              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getScoreColor(keywords_score), fontFamily: "var(--font-mono)" }}>{keywords_score}%</span>
            </div>
            <div className="mini-dim-card" style={{ background: "rgba(15, 23, 42, 0.4)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Clarity</span>
              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getScoreColor(clarity_score), fontFamily: "var(--font-mono)" }}>{clarity_score}%</span>
            </div>
            <div className="mini-dim-card" style={{ background: "rgba(15, 23, 42, 0.4)", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Confidence</span>
              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getScoreColor(confidence_score), fontFamily: "var(--font-mono)" }}>{confidence_score}%</span>
            </div>
          </div>

          {/* Speech Stats & Duration */}
          <div className="turn-speech-stats">
            {turn_duration_sec && (
              <div className="speech-stat-item">
                <Clock size={14} />
                <span>Duration: <strong className="stat-val">{turn_duration_sec}s</strong></span>
              </div>
            )}

            {fillerStats && (
              <>
                <div className="speech-stat-item">
                  <Mic size={14} />
                  <span>Filler Words: <strong className="stat-val">{fillerStats.count || 0}</strong></span>
                </div>
                <div className="speech-stat-item">
                  <span>Filler Density: <strong className="stat-val">{fillerStats.density || 0}%</strong></span>
                </div>
              </>
            )}
          </div>

          {/* Constructive Takeaway Banner */}
          {turn_feedback && (
            <div className="turn-feedback-takeaway" style={{ borderLeftColor: "#10b981", background: "rgba(16, 185, 129, 0.08)", color: "#a7f3d0" }}>
              <strong>Takeaway Feedback: </strong>
              {turn_feedback}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TurnAccordion({ turnsEvaluation = [] }) {
  if (!turnsEvaluation || turnsEvaluation.length === 0) {
    return (
      <div className="turn-accordion-section">
        <h3 className="card-title">Turn-by-Turn Question Breakdown</h3>
        <p className="empty-insight">No turn evaluations recorded for this session.</p>
      </div>
    );
  }

  return (
    <div className="turn-accordion-section">
      <div className="card-header-simple">
        <h3 className="card-title">Turn-by-Turn Detailed Review</h3>
        <p className="card-subtitle">
          Expand each question to inspect ideal answers, concept matrices, mini scores, and hesitation metrics.
        </p>
      </div>

      <div className="turn-accordion-list">
        {turnsEvaluation.map((turn, idx) => (
          <TurnCard
            key={`turn-card-${turn.id || idx}`}
            turn={turn}
            defaultExpanded={idx === 0}
          />
        ))}
      </div>
    </div>
  );
}

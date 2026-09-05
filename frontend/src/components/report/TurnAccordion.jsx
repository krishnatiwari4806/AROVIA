import React, { useState } from 'react';
import { ChevronDown, ChevronUp, MessageSquare, Sparkles, Check, X, Clock } from 'lucide-react';

/**
 * Turn-by-Turn Review Accordions matching Figma Performance Report.
 * Renders real transcript evaluations without fallback mock turns or scores.
 */
export function TurnAccordion({ turnsEvaluation = [] }) {
  const safeTurns = Array.isArray(turnsEvaluation) ? turnsEvaluation : [];
  const [expandedIndex, setExpandedIndex] = useState(0);

  const toggleExpand = (idx) => {
    setExpandedIndex(expandedIndex === idx ? -1 : idx);
  };

  return (
    <div className="arovia-turn-accordion-container">
      <div className="accordion-section-header">
        <h4 className="accordion-section-title">Turn-by-Turn Review</h4>
        <span className="accordion-count-badge">
          {safeTurns.length} {safeTurns.length === 1 ? 'Evaluated Turn' : 'Evaluated Turns'}
        </span>
      </div>

      {safeTurns.length === 0 ? (
        <div
          style={{
            padding: 'var(--space-xl) var(--space-md)',
            textAlign: 'center',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            color: 'var(--text-muted)',
            fontSize: 'var(--text-xs)',
          }}
        >
          No turn-level evaluation available.
        </div>
      ) : (
        <div className="accordion-list">
          {safeTurns.map((turn, idx) => {
            const isExpanded = expandedIndex === idx;
            const turnNum = (turn.turn_index !== undefined ? turn.turn_index : idx) + 1;
            const hasScore = typeof turn.turn_score === 'number';
            const scoreDisplay = hasScore ? `${turn.turn_score}/100` : '—';
            const coveredList = Array.isArray(turn.covered_concepts) ? turn.covered_concepts : [];
            const missedList = Array.isArray(turn.missed_concepts) ? turn.missed_concepts : [];
            const duration = turn.turn_duration_sec ?? turn.duration_sec;
            const fillerCount =
              turn.filler_words ?? turn.evaluation_data?.filler_word_stats?.count;

            return (
              <div
                key={turn.id || idx}
                className={`turn-accordion-item ${isExpanded ? 'is-expanded' : ''}`}
              >
                <div
                  className="accordion-item-header"
                  onClick={() => toggleExpand(idx)}
                >
                  <div className="item-header-left">
                    <span className="turn-number-tag">
                      {turnNum < 10 ? `0${turnNum}` : turnNum}
                    </span>
                    <p className="turn-question-title">
                      {turn.question_text || 'Interview Question'}
                    </p>
                  </div>

                  <div className="item-header-right">
                    <span className="turn-score-badge">Score: {scoreDisplay}</span>
                    <button
                      type="button"
                      className="accordion-arrow-btn"
                      aria-label={isExpanded ? 'Collapse turn' : 'Expand turn'}
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="accordion-item-body">
                    {/* Side-by-Side Candidate vs Benchmark */}
                    <div className="qa-comparison-grid">
                      <div className="qa-card candidate-response-card">
                        <div className="qa-card-header">
                          <MessageSquare size={14} className="text-accent-cyan" />
                          <span>CANDIDATE RESPONSE</span>
                        </div>
                        <p className="qa-text">
                          &ldquo;{turn.candidate_answer || 'Not available'}&rdquo;
                        </p>
                      </div>

                      <div className="qa-card benchmark-response-card">
                        <div className="qa-card-header">
                          <Sparkles size={14} className="text-accent-violet" />
                          <span>SENIOR BENCHMARK</span>
                        </div>
                        <p className="qa-text">
                          {turn.ideal_answer || 'Not available'}
                        </p>
                      </div>
                    </div>

                    {/* Turn Feedback / Comparison Takeaway */}
                    {(turn.turn_feedback || turn.ideal_answer_comparison) && (
                      <div
                        className="turn-feedback-callout"
                        style={{
                          margin: 'var(--space-sm) 0',
                          padding: 'var(--space-sm) var(--space-md)',
                          background: 'rgba(255, 255, 255, 0.02)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border)',
                          fontSize: 'var(--text-xs)',
                          lineHeight: 1.5,
                        }}
                      >
                        {turn.turn_feedback && (
                          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                            <strong style={{ color: 'var(--text-primary)' }}>Turn Takeaway: </strong>
                            {turn.turn_feedback}
                          </p>
                        )}
                        {turn.ideal_answer_comparison && (
                          <p
                            style={{
                              margin: 0,
                              marginTop: turn.turn_feedback ? 'var(--space-2xs)' : 0,
                              color: 'var(--text-secondary)',
                            }}
                          >
                            <strong style={{ color: 'var(--text-primary)' }}>Benchmark Gap: </strong>
                            {turn.ideal_answer_comparison}
                          </p>
                        )}
                      </div>
                    )}

                    {/* Concept Coverage & Filler Words */}
                    <div className="turn-meta-matrix">
                      {coveredList.length > 0 && (
                        <div className="concept-row">
                          <span className="meta-row-label">Key Concepts Covered:</span>
                          <div className="concept-tags">
                            {coveredList.map((c, cIdx) => (
                              <span key={cIdx} className="concept-tag covered">
                                <Check size={11} /> {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {missedList.length > 0 && (
                        <div className="concept-row">
                          <span className="meta-row-label">Missed Gaps:</span>
                          <div className="concept-tags">
                            {missedList.map((m, mIdx) => (
                              <span key={mIdx} className="concept-tag missed">
                                <X size={11} /> {m}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {(duration !== undefined || fillerCount !== undefined) && (
                        <div className="turn-runtime-metrics">
                          {duration !== undefined && duration !== null && (
                            <span className="runtime-metric">
                              <Clock size={13} /> {duration}s
                            </span>
                          )}
                          {fillerCount !== undefined && fillerCount !== null && (
                            <span className="runtime-metric">
                              Filler Words: {fillerCount}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default TurnAccordion;

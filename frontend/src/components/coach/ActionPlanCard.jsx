import React, { useState } from 'react';
import {
  ShieldCheck,
  Target,
  Zap,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  RotateCcw,
  ArrowRight,
  Layers,
  Award,
  ChevronDown,
  ChevronUp,
  Info,
  Sparkles,
} from 'lucide-react';

/**
 * Validates whether a category can map deterministically to an InterviewFocus track.
 * Returns the mapped InterviewFocus enum string or null if unsupported.
 */
export function mapCategoryToInterviewFocus(category, customPresetFocus = null) {
  if (customPresetFocus) {
    const cf = customPresetFocus.toLowerCase();
    if (cf.includes('system') || cf.includes('design')) return 'System Design';
    if (cf.includes('behavior') || cf.includes('star') || cf.includes('comm')) return 'Behavioral';
    if (cf.includes('tech') || cf.includes('core')) return 'Technical Core';
  }

  if (!category) return null;
  const c = category.toLowerCase();
  if (c.includes('system design')) return 'System Design';
  if (c.includes('communication') || c.includes('behavioral')) return 'Behavioral';
  if (c.includes('technical core') || c.includes('role fundamentals')) return 'Technical Core';

  return null;
}

/**
 * ActionPlanCard Component
 * 
 * Authoritative UI component for displaying the deterministic ActionableCoachingPlanDTO
 * and WeaknessResolutionStateDTO.
 * 
 * Strict Ground Truth Guarantees:
 * - Visually demarcated as "Deterministic Coaching Evidence"
 * - All metrics, priorities, lifecycles, and actions are rendered directly from backend DTOs
 * - Never parses or scrapes Gemini-generated conversational text
 * - Assigned actions are rendered as assignments (never marked completed)
 * - "Launch Focused Practice" passes a structured PracticeLaunchIntent to InterviewSetup without auto-submitting
 */
export function ActionPlanCard({
  plan,
  weaknessResolutions = [],
  sessionData = null,
  onLaunchPractice,
  onStartStandardSetup,
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Check for zero-completed-sessions / baseline state
  const isZeroState =
    !plan ||
    (plan.evidence && plan.evidence.includes('0 completed sessions'));

  if (isZeroState) {
    return (
      <div className="action-plan-card baseline-state-card" data-testid="action-plan-zero-state">
        <div className="action-plan-header">
          <div className="header-badge-group">
            <span className="deterministic-source-badge">
              <ShieldCheck size={13} className="text-secondary" />
              <span>DETERMINISTIC COACHING EVIDENCE</span>
            </span>
            <span className="priority-pill priority-p3">
              Baseline Calibration
            </span>
          </div>
        </div>

        <div className="action-plan-body">
          <div className="plan-focus-banner">
            <div className="focus-icon-orb">
              <Target size={20} className="text-primary" />
            </div>
            <div>
              <h3 className="plan-focus-title">Core Technical Fundamentals</h3>
              <p className="plan-focus-category">Category: Technical Core</p>
            </div>
          </div>

          <p className="plan-reason-text">
            Complete your first full mock interview session in AROVIA to generate personalized longitudinal coaching recommendations and recurring weakness lifecycle tracking.
          </p>

          <div className="plan-assignment-section">
            <h4 className="section-subtitle">
              <Zap size={14} className="text-secondary" /> Recommended First Step
            </h4>
            <div className="assigned-actions-list">
              <div className="assigned-action-item">
                <span className="action-number-dot">1</span>
                <span className="action-text">Complete a calibrated mock interview to establish your performance baseline.</span>
              </div>
            </div>
          </div>

          <div className="plan-footer-actions">
            <button
              type="button"
              className="launch-practice-btn"
              onClick={onStartStandardSetup}
            >
              <span>Start Baseline Interview</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Determine priority styling
  const priorityClass =
    plan.priority_level?.includes('P1')
      ? 'priority-p1'
      : plan.priority_level?.includes('P2')
      ? 'priority-p2'
      : 'priority-p3';

  // Find matching weakness resolution if one exists
  const matchingResolution = weaknessResolutions?.find(
    (wr) =>
      wr.display_title?.toLowerCase() === plan.focus_topic?.toLowerCase() ||
      wr.canonical_topic?.toLowerCase() === plan.focus_topic?.toLowerCase() ||
      plan.focus_topic?.toLowerCase().includes(wr.canonical_topic?.toLowerCase())
  );

  const isResolved = matchingResolution?.status === 'resolved';
  const isImproving = matchingResolution?.status === 'improving';
  const isActive = matchingResolution?.status === 'active' || (!isResolved && !isImproving);

  // Determine Practice Track Support
  const mappedFocus = mapCategoryToInterviewFocus(
    plan.category,
    plan.practice_preset?.focus
  );
  const isPracticeTrackSupported = Boolean(mappedFocus);

  const handleLaunch = () => {
    if (!isPracticeTrackSupported || !onLaunchPractice) return;

    const targetRole =
      sessionData?.target_role || 'Backend';
    const seniority =
      sessionData?.seniority_level || 'senior';

    const practiceIntent = {
      focus_topic: plan.focus_topic,
      category: plan.category,
      target_role: targetRole,
      seniority_level: seniority,
      interview_focus: mappedFocus,
      practice_mode: plan.practice_preset?.mode || 'quick',
      focus_skills: [plan.focus_topic],
      source_session_id: sessionData?.id || null,
      launch_source: 'coach_action_plan',
    };

    onLaunchPractice(practiceIntent);
  };

  return (
    <div
      className={`action-plan-card ${isResolved ? 'is-resolved-refresher' : ''}`}
      data-testid="action-plan-card"
    >
      {/* 1. Header Bar with Ground Truth Source Indicator */}
      <div className="action-plan-header">
        <div className="header-badge-group">
          <span
            className="deterministic-source-badge"
            title="Calculated deterministically from verified evaluation scores and recurrence records"
          >
            <ShieldCheck size={13} className="text-secondary" />
            <span>DETERMINISTIC COACHING EVIDENCE</span>
          </span>

          <span className={`priority-pill ${priorityClass}`}>
            {isResolved ? 'Refresher Practice' : plan.priority_level || 'Active Focus'}
          </span>

          {matchingResolution && (
            <span
              className={`lifecycle-status-pill status-${matchingResolution.status}`}
              title={`Weakness lifecycle: ${matchingResolution.status.toUpperCase()}`}
            >
              <span className="status-dot" />
              {matchingResolution.status.toUpperCase()}
              {matchingResolution.frequency_is_decreasing && ' (Trending Down)'}
            </span>
          )}
        </div>

        <button
          type="button"
          className="card-collapse-toggle-btn"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          aria-label={isExpanded ? 'Collapse Action Plan' : 'Expand Action Plan'}
        >
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* 2. Main Focus Title & Category */}
      <div className="action-plan-body">
        <div className="plan-focus-banner">
          <div className="focus-icon-orb">
            <Target size={20} className="text-primary" />
          </div>
          <div className="focus-title-wrap">
            <div className="category-pill-tag">
              <Layers size={11} />
              <span>{plan.category || 'Technical Core'}</span>
            </div>
            <h3 className="plan-focus-title">{plan.focus_topic}</h3>
          </div>
        </div>

        {isExpanded && (
          <>
            {/* 3. Deterministic Why & Evidence Grid */}
            <div className="plan-rationale-grid">
              <div className="rationale-col">
                <span className="col-label">
                  <Info size={12} className="text-muted" /> RATIONALE
                </span>
                <p className="col-text">{plan.reason}</p>
              </div>

              <div className="rationale-col">
                <span className="col-label">
                  <ShieldCheck size={12} className="text-secondary" /> SUPPORTING EVIDENCE
                </span>
                <p className="col-text evidence-text">{plan.evidence}</p>
                {matchingResolution && matchingResolution.sessions_observed_count > 1 && (
                  <span className="observation-count-tag">
                    Observed across {matchingResolution.sessions_observed_count} completed sessions
                  </span>
                )}
              </div>
            </div>

            {/* 4. Assigned Practice Steps (Rendered as Assignments, Never Completed) */}
            {plan.concrete_actions && plan.concrete_actions.length > 0 && (
              <div className="plan-assignment-section">
                <h4 className="section-subtitle">
                  <Zap size={14} className="text-secondary" /> Assigned Practice Steps
                </h4>
                <div className="assigned-actions-list">
                  {plan.concrete_actions.map((action, idx) => (
                    <div key={idx} className="assigned-action-item">
                      <span className="action-number-dot">{idx + 1}</span>
                      <span className="action-text">{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 5. Measurement & Verification */}
            <div className="plan-measurement-grid">
              <div className="measurement-box">
                <span className="measure-label">SUCCESS METRIC</span>
                <p className="measure-value">{plan.success_metric}</p>
              </div>

              <div className="measurement-box">
                <span className="measure-label">REVIEW CONDITION</span>
                <p className="measure-value">{plan.review_condition}</p>
              </div>
            </div>

            {/* 6. Safe Practice Launch CTA */}
            <div className="plan-footer-actions">
              {isPracticeTrackSupported ? (
                <button
                  type="button"
                  className="launch-practice-btn"
                  onClick={handleLaunch}
                  title={`Launch focused drill on ${plan.focus_topic}`}
                >
                  <RotateCcw size={15} />
                  <span>
                    {isResolved ? 'Start Refresher Practice Drill' : 'Launch Focused Practice Drill'}
                  </span>
                  <ArrowRight size={15} />
                </button>
              ) : (
                <div className="unsupported-track-notice">
                  <AlertTriangle size={15} className="text-muted flex-shrink-0" />
                  <span>This coaching topic does not currently have a supported focused practice track.</span>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default ActionPlanCard;

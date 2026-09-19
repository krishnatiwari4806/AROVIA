import React from 'react';
import {
  Check,
  Sparkles,
  Layers,
  Database,
  ShieldAlert,
  Cpu,
  CheckCircle2,
} from 'lucide-react';

/**
 * Authoritative Canonical Stage Definitions for Staged System Design Interviews.
 * Strictly 4 core architecture evaluation stages.
 */
export const SYSTEM_DESIGN_STAGES = [
  {
    index: 1,
    key: 'stage_1_requirements',
    shortName: 'Requirements',
    fullName: 'Scope & Requirements',
    defaultFocus: 'Define scope, constraints, and service expectations.',
    Icon: Layers,
  },
  {
    index: 2,
    key: 'stage_2_estimation',
    shortName: 'Estimation',
    fullName: 'Estimation & Data Model',
    defaultFocus: 'Reason about traffic, capacity, and data growth.',
    Icon: Database,
  },
  {
    index: 3,
    key: 'stage_3_architecture',
    shortName: 'Architecture',
    fullName: 'High-Level Architecture',
    defaultFocus: 'Decompose the system and explain request/data flow.',
    Icon: Cpu,
  },
  {
    index: 4,
    key: 'stage_4_defense',
    shortName: 'Failure Defense',
    fullName: 'Failure & Scale Pushback',
    defaultFocus: 'Pressure-test your design under failure and scale.',
    Icon: ShieldAlert,
  },
];

/**
 * SystemDesignStageStepper Component.
 *
 * Compact, premium, and responsive live stage progression tracker for staged System Design interviews.
 * Purely presentational; receives authoritative stage state from backend session/turn metadata.
 */
export function SystemDesignStageStepper({
  stageIndex,
  stageKey,
  stageName,
  stageFocus,
  scenarioTitle,
  isComplete = false,
  seniorityLevel = 'SENIOR',
  isSpeaking = false,
  isListening = false,
}) {
  // Normalize stageIndex safely (0 = warm-up, 1..4 = core stages)
  const numericIndex = typeof stageIndex === 'number' ? stageIndex : null;
  const isWarmup = numericIndex === 0;

  // Resolve current active stage definition
  const currentStageDef =
    SYSTEM_DESIGN_STAGES.find((s) => s.index === numericIndex || s.key === stageKey) || null;

  // Deterministic focus description text
  let activeFocusText = '';
  if (isComplete) {
    activeFocusText = 'All 4 architecture stages completed. Preparing evaluation report...';
  } else if (isWarmup) {
    activeFocusText =
      stageFocus || 'Context gathering, scenario presentation, and problem ingress.';
  } else if (stageFocus) {
    activeFocusText = stageFocus;
  } else if (currentStageDef?.defaultFocus) {
    activeFocusText = currentStageDef.defaultFocus;
  } else {
    activeFocusText = 'Articulate your architectural reasoning and trade-offs.';
  }

  // Display scenario title (neutral fallback if absent, zero fake titles)
  const displayScenario =
    scenarioTitle && typeof scenarioTitle === 'string' && scenarioTitle.trim()
      ? scenarioTitle.trim()
      : 'System Design Practice';
  const seniorityLabel = seniorityLevel ? String(seniorityLevel).toUpperCase() : 'SENIOR';

  return (
    <header
      className="staged-mode-header-container"
      role="region"
      aria-label="System Design Interview Stages"
    >
      {/* Top Meta Bar: Live Badge, Scenario Title, and Seniority */}
      <div className="staged-header-top-row">
        <div className="staged-meta-left">
          <div className="live-status-pill">
            <span className="live-pulsing-dot" aria-hidden="true" />
            <span className="live-status-label">LIVE SYSTEM DESIGN</span>
          </div>

          <div className="staged-scenario-group">
            <span className="staged-scenario-title" title={displayScenario}>
              {displayScenario}
            </span>
            <span className="meta-pill">LEVEL: {seniorityLabel}</span>
            <span className="meta-pill cyan-pill">TRACK: 4-STAGE ARCHITECTURE</span>
          </div>
        </div>

        {/* Turn 0 Warm-up or Completion Status Pill */}
        <div className="staged-meta-right">
          {isComplete ? (
            <div className="staged-status-badge completed">
              <CheckCircle2 size={13} className="text-success" aria-hidden="true" />
              <span>INTERVIEW COMPLETED</span>
            </div>
          ) : isWarmup ? (
            <div className="staged-status-badge warmup">
              <Sparkles size={12} className="text-cyan animate-pulse" aria-hidden="true" />
              <span>WARM-UP INGRESS</span>
            </div>
          ) : (
            <div className="staged-status-badge active-stage">
              <span className="stage-counter-text">
                STAGE {numericIndex || 1} OF 4
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Stepper Navigation: 4 Core Architecture Stages */}
      <nav
        className="staged-stepper-nav"
        aria-label="System Design Stage Progression"
      >
        <ol className="staged-stepper-list">
          {SYSTEM_DESIGN_STAGES.map((stage, idx) => {
            let status = 'upcoming';
            if (isComplete) {
              status = 'completed';
            } else if (isWarmup) {
              status = 'upcoming';
            } else if (numericIndex !== null && numericIndex !== undefined) {
              if (stage.index < numericIndex) {
                status = 'completed';
              } else if (stage.index === numericIndex) {
                status = 'active';
              } else {
                status = 'upcoming';
              }
            } else if (idx === 0) {
              status = 'active';
            }

            const isActive = status === 'active';
            const isCompleted = status === 'completed';

            return (
              <li
                key={stage.key}
                className={`staged-step-item step-${status}`}
                aria-current={isActive ? 'step' : undefined}
              >
                <div className="staged-step-pill">
                  <span className="step-icon-wrapper" aria-hidden="true">
                    {isCompleted ? (
                      <Check size={13} className="step-icon-check" />
                    ) : isActive ? (
                      <span className="step-active-dot" />
                    ) : (
                      <span className="step-index-num">{stage.index}</span>
                    )}
                  </span>
                  <span className="step-label-text">
                    <span className="sr-only">
                      {isCompleted
                        ? `Completed Stage ${stage.index}: `
                        : isActive
                        ? `Current Active Stage ${stage.index}: `
                        : `Upcoming Stage ${stage.index}: `}
                    </span>
                    {stage.shortName}
                  </span>
                </div>

                {/* Connector between steps */}
                {idx < SYSTEM_DESIGN_STAGES.length - 1 && (
                  <div
                    className={`staged-step-connector ${
                      isCompleted && (numericIndex > stage.index || isComplete)
                        ? 'connector-completed'
                        : isActive
                        ? 'connector-active'
                        : ''
                    }`}
                    aria-hidden="true"
                  />
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      {/* Active Stage Focus Guidance Banner */}
      <div
        className={`staged-focus-banner ${
          isComplete ? 'completed' : isWarmup ? 'warmup' : 'active'
        }`}
        role="status"
        aria-live="polite"
      >
        <div className="staged-focus-label-row">
          <span className="staged-focus-tag">
            {isComplete
              ? 'SESSION COMPLETE'
              : isWarmup
              ? 'WARM-UP FOCUS'
              : `STAGE ${numericIndex || 1} FOCUS: ${
                  currentStageDef?.shortName || stageName || 'ARCHITECTURE'
                }`}
          </span>
          <span className="staged-focus-desc">{activeFocusText}</span>
        </div>
      </div>
    </header>
  );
}

export default SystemDesignStageStepper;

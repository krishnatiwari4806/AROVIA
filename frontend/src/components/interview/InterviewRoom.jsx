import React, { useState, useEffect, useCallback } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Sparkles,
  Loader2,
  ArrowRight,
  X,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';
import { api } from '../../services/api';
import { useSpeechSynthesis } from '../../hooks/useSpeechSynthesis';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { TurnTimer } from './TurnTimer';
import { AudioVisualizer } from './AudioVisualizer';
import { CrystalCore } from './CrystalCore';
import { getAroviaSettings } from '../../services/settingsManager';

/**
 * Live Interview Room Component.
 * Restrained analytical layout with floating 3D Crystal, live question prompt,
 * live transcription panel, microphone dictation, robust turn progression, and
 * safe early termination & evaluation workflows without fallback fake data.
 */
export function InterviewRoom({ sessionId, onComplete, onRetake, onExit }) {
  const [session, setSession] = useState(null);
  const [currentTurn, setCurrentTurn] = useState(null);
  const [candidateAnswer, setCandidateAnswer] = useState('');
  const [elapsedDurationSec, setElapsedDurationSec] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [error, setError] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);

  const { speak, cancel, isSpeaking } = useSpeechSynthesis();

  const handleTranscript = useCallback((text) => {
    setCandidateAnswer(text);
  }, []);

  const {
    startListening,
    stopListening,
    toggleListening,
    isListening,
    isSupported: isSttSupported,
  } = useSpeechRecognition({ onTranscriptUpdate: handleTranscript });

  const initRoom = useCallback(async () => {
    if (!sessionId) {
      setLoading(false);
      setError('No session ID provided.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // 1. Fetch Session Metadata
      const sess = await api.getSession(sessionId);
      if (!sess) {
        throw new Error('Interview session record not found on the server.');
      }
      setSession(sess);

      // 2. Start session (idempotent) or retrieve active turn
      let turn;
      try {
        turn = await api.startInterview(sessionId);
      } catch {
        turn = await api.getCurrentTurn(sessionId);
      }

      if (!turn) {
        throw new Error('Unable to retrieve initial question turn from server.');
      }

      setCurrentTurn(turn);
      setCandidateAnswer('');

      const settings = getAroviaSettings();
      const autoPlay = settings.languageVoice?.autoPlayQuestions !== false;

      if (turn && turn.question_text && autoPlay) {
        speak(turn.question_text);
      }
    } catch (err) {
      console.error('Failed to initialize interview room:', err);
      setError(err?.message || 'Could not load interview session from the server.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, speak]);

  useEffect(() => {
    initRoom();

    return () => {
      cancel();
      stopListening();
    };
  }, [initRoom, cancel, stopListening]);

  // Submit current answer and advance to next turn
  const handleSubmitAnswer = async () => {
    if (submitting || isEnding || isCompleted || !currentTurn) return;

    try {
      setSubmitting(true);
      setError(null);
      stopListening();
      cancel();

      const answerToSubmit = candidateAnswer.trim() || 'No audible candidate response provided.';
      const payload = {
        candidate_answer: answerToSubmit,
        turn_duration_sec: Math.max(1, elapsedDurationSec || 0),
      };

      // Real API Submission - no synthetic fallback questions on failure
      const nextTurnResult = await api.submitTurnAnswer(sessionId, currentTurn.id, payload);

      if (nextTurnResult?.is_interview_complete) {
        // Evaluate session upon completing all planned questions
        const evalReport = await api.evaluateSession(sessionId);
        setIsCompleted(true);
        onComplete?.(evalReport);
      } else if (nextTurnResult?.next_turn) {
        // Advance to next genuine turn from backend
        setCurrentTurn(nextTurnResult.next_turn);
        setCandidateAnswer('');
        setElapsedDurationSec(0);

        const settings = getAroviaSettings();
        const autoPlay = settings.languageVoice?.autoPlayQuestions !== false;
        if (nextTurnResult.next_turn.question_text && autoPlay) {
          speak(nextTurnResult.next_turn.question_text);
        }
      }
    } catch (err) {
      console.error('Error submitting answer or evaluating session:', err);
      setError(err?.message || 'Error submitting answer. Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // Dedicated End Interview Early Handler
  const handleEndEarly = async () => {
    if (isEnding || submitting || isCompleted) return;

    const confirmed = window.confirm(
      'Are you sure you want to end this interview session early?\n\nIf you have answered questions, an evaluation report will be generated for your responses. If no questions were answered, this session will be cancelled.'
    );
    if (!confirmed) return;

    try {
      setIsEnding(true);
      setError(null);
      stopListening();
      cancel();

      // Check if candidate provided a draft answer for the current active turn
      const hasCurrentDraft = candidateAnswer && candidateAnswer.trim().length > 0;
      let answeredCount = currentTurn?.turn_index ?? 0;

      if (hasCurrentDraft && currentTurn?.id) {
        try {
          await api.submitTurnAnswer(sessionId, currentTurn.id, {
            candidate_answer: candidateAnswer.trim(),
            turn_duration_sec: Math.max(1, elapsedDurationSec || 0),
          });
          answeredCount += 1;
        } catch (submitErr) {
          console.warn('Could not submit final draft answer before early ending:', submitErr);
        }
      }

      // If at least one turn was answered, trigger evaluation pipeline
      if (answeredCount > 0 || hasCurrentDraft) {
        try {
          const evalReport = await api.evaluateSession(sessionId);
          setIsCompleted(true);
          onComplete?.(evalReport);
          return;
        } catch (evalErr) {
          console.error('Evaluation request error:', evalErr);
          if (evalErr?.message?.includes('zero answered questions') || evalErr?.status === 400) {
            try {
              await api.abandonSession(sessionId);
            } catch {
              // ignore
            }
            onExit?.();
            return;
          }
          // Do NOT generate fake scores or fake reports
          setError(evalErr?.message || 'Failed to generate interview evaluation. Please try again.');
          setIsEnding(false);
          return;
        }
      } else {
        // Zero answered questions: cleanly abandon session and return to Dashboard
        try {
          await api.abandonSession(sessionId);
        } catch (abandonErr) {
          console.warn('Abandon session note:', abandonErr);
        }
        onExit?.();
      }
    } catch (err) {
      setError(err?.message || 'Could not end interview session.');
      setIsEnding(false);
    }
  };

  if (loading) {
    return (
      <div className="interview-room-loading">
        <Loader2 size={36} className="animate-spin text-primary" />
        <p className="loading-text">Calibrating AROVIA AI Intelligence Room...</p>
      </div>
    );
  }

  if (!currentTurn && error && !loading) {
    return (
      <div className="arovia-interview-room-layout">
        <div
          className="room-error-card"
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
            Unable to load interview session
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
            {error}
          </p>
          <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
            <button
              type="button"
              className="footer-btn secondary"
              onClick={onExit}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-xs)' }}
            >
              <span>Back to Dashboard</span>
            </button>
            <button
              type="button"
              className="footer-btn primary-cta"
              onClick={initRoom}
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

  const turnNumber = currentTurn?.turn_index !== undefined ? currentTurn.turn_index + 1 : 1;
  const totalTurns = session?.planned_core_questions || session?.total_planned_turns || 6;
  const progressPercent = Math.min(100, Math.round((turnNumber / totalTurns) * 100));
  const roleName = session?.target_role || 'Technical Interview Session';
  const seniorityLabel = session?.seniority_level?.toUpperCase() || 'SENIOR';
  const focusLabel = session?.interview_focus?.toUpperCase() || 'TECHNICAL CORE';

  return (
    <div className="arovia-interview-room-layout">
      {/* Top Header / Progress Bar */}
      <header className="room-top-header">
        <div className="header-meta-group">
          <div className="live-status-pill">
            <span className="live-pulsing-dot" />
            <span className="live-status-label">LIVE SESSION</span>
          </div>

          <div className="role-tags-group">
            <span className="role-title-text">{roleName}</span>
            <span className="meta-pill">LEVEL: {seniorityLabel}</span>
            <span className="meta-pill cyan-pill">FOCUS: {focusLabel}</span>
          </div>
        </div>

        <div className="turn-progress-tracker">
          <div className="tracker-label-row">
            <span className="tracker-text">
              QUESTION {turnNumber} OF {totalTurns}
            </span>
          </div>
          <div className="tracker-bar-track">
            <div className="tracker-bar-fill" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      </header>

      {/* Alert / Error Banner if any */}
      {error && (
        <div className="profile-alert error-alert" style={{ margin: '0 0 var(--space-md) 0' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Interactive Stage Grid */}
      <div className="room-stage-grid">
        {/* CENTER STAGE: Floating 3D Crystal & Question Box */}
        <div className="room-center-stage">
          {/* Floating 3D Holographic Crystal */}
          <div className="crystal-stage-container">
            <CrystalCore isSpeaking={isSpeaking} isListening={isListening} size={150} />
            <AudioVisualizer isSpeaking={isSpeaking} isListening={isListening} />
          </div>

          {/* AI Question Prompt Card */}
          <div className="ai-question-card">
            <div className="question-card-header">
              <span className="ai-asking-badge">
                <Sparkles size={13} />
                {isSpeaking ? 'AROVIA IS SPEAKING' : isListening ? 'AROVIA IS LISTENING' : 'AROVIA IS ASKING'}
              </span>
              <div className="question-tag-pills">
                <span className="tag-pill">
                  {currentTurn?.category || currentTurn?.primary_concept || 'Technical Core'}
                </span>
                {currentTurn?.is_follow_up && (
                  <span className="tag-pill follow-up-pill">Follow-up Probing</span>
                )}
              </div>
            </div>

            <p className="question-prompt-text">
              &ldquo;{currentTurn?.question_text || 'Interview question prompt loading...'}&rdquo;
            </p>

            {/* TTS Repeat Control */}
            <div className="question-audio-action">
              <button
                type="button"
                className="audio-replay-btn"
                onClick={() => {
                  if (isSpeaking) cancel();
                  else if (currentTurn?.question_text) speak(currentTurn.question_text);
                }}
                title={isSpeaking ? 'Mute AI voice' : 'Replay question audio'}
              >
                {isSpeaking ? <VolumeX size={14} /> : <Volume2 size={14} />}
                <span>{isSpeaking ? 'Mute AI Voice' : 'Repeat Question'}</span>
              </button>
            </div>
          </div>

          {/* Turn Timer */}
          <div className="room-timer-row">
            <TurnTimer
              durationLimitSec={currentTurn?.ideal_time_sec || 300}
              onDurationTick={setElapsedDurationSec}
              isPaused={submitting || isEnding || isCompleted}
            />
          </div>
        </div>

        {/* RIGHT STAGE: Live Transcription (Top) + Square Mic & Action Buttons (Bottom) */}
        <div className="room-right-stage">
          {/* Top: Live Transcription Card */}
          <div className="live-transcription-card">
            <div className="transcription-header">
              <div className="transcription-title-box">
                <span className="transcription-dot" />
                <span className="transcription-title">LIVE TRANSCRIPTION</span>
              </div>
            </div>

            <div className="transcription-content-box">
              <textarea
                className="transcription-textarea"
                placeholder={
                  isListening
                    ? 'Listening to speech in real-time... (you can also edit or type manually)'
                    : 'Click the square microphone button or type your answer here...'
                }
                value={candidateAnswer}
                onChange={(e) => setCandidateAnswer(e.target.value)}
                rows={7}
                disabled={isEnding || submitting || isCompleted}
              />
              <div className="transcription-meta-footer">
                <span className="word-count">
                  {candidateAnswer.trim() ? candidateAnswer.trim().split(/\s+/).length : 0} words
                </span>
                <span className="edit-hint">Editable prior to submission</span>
              </div>
            </div>
          </div>

          {/* Bottom: Large Square Microphone + Dual Action Controls */}
          <div className="room-controls-card">
            {/* Square Microphone Control */}
            <div className="mic-square-control">
              <button
                type="button"
                className={`square-mic-btn ${isListening ? 'listening' : ''}`}
                onClick={toggleListening}
                disabled={isEnding || submitting || isCompleted}
                title={isListening ? 'Stop listening' : 'Start microphone dictation'}
              >
                {isListening ? <MicOff size={28} /> : <Mic size={28} />}
              </button>
              <span className="mic-status-label">
                {isListening ? 'LISTENING...' : 'CLICK TO SPEAK'}
              </span>
            </div>

            {/* Dual Action Buttons: END INTERVIEW & SUBMIT RESPONSE */}
            <div className="dual-action-buttons-row">
              <button
                type="button"
                className="end-interview-btn"
                onClick={handleEndEarly}
                disabled={isEnding || submitting || isCompleted}
              >
                {isEnding ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>ENDING...</span>
                  </>
                ) : (
                  <>
                    <X size={14} />
                    <span>END INTERVIEW</span>
                  </>
                )}
              </button>

              <button
                type="button"
                className="submit-turn-btn"
                onClick={handleSubmitAnswer}
                disabled={isEnding || submitting || !currentTurn || isCompleted}
              >
                {submitting ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    <span>EVALUATING...</span>
                  </>
                ) : (
                  <>
                    <span>SUBMIT RESPONSE</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default InterviewRoom;

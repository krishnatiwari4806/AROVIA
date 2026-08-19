import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Award,
} from 'lucide-react';
import { api } from '../../services/api';
import { useSpeechSynthesis } from '../../hooks/useSpeechSynthesis';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { TurnTimer } from './TurnTimer';
import { AudioVisualizer } from './AudioVisualizer';

export function InterviewRoom({ sessionId, onComplete }) {
  const [session, setSession] = useState(null);
  const [currentTurn, setCurrentTurn] = useState(null);
  const [candidateAnswer, setCandidateAnswer] = useState('');
  const [elapsedDurationSec, setElapsedDurationSec] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);

  const { speak, cancel, isSpeaking } = useSpeechSynthesis();
  const answerRef = useRef('');
  answerRef.current = candidateAnswer;

  const handleTranscript = useCallback((text) => {
    setCandidateAnswer((prev) => {
      // Append or update dictation smoothly
      return text;
    });
  }, []);

  const {
    startListening,
    stopListening,
    toggleListening,
    isListening,
    isSupported: isSttSupported,
  } = useSpeechRecognition({ onTranscriptUpdate: handleTranscript });

  // Initialize or resume session turn
  useEffect(() => {
    let isMounted = true;

    async function loadInterview() {
      try {
        setLoading(true);
        setError(null);

        const sess = await api.getSession(sessionId);
        if (!isMounted) return;
        setSession(sess);

        if (sess.status === 'completed' || sess.status === 'evaluating') {
          setIsCompleted(true);
          setLoading(false);
          return;
        }

        // Start or get active turn
        let turn;
        try {
          turn = await api.startInterview(sessionId);
        } catch {
          turn = await api.getCurrentTurn(sessionId);
        }

        if (!isMounted) return;
        setCurrentTurn(turn);
        setCandidateAnswer('');

        // Auto-speak question prompt
        if (turn && turn.question_text) {
          speak(turn.question_text);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to load interview session.');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    if (sessionId) {
      loadInterview();
    }

    return () => {
      isMounted = false;
      cancel();
      stopListening();
    };
  }, [sessionId, speak, cancel, stopListening]);

  // Handle answer submission
  const handleSubmitAnswer = async (e) => {
    if (e) e.preventDefault();
    if (!candidateAnswer.trim() || submitting || !currentTurn) return;

    try {
      setSubmitting(true);
      setError(null);
      cancel();
      stopListening();

      const response = await api.submitTurnAnswer(sessionId, currentTurn.id, {
        candidate_answer: candidateAnswer.trim(),
        turn_duration_sec: elapsedDurationSec,
      });

      if (response.is_interview_complete || !response.next_turn) {
        setIsCompleted(true);
        if (onComplete) onComplete(response);
      } else {
        setCurrentTurn(response.next_turn);
        setCandidateAnswer('');
        setElapsedDurationSec(0);
        // Auto-speak next question
        if (response.next_turn.question_text) {
          speak(response.next_turn.question_text);
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to submit answer. Please retry.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReplayAudio = () => {
    if (currentTurn && currentTurn.question_text) {
      speak(currentTurn.question_text);
    }
  };

  const handleStopAudio = () => {
    cancel();
  };

  const budgetSeconds =
    session?.interview_focus === 'System Design' ? 180 : 120;

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
        <Sparkles size={32} style={{ color: 'var(--accent-primary)', marginBottom: '1rem', animation: 'spin 2s linear infinite' }} />
        <h2 style={{ fontSize: '1.25rem' }}>Preparing your interview room...</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Fusing job requirements and generating personalized questions.</p>
      </div>
    );
  }

  if (isCompleted) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3.5rem 2rem', maxWidth: '650px', margin: '2rem auto' }}>
        <CheckCircle2 size={48} style={{ color: 'var(--success)', marginBottom: '1.25rem' }} />
        <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.75rem' }}>Mock Interview Completed!</h2>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
          Great job! Your responses across all turns have been recorded. Our multi-dimensional evaluation engine is currently analyzing your technical relevance, correctness, clarity, and key concepts.
        </p>
        <div className="badge badge-success" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
          Status: Evaluating Answers
        </div>
      </div>
    );
  }

  return (
    <div className="interview-layout">
      {error && (
        <div className="badge badge-danger" style={{ width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Session Navigation & Progress Bar */}
      <div className="card" style={{ padding: '1.25rem 1.5rem' }}>
        <div className="turn-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: '1.35rem', fontWeight: 700 }}>{session?.target_role || 'Target Role'}</h1>
              <span className="badge badge-core">{session?.seniority_level?.toUpperCase()}</span>
              <span className="badge badge-core">{session?.interview_focus}</span>
              <span className="badge badge-core">{session?.practice_mode === 'quick' ? 'Quick Practice' : 'Full Mock'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
              {currentTurn?.is_follow_up ? (
                <span className="badge badge-followup">
                  <Sparkles size={12} />
                  Adaptive Follow-up Probe
                </span>
              ) : (
                <span className="badge badge-core">
                  Turn {(currentTurn?.turn_index || 0) + 1} of {session?.planned_core_questions || 6}
                </span>
              )}
            </div>
          </div>

          <TurnTimer
            budgetSeconds={budgetSeconds}
            onTick={(sec) => setElapsedDurationSec(sec)}
            isPaused={submitting}
          />
        </div>

        {/* AI Question Card */}
        <div className="question-box">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-accent)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Award size={14} /> AI Interviewer Question
            </span>
            <AudioVisualizer active={isSpeaking} label="Speaking..." />
          </div>

          <div className="question-text">
            {currentTurn?.question_text || 'Loading question...'}
          </div>

          <div className="audio-controls">
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.825rem' }}
              onClick={handleReplayAudio}
              disabled={isSpeaking}
              title="Replay question audio"
            >
              <Volume2 size={14} /> Replay
            </button>
            {isSpeaking && (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.825rem' }}
                onClick={handleStopAudio}
                title="Mute AI voice"
              >
                <VolumeX size={14} /> Mute
              </button>
            )}
          </div>
        </div>

        {/* Candidate Response Workspace */}
        <form onSubmit={handleSubmitAnswer} className="answer-container">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <label style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Your Response:
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <AudioVisualizer active={isListening} label="Listening..." />
              {isSttSupported ? (
                <button
                  type="button"
                  className={`btn ${isListening ? 'btn-danger' : 'btn-secondary'}`}
                  onClick={toggleListening}
                  style={{ padding: '0.45rem 0.9rem', fontSize: '0.85rem' }}
                  title={isListening ? 'Stop microphone dictation' : 'Start microphone dictation'}
                >
                  {isListening ? (
                    <>
                      <MicOff size={14} /> Stop Dictation
                    </>
                  ) : (
                    <>
                      <Mic size={14} /> Dictate Answer
                    </>
                  )}
                </button>
              ) : (
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Microphone dictation unavailable in this browser. You can type your answer directly.
                </span>
              )}
            </div>
          </div>

          <div className="textarea-wrapper">
            <textarea
              className="answer-textarea"
              placeholder="Speak using the microphone or type your technical answer here in detail..."
              value={candidateAnswer}
              onChange={(e) => setCandidateAnswer(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {candidateAnswer.trim().split(/\s+/).filter(Boolean).length} words
            </span>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={!candidateAnswer.trim() || submitting}
              style={{ minWidth: '150px' }}
            >
              {submitting ? (
                <>
                  <Sparkles size={16} className="spin" /> Evaluating...
                </>
              ) : (
                <>
                  <Send size={16} /> Submit Answer
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

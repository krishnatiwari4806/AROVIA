import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ArrowLeft,
  Bot,
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Sparkles,
  RotateCcw,
  Loader2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Award,
  Layers,
  ChevronRight,
  BookOpen,
  MessageSquare,
  HelpCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { useCoachVoice } from '../../hooks/useCoachVoice';

/**
 * Format markdown-like text safely for the coaching dialogue.
 * Supports bold, headers, bullet lists, code blocks, and quote blocks.
 */
function MarkdownRenderer({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeBuffer = [];

  lines.forEach((line, idx) => {
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${idx}`} className="coach-code-block">
            <code>{codeBuffer.join('\n')}</code>
          </pre>
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      return;
    }

    const trimmed = line.trim();

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h3-${idx}`} className="coach-md-h3">
          {trimmed.replace('### ', '')}
        </h4>
      );
    } else if (trimmed.startsWith('#### ')) {
      elements.push(
        <h5 key={`h4-${idx}`} className="coach-md-h4">
          {trimmed.replace('#### ', '')}
        </h5>
      );
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const bulletText = trimmed.substring(2);
      elements.push(
        <li key={`li-${idx}`} className="coach-md-li">
          {renderFormattedText(bulletText)}
        </li>
      );
    } else if (trimmed === '') {
      elements.push(<div key={`sp-${idx}`} className="coach-md-spacer" />);
    } else {
      elements.push(
        <p key={`p-${idx}`} className="coach-md-p">
          {renderFormattedText(trimmed)}
        </p>
      );
    }
  });

  return <div className="coach-markdown-container">{elements}</div>;
}

function renderFormattedText(text) {
  // Simple bold and inline code highlighter
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="coach-inline-code">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

export function CoachView({ sessionId, onBack, onViewReport, onStartSetup }) {
  const [loading, setLoading] = useState(true);
  const [sessionData, setSessionData] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [suggestedFollowups, setSuggestedFollowups] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedTurnIndex, setSelectedTurnIndex] = useState(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [autoPlayVoice, setAutoPlayVoice] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'turns' | 'longitudinal'

  const messageEndRef = useRef(null);
  const inputRef = useRef(null);

  // Audio Voice Hook
  const { isSpeaking, activeMessageId, speakMessage, stopSpeaking } = useCoachVoice();

  // Speech-to-Text Input Hook
  const handleTranscript = useCallback((text) => {
    if (text) {
      setInputMessage(text);
    }
  }, []);

  const {
    isListening,
    toggleListening,
    stopListening,
  } = useSpeechRecognition({
    onTranscriptUpdate: handleTranscript,
  });

  // Scroll smoothly to bottom on new messages
  const scrollToBottom = useCallback(() => {
    if (messageEndRef.current) {
      messageEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending, scrollToBottom]);

  // Load session context and get or create AI Coach conversation
  const loadCoachSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch target interview session evaluation & metadata if sessionId exists
      let targetSessionId = sessionId;

      if (!targetSessionId) {
        // Find most recent completed session for candidate
        const sessions = await api.getUserSessions(10, 0).catch(() => []);
        const completed = sessions.find((s) => s.status === 'completed' && s.has_evaluation);
        if (completed) {
          targetSessionId = completed.id;
        }
      }

      if (targetSessionId) {
        const sess = await api.getSession(targetSessionId).catch(() => null);
        const evalData = await api.getSessionEvaluation(targetSessionId).catch(() => null);
        setSessionData({
          ...sess,
          evaluation: evalData,
        });
      }

      // 2. Initialize or fetch Coach conversation
      const convData = await api.getOrCreateCoachConversation(targetSessionId, true);
      setConversation(convData);
      setMessages(convData.messages || []);
      setSuggestedFollowups(convData.suggested_followups || []);

      // If auto-play voice is enabled and opening debrief exists, speak it
      if (convData.messages && convData.messages.length > 0 && autoPlayVoice) {
        const firstMsg = convData.messages[0];
        if (firstMsg.sender === 'coach') {
          speakMessage(firstMsg.id, firstMsg.message_text);
        }
      }
    } catch (err) {
      console.error('Failed to initialize AI Coach conversation:', err);
      setError(err?.message || 'Unable to connect to Personal AI Coach.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, autoPlayVoice, speakMessage]);

  useEffect(() => {
    loadCoachSession();
  }, [loadCoachSession]);

  // Send candidate question to AI Coach
  const handleSendMessage = async (customText = null, turnOverride = null) => {
    const textToSend = (customText || inputMessage).trim();
    if (!textToSend || sending || !conversation) return;

    const targetTurn = turnOverride !== null ? turnOverride : selectedTurnIndex;

    // Stop listening if mic is on
    if (isListening) {
      stopListening();
    }
    stopSpeaking();

    // Optimistically append candidate message to UI
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      conversation_id: conversation.id,
      sender: 'user',
      message_text: textToSend,
      context_turn_index: targetTurn,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setInputMessage('');
    setSending(true);
    setError(null);

    try {
      const response = await api.sendCoachChat(
        conversation.id,
        textToSend,
        targetTurn
      );

      if (response && response.coach_message) {
        // Replace temp message with server confirmed messages
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== tempUserMsg.id),
          response.user_message,
          response.coach_message,
        ]);

        if (response.suggested_followups && response.suggested_followups.length > 0) {
          setSuggestedFollowups(response.suggested_followups);
        }

        // Auto play audio if enabled
        if (autoPlayVoice) {
          speakMessage(response.coach_message.id, response.coach_message.message_text);
        }
      }
    } catch (err) {
      console.error('Failed to send message to Coach:', err);
      setError('AI Coach response timed out or failed. Please retry.');
    } finally {
      setSending(false);
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleSelectTurnPrompt = (turnIndex, promptType) => {
    setSelectedTurnIndex(turnIndex);
    let prompt = `Why was my answer in Turn ${turnIndex + 1} scored lower?`;
    if (promptType === 'model_answer') {
      prompt = `What is a senior-level benchmark model answer for Turn ${turnIndex + 1}?`;
    } else if (promptType === 'breakdown') {
      prompt = `Can you break down the trade-offs I missed in Turn ${turnIndex + 1}?`;
    }
    handleSendMessage(prompt, turnIndex);
    setActiveTab('chat');
  };

  if (loading) {
    return (
      <div className="coach-loading-container">
        <div className="coach-ai-orb animate-pulse" />
        <Loader2 size={36} className="animate-spin text-primary mt-4" />
        <h3 className="loading-title">Calibrating Personal AI Coach...</h3>
        <p className="loading-subtext">
          Grounding mentor in your transcript, turns, benchmark answers, and longitudinal history.
        </p>
      </div>
    );
  }

  const roleName = sessionData?.target_role || 'Technical Interview Track';
  const seniority = sessionData?.seniority_level || 'Senior';
  const overallScore = sessionData?.overall_score ?? (sessionData?.evaluation?.overall_score || null);
  const turnsList = sessionData?.turns || sessionData?.evaluation?.turns_evaluation || [];

  return (
    <div className="coach-view-container">
      {/* 1. Header Bar */}
      <div className="coach-header-bar">
        <div className="coach-header-left">
          <button className="coach-back-btn" onClick={onBack} title="Return to Report or Dashboard">
            <ArrowLeft size={18} />
          </button>
          <div className="coach-brand-title">
            <div className="coach-avatar-badge">
              <Sparkles size={16} className="text-secondary" />
            </div>
            <div>
              <div className="coach-title-line">
                <h2 className="coach-heading">AROVIA Personal AI Coach</h2>
                <span className="coach-status-pill">
                  <span className="ai-status-dot" /> Online & Grounded
                </span>
              </div>
              <p className="coach-subtitle">
                {roleName} ({seniority}) •{' '}
                {overallScore !== null ? `Score: ${overallScore}/100` : 'Session Debrief'}
              </p>
            </div>
          </div>
        </div>

        <div className="coach-header-actions">
          {sessionData?.id && onViewReport && (
            <button
              className="coach-secondary-btn"
              onClick={() => onViewReport(sessionData.id)}
            >
              <BookOpen size={15} />
              <span>View Scorecard</span>
            </button>
          )}

          {/* Voice Auto-Play Toggle */}
          <button
            className={`coach-voice-toggle-btn ${autoPlayVoice ? 'active' : ''}`}
            onClick={() => {
              const nextVal = !autoPlayVoice;
              setAutoPlayVoice(nextVal);
              if (!nextVal) stopSpeaking();
            }}
            title={autoPlayVoice ? 'Voice Audio Mode: Active' : 'Voice Audio Mode: Muted'}
          >
            {autoPlayVoice ? <Volume2 size={16} /> : <VolumeX size={16} />}
            <span>{autoPlayVoice ? 'Voice On' : 'Voice Off'}</span>
          </button>
        </div>
      </div>

      {/* 2. Main Dual-Column Content */}
      <div className="coach-content-grid">
        {/* LEFT / CENTER: Active Chat & Debrief Stream */}
        <div className="coach-chat-stream-column">
          {/* Mobile Tabs Switcher */}
          <div className="coach-mobile-tab-nav">
            <button
              className={`mobile-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={15} /> Coaching Dialogue
            </button>
            <button
              className={`mobile-tab-btn ${activeTab === 'turns' ? 'active' : ''}`}
              onClick={() => setActiveTab('turns')}
            >
              <Layers size={15} /> Turn Explorer ({turnsList.length})
            </button>
          </div>

          {/* Messages Stream */}
          <div className="coach-messages-scroll-area">
            {error && (
              <div className="coach-error-alert">
                <AlertCircle size={18} className="text-danger flex-shrink-0" />
                <span>{error}</span>
                <button
                  className="coach-retry-text-btn"
                  onClick={() => handleSendMessage()}
                >
                  Retry
                </button>
              </div>
            )}

            {messages.map((msg) => {
              const isCoach = msg.sender === 'coach';
              const isSpeakingThis = isSpeaking && activeMessageId === msg.id;

              return (
                <div
                  key={msg.id}
                  className={`coach-message-wrapper ${isCoach ? 'from-coach' : 'from-candidate'}`}
                >
                  {isCoach && (
                    <div className="coach-msg-avatar">
                      <Bot size={18} />
                    </div>
                  )}

                  <div className="coach-msg-bubble">
                    {/* Optional Turn Context Tag */}
                    {msg.context_turn_index !== null && msg.context_turn_index !== undefined && (
                      <div className="turn-grounding-tag">
                        <Layers size={12} />
                        <span>Focused on Turn {msg.context_turn_index + 1}</span>
                      </div>
                    )}

                    {/* Formatted Content */}
                    <MarkdownRenderer content={msg.message_text} />

                    {/* Bottom Metadata & Voice Trigger */}
                    <div className="coach-msg-footer">
                      <span className="msg-timestamp">
                        {msg.created_at
                          ? new Date(msg.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Just now'}
                      </span>

                      {isCoach && (
                        <button
                          className={`coach-speaker-action-btn ${isSpeakingThis ? 'speaking' : ''}`}
                          onClick={() => speakMessage(msg.id, msg.message_text)}
                          title={isSpeakingThis ? 'Stop Audio' : 'Play Coach Voice'}
                        >
                          {isSpeakingThis ? (
                            <>
                              <VolumeX size={14} />
                              <span>Stop</span>
                            </>
                          ) : (
                            <>
                              <Volume2 size={14} />
                              <span>Listen</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* AI Thinking Animation */}
            {sending && (
              <div className="coach-message-wrapper from-coach">
                <div className="coach-msg-avatar animate-pulse">
                  <Bot size={18} />
                </div>
                <div className="coach-msg-bubble thinking-bubble">
                  <div className="typing-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span className="thinking-label">
                    Analyzing interview transcript & formulating mentor guidance...
                  </span>
                </div>
              </div>
            )}

            <div ref={messageEndRef} />
          </div>

          {/* Quick Suggestion Chips */}
          {suggestedFollowups.length > 0 && (
            <div className="coach-suggestions-bar">
              <span className="suggestions-label">
                <Sparkles size={13} className="text-secondary" /> Suggested Inquiries:
              </span>
              <div className="suggestions-chip-list">
                {suggestedFollowups.map((chip, idx) => (
                  <button
                    key={idx}
                    className="suggestion-chip-btn"
                    onClick={() => handleSendMessage(chip)}
                    disabled={sending}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input & Voice Controls Bar */}
          <div className="coach-input-container">
            {isListening && (
              <div className="voice-listening-banner">
                <div className="voice-wave-animation">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <span className="listening-text">Listening to your voice... (click Mic to submit)</span>
              </div>
            )}

            <div className="coach-input-box">
              {/* Selected Turn Tag in Input */}
              {selectedTurnIndex !== null && (
                <div className="input-turn-attachment">
                  <span>Target: Turn {selectedTurnIndex + 1}</span>
                  <button
                    className="clear-turn-tag"
                    onClick={() => setSelectedTurnIndex(null)}
                    title="Remove Turn focus"
                  >
                    ×
                  </button>
                </div>
              )}

              <textarea
                ref={inputRef}
                className="coach-textarea"
                rows={2}
                placeholder={
                  isListening
                    ? 'Speak now...'
                    : 'Ask the Coach (e.g. "Why was my caching answer weak?", "Give me a model answer for Turn 2")...'
                }
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
              />

              <div className="coach-input-actions">
                {/* Speech to Text Mic */}
                <button
                  type="button"
                  className={`coach-mic-btn ${isListening ? 'listening' : ''}`}
                  onClick={toggleListening}
                  title={isListening ? 'Stop Voice Recording' : 'Speak to AI Coach'}
                  disabled={sending}
                >
                  {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                </button>

                {/* Send Button */}
                <button
                  type="button"
                  className="coach-send-btn"
                  onClick={() => handleSendMessage()}
                  disabled={!inputMessage.trim() || sending}
                  title="Send Question (Enter)"
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT: Turn Explorer & Longitudinal Insights Panel */}
        <div className={`coach-side-explorer-column ${activeTab === 'turns' ? 'mobile-visible' : ''}`}>
          <div className="explorer-card">
            <div className="explorer-header">
              <Layers size={16} className="text-secondary" />
              <h3 className="explorer-title">Interview Turn Explorer</h3>
            </div>
            <p className="explorer-description">
              Select any turn to prime the AI Coach with the exact question, your answer, and benchmark gap analysis.
            </p>

            <div className="turns-accordion-list">
              {turnsList.length === 0 ? (
                <div className="no-turns-placeholder">
                  <p>No turn details available for this session.</p>
                </div>
              ) : (
                turnsList.map((turn, idx) => {
                  const turnIdx = turn.turn_index !== undefined ? turn.turn_index : idx;
                  const isSelected = selectedTurnIndex === turnIdx;
                  const qText = turn.question_text || `Question ${turnIdx + 1}`;
                  const score = turn.correctness_score ?? turn.relevance_score ?? 75;

                  return (
                    <div
                      key={idx}
                      className={`turn-explorer-item ${isSelected ? 'selected' : ''}`}
                    >
                      <div
                        className="turn-item-top"
                        onClick={() => setSelectedTurnIndex(isSelected ? null : turnIdx)}
                      >
                        <span className="turn-number-badge">Turn {turnIdx + 1}</span>
                        <p className="turn-question-snippet">{qText}</p>
                        <span className="turn-score-badge">{score}/100</span>
                      </div>

                      {isSelected && (
                        <div className="turn-item-expanded">
                          {turn.candidate_answer && (
                            <div className="turn-sub-block">
                              <span className="sub-label">Your Response:</span>
                              <p className="sub-text">{turn.candidate_answer}</p>
                            </div>
                          )}

                          {turn.turn_feedback && (
                            <div className="turn-sub-block feedback-block">
                              <span className="sub-label">Evaluator Note:</span>
                              <p className="sub-text">{turn.turn_feedback}</p>
                            </div>
                          )}

                          <div className="turn-action-buttons">
                            <button
                              className="turn-prompt-action"
                              onClick={() => handleSelectTurnPrompt(turnIdx, 'breakdown')}
                            >
                              Why Did I Lose Points?
                            </button>
                            <button
                              className="turn-prompt-action"
                              onClick={() => handleSelectTurnPrompt(turnIdx, 'model_answer')}
                            >
                              Get Senior Model Answer
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Quick Practice Actions */}
          <div className="explorer-card practice-card">
            <div className="explorer-header">
              <Award size={16} className="text-secondary" />
              <h3 className="explorer-title">Targeted Practice</h3>
            </div>
            <p className="explorer-description">
              Retake this interview track or drill into targeted topics recommended by your coach.
            </p>
            <button
              className="coach-retake-btn"
              onClick={onStartSetup}
            >
              <RotateCcw size={15} />
              <span>Start New Calibrated Interview</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CoachView;

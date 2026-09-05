import { useState, useCallback, useEffect, useRef } from 'react';
import { voiceService } from '../services/voiceService';

/**
 * Reactive hook for AI Coach speech synthesis with message tracking and audio lifecycle.
 */
export function useCoachVoice() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [activeMessageId, setActiveMessageId] = useState(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      voiceService.stop();
    };
  }, []);

  const stopSpeaking = useCallback(() => {
    voiceService.stop();
    if (isMountedRef.current) {
      setIsSpeaking(false);
      setActiveMessageId(null);
    }
  }, []);

  const speakMessage = useCallback(
    (messageId, text, { onComplete } = {}) => {
      if (!text) return;

      // If currently speaking this same message, clicking again acts as a stop toggle
      if (isSpeaking && activeMessageId === messageId) {
        stopSpeaking();
        return;
      }

      voiceService.stop();
      setIsSpeaking(true);
      setActiveMessageId(messageId);

      voiceService.speak(text, {
        onStart: () => {
          if (isMountedRef.current) {
            setIsSpeaking(true);
            setActiveMessageId(messageId);
          }
        },
        onEnd: () => {
          if (isMountedRef.current) {
            setIsSpeaking(false);
            setActiveMessageId(null);
            if (onComplete) onComplete();
          }
        },
        onError: () => {
          if (isMountedRef.current) {
            setIsSpeaking(false);
            setActiveMessageId(null);
          }
        },
      });
    },
    [isSpeaking, activeMessageId, stopSpeaking]
  );

  return {
    isSpeaking,
    activeMessageId,
    speakMessage,
    stopSpeaking,
  };
}

export default useCoachVoice;

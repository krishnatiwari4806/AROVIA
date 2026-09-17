import { useState, useEffect, useCallback, useRef } from 'react';
import { getAroviaSettings } from '../services/settingsManager.js';

/**
 * Maps session preferred language to browser speech recognition BCP-47 locale.
 * en / en-us -> en-US
 * en-in -> en-IN
 * hi -> hi-IN
 * hinglish -> hi-IN (code-switching uses hi-IN locale)
 */
export function getSpeechRecognitionLocale(preferredLanguage) {
  const lang = (preferredLanguage || '').toLowerCase().trim();
  if (lang === 'hi' || lang === 'hinglish') {
    return 'hi-IN';
  }
  if (lang === 'en-in' || lang === 'en_in') {
    return 'en-IN';
  }
  return 'en-US';
}

/**
 * Recognition lifecycle states:
 * IDLE -> STARTING -> LISTENING -> STOPPING -> IDLE
 */
export const RecognitionState = {
  IDLE: 'IDLE',
  STARTING: 'STARTING',
  LISTENING: 'LISTENING',
  STOPPING: 'STOPPING',
};

/**
 * Hardened Browser-native Speech-to-Text (STT) hook using SpeechRecognition / webkitSpeechRecognition.
 * Fully referentially stable public callbacks with state machine guards against race conditions.
 */
export function useSpeechRecognition({ onTranscriptUpdate, preferredLanguage } = {}) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef(null);
  const stateRef = useRef(RecognitionState.IDLE);
  const isListeningRef = useRef(false);
  const mountedRef = useRef(true);
  const activeTurnIdRef = useRef(null);

  const preferredLanguageRef = useRef(preferredLanguage);
  const onTranscriptUpdateRef = useRef(onTranscriptUpdate);

  // Keep latest callback and language references updated without recreating instances
  useEffect(() => {
    preferredLanguageRef.current = preferredLanguage;
    if (recognitionRef.current && preferredLanguage) {
      try {
        recognitionRef.current.lang = getSpeechRecognitionLocale(preferredLanguage);
      } catch {
        // ignore if browser throws on active mutation
      }
    }
  }, [preferredLanguage]);

  useEffect(() => {
    onTranscriptUpdateRef.current = onTranscriptUpdate;
  }, [onTranscriptUpdate]);

  useEffect(() => {
    mountedRef.current = true;

    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        setIsSupported(true);
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;

        const settings = getAroviaSettings();
        recognition.lang = preferredLanguageRef.current
          ? getSpeechRecognitionLocale(preferredLanguageRef.current)
          : (settings.languageVoice?.language || 'en-US');

        recognition.onstart = () => {
          stateRef.current = RecognitionState.LISTENING;
          isListeningRef.current = true;
          if (mountedRef.current) {
            setIsListening(true);
            setError(null);
          }
        };

        recognition.onresult = (event) => {
          let currentTranscript = '';
          for (let i = 0; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          if (onTranscriptUpdateRef.current) {
            onTranscriptUpdateRef.current(currentTranscript, activeTurnIdRef.current);
          }
        };

        recognition.onerror = (event) => {
          const errType = event?.error;
          // 'no-speech' is a normal silence timeout in Chrome; 'aborted' occurs on intentional cancellation
          if (errType !== 'no-speech' && errType !== 'aborted') {
            console.warn('SpeechRecognition diagnostic error:', errType);
            if (mountedRef.current) {
              setError(errType);
            }
          }
          stateRef.current = RecognitionState.IDLE;
          isListeningRef.current = false;
          if (mountedRef.current) {
            setIsListening(false);
          }
        };

        recognition.onend = () => {
          stateRef.current = RecognitionState.IDLE;
          isListeningRef.current = false;
          if (mountedRef.current) {
            setIsListening(false);
          }
        };

        recognitionRef.current = recognition;
      }
    }

    return () => {
      mountedRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore cleanup abort exception
        }
        stateRef.current = RecognitionState.IDLE;
        isListeningRef.current = false;
      }
    };
  }, []); // Run ONCE on mount

  const startListening = useCallback((turnId = null) => {
    const settings = getAroviaSettings();
    if (settings.languageVoice && settings.languageVoice.sttEnabled === false) {
      if (mountedRef.current) {
        setError('Speech recognition is disabled in Settings.');
      }
      return;
    }

    // Mutual exclusion: Cancel active TTS synthesis before capturing microphone
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
    }

    if (mountedRef.current) {
      setError(null);
    }

    // Guard against starting if already STARTING or LISTENING or STOPPING
    if (stateRef.current !== RecognitionState.IDLE) {
      return;
    }

    if (recognitionRef.current) {
      try {
        stateRef.current = RecognitionState.STARTING;
        activeTurnIdRef.current = turnId;

        const langToUse = preferredLanguageRef.current
          ? getSpeechRecognitionLocale(preferredLanguageRef.current)
          : (settings.languageVoice?.language || 'en-US');
        recognitionRef.current.lang = langToUse;

        recognitionRef.current.start();
      } catch (err) {
        stateRef.current = RecognitionState.IDLE;
        // InvalidStateError occurs if browser has not yet finished stopping previous session
        if (err.name !== 'InvalidStateError') {
          console.warn('SpeechRecognition start diagnostic:', err);
        }
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    if (stateRef.current === RecognitionState.IDLE || stateRef.current === RecognitionState.STOPPING) {
      return;
    }

    if (recognitionRef.current) {
      stateRef.current = RecognitionState.STOPPING;
      try {
        recognitionRef.current.stop();
      } catch {
        stateRef.current = RecognitionState.IDLE;
        if (mountedRef.current) {
          setIsListening(false);
        }
      }
    }
  }, []);

  const toggleListening = useCallback((turnId = null) => {
    if (stateRef.current === RecognitionState.LISTENING || stateRef.current === RecognitionState.STARTING) {
      stopListening();
    } else if (stateRef.current === RecognitionState.IDLE) {
      startListening(turnId);
    }
  }, [startListening, stopListening]);

  return {
    startListening,
    stopListening,
    toggleListening,
    isListening,
    error,
    isSupported,
  };
}

export default useSpeechRecognition;

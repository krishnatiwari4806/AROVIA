import { useState, useEffect, useCallback, useRef } from 'react';
import { getAroviaSettings } from '../services/settingsManager';

/**
 * Browser-native Speech-to-Text (STT) hook using window.webkitSpeechRecognition / SpeechRecognition.
 * Dynamically applies language preferences from centralized settings.
 */
export function useSpeechRecognition({ onTranscriptUpdate } = {}) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const [isSupported, setIsSupported] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        setIsSupported(true);
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;

        const settings = getAroviaSettings();
        recognition.lang = settings.languageVoice?.language || 'en-US';

        recognition.onresult = (event) => {
          let currentTranscript = '';
          for (let i = 0; i < event.results.length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          if (onTranscriptUpdate) {
            onTranscriptUpdate(currentTranscript);
          }
        };

        recognition.onerror = (event) => {
          console.warn('SpeechRecognition error:', event.error);
          setError(event.error);
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
      }
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, [onTranscriptUpdate]);

  const startListening = useCallback(() => {
    const settings = getAroviaSettings();
    if (settings.languageVoice && settings.languageVoice.sttEnabled === false) {
      setError('Speech recognition is disabled in Settings.');
      return;
    }

    setError(null);
    if (recognitionRef.current && !isListening) {
      try {
        // Refresh language preference before starting
        recognitionRef.current.lang = settings.languageVoice?.language || 'en-US';
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.warn('Failed to start SpeechRecognition:', err);
      }
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      setIsListening(false);
    }
  }, [isListening]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

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

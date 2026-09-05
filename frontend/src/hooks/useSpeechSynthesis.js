import { useState, useEffect, useCallback, useRef } from 'react';
import { getAroviaSettings } from '../services/settingsManager';

/**
 * Browser-native Text-to-Speech (TTS) hook using window.speechSynthesis.
 * Dynamically calibrates to user preferences (voice, rate/speed, volume, language).
 */
export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);
  const utteranceRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      setIsSupported(true);

      const updateVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices && voices.length > 0) {
          setAvailableVoices(voices);
        }
      };

      updateVoices();
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const speak = useCallback((text, onEnd, customOptions = {}) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window) || !text) {
      return;
    }

    // Cancel any prior speech
    window.speechSynthesis.cancel();

    const settings = getAroviaSettings();
    const voicePrefs = settings.languageVoice || {};

    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;

    // Apply speed / rate
    utterance.rate = customOptions.rate ?? voicePrefs.voiceSpeed ?? 1.0;
    // Apply volume
    utterance.volume = customOptions.volume ?? voicePrefs.voiceVolume ?? 1.0;
    utterance.pitch = customOptions.pitch ?? 1.0;

    // Select voice matching preferred URI or target language
    const voices = window.speechSynthesis.getVoices();
    let selectedVoice = null;

    if (customOptions.voiceURI || voicePrefs.voiceURI) {
      const targetURI = customOptions.voiceURI || voicePrefs.voiceURI;
      selectedVoice = voices.find((v) => v.voiceURI === targetURI || v.name === targetURI);
    }

    if (!selectedVoice) {
      const targetLang = customOptions.language || voicePrefs.language || 'en-US';
      const langPrefix = targetLang.split('-')[0];

      selectedVoice =
        voices.find((v) => v.lang === targetLang && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha'))) ||
        voices.find((v) => v.lang === targetLang) ||
        voices.find((v) => v.lang.startsWith(langPrefix)) ||
        voices.find((v) => v.lang.startsWith('en'));
    }

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis error:', e);
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return {
    speak,
    cancel,
    isSpeaking,
    isSupported,
    availableVoices,
  };
}

export default useSpeechSynthesis;

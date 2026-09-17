import { useState, useEffect, useCallback, useRef } from 'react';
import { getAroviaSettings } from '../services/settingsManager.js';

/**
 * Maps session preferred language to browser speech synthesis BCP-47 locale.
 * en / en-us -> en-US
 * en-in -> en-IN
 * hi -> hi-IN
 * hinglish -> hi-IN
 */
export function getSpeechSynthesisLocale(preferredLanguage) {
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
 * Hardened Browser-native Text-to-Speech (TTS) hook using window.speechSynthesis.
 * Dynamically calibrates to user preferences (voice, rate/speed, volume, language)
 * with robust Indian English and Hindi voice matching and phoneme assignment.
 */
export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);
  const utteranceRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      setIsSupported(true);

      const updateVoices = () => {
        try {
          const voices = window.speechSynthesis.getVoices();
          if (voices && voices.length > 0 && mountedRef.current) {
            setAvailableVoices(voices);
          }
        } catch {
          // ignore
        }
      };

      updateVoices();
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }

    return () => {
      mountedRef.current = false;
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
      if (mountedRef.current) {
        setIsSpeaking(false);
      }
    }
  }, []);

  const speak = useCallback((text, onEnd, customOptions = {}) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window) || !text) {
      if (onEnd) onEnd();
      return;
    }

    // Cancel any prior speech
    try {
      window.speechSynthesis.cancel();
    } catch {
      // ignore
    }

    const settings = getAroviaSettings();
    const voicePrefs = settings.languageVoice || {};

    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;

    // Apply speed / rate
    utterance.rate = customOptions.rate ?? voicePrefs.voiceSpeed ?? 1.0;
    // Apply volume
    utterance.volume = customOptions.volume ?? voicePrefs.voiceVolume ?? 1.0;
    utterance.pitch = customOptions.pitch ?? 1.0;

    // Resolve target language
    const rawLang = customOptions.language || voicePrefs.language || 'en-US';
    const targetLang = getSpeechSynthesisLocale(rawLang);
    utterance.lang = targetLang;

    // Select voice matching preferred URI or target language
    const voices = window.speechSynthesis.getVoices();
    let selectedVoice = null;

    if (customOptions.voiceURI || voicePrefs.voiceURI) {
      const targetURI = customOptions.voiceURI || voicePrefs.voiceURI;
      selectedVoice = voices.find((v) => v.voiceURI === targetURI || v.name === targetURI);
    }

    if (!selectedVoice && voices.length > 0) {
      const isHindiTarget = targetLang.startsWith('hi');
      const isIndianEnglishTarget = targetLang === 'en-IN';

      if (isHindiTarget) {
        // Prioritize Hindi natural voices, then standard Hindi, then Indian English
        selectedVoice =
          voices.find((v) => (v.lang === 'hi-IN' || v.lang === 'hi_IN') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Kalpana') || v.name.includes('Swara') || v.name.includes('Madhur') || v.name.includes('Hemant'))) ||
          voices.find((v) => v.lang === 'hi-IN' || v.lang === 'hi_IN' || v.lang.startsWith('hi')) ||
          voices.find((v) => v.lang === 'en-IN' || v.lang === 'en_IN') ||
          null;
      } else if (isIndianEnglishTarget) {
        // Prioritize Indian English voices
        selectedVoice =
          voices.find((v) => (v.lang === 'en-IN' || v.lang === 'en_IN') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Ravi') || v.name.includes('Heera') || v.name.includes('Neerja') || v.name.includes('Prabhat'))) ||
          voices.find((v) => v.lang === 'en-IN' || v.lang === 'en_IN') ||
          null;
      }

      if (!selectedVoice) {
        const langPrefix = targetLang.split('-')[0];
        selectedVoice =
          voices.find((v) => (v.lang === targetLang || v.lang.replace('_', '-') === targetLang) && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny') || v.name.includes('Guy'))) ||
          voices.find((v) => v.lang === targetLang || v.lang.replace('_', '-') === targetLang) ||
          voices.find((v) => v.lang.startsWith(langPrefix)) ||
          voices.find((v) => v.lang.startsWith('en')) ||
          voices[0] ||
          null;
      }
    }

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = () => {
      if (mountedRef.current) {
        setIsSpeaking(true);
      }
    };

    utterance.onend = () => {
      if (mountedRef.current) {
        setIsSpeaking(false);
      }
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      if (e?.error !== 'interrupted' && e?.error !== 'canceled') {
        console.warn('SpeechSynthesis error:', e);
      }
      if (mountedRef.current) {
        setIsSpeaking(false);
      }
    };

    try {
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('speechSynthesis.speak error:', err);
      if (mountedRef.current) {
        setIsSpeaking(false);
      }
    }
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

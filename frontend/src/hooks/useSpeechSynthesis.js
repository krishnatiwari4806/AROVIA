import { useState, useEffect, useCallback, useRef } from 'react';
import { getAroviaSettings } from '../services/settingsManager.js';

/**
 * Normalizes speech text for clean, natural conversational cadence before Web Speech API dispatch.
 * Deterministic, conservative, and non-destructive:
 * - Strips code backticks, markdown markers, and superfluous quotes.
 * - Replaces em-dashes, en-dashes, double dashes, and semicolons with commas to create natural breath pauses.
 * - Normalizes duplicate punctuation and collapses whitespace.
 * - Strictly preserves technical terms (Redis, PostgreSQL, Docker, etc.) without modification.
 */
export function normalizeSpeechCadence(text) {
  if (!text || typeof text !== 'string') return '';

  let cleaned = text.trim();

  // Strip code blocks and inline backticks
  cleaned = cleaned.replace(/```[\s\S]*?```/g, '');
  cleaned = cleaned.replace(/`([^`]+)`/g, '$1');

  // Strip leading/trailing surrounding quotes if wrapped
  if ((cleaned.startsWith('"') && cleaned.endsWith('"')) || (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
    cleaned = cleaned.slice(1, -1).trim();
  }
  if ((cleaned.startsWith('“') && cleaned.endsWith('”')) || (cleaned.startsWith('‘') && cleaned.endsWith('’'))) {
    cleaned = cleaned.slice(1, -1).trim();
  }

  // Replace em-dashes, en-dashes, double dashes with a comma and space for a natural pause
  cleaned = cleaned.replace(/\s*[—–]\s*/g, ', ');
  cleaned = cleaned.replace(/\s*--\s*/g, ', ');

  // Replace semicolons with commas to guide browser TTS engines into a natural pause
  cleaned = cleaned.replace(/\s*;\s*/g, ', ');

  // Normalize duplicate commas or comma-question combinations
  cleaned = cleaned.replace(/,\s*,+/g, ',');
  cleaned = cleaned.replace(/,\s*\?/g, '?');

  // Collapse multiple whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim();

  return cleaned;
}

/**
 * Maps session preferred language to browser speech synthesis BCP-47 locale.
 * en / en-us -> en-US
 * en-in -> en-IN
 * hinglish -> en-IN (Optimal Indian technical bilingual cadence, prevents Hindi phoneme slurring)
 * hi -> hi-IN
 */
export function getSpeechSynthesisLocale(preferredLanguage) {
  const lang = (preferredLanguage || '').toLowerCase().trim();
  if (lang === 'hi') {
    return 'hi-IN';
  }
  if (lang === 'hinglish' || lang === 'en-in' || lang === 'en_in') {
    return 'en-IN';
  }
  return 'en-US';
}

/**
 * Resolves the real voice capability status for a selected interview language.
 * Pure and non-destructive: does not speak, does not request mic, does not throw.
 *
 * @param {Array} voices - Array of SpeechSynthesisVoice objects from browser
 * @param {boolean} isSupported - Whether window.speechSynthesis is supported in browser
 * @param {string} preferredLanguage - 'en', 'hi', or 'hinglish'
 * @returns {{ status: string, label: string, detail: string, type: 'available'|'fallback'|'unavailable' }}
 */
export function resolveVoiceCapability(voices, isSupported = true, preferredLanguage = 'en') {
  if (!isSupported) {
    return {
      status: 'unavailable',
      label: 'Voice: Not available on this browser',
      detail: 'Interviews will use on-screen text prompts.',
      type: 'unavailable',
    };
  }

  const lang = (preferredLanguage || 'en').toLowerCase().trim();

  if (!voices || voices.length === 0) {
    return {
      status: 'default_available',
      label: 'Voice: Default system voice',
      detail: 'Browser speech synthesis is active.',
      type: 'fallback',
    };
  }

  const normVoices = voices.map((v) => ({
    ...v,
    _normLang: (v.lang || '').replace('_', '-').toLowerCase(),
  }));

  if (lang === 'hinglish') {
    const enInVoice = normVoices.find((v) => v._normLang === 'en-in');
    if (enInVoice) {
      return {
        status: 'indian_english_available',
        label: 'Voice: Indian English available',
        detail: 'Hinglish uses Indian English pronunciation for technical terms.',
        type: 'available',
      };
    }
    const englishFallback = normVoices.find((v) => v._normLang.startsWith('en'));
    if (englishFallback) {
      return {
        status: 'english_fallback',
        label: 'Voice: English fallback',
        detail: 'Indian English voice not detected; using standard English voice.',
        type: 'fallback',
      };
    }
    return {
      status: 'system_fallback',
      label: 'Voice: English fallback',
      detail: 'Using system default voice.',
      type: 'fallback',
    };
  }

  if (lang === 'hi') {
    const hiVoice = normVoices.find((v) => v._normLang.startsWith('hi'));
    if (hiVoice) {
      return {
        status: 'hindi_available',
        label: 'Voice: Hindi available',
        detail: 'Native Hindi speech synthesis voice detected.',
        type: 'available',
      };
    }
    const fallbackVoice = normVoices.find((v) => v._normLang.startsWith('en'));
    if (fallbackVoice) {
      return {
        status: 'english_fallback',
        label: 'Voice: English fallback',
        detail: 'Hindi voice not installed on this OS; questions will use system English voice.',
        type: 'fallback',
      };
    }
    return {
      status: 'system_fallback',
      label: 'Voice: System fallback',
      detail: 'Using default system voice.',
      type: 'fallback',
    };
  }

  // English
  const englishVoice = normVoices.find((v) => v._normLang.startsWith('en'));
  if (englishVoice) {
    const isIndian = englishVoice._normLang === 'en-in';
    return {
      status: isIndian ? 'indian_english_available' : 'english_available',
      label: isIndian ? 'Voice: Indian English available' : 'Voice: English available',
      detail: 'High-clarity English speech synthesis ready.',
      type: 'available',
    };
  }

  return {
    status: 'system_fallback',
    label: 'Voice: System fallback',
    detail: 'Using available system voice.',
    type: 'fallback',
  };
}

/**
 * Pure voice matching helper with priority matching for Indian English, Hindi, Natural, and standard voices.
 * Ensures graceful fallback across Chrome, Edge, Windows, macOS, and Android.
 */
export function findBestVoice(voices, targetLang, targetURI = null) {
  if (!voices || voices.length === 0) return null;

  if (targetURI) {
    const matched = voices.find((v) => v.voiceURI === targetURI || v.name === targetURI);
    if (matched) return matched;
  }

  const isHindiTarget = targetLang.startsWith('hi');
  const isIndianEnglishTarget = targetLang === 'en-IN' || targetLang === 'en_IN';

  if (isHindiTarget) {
    return (
      // 1. hi-IN natural / neural
      voices.find((v) => (v.lang === 'hi-IN' || v.lang === 'hi_IN') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Kalpana') || v.name.includes('Swara') || v.name.includes('Madhur') || v.name.includes('Hemant'))) ||
      // 2. hi-IN standard
      voices.find((v) => v.lang === 'hi-IN' || v.lang === 'hi_IN' || v.lang.startsWith('hi')) ||
      // 3. Fallback to en-IN natural
      voices.find((v) => (v.lang === 'en-IN' || v.lang === 'en_IN') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Neerja') || v.name.includes('Prabhat'))) ||
      // 4. Any en-IN voice
      voices.find((v) => v.lang === 'en-IN' || v.lang === 'en_IN') ||
      // 5. Any English voice
      voices.find((v) => v.lang.startsWith('en')) ||
      voices[0] ||
      null
    );
  } else if (isIndianEnglishTarget) {
    return (
      // 1. en-IN natural / neural
      voices.find((v) => (v.lang === 'en-IN' || v.lang === 'en_IN') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Ravi') || v.name.includes('Heera') || v.name.includes('Neerja') || v.name.includes('Prabhat'))) ||
      // 2. en-IN standard
      voices.find((v) => v.lang === 'en-IN' || v.lang === 'en_IN') ||
      // 3. en-GB natural
      voices.find((v) => (v.lang === 'en-GB' || v.lang === 'en_GB') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('George') || v.name.includes('Mia') || v.name.includes('Oliver') || v.name.includes('Sonia'))) ||
      // 4. en-US natural
      voices.find((v) => (v.lang === 'en-US' || v.lang === 'en_US') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Jenny') || v.name.includes('Guy') || v.name.includes('Samantha') || v.name.includes('Aria'))) ||
      // 5. Any English voice
      voices.find((v) => v.lang.startsWith('en')) ||
      voices[0] ||
      null
    );
  }

  const langPrefix = targetLang.split('-')[0];
  return (
    voices.find((v) => (v.lang === targetLang || v.lang.replace('_', '-') === targetLang) && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny') || v.name.includes('Guy'))) ||
    voices.find((v) => v.lang === targetLang || v.lang.replace('_', '-') === targetLang) ||
    voices.find((v) => v.lang.startsWith(langPrefix)) ||
    voices.find((v) => v.lang.startsWith('en')) ||
    voices[0] ||
    null
  );
}

/**
 * Hardened Browser-native Text-to-Speech (TTS) hook using window.speechSynthesis.
 * Dynamically calibrates to user preferences (voice, rate/speed, volume, language)
 * with robust Indian English and Hindi voice matching and cadence normalization.
 * Optimized with voice caching to eliminate repetitive enumeration during live turns.
 */
export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);
  const utteranceRef = useRef(null);
  const mountedRef = useRef(true);
  const voicesCacheRef = useRef([]);
  const voiceMapRef = useRef(new Map());

  useEffect(() => {
    mountedRef.current = true;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      setIsSupported(true);

      const updateVoices = () => {
        try {
          const voices = window.speechSynthesis.getVoices();
          if (voices && voices.length > 0) {
            voicesCacheRef.current = voices;
            voiceMapRef.current.clear();
            if (mountedRef.current) {
              setAvailableVoices(voices);
            }
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

    const speechText = normalizeSpeechCadence(text);
    if (!speechText) {
      if (onEnd) onEnd();
      return;
    }

    const settings = getAroviaSettings();
    const voicePrefs = settings.languageVoice || {};

    const utterance = new SpeechSynthesisUtterance(speechText);
    utteranceRef.current = utterance;

    // Apply speed / rate (default calibrated to 0.93 for clear, authoritative interviewer cadence)
    utterance.rate = customOptions.rate ?? voicePrefs.voiceSpeed ?? 0.93;
    // Apply volume
    utterance.volume = customOptions.volume ?? voicePrefs.voiceVolume ?? 1.0;
    utterance.pitch = customOptions.pitch ?? 1.0;

    // Resolve target language
    const rawLang = customOptions.language || voicePrefs.language || 'en-US';
    const targetLang = getSpeechSynthesisLocale(rawLang);

    // Select voice using cached map or fast lookup
    const targetURI = customOptions.voiceURI || voicePrefs.voiceURI || null;
    const cacheKey = `${targetLang}::${targetURI || 'default'}`;

    let selectedVoice = voiceMapRef.current.get(cacheKey);
    if (!selectedVoice) {
      const voices = voicesCacheRef.current.length > 0
        ? voicesCacheRef.current
        : window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        selectedVoice = findBestVoice(voices, targetLang, targetURI);
        if (selectedVoice) {
          voiceMapRef.current.set(cacheKey, selectedVoice);
        }
      }
    }

    if (selectedVoice) {
      utterance.voice = selectedVoice;
      // Synchronize utterance.lang with selected voice's actual language
      utterance.lang = selectedVoice.lang ? selectedVoice.lang.replace('_', '-') : targetLang;
    } else {
      utterance.lang = targetLang;
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

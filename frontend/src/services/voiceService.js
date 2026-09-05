/**
 * Voice Provider Architecture for AROVIA Personal AI Coach.
 *
 * Implements an extensible provider pattern separating AI Coach reasoning
 * from speech synthesis and audio reproduction.
 */

import { getAroviaSettings } from './settingsManager';

class BaseVoiceProvider {
  async speak(text, options = {}) {
    throw new Error('speak() must be implemented by Voice Provider.');
  }

  stop() {
    throw new Error('stop() must be implemented by Voice Provider.');
  }

  pause() {}
  resume() {}
}

/**
 * High-performance browser-native Web Speech API Provider.
 * Automatically filters for high-fidelity neural/natural voice models.
 */
class BrowserVoiceProvider extends BaseVoiceProvider {
  constructor() {
    super();
    this.synth = typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis : null;
    this.currentUtterance = null;
  }

  getAvailableVoices() {
    if (!this.synth) return [];
    return this.synth.getVoices();
  }

  getBestNaturalVoice(preferredLang = 'en-US', preferredName = '') {
    const voices = this.getAvailableVoices();
    if (!voices || voices.length === 0) return null;

    if (preferredName) {
      const match = voices.find(
        (v) => v.name === preferredName || v.voiceURI === preferredName
      );
      if (match) return match;
    }

    // Rank natural / premium neural voices highest
    const naturalMatches = voices.filter(
      (v) =>
        (v.lang === preferredLang || v.lang.startsWith(preferredLang.split('-')[0])) &&
        (v.name.includes('Natural') ||
          v.name.includes('Google') ||
          v.name.includes('Neural') ||
          v.name.includes('Jenny') ||
          v.name.includes('Guy') ||
          v.name.includes('Samantha') ||
          v.name.includes('Siri') ||
          v.name.includes('Daniel') ||
          v.name.includes('Arthur'))
    );

    if (naturalMatches.length > 0) {
      return naturalMatches[0];
    }

    const exactLang = voices.find((v) => v.lang === preferredLang);
    if (exactLang) return exactLang;

    const prefixLang = voices.find((v) => v.lang.startsWith(preferredLang.split('-')[0]));
    if (prefixLang) return prefixLang;

    return voices[0] || null;
  }

  async speak(text, { onStart, onEnd, onError, rate, volume, pitch, voiceName } = {}) {
    if (!this.synth || !text) {
      if (onEnd) onEnd();
      return;
    }

    // Stop any ongoing audio playback cleanly
    this.stop();

    // Strip markdown formatting characters for natural speech synthesis
    const cleanSpeechText = text
      .replace(/[#*_`~[\]()]/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/\n+/g, '. ')
      .trim();

    if (!cleanSpeechText) {
      if (onEnd) onEnd();
      return;
    }

    const settings = getAroviaSettings();
    const voicePrefs = settings.languageVoice || {};

    const utterance = new SpeechSynthesisUtterance(cleanSpeechText);
    this.currentUtterance = utterance;

    utterance.rate = rate ?? voicePrefs.voiceSpeed ?? 1.0;
    utterance.volume = volume ?? voicePrefs.voiceVolume ?? 1.0;
    utterance.pitch = pitch ?? 1.0;

    const selectedVoice = this.getBestNaturalVoice(
      voicePrefs.language || 'en-US',
      voiceName || voicePrefs.voiceURI
    );

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = () => {
      if (onStart) onStart();
    };

    utterance.onend = () => {
      this.currentUtterance = null;
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      console.warn('Speech synthesis playback error:', e);
      this.currentUtterance = null;
      if (onError) onError(e);
      if (onEnd) onEnd();
    };

    this.synth.speak(utterance);
  }

  stop() {
    if (this.synth) {
      this.synth.cancel();
      this.currentUtterance = null;
    }
  }

  pause() {
    if (this.synth) {
      this.synth.pause();
    }
  }

  resume() {
    if (this.synth) {
      this.synth.resume();
    }
  }
}

class VoiceServiceManager {
  constructor() {
    this.provider = new BrowserVoiceProvider();
  }

  setProvider(customProvider) {
    if (customProvider instanceof BaseVoiceProvider) {
      this.provider.stop();
      this.provider = customProvider;
    }
  }

  speak(text, callbacks) {
    return this.provider.speak(text, callbacks);
  }

  stop() {
    return this.provider.stop();
  }

  pause() {
    return this.provider.pause();
  }

  resume() {
    return this.provider.resume();
  }

  getAvailableVoices() {
    if (this.provider instanceof BrowserVoiceProvider) {
      return this.provider.getAvailableVoices();
    }
    return [];
  }
}

export const voiceService = new VoiceServiceManager();
export default voiceService;

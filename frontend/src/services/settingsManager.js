/**
 * Centralized Settings Management Service for AROVIA.
 * Manages interview defaults, speech synthesis/recognition preferences,
 * accessibility tokens, visual themes, and local privacy options.
 */

const STORAGE_KEY = 'arovia_settings';

export const DEFAULT_SETTINGS = {
  interview: {
    defaultRole: 'Backend',
    defaultSeniority: 'Senior',
    defaultFocus: ['Technical Core', 'Behavioral'],
    defaultSessionMode: 'standard', // 'standard' | 'quick'
    defaultQuestionCount: 6,
  },
  languageVoice: {
    language: 'en-US',
    voiceURI: '', // empty = auto pick standard natural voice
    voiceSpeed: 1.0, // 0.75x - 1.5x
    voiceVolume: 1.0, // 0.0 - 1.0
    autoPlayQuestions: true,
    sttEnabled: true,
  },
  ai: {
    difficulty: 'calibrated', // 'standard' | 'calibrated' | 'challenging'
    adaptiveProbing: true,
    feedbackDetail: 'comprehensive', // 'concise' | 'comprehensive'
  },
  appearance: {
    theme: 'dark', // 'dark' | 'light' | 'system'
    reduceMotion: false,
    animationsEnabled: true,
  },
  notifications: {
    sessionReminders: true,
    reportReadyAlerts: true,
    progressMilestones: true,
    systemUpdates: false,
  },
  privacy: {
    saveSessionHistory: true,
    analyticsSharing: false,
  },
  accessibility: {
    highContrast: false,
    largerText: false,
    keyboardNavAssistance: true,
  },
};

/**
 * Load settings from LocalStorage or return defaults.
 */
export function getAroviaSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    return {
      interview: { ...DEFAULT_SETTINGS.interview, ...(parsed.interview || {}) },
      languageVoice: { ...DEFAULT_SETTINGS.languageVoice, ...(parsed.languageVoice || {}) },
      ai: { ...DEFAULT_SETTINGS.ai, ...(parsed.ai || {}) },
      appearance: { ...DEFAULT_SETTINGS.appearance, ...(parsed.appearance || {}) },
      notifications: { ...DEFAULT_SETTINGS.notifications, ...(parsed.notifications || {}) },
      privacy: { ...DEFAULT_SETTINGS.privacy, ...(parsed.privacy || {}) },
      accessibility: { ...DEFAULT_SETTINGS.accessibility, ...(parsed.accessibility || {}) },
    };
  } catch (e) {
    console.warn('Could not load arovia_settings from storage:', e);
    return { ...DEFAULT_SETTINGS };
  }
}

/**
 * Save settings to LocalStorage and trigger system effects (theme, motion, etc.).
 */
export function saveAroviaSettings(newSettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
    applySystemSettings(newSettings);
    // Dispatch custom event so active components can re-render immediately if needed
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('arovia_settings_changed', { detail: newSettings }));
    }
  } catch (e) {
    console.warn('Could not save arovia_settings to storage:', e);
  }
}

/**
 * Apply live DOM changes based on accessibility and theme settings.
 */
export function applySystemSettings(settings = getAroviaSettings()) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // 1. Reduced Motion
  if (settings.appearance?.reduceMotion || settings.accessibility?.reduceMotion) {
    root.classList.add('reduced-motion');
  } else {
    root.classList.remove('reduced-motion');
  }

  // 2. High Contrast
  if (settings.accessibility?.highContrast) {
    root.classList.add('high-contrast');
  } else {
    root.classList.remove('high-contrast');
  }

  // 3. Larger Text
  if (settings.accessibility?.largerText) {
    root.classList.add('larger-text');
  } else {
    root.classList.remove('larger-text');
  }

  // 4. Theme attribute
  if (settings.appearance?.theme) {
    root.setAttribute('data-theme', settings.appearance.theme);
  }
}

/**
 * API client service for AROVIA backend endpoints.
 */

const API_BASE = '/api/v1';

function getAuthHeader() {
  const token = localStorage.getItem('arovia_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(data.detail || data.message || 'API request failed');
    error.status = response.status;
    error.code = data.error_code;
    error.details = data.details;
    throw error;
  }

  return data;
}

export const api = {
  // Presets & Setup
  getPresets: () => request('/interviews/presets'),
  createSession: (payload) => request('/interviews/sessions', { method: 'POST', body: JSON.stringify(payload) }),
  getActiveSession: () => request('/interviews/sessions/active'),
  getSession: (sessionId) => request(`/interviews/sessions/${sessionId}`),
  abandonSession: (sessionId) => request(`/interviews/sessions/${sessionId}/abandon`, { method: 'POST' }),

  // Turn Progression & Adaptive Loop
  startInterview: (sessionId) => request(`/interviews/sessions/${sessionId}/start`, { method: 'POST' }),
  getCurrentTurn: (sessionId) => request(`/interviews/sessions/${sessionId}/current-turn`),
  submitTurnAnswer: (sessionId, turnId, payload) =>
    request(`/interviews/sessions/${sessionId}/turns/${turnId}/answer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getSessionTurns: (sessionId) => request(`/interviews/sessions/${sessionId}/turns`),
};

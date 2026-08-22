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

  // Evaluation & Scorecard
  evaluateSession: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/evaluate`, { method: 'POST' }),
  getSessionEvaluation: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/evaluation`),

  // Resume Ingestion & Career Profile
  getMyResume: () => request('/resumes/me'),
  uploadResume: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('arovia_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch(`${API_BASE}/resumes/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const error = new Error(data.detail || data.message || 'Resume upload failed');
      error.status = response.status;
      throw error;
    }
    return data;
  },
  deleteResume: () => request('/resumes/me', { method: 'DELETE' }),
};

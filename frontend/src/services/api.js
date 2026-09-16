/**
 * API client service for AROVIA backend endpoints.
 * Includes single-flight transparent access-token refresh and request retry.
 */

const API_BASE = '/api/v1';

let refreshPromise = null;

function getAuthHeader() {
  const token = localStorage.getItem('arovia_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Execute single-flight refresh request to /auth/refresh using HttpOnly cookie.
 * If multiple requests fail with TOKEN_EXPIRED concurrently, only ONE refresh request is dispatched.
 */
async function getRefreshedToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const data = await response.json().catch(() => ({}));

        if (response.ok && data && data.access_token) {
          localStorage.setItem('arovia_token', data.access_token);
          if (data.user) {
            try {
              localStorage.setItem('arovia_candidate_profile', JSON.stringify(data.user));
            } catch {
              // ignore storage serialization errors
            }
          }
          if (typeof window !== 'undefined') {
            window.dispatchEvent(
              new CustomEvent('arovia_token_refreshed', { detail: data })
            );
          }
          return data.access_token;
        } else {
          // Refresh token invalid or expired; clear stale authentication
          localStorage.removeItem('arovia_token');
          localStorage.removeItem('arovia_candidate_profile');
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('arovia_session_expired'));
          }
          return null;
        }
      } catch (err) {
        localStorage.removeItem('arovia_token');
        localStorage.removeItem('arovia_candidate_profile');
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('arovia_session_expired'));
        }
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const authHeader = options.headers?.Authorization ? {} : getAuthHeader();

  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...authHeader,
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(url, {
      credentials: 'include',
      ...options,
      headers,
    });
  } catch (netErr) {
    const error = new Error(
      'Cannot connect to AROVIA backend. Please ensure the backend server is running.'
    );
    error.status = 0;
    error.code = 'NETWORK_ERROR';
    throw error;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const isTokenExpired =
      response.status === 401 &&
      (data.error_code === 'TOKEN_EXPIRED' ||
        data.code === 'TOKEN_EXPIRED' ||
        (typeof data.detail === 'string' && data.detail.includes('Access token has expired')));

    const isAuthEndpoint =
      endpoint === '/auth/login' ||
      endpoint === '/auth/register' ||
      endpoint === '/auth/google' ||
      endpoint === '/auth/refresh';

    // Transparent single-flight refresh and retry if access token expired
    if (isTokenExpired && !options._isRetry && !isAuthEndpoint) {
      const newToken = await getRefreshedToken();
      if (newToken) {
        const retryHeaders = {
          ...options.headers,
          Authorization: `Bearer ${newToken}`,
        };
        return request(endpoint, {
          ...options,
          headers: retryHeaders,
          _isRetry: true,
        });
      }
    }

    let errorMsg = 'API request failed';

    if (Array.isArray(data.errors) && data.errors.length > 0) {
      errorMsg = data.errors
        .map((e) => (typeof e === 'string' ? e : e.message || e.msg || JSON.stringify(e)))
        .join('. ');
    } else if (Array.isArray(data.detail)) {
      // Format Pydantic 422 validation array into human-readable sentences
      errorMsg = data.detail
        .map((d) => (typeof d === 'string' ? d : d.msg || d.message || JSON.stringify(d)))
        .join('. ');
    } else if (typeof data.detail === 'string' && data.detail.trim()) {
      errorMsg = data.detail;
    } else if (typeof data.message === 'string' && data.message.trim()) {
      errorMsg = data.message;
    } else if (response.status === 401) {
      errorMsg = 'Invalid email or password.';
    } else if (response.status === 409) {
      errorMsg = 'An account with this email address already exists.';
    } else if (response.status >= 500) {
      errorMsg =
        'Cannot connect to AROVIA backend server. Please verify backend is active on port 8000.';
    }

    const error = new Error(errorMsg);
    error.status = response.status;
    error.code = data.error_code || data.code;
    error.details = data.details || data.detail;
    throw error;
  }

  return data;
}

export const api = {
  // Authentication & Profile Management
  login: (credentials) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }),
  register: (userData) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    }),
  googleAuth: (idToken) =>
    request('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token: idToken }),
    }),
  refreshToken: () =>
    request('/auth/refresh', {
      method: 'POST',
    }),
  logout: () =>
    request('/auth/logout', {
      method: 'POST',
    }),
  getProfile: () => request('/auth/me'),
  updateProfile: (payload) =>
    request('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Presets & Setup
  getPresets: () => request('/interviews/presets'),
  createSession: (payload) =>
    request('/interviews/sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getActiveSession: () => request('/interviews/sessions/active'),
  getSession: (sessionId) => request(`/interviews/sessions/${sessionId}`),
  abandonSession: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/abandon`, { method: 'POST' }),

  // Turn Progression & Adaptive Loop
  startInterview: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/start`, { method: 'POST' }),
  getCurrentTurn: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/current-turn`),
  submitTurnAnswer: (sessionId, turnId, payload) =>
    request(`/interviews/sessions/${sessionId}/turns/${turnId}/answer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  submitAnswer: (sessionId, turnId, payload) =>
    request(`/interviews/sessions/${sessionId}/turns/${turnId}/answer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getSessionTurns: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/turns`),

  // Evaluation & Scorecard
  evaluateSession: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/evaluate`, { method: 'POST' }),
  completeSession: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/evaluate`, { method: 'POST' }),
  getSessionEvaluation: (sessionId) =>
    request(`/interviews/sessions/${sessionId}/evaluation`),
  getUserSessions: (limit = 50, offset = 0) =>
    request(`/interviews/sessions?limit=${limit}&offset=${offset}`),

  // Progress Intelligence & Longitudinal Analytics
  getProgress: (limit = null) => {
    const query = limit ? `?limit=${limit}` : '';
    return request(`/progress${query}`);
  },
  getProgressInsight: () => request('/progress/insight'),

  // Personal AI Coach & Mentorship
  getOrCreateCoachConversation: (sessionId = null, autoDebrief = true) =>
    request('/coach/conversation', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        auto_debrief: autoDebrief,
      }),
    }),
  getCoachHistory: (sessionId) => request(`/coach/history/${sessionId}`),
  sendCoachChat: (conversationId, message, contextTurnIndex = null) =>
    request('/coach/chat', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        context_turn_index: contextTurnIndex,
      }),
    }),

  // Resume Ingestion & Career Profile
  getMyResume: () => request('/resumes/me'),
  uploadResume: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/resumes/upload', {
      method: 'POST',
      body: formData,
    });
  },
  deleteResume: () => request('/resumes/me', { method: 'DELETE' }),
};

export default api;

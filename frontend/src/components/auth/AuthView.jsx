import React, { useState, useEffect, useRef } from 'react';
import {
  User as UserIcon,
  Mail as MailIcon,
  Lock as LockIcon,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { api } from '../../services/api';
import { AroviaLogo } from '../common/AroviaLogo';

/**
 * AROVIA Master Authentication Portal.
 * Uses the dual-panel sliding layout and staggered animation architecture
 * styled to match AROVIA's native dark analytical visual design system.
 */
export function AuthView({ onAuthSuccess }) {
  const [isToggled, setIsToggled] = useState(false); // false = Sign In, true = Sign Up (Register)
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({
    full_name: '',
    email: '',
    password: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [authError, setAuthError] = useState(null);
  const googleLoginBtnRef = useRef(null);
  const googleRegisterBtnRef = useRef(null);

  // Switch between Sign In and Sign Up with sliding transition
  const handleToggleToRegister = (e) => {
    e.preventDefault();
    setIsToggled(true);
    setAuthError(null);
  };

  const handleToggleToLogin = (e) => {
    e.preventDefault();
    setIsToggled(false);
    setAuthError(null);
  };

  // Google OAuth ID Token Credential Handler
  const handleGoogleCredentialResponse = async (response) => {
    if (!response || !response.credential) return;

    try {
      setSubmitting(true);
      setAuthError(null);
      const tokenResponse = await api.googleAuth(response.credential);
      if (tokenResponse && tokenResponse.access_token) {
        onAuthSuccess(tokenResponse);
      } else {
        throw new Error('Google authentication succeeded but no session token was received.');
      }
    } catch (err) {
      console.error('Google OAuth error:', err);
      setAuthError(err?.message || 'Google authentication failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // Initialize Google Identity Services
  useEffect(() => {
    const googleClientId = import.meta.env?.VITE_GOOGLE_CLIENT_ID;
    if (googleClientId && window.google?.accounts?.id) {
      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleCredentialResponse,
        });

        if (googleLoginBtnRef.current) {
          window.google.accounts.id.renderButton(googleLoginBtnRef.current, {
            theme: 'filled_black',
            size: 'large',
            width: '100%',
            text: 'signin_with',
            shape: 'pill',
          });
        }
        if (googleRegisterBtnRef.current) {
          window.google.accounts.id.renderButton(googleRegisterBtnRef.current, {
            theme: 'filled_black',
            size: 'large',
            width: '100%',
            text: 'signup_with',
            shape: 'pill',
          });
        }
      } catch (err) {
        console.warn('Google Identity Services init note:', err);
      }
    }
  }, [isToggled]);

  const handleGoogleClick = () => {
    const googleClientId = import.meta.env?.VITE_GOOGLE_CLIENT_ID;
    if (!googleClientId) {
      setAuthError(
        'Google Sign-In is awaiting VITE_GOOGLE_CLIENT_ID in frontend/.env. Please configure your client ID to enable 1-click Google OAuth.'
      );
      return;
    }

    if (window.google?.accounts?.id) {
      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleCredentialResponse,
        });
        window.google.accounts.id.prompt();
      } catch (err) {
        console.error('Google prompt error:', err);
        setAuthError('Could not launch Google account chooser. Please check browser popups.');
      }
    } else {
      setAuthError('Google Identity Services is loading. Please try again in a few seconds.');
    }
  };

  // Handle Login Submission
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!loginData.email.trim() || !loginData.password || submitting) return;

    try {
      setSubmitting(true);
      setAuthError(null);

      const tokenResponse = await api.login({
        email: loginData.email.trim(),
        password: loginData.password,
      });

      if (tokenResponse && tokenResponse.access_token) {
        onAuthSuccess(tokenResponse);
      } else {
        throw new Error('Authentication succeeded but no access token was returned.');
      }
    } catch (err) {
      console.error('Login error:', err);
      setAuthError(err?.message || 'Invalid email or password. Please verify your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Registration Submission
  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (
      !registerData.full_name.trim() ||
      !registerData.email.trim() ||
      !registerData.password ||
      submitting
    ) {
      return;
    }

    if (registerData.password.length < 12) {
      setAuthError('Password must be at least 12 characters long.');
      return;
    }

    try {
      setSubmitting(true);
      setAuthError(null);

      const tokenResponse = await api.register({
        full_name: registerData.full_name.trim(),
        email: registerData.email.trim(),
        password: registerData.password,
      });

      if (tokenResponse && tokenResponse.access_token) {
        onAuthSuccess(tokenResponse);
      } else {
        throw new Error('Registration succeeded but no access token was returned.');
      }
    } catch (err) {
      console.error('Registration error:', err);
      setAuthError(
        err?.message || 'Registration failed. Please try a different email or stronger password.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="arovia-auth-body">
      <div className={`auth-wrapper ${isToggled ? 'toggled' : ''}`}>
        {/* Animated Background Geometric Shapes */}
        <div className="background-shape" />
        <div className="secondary-shape" />

        {/* 1. SIGN IN CREDENTIALS PANEL */}
        <div className="credentials-panel signin">
          <h2 className="slide-element">Login</h2>

          {/* Live Error Banner for Sign In */}
          {!isToggled && authError && (
            <div className="reference-auth-alert slide-element">
              <AlertCircle size={15} />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleLoginSubmit}>
            <div className="field-wrapper slide-element">
              <input
                type="email"
                required
                className={loginData.email ? 'has-val' : ''}
                value={loginData.email}
                onChange={(e) => {
                  setLoginData({ ...loginData, email: e.target.value });
                  if (authError) setAuthError(null);
                }}
                disabled={submitting}
                autoComplete="email"
              />
              <label>Email Address</label>
              <MailIcon size={18} className="field-icon-svg" />
            </div>

            <div className="field-wrapper slide-element">
              <input
                type="password"
                required
                className={loginData.password ? 'has-val' : ''}
                value={loginData.password}
                onChange={(e) => {
                  setLoginData({ ...loginData, password: e.target.value });
                  if (authError) setAuthError(null);
                }}
                disabled={submitting}
                autoComplete="current-password"
              />
              <label>Password</label>
              <LockIcon size={18} className="field-icon-svg" />
            </div>

            <div className="field-wrapper slide-element">
              <button className="submit-button" type="submit" disabled={submitting}>
                {submitting ? (
                  <span className="btn-loading-flex">
                    <Loader2 size={16} className="animate-spin" /> Authenticating...
                  </span>
                ) : (
                  'Sign In'
                )}
              </button>
            </div>

            {/* Google OAuth Button */}
            <div className="field-wrapper slide-element google-btn-wrapper">
              <button
                type="button"
                className="google-ref-button"
                onClick={handleGoogleClick}
                disabled={submitting}
              >
                <svg className="google-svg" viewBox="0 0 24 24" width="18" height="18">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.98 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>
            </div>

            <div className="switch-link slide-element">
              <p>
                Don't have an account? <br />
                <a href="#signup" className="register-trigger" onClick={handleToggleToRegister}>
                  Sign Up
                </a>
              </p>
            </div>
          </form>
        </div>

        {/* 2. SIGN IN WELCOME SECTION (RIGHT SIDE) */}
        <div className="welcome-section signin">
          <div className="welcome-brand slide-element">
            <AroviaLogo variant="compact" size={32} />
          </div>
          <h2 className="slide-element">WELCOME BACK!</h2>
          <p className="slide-element welcome-sub">
            Calibrated AI Mock Interviews &amp; Executive Career Intelligence.
          </p>
        </div>

        {/* 3. SIGN UP (REGISTER) CREDENTIALS PANEL */}
        <div className="credentials-panel signup">
          <h2 className="slide-element">Register</h2>

          {/* Live Error Banner for Register */}
          {isToggled && authError && (
            <div className="reference-auth-alert slide-element">
              <AlertCircle size={15} />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleRegisterSubmit}>
            <div className="field-wrapper slide-element">
              <input
                type="text"
                required
                className={registerData.full_name ? 'has-val' : ''}
                value={registerData.full_name}
                onChange={(e) => {
                  setRegisterData({ ...registerData, full_name: e.target.value });
                  if (authError) setAuthError(null);
                }}
                disabled={submitting}
                autoComplete="name"
              />
              <label>Full Name</label>
              <UserIcon size={18} className="field-icon-svg" />
            </div>

            <div className="field-wrapper slide-element">
              <input
                type="email"
                required
                className={registerData.email ? 'has-val' : ''}
                value={registerData.email}
                onChange={(e) => {
                  setRegisterData({ ...registerData, email: e.target.value });
                  if (authError) setAuthError(null);
                }}
                disabled={submitting}
                autoComplete="email"
              />
              <label>Email Address</label>
              <MailIcon size={18} className="field-icon-svg" />
            </div>

            <div className="field-wrapper slide-element">
              <input
                type="password"
                required
                className={registerData.password ? 'has-val' : ''}
                value={registerData.password}
                onChange={(e) => {
                  setRegisterData({ ...registerData, password: e.target.value });
                  if (authError) setAuthError(null);
                }}
                disabled={submitting}
                autoComplete="new-password"
              />
              <label>Password (min. 12 chars)</label>
              <LockIcon size={18} className="field-icon-svg" />
            </div>

            <div className="field-wrapper slide-element">
              <button className="submit-button" type="submit" disabled={submitting}>
                {submitting ? (
                  <span className="btn-loading-flex">
                    <Loader2 size={16} className="animate-spin" /> Creating Account...
                  </span>
                ) : (
                  'Create Account'
                )}
              </button>
            </div>

            {/* Google OAuth Button */}
            <div className="field-wrapper slide-element google-btn-wrapper">
              <button
                type="button"
                className="google-ref-button"
                onClick={handleGoogleClick}
                disabled={submitting}
              >
                <svg className="google-svg" viewBox="0 0 24 24" width="18" height="18">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.98 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>
            </div>

            <div className="switch-link slide-element">
              <p>
                Already have an account? <br />
                <a href="#signin" className="login-trigger" onClick={handleToggleToLogin}>
                  Sign In
                </a>
              </p>
            </div>
          </form>
        </div>

        {/* 4. SIGN UP WELCOME SECTION (LEFT SIDE) */}
        <div className="welcome-section signup">
          <div className="welcome-brand slide-element">
            <AroviaLogo variant="compact" size={32} />
          </div>
          <h2 className="slide-element">WELCOME!</h2>
          <p className="slide-element welcome-sub">
            Accelerate your career with real-time AI speech evaluation &amp; adaptive coaching.
          </p>
        </div>
      </div>
    </div>
  );
}

export default AuthView;

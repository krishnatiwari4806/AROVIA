import React, { useState, useEffect, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from './services/api';
import { IntroSequence } from './components/intro/IntroSequence';
import { AuthView } from './components/auth/AuthView';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './components/dashboard/Dashboard';
import { InterviewSetup } from './components/setup/InterviewSetup';
import { InterviewRoom } from './components/interview/InterviewRoom';
import { ReportCard } from './components/report/ReportCard';
import { CoachView } from './components/coach/CoachView';
import { HistoryView } from './components/history/HistoryView';
import { ProfileView } from './components/profile/ProfileView';
import { SettingsView } from './components/settings/SettingsView';
import { HelpSupportView } from './components/help/HelpSupportView';
import { applySystemSettings } from './services/settingsManager';

/**
 * Master AROVIA Application Controller.
 * Manages intro sequence state, secure JWT session verification,
 * authenticated user state, clean functional view routing, active session resume,
 * and report workflows.
 */
export function App() {
  // Check if user has already seen the 3D intro during this browser session
  const [showIntro, setShowIntro] = useState(() => {
    try {
      return sessionStorage.getItem('arovia_intro_seen') !== 'true';
    } catch {
      return true;
    }
  });

  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'setup' | 'interview' | 'report' | 'coach' | 'history' | 'profile' | 'settings' | 'help'
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [selectedCoachSessionId, setSelectedCoachSessionId] = useState(null);

  // Verify and hydrate authenticated candidate session
  const verifyAuthSession = useCallback(async () => {
    const token = localStorage.getItem('arovia_token');
    if (!token) {
      setUser(null);
      setAuthLoading(false);
      return;
    }

    try {
      const profile = await api.getProfile();
      if (profile && profile.id) {
        setUser(profile);
        try {
          localStorage.setItem('arovia_candidate_profile', JSON.stringify(profile));
        } catch {
          // ignore
        }
      } else {
        throw new Error('Invalid profile response');
      }
    } catch (err) {
      console.warn('Initial session check failed, attempting token refresh:', err);
      try {
        const refreshed = await api.refreshToken();
        if (refreshed && refreshed.access_token) {
          localStorage.setItem('arovia_token', refreshed.access_token);
          setUser(refreshed.user);
          try {
            localStorage.setItem('arovia_candidate_profile', JSON.stringify(refreshed.user));
          } catch {
            // ignore
          }
        } else {
          localStorage.removeItem('arovia_token');
          setUser(null);
        }
      } catch (refreshErr) {
        console.warn('Token refresh failed:', refreshErr);
        localStorage.removeItem('arovia_token');
        setUser(null);
      }
    } finally {
      setAuthLoading(false);
    }
  }, []);

  // Check active in-progress session on boot or after login
  const refreshActiveSession = useCallback(async () => {
    if (!localStorage.getItem('arovia_token')) {
      setActiveSessionId(null);
      return;
    }

    try {
      const active = await api.getActiveSession();
      if (active && active.id && active.status === 'in_progress') {
        setActiveSessionId(active.id);
      } else {
        setActiveSessionId(null);
      }
    } catch {
      setActiveSessionId(null);
    }
  }, []);

  useEffect(() => {
    applySystemSettings();
    verifyAuthSession();
  }, [verifyAuthSession]);

  useEffect(() => {
    if (user) {
      refreshActiveSession();
    }
  }, [user, refreshActiveSession]);

  const handleAuthSuccess = (tokenResponse) => {
    if (tokenResponse?.access_token) {
      localStorage.setItem('arovia_token', tokenResponse.access_token);
    }
    if (tokenResponse?.user) {
      setUser(tokenResponse.user);
      try {
        localStorage.setItem('arovia_candidate_profile', JSON.stringify(tokenResponse.user));
      } catch {
        // ignore
      }
    }
    setCurrentView('dashboard');
    refreshActiveSession();
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.warn('Logout endpoint note:', err);
    } finally {
      localStorage.removeItem('arovia_token');
      localStorage.removeItem('arovia_candidate_profile');
      setUser(null);
      setActiveSessionId(null);
      setSelectedReportId(null);
      setCurrentView('dashboard');
    }
  };

  const handleStartInterview = (sessionId) => {
    setActiveSessionId(sessionId);
    setCurrentView('interview');
  };

  const handleResumeActive = (sessionId) => {
    if (sessionId || activeSessionId) {
      setActiveSessionId(sessionId || activeSessionId);
      setCurrentView('interview');
    }
  };

  const handleViewReport = (sessionId) => {
    setSelectedReportId(sessionId);
    setCurrentView('report');
  };

  const handleInterviewComplete = (evaluationResponse) => {
    const targetSessionId =
      evaluationResponse?.session_id || evaluationResponse?.id || activeSessionId;

    if (targetSessionId) {
      try {
        const savedHistory = localStorage.getItem('arovia_recent_sessions');
        const parsed = savedHistory ? JSON.parse(savedHistory) : [];
        const newEntry = {
          id: targetSessionId,
          session_id: targetSessionId,
          target_role:
            evaluationResponse?.target_role || 'Technical Interview Session',
          seniority_level: evaluationResponse?.seniority_level || 'senior',
          interview_focus:
            evaluationResponse?.interview_focus || 'Technical Core',
          practice_mode: evaluationResponse?.practice_mode || 'standard',
          overall_score:
            evaluationResponse?.overall_score !== undefined
              ? evaluationResponse.overall_score
              : null,
          completed_at:
            evaluationResponse?.completed_at || new Date().toISOString(),
          status: 'completed',
        };
        const updated = [
          newEntry,
          ...parsed.filter(
            (p) => p && (p.session_id || p.id) !== targetSessionId
          ),
        ].slice(0, 20);
        localStorage.setItem('arovia_recent_sessions', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('arovia_sessions_updated'));
      } catch (e) {
        console.warn('Could not save session to history:', e);
      }
    }

    setSelectedReportId(targetSessionId);
    setCurrentView('report');
    setActiveSessionId(null);
    refreshActiveSession();
  };

  const handleOpenCoach = (targetSessionId = null) => {
    setSelectedCoachSessionId(targetSessionId || selectedReportId || null);
    setCurrentView('coach');
    refreshActiveSession();
  };

  const handleRetake = () => {
    setActiveSessionId(null);
    setSelectedReportId(null);
    setSelectedCoachSessionId(null);
    setCurrentView('setup');
    refreshActiveSession();
  };

  const handleReplayIntro = () => {
    try {
      sessionStorage.removeItem('arovia_intro_seen');
    } catch {
      // ignore
    }
    setShowIntro(true);
  };

  // 1. If 3D Intro is active, render the fullscreen sequence
  if (showIntro) {
    return (
      <IntroSequence
        onComplete={() => {
          setShowIntro(false);
        }}
      />
    );
  }

  // 2. Loading state while checking authentication credentials
  if (authLoading) {
    return (
      <div className="interview-room-loading">
        <Loader2 size={36} className="animate-spin text-primary" />
        <p className="loading-text">Calibrating AROVIA Candidate Authentication...</p>
      </div>
    );
  }

  // 3. Unauthenticated User Gate -> AuthView
  if (!user) {
    return <AuthView onAuthSuccess={handleAuthSuccess} />;
  }

  // 4. Authenticated Protected Application Shell
  return (
    <AppLayout
      currentView={currentView}
      onNavigate={(view) => {
        if (view === 'dashboard') {
          refreshActiveSession();
        }
        setCurrentView(view);
      }}
      hasActiveSession={Boolean(activeSessionId)}
      onResumeActive={() => handleResumeActive(activeSessionId)}
      onReplayIntro={handleReplayIntro}
      user={user}
      onLogout={handleLogout}
    >
      {/* 1. Interview Setup View */}
      {currentView === 'setup' ? (
        <InterviewSetup
          onStartInterview={handleStartInterview}
          onBack={() => setCurrentView('dashboard')}
        />
      ) : /* 2. Live Interview Room View */
      currentView === 'interview' && activeSessionId ? (
        <InterviewRoom
          sessionId={activeSessionId}
          onComplete={handleInterviewComplete}
          onRetake={handleRetake}
          onExit={() => {
            setActiveSessionId(null);
            setCurrentView('dashboard');
            refreshActiveSession();
          }}
        />
      ) : /* 3. Performance Report Card View */
      currentView === 'report' && selectedReportId ? (
        <ReportCard
          sessionId={selectedReportId}
          onRetake={handleRetake}
          onBack={() => setCurrentView('dashboard')}
          onOpenCoach={handleOpenCoach}
        />
      ) : /* 4. Personal AI Coach Mentorship View */
      currentView === 'coach' ? (
        <CoachView
          sessionId={selectedCoachSessionId || selectedReportId}
          onBack={() => setCurrentView(selectedReportId ? 'report' : 'dashboard')}
          onViewReport={handleViewReport}
          onStartSetup={() => setCurrentView('setup')}
        />
      ) : /* 5. Dedicated History View */
      currentView === 'history' ? (
        <HistoryView
          onViewReport={handleViewReport}
          onStartSetup={() => setCurrentView('setup')}
        />
      ) : /* 6. Dedicated Profile View */
      currentView === 'profile' ? (
        <ProfileView
          onStartSetup={() => setCurrentView('setup')}
        />
      ) : /* 7. Dedicated Settings View */
      currentView === 'settings' ? (
        <SettingsView
          onReplayIntro={handleReplayIntro}
          onNavigate={(view) => setCurrentView(view)}
        />
      ) : /* 8. Dedicated Help & Support View */
      currentView === 'help' ? (
        <HelpSupportView
          onStartSetup={() => setCurrentView('setup')}
        />
      ) : /* 9. Candidate Dashboard (Default) */
      (
        <Dashboard
          onStartInterview={() => setCurrentView('setup')}
          onOpenSetup={() => setCurrentView('setup')}
          onResumeActiveSession={handleResumeActive}
          onViewReport={handleViewReport}
        />
      )}
    </AppLayout>
  );
}

export default App;

import React, { useState, useEffect, useCallback } from 'react';
import { api } from './services/api';
import { Navbar } from './components/layout/Navbar';
import { Dashboard } from './components/dashboard/Dashboard';
import { InterviewRoom } from './components/interview/InterviewRoom';
import ReportCard from './components/report/ReportCard';

export function App() {
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'interview' | 'report'
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check if candidate has an existing active in-progress session on boot
  const refreshActiveSession = useCallback(async () => {
    try {
      const active = await api.getActiveSession();
      if (active && active.id && active.status === 'in_progress') {
        setActiveSessionId(active.id);
      } else {
        setActiveSessionId(null);
      }
    } catch {
      setActiveSessionId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshActiveSession();
  }, [refreshActiveSession]);

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
    // Save to local history for recent sessions list
    try {
      const savedHistory = localStorage.getItem('arovia_recent_sessions');
      const parsed = savedHistory ? JSON.parse(savedHistory) : [];
      const newEntry = {
        id: activeSessionId,
        target_role: evaluationResponse?.target_role || 'Target Role',
        seniority_level: evaluationResponse?.seniority_level || 'mid',
        interview_focus: evaluationResponse?.interview_focus || 'Technical Core',
        practice_mode: evaluationResponse?.practice_mode || 'full',
        overall_score: evaluationResponse?.overall_score || 80,
        completed_at: new Date().toISOString(),
        status: 'completed',
      };
      const updated = [newEntry, ...parsed.filter((p) => p.id !== activeSessionId)].slice(0, 10);
      localStorage.setItem('arovia_recent_sessions', JSON.stringify(updated));
    } catch {
      // ignore
    }

    refreshActiveSession();
  };

  const handleRetake = () => {
    setActiveSessionId(null);
    setSelectedReportId(null);
    setCurrentView('dashboard');
    refreshActiveSession();
  };

  return (
    <div className="app-container">
      {/* Top Luxury-Tech Navbar */}
      <Navbar
        currentView={currentView}
        onNavigate={(view) => {
          if (view === 'dashboard') {
            refreshActiveSession();
          }
          setCurrentView(view);
        }}
        hasActiveSession={Boolean(activeSessionId)}
        onResumeActive={() => handleResumeActive(activeSessionId)}
      />

      {/* Main Workspace */}
      <main className="main-content">
        {currentView === 'interview' && activeSessionId ? (
          <InterviewRoom
            sessionId={activeSessionId}
            onComplete={handleInterviewComplete}
            onRetake={handleRetake}
          />
        ) : currentView === 'report' && selectedReportId ? (
          <ReportCard
            sessionId={selectedReportId}
            onRetake={handleRetake}
            onBack={() => setCurrentView('dashboard')}
          />
        ) : (
          <Dashboard
            onStartInterview={handleStartInterview}
            onResumeActiveSession={handleResumeActive}
            onViewReport={handleViewReport}
          />
        )}
      </main>
    </div>
  );
}

export default App;


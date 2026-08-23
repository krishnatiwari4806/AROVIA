import React, { useState, useEffect } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import ActiveSessionBanner from './ActiveSessionBanner';
import DashboardHero from './DashboardHero';
import StatsOverview from './StatsOverview';
import TrackPresetsGrid from './TrackPresetsGrid';
import ResumeProfileCard from './ResumeProfileCard';
import RecentSessionsList from './RecentSessionsList';
import QuickSetupModal from './QuickSetupModal';

/**
 * Candidate Dashboard Master View.
 */
export function Dashboard({ onStartInterview, onResumeActiveSession, onViewReport }) {
  const [activeSession, setActiveSession] = useState(null);
  const [resume, setResume] = useState(null);
  const [presets, setPresets] = useState(null);
  const [recentSessions, setRecentSessions] = useState([]);
  const [stats, setStats] = useState({
    readinessScore: 82,
    totalSessions: 0,
    averageScore: 78,
    strongestDimension: 'Technical Correctness',
  });
  const [loading, setLoading] = useState(true);
  const [isAbandoning, setIsAbandoning] = useState(false);
  const [setupModalOpen, setSetupModalOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(null);

  // Fetch initial dashboard state
  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Check active session
      try {
        const active = await api.getActiveSession();
        if (active && active.id && active.status === 'in_progress') {
          setActiveSession(active);
        } else {
          setActiveSession(null);
        }
      } catch {
        setActiveSession(null);
      }

      // Check candidate resume
      try {
        const res = await api.getMyResume();
        if (res && res.id) {
          setResume(res);
        }
      } catch {
        // No resume yet
      }

      // Fetch role presets
      try {
        const pres = await api.getPresets();
        if (pres) setPresets(pres);
      } catch {
        // Use fallback presets in TrackPresetsGrid
      }

      // Check local session history if any stored or mock
      const savedHistory = localStorage.getItem('arovia_recent_sessions');
      if (savedHistory) {
        try {
          const parsed = JSON.parse(savedHistory);
          setRecentSessions(parsed);
          if (parsed.length > 0) {
            const sumScore = parsed.reduce((acc, s) => acc + (s.overall_score || 75), 0);
            const avg = Math.round(sumScore / parsed.length);
            setStats((prev) => ({
              ...prev,
              totalSessions: parsed.length,
              averageScore: avg,
              readinessScore: Math.min(95, Math.max(60, avg + 5)),
            }));
          }
        } catch {
          // ignore
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleAbandonActive = async () => {
    if (!activeSession) return;
    try {
      setIsAbandoning(true);
      await api.abandonSession(activeSession.id);
      setActiveSession(null);
    } catch (err) {
      console.error('Failed to abandon session:', err);
    } finally {
      setIsAbandoning(false);
    }
  };

  const handleSelectPreset = (preset) => {
    setSelectedPreset(preset);
    setSetupModalOpen(true);
  };

  const handleQuickStart = () => {
    setSelectedPreset(null);
    setSetupModalOpen(true);
  };

  const handleSessionCreated = (session) => {
    setSetupModalOpen(false);
    setActiveSession(session);
    if (onStartInterview) {
      onStartInterview(session.id);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Active Session Notification Banner */}
      {activeSession && (
        <ActiveSessionBanner
          activeSession={activeSession}
          onResume={() => onResumeActiveSession(activeSession.id)}
          onAbandon={handleAbandonActive}
          isAbandoning={isAbandoning}
        />
      )}

      {/* Hero Welcome & Value Proposition */}
      <DashboardHero
        onQuickStart={handleQuickStart}
        onOpenUpload={() => {
          const el = document.querySelector('.resume-card');
          if (el) el.scrollIntoView({ behavior: 'smooth' });
        }}
        hasActiveSession={Boolean(activeSession)}
        onResumeActive={() => onResumeActiveSession(activeSession?.id)}
      />

      {/* Metrics & Assessment Readiness Overview */}
      <StatsOverview stats={stats} />

      {/* Two-Column Grid: Profile/Resume + Recent Scorecards */}
      <div className="dashboard-columns-grid">
        <ResumeProfileCard
          resume={resume}
          onResumeUpdated={(updatedResume) => setResume(updatedResume)}
        />
        <RecentSessionsList
          sessions={recentSessions}
          onSelectSession={(sessId) => onViewReport(sessId)}
          onStartNew={handleQuickStart}
        />
      </div>

      {/* Technical Tracks Selection Grid */}
      <TrackPresetsGrid
        presets={presets}
        onSelectPreset={handleSelectPreset}
      />

      {/* Setup / Calibration Modal */}
      {setupModalOpen && (
        <QuickSetupModal
          initialPreset={selectedPreset}
          onClose={() => setSetupModalOpen(false)}
          onSessionCreated={handleSessionCreated}
        />
      )}
    </div>
  );
}

export default Dashboard;

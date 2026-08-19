import React, { useState, useEffect } from 'react';
import { Sparkles, Terminal } from 'lucide-react';
import { api } from './services/api';
import { InterviewRoom } from './components/interview/InterviewRoom';

export function App() {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkActiveSession() {
      try {
        const active = await api.getActiveSession();
        if (active && active.id) {
          setActiveSessionId(active.id);
        }
      } catch {
        // No active session or unauthenticated
      } finally {
        setLoading(false);
      }
    }

    checkActiveSession();
  }, []);

  return (
    <div className="app-container">
      {/* Top Navigation */}
      <header className="navbar">
        <div className="logo-brand">
          <Terminal size={22} style={{ color: 'var(--accent-primary)' }} />
          <span>AROVIA</span>
          <span className="logo-badge">MOCK ENGINE</span>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="main-content">
        {activeSessionId ? (
          <InterviewRoom
            sessionId={activeSessionId}
            onComplete={(res) => console.log('Interview completed:', res)}
            onRetake={() => setActiveSessionId(null)}
          />
        ) : (
          <div className="card" style={{ textAlign: 'center', padding: '3.5rem 2rem', maxWidth: '650px', margin: '3rem auto' }}>
            <Sparkles size={40} style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }} />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.75rem' }}>
              Adaptive AI Mock Interview
            </h1>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              Conduct structured, realistic technical and behavioral interviews calibrated to your target role, seniority, and resume background with browser-native voice flow.
            </p>
            <div style={{ display: 'inline-flex', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <span>✓ ₹0 Zero Cost</span> • <span>✓ Web Speech API</span> • <span>✓ Gemini Adaptive Probing</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

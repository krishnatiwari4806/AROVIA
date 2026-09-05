import React from 'react';
import { Sidebar } from './Sidebar';
import { TopHeader } from './TopHeader';
import { MobileNav } from './MobileNav';

/**
 * Master Application Shell Layout.
 * Provides the desktop left sidebar, top header, responsive content viewport,
 * and mobile bottom navigation bar.
 */
export function AppLayout({
  children,
  currentView,
  onNavigate,
  hasActiveSession,
  onResumeActive,
  onReplayIntro,
  user,
  onLogout,
}) {
  return (
    <div className="arovia-app-shell">
      {/* Desktop & Tablet Sidebar */}
      <Sidebar
        currentView={currentView}
        onNavigate={onNavigate}
        hasActiveSession={hasActiveSession}
        onResumeActive={onResumeActive}
      />

      {/* Main Workspace Area */}
      <div className="arovia-main-wrapper">
        {/* Top Header Bar */}
        <TopHeader
          onNavigate={onNavigate}
          onReplayIntro={onReplayIntro}
          user={user}
          onLogout={onLogout}
        />

        {/* Dynamic Page Content */}
        <main className="arovia-page-container">
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileNav
        currentView={currentView}
        onNavigate={onNavigate}
        hasActiveSession={hasActiveSession}
      />
    </div>
  );
}

export default AppLayout;

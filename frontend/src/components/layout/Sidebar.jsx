import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  History as HistoryIcon,
  User,
  Settings,
  HelpCircle,
} from 'lucide-react';
import { AroviaLogo } from '../common/AroviaLogo';

/**
 * Desktop & Tablet Left Sidebar Navigation matching Figma design.
 * Clean, structured, analytical layout with purple rounded active container.
 */
export function Sidebar({ currentView, onNavigate }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'coach', label: 'AI Coach', icon: Sparkles },
    { id: 'history', label: 'History', icon: HistoryIcon },
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'help', label: 'Help & Support', icon: HelpCircle },
  ];

  return (
    <aside className="arovia-sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand" onClick={() => onNavigate('dashboard')}>
        <AroviaLogo variant="compact" size={32} />
      </div>

      {/* Main Navigation Links */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            currentView === item.id ||
            (item.id === 'dashboard' && (currentView === 'dashboard' || currentView === 'setup'));

          return (
            <button
              key={item.id}
              className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={18} className="nav-btn-icon" />
              <span className="nav-btn-label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Bottom Status Badge */}
      <div className="sidebar-footer">
        <div className="ai-core-status">
          <span className="ai-status-dot" />
          <span className="ai-status-text">AI Core Online</span>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;

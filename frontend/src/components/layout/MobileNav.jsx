import React from 'react';
import { LayoutDashboard, Sparkles, History, User, Settings, HelpCircle } from 'lucide-react';

/**
 * Mobile Bottom Navigation Tab Bar matching Figma mobile specs.
 * Clean, touch-friendly tab bar supporting Dashboard, History, Profile, Settings, and Help.
 */
export function MobileNav({ currentView, onNavigate }) {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'coach', label: 'AI Coach', icon: Sparkles },
    { id: 'history', label: 'History', icon: History },
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'help', label: 'Help', icon: HelpCircle },
  ];

  return (
    <nav className="arovia-mobile-bottom-nav">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive =
          currentView === tab.id ||
          (tab.id === 'dashboard' && currentView === 'setup');

        return (
          <button
            key={tab.id}
            className={`mobile-tab-btn ${isActive ? 'active' : ''}`}
            onClick={() => onNavigate(tab.id)}
          >
            <div className="tab-icon-wrapper">
              <Icon size={18} />
            </div>
            <span className="tab-label">{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export default MobileNav;

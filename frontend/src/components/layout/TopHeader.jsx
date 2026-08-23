import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, User, Settings, LogOut, ChevronDown } from 'lucide-react';
import { AroviaLogo } from '../common/AroviaLogo';

/**
 * Top Header Navigation Bar matching Figma design with Search, Notifications,
 * and authenticated Candidate Profile status.
 */
export function TopHeader({ onNavigate, user, onLogout }) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const getInitials = (name) => {
    if (!name || typeof name !== 'string') return 'C';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const displayName = user?.full_name || 'Candidate';
  const displayRole = user?.target_role || 'Executive Tier';
  const displayEmail = user?.email || '';
  const initials = getInitials(displayName);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="arovia-top-header">
      <div className="header-left">
        {/* Mobile-only logo display */}
        <div className="mobile-brand-display" onClick={() => onNavigate('dashboard')}>
          <AroviaLogo variant="compact" size={28} />
        </div>

        {/* Global Intelligence Search */}
        <div className="header-search-bar">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search intelligence modules..."
            className="search-input"
          />
        </div>
      </div>

      <div className="header-right">
        {/* Notification Bell */}
        <button
          className="header-icon-btn"
          title="Notifications"
          onClick={() => onNavigate('help')}
        >
          <Bell size={17} />
          <span className="notification-dot" />
        </button>

        {/* Executive Profile Avatar Card & Dropdown */}
        <div className="header-profile-wrapper" ref={dropdownRef}>
          <div
            className="header-profile-card clickable"
            onClick={() => setDropdownOpen((prev) => !prev)}
            title="Candidate Account Menu"
          >
            <div className="profile-avatar">
              <span>{initials}</span>
            </div>
            <div className="profile-info-text">
              <span className="profile-name">{displayName}</span>
              <span className="profile-tier-badge">{displayRole.toUpperCase()}</span>
            </div>
            <ChevronDown size={14} className="profile-chevron text-muted" />
          </div>

          {dropdownOpen && (
            <div className="header-profile-dropdown">
              <div className="dropdown-user-header">
                <p className="dropdown-user-name">{displayName}</p>
                {displayEmail && <p className="dropdown-user-email">{displayEmail}</p>}
              </div>

              <div className="dropdown-divider" />

              <button
                type="button"
                className="dropdown-menu-item"
                onClick={() => {
                  setDropdownOpen(false);
                  onNavigate('profile');
                }}
              >
                <User size={15} />
                <span>Candidate Profile & Resume</span>
              </button>

              <button
                type="button"
                className="dropdown-menu-item"
                onClick={() => {
                  setDropdownOpen(false);
                  onNavigate('settings');
                }}
              >
                <Settings size={15} />
                <span>System Settings</span>
              </button>

              <div className="dropdown-divider" />

              <button
                type="button"
                className="dropdown-menu-item sign-out-item"
                onClick={() => {
                  setDropdownOpen(false);
                  onLogout?.();
                }}
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default TopHeader;

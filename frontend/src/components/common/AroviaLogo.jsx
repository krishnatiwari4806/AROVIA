import React from 'react';

/**
 * Official AROVIA Logo component.
 * Reproduces the 3D ribbon 'A' geometric identity with Cyan -> Blue -> Violet -> Pink gradient
 * and tracked futuristic typography with 'AI INTERVIEW INTELLIGENCE' tagline.
 *
 * @param {Object} props
 * @param {'full'|'icon'|'compact'|'header'} [props.variant='full'] - Display variant
 * @param {number} [props.size=40] - Icon height/width dimension in px
 * @param {string} [props.className=''] - Additional CSS classes
 * @param {boolean} [props.animated=false] - Whether to apply subtle ambient pulse
 */
export function AroviaLogo({
  variant = 'full',
  size = 36,
  className = '',
  animated = false,
  onClick,
}) {
  const iconOnly = variant === 'icon';
  const isCompact = variant === 'compact';
  const isHeader = variant === 'header';

  return (
    <div
      className={`arovia-logo-wrapper ${variant} ${animated ? 'animated-glow' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      {/* 3D Geometric Ribbon 'A' Mark */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="arovia-logo-icon"
      >
        <defs>
          {/* Main Ribbon Gradient: Cyan -> Blue -> Violet -> Pink */}
          <linearGradient id="aroviaRibbonGrad" x1="15%" y1="10%" x2="85%" y2="90%">
            <stop offset="0%" stopColor="#22D3EE" />
            <stop offset="30%" stopColor="#5B8CFF" />
            <stop offset="70%" stopColor="#8B5CF6" />
            <stop offset="100%" stopColor="#E879F9" />
          </linearGradient>

          {/* Left Arch High-Light Gradient */}
          <linearGradient id="aroviaLeftHighlight" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#67E8F9" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#3B82F6" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#7C3AED" stopOpacity="0.4" />
          </linearGradient>

          {/* Right Leg & Fold Shadow Gradient */}
          <linearGradient id="aroviaRightShade" x1="100%" y1="20%" x2="20%" y2="100%">
            <stop offset="0%" stopColor="#C084FC" />
            <stop offset="45%" stopColor="#8B5CF6" />
            <stop offset="85%" stopColor="#4338CA" />
            <stop offset="100%" stopColor="#1E1B4B" />
          </linearGradient>

          {/* Crossbar & Core Glow */}
          <linearGradient id="aroviaCoreBar" x1="10%" y1="50%" x2="90%" y2="50%">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="50%" stopColor="#818CF8" />
            <stop offset="100%" stopColor="#F472B6" />
          </linearGradient>

          {/* Ambient Glow Filter */}
          <filter id="aroviaAmbientGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Ambient background glow aura */}
        <ellipse
          cx="60"
          cy="60"
          rx="45"
          ry="45"
          fill="url(#aroviaRibbonGrad)"
          opacity="0.22"
          filter="url(#aroviaAmbientGlow)"
        />

        {/* Outer Shadow Path */}
        <path
          d="M60 14 C65 14 69 17 73 23 L104 78 C108 85 106 94 99 99 C93 103 84 102 79 96 L67 78 L53 78 L41 96 C36 102 27 103 21 99 C14 94 12 85 16 78 L47 23 C51 17 55 14 60 14 Z"
          fill="#060911"
          opacity="0.4"
        />

        {/* Left ascending arch of the 3D 'A' */}
        <path
          d="M60 15 C54 15 49 19 46 25 L16 80 C12 87 15 96 23 99 C30 102 38 98 42 91 L56 64 C57 62 60 62 61 64 L66 74 C69 80 77 82 83 78 C88 74 89 66 85 60 L68 25 C65 19 63 15 60 15 Z"
          fill="url(#aroviaLeftHighlight)"
        />

        {/* Right descending fold & wrap-around ribbon forming the 3D loop */}
        <path
          d="M60 15 C66 15 71 19 74 25 L104 80 C108 87 105 96 97 99 C90 102 82 98 78 91 L67 71 C65 67 61 67 59 71 L51 86 C47 93 39 96 32 92 C26 88 25 80 29 74 L48 39 C52 32 56 26 60 15 Z"
          fill="url(#aroviaRightShade)"
        />

        {/* Glowing Central Crossbar & Apex Bridge */}
        <path
          d="M42 56 C42 54 44 52 47 52 L73 52 C76 52 78 54 78 56 C78 58 76 60 73 60 L47 60 C44 60 42 58 42 56 Z"
          fill="url(#aroviaCoreBar)"
          filter="url(#aroviaAmbientGlow)"
        />

        {/* Specular Edge Gleam on Apex */}
        <path
          d="M54 18 C58 15 62 15 66 18 L76 36 C74 34 71 33 68 33 L52 33 C49 33 46 34 44 36 L54 18 Z"
          fill="#FFFFFF"
          opacity="0.85"
        />
      </svg>

      {/* Typography Wordmark (Rendered unless variant is 'icon') */}
      {!iconOnly && (
        <div className="arovia-wordmark-group">
          <div className="arovia-brand-title">
            <span className="arovia-letter">A</span>
            <span className="arovia-letter">R</span>
            <span className="arovia-letter">O</span>
            <span className="arovia-letter">V</span>
            <span className="arovia-letter">I</span>
            <span className="arovia-letter">A</span>
          </div>
          {(!isCompact && !isHeader) && (
            <div className="arovia-tagline-container">
              <span className="arovia-tagline-dash" />
              <span className="arovia-brand-tagline">AI INTERVIEW INTELLIGENCE</span>
              <span className="arovia-tagline-dash" />
            </div>
          )}
          {isHeader && (
            <span className="arovia-header-subtext">AI INTERVIEW INTELLIGENCE</span>
          )}
        </div>
      )}
    </div>
  );
}

export default AroviaLogo;

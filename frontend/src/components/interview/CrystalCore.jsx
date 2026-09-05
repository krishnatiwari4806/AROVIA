import React from 'react';

/**
 * 3D Floating Crystal / Hologram AI Core component matching Figma Interview Room.
 * Restrained, elegant floating with soft ambient spotlight and subtle voice reactivity.
 */
export function CrystalCore({ isSpeaking = false, isListening = false, size = 150 }) {
  return (
    <div className={`arovia-crystal-core-wrapper ${isSpeaking ? 'speaking' : ''} ${isListening ? 'listening' : ''}`}>
      {/* Soft Ambient Spotlight */}
      <div className="crystal-ambient-spotlight" />

      {/* 3D Faceted Crystal Core SVG */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="crystal-svg-object"
      >
        <defs>
          <linearGradient id="facetTopCyan" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#A5F3FC" />
            <stop offset="50%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#1E40AF" />
          </linearGradient>

          <linearGradient id="facetMidBlue" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#60A5FA" />
            <stop offset="50%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#1D4ED8" />
          </linearGradient>

          <linearGradient id="facetVioletPink" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#C084FC" />
            <stop offset="60%" stopColor="#8B5CF6" />
            <stop offset="100%" stopColor="#6D28D9" />
          </linearGradient>

          <linearGradient id="facetBottomDeep" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="50%" stopColor="#6366F1" />
            <stop offset="100%" stopColor="#0F172A" />
          </linearGradient>

          <linearGradient id="facetHighlight" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#BAE6FD" stopOpacity="0.1" />
          </linearGradient>
        </defs>

        {/* Central 3D Crystal Facets */}
        <g className="crystal-geometry-group">
          {/* Top Apex Facet */}
          <polygon points="100,20 145,65 100,80" fill="url(#facetTopCyan)" opacity="0.95" />
          <polygon points="100,20 55,65 100,80" fill="url(#facetTopCyan)" opacity="0.85" />
          
          {/* Left Wing Facets */}
          <polygon points="100,20 55,65 25,100" fill="url(#facetMidBlue)" opacity="0.9" />
          <polygon points="55,65 25,100 65,135" fill="url(#facetVioletPink)" opacity="0.95" />
          <polygon points="55,65 100,80 100,120" fill="url(#facetMidBlue)" opacity="0.9" />
          <polygon points="55,65 65,135 100,120" fill="url(#facetVioletPink)" opacity="0.85" />

          {/* Right Wing Facets */}
          <polygon points="100,20 145,65 175,100" fill="url(#facetMidBlue)" opacity="0.9" />
          <polygon points="145,65 175,100 135,135" fill="url(#facetVioletPink)" opacity="0.95" />
          <polygon points="145,65 100,80 100,120" fill="url(#facetMidBlue)" opacity="0.85" />
          <polygon points="145,65 135,135 100,120" fill="url(#facetVioletPink)" opacity="0.9" />

          {/* Bottom Apex Facets */}
          <polygon points="25,100 65,135 100,180" fill="url(#facetBottomDeep)" opacity="0.9" />
          <polygon points="65,135 100,120 100,180" fill="url(#facetBottomDeep)" opacity="0.95" />
          <polygon points="175,100 135,135 100,180" fill="url(#facetBottomDeep)" opacity="0.9" />
          <polygon points="135,135 100,120 100,180" fill="url(#facetBottomDeep)" opacity="0.95" />

          {/* Specular Highlight Sheen */}
          <polygon points="100,22 140,63 100,76" fill="url(#facetHighlight)" />
          <polygon points="100,22 96,76 75,60" fill="url(#facetHighlight)" opacity="0.6" />
        </g>
      </svg>
    </div>
  );
}

export default CrystalCore;

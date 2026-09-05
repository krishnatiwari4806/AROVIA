import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AroviaLogo } from '../common/AroviaLogo';

/**
 * AROVIA 3D Intro Sequence Component
 * 
 * 6-Stage Storyboard (5.5s Duration):
 * 01 [0.0s - 1.0s]: Perspective digital grid & cyberspace particle nodes fade in darkness.
 * 02 [1.0s - 2.5s]: 3D isometric geometric cubes/prisms extrude upward from grid.
 * 03 [2.5s - 3.8s]: Geometric elements converge and align into the iconic 'A' shape.
 * 04 [3.8s - 4.8s]: High-intensity light sweep & specular beam polishes the logo contour.
 * 05 [4.8s - 5.5s]: Full 3D AROVIA Logo + typography brand reveal with energetic aura.
 * 06 [5.5s - 6.0s]: Smooth zoom & dissolve transition directly into the application.
 */
export function IntroSequence({ onComplete }) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const [currentStage, setCurrentStage] = useState(1); // 1 to 6
  const [isExiting, setIsExiting] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);

  // Check prefers-reduced-motion
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mediaQuery.matches) {
      handleSkip();
    }
  }, []);

  const handleSkip = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setIsExiting(true);
    try {
      sessionStorage.setItem('arovia_intro_seen', 'true');
    } catch {
      // ignore
    }
    setTimeout(() => {
      onComplete?.();
    }, 400);
  }, [onComplete]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const startTime = performance.now();
    const TOTAL_DURATION = 5800; // 5.8s total duration

    // Particle nodes for grid
    const particles = Array.from({ length: 45 }, () => ({
      x: (Math.random() - 0.5) * width,
      y: (Math.random() - 0.5) * height,
      z: Math.random() * 800 + 100,
      size: Math.random() * 2 + 1,
      speed: Math.random() * 1.5 + 0.5,
      color: Math.random() > 0.5 ? '#22D3EE' : '#8B5CF6',
    }));

    const render = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / TOTAL_DURATION);
      setProgressPercent(Math.round(progress * 100));

      // Determine stage
      if (elapsed < 1000) {
        setCurrentStage(1);
      } else if (elapsed < 2500) {
        setCurrentStage(2);
      } else if (elapsed < 3800) {
        setCurrentStage(3);
      } else if (elapsed < 4800) {
        setCurrentStage(4);
      } else if (elapsed < 5400) {
        setCurrentStage(5);
      } else {
        setCurrentStage(6);
      }

      ctx.clearRect(0, 0, width, height);

      // Deep space background
      const bgGrad = ctx.createRadialGradient(
        width / 2,
        height / 2,
        20,
        width / 2,
        height / 2,
        Math.max(width, height) * 0.7
      );
      bgGrad.addColorStop(0, '#0F131D');
      bgGrad.addColorStop(0.5, '#0B0D12');
      bgGrad.addColorStop(1, '#050609');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;

      // STAGE 01 & STAGE 02: 3D Perspective Grid
      if (elapsed < 3500) {
        const gridAlpha = elapsed < 1000 ? elapsed / 1000 : Math.max(0, 1 - (elapsed - 2500) / 1000);
        ctx.save();
        ctx.strokeStyle = `rgba(34, 211, 238, ${gridAlpha * 0.25})`;
        ctx.lineWidth = 1;

        const horizon = centerY + 90;
        const fov = 350;

        // Perspective lines converging to horizon center
        for (let i = -10; i <= 10; i++) {
          const startX = centerX + i * 90;
          ctx.beginPath();
          ctx.moveTo(centerX, horizon);
          ctx.lineTo(startX * 2 - centerX, height);
          ctx.stroke();
        }

        // Horizontal depth grid lines
        const step = (elapsed * 0.05) % 30;
        for (let y = 0; y < 12; y++) {
          const depth = (y * 25 + step) / 300;
          const currentY = horizon + depth * (height - horizon);
          ctx.beginPath();
          ctx.moveTo(0, currentY);
          ctx.lineTo(width, currentY);
          ctx.stroke();
        }
        ctx.restore();
      }

      // STAGE 02: Isometric blocks extruding from grid
      if (elapsed >= 900 && elapsed < 3600) {
        const extrusionProgress = Math.min(1, Math.max(0, (elapsed - 900) / 1400));
        const fadeOut = elapsed > 2800 ? Math.max(0, 1 - (elapsed - 2800) / 800) : 1;

        ctx.save();
        ctx.translate(centerX, centerY + 30);

        const blocks = [
          { x: -110, y: 40, w: 45, maxH: 60, delay: 0, color: '#22D3EE' },
          { x: -65, y: 10, w: 45, maxH: 95, delay: 0.15, color: '#38BDF8' },
          { x: -20, y: -25, w: 45, maxH: 130, delay: 0.3, color: '#5B8CFF' },
          { x: 25, y: 10, w: 45, maxH: 95, delay: 0.45, color: '#8B5CF6' },
          { x: 70, y: 40, w: 45, maxH: 60, delay: 0.6, color: '#E879F9' },
        ];

        blocks.forEach((b) => {
          const effectiveP = Math.min(1, Math.max(0, (extrusionProgress - b.delay) / (1 - b.delay)));
          const h = b.maxH * effectiveP;
          if (h <= 0) return;

          // Draw isometric cuboid
          ctx.fillStyle = b.color;
          ctx.globalAlpha = 0.85 * fadeOut;

          // Front face
          ctx.beginPath();
          ctx.rect(b.x, b.y - h, b.w, h);
          ctx.fill();

          // Top face highlight
          ctx.fillStyle = '#FFFFFF';
          ctx.globalAlpha = 0.4 * fadeOut;
          ctx.beginPath();
          ctx.moveTo(b.x, b.y - h);
          ctx.lineTo(b.x + 12, b.y - h - 10);
          ctx.lineTo(b.x + b.w + 12, b.y - h - 10);
          ctx.lineTo(b.x + b.w, b.y - h);
          ctx.closePath();
          ctx.fill();
        });
        ctx.restore();
      }

      // STAGE 01 - 04: Cyberspace Ambient Particles
      ctx.save();
      particles.forEach((p) => {
        p.z -= p.speed;
        if (p.z <= 0) p.z = 800;

        const k = 250 / p.z;
        const px = p.x * k + centerX;
        const py = p.y * k + centerY;

        if (px >= 0 && px <= width && py >= 0 && py <= height) {
          const alpha = Math.min(1, (800 - p.z) / 400);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = alpha * 0.6;
          ctx.beginPath();
          ctx.arc(px, py, p.size * k, 0, Math.PI * 2);
          ctx.fill();
        }
      });
      ctx.restore();

      // STAGE 04: Energy Sweep Beam
      if (elapsed >= 3600 && elapsed < 4800) {
        const sweepProgress = (elapsed - 3600) / 1200; // 0 to 1
        const sweepX = centerX - 250 + sweepProgress * 500;

        ctx.save();
        const sweepGrad = ctx.createLinearGradient(sweepX - 80, centerY - 150, sweepX + 80, centerY + 150);
        sweepGrad.addColorStop(0, 'rgba(34, 211, 238, 0)');
        sweepGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.7)');
        sweepGrad.addColorStop(0.7, 'rgba(139, 92, 246, 0.8)');
        sweepGrad.addColorStop(1, 'rgba(232, 121, 249, 0)');

        ctx.strokeStyle = sweepGrad;
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.moveTo(sweepX - 120, centerY - 160);
        ctx.lineTo(sweepX + 120, centerY + 160);
        ctx.stroke();

        // Glow flare at sweep center
        ctx.fillStyle = '#FFFFFF';
        ctx.globalAlpha = 0.9;
        ctx.beginPath();
        ctx.arc(sweepX, centerY, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(render);
      } else {
        // Intro complete
        handleSkip();
      }
    };

    animationFrameRef.current = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [handleSkip]);

  return (
    <div className={`arovia-intro-container ${isExiting ? 'fade-out' : ''}`}>
      {/* Dynamic 3D WebGL / Canvas Viewport */}
      <canvas ref={canvasRef} className="arovia-intro-canvas" />

      {/* Center 3D Logo Reveal Layer */}
      <div className={`arovia-intro-content stage-${currentStage}`}>
        {currentStage >= 3 && (
          <div className="arovia-intro-logo-box">
            <AroviaLogo
              variant="full"
              size={currentStage >= 5 ? 100 : 80}
              animated={currentStage >= 4}
              className={`intro-logo-anim stage-${currentStage}`}
            />
          </div>
        )}
      </div>

      {/* Top Header & Skip Button */}
      <div className="arovia-intro-overlay-top">
        <div className="arovia-intro-badge">
          <span className="intro-live-dot" />
          <span>AROVIA 3D INTRO FLOW</span>
        </div>

        <button className="arovia-intro-skip-btn" onClick={handleSkip}>
          Skip Intro <span>→</span>
        </button>
      </div>

      {/* Bottom Storyboard Progress Bar */}
      <div className="arovia-intro-bottom-bar">
        <div className="storyboard-stage-indicators">
          <span className={currentStage >= 1 ? 'active' : ''}>01 Grid</span>
          <span className={currentStage >= 2 ? 'active' : ''}>02 Extrude</span>
          <span className={currentStage >= 3 ? 'active' : ''}>03 Align A</span>
          <span className={currentStage >= 4 ? 'active' : ''}>04 Sweep</span>
          <span className={currentStage >= 5 ? 'active' : ''}>05 Reveal</span>
          <span className={currentStage >= 6 ? 'active' : ''}>06 App</span>
        </div>

        <div className="storyboard-timeline-track">
          <div
            className="storyboard-timeline-progress"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default IntroSequence;

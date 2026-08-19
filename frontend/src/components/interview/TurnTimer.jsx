import React, { useState, useEffect, useRef } from 'react';
import { Clock, AlertCircle } from 'lucide-react';

/**
 * Soft Pacing Countdown Timer component.
 * Budget: 120s (default) or 180s (system design).
 * Soft warning at 30s (amber) and 0s (red) without forceful interruption.
 */
export function TurnTimer({ budgetSeconds = 120, onTick, isPaused = false }) {
  const [elapsed, setElapsed] = useState(0);
  const onTickRef = useRef(onTick);
  onTickRef.current = onTick;

  useEffect(() => {
    setElapsed(0);
  }, [budgetSeconds]);

  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      setElapsed((prev) => {
        const next = prev + 1;
        if (onTickRef.current) {
          onTickRef.current(next);
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isPaused]);

  const remaining = budgetSeconds - elapsed;
  const isOvertime = remaining <= 0;
  const isWarning = remaining > 0 && remaining <= 30;

  const formatTime = (seconds) => {
    const absSec = Math.abs(seconds);
    const mins = Math.floor(absSec / 60);
    const secs = absSec % 60;
    const prefix = seconds < 0 ? '+' : '';
    return `${prefix}${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  let timerClass = 'timer-green';
  if (isOvertime) timerClass = 'timer-red';
  else if (isWarning) timerClass = 'timer-amber';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
      <div className={`timer-container ${timerClass}`}>
        <Clock size={16} />
        <span>{formatTime(remaining)}</span>
      </div>
      {isOvertime && (
        <span style={{ fontSize: '0.75rem', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <AlertCircle size={12} />
          Suggested time elapsed — wrap up your answer
        </span>
      )}
      {isWarning && (
        <span style={{ fontSize: '0.75rem', color: 'var(--warning)' }}>
          30s remaining
        </span>
      )}
    </div>
  );
}

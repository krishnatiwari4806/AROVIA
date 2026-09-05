import React, { useState, useEffect, useRef } from 'react';
import { Clock } from 'lucide-react';

/**
 * Sleek Turn Timer matching Figma interview room: `03:45 / 05:00`.
 */
export function TurnTimer({ durationLimitSec = 300, onDurationTick, isPaused = false }) {
  const [elapsed, setElapsed] = useState(0);
  const onTickRef = useRef(onDurationTick);
  onTickRef.current = onDurationTick;

  useEffect(() => {
    setElapsed(0);
  }, [durationLimitSec]);

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

  const formatSeconds = (sec) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const isWarning = elapsed >= durationLimitSec - 30;

  return (
    <div className={`arovia-turn-timer ${isWarning ? 'timer-warning' : ''}`}>
      <Clock size={15} className="timer-clock-icon" />
      <span className="timer-elapsed">{formatSeconds(elapsed)}</span>
      <span className="timer-separator">/</span>
      <span className="timer-limit">{formatSeconds(durationLimitSec)}</span>
    </div>
  );
}

export default TurnTimer;

import React, { useState, useEffect, useRef } from 'react';
import { Clock } from 'lucide-react';

/**
 * Sleek Turn Timer matching Figma interview room: `03:45 / 05:00`.
 * Owns display timer state internally to prevent parent InterviewRoom re-renders.
 */
export function TurnTimer({
  turnId,
  durationLimitSec = 300,
  onDurationTick,
  isPaused = false,
}) {
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef(Date.now());
  const onTickRef = useRef(onDurationTick);
  onTickRef.current = onDurationTick;

  // Reset timer when a new question turn begins or duration limit changes
  useEffect(() => {
    startTimeRef.current = Date.now();
    setElapsed(0);
  }, [turnId, durationLimitSec]);

  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      const currentElapsed = Math.round((Date.now() - startTimeRef.current) / 1000);
      setElapsed(currentElapsed);
      if (onTickRef.current) {
        onTickRef.current(currentElapsed);
      }
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

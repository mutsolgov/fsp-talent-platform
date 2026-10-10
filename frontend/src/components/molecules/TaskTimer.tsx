import React, { useState, useEffect } from 'react';
import { Clock, AlertCircle } from '../icons';

export interface TaskTimerProps {
  totalSeconds: number;
  onTimeExpired: () => void;
  className?: string;
}

export const TaskTimer: React.FC<TaskTimerProps> = ({
  totalSeconds,
  onTimeExpired,
  className = '',
}) => {
  const [secondsLeft, setSecondsLeft] = useState(totalSeconds);

  useEffect(() => {
    setSecondsLeft(totalSeconds);
  }, [totalSeconds]);

  useEffect(() => {
    if (secondsLeft <= 0) {
      onTimeExpired();
      return;
    }

    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onTimeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [secondsLeft, onTimeExpired]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const isUrgent = secondsLeft < 300; // less than 5 min

  return (
    <div
      role="timer"
      aria-live="polite"
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-[6px] font-mono text-xs border transition-all ${
        isUrgent
          ? 'bg-rose-950/30 border-[#EC1D35] text-[#FB7185] shadow-[0_0_12px_rgba(236,29,53,0.3)] animate-pulse'
          : 'bg-[#1E1F26] border-[#3D3E42] text-[#EDEDED]'
      } ${className}`}
    >
      {isUrgent ? <AlertCircle size={14} className="text-[#EC1D35]" /> : <Clock size={14} className="text-[#402FFF]" />}
      <span>
        Осталось времени:{' '}
        <strong className="text-sm font-bold tracking-widest">
          {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
        </strong>
      </span>
    </div>
  );
};

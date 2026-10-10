import React from 'react';

export interface ProgressBarProps {
  value: number;
  max?: number;
  color?: 'mint' | 'purple' | 'gradient';
  showLabel?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  color = 'mint',
  showLabel = false,
  className = '',
}) => {
  const percentage = Math.max(0, Math.min(100, (value / max) * 100));

  const colorClasses = {
    mint: 'bg-[#00F5D4] shadow-[0_0_8px_rgba(0,245,212,0.4)]',
    purple: 'bg-[#402FFF] shadow-[0_0_8px_rgba(64,47,255,0.4)]',
    gradient: 'bg-gradient-to-r from-[#402FFF] to-[#00F5D4]',
  }[color];

  return (
    <div className={`flex flex-col gap-1 w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between items-center text-xs font-mono text-[#C8C9CA]">
          <span>Прогресс</span>
          <span className="font-semibold text-[#EDEDED]">{Math.round(percentage)}%</span>
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className="w-full h-2 rounded-full bg-[#2D2E37] overflow-hidden"
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ${colorClasses}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

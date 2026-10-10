import React from 'react';

export interface StatusDotProps {
  status: 'active' | 'idle' | 'cooldown' | 'error';
  label?: string;
  className?: string;
}

export const StatusDot: React.FC<StatusDotProps> = ({ status, label, className = '' }) => {
  const dotClasses = {
    active: 'bg-[#00F5D4] shadow-[0_0_8px_rgba(0,245,212,0.8)] animate-pulse',
    idle: 'bg-[#9B9C9E]',
    cooldown: 'bg-[#FBBF24] shadow-[0_0_8px_rgba(251,191,36,0.6)]',
    error: 'bg-[#EC1D35] shadow-[0_0_8px_rgba(236,29,53,0.8)]',
  }[status];

  return (
    <span role="status" className={`inline-flex items-center gap-2 ${className}`}>
      <span className={`w-2 h-2 rounded-full inline-block ${dotClasses}`} />
      {label && <span className="text-xs font-mono text-[#C8C9CA]">{label}</span>}
    </span>
  );
};

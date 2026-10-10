import React from 'react';
import { CheckCircle, AlertCircle, Clock } from '../icons';

export interface TestResultBadgeProps {
  status: 'passed' | 'failed' | 'tle' | 'ce';
  executionTimeMs?: number;
  memoryKb?: number;
  className?: string;
}

export const TestResultBadge: React.FC<TestResultBadgeProps> = ({
  status,
  executionTimeMs,
  memoryKb,
  className = '',
}) => {
  const config = {
    passed: {
      label: 'Пройден (Accepted)',
      icon: <CheckCircle size={14} className="text-[#00F5D4]" />,
      style: 'bg-emerald-950/40 text-[#00F5D4] border-emerald-500/40 shadow-[0_0_10px_rgba(0,245,212,0.2)]',
    },
    failed: {
      label: 'Ошибка (Wrong Answer)',
      icon: <AlertCircle size={14} className="text-[#FB7185]" />,
      style: 'bg-rose-950/40 text-[#FB7185] border-[#EC1D35]',
    },
    tle: {
      label: 'Превышен лимит времени (TLE)',
      icon: <Clock size={14} className="text-[#FBBF24]" />,
      style: 'bg-amber-950/40 text-[#FBBF24] border-amber-500/40',
    },
    ce: {
      label: 'Ошибка компиляции (CE)',
      icon: <AlertCircle size={14} className="text-[#FB7185]" />,
      style: 'bg-rose-950/40 text-[#FB7185] border-rose-500/40',
    },
  }[status];

  return (
    <div
      role="status"
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-[6px] border text-xs font-mono font-medium ${config.style} ${className}`}
    >
      {config.icon}
      <span>{config.label}</span>
      {executionTimeMs !== undefined && (
        <span className="text-[#9B9C9E] text-[11px] border-l border-current/20 pl-1.5">
          {executionTimeMs}мс
        </span>
      )}
      {memoryKb !== undefined && (
        <span className="text-[#9B9C9E] text-[11px]">
          {(memoryKb / 1024).toFixed(1)}Мб
        </span>
      )}
    </div>
  );
};

import React from 'react';
import { CheckCircle, AlertCircle } from '../icons';

export interface BenchmarkMetricTileProps {
  label: string;
  value: number;
  threshold: number;
  unit?: string;
  higherIsBetter?: boolean;
  className?: string;
}

export const BenchmarkMetricTile: React.FC<BenchmarkMetricTileProps> = ({
  label,
  value,
  threshold,
  unit = '',
  higherIsBetter = true,
  className = '',
}) => {
  const isPassed = higherIsBetter ? value >= threshold : value <= threshold;

  return (
    <div
      role="region"
      aria-label={`Метрика ${label}: ${value} (порог ${threshold})`}
      className={`p-3.5 rounded-[10px] bg-[#202129] border transition-all flex flex-col justify-between gap-2.5 ${
        isPassed
          ? 'border-emerald-500/30 hover:border-emerald-500/50 shadow-[0_0_12px_rgba(0,245,212,0.1)]'
          : 'border-rose-500/30 hover:border-rose-500/50'
      } ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-[#C8C9CA] font-medium">{label}</span>
        {isPassed ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#00F5D4] bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/30">
            <CheckCircle size={12} />
            PASS
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#FB7185] bg-rose-950/40 px-1.5 py-0.5 rounded border border-rose-500/30">
            <AlertCircle size={12} />
            FAIL
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-mono font-bold text-white tracking-tight">
          {value.toFixed(4)}
          {unit}
        </span>
        <span className="text-xs font-mono text-[#9B9C9E]">
          порог {higherIsBetter ? '≥' : '≤'} {threshold.toFixed(2)}
        </span>
      </div>
    </div>
  );
};

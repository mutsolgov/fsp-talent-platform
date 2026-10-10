import React from 'react';

export interface DiffDeltaIndicatorProps {
  deltaS: number;
  showZero?: boolean;
  className?: string;
}

export const DiffDeltaIndicator: React.FC<DiffDeltaIndicatorProps> = ({
  deltaS,
  showZero = false,
  className = '',
}) => {
  if (deltaS === 0 && !showZero) return null;

  const isPositive = deltaS > 0;
  const isZero = deltaS === 0;

  const formatted = `${isPositive ? '+' : ''}${deltaS.toFixed(1)}`;

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono text-xs font-bold px-1.5 py-0.5 rounded ${
        isPositive
          ? 'text-[#00F5D4] bg-emerald-950/40 border border-emerald-500/30 shadow-[0_0_8px_rgba(0,245,212,0.2)]'
          : isZero
          ? 'text-[#9B9C9E] bg-[#2D2E37]'
          : 'text-[#FB7185] bg-rose-950/40 border border-rose-500/30'
      } ${className}`}
      title={`Динамический сдвиг оценки: ${formatted} пунктов`}
    >
      <span>ΔS {formatted}</span>
      <span className="sr-only">
        Изменение скоринга на {deltaS > 0 ? `плюс ${deltaS}` : deltaS} пунктов
      </span>
    </span>
  );
};

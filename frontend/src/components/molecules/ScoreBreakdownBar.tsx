import React from 'react';

export interface ScoreBreakdownBarProps {
  totalScore: number;
  breakdown: {
    test: number;
    stack: number;
    fsp: number;
    freshness: number;
  };
  isFsp: boolean;
  className?: string;
}

export const ScoreBreakdownBar: React.FC<ScoreBreakdownBarProps> = ({
  totalScore,
  breakdown,
  isFsp,
  className = '',
}) => {
  return (
    <div className={`flex flex-col gap-1.5 w-full ${className}`}>
      <div className="flex justify-between items-center text-xs font-mono">
        <span className="text-[#9B9C9E]">Интегральный скоринг S:</span>
        <span className="text-sm font-bold text-[#00F5D4]">{totalScore.toFixed(1)} / 100</span>
      </div>

      <div className="flex w-full h-2 rounded-full overflow-hidden bg-[#2D2E37] gap-0.5">
        <div
          title={`Тест: ${breakdown.test.toFixed(1)}`}
          className="bg-[#402FFF] transition-all"
          style={{ width: `${Math.max(2, breakdown.test)}%` }}
        />
        <div
          title={`Стек: ${breakdown.stack.toFixed(1)}`}
          className="bg-[#00F5D4] transition-all"
          style={{ width: `${Math.max(2, breakdown.stack)}%` }}
        />
        {isFsp && (
          <div
            title={`ФСП: ${breakdown.fsp.toFixed(1)}`}
            className="bg-[#EC1D35] transition-all"
            style={{ width: `${Math.max(2, breakdown.fsp)}%` }}
          />
        )}
        <div
          title={`Свежесть: ${breakdown.freshness.toFixed(1)}`}
          className="bg-[#7B2CBF] transition-all"
          style={{ width: `${Math.max(2, breakdown.freshness)}%` }}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-mono text-[#9B9C9E] mt-0.5">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#402FFF]" />
          Тест ({isFsp ? '35%' : '52%'})
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#00F5D4]" />
          Стек (30%)
        </span>
        {isFsp && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#EC1D35]" />
            ФСП (20%)
          </span>
        )}
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#7B2CBF]" />
          Свежесть ({isFsp ? '15%' : '18%'})
        </span>
      </div>
    </div>
  );
};

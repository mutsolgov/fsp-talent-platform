import React from 'react';

export interface FspCircuitConnectorProps {
  activeStep?: number;
  totalSteps?: number;
  direction?: 'horizontal' | 'vertical';
  orientation?: 'horizontal' | 'vertical';
  variant?: 'default' | 'accent' | 'subtle';
  className?: string;
}

export const FspCircuitConnector: React.FC<FspCircuitConnectorProps> = ({
  activeStep = 1,
  totalSteps = 4,
  direction = 'horizontal',
  orientation,
  variant = 'default',
  className = '',
}) => {
  const effectiveDirection = orientation || direction;
  const isHorizontal = effectiveDirection === 'horizontal';
  const isAccent = variant === 'accent';

  return (
    <div
      role="presentation"
      className={`relative flex items-center justify-between ${
        isHorizontal ? 'w-full h-12' : 'h-full w-12 flex-col'
      } ${className}`}
    >
      {/* Decorative Brand Circuit Background Line */}
      <div
        className={`absolute bg-repeat opacity-40 pointer-events-none ${
          isHorizontal
            ? 'top-1/2 left-4 right-4 h-1 -translate-y-1/2 bg-[url("/brand/lineline1.png")] bg-contain'
            : 'left-1/2 top-4 bottom-4 w-1 -translate-x-1/2 bg-[url("/brand/lineline1.png")] bg-contain'
        }`}
      />

      {/* Dynamic Glow Line */}
      <div
        className={`absolute transition-all duration-500 ${
          isAccent
            ? 'bg-[#00F5D4] shadow-[0_0_8px_rgba(0,245,212,0.6)]'
            : 'bg-[#402FFF] shadow-[0_0_8px_rgba(64,47,255,0.6)]'
        } ${
          isHorizontal
            ? 'top-1/2 left-4 h-0.5 -translate-y-1/2'
            : 'left-1/2 top-4 w-0.5 -translate-x-1/2'
        }`}
        style={
          isHorizontal
            ? { width: `${Math.min(100, Math.max(0, ((activeStep - 1) / (totalSteps - 1)) * 100))}%` }
            : { height: `${Math.min(100, Math.max(0, ((activeStep - 1) / (totalSteps - 1)) * 100))}%` }
        }
      />

      {/* Step Nodes */}
      {Array.from({ length: totalSteps }).map((_, index) => {
        const stepNum = index + 1;
        const isCompleted = stepNum < activeStep;
        const isCurrent = stepNum === activeStep;

        return (
          <div
            key={stepNum}
            className={`relative z-10 flex items-center justify-center rounded-full border-2 transition-all font-mono text-xs font-bold ${
              isCompleted
                ? 'w-7 h-7 bg-[#402FFF] border-[#402FFF] text-white shadow-[0_0_12px_rgba(64,47,255,0.5)]'
                : isCurrent
                ? 'w-8 h-8 bg-[#1B1C21] border-[#00F5D4] text-[#00F5D4] shadow-[0_0_16px_rgba(0,245,212,0.6)] animate-pulse'
                : 'w-7 h-7 bg-[#202129] border-[#3D3E42] text-[#9B9C9E]'
            }`}
          >
            {stepNum}
          </div>
        );
      })}
    </div>
  );
};

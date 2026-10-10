import React from 'react';

export interface SliderProps {
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (v: number) => void;
  label?: string;
  unit?: string;
  className?: string;
}

export const Slider: React.FC<SliderProps> = ({
  min,
  max,
  step = 1,
  value,
  onChange,
  label,
  unit = '',
  className = '',
}) => {
  const percentage = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));

  return (
    <div className={`flex flex-col gap-2 w-full ${className}`}>
      {(label || unit) && (
        <div className="flex justify-between items-center text-xs font-mono text-[#C8C9CA]">
          {label && <span>{label}</span>}
          <span className="text-[#00F5D4] font-semibold">
            {value} {unit}
          </span>
        </div>
      )}
      <div className="relative w-full flex items-center">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          role="slider"
          aria-valuenow={value}
          aria-valuemin={min}
          aria-valuemax={max}
          className="w-full h-2 bg-[#2D2E37] rounded-lg appearance-none cursor-pointer accent-[#402FFF]"
          style={{
            background: `linear-gradient(to right, #402FFF 0%, #402FFF ${percentage}%, #2D2E37 ${percentage}%, #2D2E37 100%)`,
          }}
        />
      </div>
    </div>
  );
};

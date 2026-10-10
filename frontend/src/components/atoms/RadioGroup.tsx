import React from 'react';

export interface RadioOption {
  label: string;
  value: string;
  desc?: string;
}

export interface RadioGroupProps {
  name: string;
  value: string;
  onChange: (val: string) => void;
  options: RadioOption[];
  className?: string;
}

export const RadioGroup: React.FC<RadioGroupProps> = ({
  name,
  value,
  onChange,
  options,
  className = '',
}) => {
  return (
    <div role="radiogroup" className={`flex flex-col gap-2.5 ${className}`}>
      {options.map((opt) => {
        const isSelected = value === opt.value;
        const optId = `${name}-${opt.value}`;
        return (
          <label
            key={opt.value}
            htmlFor={optId}
            className={`flex items-start gap-3 p-3 rounded-[8px] border transition-all cursor-pointer select-none ${
              isSelected
                ? 'bg-[#402FFF]/10 border-[#402FFF] shadow-[0_0_12px_rgba(64,47,255,0.2)]'
                : 'bg-[#1E1F26] border-[#3D3E42] hover:border-[#5F5F66]'
            }`}
          >
            <div className="relative flex items-center justify-center mt-0.5">
              <input
                id={optId}
                type="radio"
                name={name}
                value={opt.value}
                checked={isSelected}
                onChange={() => onChange(opt.value)}
                aria-checked={isSelected}
                className="sr-only"
              />
              <div
                className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                  isSelected ? 'border-[#402FFF]' : 'border-[#5F5F66]'
                }`}
              >
                {isSelected && <div className="w-2 h-2 rounded-full bg-[#402FFF]" />}
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-mono font-medium text-[#EDEDED]">{opt.label}</span>
              {opt.desc && <span className="text-xs font-sans text-[#9B9C9E] mt-0.5">{opt.desc}</span>}
            </div>
          </label>
        );
      })}
    </div>
  );
};

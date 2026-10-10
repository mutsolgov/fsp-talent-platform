import React, { ReactNode } from 'react';
import { Check } from '../icons';

export interface CheckboxProps {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  label: ReactNode;
  required?: boolean;
  error?: string;
  disabled?: boolean;
  className?: string;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  id,
  checked,
  onChange,
  label,
  required = false,
  error,
  disabled = false,
  className = '',
}) => {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label
        htmlFor={id}
        className={`inline-flex items-start gap-2.5 cursor-pointer select-none ${
          disabled ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        <div className="relative flex items-center justify-center mt-0.5">
          <input
            id={id}
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            required={required}
            disabled={disabled}
            aria-required={required}
            aria-checked={checked}
            aria-invalid={Boolean(error)}
            className="sr-only"
          />
          <div
            className={`w-4 h-4 rounded-[4px] border flex items-center justify-center transition-all ${
              checked
                ? 'bg-[#402FFF] border-[#402FFF] text-white shadow-[0_0_8px_rgba(64,47,255,0.4)]'
                : 'bg-[#1E1F26] border-[#3D3E42] hover:border-[#402FFF]'
            } ${error ? 'border-[#EC1D35]' : ''}`}
          >
            {checked && <Check size={12} strokeWidth={3} />}
          </div>
        </div>
        <div className="text-xs sm:text-sm font-sans text-[#EDEDED] leading-relaxed">
          {label}
          {required && <span className="text-[#EC1D35] ml-1">*</span>}
        </div>
      </label>
      {error && (
        <span className="text-xs font-mono text-[#FB7185] pl-6.5">{error}</span>
      )}
    </div>
  );
};

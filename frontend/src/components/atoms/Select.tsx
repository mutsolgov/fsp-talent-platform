import React, { SelectHTMLAttributes } from 'react';

export interface SelectOption {
  label: string;
  value: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  id: string;
  label?: string;
  options: SelectOption[];
  error?: string;
}

export const Select: React.FC<SelectProps> = ({
  id,
  label,
  options,
  error,
  className = '',
  disabled,
  ...props
}) => {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label
          htmlFor={id}
          className="text-xs font-mono font-medium text-[#C8C9CA] tracking-wide"
        >
          {label}
        </label>
      )}
      <div className="relative w-full">
        <select
          id={id}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          className={`w-full px-3.5 py-2.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-sm border transition-colors outline-none appearance-none cursor-pointer
            ${
              error
                ? 'border-[#EC1D35] focus:border-[#EC1D35]'
                : 'border-[#3D3E42] focus:border-[#402FFF]'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
            ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#1E1F26] text-[#EDEDED]">
              {opt.label}
            </option>
          ))}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-[#9B9C9E]">
          <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
            <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
          </svg>
        </div>
      </div>
      {error && (
        <span id={`${id}-error`} className="text-xs font-mono text-[#FB7185]">
          {error}
        </span>
      )}
    </div>
  );
};

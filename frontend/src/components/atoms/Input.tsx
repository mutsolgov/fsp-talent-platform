import React, { InputHTMLAttributes } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label?: string;
  error?: string;
  helperText?: string;
  isMasked?: boolean;
}

export const Input: React.FC<InputProps> = ({
  id,
  label,
  error,
  helperText,
  isMasked = false,
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
        <input
          id={id}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : helperText ? `${id}-helper` : undefined}
          className={`w-full px-3.5 py-2.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-sm border transition-colors outline-none
            ${
              error
                ? 'border-[#EC1D35] focus:border-[#EC1D35] focus:ring-1 focus:ring-[#EC1D35]'
                : 'border-[#3D3E42] focus:border-[#402FFF] focus:ring-1 focus:ring-[#402FFF]'
            }
            disabled:opacity-50 disabled:bg-[#1B1C21] disabled:cursor-not-allowed
            placeholder:text-[#5F5F66]
            ${isMasked ? 'tracking-widest' : ''}
            ${className}`}
          {...props}
        />
      </div>
      {error && (
        <span id={`${id}-error`} className="text-xs font-mono text-[#FB7185] tracking-tight">
          {error}
        </span>
      )}
      {!error && helperText && (
        <span id={`${id}-helper`} className="text-xs font-mono text-[#9B9C9E]">
          {helperText}
        </span>
      )}
    </div>
  );
};

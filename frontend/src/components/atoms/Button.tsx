import React, { ReactNode, useTransition } from 'react';
import { Spinner } from './Spinner';

export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'fsp_mint';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  disabled?: boolean;
  onClick?: () => void | Promise<void>;
  children: ReactNode;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  onClick,
  children,
  type = 'button',
  className = '',
}) => {
  const [isPending, startTransition] = useTransition();
  const effectiveLoading = isLoading || isPending;

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs font-medium',
    md: 'px-4 py-2 text-sm font-medium',
    lg: 'px-6 py-3 text-base font-semibold',
  }[size];

  const variantClasses = {
    primary:
      'bg-[#402FFF] text-white hover:bg-[#3525E0] active:scale-[0.98] border border-transparent shadow-[0_0_16px_rgba(64,47,255,0.35)]',
    secondary:
      'bg-[#202129] text-[#EDEDED] border border-[#3D3E42] hover:border-[#402FFF] hover:bg-[#2D2E37] active:scale-[0.98]',
    ghost:
      'bg-transparent text-[#EDEDED] hover:bg-[#2D2E37] hover:text-white border border-transparent',
    danger:
      'bg-[#EC1D35] text-white hover:bg-[#D4142B] active:scale-[0.98] border border-transparent shadow-[0_0_12px_rgba(236,29,53,0.3)]',
    fsp_mint:
      'bg-[#00F5D4] text-[#1B1C21] font-semibold hover:bg-[#00D9BC] active:scale-[0.98] border border-transparent shadow-[0_0_16px_rgba(0,245,212,0.4)]',
  }[variant];

  const handleClick = () => {
    if (disabled || effectiveLoading || !onClick) return;
    startTransition(() => {
      onClick();
    });
  };

  return (
    <button
      type={type}
      disabled={disabled || effectiveLoading}
      aria-busy={effectiveLoading}
      onClick={handleClick}
      className={`inline-flex items-center justify-center gap-2 rounded-[6px] font-mono transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none ${sizeClasses} ${variantClasses} ${className}`}
    >
      {effectiveLoading && <Spinner size={size === 'lg' ? 'md' : 'sm'} />}
      {children}
    </button>
  );
};

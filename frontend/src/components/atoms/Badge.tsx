import React, { ReactNode } from 'react';

export interface BadgeProps {
  variant?: 'default' | 'fsp' | 'non_fsp' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md';
  children: ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  size = 'md',
  children,
  className = '',
}) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs sm:text-sm';

  const variantClasses = {
    default: 'bg-[#2D2E37] text-[#EDEDED] border border-[#3D3E42]',
    fsp: 'bg-[#402FFF]/15 text-[#EDEDED] border border-[#402FFF] shadow-[0_0_12px_rgba(64,47,255,0.3)]',
    non_fsp:
      'bg-[#00F5D4]/10 text-[#00F5D4] border border-[#00F5D4]/40 shadow-[0_0_12px_rgba(0,245,212,0.25)]',
    success: 'bg-emerald-950/40 text-[#00F5D4] border border-emerald-500/40',
    warning: 'bg-amber-950/40 text-[#FBBF24] border border-amber-500/40',
    danger: 'bg-rose-950/40 text-[#FB7185] border border-[#EC1D35]',
  }[variant];

  return (
    <span
      role="status"
      className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-[6px] tracking-wide transition-colors ${sizeClasses} ${variantClasses} ${className}`}
    >
      {children}
    </span>
  );
};

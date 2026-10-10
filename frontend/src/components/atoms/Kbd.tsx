import React, { ReactNode } from 'react';

export interface KbdProps {
  children: ReactNode;
  className?: string;
}

export const Kbd: React.FC<KbdProps> = ({ children, className = '' }) => {
  return (
    <kbd
      className={`inline-flex items-center justify-center px-1.5 py-0.5 rounded-[4px] bg-[#2D2E37] border border-[#3D3E42] text-[#C8C9CA] font-mono text-[11px] font-semibold shadow-[0_1px_0_1px_rgba(0,0,0,0.4)] select-none ${className}`}
    >
      {children}
    </kbd>
  );
};

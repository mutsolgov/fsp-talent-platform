import React from 'react';

export interface AvatarProps {
  src?: string;
  initials?: string;
  isMasked?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  initials = 'IT',
  isMasked = false,
  size = 'md',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-16 h-16 text-xl',
  }[size];

  if (isMasked) {
    return (
      <div
        role="img"
        aria-label="Анонимизированный кандидат (152-ФЗ)"
        className={`relative inline-flex items-center justify-center rounded-[10px] overflow-hidden border border-[#402FFF]/50 bg-[#1B1C21] shadow-[0_0_12px_rgba(64,47,255,0.25)] ${sizeClasses} ${className}`}
      >
        <img
          src="/brand/face1.png"
          alt="152-ФЗ Анонимный профиль"
          className="w-full h-full object-cover filter contrast-125 brightness-110"
        />
        <div className="absolute inset-0 bg-[#402FFF]/10 pointer-events-none" />
      </div>
    );
  }

  if (src) {
    return (
      <div
        role="img"
        aria-label={initials}
        className={`relative inline-flex items-center justify-center rounded-[10px] overflow-hidden border border-[#3D3E42] bg-[#202129] ${sizeClasses} ${className}`}
      >
        <img src={src} alt={initials} className="w-full h-full object-cover" />
      </div>
    );
  }

  return (
    <div
      role="img"
      aria-label={initials}
      className={`inline-flex items-center justify-center rounded-[10px] font-mono font-semibold bg-[#2D2E37] text-[#00F5D4] border border-[#3D3E42] select-none ${sizeClasses} ${className}`}
    >
      {initials}
    </div>
  );
};

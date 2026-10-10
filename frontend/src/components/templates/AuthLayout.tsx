import React, { ReactNode } from 'react';
import { RoleSwitcherBar } from '../molecules/RoleSwitcherBar';

export interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  subtitle?: string;
  className?: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title,
  subtitle,
  className = '',
}) => {
  return (
    <div className={`min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col justify-between p-4 sm:p-6 ${className}`}>
      {/* Top Header */}
      <header className="flex items-center justify-between max-w-6xl w-full mx-auto py-2">
        <a href="/" className="flex items-center gap-3">
          <img
            src="/brand/logo_01.svg"
            alt="ФСП Россия"
            className="h-9 w-auto"
          />
        </a>
        <RoleSwitcherBar />
      </header>

      {/* Main Centered Card */}
      <main className="flex items-center justify-center my-8">
        <div className="w-full max-w-md p-6 sm:p-8 rounded-[16px] bg-[#202129] border border-[#3D3E42] shadow-[0_20px_50px_rgba(0,0,0,0.7)] flex flex-col gap-6">
          <div className="flex flex-col text-center">
            <h1 className="font-mono text-2xl font-bold text-white tracking-tight">{title}</h1>
            {subtitle && (
              <p className="text-xs font-sans text-[#9B9C9E] mt-1.5 leading-relaxed">
                {subtitle}
              </p>
            )}
          </div>

          {children}

          <div className="text-[11px] font-sans text-[#9B9C9E] text-center leading-relaxed border-t border-[#2D2E37] pt-4">
            Вход в систему защищен в соответствии со стандартами 152-ФЗ РФ.
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl w-full mx-auto py-3 text-center text-xs font-mono text-[#5F5F66]">
        © 2026 Федерация спортивного программирования России • Цифровая платформа талантов
      </footer>
    </div>
  );
};

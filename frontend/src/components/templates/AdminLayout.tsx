import React, { ReactNode } from 'react';
import { RoleSwitcherBar } from '../molecules/RoleSwitcherBar';
import { Shield, FileText, Sliders } from '../icons';

export interface AdminLayoutProps {
  children: ReactNode;
  className?: string;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({ children, className = '' }) => {
  return (
    <div className={`min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col ${className}`}>
      <header className="border-b border-[#2D2E37] bg-[#202129] px-4 sm:px-8 py-3 sticky top-0 z-40">
        <div className="max-w-[1340px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <a href="/">
              <img src="/brand/logo_01.svg" alt="ФСП" className="h-8 w-auto" />
            </a>
            <span className="text-xs font-mono text-[#FB7185] bg-rose-950/40 px-2 py-0.5 rounded border border-rose-500/30">
              Административная панель безопасности
            </span>
          </div>

          <div className="flex items-center gap-4">
            <nav className="flex items-center gap-3 text-xs font-mono">
              <a href="/admin/audit-logs" className="hover:text-white">
                Аудит-логи 152-ФЗ
              </a>
              <a href="/admin/analytics" className="hover:text-white">
                Аналитика
              </a>
              <a href="/demo/dashboard" className="hover:text-[#00F5D4]">
                Демо Жюри
              </a>
            </nav>
            <RoleSwitcherBar />
          </div>
        </div>
      </header>

      <main className="max-w-[1340px] w-full mx-auto p-4 sm:p-8 flex-1">
        {children}
      </main>

      <footer className="border-t border-[#2D2E37] bg-[#202129] py-4 text-center text-xs font-mono text-[#5F5F66]">
        Контур информационной безопасности и соответствия 152-ФЗ платформы ФСП
      </footer>
    </div>
  );
};

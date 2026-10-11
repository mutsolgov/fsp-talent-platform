import React, { ReactNode } from 'react';
import { RoleSwitcherBar } from '../molecules/RoleSwitcherBar';
import { Shield, FileText, Sliders, LogOut } from '../icons';
import { useAuthStore } from '../../stores/useAuthStore';

export interface AdminLayoutProps {
  children: ReactNode;
  className?: string;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({ children, className = '' }) => {
  const { email, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    sessionStorage.clear();
    window.location.href = '/login';
  };

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
              {Boolean(import.meta.env?.VITE_ENABLE_DEMO_BAR === 'true') && (
                <a href="/demo/dashboard" className="hover:text-[#00F5D4]">
                  Демо Жюри
                </a>
              )}
            </nav>
            <RoleSwitcherBar />
            {email && (
              <span className="hidden sm:inline font-mono text-xs text-[#9B9C9E] bg-[#2D2E37] px-2.5 py-1 rounded-[6px] border border-[#3D3E42]">
                {email}
              </span>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] hover:text-white font-mono text-xs transition-colors cursor-pointer border border-[#3D3E42]"
              title="Выйти из системы"
            >
              <LogOut size={14} className="text-[#EC1D35]" />
              <span>Выйти</span>
            </button>
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

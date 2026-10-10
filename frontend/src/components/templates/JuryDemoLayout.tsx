import React, { ReactNode, useState } from 'react';
import { JuryControlPanel } from '../organisms/JuryControlPanel';
import { useAuthStore, UserRole } from '../../stores/useAuthStore';
import { useJuryDemoStore } from '../../stores/useJuryDemoStore';
import { Shield, Play, Lock, CheckCircle, AlertCircle } from '../icons';
import { api } from '../../api/client';

export interface JuryDemoLayoutProps {
  children: ReactNode;
  className?: string;
}

export const JuryDemoLayout: React.FC<JuryDemoLayoutProps> = ({ children, className = '' }) => {
  const { role, setAuthSession } = useAuthStore();
  const { toggleCooldownBypass } = useJuryDemoStore();
  const [seedBanner, setSeedBanner] = useState<{ message: string; isError?: boolean } | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);

  const handleRoleSwitch = async (r: string) => {
    try {
      const res = await api.post<any>('/demo/switch-role', { role: r });
      const accessToken = res.token?.access_token || res.access_token || '';
      const refreshToken = res.token?.refresh_token || res.access_token || '';
      const userRole = (res.user?.role || res.role || r) as UserRole;
      const userId = res.user?.id ?? res.user_id ?? 1;
      const userEmail = res.user?.email || res.email || `${r}@demo.local`;
      setAuthSession(accessToken, refreshToken, userRole, userId, userEmail);
    } catch (err: unknown) {
      console.error('Role switch failed in layout:', err);
    }
  };

  const handleSeed = async () => {
    setIsSeeding(true);
    try {
      const res = await api.post<any>('/demo/seed', { reset_database: false, seed_golden_dataset: true });
      const count = res.seeded_candidates_count ?? 60;
      const needsCount = res.seeded_needs_count ?? 15;
      setSeedBanner({
        message: `База данных успешно сидирована (${count} талантов, ${needsCount} потребностей, 25 таблиц)!`,
      });
      setTimeout(() => setSeedBanner(null), 4000);
    } catch (err: any) {
      console.error('Seed failed in layout:', err);
      setSeedBanner({
        message: err?.message || 'Ошибка сидирования базы данных',
        isError: true,
      });
      setTimeout(() => setSeedBanner(null), 4000);
    } finally {
      setIsSeeding(false);
    }
  };

  return (
    <div className={`min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col ${className}`}>
      {/* Top Header */}
      <header className="border-b border-[#2D2E37] bg-[#202129] px-4 sm:px-8 py-3 sticky top-0 z-40 flex flex-col gap-3">
        <div className="max-w-[1340px] w-full mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a href="/">
              <img src="/brand/logo_01.svg" alt="ФСП" className="h-8 w-auto" />
            </a>
            <span className="text-xs font-mono font-bold text-[#FFD700] bg-[#FFD700]/10 px-2 py-0.5 rounded border border-[#FFD700]/30">
              РЕЖИМ ЖЮРИ ХАКАТОНА (ЛЦТ 2026)
            </span>
          </div>

          <nav className="flex items-center gap-2 text-xs font-mono">
            <a
              href="/demo/dashboard"
              className="px-3 py-1.5 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-white"
            >
              Дашборд жюри
            </a>
            <a
              href="/demo/benchmark-runner"
              className="px-3 py-1.5 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white font-semibold shadow-[0_0_12px_rgba(64,47,255,0.4)]"
            >
              Бенчмарк 60×15
            </a>
            <a
              href="/admin/audit-logs"
              className="px-3 py-1.5 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED]"
            >
              Аудит 152-ФЗ
            </a>
          </nav>
        </div>

        {/* Embedded Jury Control Panel */}
        <div className="max-w-[1340px] w-full mx-auto">
          <JuryControlPanel
            activeRole={role}
            onRoleSwitch={handleRoleSwitch}
            onBypassCooldown={toggleCooldownBypass}
            onSeedDb={handleSeed}
          />
        </div>
      </header>

      {/* Reactive Seed Banner */}
      {seedBanner && (
        <div className="max-w-[1340px] w-full mx-auto px-4 sm:px-8 pt-3">
          <div
            className={`p-3.5 rounded-[10px] text-xs font-mono flex items-center gap-2 border ${
              seedBanner.isError
                ? 'bg-rose-950/40 border-rose-500/40 text-rose-300'
                : 'bg-[#00F5D4]/10 border-[#00F5D4]/40 text-[#00F5D4]'
            }`}
          >
            {seedBanner.isError ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
            <span>{seedBanner.message}</span>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="max-w-[1340px] w-full mx-auto p-4 sm:p-8 flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#2D2E37] bg-[#202129] py-4 text-center text-xs font-mono text-[#5F5F66]">
        Демонстрационная панель жюри хакатона ЛЦТ 2026 • Верификация математических критериев
      </footer>
    </div>
  );
};

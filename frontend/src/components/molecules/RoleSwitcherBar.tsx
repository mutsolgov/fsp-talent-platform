import React, { useState } from 'react';
import { User, Briefcase, Shield, Zap } from '../icons';
import { useAuthStore, UserRole } from '../../stores/useAuthStore';
import { useJuryDemoStore, DemoPersona } from '../../stores/useJuryDemoStore';
import { api } from '../../api/client';

export interface RoleSwitcherBarProps {
  currentRole?: string;
  onRoleChange?: (r: string) => void;
  isFloating?: boolean;
  className?: string;
}

interface SwitchRoleApiResponse {
  token?: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  };
  user?: {
    id: number;
    email: string;
    role: string;
    full_name?: string;
  };
  access_token?: string;
  user_id?: number;
  email?: string;
  role?: string;
}

export const RoleSwitcherBar: React.FC<RoleSwitcherBarProps> = ({
  currentRole: propRole,
  onRoleChange,
  isFloating = false,
  className = '',
}) => {
  const { role: storeRole, setAuthSession } = useAuthStore();
  const { activePersona, switchPersona } = useJuryDemoStore();
  const [loadingPersona, setLoadingPersona] = useState<string | null>(null);

  const active = propRole || storeRole;

  const personas: Array<{
    id: DemoPersona;
    role: UserRole;
    label: string;
    icon: React.ReactNode;
    desc: string;
  }> = [
    {
      id: 'candidate_with_fsp',
      role: 'candidate',
      label: 'Кандидат с ФСП',
      icon: <Zap size={14} className="text-[#FFD700]" />,
      desc: 'CAND-01 (МС/КМС, ЕВСК)',
    },
    {
      id: 'candidate_without_fsp',
      role: 'candidate',
      label: 'Кандидат без ФСП',
      icon: <User size={14} className="text-[#00F5D4]" />,
      desc: 'CAND-31 (Общий трек)',
    },
    {
      id: 'employer',
      role: 'employer',
      label: 'Работодатель (HR)',
      icon: <Briefcase size={14} className="text-[#402FFF]" />,
      desc: 'Потребности и банк',
    },
    {
      id: 'admin',
      role: 'admin',
      label: 'Жюри / Админ',
      icon: <Shield size={14} className="text-[#EC1D35]" />,
      desc: 'Бенчмарк и аудит',
    },
  ];

  const handleSelect = async (p: (typeof personas)[0]) => {
    setLoadingPersona(p.id);
    try {
      const res = await api.post<SwitchRoleApiResponse>('/demo/switch-role', { role: p.id });
      const accessToken = res.token?.access_token || res.access_token || '';
      const refreshToken = res.token?.refresh_token || res.access_token || '';
      const userRole = (res.user?.role || res.role || p.role) as UserRole;
      const userId = res.user?.id ?? res.user_id ?? 1;
      const userEmail = res.user?.email || res.email || `${p.id}@fsp.local`;

      setAuthSession(accessToken, refreshToken, userRole, userId, userEmail);
      switchPersona(p.id);
      onRoleChange?.(p.role);
    } catch (err: unknown) {
      console.error('Failed to switch demo role:', err);
      // Graceful offline fallback: update persona so UI stays responsive
      switchPersona(p.id);
      onRoleChange?.(p.role);
    } finally {
      setLoadingPersona(null);
    }
  };

  return (
    <div
      role="toolbar"
      aria-label="Панель переключения демо-ролей жюри"
      className={`flex items-center gap-1.5 p-1.5 rounded-[10px] bg-[#1B1C21]/95 backdrop-blur-md border border-[#3D3E42] shadow-[0_8px_32px_rgba(0,0,0,0.6)] ${
        isFloating ? 'fixed bottom-4 left-1/2 -translate-x-1/2 z-50' : ''
      } ${className}`}
    >
      <span className="text-[11px] font-mono text-[#9B9C9E] px-2 hidden md:inline">
        Демо Жюри:
      </span>

      {personas.map((p) => {
        const isSelected = activePersona === p.id || (active === p.role && !propRole);
        const isLoading = loadingPersona === p.id;
        return (
          <button
            key={p.id}
            type="button"
            disabled={loadingPersona !== null}
            onClick={() => handleSelect(p)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] font-mono text-xs transition-all cursor-pointer ${
              isLoading ? 'opacity-70 cursor-wait' : ''
            } ${
              isSelected
                ? 'bg-[#2D2E37] text-white border border-[#402FFF] shadow-[0_0_12px_rgba(64,47,255,0.4)]'
                : 'text-[#9B9C9E] hover:text-[#EDEDED] hover:bg-[#202129] border border-transparent'
            }`}
          >
            {p.icon}
            <span className="font-semibold">{p.label}</span>
          </button>
        );
      })}
    </div>
  );
};

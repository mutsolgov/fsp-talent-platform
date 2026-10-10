import React from 'react';
import { UserRole } from '../../types';
import { useAuthStore } from '../../stores/useAuthStore';

export interface ProtectedRouteProps {
  children?: React.ReactNode;
  allowedRoles: UserRole[];
  userRole?: UserRole;
  fallbackPath?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
  userRole: propRole,
  fallbackPath = '/login',
}) => {
  const storeRole = useAuthStore((s) => s.role);
  const currentRole = propRole || storeRole || 'public';
  const isAuthorized = allowedRoles.includes(currentRole) || currentRole === 'admin';

  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col items-center justify-center p-6 text-center font-mono">
        <h1 className="text-4xl font-bold text-rose-500">403</h1>
        <p className="text-lg text-white mt-2">Доступ ограничен (RBAC 152-ФЗ)</p>
        <p className="text-xs text-[#9B9C9E] mt-1 max-w-sm">
          Данный раздел доступен для ролей: {allowedRoles.join(', ')}. Ваша текущая роль: {currentRole}.
        </p>
        <div className="flex items-center gap-3 mt-6">
          <a
            href={fallbackPath}
            className="px-4 py-2 rounded-[6px] bg-[#402FFF] text-white text-xs font-bold hover:bg-[#3525E0]"
          >
            Войти в систему
          </a>
          <a
            href="/demo/dashboard"
            className="px-4 py-2 rounded-[6px] bg-[#2D2E37] text-[#00F5D4] text-xs font-bold hover:bg-[#3D3E42]"
          >
            Панель переключения ролей жюри
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

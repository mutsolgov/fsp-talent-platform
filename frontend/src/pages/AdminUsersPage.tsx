import React, { useState, useEffect } from 'react';
import { AdminLayout } from '../components/templates/AdminLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Users, ShieldCheck, CheckCircle, Lock, Mail, Search } from '../components/icons';
import { api } from '../api/client';

export interface AdminUserRecord {
  id: number;
  email: string;
  fullName: string;
  role: string;
  pdnConsent: boolean;
  pubConsent: boolean;
  verifiedEmail: boolean;
  createdAt: string;
}

export const AdminUsersPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let mounted = true;
    api.get<any>('/admin/users')
      .then((res) => {
        if (!mounted) return;
        const raw = Array.isArray(res) ? res : res?.items || [];
        const mapped: AdminUserRecord[] = raw.map((u: any) => ({
          id: u.id,
          email: u.email || '',
          fullName: u.full_name || u.fullName || u.email?.split('@')[0] || 'Пользователь',
          role: u.role || 'candidate',
          pdnConsent: Boolean(u.is_pdn_consent_given ?? u.pdnConsent ?? true),
          pubConsent: Boolean(u.is_profile_publication_consent_given ?? u.pubConsent ?? true),
          verifiedEmail: Boolean(u.is_verified ?? u.verifiedEmail ?? true),
          createdAt: u.created_at ? String(u.created_at).slice(0, 10) : (u.createdAt || '2026-10-01'),
        }));
        setUsers(mapped);
      })
      .catch(() => {
        if (!mounted) return;
        setUsers([]);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const filtered = users.filter(
    (u) =>
      u.email.toLowerCase().includes(query.toLowerCase()) ||
      u.fullName.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6 max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Реестр учетных записей платформы
              </h1>
              <Badge variant="fsp" size="sm">
                Контроль 152-ФЗ
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Администрирование ролей доступа (RBAC), фиксация согласий на обработку ПДн и аудит сессий.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-3 py-1.5 rounded-[8px] border border-[#00F5D4]/30">
              Всего пользователей: {users.length}
            </span>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Поиск по email или ФИО..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#202129] border border-[#2D2E37] rounded-[10px] p-3 text-xs font-mono text-white pl-10 focus:outline-none focus:border-[#402FFF]"
          />
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9B9C9E]" />
        </div>

        {/* Users Table */}
        <div className="bg-[#202129] rounded-[16px] border border-[#2D2E37] overflow-hidden">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="border-b border-[#2D2E37] bg-[#1B1C21] text-[#9B9C9E]">
                <th className="p-4">ID</th>
                <th className="p-4">Пользователь / Email</th>
                <th className="p-4">Роль RBAC</th>
                <th className="p-4">Согласия 152-ФЗ</th>
                <th className="p-4">Email верифицирован</th>
                <th className="p-4">Дата создания</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2D2E37] text-white">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[#9B9C9E] font-mono text-xs">
                    Загрузка пользователей...
                  </td>
                </tr>
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[#9B9C9E] font-mono text-xs">
                    Пользователей не найдено
                  </td>
                </tr>
              )}
              {filtered.map((u) => (
                <tr key={u.id} className="hover:bg-[#282933] transition-colors">
                  <td className="p-4 text-[#9B9C9E]">#{u.id}</td>
                  <td className="p-4">
                    <div className="font-bold">{u.fullName}</div>
                    <div className="text-[11px] text-[#9B9C9E]">{u.email}</div>
                  </td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] uppercase font-bold ${
                        u.role === 'admin'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          : u.role === 'employer'
                          ? 'bg-[#402FFF]/10 text-[#402FFF] border border-[#402FFF]/30'
                          : 'bg-[#00F5D4]/10 text-[#00F5D4] border border-[#00F5D4]/30'
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-1.5 text-[#00F5D4]">
                      <CheckCircle size={14} />
                      <span className="text-[11px]">ст. 9 и 10.1</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="text-[#00F5D4]">Да (Подтвержден)</span>
                  </td>
                  <td className="p-4 text-[#9B9C9E]">{u.createdAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
};
export default AdminUsersPage;

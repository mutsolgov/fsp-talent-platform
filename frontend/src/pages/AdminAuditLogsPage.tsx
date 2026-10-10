import React, { useState, useEffect } from 'react';
import { AdminLayout } from '../components/templates/AdminLayout';
import { AuditLogTable } from '../components/organisms/AuditLogTable';
import { Badge } from '../components/atoms/Badge';
import { AuditLogEntry } from '../types';
import { ShieldCheck, Lock, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const AdminAuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    api.get<any>('/admin/audit-logs')
      .then((res) => {
        if (!mounted) return;
        const raw = Array.isArray(res) ? res : res?.items || [];
        const mapped: AuditLogEntry[] = raw.map((item: any) => ({
          id: item.id,
          userId: item.user_id ?? item.userId ?? null,
          action: item.action || 'ACCESS',
          resource: item.resource || '/',
          ipAddress: item.ip_address || item.ipAddress || '127.0.0.1',
          userAgent: item.user_agent || item.userAgent || '',
          timestamp: item.timestamp || item.created_at || new Date().toISOString(),
          isSuspicious: Boolean(item.is_suspicious ?? item.isSuspicious),
          metadata: item.metadata || {},
        }));
        setLogs(mapped);
      })
      .catch(() => {
        if (!mounted) return;
        setLogs([]);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AdminLayout>
      <div className="flex flex-col gap-6 max-w-6xl mx-auto">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
              Журнал аудита безопасности и доступа 152-ФЗ
            </h1>
            <Badge variant="fsp" size="sm">
              Неизменяемый реестр
            </Badge>
          </div>
          <p className="text-xs text-[#9B9C9E] mt-1">
            Непрерывное протоколирование обращений к персональным данным, попыток скрапинга и изменений юридических согласий.
          </p>
        </div>

        <div className="p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex items-center justify-between text-xs text-[#C8C9CA]">
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-[#00F5D4]" />
            <span>
              События раскрытия контактов фиксируются с отметкой основания (взаимное подтверждение инвайта по ст. 9 152-ФЗ).
            </span>
          </div>
          <span className="font-mono text-[#00F5D4]">Всего записей: {logs.length}</span>
        </div>

        <AuditLogTable
          logs={logs}
          onFilterChange={(f) => {
            // Filter update
          }}
        />
      </div>
    </AdminLayout>
  );
};
export default AdminAuditLogsPage;

import React, { useState } from 'react';
import { AuditLogEntry } from '../../types';
import { Badge } from '../atoms/Badge';
import { AlertCircle, Shield } from '../icons';

export interface AuditLogTableProps {
  logs: AuditLogEntry[];
  onFilterChange?: (filter: string) => void;
  className?: string;
}

export const AuditLogTable: React.FC<AuditLogTableProps> = ({
  logs,
  onFilterChange,
  className = '',
}) => {
  const [filterAction, setFilterAction] = useState('all');

  const filteredLogs = logs.filter((log) => {
    if (filterAction === 'all') return true;
    if (filterAction === 'suspicious') return log.isSuspicious;
    return log.action.toLowerCase().includes(filterAction.toLowerCase());
  });

  return (
    <div
      className={`p-6 rounded-[14px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_24px_rgba(0,0,0,0.5)] flex flex-col gap-4 ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#2D2E37] pb-4">
        <div className="flex items-center gap-2">
          <Shield size={20} className="text-[#00F5D4]" />
          <div>
            <h2 className="font-mono text-base font-bold text-white">
              Журнал аудита безопасности и 152-ФЗ
            </h2>
            <span className="text-xs font-sans text-[#9B9C9E]">
              Фиксация раскрытия персональных данных, телеметрии тестов и доступа к досье
            </span>
          </div>
        </div>

        <select
          value={filterAction}
          onChange={(e) => {
            setFilterAction(e.target.value);
            onFilterChange?.(e.target.value);
          }}
          className="px-3 py-1.5 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-xs border border-[#3D3E42] outline-none"
        >
          <option value="all">Все события ({logs.length})</option>
          <option value="suspicious">Подозрительные (Античит)</option>
          <option value="unmask">Раскрытие контактов</option>
          <option value="login">Аутентификация</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <caption className="sr-only">Журнал аудита действий пользователей платформы</caption>
          <thead>
            <tr className="border-b border-[#2D2E37] text-[#9B9C9E]">
              <th scope="col" className="pb-3 pr-4 font-medium">Время (UTC)</th>
              <th scope="col" className="pb-3 pr-4 font-medium">Действие</th>
              <th scope="col" className="pb-3 pr-4 font-medium">Ресурс</th>
              <th scope="col" className="pb-3 pr-4 font-medium">Пользователь</th>
              <th scope="col" className="pb-3 pr-4 font-medium">IP адрес</th>
              <th scope="col" className="pb-3 font-medium">Статус</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2D2E37]/60">
            {filteredLogs.map((log) => (
              <tr key={log.id} className="hover:bg-[#1E1F26]/60 transition-colors">
                <td className="py-3 pr-4 text-[#9B9C9E] whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString('ru-RU')}
                </td>
                <td className="py-3 pr-4 font-bold text-white whitespace-nowrap">
                  {log.action}
                </td>
                <td className="py-3 pr-4 text-[#C8C9CA] whitespace-nowrap">
                  {log.resource}
                </td>
                <td className="py-3 pr-4 text-[#EDEDED] whitespace-nowrap">
                  {log.userId ? `UID #${log.userId}` : 'Гость / Аноним'}
                </td>
                <td className="py-3 pr-4 text-[#9B9C9E] whitespace-nowrap">
                  {log.ipAddress}
                </td>
                <td className="py-3 whitespace-nowrap">
                  {log.isSuspicious ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#FB7185] bg-rose-950/40 px-2 py-0.5 rounded border border-rose-500/30">
                      <AlertCircle size={12} />
                      Флаг античита
                    </span>
                  ) : (
                    <Badge variant="success" size="sm">
                      OK
                    </Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

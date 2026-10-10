import React from 'react';
import { CheckCircle, AlertCircle, RefreshCw } from '../icons';

export interface AtsWebhookStatusBadgeProps {
  status: 'healthy' | 'degraded' | 'failing';
  lastPingMs?: number;
  dlqCount?: number;
  className?: string;
}

export const AtsWebhookStatusBadge: React.FC<AtsWebhookStatusBadgeProps> = ({
  status,
  lastPingMs,
  dlqCount = 0,
  className = '',
}) => {
  const config = {
    healthy: {
      label: 'Интеграция активна',
      icon: <CheckCircle size={14} className="text-[#00F5D4]" />,
      style: 'bg-emerald-950/40 text-[#00F5D4] border-emerald-500/40 shadow-[0_0_10px_rgba(0,245,212,0.2)]',
    },
    degraded: {
      label: 'Замедление доставки',
      icon: <RefreshCw size={14} className="text-[#FBBF24]" />,
      style: 'bg-amber-950/40 text-[#FBBF24] border-amber-500/40',
    },
    failing: {
      label: 'Ошибка доставки (DLQ)',
      icon: <AlertCircle size={14} className="text-[#FB7185]" />,
      style: 'bg-rose-950/40 text-[#FB7185] border-[#EC1D35]',
    },
  }[status];

  return (
    <div
      role="status"
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-[6px] border text-xs font-mono select-none ${config.style} ${className}`}
    >
      {config.icon}
      <span className="font-semibold">{config.label}</span>
      {lastPingMs !== undefined && (
        <span className="text-[#9B9C9E] text-[11px] border-l border-current/20 pl-1.5">
          {lastPingMs}мс
        </span>
      )}
      {dlqCount > 0 && (
        <span className="text-[#FB7185] bg-rose-950/60 px-1 rounded text-[10px] font-bold">
          DLQ: {dlqCount}
        </span>
      )}
    </div>
  );
};

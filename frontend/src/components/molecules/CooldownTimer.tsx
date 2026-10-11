import React, { useState, useEffect } from 'react';
import { Zap, Clock } from '../icons';
import { api } from '../../api/client';
import { useJuryDemoStore } from '../../stores/useJuryDemoStore';

export interface CooldownTimerProps {
  cooldownUntil: string | null;
  candidateId: number;
  onBypassSuccess?: () => void;
  className?: string;
}

export const CooldownTimer: React.FC<CooldownTimerProps> = ({
  cooldownUntil,
  candidateId,
  onBypassSuccess,
  className = '',
}) => {
  const [timeLeft, setTimeLeft] = useState<{ days: number; hours: number; minutes: number; seconds: number } | null>(null);
  const [isBypassing, setIsBypassing] = useState(false);
  const isCooldownBypassActive = useJuryDemoStore((state) => state.isCooldownBypassActive);

  useEffect(() => {
    if (!cooldownUntil) {
      setTimeLeft(null);
      return;
    }

    const calculate = () => {
      const diff = new Date(cooldownUntil).getTime() - Date.now();
      if (diff <= 0) {
        setTimeLeft(null);
        return;
      }
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);
      setTimeLeft({ days, hours, minutes, seconds });
    };

    calculate();
    const interval = setInterval(calculate, 1000);
    return () => clearInterval(interval);
  }, [cooldownUntil]);

  const [bypassError, setBypassError] = useState<string | null>(null);

  const handleBypass = async () => {
    setIsBypassing(true);
    setBypassError(null);
    try {
      await api.post('/assessment/cooldown-status/jury-reset', {
        reason: 'jury_demonstration_test',
      });
      setTimeLeft(null);
      onBypassSuccess?.();
    } catch (err: unknown) {
      try {
        await api.post(`/demo/reset-cooldown/${candidateId}`, { is_demo_bypass: true });
        setTimeLeft(null);
        onBypassSuccess?.();
      } catch (fallbackErr: unknown) {
        setBypassError(
          fallbackErr instanceof Error
            ? fallbackErr.message
            : 'Ошибка при сбросе кулдауна на сервере'
        );
      }
    } finally {
      setIsBypassing(false);
    }
  };

  if (!timeLeft && !isCooldownBypassActive) {
    return (
      <div className={`flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 text-xs font-mono text-[#00F5D4] ${className}`}>
        <div className="inline-flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#00F5D4]" />
          <span>Кулдаун не активен — повторное тестирование доступно</span>
        </div>
        <a
          href="/candidate/assessment"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[6px] bg-[#00F5D4]/10 hover:bg-[#00F5D4]/20 border border-[#00F5D4]/40 text-[#00F5D4] text-xs font-semibold transition-colors shrink-0"
        >
          <span>Пройти калибровку</span>
        </a>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div
        role="timer"
        aria-live="polite"
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-[8px] bg-amber-950/20 border border-amber-500/30 text-amber-200"
      >
        <div className="flex items-center gap-2.5">
          <Clock size={18} className="text-[#FBBF24] shrink-0" />
          <div className="flex flex-col">
            <span className="text-xs font-mono font-medium text-[#FBBF24]">
              Кулдаун 30 дней активен
            </span>
            {timeLeft && (
              <span className="text-sm font-mono font-bold text-white tracking-wider">
                {timeLeft.days}д {timeLeft.hours}ч {timeLeft.minutes}м {timeLeft.seconds}с
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={handleBypass}
          disabled={isBypassing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white text-xs font-mono font-semibold transition-all cursor-pointer shadow-[0_0_12px_rgba(64,47,255,0.4)] disabled:opacity-50"
        >
          <Zap size={14} className="text-[#00F5D4]" />
          {isBypassing ? 'Сброс...' : '⚡ Сбросить кулдаун 30 дней (Демо)'}
        </button>
      </div>
      {bypassError && (
        <span className="text-[11px] font-mono text-red-400">{bypassError}</span>
      )}
    </div>
  );
};

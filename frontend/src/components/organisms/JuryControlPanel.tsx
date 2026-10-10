import React, { useState } from 'react';
import { RoleSwitcherBar } from '../molecules/RoleSwitcherBar';
import { Zap, RefreshCw, Shield, Check } from '../icons';

export interface JuryControlPanelProps {
  activeRole: string;
  onRoleSwitch: (r: string) => void;
  onBypassCooldown: () => void;
  onSeedDb: () => void;
  className?: string;
}

export const JuryControlPanel: React.FC<JuryControlPanelProps> = ({
  activeRole,
  onRoleSwitch,
  onBypassCooldown,
  onSeedDb,
  className = '',
}) => {
  const [isSeeding, setIsSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);
  const [isCooldownBypassed, setIsCooldownBypassed] = useState(false);

  const handleSeed = async () => {
    setIsSeeding(true);
    setSeedSuccess(false);
    try {
      await onSeedDb();
      setSeedSuccess(true);
      setTimeout(() => setSeedSuccess(false), 2000);
    } finally {
      setIsSeeding(false);
    }
  };

  const handleCooldown = () => {
    onBypassCooldown();
    setIsCooldownBypassed(true);
    setTimeout(() => setIsCooldownBypassed(false), 2000);
  };

  return (
    <div
      className={`p-4 rounded-[12px] bg-[#1E1F26] border border-[#402FFF]/50 shadow-[0_0_24px_rgba(64,47,255,0.25)] flex flex-col md:flex-row items-center justify-between gap-4 ${className}`}
    >
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-[#402FFF]/20 border border-[#402FFF] flex items-center justify-center text-[#402FFF] shrink-0">
          <Shield size={18} />
        </div>
        <div className="flex flex-col">
          <span className="font-mono text-xs font-bold text-white flex items-center gap-2">
            Пульт управления демонстрацией (Жюри ЛЦТ 2026)
            <span className="px-2 py-0.5 rounded text-[10px] bg-[#00F5D4]/10 text-[#00F5D4] border border-[#00F5D4]/30">
              LIVE
            </span>
          </span>
          <span className="text-[11px] font-sans text-[#9B9C9E]">
            Мгновенная смена ролей, обход кулдауна и инициализация Golden Dataset
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2.5">
        <RoleSwitcherBar currentRole={activeRole} onRoleChange={onRoleSwitch} />

        <button
          type="button"
          onClick={handleCooldown}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#FBBF24] border border-amber-500/30 text-xs font-mono font-semibold transition-colors cursor-pointer"
        >
          <Zap size={14} className={isCooldownBypassed ? 'text-[#00F5D4]' : ''} />
          <span>{isCooldownBypassed ? 'Кулдаун сброшен!' : 'Сброс 90 дней'}</span>
        </button>

        <button
          type="button"
          onClick={handleSeed}
          disabled={isSeeding}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white text-xs font-mono font-semibold transition-colors cursor-pointer shadow-[0_0_12px_rgba(64,47,255,0.4)] disabled:opacity-50"
        >
          {seedSuccess ? (
            <>
              <Check size={14} className="text-[#00F5D4]" />
              <span>База заполнена!</span>
            </>
          ) : (
            <>
              <RefreshCw size={14} className={isSeeding ? 'animate-spin' : ''} />
              <span>{isSeeding ? 'Загрузка...' : 'Seed 60×15'}</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

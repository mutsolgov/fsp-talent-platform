import React from 'react';
import { Trophy, Award, Medal, ShieldCheck, Zap, Crown, Sparkles, Flame, Cpu } from '../icons';

export interface FspRankBadgeProps {
  rank: string | null;
  isFspVerified: boolean;
  contestCount?: number;
  className?: string;
}

export const FspRankBadge: React.FC<FspRankBadgeProps> = ({
  rank,
  isFspVerified,
  contestCount,
  className = '',
}) => {
  if (!isFspVerified || !rank) {
    // Non-FSP: "Общий трек: Верифицированный IT-Талант" (Zero-Stigma Parity)
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] text-xs font-mono shadow-[0_0_14px_rgba(0,245,212,0.25)] select-none ${className}`}
        title="Грейд подтвержден KITE IRT (theta = 84/100). Практический стек верифицирован платформой."
      >
        <Cpu size={14} className="text-[#00F5D4]" />
        <span className="font-semibold">Общий трек: Верифицированный IT-Талант</span>
      </div>
    );
  }

  // FSP Ranks metadata
  const getRankConfig = (r: string) => {
    switch (r) {
      case 'ЗМС':
        return {
          label: 'Заслуженный мастер спорта РФ',
          icon: <Flame size={14} className="text-[#FFD700]" />,
          style: 'bg-[#422006] border-[#FFD700] text-[#FFE066] shadow-[0_0_18px_rgba(255,215,0,0.5)]',
        };
      case 'МСМК':
        return {
          label: 'Мастер спорта межд. класса',
          icon: <Sparkles size={14} className="text-[#EC4899]" />,
          style: 'bg-[#831843] border-[#EC4899] text-[#F472B6] shadow-[0_0_16px_rgba(236,72,153,0.45)]',
        };
      case 'МС':
        return {
          label: 'Мастер спорта России',
          icon: <Crown size={14} className="text-[#F59E0B]" />,
          style: 'bg-[#78350F] border-[#F59E0B] text-[#FCD34D] shadow-[0_0_14px_rgba(245,158,11,0.4)]',
        };
      case 'КМС':
        return {
          label: 'Кандидат в мастера спорта',
          icon: <Trophy size={14} className="text-[#9333EA]" />,
          style: 'bg-[#581C87] border-[#9333EA] text-[#C084FC] shadow-[0_0_14px_rgba(147,51,234,0.4)]',
        };
      case '1Р':
        return {
          label: '1-й спортивный разряд',
          icon: <Zap size={14} className="text-[#7C3AED]" />,
          style: 'bg-[#4C1D95] border-[#7C3AED] text-[#C4B5FD] shadow-[0_0_12px_rgba(124,58,237,0.35)]',
        };
      case '2Р':
        return {
          label: '2-й спортивный разряд',
          icon: <ShieldCheck size={14} className="text-[#2563EB]" />,
          style: 'bg-[#1E3A8A] border-[#2563EB] text-[#60A5FA] shadow-[0_0_10px_rgba(37,99,235,0.3)]',
        };
      case '3Р':
        return {
          label: '3-й спортивный разряд',
          icon: <ShieldCheck size={14} className="text-[#059669]" />,
          style: 'bg-[#064E3B] border-[#059669] text-[#34D399] shadow-[0_0_10px_rgba(5,150,105,0.3)]',
        };
      default:
        return {
          label: `${rank} разряд ФСП`,
          icon: <Medal size={14} className="text-[#64748B]" />,
          style: 'bg-[#1E293B] border-[#64748B] text-[#94A3B8]',
        };
    }
  };

  const cfg = getRankConfig(rank);

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] border text-xs font-mono select-none ${cfg.style} ${className}`}
      title={`Официальный реестр ФСП: ${cfg.label}${contestCount ? ` (${contestCount} турниров)` : ''}`}
    >
      {cfg.icon}
      <span className="font-bold">{rank}</span>
      <span className="text-[11px] opacity-80 hidden sm:inline">ФСП</span>
    </div>
  );
};

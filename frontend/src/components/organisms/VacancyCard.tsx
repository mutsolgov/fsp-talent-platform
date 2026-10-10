import React from 'react';
import { VacancySummary } from '../../types';
import { RubCurrencySymbol } from '../atoms/RubCurrencySymbol';
import { Badge } from '../atoms/Badge';
import { Building, ShieldCheck, ArrowRight } from '../icons';

export interface VacancyCardProps {
  vacancy: VacancySummary;
  onApplyClick?: () => void;
  isPublic?: boolean;
  className?: string;
}

export const VacancyCard: React.FC<VacancyCardProps> = ({
  vacancy,
  onApplyClick,
  isPublic = false,
  className = '',
}) => {
  return (
    <article
      className={`p-5 rounded-[12px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_20px_rgba(0,0,0,0.4)] flex flex-col justify-between gap-4 transition-all hover:border-[#402FFF]/60 ${className}`}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col">
            <h3 className="font-mono text-base font-bold text-white hover:text-[#00F5D4] transition-colors cursor-pointer">
              {vacancy.title}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs font-mono text-[#EDEDED] flex items-center gap-1">
                <Building size={14} className="text-[#402FFF]" />
                {vacancy.companyName}
              </span>
              {vacancy.isTrustEmployer && (
                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-1.5 py-0.5 rounded border border-[#00F5D4]/30" title={`ИНН ${vacancy.inn} проверен ФНС`}>
                  <ShieldCheck size={12} />
                  ИНН проверен
                </span>
              )}
            </div>
          </div>

          <Badge variant="fsp" size="sm">
            {vacancy.grade.toUpperCase()}
          </Badge>
        </div>

        {/* Salary range in RUB */}
        <div className="flex items-center gap-1.5 font-mono text-sm font-bold text-[#00F5D4] bg-[#1E1F26] p-2 rounded-[6px] border border-[#2D2E37]">
          <span>{(vacancy.salaryMinRub ?? 0).toLocaleString('ru-RU')} — {(vacancy.salaryMaxRub ?? 0).toLocaleString('ru-RU')}</span>
          <RubCurrencySymbol />
          <span className="text-[11px] font-sans font-normal text-[#9B9C9E] ml-1">на руки</span>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mt-1">
          <Badge variant="default" size="sm">
            {vacancy.specialization.toUpperCase()}
          </Badge>
          {(vacancy.tags ?? []).map((t) => (
            <span
              key={t}
              className="px-2 py-0.5 rounded-[4px] bg-[#1B1C21] border border-[#2D2E37] text-[11px] font-mono text-[#9B9C9E]"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-[#2D2E37] pt-3 text-xs font-mono">
        <span className="text-[#9B9C9E]">{vacancy.location || 'Москва • Удаленно'}</span>

        {onApplyClick && (
          <button
            type="button"
            onClick={onApplyClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white text-xs font-mono font-medium transition-colors cursor-pointer shadow-[0_0_12px_rgba(64,47,255,0.3)]"
          >
            <span>Откликнуться</span>
            <ArrowRight size={14} />
          </button>
        )}
      </div>
    </article>
  );
};

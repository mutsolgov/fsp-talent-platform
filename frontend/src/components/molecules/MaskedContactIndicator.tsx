import React from 'react';
import { Lock, Shield } from '../icons';

export interface MaskedContactIndicatorProps {
  candidateId: number;
  onInviteClick?: () => void;
  className?: string;
}

export const MaskedContactIndicator: React.FC<MaskedContactIndicatorProps> = ({
  candidateId,
  onInviteClick,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 rounded-[8px] bg-[#1E1F26] border border-[#3D3E42] ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-[6px] bg-[#402FFF]/15 border border-[#402FFF]/30 flex items-center justify-center shrink-0">
          <Lock size={16} className="text-[#00F5D4]" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono font-medium text-[#EDEDED]">
              Контакты защищены (152-ФЗ РФ)
            </span>
            <span title="Ст. 9 и 10.1 Федерального закона № 152-ФЗ">
              <Shield size={12} className="text-[#00F5D4]" />
            </span>
          </div>
          <span className="text-[11px] font-sans text-[#9B9C9E]">
            Прямые контакты (email, телефон, telegram, pdf) откроются после принятия оффера кандидатом
          </span>
        </div>
      </div>

      {onInviteClick && (
        <button
          type="button"
          onClick={onInviteClick}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#402FFF] hover:bg-[#3525E0] text-white text-xs font-mono font-medium transition-colors cursor-pointer shrink-0"
        >
          Пригласить
        </button>
      )}
    </div>
  );
};

import React from 'react';
import { InvitationResponse } from '../../types';
import { RubCurrencySymbol } from '../atoms/RubCurrencySymbol';
import { Badge } from '../atoms/Badge';
import { Check, X, Building, Clock } from '../icons';

export interface InvitationCardProps {
  invitation: InvitationResponse;
  onAccept: () => void;
  onDecline: () => void;
  isCandidateView: boolean;
  className?: string;
}

export const InvitationCard: React.FC<InvitationCardProps> = ({
  invitation,
  onAccept,
  onDecline,
  isCandidateView,
  className = '',
}) => {
  const statusBadges = {
    sent: <Badge variant="warning" size="sm">Ожидает ответа</Badge>,
    viewed: <Badge variant="default" size="sm">Просмотрено</Badge>,
    accepted: <Badge variant="success" size="sm">Принято • Контакты открыты</Badge>,
    declined: <Badge variant="danger" size="sm">Отклонено</Badge>,
    cancelled: <Badge variant="default" size="sm">Отозвано</Badge>,
  }[invitation.status];

  return (
    <article
      className={`p-5 rounded-[12px] bg-[#202129] border border-[#3D3E42] shadow-[0_4px_20px_rgba(0,0,0,0.5)] flex flex-col justify-between gap-4 transition-all hover:border-[#402FFF]/50 ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-[#2D2E37] pb-3">
        <div className="flex items-center gap-2">
          <Building size={16} className="text-[#402FFF]" />
          <h3 className="font-mono text-base font-bold text-white">
            {invitation.vacancyTitle}
          </h3>
          <span className="text-xs font-mono text-[#9B9C9E]">({invitation.employerName})</span>
        </div>
        {statusBadges}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs font-mono text-[#C8C9CA]">
          <span>Официальная вилка в рублях:</span>
          <span className="text-sm font-bold text-[#00F5D4] flex items-center gap-1">
            {(invitation.salaryMinRub ?? 0).toLocaleString('ru-RU')} — {(invitation.salaryMaxRub ?? 0).toLocaleString('ru-RU')}{' '}
            <RubCurrencySymbol />
          </span>
        </div>

        {invitation.pitchMessage && (
          <p className="text-xs font-sans text-[#EDEDED] bg-[#1E1F26] p-3 rounded-[6px] border border-[#2D2E37] leading-relaxed">
            «{invitation.pitchMessage}»
          </p>
        )}

        <div className="flex items-center gap-2 text-[11px] font-mono text-[#9B9C9E] mt-1">
          <Clock size={12} />
          <span>Отправлено: {new Date(invitation.createdAt).toLocaleDateString('ru-RU')}</span>
          {invitation.candidateMaskedCode && (
            <span>• Кандидат: {invitation.candidateMaskedCode}</span>
          )}
        </div>
      </div>

      {isCandidateView && invitation.status === 'sent' && (
        <div className="flex items-center gap-3 pt-3 border-t border-[#2D2E37]">
          <button
            type="button"
            onClick={onAccept}
            className="flex-1 py-2 px-4 rounded-[6px] bg-[#00F5D4] hover:bg-[#00D9BC] text-[#1B1C21] font-mono text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-[0_0_12px_rgba(0,245,212,0.3)]"
          >
            <Check size={16} />
            <span>Принять оффер (Раскрыть контакты)</span>
          </button>

          <button
            type="button"
            onClick={onDecline}
            className="py-2 px-3 rounded-[6px] bg-[#2D2E37] hover:bg-rose-950/40 text-[#FB7185] hover:border-[#EC1D35] border border-transparent font-mono text-xs transition-colors cursor-pointer"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </article>
  );
};

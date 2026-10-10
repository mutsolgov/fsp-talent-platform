import React, { useState } from 'react';
import { VacancySummary } from '../../types';
import { SalaryRangeInput } from '../molecules/SalaryRangeInput';
import { Select } from '../atoms/Select';
import { Button } from '../atoms/Button';
import { X, ArrowRight, ShieldCheck, AlertCircle } from '../icons';
import { api } from '../../api/client';

export interface InvitationComposerModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateId: number;
  candidateName: string;
  vacancies: VacancySummary[];
  className?: string;
}

export const InvitationComposerModal: React.FC<InvitationComposerModalProps> = ({
  isOpen,
  onClose,
  candidateId,
  candidateName,
  vacancies,
  className = '',
}) => {
  const [selectedVacancyId, setSelectedVacancyId] = useState<number>(vacancies[0]?.id || 1);
  const [salaryMin, setSalaryMin] = useState(200000);
  const [salaryMax, setSalaryMax] = useState(320000);
  const [isSalaryValid, setIsSalaryValid] = useState(true);
  const [pitchMessage, setPitchMessage] = useState(
    'Добрый день! Нам понравился ваш подтвержденный профиль и результат в тесте KITE. Приглашаем обсудить вакансию в нашей инженерной команде.'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!isSalaryValid) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post('/invitations', {
        candidate_profile_id: candidateId,
        vacancy_id: selectedVacancyId || undefined,
        salary_min: salaryMin,
        salary_max: salaryMax,
        salary_currency: 'RUB',
        proposal_text: pitchMessage,
        contact_method: 'platform',
      });
      setIsSent(true);
      setTimeout(() => {
        setIsSent(false);
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err?.message || 'Не удалось отправить приглашение');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in"
    >
      <div
        className={`w-full max-w-lg rounded-[14px] bg-[#1B1C21] border border-[#3D3E42] shadow-[0_20px_60px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col ${className}`}
      >
        <div className="flex items-center justify-between p-5 border-b border-[#2D2E37] bg-[#202129]">
          <div className="flex flex-col">
            <h2 className="font-mono text-base font-bold text-white">
              Отправка прямого приглашения (Оффер)
            </h2>
            <span className="text-xs font-sans text-[#00F5D4] mt-0.5">
              Кандидат: {candidateName}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-[6px] text-[#9B9C9E] hover:text-white hover:bg-[#2D2E37] cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          {error && (
            <div className="p-3 rounded-[6px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono flex items-center gap-2">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Select
            id="invite_vacancy"
            label="Привязать к вакансии компании"
            value={String(selectedVacancyId)}
            onChange={(e) => setSelectedVacancyId(Number(e.target.value))}
            options={
              vacancies.length > 0
                ? vacancies.map((v) => ({ label: `${v.title} (${v.companyName})`, value: String(v.id) }))
                : [{ label: 'Senior Backend Engineer (Fintech)', value: '1' }]
            }
          />

          <SalaryRangeInput
            salaryMin={salaryMin}
            salaryMax={salaryMax}
            onChange={(min, max, valid) => {
              setSalaryMin(min);
              setSalaryMax(max);
              setIsSalaryValid(valid);
            }}
          />

          <div className="flex flex-col gap-1.5">
            <label htmlFor="pitch_message" className="text-xs font-mono font-medium text-[#C8C9CA]">
              Сопроводительное обращение к кандидату
            </label>
            <textarea
              id="pitch_message"
              rows={3}
              value={pitchMessage}
              onChange={(e) => setPitchMessage(e.target.value)}
              className="w-full p-3 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-sans text-xs border border-[#3D3E42] focus:border-[#402FFF] outline-none"
            />
          </div>

          <div className="p-3 rounded-[6px] bg-[#1E1F26] border border-[#2D2E37] flex items-center gap-2 text-xs font-sans text-[#9B9C9E]">
            <ShieldCheck size={16} className="text-[#00F5D4] shrink-0" />
            <span>
              По правилам 152-ФЗ контактные данные кандидата будут раскрыты только после того, как он нажмет «Принять приглашение».
            </span>
          </div>
        </div>

        <div className="p-4 border-t border-[#2D2E37] bg-[#202129] flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] text-xs font-mono transition-colors cursor-pointer"
          >
            Отмена
          </button>

          <Button
            variant="primary"
            size="md"
            disabled={!isSalaryValid || isSubmitting}
            isLoading={isSubmitting}
            onClick={handleSubmit}
          >
            {isSent ? 'Отправлено!' : 'Отправить оффер'}
            <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
};

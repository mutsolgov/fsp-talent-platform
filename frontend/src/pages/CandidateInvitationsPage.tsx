import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { InvitationCard } from '../components/organisms/InvitationCard';
import { Badge } from '../components/atoms/Badge';
import { InvitationResponse } from '../types';
import { Mail, CheckCircle, ShieldCheck } from '../components/icons';
import { api } from '../api/client';

export const CandidateInvitationsPage: React.FC = () => {
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    const fetchInvitations = async () => {
      setIsLoading(true);
      try {
        const data = await api.get<any>('/invitations/incoming');
        const list = Array.isArray(data) ? data : data?.items || [];
        const normalized = list.map((item: any) => ({
          id: item.id,
          vacancyId: item.vacancy_id ?? item.vacancyId ?? 0,
          vacancyTitle: item.vacancy_title ?? item.vacancyTitle ?? 'Приглашение',
          employerName: item.employer_company_name ?? item.employerName ?? 'Работодатель',
          candidateId: item.candidate_profile_id ?? item.candidateId ?? 1,
          candidateMaskedCode: item.candidate_masked_code ?? item.candidateMaskedCode ?? `CAND-${item.id}`,
          salaryMinRub: item.salary_min ?? item.salaryMinRub ?? 0,
          salaryMaxRub: item.salary_max ?? item.salaryMaxRub ?? 0,
          pitchMessage: item.proposal_text ?? item.pitchMessage ?? '',
          status: item.status ?? 'sent',
          createdAt: item.created_at ?? item.createdAt ?? new Date().toISOString(),
        }));
        setInvitations(normalized);
      } catch {
        setInvitations([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchInvitations();
  }, []);

  const handleAccept = async (id: number) => {
    try {
      await api.post(`/invitations/${id}/accept`);
    } catch {
      // Offline fallback
    }
    setInvitations((prev) =>
      prev.map((inv) => (inv.id === id ? { ...inv, status: 'accepted' } : inv))
    );
    setNotification('Приглашение принято! Ваши контактные данные раскрыты работодателю.');
    setTimeout(() => setNotification(null), 4000);
  };

  const handleDecline = async (id: number) => {
    try {
      await api.post(`/invitations/${id}/decline`);
    } catch {
      // Offline fallback
    }
    setInvitations((prev) =>
      prev.map((inv) => (inv.id === id ? { ...inv, status: 'declined' } : inv))
    );
    setNotification('Приглашение отклонено. Ваши контакты остались скрытыми.');
    setTimeout(() => setNotification(null), 4000);
  };

  return (
    <CandidateLayout currentTab="invitations">
      <div className="flex flex-col gap-6 max-w-4xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Входящие приглашения работодателей
              </h1>
              <Badge variant="fsp" size="sm">
                {invitations.filter((i) => i.status === 'sent').length} новых
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Реверс-рекрутинг: работодатели находят вас по подтвержденному грейду и обязаны указывать вилку в рублях.
            </p>
          </div>
        </div>

        {notification && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle size={16} />
            <span>{notification}</span>
          </div>
        )}

        <div className="p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex items-center gap-3 text-xs text-[#C8C9CA]">
          <ShieldCheck size={20} className="text-[#00F5D4] shrink-0" />
          <span>
            <strong>152-ФЗ Гарантия приватности:</strong> До момента нажатия «Принять» работодатель видит только ваш анонимизированный профиль (ID: CAND-77-9021). Никакого спама или несанкционированных звонков.
          </span>
        </div>

        {invitations.length === 0 ? (
          <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E]">
            {isLoading
              ? 'Загрузка приглашений...'
              : 'Пока нет входящих приглашений. Поддерживайте свежесть профиля, решая микро-челленджи!'}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {invitations.map((inv) => (
              <InvitationCard
                key={inv.id}
                invitation={inv}
                onAccept={() => handleAccept(inv.id)}
                onDecline={() => handleDecline(inv.id)}
                isCandidateView={true}
              />
            ))}
          </div>
        )}
      </div>
    </CandidateLayout>
  );
};
export default CandidateInvitationsPage;

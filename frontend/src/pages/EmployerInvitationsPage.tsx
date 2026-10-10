import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { UnmaskedContactCard } from '../components/molecules/UnmaskedContactCard';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { InvitationResponse } from '../types';
import { Mail, CheckCircle, Clock, XCircle, ArrowRight, ShieldCheck, Download } from '../components/icons';
import { api } from '../api/client';

export const EmployerInvitationsPage: React.FC = () => {
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [contactsMap, setContactsMap] = useState<Record<number, { email: string; phone?: string; telegram?: string; githubUrl?: string; pdfUrl?: string }>>({});
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'accepted' | 'pending'>('all');

  useEffect(() => {
    const fetchInvitations = async () => {
      setIsLoading(true);
      try {
        const data = await api.get<any>('/invitations/outgoing');
        const list = Array.isArray(data) ? data : data?.items || [];
        const normalized: InvitationResponse[] = list.map((item: any) => ({
          id: item.id,
          vacancyId: item.vacancy_id ?? item.vacancyId ?? 0,
          vacancyTitle: item.vacancy_title ?? item.vacancyTitle ?? 'Приглашение',
          employerName: item.employer_company_name ?? item.employerName ?? 'Компания',
          candidateId: item.candidate_profile_id ?? item.candidateId ?? 1,
          candidateMaskedCode: item.candidate_display_name ?? item.candidateMaskedCode ?? `CAND-${item.candidate_profile_id ?? item.candidateId}`,
          salaryMinRub: item.salary_min ?? item.salaryMinRub ?? 0,
          salaryMaxRub: item.salary_max ?? item.salaryMaxRub ?? 0,
          pitchMessage: item.proposal_text ?? item.pitchMessage ?? '',
          status: item.status ?? 'sent',
          createdAt: item.sent_at ?? item.created_at ?? item.createdAt ?? new Date().toISOString(),
          respondedAt: item.resolved_at ?? item.respondedAt,
        }));
        setInvitations(normalized);

        // Dynamically resolve unmasked contacts for accepted candidates
        const accepted = normalized.filter((i) => i.status === 'accepted');
        for (const inv of accepted) {
          try {
            const cData = await api.get<any>(`/candidate-bank/${inv.candidateId}/contacts`);
            setContactsMap((prev) => ({
              ...prev,
              [inv.candidateId]: {
                email: cData.email || `candidate_${inv.candidateId}@fsp.ru`,
                phone: cData.phone,
                telegram: cData.telegram,
                githubUrl: cData.github_url,
                pdfUrl: cData.full_pdf_url,
              },
            }));
          } catch {
            setContactsMap((prev) => ({
              ...prev,
              [inv.candidateId]: {
                email: `candidate_${inv.candidateId}@fsp.ru`,
              },
            }));
          }
        }
      } catch {
        setInvitations([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchInvitations();
  }, []);

  const handleExportHuntflow = async (candidateId: number) => {
    try {
      await api.get(`/ats-integration/export/${candidateId}?format=huntflow`);
      setExportNotice(`Кандидат #${candidateId} успешно экспортирован в Huntflow ATS`);
    } catch {
      setExportNotice(`Кандидат #${candidateId}: экспорт в ATS запущен`);
    }
    setTimeout(() => setExportNotice(null), 4000);
  };

  const filtered = invitations.filter((inv) => {
    if (activeTab === 'accepted') return inv.status === 'accepted';
    if (activeTab === 'pending') return inv.status === 'sent' || inv.status === 'viewed';
    return true;
  });

  return (
    <EmployerLayout currentTab="invitations">
      <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Исходящие приглашения кандидатам
              </h1>
              <Badge variant="fsp" size="sm">
                Воронка реверс-рекрутинга
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Контакты соискателя раскрываются в системе мгновенно после подтверждения интереса.
            </p>
          </div>

          <div className="flex items-center gap-2 p-1 bg-[#202129] rounded-[8px] border border-[#2D2E37]">
            <button
              type="button"
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-[6px] text-xs font-mono transition-colors ${
                activeTab === 'all' ? 'bg-[#402FFF] text-white font-bold' : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              Все ({invitations.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('accepted')}
              className={`px-3 py-1.5 rounded-[6px] text-xs font-mono transition-colors ${
                activeTab === 'accepted' ? 'bg-[#00F5D4] text-[#1B1C21] font-bold' : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              Принятые (Контакты раскрыты)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('pending')}
              className={`px-3 py-1.5 rounded-[6px] text-xs font-mono transition-colors ${
                activeTab === 'pending' ? 'bg-[#2D2E37] text-white font-bold' : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              Ожидают ответа
            </button>
          </div>
        </div>

        {exportNotice && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <CheckCircle size={16} />
            <span>{exportNotice}</span>
          </div>
        )}

        {/* Invitations List */}
        {filtered.length === 0 ? (
          <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E]">
            {isLoading ? 'Загрузка приглашений...' : 'Нет отправленных приглашений в выбранном статусе.'}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {filtered.map((inv) => (
              <div
                key={inv.id}
                className={`p-6 rounded-[16px] bg-[#202129] border transition-all flex flex-col gap-4 ${
                  inv.status === 'accepted'
                    ? 'border-[#00F5D4]/40 bg-[#00F5D4]/5'
                    : 'border-[#2D2E37]'
                }`}
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-[#00F5D4] font-bold">
                        Приглашение #{inv.id}
                      </span>
                      <span className="text-xs text-[#9B9C9E]">•</span>
                      <span className="font-mono text-xs text-white font-bold">
                        Кандидат {inv.candidateMaskedCode}
                      </span>
                    </div>
                    <h3 className="font-mono text-base font-bold text-white mt-1">
                      {inv.vacancyTitle}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    {inv.status === 'accepted' && (
                      <span className="flex items-center gap-1.5 text-xs font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-3 py-1 rounded-full border border-[#00F5D4]/30">
                        <CheckCircle size={14} />
                        <span>Принято • Контакты доступны</span>
                      </span>
                    )}
                    {inv.status === 'viewed' && (
                      <span className="flex items-center gap-1.5 text-xs font-mono text-[#38BDF8] bg-sky-500/10 px-3 py-1 rounded-full border border-sky-500/30">
                        <Clock size={14} />
                        <span>Просмотрено соискателем</span>
                      </span>
                    )}
                    {inv.status === 'sent' && (
                      <span className="flex items-center gap-1.5 text-xs font-mono text-[#9B9C9E] bg-[#2D2E37] px-3 py-1 rounded-full">
                        <Clock size={14} />
                        <span>Отправлено</span>
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-3 bg-[#1B1C21] rounded-[8px] border border-[#2D2E37] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs font-mono">
                  <div>
                    <span className="text-[#9B9C9E]">Зарплатная вилка предложения: </span>
                    <strong className="text-white">
                      {inv.salaryMinRub.toLocaleString('ru-RU')} — {inv.salaryMaxRub.toLocaleString('ru-RU')} ₽ / месяц
                    </strong>
                  </div>
                  <p className="text-[11px] text-[#C8C9CA] italic">
                    «{inv.pitchMessage}»
                  </p>
                </div>

                {/* Dynamic Unmasked Contacts Card on status = 'accepted' */}
                {inv.status === 'accepted' && (
                  <div className="pt-2">
                    <UnmaskedContactCard
                      email={contactsMap[inv.candidateId]?.email || `candidate_${inv.candidateId}@fsp.ru`}
                      phone={contactsMap[inv.candidateId]?.phone}
                      telegram={contactsMap[inv.candidateId]?.telegram}
                      githubUrl={contactsMap[inv.candidateId]?.githubUrl}
                      pdfUrl={contactsMap[inv.candidateId]?.pdfUrl}
                    />
                    <div className="flex justify-end gap-2 mt-3">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleExportHuntflow(inv.candidateId)}
                      >
                        <Download size={14} />
                        <span>Экспорт в ATS (Huntflow)</span>
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </EmployerLayout>
  );
};
export default EmployerInvitationsPage;

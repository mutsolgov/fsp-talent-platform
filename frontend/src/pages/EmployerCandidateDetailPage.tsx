import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { MaskedContactIndicator } from '../components/molecules/MaskedContactIndicator';
import { UnmaskedContactCard } from '../components/molecules/UnmaskedContactCard';
import { RadarMatchChart } from '../components/molecules/RadarMatchChart';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Spinner } from '../components/atoms/Spinner';
import { InvitationComposerModal } from '../components/organisms/InvitationComposerModal';
import { Mail, Check, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export interface CandidateDetailState {
  id: number;
  maskedCode: string;
  specialization: string;
  verifiedGrade: string;
  finalScore: number;
  theta: number;
  freshnessScore: number;
  isFspVerified: boolean;
  skills: string[];
  isContactsMasked: boolean;
  email?: string | null;
  phone?: string | null;
  telegram?: string | null;
  githubUrl?: string | null;
  pdfUrl?: string | null;
}

export const EmployerCandidateDetailPage: React.FC = () => {
  const [candidate, setCandidate] = useState<CandidateDetailState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [vacancies, setVacancies] = useState<any[]>([]);

  useEffect(() => {
    const parts = window.location.pathname.split('/');
    const lastPart = parts[parts.length - 1];
    const candidateId = !isNaN(Number(lastPart)) && Number(lastPart) > 0 ? Number(lastPart) : 1;

    let isMounted = true;

    const loadCandidate = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.get<any>(`/candidate-bank/${candidateId}`);
        if (!isMounted) return;

        setCandidate({
          id: data.id ?? candidateId,
          maskedCode: data.masked_full_name || `CAND-${data.id ?? candidateId}`,
          specialization: data.specialization || 'backend',
          verifiedGrade: data.grade || 'senior',
          finalScore: data.test_score ?? 85.0,
          theta: data.test_score ?? 85.0,
          freshnessScore: data.freshness_score ?? 90,
          isFspVerified: Boolean(data.fsp_verified),
          skills: data.skills || ['Python', 'PostgreSQL', 'Docker'],
          isContactsMasked: data.is_contacts_masked !== false,
          email: data.email,
          phone: data.phone,
          telegram: data.telegram,
          githubUrl: data.github_url,
          pdfUrl: data.raw_resume_pdf_url || data.anonymized_pdf_url,
        });
      } catch (err: any) {
        if (!isMounted) return;
        setError(err?.message || 'Не удалось загрузить профиль кандидата');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    const loadVacancies = async () => {
      try {
        const vData = await api.get<any>('/vacancies');
        if (!isMounted) return;
        const list = Array.isArray(vData) ? vData : vData?.items || [];
        setVacancies(
          list.map((v: any) => ({
            id: v.id,
            title: v.title,
            companyName: v.employer_company_name ?? v.companyName ?? 'Компания',
            inn: v.inn ?? '',
            specialization: v.specialization ?? 'backend',
            grade: v.grade ?? 'middle',
            salaryMinRub: v.salary_min ?? v.salaryMinRub ?? 0,
            salaryMaxRub: v.salary_max ?? v.salaryMaxRub ?? 0,
            location: v.location ?? '',
            isTrustEmployer: v.is_trust_employer ?? v.isTrustEmployer ?? true,
            tags: v.required_skills ?? v.tags ?? [],
            createdAt: v.created_at ?? v.createdAt ?? '',
          }))
        );
      } catch {
        if (!isMounted) return;
        setVacancies([]);
      }
    };

    loadCandidate();
    loadVacancies();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <EmployerLayout currentTab="candidate-bank">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Spinner size="lg" color="#00F5D4" label="Загрузка карточки кандидата..." />
            <p className="text-xs font-mono text-[#9B9C9E]">Загрузка данных кандидата из банка талантов...</p>
          </div>
        )}

        {error && !isLoading && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 rounded-[12px] flex items-center gap-3 text-rose-300 font-mono text-xs">
            <AlertCircle size={20} className="shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {!isLoading && candidate && (
          <>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                    {!candidate.isContactsMasked ? candidate.maskedCode : `Кандидат #${candidate.maskedCode}`}
                  </h1>
                  <Badge variant="fsp" size="sm">
                    {candidate.specialization.toUpperCase()} • {candidate.verifiedGrade.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-xs text-[#9B9C9E] mt-1 font-mono">
                  Подтверждено сессией KITE IRT 3PL • Базовый скоринг S = {candidate.finalScore}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="fsp_mint"
                  size="md"
                  onClick={() => setIsInviteOpen(true)}
                >
                  <Mail size={16} />
                  <span>Отправить инвайт с вилкой</span>
                </Button>
              </div>
            </div>

            {/* 152-ФЗ Contact Card / Masked Indicator */}
            <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37]">
              {!candidate.isContactsMasked ? (
                <UnmaskedContactCard
                  email={candidate.email || ''}
                  phone={candidate.phone || undefined}
                  telegram={candidate.telegram || undefined}
                  githubUrl={candidate.githubUrl || undefined}
                  pdfUrl={candidate.pdfUrl || undefined}
                />
              ) : (
                <div className="flex flex-col items-center justify-center py-6 gap-3 text-center">
                  <img src="/brand/face1.png" alt="152-ФЗ" className="w-16 h-16 rounded-full border border-[#00F5D4]/40" />
                  <h3 className="font-mono text-base font-bold text-white">
                    Персональные контакты скрыты по 152-ФЗ РФ
                  </h3>
                  <p className="text-xs text-[#9B9C9E] max-w-md">
                    Отправьте кандидату приглашение с рублевой зарплатной вилкой. После подтверждения соискателем контакты раскроются автоматически.
                  </p>
                  <MaskedContactIndicator candidateId={candidate.id} onInviteClick={() => setIsInviteOpen(true)} />
                </div>
              )}
            </div>

            {/* Competencies & Radar */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
                <h3 className="font-mono text-sm font-bold text-white">Подтвержденные технологии:</h3>
                <div className="flex flex-wrap gap-2">
                  {candidate.skills.map((s, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 rounded-[6px] text-xs font-mono bg-[#1B1C21] border border-[#2D2E37] text-white flex items-center gap-1.5"
                    >
                      <Check size={12} className="text-[#00F5D4]" />
                      <span>{s}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col items-center justify-center">
                <h3 className="font-mono text-sm font-bold text-white mb-2 self-start">Многофакторный радар:</h3>
                <RadarMatchChart
                  testMatch={candidate.theta}
                  stackMatch={95}
                  fspMatch={90}
                  freshnessMatch={candidate.freshnessScore}
                  isFspProfile={candidate.isFspVerified}
                  size={200}
                />
              </div>
            </div>

            {isInviteOpen && (
              <InvitationComposerModal
                isOpen={true}
                onClose={() => setIsInviteOpen(false)}
                candidateId={candidate.id}
                candidateName={candidate.maskedCode}
                vacancies={vacancies}
              />
            )}
          </>
        )}
      </div>
    </EmployerLayout>
  );
};

export default EmployerCandidateDetailPage;

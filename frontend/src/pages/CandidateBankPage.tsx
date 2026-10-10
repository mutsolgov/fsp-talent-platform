import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { CandidateCard } from '../components/organisms/CandidateCard';
import { SearchFilterBar } from '../components/molecules/SearchFilterBar';
import { PinnedCandidatesDrawer } from '../components/organisms/PinnedCandidatesDrawer';
import { ExplainabilityModal } from '../components/organisms/ExplainabilityModal';
import { InvitationComposerModal } from '../components/organisms/InvitationComposerModal';
import { PaginationBar } from '../components/molecules/PaginationBar';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Spinner } from '../components/atoms/Spinner';
import { CandidateAnonymizedSummary, SearchFilters, VacancySummary, Specialization, Grade, SportRank } from '../types';
import { useShortlistStore } from '../stores/useShortlistStore';
import { Users, Pin, ShieldCheck, AlertCircle, CheckCircle, RefreshCw } from '../components/icons';
import { api } from '../api/client';

const mapBankItemToSummary = (item: any): CandidateAnonymizedSummary => ({
  id: item.id,
  maskedCode: item.masked_full_name || `CAND-${item.id}`,
  specialization: (item.specialization as Specialization) || 'backend',
  verifiedGrade: (item.grade as Grade) || 'middle',
  finalScore: item.match_score ?? item.test_score ?? 80.0,
  isFspVerified: Boolean(item.fsp_verified),
  sportRank: (item.sport_rank as SportRank) || (item.fsp_verified ? '1Р' : null),
  fspId: item.fsp_id || null,
  theta: item.test_score ?? 75.0,
  freshnessScore: item.freshness_score ?? 90,
  skills: item.skills || [],
  matchedSkills: item.explainability?.matched_skills || item.skills?.slice(0, 3) || [],
  missingSkills: item.explainability?.missing_skills || [],
  weights: item.explainability?.component_scores?.weights_applied ? {
    isFspProfile: Boolean(item.explainability.component_scores.weights_applied.is_fsp_profile ?? item.fsp_verified),
    wTest: item.explainability.component_scores.weights_applied.w_test,
    wStack: item.explainability.component_scores.weights_applied.w_stack,
    wFsp: item.explainability.component_scores.weights_applied.w_fsp,
    wFreshness: item.explainability.component_scores.weights_applied.w_freshness,
  } : {
    isFspProfile: Boolean(item.fsp_verified),
    wTest: item.fsp_verified ? 0.35 : 0.52,
    wStack: item.fsp_verified ? 0.25 : 0.30,
    wFsp: item.fsp_verified ? 0.25 : 0.00,
    wFreshness: item.fsp_verified ? 0.15 : 0.18,
  },
  factors: {
    testScore: item.explainability?.component_scores?.test_score ?? item.test_score ?? 75.0,
    stackMatchPct: item.explainability?.component_scores?.stack_score ?? 90.0,
    fspScore: item.explainability?.component_scores?.fsp_score ?? (item.fsp_verified ? 85.0 : 0.0),
    freshnessScore: item.explainability?.component_scores?.freshness_score ?? item.freshness_score ?? 90.0,
  },
  fspAchievements: item.fsp_achievements || (item.fsp_verified ? [{
    title: 'Верифицированный участник соревнований ФСП',
    year: 2025,
    rank: item.sport_rank || '1Р',
    medal: 'participant',
  }] : []),
});

const mapVacancyToSummary = (v: any): VacancySummary => ({
  id: v.id,
  title: v.title,
  companyName: v.employer_company_name || 'Компания',
  inn: v.inn || '',
  specialization: (v.specialization as Specialization) || 'backend',
  grade: (v.grade as Grade) || 'middle',
  salaryMinRub: v.salary_min ?? 0,
  salaryMaxRub: v.salary_max ?? 0,
  location: v.city || 'Москва',
  isTrustEmployer: true,
  tags: v.required_skills || [],
  createdAt: v.created_at || new Date().toISOString(),
});

export const CandidateBankPage: React.FC = () => {
  const { pinnedIds, togglePin, unpinCandidate } = useShortlistStore();

  const [candidates, setCandidates] = useState<CandidateAnonymizedSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [currentFilters, setCurrentFilters] = useState<SearchFilters>({ specialization: 'all', grade: 'all', onlyFsp: false });

  const [needId, setNeedId] = useState<number | null>(null);
  const [needTitle, setNeedTitle] = useState<string>('');
  const [vacancies, setVacancies] = useState<VacancySummary[]>([]);

  const [activeExplainCandidate, setActiveExplainCandidate] = useState<CandidateAnonymizedSummary | null>(null);
  const [activeInviteCandidate, setActiveInviteCandidate] = useState<CandidateAnonymizedSummary | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isBatchInviting, setIsBatchInviting] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Parse ?needId= from URL search params on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rawNeedId = params.get('needId') || params.get('need_id');
    if (rawNeedId && !isNaN(Number(rawNeedId)) && Number(rawNeedId) > 0) {
      const parsedNeedId = Number(rawNeedId);
      setNeedId(parsedNeedId);
      api.get<any>(`/employer-needs/${parsedNeedId}`)
        .then((data) => {
          if (data?.title) {
            setNeedTitle(data.title);
          }
        })
        .catch(() => {
          // If need title fetch fails, gracefully fallback
        });
    }
  }, []);

  // Fetch employer active vacancies
  useEffect(() => {
    api.get<any>('/vacancies')
      .then((data) => {
        const list = Array.isArray(data) ? data : data?.items || [];
        setVacancies(list.map(mapVacancyToSummary));
      })
      .catch(() => {
        setVacancies([]);
      });
  }, []);

  const fetchCandidates = async (pageToFetch: number, filters: SearchFilters, activeNeedId: number | null) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {
        page: pageToFetch,
        page_size: pageSize,
      };
      if (activeNeedId) {
        params.need_id = activeNeedId;
      }
      if (filters.specialization && filters.specialization !== 'all') {
        params.specialization = filters.specialization;
      }
      if (filters.grade && filters.grade !== 'all') {
        params.grade = filters.grade;
      }
      if (filters.onlyFsp) {
        params.fsp_only = true;
      }

      const data = await api.get<any>('/candidate-bank', { params });
      const items = Array.isArray(data) ? data : data?.items || [];
      setCandidates(items.map(mapBankItemToSummary));

      if (data?.meta) {
        setTotalItems(data.meta.total ?? items.length);
        setTotalPages(data.meta.total_pages ?? (items.length > 0 ? 1 : 0));
        setPage(data.meta.page ?? pageToFetch);
      } else {
        setTotalItems(items.length);
        setTotalPages(items.length > 0 ? 1 : 0);
        setPage(pageToFetch);
      }
    } catch (err: any) {
      setError(err?.message || 'Не удалось загрузить кандидатов');
      setCandidates([]);
      setTotalItems(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates(1, currentFilters, needId);
  }, [needId]);

  const handleFilterChange = (filters: SearchFilters) => {
    setCurrentFilters(filters);
    setPage(1);
    fetchCandidates(1, filters, needId);
  };

  const handleResetFilters = () => {
    const defaultFilters: SearchFilters = { specialization: 'all', grade: 'all', onlyFsp: false };
    setCurrentFilters(defaultFilters);
    setPage(1);
    fetchCandidates(1, defaultFilters, needId);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    fetchCandidates(newPage, currentFilters, needId);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const pinnedCandidates = candidates.filter((c) => pinnedIds.includes(c.id));

  const handleBatchInvite = async () => {
    if (pinnedCandidates.length === 0) return;
    setIsBatchInviting(true);
    let successCount = 0;
    let failCount = 0;

    for (const cand of pinnedCandidates) {
      try {
        await api.post('/invitations', {
          candidate_profile_id: cand.id,
          vacancy_id: vacancies[0]?.id || undefined,
          salary_min: 200000,
          salary_max: 320000,
          salary_currency: 'RUB',
          proposal_text: `Здравствуйте! Нам понравился ваш подтвержденный профиль KITE IRT. Приглашаем обсудить сотрудничество${needTitle ? ` в рамках потребности «${needTitle}»` : ''}.`,
          contact_method: 'platform',
        });
        successCount++;
      } catch {
        failCount++;
      }
    }

    setIsBatchInviting(false);
    setIsDrawerOpen(false);

    if (successCount > 0) {
      setFeedbackMessage({
        type: 'success',
        text: `Приглашения успешно отправлены ${successCount} ${successCount === 1 ? 'кандидату' : 'кандидатам'}${failCount > 0 ? ` (${failCount} не отправлено из-за лимитов)` : ''}.`,
      });
    } else {
      setFeedbackMessage({
        type: 'error',
        text: 'Не удалось отправить групповые приглашения (проверьте лимиты или наличие активных приглашений).',
      });
    }

    setTimeout(() => {
      setFeedbackMessage(null);
    }, 5000);
  };

  return (
    <EmployerLayout currentTab="candidate-bank">
      <div className="flex flex-col gap-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Банк проверенных ИТ-талантов
              </h1>
              <Badge variant="fsp" size="sm">
                Reverse Recruiting
              </Badge>
              {needTitle && (
                <Badge variant="default" size="sm" className="font-mono">
                  Потребность: {needTitle}
                </Badge>
              )}
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Все специалисты прошли онбординг KITE IRT 3PL. Контакты скрыты по 152-ФЗ до принятия вашего приглашения.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant={pinnedIds.length > 0 ? 'fsp_mint' : 'secondary'}
              size="md"
              onClick={() => setIsDrawerOpen(true)}
            >
              <Pin size={16} />
              <span>Закрепленные таланты ({pinnedIds.length})</span>
            </Button>
          </div>
        </div>

        {/* Feedback message banner */}
        {feedbackMessage && (
          <div
            className={`p-4 rounded-[12px] border text-xs font-mono flex items-center gap-3 animate-in fade-in ${
              feedbackMessage.type === 'success'
                ? 'bg-[#00F5D4]/10 border-[#00F5D4]/40 text-[#00F5D4]'
                : 'bg-rose-950/40 border-rose-500/40 text-[#FB7185]'
            }`}
          >
            {feedbackMessage.type === 'success' ? (
              <CheckCircle size={18} className="shrink-0" />
            ) : (
              <AlertCircle size={18} className="shrink-0" />
            )}
            <span>{feedbackMessage.text}</span>
          </div>
        )}

        {/* 152-ФЗ Privacy Banner */}
        <div className="p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex items-center justify-between text-xs text-[#C8C9CA]">
          <div className="flex items-center gap-3">
            <ShieldCheck size={20} className="text-[#00F5D4] shrink-0" />
            <span>
              <strong>Равноправие треков:</strong> Кандидаты без спортивной истории ФСП оцениваются по формуле переаллокации весов (0.52 / 0.30 / 0.00 / 0.18) с равным шансом на высший балл.
            </span>
          </div>
        </div>

        {/* Filters Molecule */}
        <SearchFilterBar
          filters={currentFilters}
          onChange={handleFilterChange}
          onReset={handleResetFilters}
        />

        {/* Error banner */}
        {error && (
          <div className="p-4 rounded-[12px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={18} className="shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => fetchCandidates(page, currentFilters, needId)}
              className="px-3 py-1 bg-rose-900/50 hover:bg-rose-800 text-white rounded-[6px] transition-colors cursor-pointer"
            >
              Повторить
            </button>
          </div>
        )}

        {/* Content State: Loading, Empty, or Candidates Grid */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Spinner size="lg" color="#402FFF" />
            <span className="text-xs font-mono text-[#9B9C9E]">Загрузка базы кандидатов...</span>
          </div>
        ) : candidates.length === 0 ? (
          <div className="text-center py-16 bg-[#202129] border border-[#2D2E37] rounded-[14px] p-8 flex flex-col items-center gap-3">
            <Users size={40} className="text-[#5F5F66]" />
            <h3 className="font-mono text-base font-bold text-white">Кандидаты не найдены</h3>
            <p className="text-xs text-[#9B9C9E] max-w-md">
              По заданным критериям фильтрации не найдено подходящих специалистов. Измените параметры фильтров или сбросьте поиск.
            </p>
            <Button variant="secondary" size="sm" onClick={handleResetFilters} className="mt-2">
              <RefreshCw size={14} />
              <span>Сбросить фильтры</span>
            </Button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {candidates.map((cand) => (
                <CandidateCard
                  key={cand.id}
                  candidate={cand}
                  isPinned={pinnedIds.includes(cand.id)}
                  onPinToggle={() => togglePin(cand.id)}
                  onExplainClick={() => setActiveExplainCandidate(cand)}
                  onInviteClick={() => setActiveInviteCandidate(cand)}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            <PaginationBar
              page={page}
              totalPages={totalPages}
              totalItems={totalItems}
              onPageChange={handlePageChange}
              className="mt-2"
            />
          </>
        )}

        {/* Explainability Modal */}
        {activeExplainCandidate && (
          <ExplainabilityModal
            isOpen={true}
            onClose={() => setActiveExplainCandidate(null)}
            candidate={activeExplainCandidate}
            needTitle={needTitle || undefined}
          />
        )}

        {/* Direct Invitation Composer Modal */}
        {activeInviteCandidate && (
          <InvitationComposerModal
            isOpen={true}
            onClose={() => setActiveInviteCandidate(null)}
            candidateId={activeInviteCandidate.id}
            candidateName={activeInviteCandidate.maskedCode}
            vacancies={vacancies}
          />
        )}

        {/* Pinned Candidates Drawer */}
        <PinnedCandidatesDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          pinnedCandidates={pinnedCandidates}
          onUnpin={(id) => unpinCandidate(id)}
          onBatchInvite={handleBatchInvite}
        />
      </div>
    </EmployerLayout>
  );
};
export default CandidateBankPage;

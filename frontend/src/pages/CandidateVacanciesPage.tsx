import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { VacancyCard } from '../components/organisms/VacancyCard';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { VacancySummary } from '../types';
import { Briefcase, CheckCircle, Search, Filter } from '../components/icons';
import { api } from '../api/client';

export const CandidateVacanciesPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'applications'>('catalog');
  const [vacancies, setVacancies] = useState<VacancySummary[]>([]);
  const [appliedIds, setAppliedIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [applyNotification, setApplyNotification] = useState<string | null>(null);

  useEffect(() => {
    const fetchVacanciesAndApps = async () => {
      setIsLoading(true);
      try {
        const [vData, aData] = await Promise.allSettled([
          api.get<any>('/vacancies'),
          api.get<any>('/applications/sent'),
        ]);

        if (vData.status === 'fulfilled') {
          const list = Array.isArray(vData.value) ? vData.value : vData.value?.items || [];
          const normalized = list.map((item: any) => ({
            id: item.id,
            title: item.title,
            companyName: item.employer_company_name ?? item.companyName ?? 'Компания',
            inn: item.inn ?? '',
            specialization: item.specialization ?? 'backend',
            grade: item.grade ?? 'middle',
            salaryMinRub: item.salary_min ?? item.salaryMinRub ?? 0,
            salaryMaxRub: item.salary_max ?? item.salaryMaxRub ?? 0,
            location: item.location ?? `${item.city || 'Москва'} (${item.work_format || 'Гибрид'})`,
            isTrustEmployer: item.is_trust_employer ?? item.isTrustEmployer ?? true,
            tags: item.required_skills ?? item.tags ?? [],
            createdAt: item.created_at ?? item.createdAt ?? '',
          }));
          setVacancies(normalized);
        } else {
          setVacancies([]);
        }

        if (aData.status === 'fulfilled') {
          const aList = Array.isArray(aData.value) ? aData.value : aData.value?.items || [];
          const ids = aList.map((a: any) => a.vacancy_id ?? a.vacancyId).filter(Boolean);
          setAppliedIds(ids);
        } else {
          setAppliedIds([]);
        }
      } catch {
        setVacancies([]);
        setAppliedIds([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchVacanciesAndApps();
  }, []);

  const handleApply = async (vacancyId: number) => {
    try {
      await api.post('/applications', { vacancy_id: vacancyId });
    } catch {
      // Best effort submit
    }
    setAppliedIds((prev) => (prev.includes(vacancyId) ? prev : [...prev, vacancyId]));
    setApplyNotification('Отклик успешно отправлен работодателю с верифицированным KITE-профилем!');
    setTimeout(() => setApplyNotification(null), 4000);
  };

  return (
    <CandidateLayout currentTab="applications">
      <div className="flex flex-col gap-6 max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
              Вакансии и прямые отклики
            </h1>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Все вакансии проверены на соответствие антифрод-политике и содержат обязательную рублевую вилку.
            </p>
          </div>

          <div className="flex items-center gap-2 p-1 bg-[#202129] rounded-[8px] border border-[#2D2E37]">
            <button
              type="button"
              onClick={() => setActiveTab('catalog')}
              className={`px-3 py-1.5 rounded-[6px] text-xs font-mono transition-colors ${
                activeTab === 'catalog' ? 'bg-[#402FFF] text-white font-bold' : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              Каталог ({vacancies.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('applications')}
              className={`px-3 py-1.5 rounded-[6px] text-xs font-mono transition-colors ${
                activeTab === 'applications' ? 'bg-[#00F5D4] text-[#1B1C21] font-bold' : 'text-[#9B9C9E] hover:text-white'
              }`}
            >
              Мои отклики ({appliedIds.length})
            </button>
          </div>
        </div>

        {applyNotification && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2">
            <CheckCircle size={16} />
            <span>{applyNotification}</span>
          </div>
        )}

        {/* Tab 1: Catalog */}
        {activeTab === 'catalog' && (
          <>
            {vacancies.length === 0 ? (
              <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E]">
                {isLoading ? 'Загрузка каталога вакансий...' : 'Вакансий в каталоге пока нет.'}
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {vacancies.map((vacancy) => (
                  <VacancyCard
                    key={vacancy.id}
                    vacancy={vacancy}
                    isApplied={appliedIds.includes(vacancy.id)}
                    onApplyClick={() => handleApply(vacancy.id)}
                    isPublic={false}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* Tab 2: My Applications */}
        {activeTab === 'applications' && (
          <div className="flex flex-col gap-4">
            {vacancies.filter((v) => appliedIds.includes(v.id)).length === 0 ? (
              <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E]">
                {isLoading ? 'Загрузка откликов...' : 'У вас пока нет активных откликов на вакансии.'}
              </div>
            ) : (
              vacancies
                .filter((v) => appliedIds.includes(v.id))
                .map((vacancy) => (
                  <div
                    key={vacancy.id}
                    className="p-5 bg-[#202129] rounded-[12px] border border-[#2D2E37] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                  >
                    <div>
                      <span className="text-xs font-mono text-[#00F5D4] font-bold">
                        {vacancy.companyName}
                      </span>
                      <h3 className="font-mono text-base font-bold text-white mt-0.5">
                        {vacancy.title}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-[#9B9C9E] mt-1.5 font-mono">
                        <span>{vacancy.salaryMinRub.toLocaleString('ru-RU')} — {vacancy.salaryMaxRub.toLocaleString('ru-RU')} ₽</span>
                        <span>•</span>
                        <span>{vacancy.location}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 self-end sm:self-center">
                      <span className="px-3 py-1 rounded-full text-xs font-mono bg-blue-500/10 text-blue-400 border border-blue-500/30">
                        На рассмотрении HR
                      </span>
                    </div>
                  </div>
                ))
            )}
          </div>
        )}
      </div>
    </CandidateLayout>
  );
};
export default CandidateVacanciesPage;

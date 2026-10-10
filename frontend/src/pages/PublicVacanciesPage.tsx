import React, { useState, useEffect } from 'react';
import { PublicLayout } from '../components/templates/PublicLayout';
import { VacancyCard } from '../components/organisms/VacancyCard';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { VacancySummary } from '../types';
import { Search, Building, ShieldCheck } from '../components/icons';

import { api } from '../api/client';

export const PublicVacanciesPage: React.FC = () => {
  const [vacancies, setVacancies] = useState<VacancySummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let mounted = true;
    api.get<any>('/vacancies')
      .then((res) => {
        if (!mounted) return;
        const rawItems = Array.isArray(res) ? res : res?.items || [];
        const mapped: VacancySummary[] = rawItems.map((v: any) => ({
          id: v.id,
          title: v.title || 'ИТ-Вакансия',
          companyName: v.employer_company_name || v.companyName || 'Верифицированный работодатель',
          inn: v.inn || '',
          specialization: v.specialization || 'backend',
          grade: v.grade || 'middle',
          salaryMinRub: v.salary_min ?? v.salaryMinRub ?? 0,
          salaryMaxRub: v.salary_max ?? v.salaryMaxRub ?? 0,
          location: v.city ? `${v.city} (${v.work_format || 'удаленно'})` : (v.location || 'РФ (Удаленно)'),
          isTrustEmployer: v.is_trust_employer ?? v.isTrustEmployer ?? true,
          tags: v.required_skills || v.tags || [],
          createdAt: v.created_at || v.createdAt || new Date().toISOString(),
        }));
        setVacancies(mapped);
      })
      .catch(() => {
        if (!mounted) return;
        setVacancies([]);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const filtered = vacancies.filter(
    (v) =>
      v.title.toLowerCase().includes(query.toLowerCase()) ||
      v.tags.some((t) => t.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <PublicLayout>
      <div className="flex flex-col gap-8 max-w-5xl mx-auto">
        <div className="text-center flex flex-col items-center gap-3">
          <Badge variant="fsp" size="md">ОТКРЫТЫЙ РЕЕСТР ВАКАНСИЙ ФСП</Badge>
          <h1 className="font-mono text-3xl sm:text-4xl font-bold text-white">
            ИТ-Вакансии с проверенными зарплатами
          </h1>
          <p className="text-xs sm:text-sm text-[#9B9C9E] max-w-xl">
            100% вакансий на платформе содержат обязательную рублевую вилку и проходят верификацию юридического лица (ИНН) через антифрод-шлюз.
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <input
            type="text"
            placeholder="Поиск по стеку, названию или технологии (например: Python, React, HighLoad)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#202129] border border-[#2D2E37] rounded-[12px] p-4 text-xs font-mono text-white pl-11 focus:outline-none focus:border-[#402FFF]"
          />
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9B9C9E]" />
        </div>

        <div className="flex flex-col gap-4">
          {isLoading && (
            <div className="text-center py-12 text-[#9B9C9E] font-mono text-xs">Загрузка вакансий...</div>
          )}
          {!isLoading && filtered.length === 0 && (
            <div className="text-center py-12 text-[#9B9C9E] font-mono text-xs">Вакансий не найдено</div>
          )}
          {filtered.map((v) => (
            <div key={v.id} className="relative">
              <VacancyCard
                vacancy={v}
                onApplyClick={() => {
                  window.location.href = `/vacancies/${v.id}`;
                }}
                isPublic={true}
              />
            </div>
          ))}
        </div>
      </div>
    </PublicLayout>
  );
};
export default PublicVacanciesPage;

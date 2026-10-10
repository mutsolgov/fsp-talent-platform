import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { VacancySummary } from '../types';
import { Building, Plus, Users, ArrowRight, CheckCircle } from '../components/icons';
import { api } from '../api/client';

export const EmployerVacanciesPage: React.FC = () => {
  const [vacancies, setVacancies] = useState<VacancySummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchMine = async () => {
      setIsLoading(true);
      try {
        const data = await api.get<any>('/vacancies/mine');
        const list = Array.isArray(data) ? data : data?.items || [];
        const normalized = list.map((v: any) => ({
          id: v.id,
          title: v.title,
          companyName: v.employer_company_name ?? v.companyName ?? 'Компания',
          inn: v.inn ?? '',
          specialization: v.specialization ?? 'backend',
          grade: v.grade ?? 'middle',
          salaryMinRub: v.salary_min ?? v.salaryMinRub ?? 0,
          salaryMaxRub: v.salary_max ?? v.salaryMaxRub ?? 0,
          location: v.location ?? `${v.city || 'Москва'} (${v.work_format || 'Гибрид'})`,
          isTrustEmployer: v.is_trust_employer ?? v.isTrustEmployer ?? true,
          tags: v.required_skills ?? v.tags ?? [],
          createdAt: v.created_at ?? v.createdAt ?? '',
        }));
        setVacancies(normalized);
      } catch {
        setVacancies([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchMine();
  }, []);

  return (
    <EmployerLayout currentTab="vacancies">
      <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Опубликованные вакансии компании
              </h1>
              <Badge variant="fsp" size="sm">
                {vacancies.length} открытых
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Все вакансии обязательно публикуются с рублевой вилкой (spread &le; 3.5) и валидируются антифрод-модулем.
            </p>
          </div>

          <a href="/employer/vacancies/new">
            <Button variant="fsp_mint" size="md">
              <Plus size={16} />
              <span>Опубликовать вакансию</span>
            </Button>
          </a>
        </div>

        {vacancies.length === 0 ? (
          <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E] flex flex-col items-center gap-4">
            <p>{isLoading ? 'Загрузка списка вакансий...' : 'У вашей компании пока нет опубликованных вакансий.'}</p>
            <a href="/employer/vacancies/new">
              <Button variant="fsp_mint" size="sm">
                <Plus size={14} />
                <span>Опубликовать первую вакансию</span>
              </Button>
            </a>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {vacancies.map((v) => (
              <div
                key={v.id}
                className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] hover:border-[#402FFF]/50 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
              >
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" size="sm" className="uppercase font-mono">
                      {v.specialization} • {v.grade}
                    </Badge>
                    <span className="text-[11px] font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-2 py-0.5 rounded border border-[#00F5D4]/30">
                      Опубликована
                    </span>
                  </div>

                  <h3 className="font-mono text-lg font-bold text-white">
                    {v.title}
                  </h3>

                  <div className="flex items-center gap-4 text-xs font-mono text-[#C8C9CA]">
                    <span>
                      Вилка ЗП: <strong className="text-white">{(v.salaryMinRub ?? 0).toLocaleString('ru-RU')} — {(v.salaryMaxRub ?? 0).toLocaleString('ru-RU')} ₽</strong>
                    </span>
                    <span>•</span>
                    <span>{v.location}</span>
                  </div>

                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {(v.tags ?? []).map((t, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#1B1C21] text-[#9B9C9E] border border-[#2D2E37]">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto justify-end">
                  <a href={`/employer/vacancies/${v.id}`}>
                    <Button variant="secondary" size="sm">
                      <span>Редактировать</span>
                    </Button>
                  </a>
                  <a href="/employer/applications">
                    <Button variant="fsp_mint" size="sm">
                      <Users size={14} />
                      <span>Отклики соискателей</span>
                    </Button>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </EmployerLayout>
  );
};
export default EmployerVacanciesPage;

import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { PaginationBar } from '../components/molecules/PaginationBar';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Spinner } from '../components/atoms/Spinner';
import { EmployerNeedSummary, Specialization, Grade } from '../types';
import { Briefcase, ArrowRight, Plus, Users, AlertCircle, RefreshCw } from '../components/icons';
import { api } from '../api/client';

export const EmployerNeedsPage: React.FC = () => {
  const [needs, setNeeds] = useState<EmployerNeedSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);

  const fetchNeeds = async (pageToFetch: number = 1) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<any>('/employer-needs', {
        params: {
          page: pageToFetch,
          page_size: pageSize,
        },
      });
      const list = Array.isArray(data) ? data : data?.items || [];
      const normalized: EmployerNeedSummary[] = list.map((need: any) => ({
        id: need.id,
        title: need.title || 'Потребность команды',
        specialization: (need.specialization?.code ?? need.specialization ?? 'backend') as Specialization,
        targetGrade: (need.grade?.code ?? need.grade ?? need.target_grade ?? 'middle') as Grade,
        salaryMinRub: need.salary_min ?? 0,
        salaryMaxRub: need.salary_max ?? 0,
        status: need.is_active ? 'active' : 'closed',
        matchedCandidatesCount: need.matched_candidates_count ?? 0,
        createdAt: need.created_at ?? '',
      }));
      setNeeds(normalized);

      if (data?.meta) {
        setTotalItems(data.meta.total ?? normalized.length);
        setTotalPages(data.meta.total_pages ?? (normalized.length > 0 ? 1 : 0));
        setPage(data.meta.page ?? pageToFetch);
      } else {
        setTotalItems(normalized.length);
        setTotalPages(normalized.length > 0 ? 1 : 0);
        setPage(pageToFetch);
      }
    } catch (err: any) {
      setError(err?.message || 'Не удалось загрузить список потребностей');
      setNeeds([]);
      setTotalItems(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNeeds(1);
  }, []);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    fetchNeeds(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <EmployerLayout currentTab="needs">
      <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Потребности инженерных команд
              </h1>
              <Badge variant="fsp" size="sm">
                {needs.filter((n) => n.status === 'active').length} активных
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Модель LHH: сформулируйте потребность команды для автоматического подбора и ранжирования $S$.
            </p>
          </div>

          <a href="/employer/needs/new">
            <Button variant="fsp_mint" size="md">
              <Plus size={16} />
              <span>Создать потребность</span>
            </Button>
          </a>
        </div>

        {/* Error notification banner */}
        {error && (
          <div className="p-4 rounded-[12px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={18} className="shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => fetchNeeds(page)}
              className="px-3 py-1 bg-rose-900/50 hover:bg-rose-800 text-white rounded-[6px] transition-colors cursor-pointer"
            >
              Повторить
            </button>
          </div>
        )}

        {/* Content States */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Spinner size="lg" color="#402FFF" />
            <span className="text-xs font-mono text-[#9B9C9E]">Загрузка потребностей...</span>
          </div>
        ) : needs.length === 0 ? (
          <div className="text-center py-16 bg-[#202129] border border-[#2D2E37] rounded-[14px] p-8 flex flex-col items-center gap-3">
            <Briefcase size={40} className="text-[#5F5F66]" />
            <h3 className="font-mono text-base font-bold text-white">Нет активных потребностей</h3>
            <p className="text-xs text-[#9B9C9E] max-w-md">
              Сформулируйте первую потребность команды с обязательной рублевой зарплатной вилкой для автоматического подбора кандидатов.
            </p>
            <a href="/employer/needs/new" className="mt-2">
              <Button variant="fsp_mint" size="sm">
                <Plus size={16} />
                <span>Создать потребность</span>
              </Button>
            </a>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4">
              {needs.map((need) => (
                <div
                  key={need.id}
                  className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] hover:border-[#402FFF]/50 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="default" size="sm" className="uppercase font-mono">
                        {need.specialization} • {need.targetGrade}
                      </Badge>
                      <span className="text-[11px] font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-2 py-0.5 rounded border border-[#00F5D4]/30">
                        {need.status === 'active' ? 'Активно' : 'Закрыто'}
                      </span>
                    </div>

                    <h3 className="font-mono text-lg font-bold text-white">
                      {need.title}
                    </h3>

                    <div className="flex items-center gap-4 text-xs font-mono text-[#C8C9CA]">
                      <span>
                        Вилка ЗП: <strong className="text-white">{(need.salaryMinRub ?? 0).toLocaleString('ru-RU')} — {(need.salaryMaxRub ?? 0).toLocaleString('ru-RU')} ₽</strong>
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1.5 text-[#00F5D4]">
                        <Users size={14} />
                        <span>{need.matchedCandidatesCount} подходящих кандидатов</span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 w-full md:w-auto justify-end">
                    <a href={`/employer/needs/${need.id}`}>
                      <Button variant="secondary" size="sm">
                        <span>Детали</span>
                      </Button>
                    </a>
                    <a href={`/employer/candidate-bank?needId=${need.id}`}>
                      <Button variant="fsp_mint" size="sm">
                        <span>Подборка талантов</span>
                        <ArrowRight size={14} />
                      </Button>
                    </a>
                  </div>
                </div>
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
      </div>
    </EmployerLayout>
  );
};
export default EmployerNeedsPage;

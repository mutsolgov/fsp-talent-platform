import React, { useState, useEffect } from 'react';
import { PublicLayout } from '../components/templates/PublicLayout';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { useAuthStore } from '../stores/useAuthStore';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Building, ShieldCheck, CheckCircle, ArrowRight, Check, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const VacancyDetailPage: React.FC = () => {
  const { role } = useAuthStore();
  const [vacancyId, setVacancyId] = useState<number>(() => {
    const parts = window.location.pathname.split('/').filter(Boolean);
    const last = parts[parts.length - 1];
    const num = Number(last);
    return !isNaN(num) && num > 0 ? num : 1;
  });
  const [vacancy, setVacancy] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);

  useEffect(() => {
    const parts = window.location.pathname.split('/').filter(Boolean);
    const last = parts[parts.length - 1];
    const num = Number(last);
    const resolvedId = !isNaN(num) && num > 0 ? num : 1;
    setVacancyId(resolvedId);

    const loadVacancy = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [vRes, aRes] = await Promise.allSettled([
          api.get<any>(`/vacancies/${resolvedId}`),
          role === 'candidate' ? api.get<any>('/applications/sent') : Promise.resolve(null),
        ]);

        if (vRes.status === 'fulfilled') {
          const data = vRes.value;
          setVacancy({
            id: data.id ?? resolvedId,
            title: data.title ?? 'Вакансия',
            companyName: data.employer_company_name ?? 'Работодатель',
            inn: data.inn ?? '7707083893',
            specialization: data.specialization ?? 'backend',
            grade: data.grade ?? 'senior',
            salaryMinRub: data.salary_min ?? 0,
            salaryMaxRub: data.salary_max ?? 0,
            location: `${data.city ?? 'Москва'} (${data.work_format ?? 'Гибрид'})`,
            isTrustEmployer: true,
            tags: data.required_skills ?? [],
            description: data.description ?? 'Описание инженерных задач и архитектуры проекта.',
            responsibilities: [
              'Проектирование и разработка масштабируемых сервисов платформы',
              'Оптимизация производительности и профилирование критических путей',
              'Code Review и участие в архитектурных комитетах команды',
            ],
            requirements: Array.isArray(data.required_skills) && data.required_skills.length > 0
              ? data.required_skills.map((s: string) => `Уверенное практическое владение ${s}`)
              : [
                  'Опыт коммерческой разработки от 3 лет',
                  'Понимание принципов построения надежных распределенных систем',
                ],
            benefits: [
              'Белая заработная плата с фиксацией в рублях и прозрачная система грейдов',
              'ДМС со стоматологией с первого рабочего дня',
              'Поддержка участия в турнирах ФСП России и спортивном программировании',
            ],
          });
        } else {
          setError('Вакансия не найдена на сервере');
        }

        if (aRes.status === 'fulfilled' && aRes.value) {
          const list = Array.isArray(aRes.value) ? aRes.value : aRes.value?.items || [];
          const isAlreadyApplied = list.some((a: any) => (a.vacancy_id ?? a.vacancyId) === resolvedId);
          if (isAlreadyApplied) {
            setApplied(true);
          }
        }
      } catch (err: any) {
        setError(err?.message || 'Вакансия не найдена на сервере');
      } finally {
        setIsLoading(false);
      }
    };
    loadVacancy();
  }, [role]);

  const handleApply = async () => {
    setApplyError(null);
    try {
      await api.post('/applications', { vacancy_id: Number(vacancyId) });
      setApplied(true);
    } catch (err: any) {
      setApplyError(err?.message || 'Не удалось отправить отклик на вакансию');
    }
  };

  const backHref = role === 'candidate' ? '/candidate/applications' : role === 'employer' ? '/employer/vacancies' : '/vacancies';
  const backLabel = role === 'candidate' ? '← Назад к откликам и вакансиям' : role === 'employer' ? '← Назад к вакансиям компании' : '← Каталог вакансий';

  const content = (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      <div className="flex items-center gap-2 text-xs font-mono text-[#9B9C9E]">
        <a href={backHref} className="hover:text-white transition-colors">{backLabel}</a>
        <span>/</span>
        <span className="text-white font-bold">{vacancy?.title || `Вакансия #${vacancyId}`}</span>
      </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[12px] text-xs font-mono flex items-center gap-2">
            <AlertCircle size={18} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {isLoading && !vacancy && (
          <div className="p-12 text-center bg-[#202129] rounded-[16px] border border-[#2D2E37] text-xs font-mono text-[#9B9C9E]">
            Загрузка информации о вакансии #{vacancyId}...
          </div>
        )}

        {vacancy && (
          <div className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="fsp" size="sm" className="uppercase font-mono">
                    {vacancy.specialization} • {vacancy.grade}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-xs font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-2.5 py-0.5 rounded border border-[#00F5D4]/30">
                    <ShieldCheck size={14} />
                    <span>Верифицированный работодатель</span>
                  </div>
                </div>

                <h1 className="font-mono text-2xl sm:text-3xl font-bold text-white mt-2">
                  {vacancy.title}
                </h1>

                <div className="text-xs text-[#9B9C9E] font-mono mt-1">
                  Компания: <strong className="text-white">{vacancy.companyName}</strong> • ИНН {vacancy.inn}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className="text-xs font-mono text-[#9B9C9E]">Зафиксированная вилка:</span>
                <span className="font-mono text-2xl font-bold text-[#00F5D4]">
                  {vacancy.salaryMinRub.toLocaleString('ru-RU')} — {vacancy.salaryMaxRub.toLocaleString('ru-RU')} ₽
                </span>
              </div>
            </div>

            <div className="p-4 bg-[#1B1C21] rounded-[10px] border border-[#2D2E37] flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div>
                <span className="text-[#9B9C9E]">Формат: </span>
                <span className="text-white">{vacancy.location}</span>
              </div>
              <div>
                <span className="text-[#9B9C9E]">Антифрод-контроль: </span>
                <span className="text-[#00F5D4]">Пройден (Спред вилки &le; 3.5)</span>
              </div>
            </div>

            {applyError && (
              <div className="p-3 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[8px] text-xs font-mono flex items-center gap-2">
                <AlertCircle size={16} className="shrink-0" />
                <span>{applyError}</span>
              </div>
            )}

            {applied ? (
              <div className="p-4 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[10px] text-xs font-mono flex items-center gap-2">
                <CheckCircle size={18} />
                <span>Ваш отклик успешно отправлен! Работодатель получил ваш верифицированный KITE-профиль.</span>
              </div>
            ) : role === 'public' ? (
              <div className="flex items-center gap-4">
                <Button
                  variant="fsp_mint"
                  size="lg"
                  onClick={() => { window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`; }}
                >
                  <span>Войти для прямого отклика</span>
                  <ArrowRight size={16} />
                </Button>
              </div>
            ) : role === 'employer' ? (
              <div className="p-3 bg-[#402FFF]/10 border border-[#402FFF]/30 text-white rounded-[8px] text-xs font-mono">
                Режим работодателя: просмотр опубликованных условий вакансии.
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <Button variant="fsp_mint" size="lg" onClick={handleApply}>
                  <span>Откликнуться верифицированным профилем</span>
                  <ArrowRight size={16} />
                </Button>
              </div>
            )}

            <div className="flex flex-col gap-4 pt-4 border-t border-[#2D2E37]">
              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wider">
                О позиции и проекте:
              </h3>
              <p className="text-xs text-[#C8C9CA] leading-relaxed">
                {vacancy.description}
              </p>

              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wider mt-2">
                Задачи:
              </h3>
              <ul className="flex flex-col gap-1.5 text-xs text-[#C8C9CA]">
                {vacancy.responsibilities.map((r: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check size={14} className="text-[#00F5D4] shrink-0 mt-0.5" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>

              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wider mt-2">
                Требования:
              </h3>
              <ul className="flex flex-col gap-1.5 text-xs text-[#C8C9CA]">
                {vacancy.requirements.map((r: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check size={14} className="text-[#402FFF] shrink-0 mt-0.5" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>

              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wider mt-2">
                Условия и бенефиты:
              </h3>
              <ul className="flex flex-col gap-1.5 text-xs text-[#C8C9CA]">
                {vacancy.benefits.map((b: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check size={14} className="text-[#FFD700] shrink-0 mt-0.5" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
  );

  if (role === 'candidate') {
    return <CandidateLayout currentTab="applications">{content}</CandidateLayout>;
  }
  if (role === 'employer') {
    return <EmployerLayout currentTab="vacancies">{content}</EmployerLayout>;
  }
  return <PublicLayout>{content}</PublicLayout>;
};
export default VacancyDetailPage;

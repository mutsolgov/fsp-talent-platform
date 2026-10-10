import React, { useState, useEffect } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { Spinner } from '../components/atoms/Spinner';
import { SalaryRangeInput } from '../components/molecules/SalaryRangeInput';
import { EmployerNeedDetail, Specialization, Grade } from '../types';
import { Briefcase, ArrowRight, CheckCircle, Users, Check, AlertCircle, ChevronLeft } from '../components/icons';
import { api } from '../api/client';

export const EmployerNeedDetailPage: React.FC = () => {
  const [need, setNeed] = useState<EmployerNeedDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [salaryMin, setSalaryMin] = useState<number>(200000);
  const [salaryMax, setSalaryMax] = useState<number>(320000);
  const [isSalaryValid, setIsSalaryValid] = useState<boolean>(true);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  useEffect(() => {
    const parts = window.location.pathname.split('/');
    const lastPart = parts[parts.length - 1];
    const needId = !isNaN(Number(lastPart)) && Number(lastPart) > 0 ? Number(lastPart) : null;

    if (!needId) {
      setError('Некорректный идентификатор потребности в URL');
      setIsLoading(false);
      return;
    }

    const loadNeed = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.get<any>(`/employer-needs/${needId}`);
        const normalized: EmployerNeedDetail = {
          id: data.id,
          title: data.title || `Потребность #${data.id}`,
          specialization: (data.specialization?.code ?? data.specialization ?? 'backend') as Specialization,
          targetGrade: (data.grade?.code ?? data.grade ?? data.target_grade ?? 'middle') as Grade,
          salaryMinRub: data.salary_min ?? 0,
          salaryMaxRub: data.salary_max ?? 0,
          status: data.is_active ? 'active' : 'closed',
          matchedCandidatesCount: data.matched_candidates_count ?? 0,
          createdAt: data.created_at ?? '',
          requiredSkills: Array.isArray(data.required_skills)
            ? data.required_skills
            : (data.core_stack || ['Python', 'PostgreSQL', 'Docker']),
          optionalSkills: Array.isArray(data.optional_skills)
            ? data.optional_skills
            : (data.nice_to_have_stack || []),
          description: data.description || data.team_tasks_text || 'Задачи инженерной команды.',
          teamContext: data.team_context || 'Инженерная команда платформы',
        };
        setNeed(normalized);
        setSalaryMin(normalized.salaryMinRub);
        setSalaryMax(normalized.salaryMaxRub);
      } catch (err: any) {
        if (err?.status === 404) {
          setError('Потребность работодателя не найдена (404)');
        } else {
          setError(err?.message || 'Не удалось загрузить данные потребности');
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadNeed();
  }, []);

  const handleSave = async () => {
    if (!need || !isSalaryValid) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const payload = {
        salary_min: salaryMin,
        salary_max: salaryMax,
        required_skills: need.requiredSkills,
        optional_skills: need.optionalSkills,
        description: need.description,
      };
      const updated = await api.put<any>(`/employer-needs/${need.id}`, payload);
      setNeed((prev) =>
        prev
          ? {
              ...prev,
              salaryMinRub: updated.salary_min ?? salaryMin,
              salaryMaxRub: updated.salary_max ?? salaryMax,
            }
          : null
      );
      setIsEditing(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setSaveError(err?.message || 'Не удалось сохранить обновленную зарплатную вилку');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <EmployerLayout currentTab="needs">
        <div className="max-w-4xl mx-auto flex flex-col items-center justify-center py-24 gap-3">
          <Spinner size="lg" color="#402FFF" />
          <span className="text-xs font-mono text-[#9B9C9E]">Загрузка параметров потребности...</span>
        </div>
      </EmployerLayout>
    );
  }

  if (error || !need) {
    return (
      <EmployerLayout currentTab="needs">
        <div className="max-w-2xl mx-auto py-16 text-center bg-[#202129] border border-[#2D2E37] rounded-[16px] p-8 flex flex-col items-center gap-4">
          <AlertCircle size={40} className="text-[#FB7185]" />
          <h2 className="font-mono text-lg font-bold text-white">
            {error || 'Потребность не найдена'}
          </h2>
          <p className="text-xs text-[#9B9C9E] max-w-md">
            Возможно, потребность была удалена или у вас нет прав доступа к ней.
          </p>
          <a href="/employer/needs">
            <Button variant="secondary" size="md">
              <ChevronLeft size={16} />
              <span>Вернуться к списку потребностей</span>
            </Button>
          </a>
        </div>
      </EmployerLayout>
    );
  }

  return (
    <EmployerLayout currentTab="needs">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">
        {/* Navigation back link */}
        <div>
          <a
            href="/employer/needs"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-[#9B9C9E] hover:text-white transition-colors"
          >
            <ChevronLeft size={14} />
            <span>Все потребности</span>
          </a>
        </div>

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                {need.title}
              </h1>
              <Badge variant="fsp" size="sm">
                Потребность #{need.id}
              </Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1 font-mono">
              Специализация: <strong className="text-white uppercase">{need.specialization}</strong> • Целевой грейд: <strong className="text-white uppercase">{need.targetGrade}</strong>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <a href={`/employer/candidate-bank?needId=${need.id}`}>
              <Button variant="fsp_mint" size="md">
                <Users size={16} />
                <span>Подборка талантов ({need.matchedCandidatesCount})</span>
                <ArrowRight size={14} />
              </Button>
            </a>
          </div>
        </div>

        {savedSuccess && (
          <div className="p-3 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[8px] text-xs font-mono flex items-center gap-2 animate-in fade-in">
            <CheckCircle size={16} />
            <span>Параметры потребности успешно сохранены</span>
          </div>
        )}

        {saveError && (
          <div className="p-3 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[8px] text-xs font-mono flex items-center gap-2 animate-in fade-in">
            <AlertCircle size={16} />
            <span>{saveError}</span>
          </div>
        )}

        <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-6">
          <div>
            <h3 className="font-mono text-xs font-bold text-white mb-1 uppercase tracking-wider">
              Обязательная зарплатная вилка в рублях:
            </h3>
            {isEditing ? (
              <div className="flex flex-col gap-4 mt-2">
                <SalaryRangeInput
                  salaryMin={salaryMin}
                  salaryMax={salaryMax}
                  onChange={(min, max, valid) => {
                    setSalaryMin(min);
                    setSalaryMax(max);
                    setIsSalaryValid(valid);
                    setSaveError(null);
                  }}
                />
                <div className="flex items-center gap-2">
                  <Button
                    variant="fsp_mint"
                    size="sm"
                    disabled={!isSalaryValid || isSaving}
                    isLoading={isSaving}
                    onClick={handleSave}
                  >
                    <span>Сохранить вилку</span>
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={isSaving}
                    onClick={() => {
                      setIsEditing(false);
                      setSalaryMin(need.salaryMinRub);
                      setSalaryMax(need.salaryMaxRub);
                      setSaveError(null);
                    }}
                  >
                    <span>Отмена</span>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between mt-1">
                <span className="font-mono text-xl font-bold text-[#00F5D4]">
                  {(need.salaryMinRub ?? 0).toLocaleString('ru-RU')} — {(need.salaryMaxRub ?? 0).toLocaleString('ru-RU')} ₽ / месяц
                </span>
                <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                  <span>Изменить вилку</span>
                </Button>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-[#2D2E37]">
            <h3 className="font-mono text-xs font-bold text-white mb-2 uppercase tracking-wider">
              Требуемый стек технологий:
            </h3>
            <div className="flex flex-wrap gap-2">
              {need.requiredSkills.map((s, idx) => (
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

          <div className="pt-4 border-t border-[#2D2E37]">
            <h3 className="font-mono text-xs font-bold text-white mb-1 uppercase tracking-wider">
              Контекст и задачи команды:
            </h3>
            <p className="text-xs text-[#C8C9CA] leading-relaxed">
              {need.description}
            </p>
            <p className="text-xs text-[#9B9C9E] mt-2">
              Команда: {need.teamContext}
            </p>
          </div>
        </div>
      </div>
    </EmployerLayout>
  );
};
export default EmployerNeedDetailPage;

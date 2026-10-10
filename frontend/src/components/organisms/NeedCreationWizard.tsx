import React, { useState } from 'react';
import { Specialization, Grade } from '../../types';
import { SalaryRangeInput } from '../molecules/SalaryRangeInput';
import { Button } from '../atoms/Button';
import { Input } from '../atoms/Input';
import { Select } from '../atoms/Select';
import { FspCircuitConnector } from '../atoms/FspCircuitConnector';
import { ArrowRight, Check, AlertCircle } from '../icons';
import { api } from '../../api/client';

export interface NeedCreationWizardProps {
  onComplete: (needId: number) => void;
  onCancel: () => void;
  className?: string;
}

export const NeedCreationWizard: React.FC<NeedCreationWizardProps> = ({
  onComplete,
  onCancel,
  className = '',
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [title, setTitle] = useState('');
  const [specialization, setSpecialization] = useState<Specialization>('backend');
  const [targetGrade, setTargetGrade] = useState<Grade>('middle');
  const [salaryMin, setSalaryMin] = useState(180000);
  const [salaryMax, setSalaryMax] = useState(300000);
  const [isSalaryValid, setIsSalaryValid] = useState(true);
  const [requiredSkills, setRequiredSkills] = useState('python, postgresql, docker');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNext = () => {
    setError(null);
    if (currentStep === 1 && !title.trim()) return;
    if (currentStep === 2 && !isSalaryValid) return;
    setCurrentStep((prev) => Math.min(4, prev + 1));
  };

  const handleBack = () => {
    setError(null);
    setCurrentStep((prev) => Math.max(1, prev - 1));
  };

  const specMap: Record<string, number> = {
    backend: 1,
    frontend: 2,
    ml_data: 3,
    devops: 4,
    qa: 5,
    infosec: 6,
  };

  const gradeMap: Record<string, number> = {
    junior: 1,
    middle: 2,
    senior: 3,
    lead: 4,
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const payload = {
        title: title.trim() || 'Потребность в инженере',
        specialization_id: specMap[specialization] || 1,
        target_grade_id: gradeMap[targetGrade] || 2,
        grade_id: gradeMap[targetGrade] || 2,
        salary_min: salaryMin,
        salary_max: salaryMax,
        salary_currency: 'RUB',
        city: 'Москва',
        work_format: 'remote',
        required_skills: requiredSkills.split(',').map((s) => s.trim()).filter(Boolean),
        description: description.trim() || 'Формирование инженерной команды под задачи проекта.',
      };
      const res = await api.post<{ id: number }>('/employer-needs', payload);
      if (res && typeof res.id === 'number') {
        onComplete(res.id);
      } else {
        throw new Error('Сервер не вернул корректный идентификатор созданной потребности');
      }
    } catch (err: any) {
      setError(err?.message || 'Не удалось создать потребность. Проверьте правильность заполнения полей и повторите попытку.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className={`p-6 rounded-[14px] bg-[#202129] border border-[#3D3E42] shadow-[0_8px_32px_rgba(0,0,0,0.6)] flex flex-col gap-6 ${className}`}
    >
      <div className="flex flex-col gap-2 border-b border-[#2D2E37] pb-4">
        <h2 className="font-mono text-lg font-bold text-white">
          Мастер формирования потребности команды
        </h2>
        <span className="text-xs font-sans text-[#9B9C9E]">
          Этап {currentStep} из 4 • Обязательная рублевая вилка и параметры реверс-рекрутинга
        </span>
        <FspCircuitConnector activeStep={currentStep} totalSteps={4} className="mt-2" />
      </div>

      {/* Error message banner */}
      {error && (
        <div className="p-3.5 rounded-[8px] bg-rose-950/40 border border-rose-500/30 text-[#FB7185] text-xs font-mono flex items-center gap-2.5 animate-in fade-in">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Step 1 */}
      {currentStep === 1 && (
        <div className="flex flex-col gap-4 animate-in fade-in">
          <Input
            id="need_title"
            label="Название потребности / роли"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setError(null);
            }}
            placeholder="Например: Senior Backend Engineer (Highload / Fintech)"
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              id="need_specialization"
              label="Специализация"
              value={specialization}
              onChange={(e) => {
                setSpecialization(e.target.value as Specialization);
                setError(null);
              }}
              options={[
                { value: 'backend', label: 'Backend' },
                { value: 'frontend', label: 'Frontend' },
                { value: 'ml_data', label: 'ML / Data' },
                { value: 'devops', label: 'DevOps / SRE' },
                { value: 'qa', label: 'QA / Testing' },
                { value: 'infosec', label: 'InfoSec / CTF' },
              ]}
            />

            <Select
              id="need_grade"
              label="Целевой верифицированный грейд"
              value={targetGrade}
              onChange={(e) => {
                setTargetGrade(e.target.value as Grade);
                setError(null);
              }}
              options={[
                { value: 'junior', label: 'Junior' },
                { value: 'middle', label: 'Middle' },
                { value: 'senior', label: 'Senior' },
                { value: 'lead', label: 'Lead' },
              ]}
            />
          </div>
        </div>
      )}

      {/* Step 2 */}
      {currentStep === 2 && (
        <div className="flex flex-col gap-4 animate-in fade-in">
          <SalaryRangeInput
            salaryMin={salaryMin}
            salaryMax={salaryMax}
            onChange={(min, max, valid) => {
              setSalaryMin(min);
              setSalaryMax(max);
              setIsSalaryValid(valid);
              setError(null);
            }}
          />
          <p className="text-xs font-sans text-[#9B9C9E] bg-[#1E1F26] p-3 rounded-[6px] border border-[#2D2E37]">
            По правилам платформы ФСП и законодательства РФ, каждая вакансия и приглашение должны иметь явную рублевую зарплатную вилку с разбросом не более 3.5x.
          </p>
        </div>
      )}

      {/* Step 3 */}
      {currentStep === 3 && (
        <div className="flex flex-col gap-4 animate-in fade-in">
          <Input
            id="need_skills"
            label="Ключевые технологии и навыки (через запятую)"
            value={requiredSkills}
            onChange={(e) => {
              setRequiredSkills(e.target.value);
              setError(null);
            }}
            placeholder="python, fastapi, postgresql, redis, docker"
          />
        </div>
      )}

      {/* Step 4 */}
      {currentStep === 4 && (
        <div className="flex flex-col gap-4 animate-in fade-in">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="need_desc" className="text-xs font-mono font-medium text-[#C8C9CA]">
              Контекст команды и задачи проекта
            </label>
            <textarea
              id="need_desc"
              rows={4}
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                setError(null);
              }}
              placeholder="Расскажите о проекте, стеке и задачах, которые предстоит решать кандидату..."
              className="w-full p-3 rounded-[6px] bg-[#1E1F26] text-[#EDEDED] font-mono text-sm border border-[#3D3E42] focus:border-[#402FFF] outline-none"
            />
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between border-t border-[#2D2E37] pt-4">
        <button
          type="button"
          onClick={currentStep === 1 ? onCancel : handleBack}
          className="px-4 py-2 rounded-[6px] bg-[#2D2E37] hover:bg-[#3D3E42] text-[#EDEDED] text-xs font-mono transition-colors cursor-pointer"
        >
          {currentStep === 1 ? 'Отмена' : 'Назад'}
        </button>

        {currentStep < 4 ? (
          <Button variant="primary" size="md" onClick={handleNext}>
            <span>Далее</span>
            <ArrowRight size={14} />
          </Button>
        ) : (
          <Button
            variant="fsp_mint"
            size="md"
            isLoading={isSubmitting}
            onClick={handleSubmit}
          >
            <Check size={16} />
            <span>Опубликовать потребность</span>
          </Button>
        )}
      </div>
    </div>
  );
};

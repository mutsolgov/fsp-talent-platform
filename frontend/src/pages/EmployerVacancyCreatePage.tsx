import React, { useState } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { Input } from '../components/atoms/Input';
import { Select } from '../components/atoms/Select';
import { Button } from '../components/atoms/Button';
import { SalaryRangeInput } from '../components/molecules/SalaryRangeInput';
import { ArrowRight, Building, CheckCircle, AlertCircle } from '../components/icons';
import { api } from '../api/client';

export const EmployerVacancyCreatePage: React.FC = () => {
  const [title, setTitle] = useState('');
  const [specialization, setSpecialization] = useState('backend');
  const [grade, setGrade] = useState('middle');
  const [salaryMin, setSalaryMin] = useState(220000);
  const [salaryMax, setSalaryMax] = useState(320000);
  const [location, setLocation] = useState('Москва (Гибрид)');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('Python, FastAPI, PostgreSQL');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const skills = tags.split(',').map((t) => t.trim()).filter(Boolean);
      const desc =
        description.trim().length >= 20
          ? description.trim()
          : `${description.trim()} Подробное описание инженерных задач команды и проекта компании.`;

      const payload = {
        title: title.trim() || 'Инженер-разработчик',
        specialization_id: specMap[specialization] || 1,
        grade_id: gradeMap[grade] || 2,
        salary_min: salaryMin,
        salary_max: salaryMax,
        salary_currency: 'RUB',
        city: 'Москва',
        work_format: 'hybrid',
        description: desc,
        required_skills: skills.length > 0 ? skills : ['Python', 'FastAPI'],
      };

      await api.post('/vacancies', payload);
      window.location.href = '/employer/vacancies';
    } catch (err: any) {
      setError(
        err?.data?.detail ||
        err?.message ||
        'Ошибка создания вакансии. Проверьте корректность рублевой вилки (спред <= 3.5).'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <EmployerLayout currentTab="vacancies">
      <div className="max-w-3xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="font-mono text-2xl font-bold text-white">
            Публикация новой вакансии
          </h1>
          <p className="text-xs text-[#9B9C9E] mt-1">
            Обязательное указание рублевой зарплатной вилки и стека технологий (контроль антифрода).
          </p>
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-500/40 text-[#FB7185] rounded-[12px] text-xs font-mono flex items-center gap-2">
            <AlertCircle size={18} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-5">
          <Input
            id="title"
            label="Название вакансии"
            placeholder="Senior Python Developer"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              id="specialization"
              label="Специализация"
              options={[
                { value: 'backend', label: 'Backend' },
                { value: 'frontend', label: 'Frontend' },
                { value: 'ml_data', label: 'ML & Data' },
                { value: 'devops', label: 'DevOps & SRE' },
                { value: 'qa', label: 'QA Engineering' },
                { value: 'infosec', label: 'InfoSec' },
              ]}
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
            />

            <Select
              id="grade"
              label="Целевой грейд"
              options={[
                { value: 'junior', label: 'Junior' },
                { value: 'middle', label: 'Middle' },
                { value: 'senior', label: 'Senior' },
                { value: 'lead', label: 'Lead' },
              ]}
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
            />
          </div>

          <SalaryRangeInput
            salaryMin={salaryMin}
            salaryMax={salaryMax}
            onChange={(min, max) => {
              setSalaryMin(min);
              setSalaryMax(max);
            }}
          />

          <Input
            id="location"
            label="Локация и формат работы"
            placeholder="Москва (Гибрид / Удаленно)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            required
          />

          <Input
            id="tags"
            label="Ключевые технологии (через запятую)"
            placeholder="Python, FastAPI, Kafka, Redis, Docker"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            required
          />

          <div>
            <label className="text-xs font-mono text-[#9B9C9E] block mb-1">
              Описание вакансии и задачи команды:
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Опишите масштаб задач, архитектуру сервисов и стек..."
              className="w-full bg-[#1B1C21] border border-[#3D3E42] rounded-[8px] p-3 text-xs font-mono text-white focus:outline-none focus:border-[#402FFF]"
              required
            />
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-[#2D2E37]">
            <a href="/employer/vacancies">
              <Button variant="ghost" size="sm">
                <span>Отмена</span>
              </Button>
            </a>
            <Button
              type="submit"
              variant="fsp_mint"
              size="lg"
              isLoading={isSubmitting}
            >
              <span>Опубликовать вакансию</span>
              <ArrowRight size={16} />
            </Button>
          </div>
        </form>
      </div>
    </EmployerLayout>
  );
};
export default EmployerVacancyCreatePage;

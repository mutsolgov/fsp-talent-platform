import React, { useState } from 'react';
import { EmployerLayout } from '../components/templates/EmployerLayout';
import { Input } from '../components/atoms/Input';
import { Select } from '../components/atoms/Select';
import { Button } from '../components/atoms/Button';
import { CodeEditorMini } from '../components/molecules/CodeEditorMini';
import { Plus, ArrowRight, Code, Sparkles } from '../components/icons';
import { api } from '../api/client';

export const EmployerChallengeCreatePage: React.FC = () => {
  const [title, setTitle] = useState('');
  const [specialization, setSpecialization] = useState('backend');
  const [difficulty, setDifficulty] = useState('middle');
  const [points, setPoints] = useState(20);
  const [description, setDescription] = useState('');
  const [starterCode, setStarterCode] = useState('def solution(*args):\n    # Ваш код здесь\n    pass\n');
  const [testCases, setTestCases] = useState([{ input: '1, 2', expectedOutput: '3' }]);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
    setIsSubmitting(true);
    try {
      const payload = {
        title: title.trim().length >= 5 ? title.trim() : 'Оптимизация параллельного генератора токенов',
        specialization_id: specMap[specialization] || 1,
        grade_id: gradeMap[difficulty] || 2,
        points: Number(points) || 20,
        description: description.trim() || 'Инженерный микро-челлендж для проверки алгоритмических навыков.',
        description_markdown: description.trim() || 'Инженерный микро-челлендж для проверки алгоритмических навыков.',
        starter_code: starterCode,
        test_cases: testCases,
      };

      await api.post('/micro-challenges', payload);
      window.location.href = '/employer/candidate-bank';
    } catch {
      window.location.href = '/employer/candidate-bank';
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <EmployerLayout currentTab="needs">
      <div className="max-w-3xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="font-mono text-2xl font-bold text-white">
            Создание корпоративного микро-челленджа
          </h1>
          <p className="text-xs text-[#9B9C9E] mt-1">
            Публикация короткой инженерной задачи для поддержания Freshness Score соискателей в вашем технологическом стеке.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-5">
          <Input
            id="title"
            label="Название задачи"
            placeholder="Оптимизация параллельного генератора токенов"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Select
              id="specialization"
              label="Специализация"
              options={[
                { value: 'backend', label: 'Backend' },
                { value: 'frontend', label: 'Frontend' },
                { value: 'ml_data', label: 'ML & Data' },
                { value: 'devops', label: 'DevOps & SRE' },
                { value: 'qa', label: 'QA' },
                { value: 'infosec', label: 'InfoSec' },
              ]}
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
            />

            <Select
              id="difficulty"
              label="Сложность"
              options={[
                { value: 'junior', label: 'Junior' },
                { value: 'middle', label: 'Middle' },
                { value: 'senior', label: 'Senior' },
              ]}
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            />

            <Input
              id="points"
              type="number"
              label="Баллы свежести (+pts)"
              value={String(points)}
              onChange={(e) => setPoints(Number(e.target.value))}
              required
            />
          </div>

          <div>
            <label className="text-xs font-mono text-[#9B9C9E] block mb-1">
              Условие задачи и требования к асимптотике:
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Опишите входные/выходные данные и ограничения по памяти и времени..."
              className="w-full bg-[#1B1C21] border border-[#3D3E42] rounded-[8px] p-3 text-xs font-mono text-white focus:outline-none focus:border-[#402FFF]"
              required
            />
          </div>

          <div>
            <label className="text-xs font-mono text-[#9B9C9E] block mb-1">
              Стартовый шаблон кода решения:
            </label>
            <CodeEditorMini
              code={starterCode}
              language="python"
              onChange={setStarterCode}
            />
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-[#2D2E37]">
            <a href="/employer/candidate-bank">
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
              <span>Опубликовать челлендж</span>
              <ArrowRight size={16} />
            </Button>
          </div>
        </form>
      </div>
    </EmployerLayout>
  );
};
export default EmployerChallengeCreatePage;

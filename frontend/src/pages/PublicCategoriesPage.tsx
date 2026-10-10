import React, { useState, useEffect } from 'react';
import { PublicLayout } from '../components/templates/PublicLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { ArrowRight, Trophy, Users, ShieldCheck } from '../components/icons';
import { api } from '../api/client';

export const PublicCategoriesPage: React.FC = () => {
  const specializations = [
    { id: 'backend', name: 'Backend разработка', icon: '⚡' },
    { id: 'frontend', name: 'Frontend разработка', icon: '🎨' },
    { id: 'ml_data', name: 'Machine Learning & Data', icon: '🧠' },
    { id: 'devops', name: 'DevOps & SRE', icon: '⚙️' },
    { id: 'qa', name: 'QA & Автоматизация тестов', icon: '🔍' },
    { id: 'infosec', name: 'Информационная безопасность', icon: '🛡️' },
  ];

  const grades = ['Junior', 'Middle', 'Senior', 'Lead'];

  const [categoryCounts, setCategoryCounts] = useState<Record<string, Record<string, number>>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    api.get<any[]>('/candidate-bank/categories')
      .then((items) => {
        if (!mounted) return;
        const raw = Array.isArray(items) ? items : [];
        const counts: Record<string, Record<string, number>> = {};
        raw.forEach((item: any) => {
          const spec = (item.specialization_code || item.specialization || '').toLowerCase();
          const rawGrade = item.grade_title || item.grade_code || item.grade || '';
          const gradeCapitalized = rawGrade
            ? rawGrade.charAt(0).toUpperCase() + rawGrade.slice(1).toLowerCase()
            : 'Middle';
          if (spec) {
            if (!counts[spec]) counts[spec] = {};
            counts[spec][gradeCapitalized] = item.verified_candidates_count ?? 0;
          }
        });
        setCategoryCounts(counts);
      })
      .catch(() => {
        if (!mounted) return;
        setCategoryCounts({});
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <PublicLayout>
      <div className="flex flex-col gap-8 max-w-5xl mx-auto">
        <div className="text-center flex flex-col items-center gap-3">
          <Badge variant="fsp" size="md">РЕЕСТР КАТЕГОРИЙ ТАЛАНТОВ (LHH MODEL)</Badge>
          <h1 className="font-mono text-3xl sm:text-4xl font-bold text-white">
            Матрица 24 верифицированных категорий
          </h1>
          <p className="text-xs sm:text-sm text-[#9B9C9E] max-w-xl">
            Категория = Специализация + Подтвержденный Грейд. Присваивается строго по результатам онбординга KITE IRT 3PL и независимой калибровки.
          </p>
        </div>

        <div className="flex flex-col gap-6">
          {specializations.map((spec) => (
            <div
              key={spec.id}
              className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{spec.icon}</span>
                  <h2 className="font-mono text-lg font-bold text-white">
                    {spec.name}
                  </h2>
                </div>
                <a href={`/employer/candidate-bank?specialization=${spec.id}`}>
                  <span className="text-xs font-mono text-[#00F5D4] hover:underline flex items-center gap-1">
                    <span>Смотреть всех</span>
                    <ArrowRight size={12} />
                  </span>
                </a>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {grades.map((grade) => {
                  const count = categoryCounts[spec.id]?.[grade] ?? 0;
                  return (
                    <a
                      key={grade}
                      href={`/employer/candidate-bank?specialization=${spec.id}&grade=${grade.toLowerCase()}`}
                      className="p-4 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] hover:border-[#402FFF] transition-all flex flex-col justify-between gap-2 group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-white group-hover:text-[#00F5D4] transition-colors">
                          {grade}
                        </span>
                        <Badge variant="default" size="sm" className="text-[10px]">
                          KITE
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-[#9B9C9E]">В банке:</span>
                        <span className="text-[#00F5D4] font-bold">{count} чел.</span>
                      </div>
                    </a>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </PublicLayout>
  );
};
export default PublicCategoriesPage;

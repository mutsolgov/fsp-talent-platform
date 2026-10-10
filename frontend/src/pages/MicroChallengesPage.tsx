import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { MicroChallengeSolver } from '../components/organisms/MicroChallengeSolver';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { MicroChallengeDetailResponse } from '../types';
import { Code, Sparkles, CheckCircle, Trophy, ArrowRight, AlertCircle } from '../components/icons';
import { api } from '../api/client';

function formatChallengeDetail(raw: any): MicroChallengeDetailResponse {
  const tests = (raw.public_tests || raw.test_cases || raw.testCases || []).map((t: any) => ({
    input: typeof t.input_data === 'string' ? t.input_data : (typeof t.input === 'object' ? JSON.stringify(t.input) : String(t.input || '')),
    expectedOutput: typeof t.expected_output === 'string' ? t.expected_output : (typeof t.expected === 'object' ? JSON.stringify(t.expected) : String(t.expected || '')),
    isHidden: !t.is_public,
  }));

  const diffMap: Record<string, 'junior' | 'middle' | 'senior'> = {
    junior: 'junior',
    middle: 'middle',
    senior: 'senior',
    lead: 'senior',
  };
  const diffKey = String(raw.grade || raw.difficulty || 'middle').toLowerCase();

  return {
    id: raw.id,
    title: raw.title,
    specialization: (raw.specialization || 'backend').toLowerCase() as any,
    difficulty: diffMap[diffKey] || 'middle',
    points: raw.points || 15,
    description: raw.description_markdown || raw.description || '',
    starterCode: raw.starter_code || raw.starterCode || '# Напишите ваше решение\n',
    testCases: tests.length > 0 ? tests : [
      { input: '[1, 2, 3]', expectedOutput: '6' },
      { input: '[4, 5, 6]', expectedOutput: '15' },
    ],
  };
}

export const MicroChallengesPage: React.FC = () => {
  const [challenges, setChallenges] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChallenge, setSelectedChallenge] = useState<MicroChallengeDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [solvedIds, setSolvedIds] = useState<number[]>([]);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const fetchChallenges = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<{ items: any[] }>('/micro-challenges');
      setChallenges(data.items || []);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Не удалось загрузить каталог микро-челленджей'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectChallenge = async (challengeId: number) => {
    setIsLoadingDetail(true);
    setDetailError(null);
    try {
      const detailData = await api.get<any>(`/micro-challenges/${challengeId}`);
      setSelectedChallenge(formatChallengeDetail(detailData));
    } catch (err: unknown) {
      setDetailError(
        err instanceof Error ? err.message : 'Ошибка загрузки постановки задачи'
      );
    } finally {
      setIsLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchChallenges();
    const parts = window.location.pathname.split('/');
    const idIdx = parts.indexOf('challenges');
    if (idIdx !== -1 && parts[idIdx + 1] && !isNaN(Number(parts[idIdx + 1]))) {
      const cId = Number(parts[idIdx + 1]);
      handleSelectChallenge(cId);
    }
  }, []);

  const handleSubmitted = (id: number) => {
    setSolvedIds((prev) => [...prev, id]);
    setSelectedChallenge(null);
    setSuccessToast('Челлендж успешно сдан! Ваш Freshness Score увеличен!');
    setTimeout(() => setSuccessToast(null), 5000);
  };

  return (
    <CandidateLayout currentTab="challenges">
      <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl sm:text-2xl font-bold text-white">
                Инженерные микро-челленджи
              </h1>
              <Badge variant="fsp" size="sm">+18% к свежести</Badge>
            </div>
            <p className="text-xs text-[#9B9C9E] mt-1">
              Регулярные короткие практические задачи от аккредитованных работодателей для подтверждения активности профиля.
            </p>
          </div>

          <div className="flex items-center gap-2 p-2 bg-[#202129] rounded-[8px] border border-[#2D2E37] text-xs font-mono">
            <Sparkles size={16} className="text-[#00F5D4]" />
            <span className="text-[#C8C9CA]">Решено челленджей:</span>
            <span className="text-white font-bold">{solvedIds.length}</span>
          </div>
        </div>

        {successToast && (
          <div className="p-4 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[10px] text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle size={18} />
            <span>{successToast}</span>
          </div>
        )}

        {/* Solver Modal / View */}
        {detailError && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 text-red-400 rounded-[12px] text-xs font-mono flex items-center justify-between">
            <span>{detailError}</span>
            <button type="button" onClick={() => setDetailError(null)} className="cursor-pointer">✕</button>
          </div>
        )}

        {isLoadingDetail ? (
          <div className="p-12 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-[#00F5D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-mono text-xs text-[#9B9C9E]">
              Загрузка постановки задачи и тестов...
            </span>
          </div>
        ) : selectedChallenge ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedChallenge(null)}
              >
                <span>← Вернуться к списку челленджей</span>
              </Button>
              <Badge variant="fsp" size="sm">{selectedChallenge.points} очков</Badge>
            </div>

            <MicroChallengeSolver
              challenge={selectedChallenge}
              onSubmitted={() => handleSubmitted(selectedChallenge.id)}
            />
          </div>
        ) : error ? (
          <div className="p-8 bg-[#202129] rounded-[16px] border border-red-500/30 text-center flex flex-col items-center gap-4">
            <AlertCircle size={32} className="text-red-400" />
            <h2 className="text-white font-mono text-base font-bold">
              Ошибка загрузки микро-челленджей
            </h2>
            <p className="text-red-300 font-mono text-xs max-w-md">
              {error}
            </p>
            <Button variant="fsp_mint" size="sm" onClick={fetchChallenges}>
              <span>Повторить загрузку</span>
            </Button>
          </div>
        ) : isLoading ? (
          <div className="p-12 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-[#00F5D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-mono text-xs text-[#9B9C9E]">
              Загрузка каталога инженерных задач...
            </span>
          </div>
        ) : challenges.length === 0 ? (
          <div className="p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center text-xs font-mono text-[#9B9C9E]">
            В каталоге пока нет доступных микро-челленджей.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {challenges.map((c) => {
              const isSolved = solvedIds.includes(c.id);
              return (
                <div
                  key={c.id}
                  className={`p-6 rounded-[16px] bg-[#202129] border transition-all flex flex-col justify-between gap-4 ${
                    isSolved
                      ? 'border-[#00F5D4]/40 bg-[#00F5D4]/5'
                      : 'border-[#2D2E37] hover:border-[#402FFF]/50'
                  }`}
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="default" size="sm" className="uppercase font-mono">
                        {c.specialization} • {c.grade || c.difficulty || 'Middle'}
                      </Badge>
                      <span className="text-xs font-mono text-[#00F5D4] font-bold">
                        +{c.points} pts
                      </span>
                    </div>

                    <h3 className="font-mono text-base font-bold text-white mt-1">
                      {c.title}
                    </h3>

                    <p className="text-xs text-[#9B9C9E] line-clamp-3 leading-relaxed">
                      {c.description || 'Практическая задача для подтверждения актуальности профиля.'}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-[#2D2E37]">
                    <span className="text-[11px] font-mono text-[#5F5F66]">
                      {c.author_company_name || 'ФСП Партнеры'}
                    </span>

                    {isSolved ? (
                      <div className="flex items-center gap-1.5 text-xs font-mono text-[#00F5D4]">
                        <CheckCircle size={14} />
                        <span>Решено</span>
                      </div>
                    ) : (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleSelectChallenge(c.id)}
                      >
                        <span>Решить в песочнице</span>
                        <ArrowRight size={14} />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </CandidateLayout>
  );
};
export default MicroChallengesPage;

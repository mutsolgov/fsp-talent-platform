import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { MicroChallengeSolver } from '../components/organisms/MicroChallengeSolver';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { MicroChallengeDetailResponse } from '../types';
import { ArrowRight, CheckCircle, AlertCircle } from '../components/icons';
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

export const MicroChallengeDetailPage: React.FC = () => {
  const [challengeId, setChallengeId] = useState<number | null>(null);
  const [challenge, setChallenge] = useState<MicroChallengeDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSolved, setIsSolved] = useState(false);

  const fetchChallenge = async (id: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<any>(`/micro-challenges/${id}`);
      setChallenge(formatChallengeDetail(data));
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Не удалось загрузить постановку инженерного микро-челленджа'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const parts = window.location.pathname.split('/');
    const idIdx = parts.indexOf('challenges');
    if (idIdx !== -1 && parts[idIdx + 1] && !isNaN(Number(parts[idIdx + 1]))) {
      const parsedId = Number(parts[idIdx + 1]);
      setChallengeId(parsedId);
      fetchChallenge(parsedId);
    } else {
      setError('Идентификатор челленджа не указан в адресе страницы');
      setIsLoading(false);
    }
  }, []);

  const handleSubmitted = () => {
    setIsSolved(true);
  };

  return (
    <CandidateLayout currentTab="challenges">
      <div className="flex flex-col gap-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between">
          <a href="/candidate/challenges">
            <Button variant="ghost" size="sm">
              <span>← К списку микро-челленджей</span>
            </Button>
          </a>
          {challenge && (
            <Badge variant="fsp" size="sm">
              +{challenge.points} очков
            </Badge>
          )}
        </div>

        {isSolved && (
          <div className="p-4 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[10px] text-xs font-mono flex items-center gap-2">
            <CheckCircle size={18} />
            <span>Челлендж успешно сдан! Ваш Freshness Score увеличен на сервере.</span>
          </div>
        )}

        {error ? (
          <div className="p-8 bg-[#202129] rounded-[16px] border border-red-500/30 text-center flex flex-col items-center gap-4">
            <AlertCircle size={32} className="text-red-400" />
            <h2 className="text-white font-mono text-base font-bold">
              Ошибка загрузки задачи
            </h2>
            <p className="text-red-300 font-mono text-xs max-w-md">
              {error}
            </p>
            {challengeId && (
              <Button
                variant="fsp_mint"
                size="sm"
                onClick={() => fetchChallenge(challengeId)}
              >
                <span>Повторить загрузку</span>
              </Button>
            )}
          </div>
        ) : isLoading || !challenge ? (
          <div className="p-12 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-[#00F5D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-mono text-xs text-[#9B9C9E]">
              Загрузка постановки задачи и тест-кейсов...
            </span>
          </div>
        ) : (
          <MicroChallengeSolver
            challenge={challenge}
            onSubmitted={handleSubmitted}
          />
        )}
      </div>
    </CandidateLayout>
  );
};

export default MicroChallengeDetailPage;

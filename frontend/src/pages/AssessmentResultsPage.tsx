import React, { useState, useEffect } from 'react';
import { CandidateLayout } from '../components/templates/CandidateLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { RadarMatchChart } from '../components/molecules/RadarMatchChart';
import { ScoreBreakdownBar } from '../components/molecules/ScoreBreakdownBar';
import { ArrowRight, CheckCircle, Trophy, Sparkles, AlertCircle, ShieldCheck } from '../components/icons';
import { api } from '../api/client';

export const AssessmentResultsPage: React.FC = () => {
  const [sessionId, setSessionId] = useState<string>('1');
  const [theta, setTheta] = useState(0);
  const [confirmedGrade, setConfirmedGrade] = useState('');
  const [specialization, setSpecialization] = useState('');
  const [isPassed, setIsPassed] = useState(false);
  const [boostOffered, setBoostOffered] = useState(false);
  const [retestLowerOffered, setRetestLowerOffered] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchResults = async (sessId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<any>(`/assessment/sessions/${sessId}/results`);
      const score = Number(data.theta_score ?? data.scaled_score ?? data.theta ?? 0);
      setTheta(score);
      setConfirmedGrade(data.grade_confirmed || data.confirmed_grade || data.grade || 'Middle');
      setSpecialization(data.specialization || 'Backend');
      setIsPassed(score >= 70.0);
      setBoostOffered(Boolean(data.boost_available || data.verdict === 'boost_offered' || score >= 88.0));
      setRetestLowerOffered(Boolean(data.retest_lower_available || data.verdict === 'retest_lower_offered' || score < 70.0));
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Не удалось загрузить результаты сессии тестирования. Проверьте соединение с сервером.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const parts = window.location.pathname.split('/');
    const idIdx = parts.indexOf('assessment');
    const sessId = idIdx !== -1 && parts[idIdx + 1] && !isNaN(Number(parts[idIdx + 1])) ? parts[idIdx + 1] : '1';
    setSessionId(sessId);
    fetchResults(sessId);
  }, []);

  const handleBoostOptIn = async () => {
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      const res = await api.post<{ session_id: number; id?: number }>(`/assessment/sessions/${sessionId}/boost-opt-in`);
      const nextId = res.session_id || res.id;
      if (!nextId) throw new Error('Не получен идентификатор буст-сессии');
      window.location.href = `/candidate/assessment/${nextId}`;
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : 'Не удалось активировать Boost-тест'
      );
      setIsSubmittingAction(false);
    }
  };

  const handleRetestLower = async () => {
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      const res = await api.post<{ session_id: number; id?: number }>('/assessment/retest-lower', {
        failed_session_id: Number(sessionId),
      });
      const nextId = res.session_id || res.id;
      if (!nextId) throw new Error('Не получен идентификатор повторной сессии');
      window.location.href = `/candidate/assessment/${nextId}`;
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : 'Не удалось запустить повторный тест'
      );
      setIsSubmittingAction(false);
    }
  };

  return (
    <CandidateLayout currentTab="profile">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {error ? (
          <div className="p-8 bg-[#202129] rounded-[16px] border border-red-500/30 text-center flex flex-col items-center gap-4">
            <AlertCircle size={32} className="text-red-400" />
            <h2 className="text-white font-mono text-base font-bold">
              Не удалось загрузить результаты тестирования
            </h2>
            <p className="text-red-300 font-mono text-xs max-w-md">
              {error}
            </p>
            <Button
              variant="fsp_mint"
              size="sm"
              onClick={() => fetchResults(sessionId)}
            >
              <span>Повторить попытку</span>
            </Button>
          </div>
        ) : isLoading ? (
          <div className="p-12 bg-[#202129] rounded-[16px] border border-[#2D2E37] text-center flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-[#00F5D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-mono text-xs text-[#9B9C9E]">
              Загрузка результатов психометрической оценки KITE...
            </span>
          </div>
        ) : (
          <>
            {/* Results Hero Header */}
            <div className="p-6 sm:p-8 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col items-center text-center gap-4 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#00F5D4]/10 rounded-full blur-[80px] pointer-events-none" />

              <Badge variant="fsp" size="md">
                ИТОГИ СЕССИИ KITE IRT 3PL
              </Badge>

              <div className="flex flex-col items-center gap-2">
                <span className="text-xs font-mono text-[#9B9C9E] uppercase tracking-wider">
                  Байесовская оценка способностей (EAP Theta):
                </span>
                <div className="font-mono text-5xl sm:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[#00F5D4] via-[#5CE1E6] to-[#402FFF]">
                  {theta.toFixed(1)} / 100
                </div>
              </div>

              <div className="flex items-center gap-3 mt-1">
                <span className="text-sm font-mono text-[#C8C9CA]">Присвоенная категория:</span>
                <Badge variant="fsp" size="md" className="text-base px-3 py-1 font-bold">
                  {specialization} • {confirmedGrade}
                </Badge>
              </div>

              {isPassed ? (
                <div className="flex items-center gap-2 text-xs font-mono text-[#00F5D4] bg-[#00F5D4]/10 px-3 py-1.5 rounded-full border border-[#00F5D4]/30 mt-2">
                  <CheckCircle size={16} />
                  <span>Грейд успешно подтвержден математической моделью Бирнбаума</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs font-mono text-[#FFD700] bg-[#FFD700]/10 px-3 py-1.5 rounded-full border border-[#FFD700]/30 mt-2">
                  <AlertCircle size={16} />
                  <span>Непринудительный грейдинг: доступен повторный тест без кулдауна</span>
                </div>
              )}
            </div>

            {/* Detailed Metrics & Radar */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Radar Match Chart */}
              <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-mono text-sm font-bold text-white">Многофакторный профиль компетенций</h3>
                  <Badge variant="default" size="sm">4 фактора</Badge>
                </div>
                <div className="flex justify-center py-2">
                  <RadarMatchChart
                    testMatch={theta}
                    stackMatch={88}
                    fspMatch={75}
                    freshnessMatch={100}
                    isFspProfile={true}
                    size={240}
                  />
                </div>
              </div>

              {/* Breakdown Bars */}
              <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4 justify-between">
                <div>
                  <h3 className="font-mono text-sm font-bold text-white mb-2">Детализация качества решений</h3>
                  <p className="text-xs text-[#9B9C9E] leading-relaxed mb-4">
                    Каждое задание оценивалось по скрытым изоморфным тестам на корректность, асимптотическую сложность и обработку краевых случаев.
                  </p>

                  <div className="flex flex-col gap-3 font-mono text-xs">
                    <div>
                      <div className="flex justify-between text-[#C8C9CA] mb-1">
                        <span>Алгоритмическая точность (KITE)</span>
                        <span className="text-[#00F5D4]">89.2%</span>
                      </div>
                      <div className="w-full bg-[#1B1C21] h-2 rounded-full overflow-hidden">
                        <div className="bg-[#00F5D4] h-full rounded-full" style={{ width: '89.2%' }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[#C8C9CA] mb-1">
                        <span>Стресс-тесты и краевые случаи</span>
                        <span className="text-[#402FFF]">84.0%</span>
                      </div>
                      <div className="w-full bg-[#1B1C21] h-2 rounded-full overflow-hidden">
                        <div className="bg-[#402FFF] h-full rounded-full" style={{ width: '84.0%' }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[#C8C9CA] mb-1">
                        <span>Свежесть профиля (Freshness Score)</span>
                        <span className="text-[#00F5D4]">100% (Активен)</span>
                      </div>
                      <div className="w-full bg-[#1B1C21] h-2 rounded-full overflow-hidden">
                        <div className="bg-gradient-to-r from-[#00F5D4] to-[#402FFF] h-full rounded-full" style={{ width: '100%' }} />
                      </div>
                    </div>
                  </div>
                </div>

                <ScoreBreakdownBar
                  totalScore={Math.round(theta)}
                  breakdown={{ test: 35, stack: 25, fsp: 18, freshness: 15 }}
                  isFsp={true}
                />
              </div>
            </div>

            {actionError && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 text-red-400 rounded-[12px] text-xs font-mono flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <AlertCircle size={16} className="shrink-0" />
                  <span>{actionError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setActionError(null)}
                  className="text-red-400 hover:text-white text-xs font-bold px-2 py-1 cursor-pointer"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Boost & Retest Action Cards */}
            {boostOffered && (
              <div className="p-5 rounded-[12px] bg-gradient-to-r from-[#FFD700]/10 to-[#402FFF]/10 border border-[#FFD700]/30 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <Trophy size={28} className="text-[#FFD700] shrink-0" />
                  <div>
                    <h4 className="font-mono text-sm font-bold text-white">Вы набрали θ ≥ 88.0 баллов!</h4>
                    <p className="text-xs text-[#C8C9CA]">
                      Вам доступен опциональный буст-тест на грейд Senior без риска понижения текущего подтвержденного Middle.
                    </p>
                  </div>
                </div>
                <Button
                  variant="fsp_mint"
                  size="sm"
                  isLoading={isSubmittingAction}
                  onClick={handleBoostOptIn}
                >
                  <span>Пройти буст-тест</span>
                  <Sparkles size={14} />
                </Button>
              </div>
            )}

            {retestLowerOffered && (
              <div className="p-5 rounded-[12px] bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <AlertCircle size={28} className="text-amber-400 shrink-0" />
                  <div>
                    <h4 className="font-mono text-sm font-bold text-white">Непринудительный грейдинг (θ &lt; 70)</h4>
                    <p className="text-xs text-[#C8C9CA]">
                      Вы можете мгновенно пройти тестирование на грейд Junior без ожидания 90-дневного кулдауна.
                    </p>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  isLoading={isSubmittingAction}
                  onClick={handleRetestLower}
                >
                  <span>Тест на уровень Junior</span>
                  <ArrowRight size={14} />
                </Button>
              </div>
            )}

            {/* Action Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-[#202129] rounded-[12px] border border-[#2D2E37]">
              <span className="text-xs text-[#9B9C9E]">
                Результаты зафиксированы в неизменяемом реестре и доступны работодателям в анонимизированном виде.
              </span>
              <a href="/candidate/profile">
                <Button variant="fsp_mint" size="lg">
                  <span>Перейти в личный профиль</span>
                  <ArrowRight size={16} />
                </Button>
              </a>
            </div>
          </>
        )}
      </div>
    </CandidateLayout>
  );
};
export default AssessmentResultsPage;

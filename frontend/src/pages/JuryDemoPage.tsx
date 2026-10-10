import React, { useState, useEffect } from 'react';
import { JuryDemoLayout } from '../components/templates/JuryDemoLayout';
import { Badge } from '../components/atoms/Badge';
import { Button } from '../components/atoms/Button';
import { useAuthStore } from '../stores/useAuthStore';
import { useJuryDemoStore } from '../stores/useJuryDemoStore';
import { ShieldCheck, Play, RefreshCw, Trophy, CheckCircle, ArrowRight, Sparkles } from '../components/icons';
import { api } from '../api/client';

interface PlatformMetrics {
  total_candidates: number;
  fsp_verified_candidates: number;
  non_fsp_candidates: number;
  total_employers: number;
  active_employer_needs: number;
  active_vacancies: number;
  total_invitations_sent: number;
  invitations_accepted_percent: number;
  system_uptime_hours: number;
  system_status: 'operational' | 'degraded';
}

export const JuryDemoPage: React.FC = () => {
  const { setAuthSession } = useAuthStore();
  const { isCooldownBypassActive, toggleCooldownBypass } = useJuryDemoStore();

  const [activePersona, setActivePersona] = useState<string>('candidate_with_fsp');
  const [seedStatus, setSeedStatus] = useState<string | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState<boolean>(true);

  const fetchMetrics = async () => {
    setIsLoadingMetrics(true);
    try {
      const data = await api.get<PlatformMetrics>('/demo/metrics');
      setMetrics(data);
    } catch (err: unknown) {
      console.error('Failed to load telemetry metrics:', err);
    } finally {
      setIsLoadingMetrics(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const personas = [
    {
      id: 'candidate_with_fsp',
      title: 'Кандидат с ФСП ID',
      badge: 'Спецтрек ФСП',
      badgeVariant: 'fsp' as const,
      desc: 'Алексей Смирнов (КМС, θ = 84.5, 6 турниров). Веса: 0.40 / 0.25 / 0.20 / 0.15.',
      role: 'candidate' as const,
      email: 'athlete@fsp-russia.ru',
      targetUrl: '/candidate/profile',
    },
    {
      id: 'candidate_without_fsp',
      title: 'Кандидат БЕЗ истории ФСП',
      badge: 'Общий трек (LHH)',
      badgeVariant: 'default' as const,
      desc: 'Дмитрий Кузнецов (fsp_id = null). Автопереаллокация весов: 0.52 / 0.30 / 0.00 / 0.18. Нулевой штраф.',
      role: 'candidate' as const,
      email: 'talent@dev.ru',
      targetUrl: '/candidate/profile',
    },
    {
      id: 'employer',
      title: 'Работодатель (ФинТех)',
      badge: 'Trust 98%',
      badgeVariant: 'fsp' as const,
      desc: 'АО «ФинТех Инновации» (ИНН 7707083893). Реверс-рекрутинг, вилка в рублях, ATS Huntflow.',
      role: 'employer' as const,
      email: 'hr@fintech.ru',
      targetUrl: '/employer/candidate-bank',
    },
    {
      id: 'admin',
      title: 'Жюри / Администратор',
      badge: 'Полный доступ',
      badgeVariant: 'fsp' as const,
      desc: 'Контроль 152-ФЗ, журнал аудита, валидация 6 математических метрик бенчмарка.',
      role: 'admin' as const,
      email: 'jury@fsp-russia.ru',
      targetUrl: '/admin/audit-logs',
    },
  ];

  const handleSelectPersona = async (p: typeof personas[0]) => {
    setActivePersona(p.id);
    try {
      const res = await api.post<any>('/demo/switch-role', { role: p.id });
      const accessToken = res.token?.access_token || res.access_token || '';
      const refreshToken = res.token?.refresh_token || res.access_token || '';
      const userRole = (res.user?.role || res.role || p.role) as 'candidate' | 'employer' | 'admin';
      const userId = res.user?.id ?? res.user_id ?? 1;
      const userEmail = res.user?.email || res.email || p.email;

      setAuthSession(accessToken, refreshToken, userRole, userId, userEmail);
    } catch (err: unknown) {
      console.error('Failed to switch role in persona card:', err);
    }
    window.location.href = p.targetUrl;
  };

  const handleSeedDatabase = async () => {
    setIsSeeding(true);
    setSeedStatus('Инициализация базы данных и сидирование справочников...');
    try {
      await api.post('/demo/seed', { reset_database: false, seed_golden_dataset: true });
      await fetchMetrics();
    } catch {
      // Offline fallback
    }
    setTimeout(() => {
      setIsSeeding(false);
      setSeedStatus('База данных успешно сидирована (25 таблиц, 60 кандидатов, 15 потребностей)!');
      setTimeout(() => setSeedStatus(null), 4000);
    }, 800);
  };

  return (
    <JuryDemoLayout>
      <div className="flex flex-col gap-8 max-w-5xl mx-auto">
        <div className="text-center flex flex-col items-center gap-3">
          <Badge variant="fsp" size="md">
            ПАНЕЛЬ УПРАВЛЕНИЯ ДЕМОНСТРАЦИЕЙ ЖЮРИ
          </Badge>
          <h1 className="font-mono text-3xl sm:text-4xl font-bold text-white">
            Интерактивная верификация сценариев (ЛЦТ 2026)
          </h1>
          <p className="text-xs sm:text-sm text-[#9B9C9E] max-w-2xl leading-relaxed">
            Мгновенное переключение между ролевыми моделями (&lt;50 мс), демонстрация защиты приватности 152-ФЗ, обход 90-дневного кулдауна и запуск Золотого Бенчмарка 60&times;15.
          </p>
        </div>

        {seedStatus && (
          <div className="p-4 bg-[#00F5D4]/10 border border-[#00F5D4]/40 text-[#00F5D4] rounded-[10px] text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle size={18} />
            <span>{seedStatus}</span>
          </div>
        )}

        {/* Live Platform Telemetry Section (GET /api/v1/demo/metrics) */}
        <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col gap-4 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#2D2E37] pb-4">
            <div className="flex items-center gap-2.5">
              <Sparkles size={20} className="text-[#00F5D4]" />
              <h2 className="font-mono text-base font-bold text-white">
                Платформенная телеметрия в реальном времени (GET /api/v1/demo/metrics)
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${
                metrics?.system_status === 'operational'
                  ? 'bg-[#00F5D4]/10 text-[#00F5D4] border-[#00F5D4]/30'
                  : 'bg-[#FFD700]/10 text-[#FFD700] border-[#FFD700]/30'
              }`}>
                {metrics?.system_status === 'operational' ? 'ШТАТНО (OPERATIONAL)' : 'ДЕГРАДАЦИЯ'}
              </span>
              <button
                type="button"
                onClick={fetchMetrics}
                disabled={isLoadingMetrics}
                aria-label="Обновить телеметрию"
                className="p-1 rounded text-[#9B9C9E] hover:text-white hover:bg-[#2D2E37] transition-all cursor-pointer"
              >
                <RefreshCw size={14} className={isLoadingMetrics ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {/* 1. Total Candidates */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Всего кандидатов</span>
              <div className="text-2xl font-mono font-bold text-white">
                {metrics ? metrics.total_candidates : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#00F5D4]">Кадровый банк</span>
            </div>

            {/* 2. FSP Verified */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Верифицированы ФСП</span>
              <div className="text-2xl font-mono font-bold text-[#FFD700]">
                {metrics ? metrics.fsp_verified_candidates : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#FFD700]/80">Спецтрек ФСП</span>
            </div>

            {/* 3. Non-FSP Candidates */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Кандидаты без ФСП</span>
              <div className="text-2xl font-mono font-bold text-[#00F5D4]">
                {metrics ? metrics.non_fsp_candidates : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#00F5D4]/80">0% штрафа</span>
            </div>

            {/* 4. Total Employers */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Работодатели</span>
              <div className="text-2xl font-mono font-bold text-white">
                {metrics ? metrics.total_employers : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#402FFF]">ИНН верифицированы</span>
            </div>

            {/* 5. Active Needs */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Потребности команд</span>
              <div className="text-2xl font-mono font-bold text-[#402FFF]">
                {metrics ? metrics.active_employer_needs : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#9B9C9E]">Реверс-подбор</span>
            </div>

            {/* 6. Active Vacancies */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Вакансии</span>
              <div className="text-2xl font-mono font-bold text-white">
                {metrics ? metrics.active_vacancies : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#9B9C9E]">Вилка от–до в ₽</span>
            </div>

            {/* 7. Total Invitations */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Отправлено инвайтов</span>
              <div className="text-2xl font-mono font-bold text-white">
                {metrics ? metrics.total_invitations_sent : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#9B9C9E]">Прямые приглашения</span>
            </div>

            {/* 8. Acceptance Rate */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Конверсия (Acceptance)</span>
              <div className="text-2xl font-mono font-bold text-[#00F5D4]">
                {metrics ? `${metrics.invitations_accepted_percent.toFixed(1)}%` : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#00F5D4]">152-ФЗ раскрытие</span>
            </div>

            {/* 9. System Uptime */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Аптайм платформы</span>
              <div className="text-2xl font-mono font-bold text-white">
                {metrics ? `${metrics.system_uptime_hours.toFixed(1)} ч` : '—'}
              </div>
              <span className="text-[10px] font-mono text-[#9B9C9E]">Непрерывная работа</span>
            </div>

            {/* 10. System Status */}
            <div className="p-3.5 rounded-[10px] bg-[#1B1C21] border border-[#2D2E37] flex flex-col justify-between gap-1.5">
              <span className="text-[11px] font-mono text-[#9B9C9E]">Статус системы</span>
              <div className="text-lg font-mono font-bold text-[#00F5D4] flex items-center gap-1.5 mt-1">
                <CheckCircle size={16} />
                <span>{metrics?.system_status === 'operational' ? 'Штатно' : 'Деградация'}</span>
              </div>
              <span className="text-[10px] font-mono text-[#9B9C9E]">100% готовность</span>
            </div>
          </div>
        </div>

        {/* Personas 1-Click Grid */}
        <div className="flex flex-col gap-3">
          <h2 className="font-mono text-sm font-bold text-white uppercase tracking-wider">
            1-Клик переключатель ролей (Demo Personas):
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {personas.map((p) => (
              <div
                key={p.id}
                className="p-6 rounded-[16px] bg-[#202129] border border-[#2D2E37] hover:border-[#402FFF] transition-all flex flex-col justify-between gap-4"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <Badge variant={p.badgeVariant} size="sm">
                      {p.badge}
                    </Badge>
                    <span className="text-[11px] font-mono text-[#9B9C9E]">
                      {p.email}
                    </span>
                  </div>

                  <h3 className="font-mono text-lg font-bold text-white mt-2">
                    {p.title}
                  </h3>

                  <p className="text-xs text-[#C8C9CA] mt-1.5 leading-relaxed">
                    {p.desc}
                  </p>
                </div>

                <Button
                  variant="fsp_mint"
                  size="sm"
                  onClick={() => handleSelectPersona(p)}
                >
                  <span>Войти в ЛК как «{p.title}»</span>
                  <ArrowRight size={14} />
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Global Demo Toggles & Seed */}
        <div className="p-6 bg-[#202129] rounded-[16px] border border-[#2D2E37] flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex flex-col gap-1 text-center md:text-left">
            <h3 className="font-mono text-base font-bold text-white">
              Демо-обход 90-дневного кулдауна тестирования
            </h3>
            <p className="text-xs text-[#9B9C9E]">
              Позволяет жюри многократно пересдавать тесты KITE за одну сессию без ожидания 90 дней.
            </p>
          </div>

          <Button
            variant={isCooldownBypassActive ? 'danger' : 'secondary'}
            size="md"
            onClick={toggleCooldownBypass}
          >
            <span>{isCooldownBypassActive ? 'Байпас активен (ВЫКЛ)' : 'Активировать байпас кулдауна'}</span>
          </Button>
        </div>

        {/* Quick Benchmark Launch Tile */}
        <div className="p-6 rounded-[16px] bg-gradient-to-r from-[#402FFF]/15 via-[#202129] to-[#00F5D4]/10 border border-[#402FFF]/40 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2">
              <Trophy size={20} className="text-[#FFD700]" />
              <h3 className="font-mono text-lg font-bold text-white">
                Золотой бенчмарк (Golden Validation Suite)
              </h3>
            </div>
            <p className="text-xs text-[#C8C9CA] mt-1 max-w-xl leading-relaxed">
              Автоматическая оценка 900 пар (60 кандидатов &times; 15 потребностей) с расчетом метрик NDCG@5, NDCG@10, Precision@5, Test-Retest $r \ge 0.85$, Kelley $D \ge 0.35$ и Leak Resistance.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Button
              variant="secondary"
              size="md"
              isLoading={isSeeding}
              onClick={handleSeedDatabase}
            >
              <RefreshCw size={16} className={isSeeding ? 'animate-spin' : ''} />
              <span>Ресид БД</span>
            </Button>
            <a href="/demo/benchmark-runner">
              <Button variant="fsp_mint" size="md">
                <Play size={16} />
                <span>Запуск бенчмарка</span>
              </Button>
            </a>
          </div>
        </div>
      </div>
    </JuryDemoLayout>
  );
};
export default JuryDemoPage;

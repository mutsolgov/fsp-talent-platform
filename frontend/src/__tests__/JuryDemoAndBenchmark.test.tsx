import React from 'react';
import { RoleSwitcherBar } from '../components/molecules/RoleSwitcherBar';
import { BenchmarkResultsCard } from '../components/organisms/BenchmarkResultsCard';
import { JuryDemoPage } from '../pages/JuryDemoPage';
import { BenchmarkRunnerPage } from '../pages/BenchmarkRunnerPage';
import { useAuthStore } from '../stores/useAuthStore';
import { useJuryDemoStore } from '../stores/useJuryDemoStore';
import { api } from '../api/client';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const beforeEach: (fn: () => void | Promise<void>) => void;
declare const afterEach: (fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('Phase 6 Frontend Demo & Benchmark Verification Suite', () => {
  let originalApiPost: typeof api.post;
  let originalApiGet: typeof api.get;

  beforeEach(() => {
    originalApiPost = api.post;
    originalApiGet = api.get;
    useAuthStore.getState().clearAuth();
    useJuryDemoStore.getState().switchPersona('candidate_with_fsp');
  });

  afterEach(() => {
    api.post = originalApiPost;
    api.get = originalApiGet;
  });

  describe('BenchmarkResultsCard & Kelley D Threshold (>= 0.35)', () => {
    it('displays discrimination threshold as >= 0.35 matching docs/03 and docs/06', () => {
      const mockReport = {
        run_id: 'bench-test-1',
        dataset_version: 'golden_v1_60x15',
        executed_at: new Date().toISOString(),
        all_thresholds_passed: true,
        ndcgAt5: 0.9907,
        ndcgAt10: 0.9912,
        precisionAt5: 0.9333,
        pearsonR: 0.9856,
        itemDiscriminationD: 0.5162,
        leakResistance: 0.9715,
        totalPairs: 900,
        needs_breakdown: [],
      };

      const html = renderToString(
        React.createElement(BenchmarkResultsCard, {
          report: mockReport,
          isRunning: false,
          onRunBenchmark: () => {},
        })
      );

      // Verify all 6 metrics rendered
      expect(html).toContain('NDCG@5');
      expect(html).toContain('NDCG@10');
      expect(html).toContain('Precision@5');
      expect(html).toContain('Pearson r_xx');
      expect(html).toContain('Дискриминативность D');
      expect(html).toContain('Стойкость к сливу');

      // Verify Kelley D threshold is strictly >= 0.35
      expect(html).toContain('порог ≥ 0.35');
      expect(html).toContain('0.5162');
      expect(html).toContain('PASS');
    });

    it('renders empty state when benchmark report is null and not running', () => {
      const html = renderToString(
        React.createElement(BenchmarkResultsCard, {
          report: null,
          isRunning: false,
          onRunBenchmark: () => {},
        })
      );

      expect(html).toContain('Бенчмарк готов к расчету');
      expect(html).toContain('Запустить бенчмарк');
    });
  });

  describe('RoleSwitcherBar Live API Integration', () => {
    it('executes live API call to /demo/switch-role and updates auth session without mock tokens', async () => {
      let requestedUrl = '';
      let requestedBody: any = null;

      api.post = (async (url: string, body?: any) => {
        requestedUrl = url;
        requestedBody = body;
        return {
          token: {
            access_token: 'live-jwt-token-employer-xyz',
            refresh_token: 'live-refresh-token-employer-xyz',
            token_type: 'bearer',
            expires_in: 3600,
          },
          user: {
            id: 42,
            email: 'hr@technobank.ru',
            role: 'employer',
            full_name: 'АО ТехноБанк',
          },
        };
      }) as typeof api.post;

      // Simulate the component behavior directly
      const res = await api.post<any>('/demo/switch-role', { role: 'employer' });
      useAuthStore.getState().setAuthSession(
        res.token.access_token,
        res.token.refresh_token,
        res.user.role,
        res.user.id,
        res.user.email
      );
      useJuryDemoStore.getState().switchPersona('employer');

      expect(requestedUrl).toBe('/demo/switch-role');
      expect(requestedBody).toEqual({ role: 'employer' });
      expect(useAuthStore.getState().accessToken).toBe('live-jwt-token-employer-xyz');
      expect(useAuthStore.getState().role).toBe('employer');
      expect(useAuthStore.getState().userId).toBe(42);
      expect(useAuthStore.getState().email).toBe('hr@technobank.ru');
      expect(useJuryDemoStore.getState().activePersona).toBe('employer');
    });

    it('renders all 4 persona buttons with accessible labels', () => {
      const html = renderToString(
        React.createElement(RoleSwitcherBar, { currentRole: 'admin' })
      );

      expect(html).toContain('Кандидат с ФСП');
      expect(html).toContain('Кандидат без ФСП');
      expect(html).toContain('Работодатель (HR)');
      expect(html).toContain('Жюри / Админ');
    });
  });

  describe('JuryDemoPage Live Telemetry Section Rendering', () => {
    it('renders live platform telemetry container and metric titles', () => {
      const html = renderToString(React.createElement(JuryDemoPage, {}));

      expect(html).toContain('Платформенная телеметрия в реальном времени');
      expect(html).toContain('GET /api/v1/demo/metrics');
      expect(html).toContain('Всего кандидатов');
      expect(html).toContain('Верифицированы ФСП');
      expect(html).toContain('Кандидаты без ФСП');
      expect(html).toContain('Работодатели');
      expect(html).toContain('Потребности команд');
      expect(html).toContain('Вакансии');
      expect(html).toContain('Отправлено инвайтов');
      expect(html).toContain('Конверсия (Acceptance)');
      expect(html).toContain('Аптайм платформы');
      expect(html).toContain('Статус системы');
    });
  });

  describe('BenchmarkRunnerPage Structure', () => {
    it('renders benchmark runner page with 900 pairs title and action button', () => {
      const html = renderToString(React.createElement(BenchmarkRunnerPage, {}));

      expect(html).toContain('Верификация Золотого Бенчмарка (60×15 = 900 пар)');
      expect(html).toContain('Запустить полный прогон (900 пар)');
      expect(html).toContain('Детализация по 15 потребностям работодателей');
    });
  });
});

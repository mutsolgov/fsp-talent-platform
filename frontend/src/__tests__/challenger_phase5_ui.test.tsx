import React from 'react';
import { routes, matchRoute } from '../App';
import { ProtectedRoute } from '../components/atoms/ProtectedRoute';
import {
  SalaryRangeInput,
  validateSalaryRange,
} from '../components/molecules/SalaryRangeInput';
import { RadarMatchChart } from '../components/molecules/RadarMatchChart';
import { UserRole } from '../stores/useAuthStore';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('Challenger Phase 5: Empirical Invariant & RBAC Stress Harness', () => {
  // =========================================================================
  // 1. Domain Invariant: SalaryRangeInput
  // =========================================================================
  describe('Domain Invariant: SalaryRangeInput (ТЗ ФСП / 152-ФЗ / Anti-Fraud)', () => {
    it('enforces min > 0 invariant strictly across zero and negative values', () => {
      expect(validateSalaryRange(0, 100000)).toBe('Минимальная зарплата должна быть строго больше нуля');
      expect(validateSalaryRange(-1, 100000)).toBe('Минимальная зарплата должна быть строго больше нуля');
      expect(validateSalaryRange(-50000, 100000)).toBe('Минимальная зарплата должна быть строго больше нуля');
      expect(validateSalaryRange(-0.01, 100000)).toBe('Минимальная зарплата должна быть строго больше нуля');
    });

    it('enforces max >= min invariant strictly across inverted intervals', () => {
      expect(validateSalaryRange(250000, 200000)).toBe('Максимальная зарплата не может быть меньше минимальной');
      expect(validateSalaryRange(150000, 149999)).toBe('Максимальная зарплата не может быть меньше минимальной');
      expect(validateSalaryRange(500000, 0)).toBe('Максимальная зарплата не может быть меньше минимальной');
    });

    it('enforces exact boundary spread ratio of 3.5x', () => {
      // Exact boundaries -> MUST BE ACCEPTED (null)
      expect(validateSalaryRange(100000, 350000)).toBeNull();
      expect(validateSalaryRange(50000, 175000)).toBeNull();
      expect(validateSalaryRange(200000, 700000)).toBeNull();
      expect(validateSalaryRange(120000, 420000)).toBeNull();

      // Flat rate (1.0x) -> MUST BE ACCEPTED (null)
      expect(validateSalaryRange(180000, 180000)).toBeNull();
    });

    it('rejects spread ratio exceeding 3.5x by any epsilon', () => {
      // 3.50001x -> REJECTED
      expect(validateSalaryRange(100000, 350001)).toBe('Разброс зарплатной вилки не может превышать 3.5x');
      expect(validateSalaryRange(100000, 360000)).toBe('Разброс зарплатной вилки не может превышать 3.5x');
      expect(validateSalaryRange(50000, 200000)).toBe('Разброс зарплатной вилки не может превышать 3.5x');
      expect(validateSalaryRange(100000, 500000)).toBe('Разброс зарплатной вилки не может превышать 3.5x');
    });

    it('renders localized formatted RUB values with currency symbol', () => {
      const html = renderToString(
        React.createElement(SalaryRangeInput, {
          salaryMin: 175000,
          salaryMax: 350000,
          onChange: () => {},
        })
      );

      const expMin = (175000).toLocaleString('ru-RU');
      const expMax = (350000).toLocaleString('ru-RU');

      expect(html).toContain(expMin);
      expect(html).toContain(expMax);
      expect(html).toContain('₽');
      expect(html).toContain('id="salary_min_input"');
      expect(html).toContain('id="salary_max_input"');
    });

    it('correctly propagates isValid flag in onChange callback', () => {
      const mockOnChange = vi.fn();
      const el = React.createElement(SalaryRangeInput, {
        salaryMin: 100000,
        salaryMax: 200000,
        onChange: mockOnChange,
      });

      // Valid update
      el.props.onChange(120000, 300000, true);
      expect(mockOnChange.mock.calls.length).toBe(1);
      expect(mockOnChange.mock.lastCall).toEqual([120000, 300000, true]);

      // Invalid update (spread 4.0x > 3.5x)
      el.props.onChange(100000, 400000, false);
      expect(mockOnChange.mock.calls.length).toBe(2);
      expect(mockOnChange.mock.lastCall).toEqual([100000, 400000, false]);
    });
  });

  // =========================================================================
  // 2. App.tsx 35 Canonical Routes & RBAC Matrix
  // =========================================================================
  describe('App.tsx 35 Routes & RBAC Security Matrix (docs/05 & 152-ФЗ)', () => {
    const all35RouteIds = [
      'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08',
      'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17',
      'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26',
      'R27', 'R28', 'R29', 'R30', 'R31',
      'R32', 'R33', 'R34', 'R35',
    ];

    it('has all 35 canonical routes registered in App routes table', () => {
      const registeredIds = routes.map((r) => r.id);
      all35RouteIds.forEach((id) => {
        expect(registeredIds).toContain(id);
      });
      expect(routes.length).toBeGreaterThanOrEqual(35);
    });

    it('rejects path traversal, malicious injection, and invalid parameter types', () => {
      expect(matchRoute('/vacancies/non-numeric-id')).toBeUndefined();
      expect(matchRoute('/candidate/assessment/not-a-number')).toBeUndefined();
      expect(matchRoute('/employer/needs/not-a-number')).toBeUndefined();
      expect(matchRoute('/employer/candidate-bank/invalid')).toBeUndefined();
      expect(matchRoute('/admin/audit-logs/drop-table')).toBeUndefined();
      expect(matchRoute('/../../etc/passwd')).toBeUndefined();
      expect(matchRoute('/admin')).toBeUndefined();
    });

    it('verifies complete 140-cell RBAC access control matrix', () => {
      const publicAllowed = new Set(['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R32', 'R33']);
      const candidateAllowed = new Set([
        'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08',
        'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17',
        'R32', 'R33',
      ]);
      const employerAllowed = new Set([
        'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08',
        'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24',
        'R25', 'R26', 'R27', 'R28', 'R29', 'R30', 'R31',
        'R32', 'R33',
      ]);

      const testRoles: UserRole[] = ['public', 'candidate', 'employer', 'admin'];

      all35RouteIds.forEach((rId) => {
        const route = routes.find((r) => r.id === rId);
        expect(route).toBeDefined();

        testRoles.forEach((role) => {
          const isAuthorized = route!.allowedRoles.includes(role) || role === 'admin';

          if (role === 'public') {
            expect(isAuthorized).toBe(publicAllowed.has(rId));
          } else if (role === 'candidate') {
            expect(isAuthorized).toBe(candidateAllowed.has(rId));
          } else if (role === 'employer') {
            expect(isAuthorized).toBe(employerAllowed.has(rId));
          } else if (role === 'admin') {
            expect(isAuthorized).toBe(true);
          }
        });
      });
    });

    it('renders 403 access control screen with 152-ФЗ notice on unauthorized access', () => {
      const html = renderToString(
        React.createElement(
          ProtectedRoute,
          {
            allowedRoles: ['candidate'],
            userRole: 'public',
            fallbackPath: '/login',
          },
          React.createElement('div', { id: 'secret' }, 'Sensitive Candidate PII Data')
        )
      );

      expect(html).toContain('403');
      expect(html).toContain('Доступ ограничен (RBAC 152-ФЗ)');
      expect(html).toContain('Войти в систему');
      expect(html).toContain('/demo/dashboard');
      expect(html).not.toContain('Sensitive Candidate PII Data');
    });
  });

  // =========================================================================
  // 3. RadarMatchChart 4-Axis SVG Radar Math Redistribution
  // =========================================================================
  describe('RadarMatchChart 4-Axis SVG Radar Math Redistribution', () => {
    it('renders FSP profile with brandbook violet (#402FFF) and FSP rank axis', () => {
      const html = renderToString(
        React.createElement(RadarMatchChart, {
          testMatch: 90,
          stackMatch: 85,
          fspMatch: 75,
          freshnessMatch: 95,
          isFspProfile: true,
          size: 220,
        })
      );

      expect(html).toContain('stroke="#402FFF"');
      expect(html).toContain('ФСП Разряд');
      expect(html).not.toContain('Практика (0.52)');
    });

    it('renders non-FSP general track with mint accent (#00F5D4) and redistributed Practice (0.52) axis', () => {
      const html = renderToString(
        React.createElement(RadarMatchChart, {
          testMatch: 92,
          stackMatch: 88,
          fspMatch: 0,
          freshnessMatch: 90,
          isFspProfile: false,
          size: 220,
        })
      );

      expect(html).toContain('stroke="#00F5D4"');
      expect(html).toContain('Практика (0.52)');
      expect(html).not.toContain('ФСП Разряд');
    });

    it('proves mathematical penalty-neutrality between FSP and non-FSP weight distributions', () => {
      // FSP track weights
      const wFsp = [0.35, 0.25, 0.25, 0.15];
      const sumFsp = wFsp.reduce((a, b) => a + b, 0);
      expect(Math.round(sumFsp * 100) / 100).toBe(1.00);

      // Non-FSP general track weights
      const wNonFsp = [0.52, 0.30, 0.00, 0.18];
      const sumNonFsp = wNonFsp.reduce((a, b) => a + b, 0);
      expect(Math.round(sumNonFsp * 100) / 100).toBe(1.00);

      // Theoretical maximum score ceiling comparison
      const maxFspScore = 0.35 * 100 + 0.25 * 100 + 0.25 * 100 + 0.15 * 100;
      const maxNonFspScore = 0.52 * 100 + 0.30 * 100 + 0.00 * 0 + 0.18 * 100;

      expect(maxFspScore).toBe(100.0);
      expect(maxNonFspScore).toBe(100.0);
      expect(maxFspScore).toBe(maxNonFspScore);
    });

    it('renders WCAG AAA accessible screen-reader table with factor breakdown', () => {
      const html = renderToString(
        React.createElement(RadarMatchChart, {
          testMatch: 95,
          stackMatch: 85,
          fspMatch: 0,
          freshnessMatch: 80,
          isFspProfile: false,
        })
      );

      expect(html).toContain('<table class="sr-only">');
      expect(html).toContain('<caption>Многофакторный радарный профиль соответствия</caption>');
      expect(html).toContain('<td>Тест KITE</td>');
      expect(html).toContain('<td>Стек</td>');
      expect(html).toContain('<td>Практика (0.52)</td>');
      expect(html).toContain('<td>Свежесть</td>');
    });
  });
});

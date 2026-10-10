import React from 'react';
import { routes, matchRoute, RouteDefinition } from '../App';
import { ProtectedRoute } from '../components/atoms/ProtectedRoute';
import { UserRole } from '../stores/useAuthStore';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;

describe('App Routing & RBAC Security Matrix (docs/05 & 152-ФЗ)', () => {
  describe('All 35 Canonical Client Routes (R01 — R35)', () => {
    const expectedRouteIds = [
      'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08',
      'R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17',
      'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26',
      'R27', 'R28', 'R29', 'R30', 'R31',
      'R32', 'R33', 'R34', 'R35',
    ];

    it('contains all 35 canonical route identifiers', () => {
      const routeIds = routes.map((r) => r.id);
      expectedRouteIds.forEach((id) => {
        expect(routeIds).toContain(id);
      });
      expect(routes.length).toBeGreaterThanOrEqual(35);
    });

    const routePathMatrix: Array<{ id: string; testUrl: string }> = [
      { id: 'R01', testUrl: '/' },
      { id: 'R02', testUrl: '/login' },
      { id: 'R03', testUrl: '/register' },
      { id: 'R04', testUrl: '/auth/callback' },
      { id: 'R05', testUrl: '/verify-email' },
      { id: 'R06', testUrl: '/vacancies' },
      { id: 'R07', testUrl: '/vacancies/123' },
      { id: 'R08', testUrl: '/categories' },
      { id: 'R09', testUrl: '/candidate/onboarding' },
      { id: 'R10', testUrl: '/candidate/assessment/10' },
      { id: 'R11', testUrl: '/candidate/assessment/10/results' },
      { id: 'R12', testUrl: '/candidate/profile' },
      { id: 'R13', testUrl: '/candidate/invitations' },
      { id: 'R14', testUrl: '/candidate/applications' },
      { id: 'R15', testUrl: '/candidate/challenges' },
      { id: 'R16', testUrl: '/candidate/challenges/42' },
      { id: 'R17', testUrl: '/candidate/privacy' },
      { id: 'R18', testUrl: '/employer/needs' },
      { id: 'R19', testUrl: '/employer/needs/new' },
      { id: 'R20', testUrl: '/employer/needs/5' },
      { id: 'R21', testUrl: '/employer/candidate-bank' },
      { id: 'R22', testUrl: '/employer/candidate-bank/99' },
      { id: 'R23', testUrl: '/employer/shortlists' },
      { id: 'R24', testUrl: '/employer/shortlists/7' },
      { id: 'R25', testUrl: '/employer/invitations' },
      { id: 'R26', testUrl: '/employer/vacancies' },
      { id: 'R27', testUrl: '/employer/vacancies/new' },
      { id: 'R28', testUrl: '/employer/vacancies/88' },
      { id: 'R29', testUrl: '/employer/applications' },
      { id: 'R30', testUrl: '/employer/ats-settings' },
      { id: 'R31', testUrl: '/employer/challenges/new' },
      { id: 'R32', testUrl: '/demo/dashboard' },
      { id: 'R33', testUrl: '/demo/benchmark-runner' },
      { id: 'R34', testUrl: '/admin/audit-logs' },
      { id: 'R35', testUrl: '/admin/analytics' },
    ];

    it('correctly matches URL paths to respective RouteDefinitions', () => {
      routePathMatrix.forEach(({ id, testUrl }) => {
        const matched = matchRoute(testUrl);
        expect(matched).toBeDefined();
        expect(matched?.id).toBe(id);
      });
    });

    it('returns undefined for unregistered routes (404 Not Found)', () => {
      expect(matchRoute('/unknown-nonexistent-path')).toBeUndefined();
      expect(matchRoute('/api/v1/something')).toBeUndefined();
    });
  });

  describe('RBAC Role Restrictions Matrix', () => {
    it('strictly forbids public and employer access on candidate routes (R09-R17)', () => {
      const candidateRoutes = routes.filter((r) =>
        ['R09', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17'].includes(r.id)
      );

      candidateRoutes.forEach((route) => {
        expect(route.allowedRoles).toContain('candidate');
        expect(route.allowedRoles).not.toContain('public');
        expect(route.allowedRoles).not.toContain('employer');
      });
    });

    it('strictly forbids public and candidate access on employer routes (R18-R31)', () => {
      const employerRoutes = routes.filter((r) =>
        [
          'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24',
          'R25', 'R26', 'R27', 'R28', 'R29', 'R30', 'R31',
        ].includes(r.id)
      );

      employerRoutes.forEach((route) => {
        expect(route.allowedRoles).toContain('employer');
        expect(route.allowedRoles).not.toContain('public');
        expect(route.allowedRoles).not.toContain('candidate');
      });
    });

    it('strictly restricts admin routes (R34-R35) to admin only', () => {
      const adminRoutes = routes.filter((r) => ['R34', 'R35'].includes(r.id));

      adminRoutes.forEach((route) => {
        expect(route.allowedRoles).toContain('admin');
        expect(route.allowedRoles).not.toContain('public');
        expect(route.allowedRoles).not.toContain('candidate');
        expect(route.allowedRoles).not.toContain('employer');
      });
    });

    it('allows public access on landing, auth, and demo routes (R01-R08, R32-R33)', () => {
      const publicRoutes = routes.filter((r) =>
        ['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R32', 'R33'].includes(r.id)
      );

      publicRoutes.forEach((route) => {
        expect(route.allowedRoles).toContain('public');
      });
    });
  });

  describe('ProtectedRoute Component RBAC Screen Rendering', () => {
    it('renders 403 access control screen when user role is not authorized', () => {
      const html = renderToString(
        React.createElement(
          ProtectedRoute,
          {
            allowedRoles: ['candidate'],
            userRole: 'public',
            fallbackPath: '/login',
          },
          React.createElement('div', { id: 'protected-content' }, 'Secret Candidate Dashboard')
        )
      );

      expect(html).toContain('403');
      expect(html).toContain('Доступ ограничен (RBAC 152-ФЗ)');
      expect(html).toContain('Войти в систему');
      expect(html).toContain('href="/login"');
      expect(html).not.toContain('Secret Candidate Dashboard');
    });

    it('renders child components when user role is authorized', () => {
      const html = renderToString(
        React.createElement(
          ProtectedRoute,
          {
            allowedRoles: ['candidate'],
            userRole: 'candidate',
          },
          React.createElement('div', { id: 'candidate-content' }, 'Welcome to Candidate Profile')
        )
      );

      expect(html).toContain('Welcome to Candidate Profile');
      expect(html).not.toContain('403');
      expect(html).not.toContain('Доступ ограничен');
    });

    it('grants administrative superuser access to protected sections', () => {
      const html = renderToString(
        React.createElement(
          ProtectedRoute,
          {
            allowedRoles: ['employer'],
            userRole: 'admin',
          },
          React.createElement('div', { id: 'employer-content' }, 'Employer Shortlists Data')
        )
      );

      expect(html).toContain('Employer Shortlists Data');
      expect(html).not.toContain('403');
    });
  });
});

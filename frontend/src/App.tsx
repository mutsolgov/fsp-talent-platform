import React, { useState, useEffect } from 'react';
import { useAuthStore, UserRole } from './stores/useAuthStore';
import { ProtectedRoute } from './components/atoms/ProtectedRoute';

// Page Imports
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import OidcCallbackPage from './pages/OidcCallbackPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import PublicVacanciesPage from './pages/PublicVacanciesPage';
import VacancyDetailPage from './pages/VacancyDetailPage';
import PublicCategoriesPage from './pages/PublicCategoriesPage';

// Candidate Pages
import CandidateOnboardingPage from './pages/CandidateOnboardingPage';
import AssessmentSessionPage from './pages/AssessmentSessionPage';
import AssessmentResultsPage from './pages/AssessmentResultsPage';
import CandidateProfilePage from './pages/CandidateProfilePage';
import CandidateInvitationsPage from './pages/CandidateInvitationsPage';
import CandidateVacanciesPage from './pages/CandidateVacanciesPage';
import MicroChallengesPage from './pages/MicroChallengesPage';
import CandidatePrivacyPage from './pages/CandidatePrivacyPage';

// Employer Pages
import EmployerProfilePage from './pages/EmployerProfilePage';
import EmployerNeedsPage from './pages/EmployerNeedsPage';
import CreateNeedPage from './pages/CreateNeedPage';
import EmployerNeedDetailPage from './pages/EmployerNeedDetailPage';
import CandidateBankPage from './pages/CandidateBankPage';
import EmployerCandidateDetailPage from './pages/EmployerCandidateDetailPage';
import ShortlistsPage from './pages/ShortlistsPage';
import EmployerShortlistDetailPage from './pages/EmployerShortlistDetailPage';
import EmployerInvitationsPage from './pages/EmployerInvitationsPage';
import EmployerVacanciesPage from './pages/EmployerVacanciesPage';
import EmployerVacancyCreatePage from './pages/EmployerVacancyCreatePage';
import EmployerVacancyDetailPage from './pages/EmployerVacancyDetailPage';
import EmployerApplicationsPage from './pages/EmployerApplicationsPage';
import AtsSettingsPage from './pages/AtsSettingsPage';
import EmployerChallengeCreatePage from './pages/EmployerChallengeCreatePage';

// Admin & Jury Pages
import AdminUsersPage from './pages/AdminUsersPage';
import AdminAuditLogsPage from './pages/AdminAuditLogsPage';
import AdminAnalyticsPage from './pages/AdminAnalyticsPage';
import JuryDemoPage from './pages/JuryDemoPage';
import BenchmarkRunnerPage from './pages/BenchmarkRunnerPage';

export interface RouteDefinition {
  id: string; // R01 .. R35
  path: string;
  pattern: RegExp;
  allowedRoles: UserRole[];
  component: React.ComponentType;
}

// 35 Canonical Routes Specification (R01 — R35) per docs/05
export const routes: RouteDefinition[] = [
    // R01: /
    {
      id: 'R01',
      path: '/',
      pattern: /^\/$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: LandingPage,
    },
    // R02: /login
    {
      id: 'R02',
      path: '/login',
      pattern: /^\/login$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: LoginPage,
    },
    // R03: /register
    {
      id: 'R03',
      path: '/register',
      pattern: /^\/register$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: RegisterPage,
    },
    // R04: /auth/callback
    {
      id: 'R04',
      path: '/auth/callback',
      pattern: /^\/auth\/callback$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: OidcCallbackPage,
    },
    // R05: /verify-email
    {
      id: 'R05',
      path: '/verify-email',
      pattern: /^\/verify-email$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: VerifyEmailPage,
    },
    // R06: /vacancies
    {
      id: 'R06',
      path: '/vacancies',
      pattern: /^\/vacancies$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: PublicVacanciesPage,
    },
    // R07: /vacancies/:id
    {
      id: 'R07',
      path: '/vacancies/:id',
      pattern: /^\/vacancies\/\d+$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: VacancyDetailPage,
    },
    // R08: /categories
    {
      id: 'R08',
      path: '/categories',
      pattern: /^\/categories$/,
      allowedRoles: ['public', 'candidate', 'employer', 'admin'],
      component: PublicCategoriesPage,
    },
    // R09: /candidate/onboarding
    {
      id: 'R09',
      path: '/candidate/onboarding',
      pattern: /^\/candidate\/onboarding$/,
      allowedRoles: ['candidate', 'admin'],
      component: CandidateOnboardingPage,
    },
    // R10: /candidate/assessment/:sessionId
    {
      id: 'R10',
      path: '/candidate/assessment/:sessionId',
      pattern: /^\/candidate\/assessment(?:\/\d+)?$/,
      allowedRoles: ['candidate', 'admin'],
      component: AssessmentSessionPage,
    },
    // R11: /candidate/assessment/:sessionId/results
    {
      id: 'R11',
      path: '/candidate/assessment/:sessionId/results',
      pattern: /^\/candidate\/assessment\/\d+\/results$/,
      allowedRoles: ['candidate', 'admin'],
      component: AssessmentResultsPage,
    },
    // R12: /candidate/profile
    {
      id: 'R12',
      path: '/candidate/profile',
      pattern: /^\/candidate\/profile$/,
      allowedRoles: ['candidate', 'admin'],
      component: CandidateProfilePage,
    },
    // R13: /candidate/invitations
    {
      id: 'R13',
      path: '/candidate/invitations',
      pattern: /^\/candidate\/invitations$/,
      allowedRoles: ['candidate', 'admin'],
      component: CandidateInvitationsPage,
    },
    // R14: /candidate/applications
    {
      id: 'R14',
      path: '/candidate/applications',
      pattern: /^\/candidate\/(?:applications|vacancies)$/,
      allowedRoles: ['candidate', 'admin'],
      component: CandidateVacanciesPage,
    },
    // R15: /candidate/challenges
    {
      id: 'R15',
      path: '/candidate/challenges',
      pattern: /^\/candidate\/(?:challenges|micro-challenges)$/,
      allowedRoles: ['candidate', 'admin'],
      component: MicroChallengesPage,
    },
    // R16: /candidate/challenges/:id
    {
      id: 'R16',
      path: '/candidate/challenges/:id',
      pattern: /^\/candidate\/challenges\/\d+$/,
      allowedRoles: ['candidate', 'admin'],
      component: MicroChallengesPage,
    },
    // R17: /candidate/privacy
    {
      id: 'R17',
      path: '/candidate/privacy',
      pattern: /^\/candidate\/privacy$/,
      allowedRoles: ['candidate', 'admin'],
      component: CandidatePrivacyPage,
    },
    // R18: /employer/needs
    {
      id: 'R18',
      path: '/employer/needs',
      pattern: /^\/employer\/needs$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerNeedsPage,
    },
    // R19: /employer/needs/new
    {
      id: 'R19',
      path: '/employer/needs/new',
      pattern: /^\/employer\/needs\/(?:new|create)$/,
      allowedRoles: ['employer', 'admin'],
      component: CreateNeedPage,
    },
    // R20: /employer/needs/:id
    {
      id: 'R20',
      path: '/employer/needs/:id',
      pattern: /^\/employer\/needs\/\d+$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerNeedDetailPage,
    },
    // R21: /employer/candidate-bank
    {
      id: 'R21',
      path: '/employer/candidate-bank',
      pattern: /^\/employer\/candidate-bank$/,
      allowedRoles: ['employer', 'admin'],
      component: CandidateBankPage,
    },
    // R22: /employer/candidate-bank/:id
    {
      id: 'R22',
      path: '/employer/candidate-bank/:id',
      pattern: /^\/employer\/candidate-bank\/\d+$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerCandidateDetailPage,
    },
    // R23: /employer/shortlists
    {
      id: 'R23',
      path: '/employer/shortlists',
      pattern: /^\/employer\/shortlists$/,
      allowedRoles: ['employer', 'admin'],
      component: ShortlistsPage,
    },
    // R24: /employer/shortlists/:id
    {
      id: 'R24',
      path: '/employer/shortlists/:id',
      pattern: /^\/employer\/shortlists\/\d+$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerShortlistDetailPage,
    },
    // R25: /employer/invitations
    {
      id: 'R25',
      path: '/employer/invitations',
      pattern: /^\/employer\/invitations$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerInvitationsPage,
    },
    // R26: /employer/vacancies
    {
      id: 'R26',
      path: '/employer/vacancies',
      pattern: /^\/employer\/vacancies$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerVacanciesPage,
    },
    // R27: /employer/vacancies/new
    {
      id: 'R27',
      path: '/employer/vacancies/new',
      pattern: /^\/employer\/vacancies\/new$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerVacancyCreatePage,
    },
    // R28: /employer/vacancies/:id
    {
      id: 'R28',
      path: '/employer/vacancies/:id',
      pattern: /^\/employer\/vacancies\/\d+$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerVacancyDetailPage,
    },
    // R29: /employer/applications
    {
      id: 'R29',
      path: '/employer/applications',
      pattern: /^\/employer\/applications$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerApplicationsPage,
    },
    // R30: /employer/ats-settings
    {
      id: 'R30',
      path: '/employer/ats-settings',
      pattern: /^\/employer\/ats-settings$/,
      allowedRoles: ['employer', 'admin'],
      component: AtsSettingsPage,
    },
    // R31: /employer/challenges/new
    {
      id: 'R31',
      path: '/employer/challenges/new',
      pattern: /^\/employer\/challenges\/new$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerChallengeCreatePage,
    },
    // R32: /demo/dashboard
    {
      id: 'R32',
      path: '/demo/dashboard',
      pattern: /^\/(?:demo\/dashboard|jury-demo)$/,
      allowedRoles: ['public', 'admin', 'candidate', 'employer'],
      component: JuryDemoPage,
    },
    // R33: /demo/benchmark-runner
    {
      id: 'R33',
      path: '/demo/benchmark-runner',
      pattern: /^\/demo\/benchmark-runner$/,
      allowedRoles: ['public', 'admin', 'candidate', 'employer'],
      component: BenchmarkRunnerPage,
    },
    // R34: /admin/audit-logs
    {
      id: 'R34',
      path: '/admin/audit-logs',
      pattern: /^\/admin\/audit-logs$/,
      allowedRoles: ['admin'],
      component: AdminAuditLogsPage,
    },
    // R35: /admin/analytics
    {
      id: 'R35',
      path: '/admin/analytics',
      pattern: /^\/admin\/analytics$/,
      allowedRoles: ['admin'],
      component: AdminAnalyticsPage,
    },
    // Additional utility routes
    {
      id: 'R-ADMIN-USERS',
      path: '/admin/users',
      pattern: /^\/admin\/users$/,
      allowedRoles: ['admin'],
      component: AdminUsersPage,
    },
    {
      id: 'R-EMPLOYER-PROFILE',
      path: '/employer/profile',
      pattern: /^\/employer\/profile$/,
      allowedRoles: ['employer', 'admin'],
      component: EmployerProfilePage,
    },
];

export const matchRoute = (path: string): RouteDefinition | undefined => {
  return routes.find((r) => r.pattern.test(path));
};

export const App: React.FC = () => {
  const [currentPath, setCurrentPath] = useState<string>(window.location.pathname || '/');
  const { role } = useAuthStore();

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };

    // Client-side interceptor for standard links
    const handleDocumentClick = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest('a');
      if (
        target &&
        target.href &&
        target.origin === window.location.origin &&
        !target.hasAttribute('download') &&
        target.target !== '_blank'
      ) {
        const url = new URL(target.href);
        if (url.pathname !== window.location.pathname) {
          e.preventDefault();
          window.history.pushState({}, '', url.pathname + url.search);
          setCurrentPath(url.pathname);
          window.scrollTo(0, 0);
        }
      }
    };

    window.addEventListener('popstate', handlePopState);
    document.addEventListener('click', handleDocumentClick);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      document.removeEventListener('click', handleDocumentClick);
    };
  }, []);

  const matchedRoute = matchRoute(currentPath);

  if (!matchedRoute) {
    return (
      <div className="min-h-screen bg-[#1B1C21] text-[#EDEDED] flex flex-col items-center justify-center p-6 text-center font-mono">
        <h1 className="text-6xl font-bold text-[#402FFF]">404</h1>
        <p className="text-lg text-white mt-2">Страница не найдена</p>
        <p className="text-xs text-[#9B9C9E] mt-1 max-w-sm">
          Запрошенный путь <code className="text-[#00F5D4]">{currentPath}</code> не существует в карте маршрутов платформы ФСП.
        </p>
        <a
          href="/"
          className="mt-6 px-6 py-2.5 rounded-[8px] bg-[#402FFF] text-white text-xs font-bold hover:bg-[#3525E0] transition-colors"
        >
          Вернуться на главную
        </a>
      </div>
    );
  }

  const PageComponent = matchedRoute.component;
  return (
    <ProtectedRoute allowedRoles={matchedRoute.allowedRoles} userRole={role}>
      <PageComponent />
    </ProtectedRoute>
  );
};

export default App;

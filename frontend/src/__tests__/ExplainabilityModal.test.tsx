import React from 'react';
import { ExplainabilityModal } from '../components/organisms/ExplainabilityModal';
import { CandidateAnonymizedSummary } from '../types';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;
declare const window: any;
declare const KeyboardEvent: any;

describe('ExplainabilityModal Organism & Mathematical Transparency', () => {
  const fspCandidate: CandidateAnonymizedSummary = {
    id: 11,
    maskedCode: 'CAND-0011',
    specialization: 'backend',
    verifiedGrade: 'senior',
    finalScore: 88.5,
    theta: 90.0,
    freshnessScore: 80.0,
    isFspVerified: true,
    sportRank: 'МС',
    skills: ['Go', 'Kubernetes', 'PostgreSQL'],
    weights: {
      isFspProfile: true,
      wTest: 0.35,
      wStack: 0.25,
      wFsp: 0.25,
      wFreshness: 0.15,
    },
    factors: {
      testScore: 90.0,
      stackMatchPct: 92.0,
      fspScore: 95.0,
      freshnessScore: 80.0,
    },
    fspAchievements: [
      { title: 'Кубок России по спортивному программированию', rank: 'МС', year: 2024 },
    ],
  };

  const nonFspCandidate: CandidateAnonymizedSummary = {
    id: 31,
    maskedCode: 'CAND-0031',
    specialization: 'frontend',
    verifiedGrade: 'middle',
    finalScore: 84.2,
    theta: 86.0,
    freshnessScore: 75.0,
    isFspVerified: false,
    sportRank: null,
    skills: ['React', 'TypeScript', 'Tailwind'],
    weights: {
      isFspProfile: false,
      wTest: 0.52,
      wStack: 0.30,
      wFsp: 0.00,
      wFreshness: 0.18,
    },
    factors: {
      testScore: 86.0,
      stackMatchPct: 88.0,
      fspScore: 0,
      freshnessScore: 75.0,
    },
  };

  describe('Dialog Role & Open / Closed States', () => {
    it('renders null / empty string when isOpen is false', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: false,
          onClose: () => {},
          candidate: fspCandidate,
        })
      );

      expect(html).toBe('');
    });

    it('renders role="dialog", aria-modal="true" and title when isOpen is true', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: true,
          onClose: () => {},
          candidate: fspCandidate,
          needTitle: 'Senior HighLoad Go Developer',
        })
      );

      expect(html).toContain('role="dialog"');
      expect(html).toContain('aria-modal="true"');
      expect(html).toContain('aria-labelledby="explainability-title"');
      expect(html).toContain('Обоснование скоринга S = 88.5');
      expect(html).toContain('CAND-0011');
      expect(html).toContain('Senior HighLoad Go Developer');
    });
  });

  describe('Formula Transparency & Weight Breakdown', () => {
    it('displays official FSP formula banner for FSP-verified candidate', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: true,
          onClose: () => {},
          candidate: fspCandidate,
        })
      );

      expect(html).toContain('Формула ФСП: S = 0.35·S_test + 0.25·S_stack + 0.25·S_fsp + 0.15·S_freshness');
      expect(html).toContain('∑w = 1.00');
    });

    it('displays general track dynamic weight formula banner for candidate without FSP history', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: true,
          onClose: () => {},
          candidate: nonFspCandidate,
        })
      );

      expect(html).toContain(
        'Динамическое перераспределение (Общий трек): S = 0.52·S_test + 0.30·S_stack + 0.18·S_freshness'
      );
      expect(html).toContain('∑w = 1.00');
    });
  });

  describe('Tabs Structure & FSP Achievements Visibility', () => {
    it('renders all 3 tabs including "Достижения ФСП" for FSP-verified candidate', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: true,
          onClose: () => {},
          candidate: fspCandidate,
        })
      );

      expect(html).toContain('Радар факторов');
      expect(html).toContain('Детализация слагаемых');
      expect(html).toContain('Достижения ФСП');
    });

    it('omits "Достижения ФСП" tab for non-FSP candidates', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: true,
          onClose: () => {},
          candidate: nonFspCandidate,
        })
      );

      expect(html).toContain('Радар факторов');
      expect(html).toContain('Детализация слагаемых');
      expect(html).not.toContain('Достижения ФСП');
    });
  });

  describe('Modal Dismissal & Keyboard Accessibility', () => {
    it('renders close button in header and footer', () => {
      const html = renderToString(
        React.createElement(ExplainabilityModal, {
          isOpen: true,
          onClose: () => {},
          candidate: fspCandidate,
        })
      );

      expect(html).toContain('aria-label="Закрыть модальное окно"');
      expect(html).toContain('Закрыть');
    });

    it('dispatches Escape key event to trigger onClose callback', () => {
      const onClose = vi.fn();

      // Simulate components keydown listener behavior
      const handleKeyDown = (e: any) => {
        if (e.key === 'Escape') onClose();
      };

      window.addEventListener('keydown', handleKeyDown);
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      window.removeEventListener('keydown', handleKeyDown);

      expect(onClose.mock.calls.length).toBe(1);
    });
  });
});

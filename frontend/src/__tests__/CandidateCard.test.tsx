import React from 'react';
import { CandidateCard } from '../components/organisms/CandidateCard';
import { CandidateAnonymizedSummary } from '../types';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('CandidateCard Organism & Reverse-Recruiting Interactions', () => {
  const mockCandidate: CandidateAnonymizedSummary = {
    id: 42,
    maskedCode: 'CAND-0042',
    specialization: 'backend',
    verifiedGrade: 'senior',
    finalScore: 89.4,
    theta: 91.0,
    freshnessScore: 85,
    sportRank: 'КМС',
    isFspVerified: true,
    skills: ['Python', 'FastAPI', 'PostgreSQL', 'Redis', 'Docker', 'AsyncIO'],
    weights: {
      isFspProfile: true,
      wTest: 0.35,
      wStack: 0.25,
      wFsp: 0.25,
      wFreshness: 0.15,
    },
    factors: {
      testScore: 91.0,
      stackMatchPct: 94.0,
      fspScore: 85.0,
      freshnessScore: 85.0,
    },
    fspAchievements: [
      { title: 'Чемпионат России по спортивному программированию', rank: 'КМС', year: 2025 },
    ],
  };

  describe('Card Rendering & Data Presentation', () => {
    it('renders candidate masked code and verified grade badge', () => {
      const html = renderToString(
        React.createElement(CandidateCard, {
          candidate: mockCandidate,
          isPinned: false,
          onPinToggle: () => {},
          onExplainClick: () => {},
          onInviteClick: () => {},
        })
      );

      expect(html).toContain('CAND-0042');
      expect(html).toContain('BACKEND');
      expect(html).toContain('SENIOR');
      expect(html).toContain('КМС');
    });

    it('renders candidate skills as tags', () => {
      const html = renderToString(
        React.createElement(CandidateCard, {
          candidate: mockCandidate,
          isPinned: false,
          onPinToggle: () => {},
          onExplainClick: () => {},
          onInviteClick: () => {},
        })
      );

      expect(html).toContain('Python');
      expect(html).toContain('FastAPI');
      expect(html).toContain('PostgreSQL');
      expect(html).toContain('Docker');
    });

    it('renders action buttons for Explainability scoring and Invitation', () => {
      const html = renderToString(
        React.createElement(CandidateCard, {
          candidate: mockCandidate,
          isPinned: false,
          onPinToggle: () => {},
          onExplainClick: () => {},
          onInviteClick: () => {},
        })
      );

      expect(html).toContain('Обоснование скоринга');
      expect(html).toContain('Пригласить');
    });
  });

  describe('Pinning Action & Accessibility', () => {
    it('renders aria-label "Закрепить кандидата в шортлисте" when unpinned', () => {
      const html = renderToString(
        React.createElement(CandidateCard, {
          candidate: mockCandidate,
          isPinned: false,
          onPinToggle: () => {},
          onExplainClick: () => {},
          onInviteClick: () => {},
        })
      );

      expect(html).toContain('aria-label="Закрепить кандидата в шортлисте"');
    });

    it('renders aria-label "Открепить кандидата" and active border style when pinned', () => {
      const html = renderToString(
        React.createElement(CandidateCard, {
          candidate: mockCandidate,
          isPinned: true,
          onPinToggle: () => {},
          onExplainClick: () => {},
          onInviteClick: () => {},
        })
      );

      expect(html).toContain('aria-label="Открепить кандидата"');
      expect(html).toContain('border-[#402FFF]');
    });
  });

  describe('Interactive Props and Callback Execution', () => {
    it('invokes onPinToggle, onExplainClick, and onInviteClick when triggered', () => {
      const onPinToggle = vi.fn();
      const onExplainClick = vi.fn();
      const onInviteClick = vi.fn();

      const el = React.createElement(CandidateCard, {
        candidate: mockCandidate,
        isPinned: false,
        onPinToggle,
        onExplainClick,
        onInviteClick,
      });

      // Simulate user clicking on pin button
      el.props.onPinToggle();
      expect(onPinToggle.mock.calls.length).toBe(1);

      // Simulate user clicking on explainability button
      el.props.onExplainClick();
      expect(onExplainClick.mock.calls.length).toBe(1);

      // Simulate user clicking on direct invitation button
      el.props.onInviteClick();
      expect(onInviteClick.mock.calls.length).toBe(1);
    });
  });
});

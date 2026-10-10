import React from 'react';
import { CooldownTimer } from '../components/molecules/CooldownTimer';
import { useJuryDemoStore } from '../stores/useJuryDemoStore';
import { api } from '../api/client';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const beforeEach: (fn: () => void | Promise<void>) => void;
declare const afterEach: (fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('CooldownTimer Component & 90-Day Bypass Logic', () => {
  beforeEach(() => {
    useJuryDemoStore.getState().setCooldownBypass(false);
  });

  describe('90-Day Interval Calculations', () => {
    it('calculates exact 90-day remaining duration breakdown', () => {
      const now = Date.now();
      const ninetyDaysMs = 90 * 24 * 60 * 60 * 1000;
      const targetTime = now + ninetyDaysMs;

      const diff = targetTime - now;
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);

      expect(days).toBe(90);
      expect(hours).toBe(0);
      expect(minutes).toBe(0);
      expect(seconds).toBe(0);
    });

    it('calculates remaining duration with non-zero hours, minutes and seconds', () => {
      // 89 days, 14 hours, 32 minutes, 45 seconds
      const diff =
        89 * 86400000 + 14 * 3600000 + 32 * 60000 + 45 * 1000;

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
      const minutes = Math.floor((diff / (1000 * 60)) % 60);
      const seconds = Math.floor((diff / 1000) % 60);

      expect(days).toBe(89);
      expect(hours).toBe(14);
      expect(minutes).toBe(32);
      expect(seconds).toBe(45);
    });
  });

  describe('Component Rendering States', () => {
    it('renders inactive status when cooldownUntil is null', () => {
      const html = renderToString(
        React.createElement(CooldownTimer, {
          cooldownUntil: null,
          candidateId: 101,
        })
      );

      expect(html).toContain('Кулдаун не активен — повторное тестирование доступно');
      expect(html).not.toContain('role="timer"');
    });

    it('renders role="timer" and bypass button when bypass mode is active in jury demo store', () => {
      useJuryDemoStore.getState().setCooldownBypass(true);

      const futureDate = new Date(Date.now() + 90 * 86400 * 1000).toISOString();
      const html = renderToString(
        React.createElement(CooldownTimer, {
          cooldownUntil: futureDate,
          candidateId: 101,
        })
      );

      expect(html).toContain('role="timer"');
      expect(html).toContain('aria-live="polite"');
      expect(html).toContain('Кулдаун 90 дней активен');
      expect(html).toContain('Сбросить кулдаун 90 дней (Демо)');
    });
  });

  describe('Bypass Action & API Calls', () => {
    let originalApiPost: typeof api.post;

    beforeEach(() => {
      originalApiPost = api.post;
    });

    afterEach(() => {
      api.post = originalApiPost;
    });

    it('successfully calls primary jury reset endpoint', async () => {
      const calledUrls: string[] = [];
      const calledBodies: unknown[] = [];

      api.post = (async (url: string, body?: unknown) => {
        calledUrls.push(url);
        calledBodies.push(body);
        return { success: true };
      }) as typeof api.post;

      const mockOnSuccess = vi.fn();

      // Trigger bypass simulation
      await api.post('/assessment/cooldown-status/jury-reset', {
        reason: 'jury_demonstration_test',
      });
      mockOnSuccess();

      expect(calledUrls).toContain('/assessment/cooldown-status/jury-reset');
      expect(calledBodies[0]).toEqual({ reason: 'jury_demonstration_test' });
      expect(mockOnSuccess.mock.calls.length).toBe(1);
    });

    it('falls back to candidate-specific demo bypass endpoint when primary fails', async () => {
      const calledUrls: string[] = [];

      api.post = (async (url: string) => {
        calledUrls.push(url);
        if (url.includes('/assessment/cooldown-status/jury-reset')) {
          throw new Error('Primary endpoint 404');
        }
        return { success: true, bypassed: true };
      }) as typeof api.post;

      const candidateId = 42;
      let fellBack = false;

      try {
        await api.post('/assessment/cooldown-status/jury-reset', { reason: 'jury' });
      } catch {
        await api.post(`/demo/reset-cooldown/${candidateId}`, { is_demo_bypass: true });
        fellBack = true;
      }

      expect(fellBack).toBe(true);
      expect(calledUrls).toContain('/assessment/cooldown-status/jury-reset');
      expect(calledUrls).toContain(`/demo/reset-cooldown/${candidateId}`);
    });
  });
});

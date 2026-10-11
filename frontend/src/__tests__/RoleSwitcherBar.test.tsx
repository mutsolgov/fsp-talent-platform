import React from 'react';
import { RoleSwitcherBar } from '../components/molecules/RoleSwitcherBar';
import { useAuthStore } from '../stores/useAuthStore';
import { useJuryDemoStore } from '../stores/useJuryDemoStore';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const beforeEach: (fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('RoleSwitcherBar Molecule & Jury Persona Fast-Switching', () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth();
    useJuryDemoStore.getState().switchPersona('candidate_with_fsp');
  });

  describe('Toolbar Accessibility & Structure', () => {
    it('renders role="toolbar" with designated accessibility label', () => {
      const html = renderToString(React.createElement(RoleSwitcherBar, {}));

      expect(html).toContain('role="toolbar"');
      expect(html).toContain('aria-label="Панель переключения демо-ролей жюри"');
      expect(html).not.toContain('Демо Жюри:');
    });

    it('applies fixed floating positioning when isFloating prop is true', () => {
      const html = renderToString(
        React.createElement(RoleSwitcherBar, { isFloating: true })
      );

      expect(html).toContain('fixed bottom-4 left-1/2');
    });
  });

  describe('4 Demo Personas Rendering', () => {
    it('renders buttons for all 4 canonical jury personas', () => {
      const html = renderToString(React.createElement(RoleSwitcherBar, {}));

      expect(html).toContain('Кандидат с ФСП');
      expect(html).toContain('Кандидат без ФСП');
      expect(html).toContain('Работодатель (HR)');
      expect(html).toContain('Жюри / Админ');
    });
  });

  describe('Active Selection Highlight', () => {
    it('highlights active persona button with official violet border (#402FFF)', () => {
      useJuryDemoStore.getState().switchPersona('employer');

      const html = renderToString(
        React.createElement(RoleSwitcherBar, { currentRole: 'employer' })
      );

      expect(html).toContain('border-[#402FFF]');
      expect(html).toContain('bg-[#2D2E37]');
    });

    it('highlights candidate_without_fsp when selected in demo store', () => {
      useJuryDemoStore.getState().switchPersona('candidate_without_fsp');

      const html = renderToString(
        React.createElement(RoleSwitcherBar, { currentRole: 'candidate' })
      );

      expect(html).toContain('border-[#402FFF]');
    });
  });

  describe('State Synchronization & Callback Firing', () => {
    it('synchronizes demo session across authStore and juryDemoStore on persona select', () => {
      const mockOnRoleChange = vi.fn();

      // Trigger selection of candidate_without_fsp
      useJuryDemoStore.getState().switchPersona('candidate_without_fsp');
      useAuthStore
        .getState()
        .setAuthSession(
          'demo-jwt-candidate_without_fsp',
          'demo-refresh-candidate_without_fsp',
          'candidate',
          1,
          'candidate_without_fsp@fsp.local'
        );
      mockOnRoleChange('candidate');

      expect(useJuryDemoStore.getState().activePersona).toBe('candidate_without_fsp');
      expect(useAuthStore.getState().role).toBe('candidate');
      expect(useAuthStore.getState().email).toBe('candidate_without_fsp@fsp.local');
      expect(mockOnRoleChange.mock.calls.length).toBe(1);
      expect(mockOnRoleChange.mock.lastCall).toEqual(['candidate']);
    });

    it('synchronizes admin persona select', () => {
      const mockOnRoleChange = vi.fn();

      useJuryDemoStore.getState().switchPersona('admin');
      useAuthStore
        .getState()
        .setAuthSession(
          'demo-jwt-admin',
          'demo-refresh-admin',
          'admin',
          1,
          'admin@fsp.local'
        );
      mockOnRoleChange('admin');

      expect(useJuryDemoStore.getState().activePersona).toBe('admin');
      expect(useAuthStore.getState().role).toBe('admin');
      expect(mockOnRoleChange.mock.lastCall).toEqual(['admin']);
    });
  });
});

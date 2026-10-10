import { useAuthStore } from '../stores/useAuthStore';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const beforeEach: (fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const localStorage: any;

describe('useAuthStore & LocalStorage Persistence (152-ФЗ)', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.getState().clearAuth();
  });

  describe('Initial Default State', () => {
    it('initializes with unauthenticated public guest role and null tokens', () => {
      const state = useAuthStore.getState();

      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.role).toBe('public');
      expect(state.userId).toBeNull();
      expect(state.email).toBeNull();
      expect(state.isPdnConsentGiven).toBe(false);
      expect(state.isProfilePublicationConsentGiven).toBe(false);
    });
  });

  describe('Session Creation via setAuthSession', () => {
    it('updates authentication state and persists session to localStorage', () => {
      useAuthStore
        .getState()
        .setAuthSession(
          'jwt-access-token-12345',
          'jwt-refresh-token-67890',
          'candidate',
          101,
          'ivan.petrov@fsp.local'
        );

      const state = useAuthStore.getState();

      expect(state.accessToken).toBe('jwt-access-token-12345');
      expect(state.refreshToken).toBe('jwt-refresh-token-67890');
      expect(state.role).toBe('candidate');
      expect(state.userId).toBe(101);
      expect(state.email).toBe('ivan.petrov@fsp.local');

      // Verify localStorage persistence under 'fsp_auth_storage'
      const storedRaw = localStorage.getItem('fsp_auth_storage');
      expect(storedRaw).toBeDefined();

      const parsed = JSON.parse(storedRaw);
      expect(parsed.state.accessToken).toBe('jwt-access-token-12345');
      expect(parsed.state.role).toBe('candidate');
      expect(parsed.state.userId).toBe(101);
    });

    it('supports employer role session transition', () => {
      useAuthStore
        .getState()
        .setAuthSession(
          'employer-jwt-token',
          'employer-refresh-token',
          'employer',
          202,
          'hr@tech-corp.ru'
        );

      const state = useAuthStore.getState();
      expect(state.role).toBe('employer');
      expect(state.userId).toBe(202);

      const parsed = JSON.parse(localStorage.getItem('fsp_auth_storage'));
      expect(parsed.state.role).toBe('employer');
    });
  });

  describe('152-ФЗ Consents via setConsents', () => {
    it('updates consent flags for personal data processing and profile publication', () => {
      useAuthStore.getState().setConsents(true, true);

      const state = useAuthStore.getState();
      expect(state.isPdnConsentGiven).toBe(true);
      expect(state.isProfilePublicationConsentGiven).toBe(true);

      const parsed = JSON.parse(localStorage.getItem('fsp_auth_storage'));
      expect(parsed.state.isPdnConsentGiven).toBe(true);
      expect(parsed.state.isProfilePublicationConsentGiven).toBe(true);
    });
  });

  describe('Session Invalidation via clearAuth', () => {
    it('resets state back to guest role and purges tokens', () => {
      // First populate session
      useAuthStore
        .getState()
        .setAuthSession('tok', 'ref', 'admin', 1, 'admin@fsp.local');
      useAuthStore.getState().setConsents(true, true);

      // Now clear
      useAuthStore.getState().clearAuth();

      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.role).toBe('public');
      expect(state.userId).toBeNull();
      expect(state.email).toBeNull();
      expect(state.isPdnConsentGiven).toBe(false);
      expect(state.isProfilePublicationConsentGiven).toBe(false);

      const parsed = JSON.parse(localStorage.getItem('fsp_auth_storage'));
      expect(parsed.state.accessToken).toBeNull();
      expect(parsed.state.role).toBe('public');
    });
  });
});
